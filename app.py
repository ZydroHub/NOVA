import logging
import math
import os
import json
import re
import socket
import struct
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import threading
from contextlib import asynccontextmanager
from asyncio import sleep
from datetime import datetime, timedelta

import psutil
import uvicorn

from config import PORT, setup_logging
from news_alerts import fetch_swedish_alerts
from telegram_bot import start_telegram_bot, stop_telegram_bot


def _pip_reinstall(packages):
    """Best-effort dependency repair in the current interpreter environment."""
    cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "--force-reinstall", *packages]
    try:
        result = subprocess.run(cmd, check=False, capture_output=True, text=True)
        return result.returncode == 0
    except Exception:
        return False


def _import_fastapi_components():
    try:
        from fastapi import FastAPI as _FastAPI
        from fastapi import WebSocket as _WebSocket
        from fastapi import WebSocketDisconnect as _WebSocketDisconnect
        from fastapi.middleware.cors import CORSMiddleware as _CORSMiddleware
        return _FastAPI, _CORSMiddleware, _WebSocket, _WebSocketDisconnect
    except Exception as exc:
        msg = str(exc).lower()
        if "annotated_doc" in msg or "cannot import name 'doc'" in msg:
            repaired = _pip_reinstall(["annotated-doc==0.0.4", "fastapi==0.129.2"])
            if repaired:
                from fastapi import FastAPI as _FastAPI
                from fastapi import WebSocket as _WebSocket
                from fastapi import WebSocketDisconnect as _WebSocketDisconnect
                from fastapi.middleware.cors import CORSMiddleware as _CORSMiddleware
                return _FastAPI, _CORSMiddleware, _WebSocket, _WebSocketDisconnect
        raise


def _import_chat_state():
    try:
        from chat_ai import router as _chat_router, ai as _ai_state
        return _chat_router, _ai_state
    except Exception as exc:
        msg = str(exc).lower()
        repaired = False
        if "cannot import name 'tqdm' from 'tqdm.auto'" in msg or "tqdm.auto" in msg:
            repaired = _pip_reinstall(["tqdm>=4.66,<5", "huggingface-hub==1.4.1"])
        elif "no module named 'llama_cpp'" in msg:
            repaired = _pip_reinstall(["llama-cpp-python==0.3.16"])
        if repaired:
            from chat_ai import router as _chat_router, ai as _ai_state
            return _chat_router, _ai_state
        raise


FastAPI, CORSMiddleware, WebSocket, WebSocketDisconnect = _import_fastapi_components()
chat_router, ai_state = _import_chat_state()

setup_logging()
logger = logging.getLogger(__name__)

_startup_lock = threading.Lock()
_startup_completed = False


def _initialize_backend_once() -> None:
    global _startup_completed
    with _startup_lock:
        if _startup_completed:
            logger.info("NOVA backend initialization already completed in this process; skipping duplicate startup.")
            return

        logger.info("NOVA backend starting up on port %s", PORT)
        logger.debug("SKIP_MODEL_LOAD=%s", os.environ.get("SKIP_MODEL_LOAD", ""))
        if not os.environ.get("SKIP_MODEL_LOAD"):
            logger.info("Loading chat model...")
            ai_state.load_model()
            logger.info("Chat model loaded.")
            # Tool model is loaded in a subprocess when needed (avoids thread/crash issues)

        try:
            from task_scheduler import init_scheduler
            init_scheduler(ai_state.conv_manager)
        except Exception as e:
            logger.warning("Task scheduler not started: %s", e)

        _startup_completed = True
        logger.info("NOVA backend ready.")


@asynccontextmanager
async def lifespan(_app):
    _initialize_backend_once()
    telegram_bot = start_telegram_bot()
    try:
        yield
    finally:
        if telegram_bot is not None:
            telegram_bot.stop()
        else:
            stop_telegram_bot()

app = FastAPI(title="NOVA Unified Backend", lifespan=lifespan)

# Enable CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the routers
app.include_router(chat_router)

@app.get("/health")
async def health():
    """Simple health check for monitoring and tests."""
    return {"status": "ok"}


@app.get("/system/stats")
async def system_stats():
    """Get current system stats (CPU, RAM, temperature, wattage)."""
    try:
        cpu_percent = psutil.cpu_percent(interval=0.05)
        ram = psutil.virtual_memory()
        ram_percent = ram.percent

        temp = _read_temperature_celsius()
        watts = _read_power_watts()
        now = datetime.now().strftime("%H:%M:%S")
        cpu_value = _finite_float(cpu_percent)
        ram_value = _finite_float(ram_percent)
        temp_value = _finite_float(temp)
        watts_value = _finite_float(watts)

        stats = {
            # Canonical keys used by the renderer.
            "time": now,
            "cpu_percent": round(cpu_value, 1),
            "memory_percent": round(ram_value, 1),
            "temperature": round(temp_value, 1),
            "wattage": round(watts_value, 2),
            # Backward-compatible aliases.
            "cpu": round(cpu_value, 1),
            "ram": round(ram_value, 1),
            "temp": round(temp_value, 1),
            "watts": round(watts_value, 2),
        }
        logger.debug("System stats sampled: %s", stats)
        return stats
    except Exception as e:
        logger.warning("Error getting system stats: %s", e)
        return {
            "time": datetime.now().strftime("%H:%M:%S"),
            "cpu_percent": 0,
            "memory_percent": 0,
            "temperature": 0,
            "wattage": 0,
            "cpu": 0,
            "ram": 0,
            "temp": 0,
            "watts": 0,
        }


@app.websocket("/ws/system-stats")
async def system_stats_websocket(websocket):
    """Push system stats once per second to avoid polling overhead on the Pi."""
    await websocket.accept()
    try:
        while True:
            await websocket.send_json(await system_stats())
            await sleep(1)
    except WebSocketDisconnect:
        logger.info("System stats websocket disconnected")
    except Exception as exc:
        logger.debug("System stats websocket closed with error: %s", exc)


def _read_temperature_celsius() -> float:
    """Read CPU temperature with Linux/Raspberry Pi fallbacks."""
    # 1) psutil sensors API (works on many Linux systems, including some Pi setups).
    try:
        temps = psutil.sensors_temperatures()
        if temps:
            for entries in temps.values():
                if entries and entries[0].current is not None:
                    return float(entries[0].current)
    except (AttributeError, OSError):
        pass

    # 2) Direct sysfs read (common on Raspberry Pi).
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r", encoding="utf-8") as f:
            milli_c = f.read().strip()
        if milli_c:
            return float(milli_c) / 1000.0
    except (OSError, ValueError):
        pass

    # 3) vcgencmd fallback (Pi firmware utility).
    try:
        result = subprocess.run(
            ["vcgencmd", "measure_temp"],
            capture_output=True,
            text=True,
            timeout=1,
            check=False,
        )
        output = (result.stdout or "").strip()
        # Expected format: temp=52.8'C
        if output.startswith("temp=") and "'" in output:
            value = output.split("=", 1)[1].split("'", 1)[0]
            return float(value)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass

    logger.debug("Temperature sources unavailable; returning 0C.")
    return 0.0


def _run_cmd(args: list[str], timeout: float = 1.0) -> str:
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return (result.stdout or "").strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


def _parse_first_float(text: str) -> float | None:
    match = re.search(r"[-+]?\d*\.?\d+", text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _parse_measure_volts() -> float | None:
    output = _run_cmd(["vcgencmd", "measure_volts"])
    # Expected: volt=0.7200V
    if not output:
        return None
    return _parse_first_float(output)


def _read_power_watts() -> float:
    """Estimate Pi 5 power from PMIC rails via vcgencmd pmic_read_adc."""
    pmic_output = _run_cmd(["vcgencmd", "pmic_read_adc"], timeout=1.5)
    if not pmic_output:
        return 0.0

    # Parse PMIC ADC output: rail_name (channel)=value_with_unit
    # Examples: 5V0_A current(0)=0.150A or 5V0_A=0.150A
    rails: dict[str, tuple[float | None, float | None]] = {}  # name -> (voltage, current)

    for raw_line in pmic_output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        # Extract rail name (e.g., "3V3_SYS_A", "5V0_A", "VDD_CORE_V")
        rail_match = re.match(r"([A-Z0-9_]+)\s*", line)
        if not rail_match:
            continue
        rail_full = rail_match.group(1)
        # Strip trailing _A or _V to get base name
        rail = rail_full[:-2] if rail_full.endswith(("_A", "_V")) else rail_full
        is_current = rail_full.endswith("_A") or "current" in line.lower()
        is_voltage = rail_full.endswith("_V") or "volt" in line.lower()
        value = _parse_first_float(line)
        if value is None or value == 0:
            continue
        if rail not in rails:
            rails[rail] = (None, None)
        volt, curr = rails[rail]
        if is_current:
            rails[rail] = (volt, value)
        elif is_voltage:
            rails[rail] = (value, curr)

    # Compute total watts from voltage*current pairs
    watts = 0.0
    for rail, (volt, curr) in rails.items():
        if volt is not None and curr is not None and volt > 0 and curr > 0:
            watts += volt * curr

    # If no PMIC rails parsed successfully, return small nominal value
    if watts == 0.0 or watts > 50.0:
        return min(watts, 15.0) if watts > 0 else 3.5  # Clamp typical Pi 5 idle to ~3.5–15W

    return watts


def _finite_float(value: float, fallback: float = 0.0) -> float:
    """Convert numeric-like values to a finite float, with fallback on NaN/inf/errors."""
    try:
        number = float(value)
        return number if math.isfinite(number) else fallback
    except (TypeError, ValueError):
        return fallback


def _fetch_json(url: str, timeout: float = 8.0) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "NOVA/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def _fetch_json_post(url: str, payload: str, timeout: float = 8.0, headers: dict[str, str] | None = None) -> dict:
    req_headers = {"User-Agent": "NOVA/1.0", "Content-Type": "text/xml"}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(
        url,
        data=payload.encode("utf-8"),
        headers=req_headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def _fetch_trafikverket_items(limit: int, region: str) -> tuple[list[dict], str | None]:
    api_key = (os.environ.get("TRAFIKVERKET_API_KEY") or "").strip()
    if not api_key:
        return [], "Trafikverket API key missing (set TRAFIKVERKET_API_KEY)"

    request_xml = f"""<REQUEST>
  <LOGIN authenticationkey=\"{api_key}\" />
  <QUERY objecttype=\"Situation\" schemaversion=\"1.5\" limit=\"{max(1, min(limit * 2, 50))}\">
    <FILTER>
      <EQ name=\"Deleted\" value=\"false\" />
    </FILTER>
    <INCLUDE>Id</INCLUDE>
    <INCLUDE>Header</INCLUDE>
    <INCLUDE>Description</INCLUDE>
    <INCLUDE>Deviation</INCLUDE>
    <INCLUDE>TrafficRestrictionType</INCLUDE>
    <INCLUDE>StartTime</INCLUDE>
    <INCLUDE>EndTime</INCLUDE>
    <INCLUDE>LocationDescriptor</INCLUDE>
    <INCLUDE>WebLink</INCLUDE>
  </QUERY>
</REQUEST>"""

    payload = _fetch_json_post("https://api.trafikinfo.trafikverket.se/v2/data.json", request_xml, timeout=10.0)

    response = payload.get("RESPONSE") if isinstance(payload, dict) else None
    results = response.get("RESULT") if isinstance(response, dict) else None
    situations: list[dict] = []
    if isinstance(results, list):
        for result in results:
            if not isinstance(result, dict):
                continue
            candidate = result.get("Situation")
            if isinstance(candidate, list):
                situations.extend([x for x in candidate if isinstance(x, dict)])

    items: list[dict] = []
    for entry in situations:
        title = (entry.get("Header") or entry.get("Description") or "Trafikinfo").strip()[:120]
        location = (entry.get("LocationDescriptor") or "").strip()
        if not _match_region_text(region, title, location):
            continue

        description = (entry.get("Deviation") or entry.get("Description") or "").strip()
        if description and description != title:
            title = f"{title} - {description[:80]}"

        published = entry.get("StartTime") or entry.get("EndTime") or ""
        items.append(
            {
                "source": "Trafikverket",
                "title": title,
                "url": entry.get("WebLink") or "https://www.trafikverket.se/trafikinformation/",
                "published": published,
                "location": location,
                "priority_rank": 50,
                "priority_label": "Traffic",
            }
        )
        if len(items) >= limit:
            break

    return items, None


def _alert_priority(source: str, title: str = "") -> tuple[int, str]:
    source_l = source.lower()
    title_l = title.lower()
    if "vma" in source_l:
        return 100, "Critical"
    if "polisen" in source_l:
        return 80, "Police"
    if "sos" in source_l:
        return 70, "Emergency"
    if "trafikverket" in source_l:
        return 50, "Traffic"
    if "krisinformation" in source_l:
        if any(word in title_l for word in ["varning", "störning", "brand", "explosion", "olycka", "farlig"]):
            return 90, "Alert"
        return 60, "Notice"
    return 20, "News"


def _normalize_alert_region(region: str) -> str:
    value = (region or "").strip().lower()
    if value in {"nacka", "stockholm", "sweden"}:
        return value
    return "nacka"


def _region_keywords(region: str) -> tuple[str, ...]:
    if region == "nacka":
        return (
            "nacka",
            "saltsjöbaden",
            "saltsjobaden",
            "fisksätra",
            "fisksatra",
            "orminge",
            "boo",
            "saltsjö-boo",
            "saltsjo-boo",
        )
    if region == "stockholm":
        return (
            "stockholm",
            "stockholms",
            "södertälje",
            "sodertalje",
            "solna",
            "sundbyberg",
            "huddinge",
            "botkyrka",
            "haninge",
            "täby",
            "taby",
            "nacka",
            "järfälla",
            "jarfalla",
        )
    return ()


def _match_region_text(region: str, *parts: str) -> bool:
    if region == "sweden":
        return True

    haystack = " ".join((part or "") for part in parts).lower()
    keywords = _region_keywords(region)
    return any(keyword in haystack for keyword in keywords)


def _polisen_location_name(entry: dict) -> str:
    location = entry.get("location")
    if isinstance(location, dict):
        return str(location.get("name") or "").strip()
    if isinstance(location, str):
        return location.strip()
    return ""


def _parse_published_datetime(value: str) -> datetime | None:
    text = (value or "").strip()
    if not text:
        return None

    # Handle common ISO variants from Swedish public APIs.
    iso_candidate = text.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(iso_candidate)
    except ValueError:
        pass

    for fmt in (
        "%Y-%m-%d %H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S",
        "%a, %d %b %Y %H:%M:%S %z",
    ):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue

    return None


def _is_within_last_days(value: str, days: int = 30) -> bool:
    parsed = _parse_published_datetime(value)
    if parsed is None:
        # Keep entries with unknown date rather than hiding useful alerts.
        return True

    now = datetime.now(parsed.tzinfo) if parsed.tzinfo else datetime.now()
    return parsed >= (now - timedelta(days=days))


def _published_sort_value(value: str) -> float:
    parsed = _parse_published_datetime(value)
    if parsed is None:
        return float("-inf")
    try:
        return parsed.timestamp()
    except (OverflowError, OSError, ValueError):
        return float("-inf")


def _balance_items_by_source(items: list[dict]) -> list[dict]:
    """Interleave sources so one feed does not dominate the Sweden list."""
    if not items:
        return items

    preferred_order = [
        "Krisinformation VMA",
        "SOS Alarm",
        "Polisen",
        "Krisinformation",
        "Trafikverket",
    ]

    buckets: dict[str, list[dict]] = {}
    for item in items:
        source = str(item.get("source") or "Unknown")
        buckets.setdefault(source, []).append(item)

    ordered_sources = [source for source in preferred_order if source in buckets]
    ordered_sources.extend(source for source in buckets.keys() if source not in ordered_sources)

    balanced: list[dict] = []
    while True:
        added = False
        for source in ordered_sources:
            bucket = buckets.get(source) or []
            if not bucket:
                continue
            balanced.append(bucket.pop(0))
            added = True
        if not added:
            break

    return balanced


def _extract_sos_statistics(payload: object) -> dict[str, str]:
    if not isinstance(payload, dict):
        return {}

    def _canonicalize_stats(source: dict) -> dict[str, str]:
        aliases: dict[str, tuple[str, ...]] = {
            "Alla samtal": ("alla samtal",),
            "Polisen": ("polisen",),
            "Vårdbehov": ("vårdbehov", "vÃ¥rdbehov", "vardbehov"),
            "Räddning": ("räddning", "rÃ¤ddning", "raddning"),
            "Ej akuta behov": ("ej akuta behov",),
        }

        normalized: dict[str, str] = {
            str(k).strip().lower(): str(v)
            for k, v in source.items()
            if k is not None and v is not None
        }

        result: dict[str, str] = {}
        for canonical, keys in aliases.items():
            for key in keys:
                if key in normalized:
                    result[canonical] = normalized[key]
                    break
        return result

    for key in ["statistics", "statistik", "stats", "summary"]:
        candidate = payload.get(key)
        if isinstance(candidate, dict):
            canonical = _canonicalize_stats(candidate)
            if canonical:
                return canonical

    # Fallback: if the statistics are flattened on top-level keys.
    return _canonicalize_stats(payload)


@app.get("/integrations/weather")
async def weather_open_meteo(latitude: float = 59.3293, longitude: float = 18.0686, timezone: str = "auto"):
    """Weather for dashboard cards via Open-Meteo (current + hourly + 7-day forecast)."""
    params = urllib.parse.urlencode(
        {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m,relative_humidity_2m,uv_index",
            "hourly": "temperature_2m,weather_code,precipitation_probability",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_speed_10m_max,uv_index_max",
            "forecast_days": 7,
            "forecast_hours": 24,
            "timezone": timezone,
        }
    )
    url = f"https://api.open-meteo.com/v1/forecast?{params}"
    try:
        data = _fetch_json(url)
        return {
            "provider": "open-meteo",
            "latitude": latitude,
            "longitude": longitude,
            "current": data.get("current", {}),
            "hourly": data.get("hourly", {}),
            "daily": data.get("daily", {}),
        }
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        logger.warning("Weather fetch failed: %s", exc)
        return {"provider": "open-meteo", "error": str(exc), "current": {}, "hourly": {}, "daily": {}}


@app.get("/integrations/swedish-alerts")
async def swedish_alerts(limit: int = 12, region: str = "nacka"):
    """Aggregate Sweden-focused alerts/news from official APIs."""
    return fetch_swedish_alerts(limit=limit, region=region)


def _send_magic_packet(mac: str, broadcast_ip: str, port: int = 9) -> None:
    cleaned_mac = mac.replace(":", "").replace("-", "").strip()
    if len(cleaned_mac) != 12:
        raise ValueError("MAC address must be 12 hex characters")
    mac_bytes = struct.pack("!6B", *[int(cleaned_mac[i : i + 2], 16) for i in range(0, 12, 2)])
    payload = b"\xff" * 6 + mac_bytes * 16
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(payload, (broadcast_ip, port))


@app.post("/actions/wake-pc")
async def wake_pc():
    """Wake PC-Oscar over LAN using a magic packet broadcast."""
    target_mac = "1C:69:7A:9E:54:06"
    broadcast_ip = "192.168.1.255"
    try:
        _send_magic_packet(target_mac, broadcast_ip)
        logger.info("Start PC action sent to %s via %s", target_mac, broadcast_ip)
        return {"status": "sent", "target": "Start PC", "mac": target_mac, "broadcast": broadcast_ip}
    except Exception as exc:
        logger.exception("Start PC / Wake-on-LAN failed")
        return {"status": "error", "target": "Start PC", "error": str(exc)}


@app.post("/shutdown")
async def shutdown():
    import threading
    import time
    def delayed_exit():
        time.sleep(1)
        os._exit(0)
    threading.Thread(target=delayed_exit, daemon=True).start()
    return {"status": "shutting down..."}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
