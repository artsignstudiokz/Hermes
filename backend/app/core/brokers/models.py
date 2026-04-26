"""Broker-agnostic data classes — the contract between adapters and strategy.

All units are normalized so the strategy never has to ask "is this a Forex
pip or a crypto tick?". Conversions live inside each adapter.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class Direction(str, Enum):
    LONG = "long"
    SHORT = "short"


class BrokerType(str, Enum):
    MT5 = "mt5"
    BINANCE = "binance"
    BYBIT = "bybit"
    OKX = "okx"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"


@dataclass(slots=True)
class AccountInfo:
    """Snapshot of the broker account at a point in time."""

    balance: float
    equity: float
    margin: float
    free_margin: float
    profit: float
    currency: str = "USD"
    leverage: int = 100
    server: str | None = None
    login: int | None = None


@dataclass(slots=True)
class SymbolInfo:
    """Normalized instrument metadata."""

    symbol: str                # canonical ticker, e.g. "EURUSD" or "BTCUSDT"
    broker_symbol: str         # actual broker name (e.g. "EURUSDm" with suffix)
    tick_size: float           # smallest price increment
    pip_value: float           # 0.0001 for most FX, 0.01 for JPY pairs, varies for crypto
    min_lot: float
    max_lot: float
    lot_step: float
    contract_size: float       # standard lot size in base units
    spread_pips: float = 0.0
    is_crypto: bool = False
    quote_currency: str = "USD"


@dataclass(slots=True)
class Tick:
    symbol: str
    bid: float
    ask: float
    timestamp: datetime
    last: float | None = None
    volume: float | None = None


@dataclass(slots=True)
class Bar:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(slots=True)
class OrderRequest:
    """User-side order spec, before broker translation."""

    symbol: str
    direction: Direction
    lot_size: float
    order_type: OrderType = OrderType.MARKET
    price: float | None = None      # for limit orders
    comment: str = ""
    magic: int = 0xBA1C0           # BAI Core magic number for trade attribution
    deviation_points: int = 20


@dataclass(slots=True)
class Order:
    """Confirmed order from the broker."""

    ticket: str
    symbol: str
    direction: Direction
    lot_size: float
    entry_price: float
    timestamp: datetime
    commission: float = 0.0
    swap: float = 0.0
    comment: str = ""


@dataclass(slots=True)
class Position:
    """Currently open position, normalized."""

    ticket: str
    symbol: str
    direction: Direction
    lot_size: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    swap: float
    commission: float
    opened_at: datetime
    comment: str = ""


@dataclass(slots=True)
class Trade:
    """Closed trade — what hits the trade history table."""

    ticket: str
    symbol: str
    direction: Direction
    lot_size: float
    entry_price: float
    exit_price: float
    pnl: float
    commission: float
    swap: float
    opened_at: datetime
    closed_at: datetime
    reason: str = ""               # TAKE_PROFIT, STOP_LOSS, KILL_SWITCH, etc.


@dataclass(slots=True)
class BrokerCredentials:
    """Free-form bag of secrets — adapter-specific shape, validated inside."""

    type: BrokerType
    server: str | None = None
    login: int | None = None
    password: str | None = None
    api_key: str | None = None
    api_secret: str | None = None
    api_passphrase: str | None = None         # OKX requires this
    testnet: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


# Common FX pair configurations
DEFAULT_FX_PAIRS = [
    "EURUSD", "GBPUSD", "EURCHF", "EURJPY", "USDCHF", "USDJPY",
    "AUDUSD", "NZDUSD", "USDCAD",
]
