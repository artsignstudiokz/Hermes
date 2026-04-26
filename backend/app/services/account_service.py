"""AccountService — facade over BrokerRegistry for routes that need
account-level data without touching adapters directly.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.brokers.models import AccountInfo, Position
from app.core.brokers.registry import BrokerRegistry
from app.db.models import EquityPoint


class AccountService:
    def __init__(self, registry: BrokerRegistry) -> None:
        self._registry = registry

    async def info(self) -> AccountInfo | None:
        adapter = self._registry.get_active()
        if not adapter:
            return None
        return await adapter.get_account()

    async def positions(self) -> list[Position]:
        adapter = self._registry.get_active()
        if not adapter:
            return []
        return await adapter.get_positions()

    async def equity_history(
        self,
        session: AsyncSession,
        broker_account_id: int,
        days: int = 30,
    ) -> list[EquityPoint]:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        result = await session.execute(
            select(EquityPoint)
            .where(EquityPoint.broker_account_id == broker_account_id)
            .where(EquityPoint.ts >= since)
            .order_by(EquityPoint.ts.asc()),
        )
        return list(result.scalars())
