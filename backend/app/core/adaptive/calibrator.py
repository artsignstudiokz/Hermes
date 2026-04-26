"""AutoCalibrator — weekly parameter recalibration with champion-challenger.

Pipeline:
  1. Pull 90 days of OHLCV per enabled pair (via the active BrokerAdapter).
  2. Walk-forward split (70/30).
  3. Optuna 100 trials on train slice; pick best by penalised score.
  4. Run challenger on out-of-sample.
  5. Compare to current champion. Apply only when:
       score_new > 1.05 · score_current  AND
       max_dd_oos < 1.20 · max_dd_current

If either guard fails, the calibration is logged but `applied=False`.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd
from sqlalchemy import select

from app.core.adaptive.regime import classify_global, classify_pair
from app.core.adaptive.walk_forward import evaluate, run_backtest
from app.core.brokers.base import BrokerAdapter
from app.db.models import CalibrationRun, StrategyConfigRow
from app.db.session import get_sessionmaker

logger = logging.getLogger(__name__)

OHLCV_DAYS = 90
OHLCV_TIMEFRAME = "1h"
OPTUNA_TRIALS = 100
APPLY_SCORE_RATIO = 1.05
APPLY_DD_RATIO = 1.20


@dataclass
class CalibrationOutcome:
    applied: bool
    challenger_score: float
    champion_score: float
    regime: str
    challenger_params: dict
    champion_params: dict
    walk_forward_summary: dict


def _suggest_params(trial: Any, baseline: dict) -> dict:
    """Optuna search space — tuned around the active config rather than zero."""
    return {
        **baseline,
        "base_grid_distance_pips": trial.suggest_float(
            "base_grid_distance_pips", 15.0, 60.0, step=2.5,
        ),
        "grid_distance_multiplier": trial.suggest_float(
            "grid_distance_multiplier", 1.1, 1.8, step=0.05,
        ),
        "lot_multiplier": trial.suggest_float("lot_multiplier", 1.05, 1.7, step=0.05),
        "max_grid_levels": trial.suggest_int("max_grid_levels", 3, 9),
        "fix_take_profit_pct": trial.suggest_float(
            "fix_take_profit_pct", 1.0, 4.0, step=0.1,
        ),
        "stop_drawdown_pct": trial.suggest_float(
            "stop_drawdown_pct", 5.0, 20.0, step=0.5,
        ),
    }


async def fetch_data(
    adapter: BrokerAdapter, symbols: list[str], days: int = OHLCV_DAYS,
) -> dict[str, pd.DataFrame]:
    bars = max(200, int(days * 24))   # 1h timeframe → ~24 bars/day
    out: dict[str, pd.DataFrame] = {}
    for s in symbols:
        try:
            out[s] = await adapter.get_ohlcv(s, OHLCV_TIMEFRAME, bars)
        except Exception:
            logger.exception("OHLCV fetch failed for %s", s)
    return out


def detect_regime(data: dict[str, pd.DataFrame]) -> str:
    per_pair = [classify_pair(s, df) for s, df in data.items()]
    g = classify_global(per_pair)
    return g.regime


async def run_calibration(
    adapter: BrokerAdapter,
    base_params: dict,
    symbols: list[str],
    *,
    n_trials: int = OPTUNA_TRIALS,
    initial_equity: float = 10_000.0,
    progress: "callable[[dict], None] | None" = None,
) -> CalibrationOutcome:
    """Top-level entry — fetches data, runs Optuna, applies champion-challenger."""
    if progress:
        progress({"stage": "fetch_data", "pct": 0.0})
    data = await fetch_data(adapter, symbols)
    if not data:
        raise RuntimeError("No OHLCV data available for calibration")

    if progress:
        progress({"stage": "regime", "pct": 5.0})
    regime = detect_regime(data)

    # Optuna search on the in-sample slice.
    # We do `await asyncio.to_thread` because Optuna is sync and CPU-bound.
    if progress:
        progress({"stage": "optuna", "pct": 10.0})

    def _optuna() -> dict:
        import optuna
        from app.core.adaptive.walk_forward import split_data

        train, _test = split_data(data, train_ratio=0.7)

        def objective(trial: Any) -> float:
            params = _suggest_params(trial, base_params)
            metrics = run_backtest(train, params, initial_equity)
            sharpe = float(metrics.get("sharpe_ratio") or -10)
            return -sharpe   # Optuna minimises by default

        sampler = optuna.samplers.TPESampler(seed=42)
        study = optuna.create_study(direction="minimize", sampler=sampler)

        def cb(study_, trial_) -> None:
            if progress:
                pct = 10.0 + 70.0 * (trial_.number / max(1, n_trials))
                progress({
                    "stage": "optuna",
                    "pct": pct,
                    "trial": trial_.number,
                    "best_value": -study_.best_value if study_.best_trial else None,
                })

        study.optimize(objective, n_trials=n_trials, callbacks=[cb], show_progress_bar=False)
        best = {**base_params, **study.best_params}
        return best

    challenger = await asyncio.to_thread(_optuna)

    # Walk-forward check.
    if progress:
        progress({"stage": "walk_forward", "pct": 85.0})
    challenger_eval = await asyncio.to_thread(
        evaluate, data, challenger, initial_equity,
    )
    champion_eval = await asyncio.to_thread(
        evaluate, data, base_params, initial_equity,
    )

    apply_ok = (
        challenger_eval.valid
        and challenger_eval.score > APPLY_SCORE_RATIO * max(champion_eval.score, 0.01)
        and abs(challenger_eval.oos_max_dd_pct)
            < APPLY_DD_RATIO * max(abs(champion_eval.oos_max_dd_pct), 0.5)
    )

    summary = {
        "challenger": {
            "is_sharpe": challenger_eval.is_sharpe,
            "oos_sharpe": challenger_eval.oos_sharpe,
            "oos_max_dd_pct": challenger_eval.oos_max_dd_pct,
            "oos_trades": challenger_eval.oos_trades,
        },
        "champion": {
            "is_sharpe": champion_eval.is_sharpe,
            "oos_sharpe": champion_eval.oos_sharpe,
            "oos_max_dd_pct": champion_eval.oos_max_dd_pct,
            "oos_trades": champion_eval.oos_trades,
        },
    }

    if progress:
        progress({"stage": "done", "pct": 100.0, "applied": apply_ok})

    # Persist a CalibrationRun row + flip the active StrategyConfig if won.
    sm = get_sessionmaker()
    async with sm() as session:
        run = CalibrationRun(
            ts=datetime.now(timezone.utc),
            regime=regime,
            before_params=base_params,
            after_params=challenger,
            walk_forward_score=challenger_eval.score,
            challenger_won=apply_ok,
            applied=apply_ok,
        )
        session.add(run)
        if apply_ok:
            current = (await session.execute(
                select(StrategyConfigRow).where(StrategyConfigRow.is_active.is_(True)),
            )).scalars().all()
            parent_id = current[0].id if current else None
            for c in current:
                c.is_active = False
            session.add(StrategyConfigRow(
                name=f"Auto · {datetime.now(timezone.utc).date().isoformat()}",
                payload=challenger,
                is_active=True,
                source="auto_calibrator",
                parent_id=parent_id,
            ))
        await session.commit()

    return CalibrationOutcome(
        applied=apply_ok,
        challenger_score=challenger_eval.score,
        champion_score=champion_eval.score,
        regime=regime,
        challenger_params=challenger,
        champion_params=base_params,
        walk_forward_summary=summary,
    )


async def rollback_to_parent() -> bool:
    """Restore the previous active StrategyConfig (parent_id link)."""
    sm = get_sessionmaker()
    async with sm() as session:
        current = (await session.execute(
            select(StrategyConfigRow).where(StrategyConfigRow.is_active.is_(True)),
        )).scalar_one_or_none()
        if not current or current.parent_id is None:
            return False
        parent = await session.get(StrategyConfigRow, current.parent_id)
        if not parent:
            return False
        current.is_active = False
        parent.is_active = True
        await session.commit()
        return True
