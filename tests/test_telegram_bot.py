"""Tests for Telegram alert command handling and alert dispatch."""


def test_telegram_command_subscribe_and_test(tmp_path):
    from telegram_bot import TelegramAlertBot

    sent_messages = []

    def fake_sender(chat_id, text):
        sent_messages.append((chat_id, text))
        return True

    bot = TelegramAlertBot(
        token="token",
        subscriptions_file=str(tmp_path / "subs.json"),
        alert_fetcher=lambda limit, region: {"items": []},
        send_message_fn=fake_sender,
        poll_interval_seconds=15,
        request_timeout_seconds=3,
    )

    assert bot.process_message(42, "/Nacka") == "Subscribed to Nacka alerts."
    assert bot.process_message(42, "/test") == "NOVA Telegram bot test OK."
    assert sent_messages[0] == (42, "Subscribed to Nacka alerts.")
    assert sent_messages[1] == (42, "NOVA Telegram bot test OK.")


def test_telegram_dispatch_deduplicates_alerts(tmp_path):
    from telegram_bot import TelegramAlertBot

    sent_messages = []

    def fake_sender(chat_id, text):
        sent_messages.append((chat_id, text))
        return True

    def fake_alert_fetcher(limit, region):
        return {
            "items": [
                {
                    "id": f"{region}:alert-1",
                    "title": "Road closure",
                    "description": "Detour in place",
                    "priority": "Traffic",
                    "type": "Trafikverket",
                    "timestamp": "2026-04-27T10:00:00Z",
                    "location": "Nacka",
                    "url": "https://example.invalid/alert",
                }
            ]
        }

    bot = TelegramAlertBot(
        token="token",
        subscriptions_file=str(tmp_path / "subs.json"),
        alert_fetcher=fake_alert_fetcher,
        send_message_fn=fake_sender,
        poll_interval_seconds=15,
        request_timeout_seconds=3,
    )

    bot.subscribe(42, "nacka")
    bot._poll_alerts_once()
    bot._poll_alerts_once()

    alert_messages = [message for message in sent_messages if message[1].startswith("Traffic: Road closure")]
    assert len(alert_messages) == 1