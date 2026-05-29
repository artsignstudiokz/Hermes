"""Indicator panel - computes every technical indicator the bot uses
to make decisions, in one pass per bar.

The panel is intentionally read-only: strategies and signal generators
pull values from it but never mutate the source DataFrame. This keeps
backtests deterministic and lets us cache the result per (symbol, bar).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class IndicatorSnapshot:
    """One bar's worth of indicators, pre-computed for the strategy layer."""
    symbol: str
    close: float
    rsi: float                 # 0..100 - Wilder RSI
    macd: float                # MACD line (12/26 EMA difference)
    macd_signal: float         # 9-EMA of MACD line
    macd_hist: float           # MACD - signal
    bb_upper: float            # 20-period Bollinger upper (2σ)
    bb_lower: float
    bb_middle: float
    atr: float                 # 14-period ATR
    atr_pct: float             # ATR / close, scale-free
    ema_fast: float
    ema_slow: float
    adx: float                 # 0..100 - trend strength
    plus_di: float
    minus_di: float
    stoch_k: float             # 0..100
    stoch_d: float
    donchian_high: float       # 20-period
    donchian_low: float
    trend: int = 0             # -1 / 0 / +1 - quick directional consensus

    @property
    def in_bollinger_lower(self) -> bool:
        return self.close <= self.bb_lower

    @property
    def in_bollinger_upper(self) -> bool:
        return self.close >= self.bb_upper

    @property
    def rsi_oversold(self) -> bool:
        return self.rsi <= 30

    @property
    def rsi_overbought(self) -> bool:
        return self.rsi >= 70


@dataclass
class IndicatorPanel:
    """One panel per symbol; call `compute(df)` to refresh from OHLCV."""
    rsi_period: int = 14
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    bb_period: int = 20
    bb_std: float = 2.0
    atr_period: int = 14
    ema_fast_period: int = 50
    ema_slow_period: int = 200
    adx_period: int = 14
    stoch_period: int = 14
    stoch_smooth: int = 3
    donchian_period: int = 20
    snapshots: dict[str, IndicatorSnapshot] = field(default_factory=dict)

    def compute(self, symbol: str, df: pd.DataFrame) -> IndicatorSnapshot:
        if df is None or len(df) < max(self.ema_slow_period, self.donchian_period) + 1:
            raise ValueError(f"Not enough bars to compute indicators for {symbol}")

        close = df["close"].astype(float)
        high = df["high"].astype(float)
        low = df["low"].astype(float)

        rsi = _wilder_rsi(close, self.rsi_period)
        macd, macd_sig, macd_hist = _macd(close, self.macd_fast, self.macd_slow, self.macd_signal)
        bb_mid, bb_up, bb_lo = _bollinger(close, self.bb_period, self.bb_std)
        atr = _atr(high, low, close, self.atr_period)
        ema_f = close.ewm(span=self.ema_fast_period, adjust=False).mean()
        ema_s = close.ewm(span=self.ema_slow_period, adjust=False).mean()
        adx, pdi, mdi = _adx(high, low, close, self.adx_period)
        stoch_k, stoch_d = _stochastic(high, low, close, self.stoch_period, self.stoch_smooth)
        d_high = high.rolling(self.donchian_period).max()
        d_low = low.rolling(self.donchian_period).min()

        last = -1
        c = float(close.iloc[last])
        snap = IndicatorSnapshot(
            symbol=symbol,
            close=c,
            rsi=_finite(rsi.iloc[last], 50.0),
            macd=_finite(macd.iloc[last], 0.0),
            macd_signal=_finite(macd_sig.iloc[last], 0.0),
            macd_hist=_finite(macd_hist.iloc[last], 0.0),
            bb_upper=_finite(bb_up.iloc[last], c),
            bb_lower=_finite(bb_lo.iloc[last], c),
            bb_middle=_finite(bb_mid.iloc[last], c),
            atr=_finite(atr.iloc[last], 0.0),
            atr_pct=_finite(atr.iloc[last] / c if c else 0.0, 0.0),
            ema_fast=_finite(ema_f.iloc[last], c),
            ema_slow=_finite(ema_s.iloc[last], c),
            adx=_finite(adx.iloc[last], 0.0),
            plus_di=_finite(pdi.iloc[last], 0.0),
            minus_di=_finite(mdi.iloc[last], 0.0),
            stoch_k=_finite(stoch_k.iloc[last], 50.0),
            stoch_d=_finite(stoch_d.iloc[last], 50.0),
            donchian_high=_finite(d_high.iloc[last], c),
            donchian_low=_finite(d_low.iloc[last], c),
            trend=_consensus_trend(
                ema_fast=_finite(ema_f.iloc[last], c),
                ema_slow=_finite(ema_s.iloc[last], c),
                macd_hist=_finite(macd_hist.iloc[last], 0.0),
                plus_di=_finite(pdi.iloc[last], 0.0),
                minus_di=_finite(mdi.iloc[last], 0.0),
            ),
        )
        self.snapshots[symbol] = snap
        return snap


# ── primitive indicator helpers ──────────────────────────────────────────


def _finite(v, default: float) -> float:
    f = float(v)
    return f if np.isfinite(f) else default


def _wilder_rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _macd(close: pd.Series, fast: int, slow: int, sig: int):
    ema_f = close.ewm(span=fast, adjust=False).mean()
    ema_s = close.ewm(span=slow, adjust=False).mean()
    macd = ema_f - ema_s
    signal = macd.ewm(span=sig, adjust=False).mean()
    return macd, signal, macd - signal


def _bollinger(close: pd.Series, period: int, std: float):
    mid = close.rolling(period).mean()
    dev = close.rolling(period).std()
    return mid, mid + std * dev, mid - std * dev


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False).mean()


def _adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int):
    up = high.diff()
    down = -low.diff()
    plus_dm = ((up > down) & (up > 0)) * up
    minus_dm = ((down > up) & (down > 0)) * down
    atr = _atr(high, low, close, period)
    plus_di = 100 * (plus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr.replace(0, np.nan))
    minus_di = 100 * (minus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr.replace(0, np.nan))
    dx = (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan) * 100
    adx = dx.ewm(alpha=1 / period, adjust=False).mean()
    return adx, plus_di, minus_di


def _stochastic(high: pd.Series, low: pd.Series, close: pd.Series, period: int, smooth: int):
    lowest = low.rolling(period).min()
    highest = high.rolling(period).max()
    raw_k = 100 * (close - lowest) / (highest - lowest).replace(0, np.nan)
    k = raw_k.rolling(smooth).mean()
    d = k.rolling(smooth).mean()
    return k, d


def _consensus_trend(*, ema_fast: float, ema_slow: float, macd_hist: float,
                     plus_di: float, minus_di: float) -> int:
    """+1 if EMA + MACD + DI all agree up, -1 if down, 0 otherwise.

    Used as a quick "house view" by strategies that don't want to
    re-derive trend themselves.
    """
    bull = (ema_fast > ema_slow) + (macd_hist > 0) + (plus_di > minus_di)
    bear = (ema_fast < ema_slow) + (macd_hist < 0) + (plus_di < minus_di)
    if bull >= 2 and bear == 0:
        return 1
    if bear >= 2 and bull == 0:
        return -1
    return 0
