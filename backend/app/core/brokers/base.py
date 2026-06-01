"""BrokerAdapter - abstract base every broker integration must implement."""

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

    async def check_autotrading(self) -> tuple[bool, str]:
        """Probe whether the broker accepts algo orders right now.

        Default: always OK. MT5Adapter overrides this to inspect
        terminal_info().trade_allowed - some users have AutoTrading
        disabled in the MT5 client and every order_send fails with
        retcode 10027 until they enable it.
        """
        return True, ""

    async def compute_lot_for_risk(
        self,
        symbol: str,
        entry_price: float,
        sl_price: float,
        risk_dollars: float,
    ) -> float | None:
        """Compute lot that risks ~risk_dollars between entry and SL.

        MT5Adapter implements it via symbol_info.trade_tick_size /
        trade_tick_value. Other adapters can return None to use
        notional sizing instead.
        """
        return None

    async def get_deal_for_position(self, ticket: str) -> dict | None:
        """Best-effort lookup of the closing deal for a position ticket.

        Returns a dict like
        {"exit_price": float, "pnl": float, "trigger": "tp"|"sl"|"manual"}
        if the broker exposes the history. MT5Adapter implements this
        via deals_get(); other adapters can return None to skip the
        enriched notification.
        """
        return None

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
                except Exception:  # noqa: BLE001 - broker errors logged by caller
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
        """Cheap health check - adapters can override with broker-specific call."""
        try:
            await self.get_account()
            return True
        except Exception:  # noqa: BLE001
            return False
