"""Localised message templates for trade events.

We render once and dispatch the same body to all channels. Each language
returns dicts of {title, body, body_long} so simple Web Push toasts can
use `body` while Telegram / email use `body_long`.
"""

from __future__ import annotations

from app.api.ws.manager import WebSocketManager  # noqa: F401  (kept for type discoverability)


def _arrow(direction: str) -> str:
    return "▲" if direction == "long" else "▼"


def _ru(event: dict) -> dict[str, str]:
    t = event.get("type")
    sym = event.get("symbol", "")
    direction = event.get("direction", "")
    price = event.get("price")
    pnl = event.get("pnl")
    level = event.get("level")
    lots = event.get("lots")

    if t == "open":
        side_word = "Покупка" if direction == "long" else "Продажа"
        return {
            "title": f"Hermes · {sym}",
            "body": f"{_arrow(direction)} {side_word} L{level} · {lots} лот @ {price:.5f}",
            "body_long": (
                f"<b>Hermes</b> открыл сделку\n"
                f"{sym} · {side_word} (уровень {level})\n"
                f"Объём: {lots} лот · Цена: {price:.5f}"
            ),
        }
    if t == "close_basket":
        sign = "+" if (pnl or 0) >= 0 else ""
        return {
            "title": f"Hermes · {sym} закрыто",
            "body": f"{event.get('reason','')} · {sign}{pnl:.2f}",
            "body_long": (
                f"<b>Hermes</b> закрыл корзину\n"
                f"{sym} · причина: {event.get('reason','')}\n"
                f"Результат: <b>{sign}{pnl:.2f}</b>"
            ),
        }
    if t == "kill_switch":
        n = event.get("closed_count", 0)
        return {
            "title": "Hermes · Аварийная остановка",
            "body": f"Закрыто позиций: {n}",
            "body_long": f"⚠️ <b>Hermes</b> выполнил аварийную остановку.\nЗакрыто позиций: {n}",
        }
    if t == "error":
        return {
            "title": "Hermes · Ошибка",
            "body": (event.get("message") or "Неизвестная ошибка")[:120],
            "body_long": f"❌ <b>Hermes</b> сообщил об ошибке:\n<code>{event.get('message','')}</code>",
        }
    return {"title": f"Hermes · {t}", "body": str(event), "body_long": str(event)}


def render(event: dict, locale: str = "ru") -> dict[str, str]:
    return _ru(event)  # KZ/EN added in Phase 6
