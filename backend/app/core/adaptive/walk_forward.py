"""Walk-forward validation for strategy parameter tuning.

Splits each pair's history into a train and a held-out test slice. Optuna
explores parameters on the train slice; we then score the survivor on the
test slice. The combined score penalises in/out divergence to discourage
overfitting:

    score = sharpe_oos − 0.5 · |sharpe_is − sharpe_oos|

Caller passes a pre-built data dict {symbol → DataFrame}; we don't fetch
data here, that's the AutoCalibrator's responsibility.
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

LEGACY_DIR = Path(__file__).resolve().parents[3].parent / "legacy"
if LEGACY_DIR.exists() and str(LEGACY_DIR) not in sys.path:
    sys.path.insert(0, str(LEGACY_DIR))


@dataclass(frozen=True)
class WalkForwardResult:
    is_metrics: dict           # in-sample metrics from BacktestEngine
    oos_metrics: dict          # out-of-sample metrics
    is_sharpe: float
    oos_sharpe: float
    oos_max_dd_pct: float
    oos_trades: int
    score: float               # composite, see module docstring
    valid: bool                # passes minimum-trade filter


MIN_OOS_TRADES = 50            # below this, results aren't trustworthy


def _import_legacy():
    from config import GridConfig  # type: ignore[import-not-found]
    from backtester import BacktestEngine, AppConfig  # type: ignore[import-not-found]
    return GridConfig, BacktestEngine, AppConfig


def split_data(
    data: dict[str, pd.DataFrame], train_ratio: float = 0.7,
) -> tuple[dict[str, pd.DataFrame], dict[str, pd.DataFrame]]:
    train: dict[str, pd.DataFrame] = {}
    test: dict[str, pd.DataFrame] = {}
    for sym, df in data.items():
        cut = int(len(df) * train_ratio)
        if cut < 100 or len(df) - cut < 50:
            logger.warning("Skipping %s — not enough bars for split", sym)
            continue
        train[sym] = df.iloc[:cut]
        test[sym] = df.iloc[cut:]
    return train, test


def run_backtest(
    data: dict[str, pd.DataFrame],
    params: dict,
    initial_equity: float = 10_000.0,
) -> dict:
    """Run a single backtest via the legacy BacktestEngine. Returns metrics dict."""
    GridConfig, BacktestEngine, AppConfig = _import_legacy()

    cfg = AppConfig()
    cfg.backtest.initial_equity = initial_equity
    cfg.backtest.timeframe = "1h"
    grid = GridConfig()
    for k, v in params.items():
        if hasattr(grid, k):
            setattr(grid, k, v)
    grid.__post_init__()
    cfg.grid = grid

    engine = BacktestEngine(cfg)
    result = engine.run(data)

    # Best-effort metric extraction; legacy reporter exposes a dict-like result.
    metrics: dict = {}
    if hasattr(result, "metrics"):
        metrics = dict(result.metrics)
    elif isinstance(result, dict):
        metrics = result
    else:
        # Fallback: pull common attrs.
        for key in ("total_return", "sharpe_ratio", "max_drawdown", "calmar_ratio",
                    "profit_factor", "trade_count", "win_rate"):
            if hasattr(result, key):
                metrics[key] = getattr(result, key)
    return metrics


def evaluate(
    data: dict[str, pd.DataFrame],
    params: dict,
    initial_equity: float = 10_000.0,
) -> WalkForwardResult:
    train, test = split_data(data, train_ratio=0.7)
    if not train or not test:
        return WalkForwardResult({}, {}, 0.0, 0.0, 0.0, 0, -1e9, valid=False)

    is_m = run_backtest(train, params, initial_equity)
    oos_m = run_backtest(test, params, initial_equity)

    is_sharpe = float(is_m.get("sharpe_ratio") or 0.0)
    oos_sharpe = float(oos_m.get("sharpe_ratio") or 0.0)
    oos_dd = float(oos_m.get("max_drawdown") or oos_m.get("max_drawdown_pct") or 0.0)
    oos_trades = int(oos_m.get("trade_count") or 0)
    valid = oos_trades >= MIN_OOS_TRADES
    score = oos_sharpe - 0.5 * abs(is_sharpe - oos_sharpe)
    return WalkForwardResult(
        is_metrics=is_m,
        oos_metrics=oos_m,
        is_sharpe=is_sharpe,
        oos_sharpe=oos_sharpe,
        oos_max_dd_pct=oos_dd,
        oos_trades=oos_trades,
        score=score,
        valid=valid,
    )
