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
    if t == "trade_opened":
        # Auto-entry from the ensemble (proven / autonomous mode). Carries
        # the mode, confidence, and the markdown reason from the signal.
        side_word = "Покупка" if direction == "long" else "Продажа"
        mode_word = {"proven": "Проверенный", "autonomous": "Автономный"}.get(
            event.get("mode", ""), event.get("mode", ""),
        )
        conf = event.get("confidence", 0)
        return {
            "title": f"Hermes · {sym} открыто",
            "body": f"{_arrow(direction)} {side_word} {sym} · режим {mode_word}",
            "body_long": (
                f"<b>Hermes</b> открыл сделку ({mode_word})\n"
                f"{sym} · {side_word} · уверенность {conf:.2f}\n\n"
                f"<i>{event.get('reason', '')[:500]}</i>"
            ),
        }
    if t == "broker_down":
        return {
            "title": "Hermes · Брокер недоступен",
            "body": "Бот приостановлен — проверьте MT5 терминал",
            "body_long": (
                f"⚠️ <b>Hermes</b> приостановлен: брокер не отвечает.\n"
                f"<code>{event.get('reason','')}</code>\n\n"
                f"Откройте терминал MT5 и убедитесь что вы вошли в аккаунт."
            ),
        }
    if t == "risk_block":
        return {
            "title": "Hermes · Сигнал отклонён",
            "body": f"Risk engine: {event.get('reason', '')[:80]}",
            "body_long": (
                f"🛡 <b>Hermes</b> не открыл сделку на {sym}\n\n"
                f"<i>{event.get('reason', '')}</i>"
            ),
        }
    return {"title": f"Hermes · {t}", "body": str(event), "body_long": str(event)}


def render(event: dict, locale: str = "ru") -> dict[str, str]:
    return _ru(event)  # KZ/EN added in Phase 6
