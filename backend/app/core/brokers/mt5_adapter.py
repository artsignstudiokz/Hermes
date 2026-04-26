"""MetaTrader 5 adapter — wraps the synchronous SDK in async threads.

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

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": broker_symbol,
            "volume": float(req.lot_size),
            "type": order_type,
            "price": price,
            "deviation": req.deviation_points,
            "magic": req.magic,
            "comment": req.comment[:31] or "hermes",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        result = await asyncio.to_thread(mt5.order_send, request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            err = result.comment if result else "send returned None"
            logger.error("Order failed for %s: %s", broker_symbol, err)
            return None

        return Order(
            ticket=str(result.order),
            symbol=req.symbol,
            direction=req.direction,
            lot_size=req.lot_size,
            entry_price=float(price),
            timestamp=datetime.now(timezone.utc),
            comment=req.comment,
        )

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
