"""Bar-by-bar backtest for the explainable ensemble.

Walks the historical OHLCV for one or more symbols, feeds each new bar
to IndicatorPanel + StrategyEnsemble, and simulates entries/exits the
same way the live worker would:

  - One position per symbol at a time (entry_lock equivalent).
  - Broker-side SL/TP at 2×ATR / 4×ATR (1:2 R/R) - exits when the
    bar's high/low touches the level.
  - Risk-based sizing: 1% of running equity per trade, computed from
    SL distance, mirroring TradingWorker._maybe_enter live behaviour.
  - Per-mode confidence floor: 0.7 proven, 0.5 autonomous.
  - Daily cap of 3 trades.

Returns a metrics dict consumable by BacktestService - same keys as
the legacy engine: total_return, sharpe_ratio, max_drawdown, win_rate,
profit_factor, trade_count, plus equity_curve.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from app.core.strategy.indicators import IndicatorPanel
from app.core.strategy.signals import StrategyEnsemble, build_ensemble

logger = logging.getLogger(__name__)


# Each indicator needs at least this many bars of history before we
# trust it (EMA-200 stabilises around bar 200, ADX around bar 28, etc).
WARMUP_BARS = 220
DAILY_TRADE_CAP = 3
MAX_OPEN_POSITIONS = 5


@dataclass
class _SimPosition:
    symbol: str
    direction: str          # "long" | "short"
    entry_ts: pd.Timestamp
    entry_price: float
    sl: float
    tp: float
    lot: float              # in standard lots (100k units of base)
    reason: str
    confidence: float


@dataclass
class _SimResult:
    closed_trades: list[dict] = field(default_factory=list)
    equity_curve: list[tuple[pd.Timestamp, float]] = field(default_factory=list)


# Pip-value approximation per 1 standard lot, account currency = USD.
# Good enough for FX majors and metals. Crypto handled separately
# below.  Each unit move in price corresponds to `contract_size` of the
# quote currency.  The risk math:
#   risk_dollars = (entry - sl) * lot * contract_size  (long)
#   solve for lot to hit target risk pct of equity.
_DEFAULT_CONTRACT_SIZE = 100_000.0     # FX
_METALS = {"XAUUSD", "XAGUSD"}
_METALS_CONTRACT_SIZE = 100.0
_CRYPTO_HINTS = ("BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE")
_CRYPTO_CONTRACT_SIZE = 1.0


def _contract_size(symbol: str) -> float:
    if symbol in _METALS:
        return _METALS_CONTRACT_SIZE
    if any(symbol.startswith(p) or symbol.endswith(p) for p in _CRYPTO_HINTS):
        return _CRYPTO_CONTRACT_SIZE
    return _DEFAULT_CONTRACT_SIZE


def _sized_lot(
    equity: float, entry: float, sl: float, symbol: str, risk_pct: float,
) -> float:
    """Return lot size that risks ~risk_pct% of equity if SL fires."""
    distance = abs(entry - sl)
    if distance <= 0 or equity <= 0:
        return 0.01
    risk_dollars = equity * risk_pct / 100.0
    contract = _contract_size(symbol)
    # money risked per 1 lot = distance × contract_size (USD-quoted).
    # For JPY-quoted (USDJPY, EURJPY) one would divide by USDJPY rate,
    # but at the precision we need for a presentation backtest this is
    # close enough and consistent across replays.
    risk_per_lot = distance * contract
    if risk_per_lot <= 0:
        return 0.01
    raw = risk_dollars / risk_per_lot
    return max(0.01, round(raw, 2))


def _pnl(
    direction: str, entry: float, exit_price: float, lot: float, symbol: str,
) -> float:
    """Realised P&L for a closed position in account currency (USD)."""
    contract = _contract_size(symbol)
    if direction == "long":
        return (exit_price - entry) * lot * contract
    return (entry - exit_price) * lot * contract


def _confidence_floor(mode: str) -> float:
    return {"proven": 0.7, "autonomous": 0.5}.get(mode, 0.5)


def _ensemble_for_mode(mode: str, params: dict) -> StrategyEnsemble:
    """Pick the same ensemble the live worker would use for `mode`."""
    if mode == "proven":
        # The proven mode runs only TrendFollowing with an "any" merge -
        # same as TradingWorker.set_mode("proven").
        return build_ensemble(["trend"], mode="any")
    # Autonomous: respect the strategy config if it explicitly sets
    # `ensemble`, otherwise default to the v1.0.22-validated pair.
    names = params.get("ensemble") or ["trend", "momentum"]
    return build_ensemble(names, mode=params.get("ensemble_mode") or "majority")


def run_ensemble_backtest(
    data: dict[str, pd.DataFrame],
    mode: str = "proven",
    params: dict | None = None,
    initial_equity: float = 10_000.0,
    risk_pct: float = 1.0,
) -> dict:
    """Replay history bar-by-bar through the live signal ensemble.

    `data` maps each symbol to a pandas DataFrame with the columns
    `open, high, low, close, volume` indexed by UTC timestamp - the
    same shape `MT5Adapter.get_ohlcv` returns.
    """
    params = params or {}
    ensemble = _ensemble_for_mode(mode, params)
    panel = IndicatorPanel()
    threshold = _confidence_floor(mode)

    symbols = list(data.keys())
    if not symbols:
        return {
            "total_return": 0.0, "sharpe_ratio": 0.0, "max_drawdown": 0.0,
            "win_rate": 0.0, "profit_factor": 0.0, "trade_count": 0,
            "error": "no data",
        }

    # Build a union of all timestamps. The replay clock moves through
    # the union; each tick we evaluate every symbol that has a bar at
    # that time. That keeps multi-symbol replay deterministic without
    # forcing all DataFrames to share the same index.
    all_ts = sorted(set().union(*[df.index for df in data.values()]))
    if len(all_ts) < WARMUP_BARS + 50:
        return {
            "total_return": 0.0, "sharpe_ratio": 0.0, "max_drawdown": 0.0,
            "win_rate": 0.0, "profit_factor": 0.0, "trade_count": 0,
            "error": f"need at least {WARMUP_BARS + 50} bars, got {len(all_ts)}",
        }

    equity = initial_equity
    peak_equity = equity
    max_dd = 0.0
    open_pos: dict[str, _SimPosition] = {}
    closed: list[dict] = []
    equity_curve: list[tuple[pd.Timestamp, float]] = [(all_ts[0], equity)]
    trades_by_day: dict[str, int] = {}

    for ts in all_ts[WARMUP_BARS:]:
        day_key = ts.strftime("%Y-%m-%d")
        # ── Exit pass: walk every open position and check if THIS
        # bar's high/low triggered its SL or TP. SL has priority over
        # TP in adverse intra-bar moves (conservative - assume the
        # worst when both touched in one bar).
        to_close = []
        for sym, pos in open_pos.items():
            df = data.get(sym)
            if df is None or ts not in df.index:
                continue
            bar = df.loc[ts]
            high, low = float(bar["high"]), float(bar["low"])
            exit_price: float | None = None
            trigger: str = ""
            if pos.direction == "long":
                if low <= pos.sl:
                    exit_price, trigger = pos.sl, "sl"
                elif high >= pos.tp:
                    exit_price, trigger = pos.tp, "tp"
            else:   # short
                if high >= pos.sl:
                    exit_price, trigger = pos.sl, "sl"
                elif low <= pos.tp:
                    exit_price, trigger = pos.tp, "tp"
            if exit_price is None:
                continue
            realised = _pnl(pos.direction, pos.entry_price, exit_price, pos.lot, pos.symbol)
            equity += realised
            closed.append({
                "symbol": pos.symbol,
                "direction": pos.direction,
                "entry_ts": pos.entry_ts.isoformat(),
                "exit_ts": ts.isoformat(),
                "entry_price": pos.entry_price,
                "exit_price": exit_price,
                "lot": pos.lot,
                "sl": pos.sl,
                "tp": pos.tp,
                "trigger": trigger,
                "pnl": realised,
                "reason": pos.reason,
                "confidence": pos.confidence,
            })
            to_close.append(sym)
        for sym in to_close:
            del open_pos[sym]

        # ── Entry pass: per-symbol signal + entry if we still have a
        # daily quota and no open position on that symbol.
        if trades_by_day.get(day_key, 0) >= DAILY_TRADE_CAP:
            equity_curve.append((ts, equity))
            continue
        if len(open_pos) >= MAX_OPEN_POSITIONS:
            equity_curve.append((ts, equity))
            continue

        candidates: list[tuple[float, str, "SignalReport"]] = []  # noqa: F821
        for sym in symbols:
            if sym in open_pos:
                continue
            df = data[sym]
            if ts not in df.index:
                continue
            # Slice up to and INCLUDING the current bar - we evaluate
            # at bar close, identical to the live worker.
            idx_pos = df.index.get_loc(ts)
            if idx_pos < WARMUP_BARS:
                continue
            window = df.iloc[max(0, idx_pos - WARMUP_BARS - 5):idx_pos + 1]
            try:
                snap = panel.compute(sym, window)
                report = ensemble.evaluate(snap)
            except Exception:  # noqa: BLE001
                continue
            if report.direction == "flat" or report.confidence < threshold:
                continue
            candidates.append((report.confidence, sym, report))

        if candidates:
            candidates.sort(reverse=True)
            best_conf, sym, report = candidates[0]
            df = data[sym]
            bar = df.loc[ts]
            entry_price = float(bar["close"])
            snap = panel.compute(
                sym, df.iloc[max(0, df.index.get_loc(ts) - WARMUP_BARS - 5):df.index.get_loc(ts) + 1],
            )
            atr = float(snap.atr or 0.0)
            if atr <= 0:
                equity_curve.append((ts, equity))
                continue
            if report.direction == "long":
                sl, tp = entry_price - 2 * atr, entry_price + 4 * atr
            else:
                sl, tp = entry_price + 2 * atr, entry_price - 4 * atr
            lot = _sized_lot(equity, entry_price, sl, sym, risk_pct)
            open_pos[sym] = _SimPosition(
                symbol=sym, direction=report.direction,
                entry_ts=ts, entry_price=entry_price,
                sl=sl, tp=tp, lot=lot,
                reason=report.reason, confidence=report.confidence,
            )
            trades_by_day[day_key] = trades_by_day.get(day_key, 0) + 1

        # Track drawdown using equity + open-position float to be
        # honest about unrealised exposure.
        floating = sum(
            _pnl(p.direction, p.entry_price, float(data[p.symbol].loc[ts, "close"]),
                 p.lot, p.symbol)
            for p in open_pos.values()
            if ts in data[p.symbol].index
        )
        mark_to_market = equity + floating
        peak_equity = max(peak_equity, mark_to_market)
        dd = (peak_equity - mark_to_market) / peak_equity if peak_equity > 0 else 0
        max_dd = max(max_dd, dd)
        equity_curve.append((ts, mark_to_market))

    # ── Metrics ──────────────────────────────────────────────────────
    n = len(closed)
    wins = [t for t in closed if t["pnl"] > 0]
    losses = [t for t in closed if t["pnl"] <= 0]
    total_pnl = sum(t["pnl"] for t in closed)
    total_return = (total_pnl / initial_equity) if initial_equity > 0 else 0.0
    win_rate = (len(wins) / n) if n else 0.0
    gross_win = sum(t["pnl"] for t in wins)
    gross_loss = -sum(t["pnl"] for t in losses)
    profit_factor = (gross_win / gross_loss) if gross_loss > 0 else (math.inf if wins else 0.0)
    if profit_factor == math.inf:
        profit_factor = 99.0   # keep the JSON encoder happy

    # Sharpe from per-trade returns relative to equity at entry. Simple
    # but a fair "is this profitable consistently" metric for a
    # presentation backtest.
    rets = [t["pnl"] / initial_equity for t in closed]
    if len(rets) >= 2:
        mean_ret = float(np.mean(rets))
        std_ret = float(np.std(rets, ddof=1))
        sharpe = (mean_ret / std_ret) * math.sqrt(252) if std_ret > 0 else 0.0
    else:
        sharpe = 0.0

    eq_series = pd.Series(
        [v for _, v in equity_curve],
        index=pd.to_datetime([t for t, _ in equity_curve], utc=True),
        name="equity",
    )

    return {
        "total_return": float(total_return),
        "sharpe_ratio": float(sharpe),
        "max_drawdown": float(max_dd),
        "max_drawdown_pct": float(max_dd * 100),
        "win_rate": float(win_rate),
        "profit_factor": float(profit_factor),
        "trade_count": int(n),
        "total_pnl": float(total_pnl),
        "wins": int(len(wins)),
        "losses": int(len(losses)),
        "avg_win": float(np.mean([t["pnl"] for t in wins])) if wins else 0.0,
        "avg_loss": float(np.mean([t["pnl"] for t in losses])) if losses else 0.0,
        "initial_equity": float(initial_equity),
        "final_equity": float(initial_equity + total_pnl),
        "mode": mode,
        "symbols": list(symbols),
        "trades": closed,
        "equity_curve": eq_series,
    }
