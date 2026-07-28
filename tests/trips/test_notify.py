"""Tests for the Telegram failure notifier (issue #408)."""

import types

from trips.utils.notify import notify_task_failure, send_telegram_message


class TestSendTelegramMessage:
    def test_no_op_when_unconfigured(self, settings):
        settings.TELEGRAM_BOT_TOKEN = ""  # nosec B105
        settings.TELEGRAM_CHAT_ID = ""

        assert send_telegram_message("hi") is False

    def test_sends_when_configured(self, settings, httpx_mock):
        settings.TELEGRAM_BOT_TOKEN = "tok"  # nosec B105
        settings.TELEGRAM_CHAT_ID = "42"
        httpx_mock.add_response(json={"ok": True})

        assert send_telegram_message("hello") is True
        request = httpx_mock.get_requests()[0]
        assert "bottok/sendMessage" in str(request.url)
        assert b"hello" in request.content
        assert b"42" in request.content

    def test_returns_false_on_http_error(self, settings, httpx_mock):
        settings.TELEGRAM_BOT_TOKEN = "tok"  # nosec B105
        settings.TELEGRAM_CHAT_ID = "42"
        httpx_mock.add_response(status_code=500)

        assert send_telegram_message("boom") is False


class TestNotifyTaskFailure:
    def test_failed_task_sends_alert(self, settings, httpx_mock):
        settings.TELEGRAM_BOT_TOKEN = "tok"  # nosec B105
        settings.TELEGRAM_CHAT_ID = "42"
        settings.TELEGRAM_PROJECT_LABEL = "organizeit"
        httpx_mock.add_response(json={"ok": True})
        task = types.SimpleNamespace(
            success=False,
            func="trips.tasks.backup_database",
            name="abc",
            result="disk full",
        )

        notify_task_failure(task)

        request = httpx_mock.get_requests()[0]
        assert b"organizeit" in request.content
        assert b"backup_database" in request.content
        assert b"disk full" in request.content

    def test_successful_task_sends_nothing(self, settings, httpx_mock):
        settings.TELEGRAM_BOT_TOKEN = "tok"  # nosec B105
        settings.TELEGRAM_CHAT_ID = "42"
        task = types.SimpleNamespace(
            success=True,
            func="trips.tasks.backup_database",
            name="abc",
            result="ok",
        )

        notify_task_failure(task)

        assert httpx_mock.get_requests() == []
