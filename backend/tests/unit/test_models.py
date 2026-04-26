"""Broker domain dataclasses — round-trip + enum stability."""

from __future__ import annotations

from datetime import datetime, timezone

from app.core.brokers.models import (
    BrokerCredentials,
    BrokerType,
    Direction,
    Order,
    OrderRequest,
    Position,
    SymbolInfo,
    Tick,
    Trade,
)


def test_direction_string_values() -> None:
    assert Direction.LONG.value == "long"
    assert Direction.SHORT.value == "short"


def test_broker_type_includes_all_supported() -> None:
    assert BrokerType.MT5.value == "mt5"
    assert {t.value for t in BrokerType} == {"mt5", "binance", "bybit", "okx"}


def test_credentials_default_extra() -> None:
    c = BrokerCredentials(type=BrokerType.MT5)
    assert c.extra == {}
    c.extra["foo"] = 1
    assert BrokerCredentials(type=BrokerType.MT5).extra == {}    # not shared


def test_order_request_magic_default() -> None:
    req = OrderRequest(symbol="EURUSD", direction=Direction.LONG, lot_size=0.01)
    # Magic = 0xBA1C0 (BAI Core attribution).
    assert req.magic == 0xBA1C0
    assert req.deviation_points == 20


def test_models_construct() -> None:
    now = datetime.now(timezone.utc)
    SymbolInfo(
        symbol="EURUSD", broker_symbol="EURUSDm", tick_size=0.00001, pip_value=0.0001,
        min_lot=0.01, max_lot=10, lot_step=0.01, contract_size=100_000,
    )
    Tick(symbol="EURUSD", bid=1.1, ask=1.1001, timestamp=now)
    Order(ticket="1", symbol="EURUSD", direction=Direction.LONG, lot_size=0.01,
          entry_price=1.1, timestamp=now)
    Position(ticket="1", symbol="EURUSD", direction=Direction.LONG, lot_size=0.01,
             entry_price=1.1, current_price=1.1001, unrealized_pnl=0.1,
             swap=0, commission=0, opened_at=now)
    Trade(ticket="1", symbol="EURUSD", direction=Direction.LONG, lot_size=0.01,
          entry_price=1.1, exit_price=1.11, pnl=10, commission=0, swap=0,
          opened_at=now, closed_at=now)
