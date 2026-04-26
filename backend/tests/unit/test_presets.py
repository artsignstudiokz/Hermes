"""Strategy presets registry."""

from __future__ import annotations

import pytest

from app.core.strategy.presets import PRESETS, get_preset


def test_required_presets_present() -> None:
    ids = {p.id for p in PRESETS}
    assert {"conservative", "balanced", "aggressive", "auto"} <= ids


def test_get_preset_returns_payload() -> None:
    auto = get_preset("auto")
    assert auto.payload.get("auto_calibrate") is True
    assert auto.payload["max_grid_levels"] >= 1


def test_unknown_preset_raises() -> None:
    with pytest.raises(KeyError):
        get_preset("ultra-mega-aggressive")


def test_preset_risk_progression() -> None:
    cons = get_preset("conservative").payload
    bal = get_preset("balanced").payload
    aggr = get_preset("aggressive").payload
    # Lot size grows with risk; conservative is the safest.
    assert cons["base_lot_size"] <= bal["base_lot_size"] <= aggr["base_lot_size"]
    assert cons["max_grid_levels"] <= bal["max_grid_levels"] <= aggr["max_grid_levels"]
    assert cons["risk_per_trade_pct"] <= bal["risk_per_trade_pct"] <= aggr["risk_per_trade_pct"]
