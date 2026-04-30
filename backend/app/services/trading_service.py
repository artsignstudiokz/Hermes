"""TradingService — single orchestrator the routes/workers go through."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.ws.manager import WebSocketManager, get_ws_manager
from app.core.brokers.models import BrokerCredentials, BrokerType
from app.core.brokers.registry import BrokerRegistry
from app.core.notifications.service import NotificationService
from app.core.security.vault import CredentialVault
from app.core.strategy.runner import StrategyRunner
from app.db.models import BrokerAccount, StrategyConfigRow
from app.db.session import get_sessionmaker
from app.workers.trading_worker import TradingWorker

logger = logging.getLogger(__name__)


class TradingService:
    """Owns the active TradingWorker. One worker per process for now."""

    def __init__(
        self,
        registry: BrokerRegistry,
        vault: CredentialVault,
        notifier: NotificationService | None = None,
    ) -> None:
        self._registry = registry
        self._vault = vault
        self._notifier = notifier
        self._ws: WebSocketManager = get_ws_manager()
        self._worker: TradingWorker | None = None
        self._broker_account_id: int | None = None

    @property
    def status(self) -> dict:
        # Worker is always a dict so consumers can do .get("running") safely
        # without a None-check. Shape matches TradingWorker.state exactly.
        worker_state = self._worker.state if self._worker else {
            "running": False,
            "paused": False,
            "trading_enabled": False,
            "last_tick": None,
            "tick_count": 0,
            "last_error": None,
        }
        return {
            "broker_account_id": self._broker_account_id,
            "worker": worker_state,
        }

    async def start(self, broker_account_id: int) -> dict:
        if self._worker and self._worker.state["running"]:
            return self.status

        # Load broker account + active strategy config.
        sm = get_sessionmaker()
        async with sm() as session:
            account = await session.get(BrokerAccount, broker_account_id)
            if account is None:
                raise ValueError(f"BrokerAccount {broker_account_id} not found")

            cfg_row = await self._active_strategy(session)
            params = cfg_row.payload if cfg_row else {}

        creds_payload = self._vault.get(account.vault_key)
        if creds_payload is None:
            raise ValueError(f"No credentials in vault for account {broker_account_id}")
        creds = BrokerCredentials(
            type=BrokerType(account.type),
            server=account.server,
            login=int(account.login) if account.login else None,
            password=creds_payload.get("password"),
            api_key=creds_payload.get("api_key"),
            api_secret=creds_payload.get("api_secret"),
            api_passphrase=creds_payload.get("api_passphrase"),
            testnet=account.is_testnet,
        )

        adapter = await self._registry.connect(broker_account_id, creds)
        symbols = params.get("symbols") or [
            "EURUSD", "GBPUSD", "EURCHF", "EURJPY", "USDCHF", "USDJPY",
        ]

        runner = StrategyRunner(
            adapter=adapter,
            params=params,
            symbols=symbols,
            timeframe=params.get("timeframe", "1h"),
        )

        self._worker = TradingWorker(
            broker_account_id=broker_account_id,
            adapter=adapter,
            runner=runner,
            ws=self._ws,
            notifier=self._notifier,
            check_interval=float(params.get("check_interval_sec", 60)),
        )
        await self._worker.start()
        self._broker_account_id = broker_account_id
        return self.status

    async def stop(self) -> dict:
        if self._worker:
            await self._worker.stop()
            self._worker = None
        return self.status

    async def pause(self) -> dict:
        if self._worker:
            self._worker.pause()
        return self.status

    async def resume(self) -> dict:
        if self._worker:
            self._worker.resume()
        return self.status

    async def kill_switch(self) -> int:
        if not self._worker:
            return 0
        return await self._worker.kill_switch()

    def enable_trading(self) -> dict:
        if self._worker is None:
            raise ValueError("Trading worker not started — click Start first")
        self._worker.enable_trading()
        return self.status

    def disable_trading(self) -> dict:
        if self._worker is None:
            raise ValueError("Trading worker not started")
        self._worker.disable_trading()
        return self.status

    async def manual_open(
        self, symbol: str, direction: str, lot_size: float, comment: str = "manual_test",
    ) -> dict:
        """Place a single test order regardless of trading_enabled.

        Used by the "Тестовая сделка" button so the operator can verify
        broker connectivity / order routing without flipping the bot's
        trading toggle on. Bypasses the strategy entirely.
        """
        from app.core.brokers.models import Direction, OrderRequest

        adapter = self._registry.get_active()
        if adapter is None:
            raise ValueError("No active broker — connect one first")
        d = Direction.LONG if direction.lower() == "long" else Direction.SHORT
        order = await adapter.place_order(OrderRequest(
            symbol=symbol, direction=d, lot_size=lot_size, comment=comment,
        ))
        if order is None:
            raise ValueError(f"Broker rejected the order for {symbol}")
        return {
            "ticket": order.ticket,
            "symbol": symbol,
            "direction": direction,
            "lot_size": lot_size,
            "entry_price": getattr(order, "entry_price", None),
        }

    async def _active_strategy(self, session: AsyncSession) -> StrategyConfigRow | None:
        result = await session.execute(
            select(StrategyConfigRow).where(StrategyConfigRow.is_active.is_(True)).limit(1),
        )
        return result.scalar_one_or_none()


# Process-wide singletons (initialized in lifespan).
_service: TradingService | None = None


def init_trading_service(
    registry: BrokerRegistry,
    vault: CredentialVault,
    notifier: NotificationService | None = None,
) -> TradingService:
    global _service
    _service = TradingService(registry, vault, notifier)
    return _service


def get_trading_service() -> TradingService:
    if _service is None:
        raise RuntimeError("TradingService not initialised")
    return _service
