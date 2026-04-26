"""OptimizeService — Optuna runs with live trial-by-trial WS broadcast."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.api.ws.manager import get_ws_manager
from app.core.adaptive.walk_forward import run_backtest
from app.core.brokers.registry import BrokerRegistry
from app.db.models import BacktestRun, StrategyConfigRow
from app.db.session import get_sessionmaker

logger = logging.getLogger(__name__)


class OptimizeService:
    def __init__(self, registry: BrokerRegistry) -> None:
        self._registry = registry
        self._ws = get_ws_manager()
        self._tasks: dict[int, asyncio.Task] = {}

    async def submit(
        self, base_params: dict, symbols: list[str], n_trials: int, days: int,
    ) -> int:
        """Reuses BacktestRun table for runs, with status='optimize'."""
        sm = get_sessionmaker()
        async with sm() as session:
            row = BacktestRun(
                params={**base_params, "symbols": symbols, "n_trials": n_trials, "days": days, "kind": "optimize"},
                status="pending",
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            run_id = row.id

        task = asyncio.create_task(self._run(run_id, base_params, symbols, n_trials, days))
        self._tasks[run_id] = task
        return run_id

    async def apply_best(self, run_id: int) -> dict:
        sm = get_sessionmaker()
        async with sm() as session:
            row = await session.get(BacktestRun, run_id)
            if row is None or not row.metrics:
                raise ValueError("Run not found or not finished")
            best = row.metrics.get("best_params")
            if not best:
                raise ValueError("No best params on run")

            current = (await session.execute(
                select(StrategyConfigRow).where(StrategyConfigRow.is_active.is_(True)),
            )).scalars().all()
            parent_id = current[0].id if current else None
            for c in current:
                c.is_active = False

            new_row = StrategyConfigRow(
                name=f"Optimizer · run #{run_id}",
                payload=best,
                is_active=True,
                source="optimizer",
                parent_id=parent_id,
            )
            session.add(new_row)
            await session.commit()
            await session.refresh(new_row)
            return {"id": new_row.id, "name": new_row.name, "payload": best}

    async def _run(
        self,
        run_id: int,
        base_params: dict,
        symbols: list[str],
        n_trials: int,
        days: int,
    ) -> None:
        sm = get_sessionmaker()
        topic = f"optimize_{run_id}"
        await self._ws.broadcast(topic, {"type": "started", "run_id": run_id})

        try:
            adapter = self._registry.get_active()
            if adapter is None:
                raise RuntimeError("No active broker")

            data = {}
            for s in symbols:
                try:
                    data[s] = await adapter.get_ohlcv(s, "1h", max(200, days * 24))
                except Exception:
                    logger.exception("OHLCV %s failed", s)
            if not data:
                raise RuntimeError("No data fetched")

            best_params, best_value, trials = await asyncio.to_thread(
                self._optuna_loop, data, base_params, n_trials, run_id, topic,
            )

            async with sm() as session:
                row = await session.get(BacktestRun, run_id)
                if row:
                    row.status = "done"
                    row.metrics = {
                        "best_value": best_value,
                        "best_params": best_params,
                        "trials": trials[-50:],     # cap for size
                    }
                    row.finished_at = datetime.now(timezone.utc)
                    await session.commit()

            await self._ws.broadcast(topic, {
                "type": "complete",
                "run_id": run_id,
                "best_value": best_value,
                "best_params": best_params,
            })
        except Exception as e:  # noqa: BLE001
            logger.exception("Optimize run %d failed", run_id)
            async with sm() as session:
                row = await session.get(BacktestRun, run_id)
                if row:
                    row.status = "error"
                    row.metrics = {"error": str(e)}
                    row.finished_at = datetime.now(timezone.utc)
                    await session.commit()
            await self._ws.broadcast(topic, {"type": "error", "message": str(e)})
        finally:
            self._tasks.pop(run_id, None)

    def _optuna_loop(
        self, data, base_params, n_trials, run_id, topic,
    ) -> tuple[dict, float, list[dict]]:
        import optuna

        trials_log: list[dict] = []

        def objective(trial):
            params = {
                **base_params,
                "base_grid_distance_pips": trial.suggest_float("base_grid_distance_pips", 15.0, 60.0, step=2.5),
                "grid_distance_multiplier": trial.suggest_float("grid_distance_multiplier", 1.1, 1.8, step=0.05),
                "lot_multiplier": trial.suggest_float("lot_multiplier", 1.05, 1.7, step=0.05),
                "max_grid_levels": trial.suggest_int("max_grid_levels", 3, 9),
                "fix_take_profit_pct": trial.suggest_float("fix_take_profit_pct", 1.0, 4.0, step=0.1),
                "stop_drawdown_pct": trial.suggest_float("stop_drawdown_pct", 5.0, 20.0, step=0.5),
            }
            metrics = run_backtest(data, params, 10_000.0)
            sharpe = float(metrics.get("sharpe_ratio") or -10)
            return -sharpe

        sampler = optuna.samplers.TPESampler(seed=42)
        study = optuna.create_study(direction="minimize", sampler=sampler)

        def cb(_, trial):
            entry = {
                "trial": trial.number,
                "value": -trial.value if trial.value is not None else None,
                "params": dict(trial.params),
            }
            trials_log.append(entry)
            try:
                import asyncio as _aio
                _aio.run_coroutine_threadsafe(
                    self._ws.broadcast(topic, {"type": "trial", **entry}),
                    _aio.get_event_loop_policy().get_event_loop(),
                )
            except Exception:
                pass

        study.optimize(objective, n_trials=n_trials, callbacks=[cb], show_progress_bar=False)
        return {**base_params, **study.best_params}, -study.best_value, trials_log


_service: OptimizeService | None = None


def init_optimize_service(registry: BrokerRegistry) -> OptimizeService:
    global _service
    _service = OptimizeService(registry)
    return _service


def get_optimize_service() -> OptimizeService:
    if _service is None:
        raise RuntimeError("OptimizeService not initialised")
    return _service
