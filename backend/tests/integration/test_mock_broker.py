"""End-to-end through a fake BrokerAdapter — exercises the abstraction
without touching real exchanges or MT5."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest

from app.core.brokers.base import BrokerAdapter
from app.core.brokers.models import (
    AccountInfo,
    BrokerCredentials,
    BrokerType,
    Direction,
    Order,
    OrderRequest,
    Position,
    SymbolInfo,
    Tick,
    Trade,
)


class MockBroker(BrokerAdapter):
    """In-memory adapter that mimics MT5 / ccxt behaviour."""

    def __init__(self, creds: BrokerCredentials) -> None:
        super().__init__(creds)
        self.balance = 10_000.0
        self.positions: list[Position] = []
        self.orders: list[Order] = []
        self.trades: list[Trade] = []
        self._next_ticket = 1

    async def connect(self) -> None:
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False

    async def get_account(self) -> AccountInfo:
        unreal = sum(p.unrealized_pnl for p in self.positions)
        return AccountInfo(
            balance=self.balance, equity=self.balance + unreal, margin=0,
            free_margin=self.balance, profit=unreal, currency="USD", leverage=100,
        )

    async def get_symbols(self, symbols: list[str] | None = None) -> list[SymbolInfo]:
        out = []
        for s in symbols or []:
            out.append(SymbolInfo(
                symbol=s, broker_symbol=s, tick_size=0.00001, pip_value=0.0001,
                min_lot=0.01, max_lot=10, lot_step=0.01, contract_size=100_000,
            ))
        return out

    async def get_ohlcv(self, symbol: str, timeframe: str, bars: int) -> pd.DataFrame:
        rng = np.random.default_rng(hash(symbol) & 0xFFFF)
        idx = pd.date_range(end=datetime.now(timezone.utc), periods=bars, freq="h")
        close = 1.10 + rng.normal(0, 0.001, bars).cumsum()
        return pd.DataFrame({
            "open": close, "high": close * 1.0005, "low": close * 0.9995,
            "close": close, "volume": np.ones(bars),
        }, index=idx)

    async def get_current_price(self, symbol: str) -> Tick:
        return Tick(symbol=symbol, bid=1.10, ask=1.1001, timestamp=datetime.now(timezone.utc))

    async def stream_prices(self, symbols: list[str]) -> AsyncIterator[Tick]:
        for s in symbols:
            yield await self.get_current_price(s)

    async def place_order(self, req: OrderRequest) -> Order | None:
        ticket = str(self._next_ticket)
        self._next_ticket += 1
        order = Order(
            ticket=ticket, symbol=req.symbol, direction=req.direction,
            lot_size=req.lot_size, entry_price=1.10,
            timestamp=datetime.now(timezone.utc), comment=req.comment,
        )
        self.orders.append(order)
        self.positions.append(Position(
            ticket=ticket, symbol=req.symbol, direction=req.direction,
            lot_size=req.lot_size, entry_price=1.10, current_price=1.1001,
            unrealized_pnl=0.0, swap=0, commission=0,
            opened_at=order.timestamp,
        ))
        return order

    async def close_position(self, ticket: str, lots: float | None = None) -> bool:
        for i, p in enumerate(self.positions):
            if p.ticket == ticket:
                self.positions.pop(i)
                return True
        return False

    async def close_all(self, symbol: str | None = None) -> int:
        n = sum(1 for p in self.positions if symbol is None or p.symbol == symbol)
        self.positions = [p for p in self.positions if symbol and p.symbol != symbol]
        return n

    async def get_positions(self) -> list[Position]:
        return list(self.positions)

    async def get_history(self, since: datetime) -> list[Trade]:
        return list(self.trades)


# ── Tests ───────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_lifecycle() -> None:
    adapter = MockBroker(BrokerCredentials(type=BrokerType.MT5))
    await adapter.connect()
    assert adapter.connected

    info = await adapter.get_account()
    assert info.balance == 10_000.0

    order = await adapter.place_order(OrderRequest(
        symbol="EURUSD", direction=Direction.LONG, lot_size=0.01,
    ))
    assert order is not None
    assert order.ticket == "1"

    positions = await adapter.get_positions()
    assert len(positions) == 1

    closed = await adapter.close_all()
    assert closed >= 1
    assert await adapter.get_positions() == []

    await adapter.disconnect()
    assert not adapter.connected


@pytest.mark.asyncio
async def test_get_symbols_normalizes() -> None:
    adapter = MockBroker(BrokerCredentials(type=BrokerType.MT5))
    await adapter.connect()
    syms = await adapter.get_symbols(["EURUSD", "GBPUSD"])
    assert {s.symbol for s in syms} == {"EURUSD", "GBPUSD"}
    assert all(s.contract_size == 100_000 for s in syms)


@pytest.mark.asyncio
async def test_ping_when_connected() -> None:
    adapter = MockBroker(BrokerCredentials(type=BrokerType.MT5))
    await adapter.connect()
    assert await adapter.ping() is True
    await adapter.disconnect()
    # Mock raises on get_account when disconnected? No — it doesn't here, so just check it runs.
