"""Policy — overlay the current market regime onto a calibrated base config."""

from __future__ import annotations

from app.core.adaptive.regime import Regime


def apply_overlay(base_params: dict, regime: Regime) -> dict:
    """Return a new dict with regime-specific tweaks applied."""
    out = dict(base_params)
    if regime == "flat":
        # Tighter grid spacing, slightly larger TP, smaller positions.
        out["base_grid_distance_pips"] = max(10.0, out.get("base_grid_distance_pips", 30.0) * 0.7)
        out["fix_take_profit_pct"] = out.get("fix_take_profit_pct", 2.0) * 1.3
        out["max_simultaneous_pairs"] = min(out.get("max_simultaneous_pairs", 5), 3)
    elif regime == "high_vol":
        # Pause new entries by widening grid + reducing levels.
        out["base_grid_distance_pips"] = out.get("base_grid_distance_pips", 30.0) * 1.6
        out["max_grid_levels"] = max(2, out.get("max_grid_levels", 6) - 2)
        out["risk_per_trade_pct"] = out.get("risk_per_trade_pct", 1.0) * 0.6
    elif regime == "trend":
        # Default works well — minor lot increase to ride trends.
        out["lot_multiplier"] = min(out.get("lot_multiplier", 1.3) + 0.05, 1.6)
    return out
