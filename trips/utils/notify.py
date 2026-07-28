"""Telegram alerts for failed scheduled django-q2 tasks (issue #408).

The target chat is a single Telegram group shared by several Coolify projects,
so every message is prefixed with a project label to stay legible. The feature
is a no-op when the bot token or chat id are unset, leaving dev/test untouched.
"""

import logging

import httpx
from django.conf import settings

logger = logging.getLogger("task")

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"


def send_telegram_message(text: str) -> bool:
    """Post ``text`` to the configured Telegram chat.

    Returns True when a message was sent. No-op (logs only) when
    ``TELEGRAM_BOT_TOKEN`` or ``TELEGRAM_CHAT_ID`` are empty.
    """
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID
    if not token or not chat_id:
        logger.info("Telegram notifier disabled (no token/chat id); message: %s", text)
        return False
    try:
        response = httpx.post(
            TELEGRAM_API_URL.format(token=token),
            json={"chat_id": chat_id, "text": text},
            timeout=5,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.error("Telegram notification failed: %s", exc)
        return False
    return True


def notify_task_failure(task) -> None:
    """django-q2 schedule hook: alert on Telegram when a task fails.

    ``task`` is the completed django-q2 ``Task``; nothing is sent for a
    successful run. The message carries the task function and its error.
    """
    if getattr(task, "success", True):
        return
    label = settings.TELEGRAM_PROJECT_LABEL
    name = getattr(task, "func", None) or getattr(task, "name", "unknown task")
    send_telegram_message(f"[{label}] {name} FAILED: {task.result}")
