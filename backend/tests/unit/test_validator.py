"""Strategy parameter validator."""

from __future__ import annotations

from app.core.strategy.validator import has_errors, validate_strategy


def _params(**overrides) -> dict:
    base = {
        "base_lot_size": 0.01,
        "lot_multiplier": 1.3,
        "max_grid_levels": 6,
        "risk_per_trade_pct": 1.0,
        "stop_drawdown_pct": 10.0,
        "max_portfolio_drawdown_pct": 20.0,
        "fix_take_profit_pct": 2.0,
        "ema_fast": 50,
        "ema_slow": 200,
    }
    base.update(overrides)
    return base


def test_balanced_passes() -> None:
    issues = validate_strategy(_params(), equity=10_000)
    assert not has_errors(issues)


def test_oversize_lot_blocks() -> None:
    issues = validate_strategy(
        _params(base_lot_size=1.0, lot_multiplier=2.0, max_grid_levels=8),
        equity=1_000,
    )
    assert has_errors(issues)
    assert any(i.field == "base_lot_size" and i.severity == "error" for i in issues)


def test_dd_invariant() -> None:
    issues = validate_strategy(
        _params(stop_drawdown_pct=15.0, max_portfolio_drawdown_pct=10.0),
        equity=10_000,
    )
    assert has_errors(issues)
    assert any(i.field == "max_portfolio_drawdown_pct" for i in issues)


def test_lot_multiplier_lt_one() -> None:
    issues = validate_strategy(_params(lot_multiplier=0.9), equity=10_000)
    assert has_errors(issues)
    assert any(i.field == "lot_multiplier" for i in issues)


def test_ema_order() -> None:
    issues = validate_strategy(_params(ema_fast=200, ema_slow=50), equity=10_000)
    assert has_errors(issues)
    assert any(i.field == "ema_fast" for i in issues)


def test_warning_only_for_25_50() -> None:
    # Sized between 25 % and 50 % of equity — warning, not error.
    issues = validate_strategy(
        _params(base_lot_size=0.05, lot_multiplier=1.5, max_grid_levels=6),
        equity=1_000,
    )
    assert not has_errors(issues)
    assert any(i.severity == "warning" for i in issues)
