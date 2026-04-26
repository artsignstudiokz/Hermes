from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class BrokerTestRequest(BaseModel):
    type: Literal["mt5", "binance", "bybit", "okx"]
    server: str | None = None
    login: int | None = None
    password: str | None = None
    api_key: str | None = None
    api_secret: str | None = None
    api_passphrase: str | None = None
    testnet: bool = False


class BrokerCreateRequest(BrokerTestRequest):
    name: str = Field(min_length=1, max_length=64)


class BrokerOut(BaseModel):
    id: int
    type: str
    name: str
    server: str | None
    login: str | None
    is_active: bool
    is_testnet: bool


class BrokerTestResult(BaseModel):
    ok: bool
    balance: float | None = None
    currency: str | None = None
    leverage: int | None = None
    server: str | None = None
    error: str | None = None


class AccountInfoOut(BaseModel):
    balance: float
    equity: float
    margin: float
    free_margin: float
    profit: float
    currency: str
    leverage: int
    server: str | None
    login: int | None


class PositionOut(BaseModel):
    ticket: str
    symbol: str
    direction: str
    lot_size: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    swap: float
    commission: float
    opened_at: str


class TradeOut(BaseModel):
    id: int
    ticket: str
    symbol: str
    direction: str
    level: int
    lots: float
    entry_price: float
    exit_price: float | None
    pnl: float
    commission: float
    swap: float
    opened_at: str
    closed_at: str | None
    reason: str
