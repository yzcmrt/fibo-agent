from __future__ import annotations

import json
import os
import urllib.request


def send_signal(text: str) -> bool:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat = os.getenv("TELEGRAM_CHAT_ID")
    webhook = os.getenv("DISCORD_WEBHOOK_URL")
    sent = False
    if token and chat:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        body = json.dumps({"chat_id": chat, "text": text[:3500]}).encode()
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=15)
            sent = True
        except Exception:
            sent = False
    if webhook:
        body = json.dumps({"content": text[:1800]}).encode()
        req = urllib.request.Request(webhook, data=body, headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=15)
            sent = True
        except Exception:
            sent = False
    return sent
