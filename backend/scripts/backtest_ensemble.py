"""Walk-forward backtest of the v1.0.21 indicator ensemble.

Goal: prove (or disprove) that the four bundled strategies — Trend
Following, Mean Reversion, Breakout, Momentum — and the majority-
voting ensemble produce a positive expectancy on representative
historical data. If a strategy posts a negative Sharpe, we know the
defaults are wrong before any user trusts them.

Method:
  1. Generate a 12-month, multi-regime OHLCV fixture per symbol:
     3 months trending up + 3 months ranging + 3 months volatile +
     3 months trending down. This is the lab — clean, deterministic.
  2. For each strategy, walk bar-by-bar: evaluate the snapshot, open
     a 0.01-lot position on a non-flat signal, close on the next
     opposite signal OR after 24 bars (1 day max holding) OR on a
     1% adverse move.
  3. Track equity, drawdown, win-rate. Compute Sharpe (annualised
     from hourly bars), profit factor, max DD, win rate, trade count.
  4. Repeat for the ensemble (Trend + MeanRev + Breakout + Momentum,
     majority vote) on the same data.

Run from backend/ via:  python scripts/backtest_ensemble.py
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.strategy.indicators import IndicatorPanel
from app.core.strategy.signals import (
    BreakoutStrategy,
    MeanReversionStrategy,
    MomentumStrategy,
    StrategyEnsemble,
    TrendFollowingStrategy,
)


# ── Synthetic data generation ────────────────────────────────────────


def _trending_segment(n: int, drift: float, vol: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return np.cumsum(rng.normal(drift, vol, n))


def _ranging_segment(n: int, mean: float, amplitude: float, period: int, vol: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    t = np.arange(n)
    sine = amplitude * np.sin(2 * np.pi * t / period)
    return sine + rng.normal(0, vol, n).cumsum() * 0.1 + mean


def _volatile_segment(n: int, vol: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    # Periods of low and high vol mixed.
    chunks = []
    pos = 0
    while pos < n:
        chunk = rng.integers(40, 100)
        chunk = min(chunk, n - pos)
        local_vol = vol * (1.0 if rng.random() > 0.5 else 3.5)
        chunks.append(rng.normal(0, local_vol, chunk))
        pos += chunk
    return np.cumsum(np.concatenate(chunks)[:n])


def build_fixture(symbol: str, seed: int = 42) -> pd.DataFrame:
    """12 months of 1h bars stitched from 4 regime segments."""
    n_per = 3 * 30 * 24      # 3 months × 30 days × 24 hours = 2160 bars
    base_price = 1.10

    up = _trending_segment(n_per, drift=0.00015, vol=0.001, seed=seed)
    rng = _ranging_segment(n_per, mean=0.0, amplitude=0.015, period=80, vol=0.001, seed=seed + 1)
    vol = _volatile_segment(n_per, vol=0.0015, seed=seed + 2)
    down = _trending_segment(n_per, drift=-0.00012, vol=0.001, seed=seed + 3)

    series = np.concatenate([up, rng + up[-1], vol + (rng + up[-1])[-1], down + (vol + (rng + up[-1])[-1])[-1]])
    series += base_price

    rng_noise = np.random.default_rng(seed + 100)
    high = series + np.abs(rng_noise.normal(0.0005, 0.0002, len(series)))
    low = series - np.abs(rng_noise.normal(0.0005, 0.0002, len(series)))
    open_ = np.concatenate([[series[0]], series[:-1]])
    volume = rng_noise.integers(100, 1000, len(series))

    df = pd.DataFrame({
        "open": open_, "high": high, "low": low, "close": series, "volume": volume,
    })
    df.index = pd.date_range("2025-01-01", periods=len(series), freq="1h")
    df.attrs["symbol"] = symbol
    df.attrs["regime_boundaries"] = [n_per, 2 * n_per, 3 * n_per]
    return df


# ── Walk-forward driver ──────────────────────────────────────────────


@dataclass
class Trade:
    symbol: str
    direction: str
    entry_idx: int
    entry_price: float
    exit_idx: int | None = None
    exit_price: float | None = None
    pnl_pct: float = 0.0     # % move in our favour
    strategy: str = ""

    def close(self, idx: int, price: float):
        self.exit_idx = idx
        self.exit_price = price
        move = (price - self.entry_price) / self.entry_price
        self.pnl_pct = move if self.direction == "long" else -move


@dataclass
class StrategyMetrics:
    name: str
    trades: int
    wins: int
    win_rate: float
    total_return_pct: float
    sharpe: float
    max_dd_pct: float
    profit_factor: float
    avg_trade_pct: float

    def __str__(self) -> str:
        return (
            f"{self.name:24s} | trades={self.trades:4d} | "
            f"win={self.win_rate * 100:5.1f}% | "
            f"return={self.total_return_pct:+7.2f}% | "
            f"Sharpe={self.sharpe:+5.2f} | "
            f"MaxDD={self.max_dd_pct:5.2f}% | "
            f"PF={self.profit_factor:5.2f} | "
            f"avg={self.avg_trade_pct:+5.3f}%"
        )


def simulate(strategy, panel: IndicatorPanel, df: pd.DataFrame, name: str,
             max_hold_bars: int = 24, stop_loss_pct: float = 0.01) -> StrategyMetrics:
    """Walk bar-by-bar, open on signal, close on opposite/time/stop."""
    open_trade: Trade | None = None
    completed: list[Trade] = []
    # Need at least ema_slow_period (200) bars before evaluation makes sense.
    warmup = 220
    for i in range(warmup, len(df)):
        window = df.iloc[: i + 1]
        try:
            snap = panel.compute(df.attrs["symbol"], window)
        except ValueError:
            continue
        sig = strategy.evaluate(snap)
        cur_price = float(df["close"].iloc[i])

        # Manage open trade first.
        if open_trade is not None:
            held = i - open_trade.entry_idx
            adverse = (
                (cur_price - open_trade.entry_price) / open_trade.entry_price
                if open_trade.direction == "long"
                else (open_trade.entry_price - cur_price) / open_trade.entry_price
            )
            time_out = held >= max_hold_bars
            stop_hit = adverse <= -stop_loss_pct
            reverse = sig is not None and sig.direction != "flat" and sig.direction != open_trade.direction
            if time_out or stop_hit or reverse:
                open_trade.close(i, cur_price)
                completed.append(open_trade)
                open_trade = None

        # Open a new trade?
        if open_trade is None and sig is not None and sig.direction in ("long", "short"):
            open_trade = Trade(
                symbol=df.attrs["symbol"], direction=sig.direction,
                entry_idx=i, entry_price=cur_price, strategy=name,
            )

    # Close anything still open at the end.
    if open_trade is not None:
        open_trade.close(len(df) - 1, float(df["close"].iloc[-1]))
        completed.append(open_trade)

    return _metrics(completed, name)


def _metrics(trades: list[Trade], name: str) -> StrategyMetrics:
    if not trades:
        return StrategyMetrics(name, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    pct_returns = np.array([t.pnl_pct for t in trades])
    wins = int((pct_returns > 0).sum())
    win_rate = wins / len(trades)
    total_return = pct_returns.sum() * 100
    avg = pct_returns.mean() * 100
    sharpe = (
        (pct_returns.mean() / pct_returns.std() * np.sqrt(252 * 24))
        if pct_returns.std() > 0 else 0.0
    )
    equity = np.cumprod(1 + pct_returns) - 1
    peak = np.maximum.accumulate(equity)
    drawdown = (peak - equity) / np.where(peak == 0, 1, peak + 1)
    max_dd = drawdown.max() * 100
    gross_gain = pct_returns[pct_returns > 0].sum()
    gross_loss = -pct_returns[pct_returns < 0].sum()
    profit_factor = gross_gain / gross_loss if gross_loss > 0 else float("inf")
    return StrategyMetrics(
        name=name, trades=len(trades), wins=wins, win_rate=win_rate,
        total_return_pct=total_return, sharpe=sharpe, max_dd_pct=max_dd,
        profit_factor=profit_factor, avg_trade_pct=avg,
    )


# ── Main ─────────────────────────────────────────────────────────────


def main() -> int:
    print("=" * 90)
    print("HERMES ENSEMBLE BACKTEST — v1.0.21 strategies vs synthetic 12-month fixture")
    print("=" * 90)
    print()
    print("Fixture: 4 stitched regimes (uptrend -> range -> vol -> downtrend), 8640 hourly bars")
    print("Trade model: 1% stop, 24h max hold, opposite-signal exit, no commission/slippage")
    print()
    print(f"{'Strategy':24s} | {'Trades':6s} | {'Win%':6s} | {'Return':8s} | "
          f"{'Sharpe':6s} | {'MaxDD':6s} | {'PF':5s} | Avg")
    print("-" * 90)

    symbols = ["EURUSD", "GBPUSD", "EURJPY"]
    all_strategies = [
        ("Trend Following", TrendFollowingStrategy(adx_min=22)),
        ("Mean Reversion", MeanReversionStrategy()),
        ("Breakout", BreakoutStrategy()),
        ("Momentum", MomentumStrategy()),
        ("ENSEMBLE v1.0.22 default", StrategyEnsemble(
            [TrendFollowingStrategy(adx_min=22), MomentumStrategy()],
            mode="majority",
        )),
        ("ENSEMBLE (all four)", StrategyEnsemble(
            [TrendFollowingStrategy(adx_min=22), MeanReversionStrategy(),
             BreakoutStrategy(), MomentumStrategy()],
            mode="majority",
        )),
    ]

    aggregated: dict[str, list[StrategyMetrics]] = {n: [] for n, _ in all_strategies}
    for i, sym in enumerate(symbols):
        df = build_fixture(sym, seed=42 + i * 7)
        for name, strat in all_strategies:
            panel = IndicatorPanel()
            m = simulate(strat, panel, df, name)
            aggregated[name].append(m)

    # Aggregate across symbols.
    for name, metrics_list in aggregated.items():
        total_trades = sum(m.trades for m in metrics_list)
        total_wins = sum(m.wins for m in metrics_list)
        win_rate = total_wins / total_trades if total_trades else 0
        total_return = sum(m.total_return_pct for m in metrics_list) / len(metrics_list)
        sharpe = sum(m.sharpe for m in metrics_list) / len(metrics_list)
        max_dd = max(m.max_dd_pct for m in metrics_list)
        pf_values = [m.profit_factor for m in metrics_list if np.isfinite(m.profit_factor)]
        pf = sum(pf_values) / len(pf_values) if pf_values else float("inf")
        avg = sum(m.avg_trade_pct for m in metrics_list) / len(metrics_list)
        summary = StrategyMetrics(
            name=name, trades=total_trades, wins=total_wins, win_rate=win_rate,
            total_return_pct=total_return, sharpe=sharpe, max_dd_pct=max_dd,
            profit_factor=pf, avg_trade_pct=avg,
        )
        print(summary)

    print()
    print("=" * 90)
    print("Interpretation:")
    print("  - Sharpe >= 1.0  = decent, >= 2.0 = strong, < 0 = the strategy loses")
    print("  - Profit Factor  = gross_gain / gross_loss; >1.5 healthy, <1 broken")
    print("  - MaxDD          = worst peak-to-trough drawdown; <10% comfortable")
    print("  - Win rate alone is misleading - trend strategies often <50% but profit")
    print("=" * 90)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
