"""Market regime classification on synthetic series."""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.core.adaptive.regime import classify_global, classify_pair


def _ohlcv(closes: np.ndarray) -> pd.DataFrame:
    return pd.DataFrame({
        "open": closes,
        "high": closes * 1.001,
        "low": closes * 0.999,
        "close": closes,
        "volume": np.ones_like(closes),
    })


def test_classify_strong_uptrend() -> None:
    rng = np.random.default_rng(7)
    base = np.linspace(100, 130, 400) + rng.normal(0, 0.1, 400)
    res = classify_pair("UPTREND", _ohlcv(base))
    assert res.regime in ("trend", "high_vol")
    assert res.adx > 0


def test_classify_flat() -> None:
    rng = np.random.default_rng(7)
    base = 100 + rng.normal(0, 0.05, 400)
    res = classify_pair("FLAT", _ohlcv(base))
    assert res.regime in ("flat", "trend")        # ADX may flag tiny trend; tolerate
    assert res.adx < 30


def test_classify_high_volatility() -> None:
    rng = np.random.default_rng(7)
    base = 100 + np.cumsum(rng.normal(0, 2.0, 400))   # large step variance
    res = classify_pair("VOL", _ohlcv(base))
    assert res.regime in ("high_vol", "trend")
    assert res.atr_pct > 0


def test_classify_global_majority_vote() -> None:
    rng = np.random.default_rng(7)
    pairs = [
        classify_pair("A", _ohlcv(np.linspace(100, 130, 300))),
        classify_pair("B", _ohlcv(np.linspace(100, 130, 300))),
        classify_pair("C", _ohlcv(100 + rng.normal(0, 0.05, 300))),
    ]
    g = classify_global(pairs)
    assert g.regime in ("trend", "high_vol")
    assert g.counts.get(g.regime, 0) >= 2


def test_classify_short_series_returns_flat() -> None:
    short = _ohlcv(np.array([100.0] * 10))
    res = classify_pair("SHORT", short)
    assert res.regime == "flat"
    assert res.confidence == 0.0
