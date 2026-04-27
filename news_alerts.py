"""Shared Swedish alert fetcher and normalizer for the backend and Telegram bot."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def fetch_json(url: str, timeout: float = 8.0) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "NOVA/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def fetch_json_post(url: str, payload: str, timeout: float = 8.0, headers: dict[str, str] | None = None) -> dict:
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


def normalize_alert_region(region: str) -> str:
    value = (region or "").strip().lower()
    if value in {"nacka", "stockholm", "sweden"}:
        return value
    return "nacka"


def alert_priority(source: str, title: str = "") -> tuple[int, str]:
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


def region_keywords(region: str) -> tuple[str, ...]:
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


def match_region_text(region: str, *parts: str) -> bool:
    if region == "sweden":
        return True

    haystack = " ".join((part or "") for part in parts).lower()
    keywords = region_keywords(region)
    return any(keyword in haystack for keyword in keywords)


def polisen_location_name(entry: dict) -> str:
    location = entry.get("location")
    if isinstance(location, dict):
        return str(location.get("name") or "").strip()
    if isinstance(location, str):
        return location.strip()
    return ""


def parse_published_datetime(value: str) -> datetime | None:
    text = (value or "").strip()
    if not text:
        return None

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


def is_within_last_days(value: str, days: int = 30) -> bool:
    parsed = parse_published_datetime(value)
    if parsed is None:
        return True

    now = datetime.now(parsed.tzinfo) if parsed.tzinfo else datetime.now()
    return parsed >= (now - timedelta(days=days))


def published_sort_value(value: str) -> float:
    parsed = parse_published_datetime(value)
    if parsed is None:
        return float("-inf")
    try:
        return parsed.timestamp()
    except (OverflowError, OSError, ValueError):
        return float("-inf")


def balance_items_by_source(items: list[dict]) -> list[dict]:
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


def extract_sos_statistics(payload: object) -> dict[str, str]:
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

    return _canonicalize_stats(payload)


def build_alert_id(item: dict, region: str | None = None) -> str:
    raw_id = str(item.get("id") or item.get("alert_id") or "").strip()
    if raw_id:
        return raw_id

    source = str(item.get("source") or item.get("type") or "alert").strip().lower()
    title = str(item.get("title") or "").strip().lower()
    description = str(item.get("description") or "").strip().lower()
    timestamp = str(item.get("timestamp") or item.get("published") or "").strip().lower()
    location = str(item.get("location") or "").strip().lower()
    url = str(item.get("url") or "").strip().lower()
    seed = "|".join([source, title, description, timestamp, location, url])
    digest = hashlib.sha1(seed.encode("utf-8", errors="ignore")).hexdigest()
    return f"{source or 'alert'}:{digest}"


def normalize_alert_item(item: dict, *, region: str, fallback_source: str = "Alert") -> dict:
    source = str(item.get("source") or fallback_source).strip() or fallback_source
    title = str(item.get("title") or item.get("Headline") or item.get("headline") or item.get("name") or "Untitled alert").strip()
    description = str(
        item.get("description")
        or item.get("summary")
        or item.get("Summary")
        or item.get("location")
        or item.get("LocationDescriptor")
        or item.get("Area")
        or item.get("area")
        or ""
    ).strip()
    location = str(item.get("location") or item.get("Area") or item.get("area") or "").strip()
    timestamp = str(item.get("timestamp") or item.get("published") or item.get("Published") or item.get("updated") or item.get("Updated") or "").strip()
    url = str(item.get("url") or item.get("Link") or item.get("link") or "").strip()
    try:
        priority_rank = int(item.get("priority_rank") or 0)
    except (TypeError, ValueError):
        priority_rank = 0
    priority_label = str(item.get("priority_label") or item.get("priority") or alert_priority(source, title)[1]).strip() or "News"

    normalized = {
        **item,
        "id": build_alert_id(item, region),
        "source": source,
        "title": title,
        "description": description,
        "priority": priority_label,
        "type": source,
        "timestamp": timestamp,
        "region": region,
        "location": location,
        "url": url,
        "published": timestamp,
        "priority_rank": priority_rank,
        "priority_label": priority_label,
    }
    return normalized


def fetch_trafikverket_items(limit: int, region: str) -> tuple[list[dict], str | None]:
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

    payload = fetch_json_post("https://api.trafikinfo.trafikverket.se/v2/data.json", request_xml, timeout=10.0)

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
        if not match_region_text(region, title, location):
            continue

        description = (entry.get("Deviation") or entry.get("Description") or "").strip()
        if description and description != title:
            title = f"{title} - {description[:80]}"

        published = entry.get("StartTime") or entry.get("EndTime") or ""
        items.append(
            {
                "source": "Trafikverket",
                "title": title,
                "description": description or location,
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


def fetch_swedish_alerts(limit: int = 12, region: str = "nacka") -> dict:
    selected_region = normalize_alert_region(region)
    try:
        limit_value = max(1, int(limit))
    except (TypeError, ValueError):
        limit_value = 12

    items: list[dict] = []
    source_errors: list[str] = []
    area_statistics: dict[str, str] = {}
    polisen_data_cache: list[dict] = []
    days_back = 30

    def _as_items(payload: object, keys: list[str]) -> list[dict]:
        if isinstance(payload, list):
            return [x for x in payload if isinstance(x, dict)]
        if isinstance(payload, dict):
            for key in keys:
                value = payload.get(key)
                if isinstance(value, list):
                    return [x for x in value if isinstance(x, dict)]
        return []

    try:
        polisen_data = fetch_json("https://polisen.se/api/events", timeout=5.0)
        polisen_data_cache = [entry for entry in (polisen_data or []) if isinstance(entry, dict)]
        for entry in polisen_data_cache:
            title = (entry.get("name") or "Polisen event").strip()
            summary = (entry.get("summary") or "").strip()
            location = polisen_location_name(entry)
            published = entry.get("datetime") or ""
            if not match_region_text(selected_region, title, location, summary):
                continue
            if not is_within_last_days(published, days=days_back):
                continue

            priority_rank, priority_label = alert_priority("Polisen", title)
            items.append(
                {
                    "source": "Polisen",
                    "title": title,
                    "description": summary or location,
                    "url": entry.get("url") or "https://polisen.se/aktuellt/",
                    "published": published,
                    "location": location,
                    "priority_rank": priority_rank,
                    "priority_label": priority_label,
                }
            )
        logger.debug("Polisen: fetched %d items", len(polisen_data or []))
    except Exception as exc:
        source_errors.append(f"Polisen: {str(exc)[:40]}")

    try:
        krisis_vmas = fetch_json("https://api.krisinformation.se/v3/vmas?language=sv", timeout=4.0)
        krisis_news = fetch_json(
            f"https://api.krisinformation.se/v3/news?language=sv&numberOfNewsArticles={max(limit_value, 10)}",
            timeout=4.0,
        )

        vma_items = _as_items(krisis_vmas, ["vmas", "items", "data"])
        news_items = _as_items(krisis_news, ["news", "items", "data"])
        scan_limit = max(limit_value * 20, 200)

        for entry in vma_items[:scan_limit]:
            title = (entry.get("Headline") or entry.get("headline") or entry.get("title") or "VMA").strip()[:100]
            location = entry.get("Area") or entry.get("area") or ""
            published = entry.get("Published") or entry.get("published") or entry.get("Updated") or ""
            if not match_region_text(selected_region, title, location):
                continue
            if not is_within_last_days(published, days=days_back):
                continue

            priority_rank, priority_label = alert_priority("Krisinformation VMA", title)
            items.append(
                {
                    "source": "Krisinformation VMA",
                    "title": title,
                    "description": location,
                    "url": entry.get("Link") or entry.get("link") or "https://krisinformation.se/",
                    "published": published,
                    "location": location,
                    "priority_rank": priority_rank,
                    "priority_label": priority_label,
                }
            )

        for entry in news_items[:scan_limit]:
            title = (entry.get("Headline") or entry.get("headline") or entry.get("Title") or entry.get("title") or "Alert").strip()[:100]
            location = entry.get("Area") or entry.get("area") or ""
            published = entry.get("Published") or entry.get("published") or entry.get("Updated") or entry.get("updated") or ""
            if not match_region_text(selected_region, title, location):
                continue
            if not is_within_last_days(published, days=days_back):
                continue

            priority_rank, priority_label = alert_priority("Krisinformation", title)
            items.append(
                {
                    "source": "Krisinformation",
                    "title": title,
                    "description": location,
                    "url": entry.get("Link") or entry.get("link") or "https://krisinformation.se/",
                    "published": published,
                    "location": location,
                    "priority_rank": priority_rank,
                    "priority_label": priority_label,
                }
            )
        logger.debug("Krisinformation: fetched %d VMAs and %d news items", len(vma_items), len(news_items))
    except Exception as exc:
        source_errors.append(f"Krisinformation: {str(exc)[:40]}")

    try:
        if selected_region == "nacka":
            sos_url = "https://www.henrikhjelm.se/api/sos/Nacka_kommun.json"
        else:
            sos_url = "https://henrikhjelm.se/api/sos/"

        sos_data = fetch_json(sos_url, timeout=4.0)
        if selected_region == "nacka":
            area_statistics = extract_sos_statistics(sos_data)

        sos_items = _as_items(sos_data, ["items", "data", "results"])
        scan_limit = max(limit_value * 20, 200)
        for entry in sos_items[:scan_limit]:
            title = (entry.get("headline") or entry.get("title") or "SOS Event").strip()[:100]
            location = entry.get("location") or ""
            published = entry.get("timestamp") or entry.get("updated") or entry.get("published") or ""
            if not match_region_text(selected_region, title, location):
                continue
            if not is_within_last_days(published, days=days_back):
                continue

            priority_rank, priority_label = alert_priority("SOS Alarm", title)
            items.append(
                {
                    "source": "SOS Alarm",
                    "title": title,
                    "description": location,
                    "url": entry.get("url") or "https://www.sosalarm.se/",
                    "published": published,
                    "location": location,
                    "priority_rank": priority_rank,
                    "priority_label": priority_label,
                }
            )
        logger.debug("SOS Alarm: fetched %d items", len(sos_items))
    except Exception as exc:
        source_errors.append(f"SOS Alarm: {str(exc)[:40]}")

    if selected_region != "nacka":
        try:
            trafik_items, trafik_error = fetch_trafikverket_items(limit=limit_value, region=selected_region)
            if trafik_items:
                for item in trafik_items:
                    if is_within_last_days(item.get("published") or "", days=days_back):
                        items.append(item)
            elif trafik_error:
                source_errors.append(f"Trafikverket: {trafik_error[:60]}")
        except Exception as exc:
            source_errors.append(f"Trafikverket: {str(exc)[:60]}")

    deduped: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for item in items:
        key = ((item.get("source") or "").strip(), (item.get("title") or "").strip())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    deduped.sort(
        key=lambda item: (
            -int(item.get("priority_rank") or 0),
            -published_sort_value(item.get("published") or ""),
            (item.get("title") or ""),
        )
    )

    if selected_region == "sweden":
        deduped = balance_items_by_source(deduped)

    if not deduped and selected_region == "stockholm" and polisen_data_cache:
        for entry in polisen_data_cache[: max(limit_value * 10, 120)]:
            title = (entry.get("name") or "Polisen event").strip()
            if not title:
                continue
            deduped.append(
                {
                    "source": "Polisen",
                    "title": title,
                    "description": entry.get("summary") or _safe_text(polisen_location_name(entry)),
                    "url": entry.get("url") or "https://polisen.se/aktuellt/",
                    "published": entry.get("datetime") or "",
                    "location": polisen_location_name(entry),
                    "priority_rank": alert_priority("Polisen", title)[0],
                    "priority_label": "Police",
                }
            )
            if len(deduped) >= limit_value:
                break

        if deduped:
            source_errors.append(f"{selected_region}: local filter empty; using broader Polisen fallback")

    deduped = deduped[:limit_value]
    normalized_items = [normalize_alert_item(item, region=selected_region) for item in deduped]

    result = {
        "items": normalized_items,
        "count": len(normalized_items),
        "region": selected_region,
        "statistics": area_statistics if selected_region == "nacka" else {},
        "errors": source_errors if source_errors else [],
        "sources": ["Polisen", "Krisinformation", "SOS Alarm", "Trafikverket"],
    }

    if not normalized_items:
        logger.warning("No Swedish alerts fetched. Errors: %s", source_errors)
    elif source_errors:
        logger.info("Swedish alerts fetched with partial source errors: %s", source_errors)

    return result


def _safe_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()
