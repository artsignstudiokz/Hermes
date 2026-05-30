"""MetaTrader 5 adapter - wraps the synchronous SDK in async threads.

The MetaTrader5 Python package only works on Windows. Import is therefore
deferred until `connect()` so the rest of the app remains importable on
macOS/Linux (e.g. for tests with a mock adapter).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from app.core.brokers.base import BrokerAdapter


class BrokerOrderRejected(Exception):
    """MT5 returned a non-DONE retcode for an order request.

    The message is already translated into a user-facing Russian
    string (see MT5Adapter._translate_retcode). Callers in route
    handlers raise HTTP 400 with this message so the SPA toast
    reads "Рынок закрыт" instead of "Брокер отклонил ордер".
    """


from app.core.brokers.models import (
    AccountInfo,
    BrokerCredentials,
    Direction,
    Order,
    OrderRequest,
    Position,
    SymbolInfo,
    Tick,
    Trade,
)

logger = logging.getLogger(__name__)

# Common broker symbol suffixes we probe in order.
_SYMBOL_SUFFIXES = ("", "m", ".m", ".i", ".e", ".pro", ".raw", ".std")


class MT5Adapter(BrokerAdapter):
    """Adapter for MetaTrader 5 brokers (Forex)."""

    def __init__(self, credentials: BrokerCredentials) -> None:
        super().__init__(credentials)
        self._mt5: Any | None = None  # MetaTrader5 module ref
        self._symbol_map: dict[str, str] = {}   # canonical → broker-specific
        self._timeframes: dict[str, int] = {}
        self._lock = asyncio.Lock()             # MT5 SDK is not thread-safe

    # ── Lifecycle ────────────────────────────────────────────────────────────
    async def connect(self) -> None:
        async with self._lock:
            await asyncio.to_thread(self._connect_sync)
            self._connected = True

    def _connect_sync(self) -> None:
        try:
            import MetaTrader5 as mt5  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError(
                "MetaTrader5 package is not available. MT5 supports Windows only.",
            ) from exc

        self._mt5 = mt5
        self._timeframes = {
            "1m": mt5.TIMEFRAME_M1,
            "5m": mt5.TIMEFRAME_M5,
            "15m": mt5.TIMEFRAME_M15,
            "30m": mt5.TIMEFRAME_M30,
            "1h": mt5.TIMEFRAME_H1,
            "4h": mt5.TIMEFRAME_H4,
            "1d": mt5.TIMEFRAME_D1,
        }

        kwargs: dict[str, Any] = {"timeout": 10_000}
        if self._creds.login:
            kwargs["login"] = int(self._creds.login)
            kwargs["password"] = self._creds.password or ""
            kwargs["server"] = self._creds.server or ""

        if not mt5.initialize(**kwargs):
            err = mt5.last_error()
            raise ConnectionError(f"MT5 initialize() failed: {err}")

        info = mt5.account_info()
        if info is None:
            mt5.shutdown()
            raise ConnectionError("MT5 connected but account_info() returned None")

        logger.info(
            "MT5 connected: server=%s login=%s balance=%.2f leverage=1:%d",
            info.server, info.login, info.balance, info.leverage,
        )

    async def disconnect(self) -> None:
        if not self._connected or self._mt5 is None:
            return
        async with self._lock:
            await asyncio.to_thread(self._mt5.shutdown)
            self._connected = False
            logger.info("MT5 disconnected")

    # ── Symbol resolution ────────────────────────────────────────────────────
    async def _resolve_symbol(self, symbol: str) -> str:
        if symbol in self._symbol_map:
            return self._symbol_map[symbol]
        broker_symbol = await asyncio.to_thread(self._resolve_symbol_sync, symbol)
        self._symbol_map[symbol] = broker_symbol
        return broker_symbol

    def _resolve_symbol_sync(self, symbol: str) -> str:
        assert self._mt5 is not None
        for suffix in _SYMBOL_SUFFIXES:
            candidate = symbol + suffix
            info = self._mt5.symbol_info(candidate)
            if info is not None:
                if not info.visible:
                    self._mt5.symbol_select(candidate, True)
                if suffix:
                    logger.info("Symbol mapping %s → %s", symbol, candidate)
                return candidate
        return symbol

    # ── Account ──────────────────────────────────────────────────────────────
    async def get_account(self) -> AccountInfo:
        self._ensure_connected()
        info = await asyncio.to_thread(self._mt5.account_info)
        if info is None:
            raise RuntimeError("MT5 account_info returned None")
        return AccountInfo(
            balance=float(info.balance),
            equity=float(info.equity),
            margin=float(info.margin),
            free_margin=float(info.margin_free),
            profit=float(info.profit),
            currency=info.currency,
            leverage=int(info.leverage),
            server=info.server,
            login=int(info.login),
        )

    async def get_symbols(self, symbols: list[str] | None = None) -> list[SymbolInfo]:
        self._ensure_connected()
        targets = symbols or []
        out: list[SymbolInfo] = []
        for s in targets:
            broker_symbol = await self._resolve_symbol(s)
            info = await asyncio.to_thread(self._mt5.symbol_info, broker_symbol)
            if info is None:
                continue
            point = float(info.point)
            digits = int(info.digits)
            # Forex pip = 10*point on 5/3-digit brokers; 1*point on JPY 3-digit.
            pip_value = point * (10 if digits in (3, 5) else 1)
            out.append(SymbolInfo(
                symbol=s,
                broker_symbol=broker_symbol,
                tick_size=point,
                pip_value=pip_value,
                min_lot=float(info.volume_min),
                max_lot=float(info.volume_max),
                lot_step=float(info.volume_step),
                contract_size=float(info.trade_contract_size),
                spread_pips=float(info.spread) * point / pip_value if pip_value else 0.0,
                is_crypto=False,
                quote_currency=info.currency_profit,
            ))
        return out

    # ── Market data ──────────────────────────────────────────────────────────
    async def get_ohlcv(self, symbol: str, timeframe: str, bars: int) -> pd.DataFrame:
        self._ensure_connected()
        tf = self._timeframes.get(timeframe)
        if tf is None:
            raise ValueError(f"Unknown timeframe: {timeframe}")
        broker_symbol = await self._resolve_symbol(symbol)
        rates = await asyncio.to_thread(self._mt5.copy_rates_from_pos, broker_symbol, tf, 0, bars)
        if rates is None or len(rates) == 0:
            raise ValueError(f"No OHLCV data for {symbol}")
        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
        df = df.set_index("time").rename(columns={"tick_volume": "volume"})
        return df[["open", "high", "low", "close", "volume"]]

    async def get_current_price(self, symbol: str) -> Tick:
        self._ensure_connected()
        broker_symbol = await self._resolve_symbol(symbol)
        tick = await asyncio.to_thread(self._mt5.symbol_info_tick, broker_symbol)
        if tick is None:
            raise ValueError(f"No tick for {symbol}")
        return Tick(
            symbol=symbol,
            bid=float(tick.bid),
            ask=float(tick.ask),
            last=float(tick.last) if tick.last else None,
            volume=float(tick.volume) if tick.volume else None,
            timestamp=datetime.fromtimestamp(tick.time, tz=timezone.utc),
        )

    # ── Orders ───────────────────────────────────────────────────────────────
    async def place_order(self, req: OrderRequest) -> Order | None:
        self._ensure_connected()
        broker_symbol = await self._resolve_symbol(req.symbol)
        tick = await self.get_current_price(req.symbol)
        mt5 = self._mt5
        order_type = mt5.ORDER_TYPE_BUY if req.direction == Direction.LONG else mt5.ORDER_TYPE_SELL
        price = tick.ask if req.direction == Direction.LONG else tick.bid

        # v1.0.38: snap volume to the symbol's lot_step and floor at
        # volume_min, otherwise MT5 rejects with "Invalid volume". Our
        # _scale_lot already rounds to 0.01 but symbols can have
        # different steps (BTCUSD often 0.001; XAUUSD 0.01; metals
        # 0.1) and different minimums.
        info = await asyncio.to_thread(self._mt5.symbol_info, broker_symbol)
        volume = float(req.lot_size)
        if info is not None:
            step = float(info.volume_step) or 0.01
            vmin = float(info.volume_min) or 0.01
            vmax = float(info.volume_max) or 100.0
            volume = max(vmin, min(vmax, round(round(volume / step) * step, 8)))

        # v1.0.38: not every broker honours IOC. Exness Trial frequently
        # rejects with "Unsupported filling mode". Pick a mode the
        # symbol actually allows.
        filling_mode = self._pick_filling_mode(info)

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": broker_symbol,
            "volume": volume,
            "type": order_type,
            "price": price,
            "deviation": req.deviation_points,
            "magic": req.magic,
            "comment": req.comment[:31] or "hermes",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": filling_mode,
        }
        # Broker-side SL/TP - survive bot crashes, OS reboots, network
        # drops. MT5 will close the position autonomously when price
        # touches either level. We send them as absolute prices because
        # different brokers quote different decimal places per symbol.
        if req.stop_loss is not None and req.stop_loss > 0:
            request["sl"] = float(req.stop_loss)
        if req.take_profit is not None and req.take_profit > 0:
            request["tp"] = float(req.take_profit)
        result = await asyncio.to_thread(mt5.order_send, request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            err = self._translate_retcode(result, mt5)
            logger.error(
                "Order failed for %s (vol=%s, fill=%s): %s",
                broker_symbol, volume, filling_mode, err,
            )
            # v1.0.40: surface a translated reason via a tagged exception
            # so the route can show "Рынок закрыт" instead of the
            # vendor-generic "Брокер отклонил ордер".
            raise BrokerOrderRejected(err)

        return Order(
            ticket=str(result.order),
            symbol=req.symbol,
            direction=req.direction,
            lot_size=volume,
            entry_price=float(price),
            timestamp=datetime.now(timezone.utc),
            comment=req.comment,
        )

    def _translate_retcode(self, result: Any, mt5: Any) -> str:
        """Map an MT5 retcode + comment into a clear Russian message.

        Most retcodes have a `comment` that's reasonable, but the few
        common ones (market closed, trade disabled, off-quotes) deserve
        a friendly translation so the operator doesn't blame the bot
        when the FX market is shut for the weekend.
        """
        if result is None:
            return "Терминал MT5 не ответил - проверьте что он открыт и подключён."
        code = int(getattr(result, "retcode", 0))
        comment = getattr(result, "comment", "") or ""
        # Mapping of common retcodes we want to surface clearly.
        # Numeric values are stable across MT5 versions.
        friendly: dict[int, str] = {
            10004: "Запрошена котировка - попробуйте снова через несколько секунд.",
            10006: "Заявка отклонена брокером.",
            10007: "Заявка отменена трейдером.",
            10008: "Заявка размещена.",
            10013: "Заявка некорректна - проверьте символ и объём.",
            10014: "Некорректный объём ордера.",
            10015: "Цена изменилась - попробуйте снова.",
            10016: "Некорректные стопы (SL/TP слишком близко к цене).",
            10017: "Торговля отключена для этого символа.",
            10018: "Рынок закрыт - откроется в понедельник около 03:00 по Алматы.",
            10019: "Недостаточно средств на счёте.",
            10020: "Котировки устарели - подождите следующего тика.",
            10021: "Нет котировок для этого символа.",
            10022: "Некорректная дата истечения ордера.",
            10023: "Состояние ордера изменилось.",
            10024: "Слишком частые запросы - сбавьте обороты.",
            10025: "На счёте уже изменения - запрос отвергнут.",
            10026: "Автотрейдинг отключён на сервере брокера.",
            10027: "Автотрейдинг отключён в терминале.",
            10028: "Запрос заблокирован для обработки.",
            10029: "Не удалось исполнить ордер.",
            10030: "Неподдерживаемый режим исполнения (filling mode).",
            10031: "Нет связи с торговым сервером.",
            10032: "Операция доступна только для реального счёта.",
            10033: "Достигнут лимит количества отложенных ордеров.",
            10034: "Достигнут лимит объёма по символу.",
            10035: "Некорректный или запрещённый тип ордера.",
            10036: "Позиция уже закрыта.",
        }
        msg = friendly.get(code)
        if msg:
            return msg
        # Fallback: include code + comment so we don't hide info.
        return f"Брокер отклонил ордер (код {code}): {comment}".strip()

    def _pick_filling_mode(self, info: Any) -> int:
        """Pick a filling mode the symbol's MT5 broker honours.

        symbol_info.filling_mode is a bitmask where bit 0 = FOK is
        allowed, bit 1 = IOC. RETURN (mode 2) has no bit and is the
        universal fallback. Order of preference: FOK (atomic),
        IOC (partial-fill), then RETURN (queue the leftover).
        """
        mt5 = self._mt5
        mask = int(getattr(info, "filling_mode", 0)) if info else 0
        if mask & 1:
            return mt5.ORDER_FILLING_FOK
        if mask & 2:
            return mt5.ORDER_FILLING_IOC
        return mt5.ORDER_FILLING_RETURN

    async def close_position(self, ticket: str, lots: float | None = None) -> bool:
        self._ensure_connected()
        positions = await asyncio.to_thread(self._mt5.positions_get, ticket=int(ticket))
        if not positions:
            return False
        pos = positions[0]
        return await self._close_position_object(pos, lots)

    async def _close_position_object(self, pos: Any, lots: float | None) -> bool:
        mt5 = self._mt5
        symbol = pos.symbol
        direction = Direction.LONG if pos.type == mt5.POSITION_TYPE_BUY else Direction.SHORT
        close_type = mt5.ORDER_TYPE_SELL if direction == Direction.LONG else mt5.ORDER_TYPE_BUY
        tick = await asyncio.to_thread(mt5.symbol_info_tick, symbol)
        price = tick.bid if direction == Direction.LONG else tick.ask
        volume = lots if lots is not None else pos.volume

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(volume),
            "type": close_type,
            "position": pos.ticket,
            "price": price,
            "deviation": 20,
            "magic": pos.magic,
            "comment": "hermes_close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        result = await asyncio.to_thread(mt5.order_send, request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error("Close failed for ticket %s: %s", pos.ticket, result and result.comment)
            return False
        return True

    async def close_all(self, symbol: str | None = None) -> int:
        self._ensure_connected()
        if symbol:
            broker_symbol = await self._resolve_symbol(symbol)
            positions = await asyncio.to_thread(self._mt5.positions_get, symbol=broker_symbol)
        else:
            positions = await asyncio.to_thread(self._mt5.positions_get)
        if not positions:
            return 0
        closed = 0
        for pos in positions:
            if await self._close_position_object(pos, None):
                closed += 1
        return closed

    async def get_positions(self) -> list[Position]:
        self._ensure_connected()
        positions = await asyncio.to_thread(self._mt5.positions_get)
        if not positions:
            return []
        return [
            Position(
                ticket=str(p.ticket),
                symbol=p.symbol,
                direction=Direction.LONG if p.type == self._mt5.POSITION_TYPE_BUY else Direction.SHORT,
                lot_size=float(p.volume),
                entry_price=float(p.price_open),
                current_price=float(p.price_current),
                unrealized_pnl=float(p.profit),
                swap=float(p.swap),
                commission=0.0,  # MT5 reports commissions via deals, not positions
                opened_at=datetime.fromtimestamp(p.time, tz=timezone.utc),
                comment=p.comment or "",
            )
            for p in positions
        ]

    async def get_history(self, since: datetime) -> list[Trade]:
        self._ensure_connected()
        from_ts = int(since.timestamp())
        to_ts = int(datetime.now(tz=timezone.utc).timestamp())
        deals = await asyncio.to_thread(self._mt5.history_deals_get, from_ts, to_ts)
        if not deals:
            return []

        # Pair entry+exit deals by position id.
        by_position: dict[int, list[Any]] = {}
        for d in deals:
            by_position.setdefault(d.position_id, []).append(d)

        trades: list[Trade] = []
        for pos_id, group in by_position.items():
            if len(group) < 2:
                continue
            entry, exit_ = sorted(group, key=lambda d: d.time)[:2]
            direction = Direction.LONG if entry.type == self._mt5.DEAL_TYPE_BUY else Direction.SHORT
            trades.append(Trade(
                ticket=str(pos_id),
                symbol=entry.symbol,
                direction=direction,
                lot_size=float(entry.volume),
                entry_price=float(entry.price),
                exit_price=float(exit_.price),
                pnl=float(sum(d.profit for d in group)),
                commission=float(sum(d.commission for d in group)),
                swap=float(sum(d.swap for d in group)),
                opened_at=datetime.fromtimestamp(entry.time, tz=timezone.utc),
                closed_at=datetime.fromtimestamp(exit_.time, tz=timezone.utc),
                reason=entry.comment or "",
            ))
        return trades

    # ── Internals ────────────────────────────────────────────────────────────
    def _ensure_connected(self) -> None:
        if not self._connected or self._mt5 is None:
            raise ConnectionError("MT5 adapter is not connected")
