from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class StrategyParams(BaseModel):
    """Mirror of legacy GridConfig — UI-editable parameters.

    Any field omitted from the request will fall back to its default in
    legacy.config.GridConfig when the runner is constructed.
    """

    base_grid_distance_pips: float = Field(default=30.0, ge=1.0, le=500.0)
    grid_distance_multiplier: float = Field(default=1.4, ge=1.0, le=4.0)
    base_lot_size: float = Field(default=0.01, gt=0.0, le=10.0)
    lot_multiplier: float = Field(default=1.3, ge=1.0, le=3.0)
    max_grid_levels: int = Field(default=6, ge=1, le=12)

    base_time_delay_seconds: int = Field(default=1800, ge=0)
    time_delay_multiplier: float = Field(default=2.0, ge=1.0)
    atr_period: int = Field(default=14, ge=2)
    atr_multiplier: float = Field(default=1.0, gt=0.0)

    fix_take_profit_pct: float = Field(default=2.0, gt=0.0, le=20.0)
    stop_drawdown_pct: float = Field(default=10.0, gt=0.0, le=50.0)
    max_portfolio_drawdown_pct: float = Field(default=20.0, gt=0.0, le=80.0)

    trend_filter_enabled: bool = True
    ema_fast: int = Field(default=50, ge=2)
    ema_slow: int = Field(default=200, ge=3)

    correlation_filter_enabled: bool = True
    correlation_window: int = Field(default=100, ge=20)
    correlation_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    max_correlated_positions: int = Field(default=2, ge=1)

    session_filter_enabled: bool = True
    session_start_utc: int = Field(default=7, ge=0, le=23)
    session_end_utc: int = Field(default=21, ge=0, le=24)

    dynamic_lot_enabled: bool = True
    risk_per_trade_pct: float = Field(default=1.0, gt=0.0, le=10.0)
    equity_base: float = Field(default=10_000.0, gt=0.0)

    base_cooldown_hours: int = Field(default=2, ge=0)
    max_cooldown_hours: int = Field(default=24, ge=1)
    max_simultaneous_pairs: int = Field(default=5, ge=1, le=20)

    timezone_offset_utc: int = Field(default=3, ge=-12, le=14)

    symbols: list[str] = Field(default_factory=lambda: [
        "EURUSD", "GBPUSD", "EURCHF", "EURJPY", "USDCHF", "USDJPY",
    ])
    timeframe: str = Field(default="1h")


class PresetOut(BaseModel):
    id: str
    name: str
    description: str
    risk_emoji: str
    payload: dict[str, Any]


class StrategyConfigOut(BaseModel):
    id: int
    name: str
    payload: dict[str, Any]
    is_active: bool
    source: str


class ValidationIssue(BaseModel):
    field: str
    severity: str
    message: str


class ValidationResult(BaseModel):
    issues: list[ValidationIssue]
    has_errors: bool
