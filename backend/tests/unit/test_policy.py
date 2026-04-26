"""Regime overlay policy."""

from __future__ import annotations

from app.core.adaptive.policy import apply_overlay

BASE = {
    "base_grid_distance_pips": 30.0,
    "fix_take_profit_pct": 2.0,
    "max_simultaneous_pairs": 5,
    "max_grid_levels": 6,
    "lot_multiplier": 1.3,
    "risk_per_trade_pct": 1.0,
}


def test_flat_tightens_grid() -> None:
    out = apply_overlay(BASE, "flat")
    assert out["base_grid_distance_pips"] < BASE["base_grid_distance_pips"]
    assert out["fix_take_profit_pct"] > BASE["fix_take_profit_pct"]
    assert out["max_simultaneous_pairs"] <= 3


def test_high_vol_widens_grid_and_cuts_risk() -> None:
    out = apply_overlay(BASE, "high_vol")
    assert out["base_grid_distance_pips"] > BASE["base_grid_distance_pips"]
    assert out["max_grid_levels"] < BASE["max_grid_levels"]
    assert out["risk_per_trade_pct"] < BASE["risk_per_trade_pct"]


def test_trend_bumps_lot_multiplier() -> None:
    out = apply_overlay(BASE, "trend")
    assert out["lot_multiplier"] > BASE["lot_multiplier"]
    assert out["lot_multiplier"] <= 1.6


def test_overlay_returns_new_dict() -> None:
    out = apply_overlay(BASE, "flat")
    assert out is not BASE
    assert BASE["base_grid_distance_pips"] == 30.0   # untouched
