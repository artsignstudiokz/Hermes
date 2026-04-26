"""BrokerAdapter — abstract base every broker integration must implement."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from datetime import datetime

import pandas as pd

from app.core.brokers.models import (
    AccountInfo,
    BrokerCredentials,
    Order,
    OrderRequest,
    Position,
    SymbolInfo,
    Tick,
    Trade,
)


class BrokerAdapter(ABC):
    """Async, broker-agnostic trading interface.

    Implementations:
      - MT5Adapter   (Windows-only, wraps the synchronous MetaTrader5 SDK)
      - CCXTAdapter  (cross-platform; Binance/Bybit/OKX)

    Each adapter must:
      1. Normalise symbols (e.g. EURUSD → EURUSDm), lots, pip values.
      2. Be safe to call from async code (heavy ops dispatched to threads).
      3. Return only dataclasses from `core/brokers/models.py`.
    """

    def __init__(self, credentials: BrokerCredentials) -> None:
        self._creds = credentials
        self._connected: bool = False

    @property
    def connected(self) -> bool:
        return self._connected

    # ── Lifecycle ────────────────────────────────────────────────────────────
    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def disconnect(self) -> None: ...

    # ── Account ──────────────────────────────────────────────────────────────
    @abstractmethod
    async def get_account(self) -> AccountInfo: ...

    @abstractmethod
    async def get_symbols(self, symbols: list[str] | None = None) -> list[SymbolInfo]: ...

    # ── Market data ──────────────────────────────────────────────────────────
    @abstractmethod
    async def get_ohlcv(self, symbol: str, timeframe: str, bars: int) -> pd.DataFrame: ...

    @abstractmethod
    async def get_current_price(self, symbol: str) -> Tick: ...

    async def stream_prices(self, symbols: list[str]) -> AsyncIterator[Tick]:
        """Default: poll get_current_price every 500ms.

        Subclasses with native streaming (ccxt.pro) override this.
        """
        import asyncio

        while True:
            for s in symbols:
                try:
                    yield await self.get_current_price(s)
                except Exception:  # noqa: BLE001 — broker errors logged by caller
                    continue
            await asyncio.sleep(0.5)

    # ── Orders ───────────────────────────────────────────────────────────────
    @abstractmethod
    async def place_order(self, req: OrderRequest) -> Order | None: ...

    @abstractmethod
    async def close_position(self, ticket: str, lots: float | None = None) -> bool: ...

    @abstractmethod
    async def close_all(self, symbol: str | None = None) -> int: ...

    @abstractmethod
    async def get_positions(self) -> list[Position]: ...

    @abstractmethod
    async def get_history(self, since: datetime) -> list[Trade]: ...

    # ── Health ───────────────────────────────────────────────────────────────
    async def ping(self) -> bool:
        """Cheap health check — adapters can override with broker-specific call."""
        try:
            await self.get_account()
            return True
        except Exception:  # noqa: BLE001
            return False
