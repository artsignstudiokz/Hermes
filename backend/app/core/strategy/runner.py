"""StrategyRunner — bridges legacy GridStrategy to the BrokerAdapter contract.

The legacy strategy is broker-agnostic: it consumes a price dict and emits
action dicts. The runner:
  1. Pulls OHLCV via the adapter.
  2. Computes indicators.
  3. Calls strategy.on_bar().
  4. Translates actions into broker calls (place_order / close_all).
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from app.core.brokers.base import BrokerAdapter
from app.core.brokers.models import Direction, OrderRequest, SymbolInfo

# Make the legacy package importable for the strategy core.
LEGACY_DIR = Path(__file__).resolve().parents[3].parent / "legacy"
if LEGACY_DIR.exists() and str(LEGACY_DIR) not in sys.path:
    sys.path.insert(0, str(LEGACY_DIR))

logger = logging.getLogger(__name__)


def _import_legacy():
    """Lazy-import legacy modules so backend works even without legacy on path."""
    from config import GridConfig, PairConfig  # type: ignore[import-not-found]
    from indicators import compute_indicators, correlation_matrix  # type: ignore[import-not-found]
    from risk_manager import RiskManager  # type: ignore[import-not-found]
    from strategy import GridStrategy  # type: ignore[import-not-found]
    return GridConfig, PairConfig, compute_indicators, correlation_matrix, RiskManager, GridStrategy


class StrategyRunner:
    def __init__(
        self,
        adapter: BrokerAdapter,
        params: dict,
        symbols: list[str],
        timeframe: str = "1h",
        commission_per_lot: float = 7.0,
        on_action: "callable[..., None] | None" = None,
    ) -> None:
        GridConfig, PairConfig, compute_indicators, corr_fn, RiskManager, GridStrategy = _import_legacy()

        self._adapter = adapter
        self._symbols = symbols
        self._timeframe = timeframe
        self._on_action = on_action

        # Build the GridConfig dataclass from a dict.
        self._grid_cfg = GridConfig()
        for k, v in params.items():
            if hasattr(self._grid_cfg, k):
                setattr(self._grid_cfg, k, v)
        self._grid_cfg.__post_init__()  # re-validate

        self._compute_indicators = compute_indicators
        self._corr_fn = corr_fn

        self._pair_cfgs: list = []  # PairConfig list
        self._strategy = None       # initialised once we have SymbolInfo
        self._risk = None
        self._PairConfig = PairConfig
        self._GridStrategy = GridStrategy
        self._RiskManager = RiskManager
        self._commission = commission_per_lot

    async def setup(self) -> None:
        """Resolve symbol metadata and instantiate the underlying strategy."""
        infos = await self._adapter.get_symbols(self._symbols)
        info_map: dict[str, SymbolInfo] = {i.symbol: i for i in infos}
        self._pair_cfgs = []
        for s in self._symbols:
            info = info_map.get(s)
            if info is None:
                logger.warning("Symbol %s unavailable on broker — skipping", s)
                continue
            self._pair_cfgs.append(self._PairConfig(
                symbol=s,
                pip_value=info.pip_value,
                spread_pips=info.spread_pips or 1.5,
                min_lot=info.min_lot,
                max_lot=info.max_lot,
                contract_size=info.contract_size,
            ))
        if not self._pair_cfgs:
            raise RuntimeError("No tradable symbols resolved by adapter")

        self._risk = self._RiskManager(self._grid_cfg, self._pair_cfgs)
        self._strategy = self._GridStrategy(
            self._grid_cfg, self._risk, self._pair_cfgs,
            commission_per_lot=self._commission,
        )

    async def tick(self) -> list[dict]:
        """Run one analysis cycle. Returns list of actions executed."""
        if self._strategy is None:
            await self.setup()

        account = await self._adapter.get_account()
        equity = account.equity

        prices: dict[str, dict] = {}
        close_dict: dict[str, pd.Series] = {}
        for pair in self._pair_cfgs:
            try:
                df = await self._adapter.get_ohlcv(pair.symbol, self._timeframe, 300)
                df = self._compute_indicators(
                    df,
                    atr_period=self._grid_cfg.atr_period,
                    ema_fast=self._grid_cfg.ema_fast,
                    ema_slow=self._grid_cfg.ema_slow,
                )
                last = df.iloc[-1]
                prices[pair.symbol] = {
                    "open": float(last["open"]),
                    "high": float(last["high"]),
                    "low": float(last["low"]),
                    "close": float(last["close"]),
                    "atr": float(last["atr"]) if not pd.isna(last["atr"]) else 0.0,
                    "trend": int(last["trend"]) if not pd.isna(last["trend"]) else 0,
                }
                close_dict[pair.symbol] = df["close"]
            except Exception:
                logger.exception("Data fetch failed for %s", pair.symbol)

        if not prices:
            return []

        corr_matrix = None
        if len(close_dict) > 1:
            corr_matrix = self._corr_fn(close_dict, self._grid_cfg.correlation_window)

        tz_offset = getattr(self._grid_cfg, "timezone_offset_utc", 3)
        timestamp = pd.Timestamp.now(tz=timezone(timedelta(hours=tz_offset)))
        assert self._strategy is not None
        actions = self._strategy.on_bar(timestamp, prices, equity, corr_matrix)

        executed: list[dict] = []
        for action in actions:
            if action["action"] == "open":
                direction = Direction.LONG if action["direction"] == "long" else Direction.SHORT
                order = await self._adapter.place_order(OrderRequest(
                    symbol=action["symbol"],
                    direction=direction,
                    lot_size=action["lot_size"],
                    comment=f"hermes_L{action['level']}",
                ))
                if order is not None:
                    # Update the strategy's internal order_id to the broker ticket.
                    for state in self._strategy.pair_states.values():
                        for o in state.active_orders:
                            if o.order_id == action["order_id"]:
                                o.order_id = order.ticket
                    action["broker_ticket"] = order.ticket
                    executed.append(action)
                    if self._on_action:
                        self._on_action(action)
            elif action["action"] == "close_basket":
                closed = await self._adapter.close_all(action["symbol"])
                action["closed_count"] = closed
                executed.append(action)
                if self._on_action:
                    self._on_action(action)
        return executed

    @property
    def grid_config(self) -> object:
        return self._grid_cfg

    @property
    def symbols(self) -> list[str]:
        return [p.symbol for p in self._pair_cfgs]

    def portfolio_state(self) -> dict:
        return self._strategy.get_portfolio_state() if self._strategy else {}
