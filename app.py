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
import xml.etree.ElementTree as ET
from asyncio import sleep
from datetime import datetime

import psutil
import uvicorn

from config import PORT, setup_logging


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

app = FastAPI(title="NOVA Unified Backend")

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


def _fetch_rss_items(url: str, source: str, limit: int = 8) -> list[dict]:
    req = urllib.request.Request(url, headers={"User-Agent": "NOVA/1.0"})
    with urllib.request.urlopen(req, timeout=8.0) as resp:
        xml_text = resp.read().decode("utf-8", errors="replace")
    root = ET.fromstring(xml_text)
    items: list[dict] = []
    for item in root.findall(".//item")[:limit]:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip()
        if not title:
            continue
        items.append({"source": source, "title": title, "url": link, "published": pub_date})
    return items


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
async def swedish_alerts(limit: int = 12):
    """Aggregate Sweden-focused alerts/news from official APIs."""
    items: list[dict] = []
    errors: list[str] = []

    # 1) Polisen events API (JSON) - https://polisen.se/om-polisen/om-webbplatsen/oppna-data/api-over-polisens-handelser/
    try:
        polisen_data = _fetch_json("https://polisen.se/api/events")
        for entry in (polisen_data or [])[:limit]:
            items.append(
                {
                    "source": "Polisen",
                    "title": (entry.get("name") or "Polisen event").strip(),
                    "url": entry.get("url") or "https://polisen.se/aktuellt/",
                    "published": entry.get("datetime") or "",
                    "location": entry.get("location", {}).get("name") or "",
                }
            )
        logger.debug("Polisen: fetched %d items", len(polisen_data or []))
    except Exception as exc:
        error_msg = str(exc)[:40]
        logger.warning("Polisen API failed: %s", error_msg)
        errors.append(f"Polisen: {error_msg}")

    # 2) Krisinformation API - https://api.krisinformation.se/
    try:
        krisis_data = _fetch_json("https://api.krisinformation.se/v4/events?severity=WARNING,ALERT")
        for entry in (krisis_data.get("events") or [])[:limit]:
            items.append(
                {
                    "source": "Krisinformation",
                    "title": (entry.get("headline") or entry.get("title") or "Alert").strip()[:80],
                    "url": "https://krisinformation.se/",
                    "published": entry.get("updated") or entry.get("created") or "",
                }
            )
        logger.debug("Krisinformation: fetched %d items", len(krisis_data.get("events") or []))
    except Exception as exc:
        error_msg = str(exc)[:40]
        logger.warning("Krisinformation API failed: %s", error_msg)
        errors.append(f"Krisinformation: {error_msg}")

    # 3) SOS Alarm API via henrikhjelm.se proxy - https://henrikhjelm.se/api/sos/
    try:
        sos_data = _fetch_json("https://henrikhjelm.se/api/sos/")
        if isinstance(sos_data, list):
            for entry in sos_data[:limit]:
                items.append(
                    {
                        "source": "SOS Alarm",
                        "title": (entry.get("headline") or entry.get("title") or "SOS Event").strip()[:80],
                        "url": "https://www.sosalarm.se/",
                        "published": entry.get("timestamp") or entry.get("updated") or "",
                    }
                )
        logger.debug("SOS Alarm: fetched %d items", len(sos_data) if isinstance(sos_data, list) else 0)
    except Exception as exc:
        error_msg = str(exc)[:40]
        logger.warning("SOS Alarm API failed: %s", error_msg)
        errors.append(f"SOS Alarm: {error_msg}")

    # 4) RSS fallback so UI still shows items even if JSON APIs fail
    if not items:
        fallback_feeds = [
            ("https://www.svt.se/nyheter/rss.xml", "SVT Nyheter"),
            ("https://feeds.expressen.se/nyheter", "Expressen"),
            ("https://www.svd.se/?service=rss", "Svenska Dagbladet"),
        ]
        for feed_url, source in fallback_feeds:
            try:
                feed_items = _fetch_rss_items(feed_url, source, limit=limit)
                items.extend(feed_items)
                if len(items) >= limit:
                    break
            except Exception as exc:
                error_msg = str(exc)[:40]
                logger.warning("%s RSS failed: %s", source, error_msg)
                errors.append(f"{source}: {error_msg}")

    # Deduplicate by title and source, keep first seen entries
    deduped: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for item in items:
        key = ((item.get("source") or "").strip(), (item.get("title") or "").strip())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
        if len(deduped) >= limit:
            break

    # Return results with error log
    result = {
        "items": deduped,
        "count": len(deduped),
        "errors": errors if errors else [],
        "sources": ["Polisen", "Krisinformation", "SOS Alarm"],
    }
    
    if not deduped:
        logger.warning("No Swedish alerts fetched. Errors: %s", errors)
    
    return result


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
        return {"status": "sent", "target": "PC-Oscar", "mac": target_mac, "broadcast": broadcast_ip}
    except Exception as exc:
        logger.warning("Wake-on-LAN failed: %s", exc)
        return {"status": "error", "target": "PC-Oscar", "error": str(exc)}


@app.on_event("startup")
async def startup_event():
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
    logger.info("NOVA backend ready.")

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
