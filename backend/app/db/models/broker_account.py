from __future__ import annotations

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class BrokerAccount(Base, TimestampMixin):
    __tablename__ = "broker_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[str] = mapped_column(String(16), nullable=False)            # mt5/binance/bybit/okx
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    server: Mapped[str | None] = mapped_column(String(128), nullable=True)
    login: Mapped[str | None] = mapped_column(String(64), nullable=True)     # str: handles MT5 ints + ccxt key prefixes
    vault_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_testnet: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
