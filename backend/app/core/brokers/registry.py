"""BrokerRegistry — lookup-by-id for active broker adapter instances.

The registry holds one adapter per broker_account.id. It is process-wide
(singletons live in app.state) and serializes connect/disconnect via locks
to avoid races during reconfiguration.
"""

from __future__ import annotations

import asyncio
import logging

from app.core.brokers.base import BrokerAdapter
from app.core.brokers.models import BrokerCredentials, BrokerType

logger = logging.getLogger(__name__)


class BrokerRegistry:
    def __init__(self) -> None:
        self._adapters: dict[int, BrokerAdapter] = {}
        self._active_id: int | None = None
        self._lock = asyncio.Lock()

    async def connect(self, account_id: int, creds: BrokerCredentials) -> BrokerAdapter:
        async with self._lock:
            if account_id in self._adapters:
                return self._adapters[account_id]
            adapter = self._build(creds)
            await adapter.connect()
            self._adapters[account_id] = adapter
            if self._active_id is None:
                self._active_id = account_id
            return adapter

    async def disconnect(self, account_id: int) -> None:
        async with self._lock:
            adapter = self._adapters.pop(account_id, None)
            if adapter is not None:
                await adapter.disconnect()
            if self._active_id == account_id:
                self._active_id = next(iter(self._adapters), None)

    async def disconnect_all(self) -> None:
        async with self._lock:
            for adapter in list(self._adapters.values()):
                try:
                    await adapter.disconnect()
                except Exception:  # noqa: BLE001
                    logger.exception("Error disconnecting adapter")
            self._adapters.clear()
            self._active_id = None

    def get(self, account_id: int) -> BrokerAdapter | None:
        return self._adapters.get(account_id)

    def get_active(self) -> BrokerAdapter | None:
        if self._active_id is None:
            return None
        return self._adapters.get(self._active_id)

    @property
    def active_id(self) -> int | None:
        return self._active_id

    async def set_active(self, account_id: int) -> None:
        async with self._lock:
            if account_id not in self._adapters:
                raise KeyError(f"No adapter connected for account {account_id}")
            self._active_id = account_id

    def _build(self, creds: BrokerCredentials) -> BrokerAdapter:
        if creds.type == BrokerType.MT5:
            from app.core.brokers.mt5_adapter import MT5Adapter
            return MT5Adapter(creds)
        if creds.type in (BrokerType.BINANCE, BrokerType.BYBIT, BrokerType.OKX):
            from app.core.brokers.ccxt_adapter import CCXTAdapter
            return CCXTAdapter(creds)
        raise ValueError(f"Unsupported broker type: {creds.type}")
