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
        # the mode, confidence, lot, entry, sl, tp, plus the markdown
        # reason from the signal. The Telegram message lays them out as
        # a trader's brief - direction, prices, ratio - so the operator
        # can validate from their phone without opening the dashboard.
        side_word = "Покупка" if direction == "long" else "Продажа"
        mode_word = {"proven": "Проверенный", "autonomous": "Автономный"}.get(
            event.get("mode", ""), event.get("mode", ""),
        )
        conf = event.get("confidence", 0)
        lot = event.get("lot")
        entry = event.get("entry")
        sl = event.get("sl")
        tp = event.get("tp")

        # Compute risk/reward distance if we have all three prices.
        rr_line = ""
        if entry and sl and tp:
            risk = abs(entry - sl)
            reward = abs(tp - entry)
            if risk > 0:
                rr_line = f"\nR/R: 1:{reward / risk:.1f}"

        # Price formatting: 5 digits for FX majors, fewer for instruments
        # with bigger quotes (XAUUSD, BTCUSD). Pick by magnitude.
        def fmt(p: float | None) -> str:
            if p is None: return "-"
            if p >= 1000: return f"{p:.2f}"
            if p >= 100: return f"{p:.3f}"
            return f"{p:.5f}"

        lines = [
            f"<b>🟢 Hermes открыл сделку</b> ({mode_word})",
            "",
            f"<b>{sym}</b> · {_arrow(direction)} {side_word}",
            f"Уверенность: <b>{conf:.2f}</b>",
        ]
        if lot is not None:
            lines.append(f"Объём: <b>{lot}</b> лот")
        if entry is not None:
            lines.append(f"Вход: <code>{fmt(entry)}</code>")
        if sl is not None:
            lines.append(f"Stop Loss: <code>{fmt(sl)}</code>")
        if tp is not None:
            lines.append(f"Take Profit: <code>{fmt(tp)}</code>{rr_line}")
        risk_dollars = event.get("risk_dollars")
        risk_pct_v = event.get("risk_pct")
        if risk_dollars is not None and risk_pct_v is not None:
            lines.append(f"Риск: <b>~{risk_dollars}</b> ({risk_pct_v}% эквити)")
        reason = (event.get("reason") or "")[:400]
        if reason:
            lines += ["", f"<i>{reason}</i>"]

        return {
            "title": f"Hermes · {sym} открыто",
            "body": f"{_arrow(direction)} {side_word} {sym} · {lot or ''} лот · режим {mode_word}",
            "body_long": "\n".join(lines),
        }
    if t == "trade_closed":
        # Reconciliation detected a broker-side close (SL or TP hit, or
        # operator closed manually from MT5). Show which threshold
        # triggered and the realised P&L.
        sign = "+" if (pnl or 0) >= 0 else ""
        trigger = event.get("trigger") or "manual"   # "tp" | "sl" | "manual"
        trigger_word = {"tp": "Take Profit", "sl": "Stop Loss", "manual": "Закрыто вручную"}.get(
            trigger, trigger,
        )
        emoji = "🎯" if trigger == "tp" else ("🛑" if trigger == "sl" else "✋")
        exit_price = event.get("exit_price")

        def fmt(p):
            if p is None: return "-"
            if p >= 1000: return f"{p:.2f}"
            if p >= 100: return f"{p:.3f}"
            return f"{p:.5f}"

        lines = [
            f"<b>{emoji} Hermes закрыл сделку</b>",
            "",
            f"<b>{sym}</b> · {trigger_word}",
        ]
        if exit_price is not None:
            lines.append(f"Цена закрытия: <code>{fmt(exit_price)}</code>")
        if pnl is not None:
            lines.append(f"Результат: <b>{sign}{pnl:.2f}</b>")

        return {
            "title": f"Hermes · {sym} закрыто",
            "body": f"{trigger_word} · {sign}{(pnl or 0):.2f}",
            "body_long": "\n".join(lines),
        }
    if t == "broker_down":
        return {
            "title": "Hermes · Брокер недоступен",
            "body": "Бот приостановлен - проверьте MT5 терминал",
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
