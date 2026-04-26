"""BacktestService — fire-and-forget backtest runs with WS progress."""

from __future__ import annotations

import asyncio
import gzip
import io
import logging
from datetime import datetime, timezone

import pandas as pd

from app.api.ws.manager import get_ws_manager
from app.core.adaptive.walk_forward import run_backtest
from app.core.brokers.registry import BrokerRegistry
from app.db.models import BacktestRun
from app.db.session import get_sessionmaker

logger = logging.getLogger(__name__)


class BacktestService:
    def __init__(self, registry: BrokerRegistry) -> None:
        self._registry = registry
        self._ws = get_ws_manager()
        self._tasks: dict[int, asyncio.Task] = {}

    async def submit(self, params: dict, symbols: list[str], days: int) -> int:
        """Persist a row, kick off a task, return run_id."""
        sm = get_sessionmaker()
        async with sm() as session:
            row = BacktestRun(params={**params, "symbols": symbols, "days": days}, status="pending")
            session.add(row)
            await session.commit()
            await session.refresh(row)
            run_id = row.id

        task = asyncio.create_task(self._run(run_id, params, symbols, days))
        self._tasks[run_id] = task
        return run_id

    async def _run(self, run_id: int, params: dict, symbols: list[str], days: int) -> None:
        sm = get_sessionmaker()
        ws_topic = f"backtest_{run_id}"
        await self._broadcast(ws_topic, {"type": "started", "run_id": run_id})

        async with sm() as session:
            row = await session.get(BacktestRun, run_id)
            if row:
                row.status = "running"
                row.started_at = datetime.now(timezone.utc)
                await session.commit()

        try:
            adapter = self._registry.get_active()
            if adapter is None:
                raise RuntimeError("No active broker — connect one first")

            await self._broadcast(ws_topic, {"type": "progress", "stage": "fetching", "pct": 5})
            data = {}
            for i, s in enumerate(symbols):
                try:
                    data[s] = await adapter.get_ohlcv(s, "1h", max(200, days * 24))
                except Exception:  # noqa: BLE001
                    logger.exception("OHLCV %s failed", s)
                pct = 5 + (35 * (i + 1) / max(1, len(symbols)))
                await self._broadcast(ws_topic, {
                    "type": "progress", "stage": "fetching", "pct": pct, "symbol": s,
                })

            if not data:
                raise RuntimeError("No data fetched — backtest aborted")

            await self._broadcast(ws_topic, {"type": "progress", "stage": "running", "pct": 50})
            metrics = await asyncio.to_thread(run_backtest, data, params, 10_000.0)
            await self._broadcast(ws_topic, {"type": "progress", "stage": "running", "pct": 95})

            equity_series = metrics.pop("equity_curve", None)
            equity_blob = self._gzip_csv(equity_series) if equity_series is not None else None

            async with sm() as session:
                row = await session.get(BacktestRun, run_id)
                if row:
                    row.status = "done"
                    row.metrics = {k: _jsonable(v) for k, v in metrics.items()}
                    row.equity_blob = equity_blob
                    row.finished_at = datetime.now(timezone.utc)
                    await session.commit()

            await self._broadcast(ws_topic, {
                "type": "complete", "run_id": run_id, "metrics": {k: _jsonable(v) for k, v in metrics.items()},
            })
        except Exception as e:  # noqa: BLE001
            logger.exception("Backtest %d failed", run_id)
            async with sm() as session:
                row = await session.get(BacktestRun, run_id)
                if row:
                    row.status = "error"
                    row.metrics = {"error": str(e)}
                    row.finished_at = datetime.now(timezone.utc)
                    await session.commit()
            await self._broadcast(ws_topic, {"type": "error", "message": str(e)})
        finally:
            self._tasks.pop(run_id, None)

    async def _broadcast(self, topic: str, payload: dict) -> None:
        # Reuse the generic ws manager — clients subscribe to /ws/<topic>.
        await self._ws.broadcast(topic, payload)

    @staticmethod
    def _gzip_csv(series: pd.Series | pd.DataFrame) -> bytes:
        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb") as f:
            if isinstance(series, pd.Series):
                series.to_csv(f)  # type: ignore[arg-type]
            else:
                series.to_csv(f)  # type: ignore[arg-type]
        return buf.getvalue()


def _jsonable(value):
    if isinstance(value, (int, float, str, bool, type(None))):
        return value
    try:
        return float(value)
    except Exception:
        return str(value)


_service: BacktestService | None = None


def init_backtest_service(registry: BrokerRegistry) -> BacktestService:
    global _service
    _service = BacktestService(registry)
    return _service


def get_backtest_service() -> BacktestService:
    if _service is None:
        raise RuntimeError("BacktestService not initialised")
    return _service
