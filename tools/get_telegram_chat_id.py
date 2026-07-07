from __future__ import annotations

import getpass
import os

import requests


def main() -> int:
    token = os.getenv("TELEGRAM_BOT_TOKEN") or getpass.getpass("Telegram bot token: ")
    try:
        response = requests.get(
            f"https://api.telegram.org/bot{token}/getUpdates",
            timeout=30,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"Could not reach Telegram: {str(exc).replace(token, '[REDACTED]')}")
        return 1
    payload = response.json()
    updates = payload.get("result", [])
    if not updates:
        print("No updates yet. Send /start to the bot in Telegram, then run this again.")
        return 1
    for update in updates:
        message = update.get("message") or update.get("channel_post") or {}
        chat = message.get("chat") or {}
        if chat.get("id"):
            print(f"chat_id: {chat['id']}")
            if chat.get("username"):
                print(f"username: @{chat['username']}")
            if chat.get("title"):
                print(f"title: {chat['title']}")
            return 0
    print("Updates were returned, but no chat ID was found.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
