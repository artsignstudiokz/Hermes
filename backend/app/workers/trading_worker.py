"""Asyncio worker that runs the strategy loop and persists results.

Polls every CHECK_INTERVAL seconds, calls runner.tick(), persists
position/equity snapshots, and broadcasts updates over WebSocket.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from app.api.ws.manager import WebSocketManager
from app.core.brokers.base import BrokerAdapter
from app.core.notifications.service import NotificationService
from app.core.strategy.runner import StrategyRunner
from app.db.models import EquityPoint, PositionSnapshot, TradeRow
from app.db.session import get_sessionmaker

logger = logging.getLogger(__name__)


class TradingWorker:
    """Long-running async loop. Cancellable via stop()."""

    def __init__(
        self,
        broker_account_id: int,
        adapter: BrokerAdapter,
        runner: StrategyRunner,
        ws: WebSocketManager,
        notifier: NotificationService | None = None,
        check_interval: float = 60.0,
    ) -> None:
        self._account_id = broker_account_id
        self._adapter = adapter
        self._runner = runner
        self._ws = ws
        self._notifier = notifier
        self._check_interval = check_interval
        self._task: asyncio.Task | None = None
        self._stop_evt = asyncio.Event()
        self._paused = False
        self._last_tick: datetime | None = None
        self._last_error: str | None = None
        self._tick_count = 0

    @property
    def state(self) -> dict:
        return {
            "running": self._task is not None and not self._task.done(),
            "paused": self._paused,
            "last_tick": self._last_tick.isoformat() if self._last_tick else None,
            "tick_count": self._tick_count,
            "last_error": self._last_error,
        }

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        await self._runner.setup()
        self._stop_evt.clear()
        self._task = asyncio.create_task(self._run(), name="hermes-trading-worker")
        logger.info("Trading worker started for account %d", self._account_id)

    async def stop(self) -> None:
        self._stop_evt.set()
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=5.0)
            except asyncio.TimeoutError:
                self._task.cancel()
        self._task = None
        logger.info("Trading worker stopped for account %d", self._account_id)

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    async def kill_switch(self) -> int:
        """Close everything immediately, regardless of strategy state."""
        closed = await self._adapter.close_all()
        await self._ws.broadcast("signals", {
            "type": "kill_switch",
            "closed_count": closed,
            "ts": datetime.now(timezone.utc).isoformat(),
        })
        logger.warning("Kill-switch invoked: %d positions closed", closed)
        return closed

    async def _run(self) -> None:
        sm = get_sessionmaker()
        try:
            while not self._stop_evt.is_set():
                if not self._paused:
                    try:
                        await self._tick(sm)
                    except Exception as e:  # noqa: BLE001
                        self._last_error = str(e)
                        logger.exception("tick failed")
                        await self._ws.broadcast("signals", {
                            "type": "error",
                            "message": str(e),
                            "ts": datetime.now(timezone.utc).isoformat(),
                        })
                # Sleep with cancellation support.
                try:
                    await asyncio.wait_for(self._stop_evt.wait(), timeout=self._check_interval)
                except asyncio.TimeoutError:
                    pass
        except asyncio.CancelledError:
            logger.info("Worker cancelled")
            raise

    async def _tick(self, sm) -> None:
        actions = await self._runner.tick()
        self._last_tick = datetime.now(timezone.utc)
        self._tick_count += 1

        # Pull the latest account/position/equity snapshot.
        account = await self._adapter.get_account()
        positions = await self._adapter.get_positions()

        async with sm() as session:
            session.add(EquityPoint(
                broker_account_id=self._account_id,
                ts=self._last_tick,
                equity=account.equity,
                balance=account.balance,
                margin=account.margin,
                drawdown_pct=0.0,  # filled by separate calc later
            ))
            for p in positions:
                session.add(PositionSnapshot(
                    broker_account_id=self._account_id,
                    ts=self._last_tick,
                    symbol=p.symbol,
                    lots=p.lot_size,
                    avg_price=p.entry_price,
                    unrealized_pnl=p.unrealized_pnl,
                ))
            for action in actions:
                if action.get("action") == "open" and "broker_ticket" in action:
                    session.add(TradeRow(
                        broker_account_id=self._account_id,
                        ticket=action["broker_ticket"],
                        symbol=action["symbol"],
                        direction=action["direction"],
                        level=action.get("level", 0),
                        lots=action["lot_size"],
                        entry_price=action["price"],
                        opened_at=self._last_tick,
                        reason="grid_entry",
                    ))
            await session.commit()

        # Broadcast over WS.
        await self._ws.broadcast("equity", {
            "ts": self._last_tick.isoformat(),
            "equity": account.equity,
            "balance": account.balance,
            "margin": account.margin,
        })
        # Field names MUST match PositionOut schema — frontend writes the
        # WS payload directly into the ["positions"] react-query cache, so
        # any drift (lots vs lot_size, swap missing, etc.) → undefined →
        # `.toFixed` crash in PositionsTable.
        await self._ws.broadcast("positions", [
            {
                "ticket": p.ticket,
                "symbol": p.symbol,
                "direction": p.direction.value,
                "lot_size": p.lot_size,
                "entry_price": p.entry_price,
                "current_price": p.current_price,
                "unrealized_pnl": p.unrealized_pnl,
                "swap": p.swap,
                "commission": p.commission,
                "opened_at": p.opened_at.isoformat(),
            }
            for p in positions
        ])
        for action in actions:
            event = {
                "type": action["action"],
                "symbol": action.get("symbol"),
                "direction": action.get("direction"),
                "level": action.get("level"),
                "lots": action.get("lot_size"),
                "price": action.get("price"),
                "pnl": action.get("pnl"),
                "reason": action.get("reason"),
                "ts": self._last_tick.isoformat(),
            }
            await self._ws.broadcast("signals", event)
            if self._notifier:
                try:
                    await self._notifier.dispatch(event)
                except Exception:  # noqa: BLE001
                    logger.exception("Notifier dispatch failed")
