"""Pre-flight validation for strategy parameters.

Goal: prevent users from saving a config that will blow up their account
on the first signal. Returns a list of `Issue`s — the UI shows them next
to the offending field.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Issue:
    field: str
    severity: str        # "error" | "warning"
    message: str


def validate_strategy(params: dict, equity: float) -> list[Issue]:
    issues: list[Issue] = []

    base_lot = float(params.get("base_lot_size", 0.01))
    lot_mult = float(params.get("lot_multiplier", 1.3))
    max_levels = int(params.get("max_grid_levels", 6))
    risk_per_trade_pct = float(params.get("risk_per_trade_pct", 1.0))
    stop_dd = float(params.get("stop_drawdown_pct", 10.0))
    max_dd = float(params.get("max_portfolio_drawdown_pct", 20.0))
    tp_pct = float(params.get("fix_take_profit_pct", 2.0))
    ema_fast = int(params.get("ema_fast", 50))
    ema_slow = int(params.get("ema_slow", 200))

    # Estimated max exposure if grid fills completely (worst case).
    geometric = sum(base_lot * (lot_mult ** lvl) for lvl in range(max_levels))
    # Forex contract size = 100,000 units; assume 1:100 leverage.
    notional_usd = geometric * 100_000.0
    margin_usd = notional_usd / 100.0

    if equity > 0 and margin_usd > equity * 0.5:
        issues.append(Issue(
            field="base_lot_size",
            severity="error",
            message=(
                f"Полное заполнение сетки потребует ~${margin_usd:,.0f} маржи "
                f"при депозите ${equity:,.0f} (>50%). Уменьшите base_lot_size или max_grid_levels."
            ),
        ))
    elif equity > 0 and margin_usd > equity * 0.25:
        issues.append(Issue(
            field="base_lot_size",
            severity="warning",
            message=(
                f"Полное заполнение сетки = ~${margin_usd:,.0f} маржи (>25% депозита). "
                f"Возможен margin call при сильном движении против сетки."
            ),
        ))

    if max_dd <= stop_dd:
        issues.append(Issue(
            field="max_portfolio_drawdown_pct",
            severity="error",
            message="Максимальная просадка должна быть больше уровня остановки новых ордеров.",
        ))

    if tp_pct <= 0:
        issues.append(Issue(field="fix_take_profit_pct", severity="error", message="Take Profit должен быть > 0%."))

    if stop_dd <= 0:
        issues.append(Issue(field="stop_drawdown_pct", severity="error", message="Уровень стопа должен быть > 0%."))

    if lot_mult < 1.0:
        issues.append(Issue(
            field="lot_multiplier",
            severity="error",
            message="Множитель лота меньше 1.0 уменьшит экспозицию на каждом следующем уровне — это не сетка.",
        ))

    if risk_per_trade_pct > 5:
        issues.append(Issue(
            field="risk_per_trade_pct",
            severity="warning",
            message="Риск на сделку >5% от депозита — крайне агрессивно.",
        ))

    if ema_fast >= ema_slow:
        issues.append(Issue(
            field="ema_fast",
            severity="error",
            message="EMA fast должен быть меньше EMA slow.",
        ))

    return issues


def has_errors(issues: list[Issue]) -> bool:
    return any(i.severity == "error" for i in issues)
