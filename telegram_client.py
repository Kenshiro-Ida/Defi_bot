"""Minimal Telegram Bot API client for sending a photo with a caption."""
import os
import requests

TELEGRAM_API = "https://api.telegram.org"


class TelegramError(Exception):
    pass


def send_photo(image_bytes, caption=None, bot_token=None, chat_id=None, filename="deposit.png"):
    """Send a photo to a Telegram chat/channel.

    bot_token: the BotFather token. Falls back to TELEGRAM_BOT_TOKEN env var.
    chat_id:   numeric id or @channelusername. Falls back to TELEGRAM_CHAT_ID env var.
    """
    bot_token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")

    if not bot_token:
        raise TelegramError("Missing bot token (set TELEGRAM_BOT_TOKEN).")
    if not chat_id:
        raise TelegramError("Missing chat id (set TELEGRAM_CHAT_ID, e.g. @aidefiofficially).")

    url = f"{TELEGRAM_API}/bot{bot_token}/sendPhoto"
    data = {"chat_id": chat_id}
    if caption:
        data["caption"] = caption
        data["parse_mode"] = "HTML"

    files = {"photo": (filename, image_bytes, "image/png")}

    resp = requests.post(url, data=data, files=files, timeout=30)
    try:
        payload = resp.json()
    except ValueError:
        raise TelegramError(f"Telegram returned non-JSON response ({resp.status_code}): {resp.text[:200]}")

    if not payload.get("ok"):
        raise TelegramError(f"Telegram API error: {payload.get('description', payload)}")

    return payload
