"""Market regime detector — classifies each pair into trend / flat / high_vol.

Used for two purposes:
  1. Live overlay: when in Auto preset, regime tweaks parameters (flat → tighter
     grid + larger TP; high_vol → pause new entries until normalised).
  2. Status display in the UI (RegimeBadge per pair on Dashboard).

Indicators used:
  * ADX(14) — trend strength
  * ATR(14) as a percentage of price — volatility
  * EMA50 vs EMA200 alignment — trend confirmation
  * Hurst exponent (optional, scipy-based) — persistence

Global regime is a majority vote across enabled pairs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

Regime = Literal["trend", "flat", "high_vol"]


@dataclass(frozen=True)
class PairRegime:
    symbol: str
    regime: Regime
    adx: float
    atr_pct: float
    ema_aligned: bool
    hurst: float | None
    confidence: float                # 0..1


@dataclass(frozen=True)
class GlobalRegime:
    regime: Regime
    counts: dict[str, int]
    per_pair: list[PairRegime]


# ── Indicator helpers ────────────────────────────────────────────────────────
def _adx(df: pd.DataFrame, period: int = 14) -> float:
    """Wilder's ADX. Returns the most-recent value."""
    high, low, close = df["high"], df["low"], df["close"]
    plus_dm = (high.diff()).clip(lower=0)
    minus_dm = (-low.diff()).clip(lower=0)

    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr = tr.ewm(alpha=1 / period, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr
    minus_di = 100 * minus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = dx.ewm(alpha=1 / period, adjust=False).mean()
    return float(adx.iloc[-1]) if not adx.empty and not np.isnan(adx.iloc[-1]) else 0.0


def _atr_pct(df: pd.DataFrame, period: int = 14) -> tuple[float, float]:
    """Returns (current ATR%, ATR%-percentile-rank over the available window)."""
    high, low, close = df["high"], df["low"], df["close"]
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs(),
    ], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    atr_pct = (atr / close) * 100
    if atr_pct.empty or atr_pct.isna().all():
        return 0.0, 0.0
    current = float(atr_pct.iloc[-1])
    rank = float((atr_pct.rank(pct=True).iloc[-1]) * 100)
    return current, rank


def _ema_aligned(df: pd.DataFrame, fast: int = 50, slow: int = 200) -> tuple[bool, int]:
    close = df["close"]
    if len(close) < slow + 1:
        return False, 0
    ef = close.ewm(span=fast, adjust=False).mean().iloc[-1]
    es = close.ewm(span=slow, adjust=False).mean().iloc[-1]
    direction = 1 if ef > es else -1 if ef < es else 0
    return abs(ef - es) / close.iloc[-1] > 0.001, direction


def _hurst(series: pd.Series) -> float | None:
    """Simple R/S Hurst exponent. >0.55 = trending, <0.45 = mean-reverting."""
    s = series.dropna().values
    if len(s) < 64:
        return None
    try:
        lags = range(2, min(64, len(s) // 2))
        tau = [np.std(s[lag:] - s[:-lag]) for lag in lags]
        if any(t == 0 for t in tau):
            return None
        m = np.polyfit(np.log(list(lags)), np.log(tau), 1)
        return float(m[0])
    except Exception:  # noqa: BLE001
        return None


# ── Classification ───────────────────────────────────────────────────────────
def classify_pair(symbol: str, df: pd.DataFrame) -> PairRegime:
    """`df` must have at least 200 4h bars (or any consistent timeframe)."""
    if len(df) < 50:
        return PairRegime(symbol, "flat", 0.0, 0.0, False, None, 0.0)

    adx = _adx(df, period=14)
    atr_now, atr_rank = _atr_pct(df, period=14)
    ema_ok, _ = _ema_aligned(df)
    hurst = _hurst(df["close"])

    # Decision tree.
    if atr_rank > 80:
        regime: Regime = "high_vol"
        confidence = min(1.0, atr_rank / 100)
    elif adx > 25 and ema_ok and (hurst is None or hurst > 0.5):
        regime = "trend"
        confidence = min(1.0, adx / 50)
    elif adx < 20:
        regime = "flat"
        confidence = min(1.0, (25 - adx) / 25)
    else:
        # Borderline — fall back to EMA.
        regime = "trend" if ema_ok else "flat"
        confidence = 0.45

    return PairRegime(
        symbol=symbol,
        regime=regime,
        adx=adx,
        atr_pct=atr_now,
        ema_aligned=ema_ok,
        hurst=hurst,
        confidence=confidence,
    )


def classify_global(per_pair: list[PairRegime]) -> GlobalRegime:
    counts: dict[str, int] = {"trend": 0, "flat": 0, "high_vol": 0}
    for r in per_pair:
        counts[r.regime] += 1
    if not per_pair:
        return GlobalRegime("flat", counts, [])
    # Majority. Tie broken by high_vol > trend > flat (caution-first).
    winner = max(counts, key=lambda k: (counts[k], {"high_vol": 2, "trend": 1, "flat": 0}[k]))
    return GlobalRegime(regime=winner, counts=counts, per_pair=per_pair)
