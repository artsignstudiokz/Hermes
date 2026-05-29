"""Asyncio worker that runs the strategy loop and persists results.

Polls every CHECK_INTERVAL seconds, calls runner.tick(), persists
position/equity snapshots, and broadcasts updates over WebSocket.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.api.ws.manager import WebSocketManager
from app.core.brokers.base import BrokerAdapter
from app.core.notifications.service import NotificationService
from app.core.strategy.runner import StrategyRunner
from app.db.models import EquityPoint, PositionSnapshot, TradeRow
from app.db.session import get_sessionmaker

logger = logging.getLogger(__name__)


class TradingWorker:
    """Long-running async loop. Cancellable via stop()."""

    def __init__(
        self,
        broker_account_id: int,
        adapter: BrokerAdapter,
        runner: StrategyRunner,
        ws: WebSocketManager,
        notifier: NotificationService | None = None,
        check_interval: float = 60.0,
    ) -> None:
        self._account_id = broker_account_id
        self._adapter = adapter
        self._runner = runner
        self._ws = ws
        self._notifier = notifier
        self._check_interval = check_interval
        self._task: asyncio.Task | None = None
        self._stop_evt = asyncio.Event()
        self._paused = False
        self._last_tick: datetime | None = None
        self._last_error: str | None = None
        self._tick_count = 0
        # Trading mode — mutually exclusive with itself by virtue of one
        # worker per service. Values: "off" (observation only, no orders),
        # "proven" (single calibrated strategy, strict confidence, 1-3
        # trades/day, only on the configured 3-5 pairs), "autonomous"
        # (full ensemble, any pair, picks the highest-confidence signal
        # of the bar, 1-3 trades/day). Both modes obey the daily limit.
        self._mode = "off"
        # Per-UTC-day counter for the daily trade cap. Reset whenever the
        # tick date changes.
        self._day_key = ""
        self._trades_today = 0
        self._max_trades_per_day = 3
        # Minimum confidence for a signal to actually open a trade.
        # Stricter in proven mode (best historical pattern wanted),
        # looser in autonomous (still ≥0.5 — never YOLO).
        self._confidence_thresholds = {"proven": 0.7, "autonomous": 0.5}
        # Pre-built ensembles. Constructed once on mode change instead of
        # every tick — `build_ensemble` instantiates strategy objects so
        # rebuilding 1× per minute is wasteful and shows up in profiles
        # over a 12-hour session.
        self._ensemble_cache: dict = {}
        # Guard for the entry path — prevents a second tick from racing
        # ahead and double-opening when MT5 place_order is slow (some
        # brokers take 2-3s to respond).
        self._entry_lock = asyncio.Lock()
        # Risk engine — hard circuit breakers (daily loss, drawdown,
        # max concurrent positions). Tripped state survives mode flips;
        # only UTC-midnight rollover clears it. See app.core.risk.engine
        # for thresholds.
        from app.core.risk.engine import RiskEngine
        self._risk = RiskEngine()
        # MT5 watchdog — counts consecutive broker-health-probe failures
        # so we can pause and surface a clear "broker_down" event to the
        # SPA instead of silently trading on stale state.
        self._consecutive_health_fails = 0

    @property
    def state(self) -> dict:
        return {
            "running": self._task is not None and not self._task.done(),
            "paused": self._paused,
            # Kept for back-compat with the old SPA toggle but the real
            # source of truth is `mode`.
            "trading_enabled": self._mode != "off",
            "mode": self._mode,
            "trades_today": self._trades_today,
            "max_trades_per_day": self._max_trades_per_day,
            "last_tick": self._last_tick.isoformat() if self._last_tick else None,
            "tick_count": self._tick_count,
            "last_error": self._last_error,
            "risk": self._risk.to_dict(),
        }

    def set_mode(self, mode: str) -> None:
        if mode not in ("off", "proven", "autonomous"):
            raise ValueError(f"Unknown trading mode: {mode}")
        self._mode = mode
        # Ensure the ensemble for this mode is ready ahead of next tick.
        # Default rosters were tuned in v1.0.22 after the walk-forward
        # backtest: TrendFollowing + Momentum has positive expectancy on
        # synthetic data; MeanReversion / Breakout enter only when the
        # operator opts in via the strategy config (params["ensemble"]).
        if mode in ("proven", "autonomous") and mode not in self._ensemble_cache:
            from app.core.strategy.signals import build_ensemble
            if mode == "proven":
                self._ensemble_cache[mode] = build_ensemble(["trend"], mode="any")
            else:
                self._ensemble_cache[mode] = build_ensemble(
                    ["trend", "momentum"], mode="majority",
                )
        logger.info("Trading mode = %s for account %d", mode, self._account_id)

    # Kept for back-compat with the older one-toggle UI. Maps to
    # autonomous mode (the closest analog to "live trading on").
    def enable_trading(self) -> None:
        self.set_mode("autonomous")

    def disable_trading(self) -> None:
        self.set_mode("off")

    def _bump_day_counter(self) -> None:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if today != self._day_key:
            self._day_key = today
            self._trades_today = 0

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        await self._runner.setup()
        self._stop_evt.clear()
        # Seed risk engine with the starting equity so daily-loss is
        # measured from "the moment trading began this session", not
        # from a stale value.
        try:
            account = await self._adapter.get_account()
            self._risk.reset(float(account.equity))
        except Exception:  # noqa: BLE001
            logger.warning("Could not seed risk engine on start — will use first tick equity")

        # Seed an immediate observation tick so existing broker positions
        # and balance show up on the Dashboard at once.
        sm = get_sessionmaker()
        try:
            await self._tick(sm)
        except Exception:
            logger.exception("Initial observation tick failed (will retry on schedule)")
        self._task = asyncio.create_task(self._run(), name="hermes-trading-worker")
        logger.info(
            "Trading worker started for account %d (trading_enabled=%s)",
            self._account_id, self._trading_enabled,
        )

    async def stop(self) -> None:
        self._stop_evt.set()
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=5.0)
            except asyncio.TimeoutError:
                self._task.cancel()
        self._task = None
        logger.info("Trading worker stopped for account %d", self._account_id)

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    async def _broker_health_probe(self) -> bool:
        """Returns True if the adapter answered, False if we should skip
        the tick (already paused / still trying to reconnect).
        """
        try:
            await asyncio.wait_for(self._adapter.get_account(), timeout=8.0)
            if self._consecutive_health_fails > 0:
                logger.info(
                    "Adapter recovered after %d failed probes",
                    self._consecutive_health_fails,
                )
            self._consecutive_health_fails = 0
            return True
        except Exception as e:  # noqa: BLE001
            self._consecutive_health_fails += 1
            logger.warning(
                "Adapter health probe failed (%d/3): %s",
                self._consecutive_health_fails, e,
            )
            if self._consecutive_health_fails >= 3:
                self._paused = True
                self._last_error = f"Broker unreachable: {e}"
                await self._ws.broadcast("signals", {
                    "type": "broker_down",
                    "reason": str(e),
                    "ts": datetime.now(timezone.utc).isoformat(),
                })
                return False
            # Try to reconnect quietly between probes.
            try:
                await self._adapter.disconnect()
            except Exception:  # noqa: BLE001
                pass
            try:
                await self._adapter.connect()
                logger.info(
                    "Adapter reconnected after %d health-probe failures",
                    self._consecutive_health_fails,
                )
            except Exception as e2:  # noqa: BLE001
                logger.warning("Reconnect attempt failed: %s", e2)
            return False

    async def _maybe_enter(self, sm) -> None:
        """Pick the best signal report and possibly open ONE trade.

        Order of guards (each one short-circuits the rest):
          1. mode is "off"                       → never enter
          2. trades_today ≥ max_trades_per_day  → daily cap hit
          3. no actionable report                → nothing to do
          4. confidence below per-mode floor    → bot is not convinced
          5. proven mode: report.symbol must be in configured pairs

        Wrapped in self._entry_lock so a slow MT5 place_order can't be
        racing with the next 60-second tick — that's what caused dupe
        opens on the same minute in early bench testing.
        """
        from app.db.models import TradeRow
        from app.core.brokers.models import Direction, OrderRequest

        if self._mode == "off":
            return
        if self._entry_lock.locked():
            return     # previous tick's place_order still in flight
        if self._trades_today >= self._max_trades_per_day:
            return

        ensemble = self._ensemble_cache.get(self._mode)
        if ensemble is None:
            return     # set_mode wasn't called — defensive

        # Re-run the ensemble against the snapshots the runner just
        # computed — quick (no OHLCV refetch).
        candidates = [ensemble.evaluate(snap) for snap in self._runner.last_snapshots.values()]
        # Proven mode: restrict to the strategy's configured symbols
        # (defaults to 3-5 majors picked at onboarding).
        if self._mode == "proven":
            allowed = set(self._runner.symbols)
            candidates = [c for c in candidates if c.symbol in allowed]

        actionable = [c for c in candidates
                      if c.direction != "flat"
                      and c.confidence >= self._confidence_thresholds[self._mode]]
        if not actionable:
            return
        actionable.sort(key=lambda c: c.confidence, reverse=True)
        best = actionable[0]

        # Risk gate — daily loss / drawdown / max positions. The engine
        # was updated in _tick with the latest account & positions count.
        ok, reason = self._risk.allow_new_entry()
        if not ok:
            logger.info("Risk engine vetoed entry on %s: %s", best.symbol, reason)
            await self._ws.broadcast("signals", {
                "type": "risk_block", "symbol": best.symbol, "reason": reason,
                "ts": datetime.now(timezone.utc).isoformat(),
            })
            return

        d = Direction.LONG if best.direction == "long" else Direction.SHORT

        # Compute broker-side SL/TP from the symbol's ATR. The position
        # then closes autonomously if the bot dies — we use 2×ATR stop
        # and 4×ATR target (1:2 risk/reward). ATR is in price units, so
        # adding/subtracting it from the close gives an absolute price.
        snap = self._runner.last_snapshots.get(best.symbol)
        sl_price: float | None = None
        tp_price: float | None = None
        if snap is not None and snap.atr > 0:
            if best.direction == "long":
                sl_price = snap.close - 2 * snap.atr
                tp_price = snap.close + 4 * snap.atr
            else:
                sl_price = snap.close + 2 * snap.atr
                tp_price = snap.close - 4 * snap.atr

        async with self._entry_lock:
            # Re-check quota under the lock so two ticks can't both pass
            # the early gate before either has finished placing.
            if self._trades_today >= self._max_trades_per_day:
                return
            try:
                order = await self._adapter.place_order(OrderRequest(
                    symbol=best.symbol, direction=d, lot_size=0.01,
                    comment=f"hermes_{self._mode[:4]}_{best.symbol[:6]}",
                    stop_loss=sl_price, take_profit=tp_price,
                ))
            except Exception as e:  # noqa: BLE001
                logger.warning("Auto-entry rejected for %s: %s", best.symbol, e)
                return
            if order is None:
                logger.info("Broker returned None for auto-entry on %s", best.symbol)
                return
            # Increment under the same lock — closes the race where two
            # concurrent ticks could both place_order before either bumps
            # the counter.
            self._trades_today += 1

        async with sm() as session:
            session.add(TradeRow(
                broker_account_id=self._account_id,
                ticket=str(order.ticket),
                symbol=best.symbol,
                direction=best.direction,
                level=0,
                lots=0.01,
                entry_price=getattr(order, "entry_price", 0.0),
                opened_at=self._last_tick,
                reason=f"auto_{self._mode}",
                mode=self._mode,
                signal_reason=best.reason,
            ))
            await session.commit()
        await self._ws.broadcast("signals", {
            "type": "trade_opened",
            "mode": self._mode,
            "symbol": best.symbol,
            "direction": best.direction,
            "confidence": round(best.confidence, 3),
            "reason": best.reason,
            "trades_today": self._trades_today,
            "ts": self._last_tick.isoformat(),
        })
        logger.info(
            "Opened %s %s in %s mode (conf=%.2f, %d/%d today)",
            best.direction, best.symbol, self._mode, best.confidence,
            self._trades_today, self._max_trades_per_day,
        )

    async def kill_switch(self) -> int:
        """Close everything immediately, regardless of strategy state."""
        closed = await self._adapter.close_all()
        await self._ws.broadcast("signals", {
            "type": "kill_switch",
            "closed_count": closed,
            "ts": datetime.now(timezone.utc).isoformat(),
        })
        logger.warning("Kill-switch invoked: %d positions closed", closed)
        return closed

    async def _run(self) -> None:
        sm = get_sessionmaker()
        try:
            while not self._stop_evt.is_set():
                if not self._paused:
                    try:
                        await self._tick(sm)
                    except Exception as e:  # noqa: BLE001
                        self._last_error = str(e)
                        logger.exception("tick failed")
                        await self._ws.broadcast("signals", {
                            "type": "error",
                            "message": str(e),
                            "ts": datetime.now(timezone.utc).isoformat(),
                        })
                # Sleep with cancellation support.
                try:
                    await asyncio.wait_for(self._stop_evt.wait(), timeout=self._check_interval)
                except asyncio.TimeoutError:
                    pass
        except asyncio.CancelledError:
            logger.info("Worker cancelled")
            raise

    async def _tick(self, sm) -> None:
        # Watchdog probe — confirm the broker socket is alive BEFORE we
        # spend time computing 19 indicators on stale data. If three
        # consecutive ticks fail, pause the worker and tell the SPA so
        # the user sees the wine banner instead of silent inactivity.
        if not await self._broker_health_probe():
            return

        # The grid strategy still runs but ALWAYS in dry_run — it gives
        # us close-basket actions for managing existing legacy positions
        # and indicator data for analysis, but it does NOT open new
        # entries any more. New entries are made strictly through the
        # explainable signal ensemble, gated by mode + daily limit.
        # This is the change that stops "hermes_L0 immediately after
        # Start" once and for all.
        actions = await self._runner.tick(dry_run=True)
        self._last_tick = datetime.now(timezone.utc)
        self._tick_count += 1
        self._bump_day_counter()

        # Broadcast explainable per-symbol analysis so the dashboard can
        # show "Бот рассматривает EURUSD: trend up, MACD+, ADX 31 ⇒ LONG
        # (уверенность 0.62)" with the full reasoning markdown. Sent
        # before order broadcasts so the UI can correlate: this analysis
        # → that action.
        for report in self._runner.last_signal_reports:
            try:
                await self._ws.broadcast("signals", report.to_dict())
            except Exception:  # noqa: BLE001
                logger.debug("Failed to broadcast signal report", exc_info=True)

        # Pull the latest account/position/equity snapshot first so the
        # risk engine has a fresh equity reading before we decide whether
        # to open. Order matters: account → risk.update → _maybe_enter.
        account = await self._adapter.get_account()
        positions = await self._adapter.get_positions()
        self._risk.update(float(account.equity), len(positions))

        # Mode-driven entry decision: pick the strongest report, open ONE
        # trade if it clears the per-mode confidence floor, daily quota,
        # and risk-engine guards. Conservative on purpose — at most one
        # pair per tick.
        await self._maybe_enter(sm)

        async with sm() as session:
            session.add(EquityPoint(
                broker_account_id=self._account_id,
                ts=self._last_tick,
                equity=account.equity,
                balance=account.balance,
                margin=account.margin,
                drawdown_pct=0.0,  # filled by separate calc later
            ))
            for p in positions:
                session.add(PositionSnapshot(
                    broker_account_id=self._account_id,
                    ts=self._last_tick,
                    symbol=p.symbol,
                    lots=p.lot_size,
                    avg_price=p.entry_price,
                    unrealized_pnl=p.unrealized_pnl,
                ))
            for action in actions:
                if action.get("action") == "open" and "broker_ticket" in action:
                    session.add(TradeRow(
                        broker_account_id=self._account_id,
                        ticket=action["broker_ticket"],
                        symbol=action["symbol"],
                        direction=action["direction"],
                        level=action.get("level", 0),
                        lots=action["lot_size"],
                        entry_price=action["price"],
                        opened_at=self._last_tick,
                        reason="grid_entry",
                    ))
                elif action.get("action") == "close_basket":
                    # Mark every still-open trade for this symbol as closed.
                    # close_basket aggregates the basket P&L; per-trade exit
                    # price isn't reported by the strategy, so we use the
                    # latest snapshot price as an approximation and leave
                    # exact reconciliation to a future broker-history sync.
                    sym = action.get("symbol")
                    pnl = float(action.get("pnl") or 0.0)
                    reason = str(action.get("reason") or "close_basket")
                    open_trades = (await session.execute(
                        select(TradeRow).where(
                            TradeRow.broker_account_id == self._account_id,
                            TradeRow.symbol == sym,
                            TradeRow.closed_at.is_(None),
                        ),
                    )).scalars().all()
                    n = max(1, len(open_trades))
                    per_trade_pnl = pnl / n
                    for tr in open_trades:
                        tr.closed_at = self._last_tick
                        tr.pnl = per_trade_pnl
                        tr.reason = reason
            await session.commit()

        # Broadcast over WS.
        await self._ws.broadcast("equity", {
            "ts": self._last_tick.isoformat(),
            "equity": account.equity,
            "balance": account.balance,
            "margin": account.margin,
        })
        # Field names MUST match PositionOut schema — frontend writes the
        # WS payload directly into the ["positions"] react-query cache, so
        # any drift (lots vs lot_size, swap missing, etc.) → undefined →
        # `.toFixed` crash in PositionsTable.
        await self._ws.broadcast("positions", [
            {
                "ticket": p.ticket,
                "symbol": p.symbol,
                "direction": p.direction.value,
                "lot_size": p.lot_size,
                "entry_price": p.entry_price,
                "current_price": p.current_price,
                "unrealized_pnl": p.unrealized_pnl,
                "swap": p.swap,
                "commission": p.commission,
                "opened_at": p.opened_at.isoformat(),
            }
            for p in positions
        ])
        for action in actions:
            event = {
                "type": action["action"],
                "symbol": action.get("symbol"),
                "direction": action.get("direction"),
                "level": action.get("level"),
                "lots": action.get("lot_size"),
                "price": action.get("price"),
                "pnl": action.get("pnl"),
                "reason": action.get("reason"),
                "ts": self._last_tick.isoformat(),
            }
            await self._ws.broadcast("signals", event)
            if self._notifier:
                try:
                    await self._notifier.dispatch(event)
                except Exception:  # noqa: BLE001
                    logger.exception("Notifier dispatch failed")
