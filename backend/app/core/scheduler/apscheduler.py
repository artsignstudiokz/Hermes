"""APScheduler bootstrap — weekly auto-calibration + heartbeat broadcast."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

from app.api.ws.manager import get_ws_manager
from app.core.adaptive.calibrator import run_calibration
from app.core.brokers.registry import BrokerRegistry
from app.db.models import StrategyConfigRow
from app.db.session import get_sessionmaker

logger = logging.getLogger(__name__)


class HermesScheduler:
    def __init__(self, registry: BrokerRegistry) -> None:
        self._registry = registry
        self._scheduler = AsyncIOScheduler()
        self._ws = get_ws_manager()

    def start(self) -> None:
        # Weekly recalibration: Sunday 03:00 local.
        self._scheduler.add_job(
            self._weekly_calibrate,
            CronTrigger(day_of_week="sun", hour=3, minute=0),
            id="auto_calibrate",
            replace_existing=True,
        )
        # Heartbeat: every 5 minutes broadcast that we're alive.
        self._scheduler.add_job(
            self._heartbeat,
            IntervalTrigger(minutes=5),
            id="heartbeat",
            replace_existing=True,
        )
        self._scheduler.start()
        logger.info("Hermes scheduler started")

    def shutdown(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)

    async def _heartbeat(self) -> None:
        await self._ws.broadcast("system", {
            "type": "heartbeat",
            "ts": datetime.now(timezone.utc).isoformat(),
        })

    async def _weekly_calibrate(self) -> None:
        adapter = self._registry.get_active()
        if adapter is None:
            logger.info("Skipping auto-calibration — no active broker")
            return

        sm = get_sessionmaker()
        async with sm() as session:
            cfg = (await session.execute(
                select(StrategyConfigRow).where(StrategyConfigRow.is_active.is_(True)).limit(1),
            )).scalar_one_or_none()

        if cfg is None or not cfg.payload.get("auto_calibrate"):
            logger.info("Skipping auto-calibration — not in Auto preset")
            return

        symbols = cfg.payload.get("symbols") or [
            "EURUSD", "GBPUSD", "EURCHF", "EURJPY", "USDCHF", "USDJPY",
        ]
        logger.info("Weekly auto-calibration starting (%d symbols)", len(symbols))

        async def _progress(p: dict) -> None:
            await self._ws.broadcast("calibration", p)

        def _sync_progress(p: dict) -> None:
            import asyncio

            try:
                asyncio.create_task(_progress(p))
            except RuntimeError:
                pass

        try:
            outcome = await run_calibration(
                adapter, cfg.payload, symbols, progress=_sync_progress,
            )
            await self._ws.broadcast("calibration", {
                "type": "complete",
                "applied": outcome.applied,
                "score": outcome.challenger_score,
                "regime": outcome.regime,
            })
        except Exception:  # noqa: BLE001
            logger.exception("Auto-calibration failed")


_scheduler: HermesScheduler | None = None


def init_scheduler(registry: BrokerRegistry) -> HermesScheduler:
    global _scheduler
    _scheduler = HermesScheduler(registry)
    _scheduler.start()
    return _scheduler


def get_scheduler() -> HermesScheduler:
    if _scheduler is None:
        raise RuntimeError("Scheduler not initialised")
    return _scheduler
