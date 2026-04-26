"""Telegram bot client — async, replaces legacy/telegram_bot.py.

We avoid the heavy `python-telegram-bot` polling stack and use plain HTTP
because all we ever do is sendMessage with HTML formatting.
"""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)


class TelegramClient:
    def __init__(self, token: str, chat_id: str) -> None:
        self._token = token
        self._chat_id = chat_id
        self._url = f"https://api.telegram.org/bot{token}"

    async def send(self, text: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.post(
                    f"{self._url}/sendMessage",
                    json={
                        "chat_id": self._chat_id,
                        "text": text,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": True,
                    },
                )
                r.raise_for_status()
                return True
        except Exception as e:  # noqa: BLE001
            logger.warning("Telegram send failed: %s", e)
            return False

    async def test(self) -> bool:
        return await self.send("✅ Hermes подключился к Telegram. Уведомления работают.")
