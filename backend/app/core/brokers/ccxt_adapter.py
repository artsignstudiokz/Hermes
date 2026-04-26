"""CCXT adapter — Phase 4 stub. Full implementation lands in Phase 4.

Defined here so BrokerRegistry compiles and the type system already knows
about Binance/Bybit/OKX paths.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime

import pandas as pd

from app.core.brokers.base import BrokerAdapter
from app.core.brokers.models import (
    AccountInfo,
    Order,
    OrderRequest,
    Position,
    SymbolInfo,
    Tick,
    Trade,
)


class CCXTAdapter(BrokerAdapter):
    """Stub for crypto exchanges. Implemented in Phase 4."""

    async def connect(self) -> None:
        raise NotImplementedError("CCXTAdapter is implemented in Phase 4")

    async def disconnect(self) -> None: ...

    async def get_account(self) -> AccountInfo:
        raise NotImplementedError

    async def get_symbols(self, symbols: list[str] | None = None) -> list[SymbolInfo]:
        raise NotImplementedError

    async def get_ohlcv(self, symbol: str, timeframe: str, bars: int) -> pd.DataFrame:
        raise NotImplementedError

    async def get_current_price(self, symbol: str) -> Tick:
        raise NotImplementedError

    async def stream_prices(self, symbols: list[str]) -> AsyncIterator[Tick]:
        raise NotImplementedError
        yield  # pragma: no cover

    async def place_order(self, req: OrderRequest) -> Order | None:
        raise NotImplementedError

    async def close_position(self, ticket: str, lots: float | None = None) -> bool:
        raise NotImplementedError

    async def close_all(self, symbol: str | None = None) -> int:
        raise NotImplementedError

    async def get_positions(self) -> list[Position]:
        raise NotImplementedError

    async def get_history(self, since: datetime) -> list[Trade]:
        raise NotImplementedError
