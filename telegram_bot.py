"""Telegram bot worker for NOVA alert subscriptions."""
from __future__ import annotations

import json
import logging
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable

from news_alerts import fetch_swedish_alerts, normalize_alert_region

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
TELEGRAM_SUBSCRIPTIONS_FILE = (os.getenv("TELEGRAM_SUBSCRIPTIONS_FILE") or "telegram_subscriptions.json").strip()
TELEGRAM_POLL_INTERVAL_SECONDS = max(15, int(os.getenv("TELEGRAM_POLL_INTERVAL_SECONDS", "60")))
TELEGRAM_REQUEST_TIMEOUT_SECONDS = max(3, int(os.getenv("TELEGRAM_REQUEST_TIMEOUT_SECONDS", "10")))
TELEGRAM_MAX_RETRIES = max(1, int(os.getenv("TELEGRAM_MAX_RETRIES", "3")))

_HELP_TEXT = (
    "Send /Nacka to subscribe to Nacka alerts. "
    "Send /stockholm to subscribe to Stockholm alerts. "
    "Send /test to verify the bot reply."
)

_STARTUP_TEXT = "NOVA started successfully and is now monitoring alerts."


def _coerce_chat_id(value: object) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_command(text: str) -> str:
    first_token = (text or "").strip().split()[0] if (text or "").strip() else ""
    if not first_token.startswith("/"):
        return ""
    command = first_token[1:].split("@", 1)[0].strip().lower()
    if command in {"start", "help", "nacka", "stockholm", "test"}:
        return command
    return ""


def _format_alert_message(alert: dict) -> str:
    title = str(alert.get("title") or "Untitled alert").strip()
    priority = str(alert.get("priority") or alert.get("priority_label") or "News").strip()
    alert_type = str(alert.get("type") or alert.get("source") or "Alert").strip()
    description = str(alert.get("description") or "").strip()
    timestamp = str(alert.get("timestamp") or alert.get("published") or "").strip()
    location = str(alert.get("location") or "").strip()
    url = str(alert.get("url") or "").strip()

    lines = [f"{priority}: {title}"]
    if alert_type:
        lines.append(f"Type: {alert_type}")
    if description and description != title:
        lines.append(f"Details: {description}")
    if location and location != description:
        lines.append(f"Location: {location}")
    if timestamp:
        lines.append(f"Time: {timestamp}")
    if url:
        lines.append(f"Link: {url}")
    return "\n".join(lines)


class TelegramAlertBot:
    def __init__(
        self,
        token: str,
        subscriptions_file: str,
        *,
        poll_interval_seconds: int = TELEGRAM_POLL_INTERVAL_SECONDS,
        request_timeout_seconds: int = TELEGRAM_REQUEST_TIMEOUT_SECONDS,
        max_retries: int = TELEGRAM_MAX_RETRIES,
        alert_fetcher: Callable[[int, str], dict] = fetch_swedish_alerts,
        send_message_fn: Callable[[int, str], bool] | None = None,
    ) -> None:
        self.token = token
        self.subscriptions_file = subscriptions_file
        self.poll_interval_seconds = max(10, int(poll_interval_seconds))
        self.request_timeout_seconds = max(3, int(request_timeout_seconds))
        self.max_retries = max(1, int(max_retries))
        self.alert_fetcher = alert_fetcher
        self._send_message_fn = send_message_fn or self._send_message_via_api
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._state_lock = threading.Lock()
        self._subscriptions = self._load_subscriptions()
        self._seen_alert_ids: set[str] = set()
        self._update_offset: int | None = None

    @property
    def enabled(self) -> bool:
        return bool(self.token)

    def start(self) -> bool:
        if not self.enabled:
            logger.info("Telegram bot disabled: TELEGRAM_BOT_TOKEN is not set.")
            return False
        if self._thread and self._thread.is_alive():
            return True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="telegram-alert-bot", daemon=True)
        self._thread.start()
        logger.info("Telegram bot worker started.")
        return True

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        self._thread = None

    def subscribe(self, chat_id: int, region: str) -> bool:
        normalized_region = normalize_alert_region(region)
        with self._state_lock:
            chat_ids = self._subscriptions.setdefault(normalized_region, set())
            before = len(chat_ids)
            chat_ids.add(chat_id)
            changed = len(chat_ids) != before
            if changed:
                self._save_subscriptions()
        return changed

    def process_message(self, chat_id: int, text: str) -> str | None:
        command = _normalize_command(text)
        if not command:
            return None
        if command == "nacka":
            was_new = self.subscribe(chat_id, "nacka")
            reply = "Subscribed to Nacka alerts."
            if not was_new:
                reply = "Nacka alerts are already enabled."
            self._send_message(chat_id, reply)
            return reply
        if command == "stockholm":
            was_new = self.subscribe(chat_id, "stockholm")
            reply = "Subscribed to Stockholm alerts."
            if not was_new:
                reply = "Stockholm alerts are already enabled."
            self._send_message(chat_id, reply)
            return reply
        if command == "test":
            reply = "NOVA Telegram bot test OK."
            self._send_message(chat_id, reply)
            return reply
        if command in {"start", "help"}:
            self._send_message(chat_id, _HELP_TEXT)
            return _HELP_TEXT
        return None

    def poll_once(self) -> None:
        self._poll_updates_once()
        self._poll_alerts_once()

    def send_startup_notification(self) -> int:
        with self._state_lock:
            chat_ids = sorted({chat_id for ids in self._subscriptions.values() for chat_id in ids})

        sent_count = 0
        for chat_id in chat_ids:
            if self._send_message(chat_id, _STARTUP_TEXT):
                sent_count += 1

        if sent_count:
            logger.info("Telegram startup notification sent to %d chat(s).", sent_count)
        else:
            logger.debug("No Telegram startup notification sent; no subscribed chats yet.")

        return sent_count

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.poll_once()
            except Exception as exc:
                logger.warning("Telegram bot poll failed: %s", exc)
            self._stop_event.wait(self.poll_interval_seconds)

    def _poll_updates_once(self) -> None:
        updates = self._fetch_updates()
        if not updates:
            return

        for update in updates:
            update_id = update.get("update_id")
            if isinstance(update_id, int):
                self._update_offset = update_id + 1

            message = update.get("message")
            if not isinstance(message, dict):
                continue
            chat = message.get("chat")
            chat_id = _coerce_chat_id(chat.get("id") if isinstance(chat, dict) else None)
            if chat_id is None:
                continue
            text = message.get("text")
            if isinstance(text, str):
                self.process_message(chat_id, text)

    def _poll_alerts_once(self) -> None:
        with self._state_lock:
            subscriptions = {region: set(chat_ids) for region, chat_ids in self._subscriptions.items() if chat_ids}

        if not subscriptions:
            return

        for region, chat_ids in subscriptions.items():
            try:
                alerts_payload = self.alert_fetcher(60 if region != "sweden" else 180, region)
            except Exception as exc:
                logger.warning("Alert fetch failed for %s: %s", region, exc)
                continue

            alerts = alerts_payload.get("items") if isinstance(alerts_payload, dict) else []
            if not isinstance(alerts, list):
                continue

            new_alerts = self._filter_new_alerts(region, alerts)
            if not new_alerts:
                continue

            for alert in new_alerts:
                message = _format_alert_message(alert)
                for chat_id in chat_ids:
                    self._send_message(chat_id, message)

    def _filter_new_alerts(self, region: str, alerts: list[dict]) -> list[dict]:
        new_alerts: list[dict] = []
        seen = self._seen_alert_ids
        for alert in alerts:
            if not isinstance(alert, dict):
                continue
            alert_id = str(alert.get("id") or "").strip()
            if not alert_id:
                continue
            if alert_id in seen:
                continue
            seen.add(alert_id)
            new_alerts.append(alert)
        return new_alerts

    def _fetch_updates(self) -> list[dict]:
        if not self.token:
            return []

        params = {
            "timeout": 1,
            "allowed_updates": json.dumps(["message"]),
        }
        if self._update_offset is not None:
            params["offset"] = self._update_offset
        url = f"{self._api_base()}/getUpdates?{urllib.parse.urlencode(params)}"
        try:
            with urllib.request.urlopen(url, timeout=self.request_timeout_seconds) as resp:
                payload = json.loads(resp.read().decode("utf-8", errors="replace"))
        except urllib.error.URLError as exc:
            logger.debug("Telegram update poll failed: %s", exc)
            return []

        if not isinstance(payload, dict) or not payload.get("ok"):
            return []
        result = payload.get("result")
        return result if isinstance(result, list) else []

    def _send_message(self, chat_id: int, text: str) -> bool:
        try:
            return bool(self._send_message_fn(chat_id, text))
        except Exception as exc:
            logger.warning("Telegram send helper failed for chat %s: %s", chat_id, exc)
            return False

    def _send_message_via_api(self, chat_id: int, text: str) -> bool:
        if not self.token:
            return False

        payload = urllib.parse.urlencode(
            {
                "chat_id": str(chat_id),
                "text": text,
                "disable_web_page_preview": "true",
            }
        ).encode("utf-8")
        url = f"{self._api_base()}/sendMessage"
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                request = urllib.request.Request(
                    url,
                    data=payload,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=self.request_timeout_seconds) as resp:
                    response_payload = json.loads(resp.read().decode("utf-8", errors="replace"))
                if isinstance(response_payload, dict) and response_payload.get("ok"):
                    return True
                last_error = RuntimeError(str(response_payload))
            except Exception as exc:
                last_error = exc

            if attempt < self.max_retries:
                time.sleep(min(2 ** (attempt - 1), 5))

        logger.warning("Telegram sendMessage failed for chat %s after %s attempts: %s", chat_id, self.max_retries, last_error)
        return False

    def _api_base(self) -> str:
        return f"https://api.telegram.org/bot{self.token}"

    def _load_subscriptions(self) -> dict[str, set[int]]:
        path = Path(self.subscriptions_file)
        if not path.exists():
            return {"nacka": set(), "stockholm": set()}

        try:
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Telegram subscription load failed: %s", exc)
            return {"nacka": set(), "stockholm": set()}

        result: dict[str, set[int]] = {"nacka": set(), "stockholm": set()}
        if isinstance(payload, dict):
            for region, chat_ids in payload.items():
                normalized_region = normalize_alert_region(region)
                if not isinstance(chat_ids, list):
                    continue
                for chat_id in chat_ids:
                    coerced = _coerce_chat_id(chat_id)
                    if coerced is not None:
                        result.setdefault(normalized_region, set()).add(coerced)
        return result

    def _save_subscriptions(self) -> None:
        path = Path(self.subscriptions_file)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = path.with_suffix(path.suffix + ".tmp")
            payload = {region: sorted(chat_ids) for region, chat_ids in self._subscriptions.items() if chat_ids}
            with temp_path.open("w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, sort_keys=True)
            os.replace(temp_path, path)
        except OSError as exc:
            logger.warning("Telegram subscription save failed: %s", exc)


_telegram_bot: TelegramAlertBot | None = None


def get_telegram_bot() -> TelegramAlertBot:
    global _telegram_bot
    if _telegram_bot is None:
        _telegram_bot = TelegramAlertBot(
            token=TELEGRAM_BOT_TOKEN,
            subscriptions_file=TELEGRAM_SUBSCRIPTIONS_FILE,
        )
    return _telegram_bot


def start_telegram_bot() -> TelegramAlertBot | None:
    bot = get_telegram_bot()
    if bot.enabled:
        bot.start()
        return bot
    return None


def stop_telegram_bot() -> None:
    if _telegram_bot is not None:
        _telegram_bot.stop()
