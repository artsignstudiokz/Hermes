"""Risk engine - hard circuit breakers that override the strategy.

This is the layer that says "no" to the bot when it has already lost
too much in a single session, regardless of how good the next signal
looks. Three guards:

  1. Daily P&L floor       - if today's realised + unrealised P&L
                              drops below -X% of session start equity,
                              flip the worker to "off" and refuse new
                              entries until UTC midnight reset.
  2. Equity drawdown floor - if equity from session-peak retraces by
                              more than Y%, same circuit-breaker.
  3. Open-position cap     - max N concurrent positions across the
                              account; protects against grid-style
                              martingale runaways.

The engine is queried by TradingWorker._maybe_enter BEFORE the broker
call. State is stored on the engine itself (process-wide; persists
across mode flips). Resets when the UTC day rolls over.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class RiskLimits:
    """Defaults intentionally conservative. Operators can override via
    StrategyConfig.payload - see app.core.risk.engine.from_params."""
    daily_loss_pct: float = 0.05         # 5% of session-start equity
    drawdown_pct: float = 0.10           # 10% from session peak
    max_open_positions: int = 5
    # When tripped, the engine stays tripped until this many seconds
    # have passed AND the date has rolled. 0 = wait for UTC midnight
    # only (default).
    cooldown_seconds: int = 0


@dataclass
class RiskState:
    """Live state - gets serialised into the worker status dict so the
    SPA can render a banner explaining why trading is frozen."""
    session_start_equity: float = 0.0
    session_peak_equity: float = 0.0
    tripped: bool = False
    trip_reason: str = ""
    trip_ts: datetime | None = None
    day_key: str = ""
    # For UI: latest computed metrics so the dashboard can show the
    # "you're 2% away from cap" warning before we actually trip.
    last_equity: float = 0.0
    last_drawdown_pct: float = 0.0
    last_daily_pnl_pct: float = 0.0
    open_positions: int = 0


class RiskEngine:
    def __init__(self, limits: RiskLimits | None = None):
        self.limits = limits or RiskLimits()
        self.state = RiskState()

    @classmethod
    def from_params(cls, params: dict) -> "RiskEngine":
        return cls(RiskLimits(
            daily_loss_pct=float(params.get("daily_loss_pct", 0.05)),
            drawdown_pct=float(params.get("max_portfolio_drawdown_pct", 10) / 100),
            max_open_positions=int(params.get("max_open_positions", 5)),
        ))

    def reset(self, equity: float) -> None:
        """Call this on worker.start() - establishes the session baseline."""
        self.state = RiskState(
            session_start_equity=equity,
            session_peak_equity=equity,
            last_equity=equity,
            day_key=_today_utc(),
        )
        logger.info("Risk engine reset: session start equity = %.2f", equity)

    def reset_for_new_day(self, equity: float) -> None:
        """UTC-midnight rollover - clears the trip and rebases."""
        prev_tripped = self.state.tripped
        self.state = RiskState(
            session_start_equity=equity,
            session_peak_equity=equity,
            last_equity=equity,
            day_key=_today_utc(),
        )
        if prev_tripped:
            logger.info("Risk engine reset by UTC-midnight rollover (was tripped)")

    def update(self, equity: float, open_positions_count: int) -> None:
        """Recompute live metrics. Trips the engine if any guard fires.

        Called from TradingWorker._tick AFTER fetching account info but
        BEFORE _maybe_enter - so any new tick that would have crossed
        the threshold is blocked.
        """
        today = _today_utc()
        if today != self.state.day_key:
            self.reset_for_new_day(equity)

        self.state.last_equity = equity
        self.state.open_positions = open_positions_count
        if equity > self.state.session_peak_equity:
            self.state.session_peak_equity = equity

        # If we never got a real equity reading at session start
        # (broker disconnect during start()), use the first one we see.
        if self.state.session_start_equity == 0:
            self.state.session_start_equity = equity
            self.state.session_peak_equity = equity

        start = max(1.0, self.state.session_start_equity)
        peak = max(1.0, self.state.session_peak_equity)
        self.state.last_daily_pnl_pct = (equity - start) / start
        self.state.last_drawdown_pct = (peak - equity) / peak

        if self.state.tripped:
            return    # already frozen - only cleared by reset_for_new_day

        if self.state.last_daily_pnl_pct <= -self.limits.daily_loss_pct:
            self._trip(
                f"Daily loss {self.state.last_daily_pnl_pct * 100:+.2f}% "
                f"exceeded limit {-self.limits.daily_loss_pct * 100:.1f}%"
            )
        elif self.state.last_drawdown_pct >= self.limits.drawdown_pct:
            self._trip(
                f"Drawdown {self.state.last_drawdown_pct * 100:.2f}% "
                f"exceeded limit {self.limits.drawdown_pct * 100:.1f}%"
            )

    def allow_new_entry(self) -> tuple[bool, str]:
        """Final guard the worker calls right before place_order.

        Returns (ok, reason). reason is empty when ok=True; otherwise
        it's a short human-readable string for the dashboard banner.
        """
        if self.state.tripped:
            return False, f"Risk circuit breaker tripped: {self.state.trip_reason}"
        if self.state.open_positions >= self.limits.max_open_positions:
            return False, (
                f"Open positions {self.state.open_positions} / "
                f"{self.limits.max_open_positions} - bot is at capacity"
            )
        return True, ""

    def to_dict(self) -> dict:
        return {
            "tripped": self.state.tripped,
            "trip_reason": self.state.trip_reason,
            "trip_ts": self.state.trip_ts.isoformat() if self.state.trip_ts else None,
            "session_start_equity": self.state.session_start_equity,
            "session_peak_equity": self.state.session_peak_equity,
            "last_equity": self.state.last_equity,
            "daily_pnl_pct": round(self.state.last_daily_pnl_pct * 100, 3),
            "drawdown_pct": round(self.state.last_drawdown_pct * 100, 3),
            "open_positions": self.state.open_positions,
            "limits": {
                "daily_loss_pct": self.limits.daily_loss_pct * 100,
                "drawdown_pct": self.limits.drawdown_pct * 100,
                "max_open_positions": self.limits.max_open_positions,
            },
        }

    # ── internals ──────────────────────────────────────────────────────

    def _trip(self, reason: str) -> None:
        self.state.tripped = True
        self.state.trip_reason = reason
        self.state.trip_ts = datetime.now(timezone.utc)
        logger.warning("Risk engine TRIPPED: %s", reason)


def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")
