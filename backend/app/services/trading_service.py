"""TradingService - single orchestrator the routes/workers go through."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.ws.manager import WebSocketManager, get_ws_manager
from app.core.brokers.models import BrokerCredentials, BrokerType
from app.core.brokers.registry import BrokerRegistry
from app.core.notifications.service import NotificationService
from app.core.security.vault import CredentialVault
from app.core.strategy.runner import StrategyRunner
from app.db.models import BrokerAccount, StrategyConfigRow
from app.db.session import get_sessionmaker
from app.workers.trading_worker import TradingWorker

logger = logging.getLogger(__name__)


class TradingService:
    """Owns the active TradingWorker. One worker per process for now."""

    def __init__(
        self,
        registry: BrokerRegistry,
        vault: CredentialVault,
        notifier: NotificationService | None = None,
    ) -> None:
        self._registry = registry
        self._vault = vault
        self._notifier = notifier
        self._ws: WebSocketManager = get_ws_manager()
        self._worker: TradingWorker | None = None
        self._broker_account_id: int | None = None

    @property
    def status(self) -> dict:
        # Worker is always a dict - same shape as TradingWorker.state -
        # so the SPA can read .mode / .trades_today without first
        # checking if a worker exists. Default values reflect the
        # "never started" state.
        worker_state = self._worker.state if self._worker else {
            "running": False,
            "paused": False,
            "trading_enabled": False,
            "mode": "off",
            "trades_today": 0,
            "max_trades_per_day": 3,
            "last_tick": None,
            "tick_count": 0,
            "last_error": None,
            "risk": {
                "tripped": False, "trip_reason": "", "trip_ts": None,
                "session_start_equity": 0.0, "session_peak_equity": 0.0,
                "last_equity": 0.0, "daily_pnl_pct": 0.0, "drawdown_pct": 0.0,
                "open_positions": 0,
                "limits": {"daily_loss_pct": 5.0, "drawdown_pct": 10.0, "max_open_positions": 5},
            },
        }
        return {
            "broker_account_id": self._broker_account_id,
            "worker": worker_state,
        }

    async def start(self, broker_account_id: int) -> dict:
        if self._worker and self._worker.state["running"]:
            return self.status

        # Load broker account + active strategy config.
        sm = get_sessionmaker()
        async with sm() as session:
            account = await session.get(BrokerAccount, broker_account_id)
            if account is None:
                raise ValueError(f"BrokerAccount {broker_account_id} not found")

            cfg_row = await self._active_strategy(session)
            params = cfg_row.payload if cfg_row else {}

        creds_payload = self._vault.get(account.vault_key)
        if creds_payload is None:
            raise ValueError(f"No credentials in vault for account {broker_account_id}")
        creds = BrokerCredentials(
            type=BrokerType(account.type),
            server=account.server,
            login=int(account.login) if account.login else None,
            password=creds_payload.get("password"),
            api_key=creds_payload.get("api_key"),
            api_secret=creds_payload.get("api_secret"),
            api_passphrase=creds_payload.get("api_passphrase"),
            testnet=account.is_testnet,
        )

        adapter = await self._registry.connect(broker_account_id, creds)
        symbols = params.get("symbols") or [
            "EURUSD", "GBPUSD", "EURCHF", "EURJPY", "USDCHF", "USDJPY",
        ]

        runner = StrategyRunner(
            adapter=adapter,
            params=params,
            symbols=symbols,
            timeframe=params.get("timeframe", "1h"),
        )

        self._worker = TradingWorker(
            broker_account_id=broker_account_id,
            adapter=adapter,
            runner=runner,
            ws=self._ws,
            notifier=self._notifier,
            check_interval=float(params.get("check_interval_sec", 60)),
        )
        await self._worker.start()
        self._broker_account_id = broker_account_id
        return self.status

    async def stop(self) -> dict:
        if self._worker:
            await self._worker.stop()
            self._worker = None
        return self.status

    async def pause(self) -> dict:
        if self._worker:
            self._worker.pause()
        return self.status

    async def resume(self) -> dict:
        if self._worker:
            self._worker.resume()
        return self.status

    async def kill_switch(self) -> int:
        if not self._worker:
            return 0
        return await self._worker.kill_switch()

    def enable_trading(self) -> dict:
        if self._worker is None:
            raise ValueError("Trading worker not started - click Start first")
        self._worker.enable_trading()
        return self.status

    def disable_trading(self) -> dict:
        if self._worker is None:
            raise ValueError("Trading worker not started")
        self._worker.disable_trading()
        return self.status

    async def start_proven(self, broker_account_id: int) -> dict:
        """Start the worker and set it into the proven scenario mode.

        Only one mode runs at a time - if the worker is already up in
        autonomous mode we flip it; otherwise we boot the worker first
        and then set the mode.
        """
        if self._worker is None or not self._worker.state["running"]:
            await self.start(broker_account_id)
        self._worker.set_mode("proven")  # type: ignore[union-attr]
        return self.status

    async def start_autonomous(self, broker_account_id: int) -> dict:
        if self._worker is None or not self._worker.state["running"]:
            await self.start(broker_account_id)
        self._worker.set_mode("autonomous")  # type: ignore[union-attr]
        return self.status

    def set_mode(self, mode: str) -> dict:
        """Generic mode setter used by the legacy enable/disable endpoints."""
        if self._worker is None:
            raise ValueError("Trading worker not started - click Start first")
        self._worker.set_mode(mode)
        return self.status

    async def analyze_and_trade(
        self, lot_size: float = 0.01, dry_run: bool = False,
    ) -> dict:
        """Scan every pair from the active strategy config, run the
        full ensemble, pick the symbol with the highest-confidence
        non-flat signal, and open one position. The dashboard renders
        the returned report so the user sees exactly WHY this pair,
        WHAT indicators agreed, and the markdown reasoning.

        dry_run=True returns the analysis without placing the order -
        used by the "Глубокий анализ" preview button.
        """
        from app.core.brokers.models import Direction, OrderRequest
        from app.core.strategy.indicators import IndicatorPanel
        from app.core.strategy.signals import build_ensemble

        adapter = self._registry.get_active()
        if adapter is None:
            raise ValueError("No active broker - connect one first")

        # Load active strategy config to know which symbols + ensemble.
        sm = get_sessionmaker()
        async with sm() as session:
            cfg_row = await self._active_strategy(session)
            params = cfg_row.payload if cfg_row else {}
        symbols = params.get("symbols") or [
            "EURUSD", "GBPUSD", "EURCHF", "EURJPY", "USDCHF", "USDJPY",
        ]
        # Default ensemble - see v1.0.22 backtest in
        # scripts/backtest_ensemble.py for the reasoning behind
        # excluding MeanReversion/Breakout from the default.
        ensemble = build_ensemble(
            params.get("ensemble") or ["trend", "momentum"],
            mode=params.get("ensemble_mode") or "majority",
        )
        panel = IndicatorPanel()

        reports = []
        for sym in symbols:
            try:
                df = await adapter.get_ohlcv(sym, params.get("timeframe", "1h"), 300)
                snap = panel.compute(sym, df)
                reports.append(ensemble.evaluate(snap))
            except Exception as e:  # noqa: BLE001
                logger.warning("Analyze skipped %s: %s", sym, e)

        # Sort by confidence - only act if the bot is actually convinced.
        actionable = [r for r in reports if r.direction != "flat" and r.confidence >= 0.5]
        actionable.sort(key=lambda r: r.confidence, reverse=True)

        if not actionable:
            return {
                "opened": False,
                "reason": "Ни одна пара не дала сигнал с уверенностью ≥ 0.5. Бот предпочитает подождать.",
                "reports": [r.to_dict() for r in reports],
            }

        best = actionable[0]
        result: dict = {
            "opened": False,
            "best": best.to_dict(),
            "reports": [r.to_dict() for r in reports],
        }
        if dry_run:
            result["reason"] = (
                f"DRY-RUN: бот выбрал бы {best.symbol} ({best.direction}) с уверенностью "
                f"{best.confidence:.2f}. Реальная сделка не открыта."
            )
            return result

        d = Direction.LONG if best.direction == "long" else Direction.SHORT
        try:
            order = await adapter.place_order(OrderRequest(
                symbol=best.symbol, direction=d, lot_size=lot_size,
                comment=f"hermes_analyze_{best.symbol[:6]}",
            ))
        except Exception as e:  # noqa: BLE001
            result["reason"] = f"Анализ выбрал {best.symbol}, но брокер отклонил ордер: {e}"
            return result
        if order is None:
            result["reason"] = f"Анализ выбрал {best.symbol}, но брокер вернул None."
            return result
        result["opened"] = True
        result["ticket"] = order.ticket
        result["reason"] = (
            f"Открыта позиция {best.direction.upper()} {best.symbol} {lot_size} лот. "
            f"Уверенность {best.confidence:.2f}. Тикет {order.ticket}."
        )
        return result

    async def manual_open(
        self,
        symbol: str | None = None,
        direction: str | None = None,
        lot_size: float | None = None,
        comment: str = "manual_test",
        risk_pct: float = 0.5,
    ) -> dict:
        """One-shot test trade with full reasoning.

        v1.0.33: instead of a hardcoded 0.01 lot on the first configured
        symbol, this now:
          1. Runs the same indicator ensemble used in autonomous mode
             across every configured pair.
          2. Picks the strongest non-flat signal (≥0.4 confidence so
             we don't open garbage).
          3. Sizes the lot from the live account equity at risk_pct%
             of equity (default 0.5%, with a 0.01 lot floor).
          4. Returns a human-readable reason explaining WHY this symbol,
             this direction, this size - the operator sees it in a
             dashboard toast.

        Old call-shape is still supported: passing explicit symbol /
        direction / lot_size bypasses the analysis and just routes the
        order. Used by tests.
        """
        from app.core.brokers.models import Direction, OrderRequest
        from app.core.strategy.indicators import IndicatorPanel
        from app.core.strategy.signals import build_ensemble
        from app.workers.trading_worker import _scale_lot

        adapter = self._registry.get_active()
        if adapter is None:
            raise ValueError("No active broker - connect one first")

        # Explicit-args path (legacy / tests).
        if symbol and direction and lot_size:
            d = Direction.LONG if direction.lower() == "long" else Direction.SHORT
            order = await adapter.place_order(OrderRequest(
                symbol=symbol, direction=d, lot_size=lot_size, comment=comment,
            ))
            if order is None:
                raise ValueError(f"Broker rejected the order for {symbol}")
            return {
                "ticket": str(order.ticket),
                "symbol": symbol,
                "direction": direction,
                "lot_size": lot_size,
                "entry_price": getattr(order, "entry_price", None),
                "reason": "Ручной тест: символ и направление переданы напрямую.",
                "confidence": None,
            }

        # Analysis path - choose symbol + direction from the ensemble.
        sm = get_sessionmaker()
        async with sm() as session:
            cfg_row = await self._active_strategy(session)
            params = cfg_row.payload if cfg_row else {}
        symbols = params.get("symbols") or [
            "EURUSD", "GBPUSD", "EURCHF", "EURJPY", "USDCHF", "USDJPY",
        ]
        ensemble = build_ensemble(
            params.get("ensemble") or ["trend", "momentum"],
            mode=params.get("ensemble_mode") or "majority",
        )
        panel = IndicatorPanel()

        reports = []
        for sym in symbols:
            try:
                df = await adapter.get_ohlcv(sym, params.get("timeframe", "1h"), 300)
                snap = panel.compute(sym, df)
                reports.append(ensemble.evaluate(snap))
            except Exception as e:  # noqa: BLE001
                logger.warning("Test-trade analyze skipped %s: %s", sym, e)

        actionable = [r for r in reports if r.direction != "flat" and r.confidence >= 0.4]
        actionable.sort(key=lambda r: r.confidence, reverse=True)
        if not actionable:
            raise ValueError(
                "Ни одна пара не дала достаточно уверенного сигнала "
                "(порог 0.4). Подождите немного и попробуйте снова."
            )
        best = actionable[0]

        # Lot sizing from live equity.
        try:
            account = await adapter.get_account()
            equity = float(account.equity)
        except Exception:
            equity = 0.0
        lot_size = _scale_lot(equity, risk_pct=risk_pct)

        d = Direction.LONG if best.direction == "long" else Direction.SHORT
        order = await adapter.place_order(OrderRequest(
            symbol=best.symbol, direction=d, lot_size=lot_size, comment=comment,
        ))
        if order is None:
            raise ValueError(f"Брокер отклонил ордер на {best.symbol}")
        return {
            "ticket": str(order.ticket),
            "symbol": best.symbol,
            "direction": best.direction,
            "lot_size": lot_size,
            "entry_price": getattr(order, "entry_price", None),
            "reason": (
                f"Размер позиции {lot_size} лот — это около {risk_pct}% от текущего эквити "
                f"({equity:.2f}). Бот выбрал {best.symbol} {best.direction.upper()} "
                f"с уверенностью {best.confidence:.2f}.\n\n{best.reason}"
            ),
            "confidence": round(best.confidence, 3),
        }

    async def _active_strategy(self, session: AsyncSession) -> StrategyConfigRow | None:
        result = await session.execute(
            select(StrategyConfigRow).where(StrategyConfigRow.is_active.is_(True)).limit(1),
        )
        return result.scalar_one_or_none()


# Process-wide singletons (initialized in lifespan).
_service: TradingService | None = None


def init_trading_service(
    registry: BrokerRegistry,
    vault: CredentialVault,
    notifier: NotificationService | None = None,
) -> TradingService:
    global _service
    _service = TradingService(registry, vault, notifier)
    return _service


def get_trading_service() -> TradingService:
    if _service is None:
        raise RuntimeError("TradingService not initialised")
    return _service
