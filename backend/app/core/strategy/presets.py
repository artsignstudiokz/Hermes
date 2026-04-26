"""Built-in strategy presets — what users see in the UI before tuning."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PresetSpec:
    id: str
    name: str
    description: str
    risk_emoji: str
    payload: dict


PRESETS: list[PresetSpec] = [
    PresetSpec(
        id="conservative",
        name="Консервативный",
        description="Малый риск, редкие но качественные входы. ~3-5 сделок в неделю.",
        risk_emoji="🛡",
        payload={
            "base_grid_distance_pips": 40.0,
            "grid_distance_multiplier": 1.5,
            "base_lot_size": 0.01,
            "lot_multiplier": 1.2,
            "max_grid_levels": 4,
            "fix_take_profit_pct": 1.5,
            "stop_drawdown_pct": 6.0,
            "max_portfolio_drawdown_pct": 12.0,
            "trend_filter_enabled": True,
            "session_filter_enabled": True,
            "risk_per_trade_pct": 0.5,
            "max_simultaneous_pairs": 3,
        },
    ),
    PresetSpec(
        id="balanced",
        name="Сбалансированный",
        description="Оптимальный баланс риска и доходности. ~7-12 сделок в неделю.",
        risk_emoji="⚖",
        payload={
            "base_grid_distance_pips": 30.0,
            "grid_distance_multiplier": 1.4,
            "base_lot_size": 0.01,
            "lot_multiplier": 1.3,
            "max_grid_levels": 6,
            "fix_take_profit_pct": 2.0,
            "stop_drawdown_pct": 10.0,
            "max_portfolio_drawdown_pct": 20.0,
            "trend_filter_enabled": True,
            "session_filter_enabled": True,
            "risk_per_trade_pct": 1.0,
            "max_simultaneous_pairs": 5,
        },
    ),
    PresetSpec(
        id="aggressive",
        name="Агрессивный",
        description="Высокий риск, частые входы, больший размер ордеров.",
        risk_emoji="⚔",
        payload={
            "base_grid_distance_pips": 20.0,
            "grid_distance_multiplier": 1.3,
            "base_lot_size": 0.02,
            "lot_multiplier": 1.5,
            "max_grid_levels": 8,
            "fix_take_profit_pct": 3.0,
            "stop_drawdown_pct": 15.0,
            "max_portfolio_drawdown_pct": 30.0,
            "trend_filter_enabled": True,
            "session_filter_enabled": False,
            "risk_per_trade_pct": 2.0,
            "max_simultaneous_pairs": 6,
        },
    ),
    PresetSpec(
        id="auto",
        name="Auto",
        description="Hermes сам подбирает параметры под рынок (еженедельная калибровка).",
        risk_emoji="✨",
        payload={
            # Auto mode starts from balanced and gets overridden by AutoCalibrator.
            "base_grid_distance_pips": 30.0,
            "grid_distance_multiplier": 1.4,
            "base_lot_size": 0.01,
            "lot_multiplier": 1.3,
            "max_grid_levels": 6,
            "fix_take_profit_pct": 2.0,
            "stop_drawdown_pct": 10.0,
            "max_portfolio_drawdown_pct": 20.0,
            "trend_filter_enabled": True,
            "session_filter_enabled": True,
            "risk_per_trade_pct": 1.0,
            "max_simultaneous_pairs": 5,
            "auto_calibrate": True,
        },
    ),
]


def get_preset(preset_id: str) -> PresetSpec:
    for p in PRESETS:
        if p.id == preset_id:
            return p
    raise KeyError(f"Unknown preset: {preset_id}")
