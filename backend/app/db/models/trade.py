from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TradeRow(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    broker_account_id: Mapped[int] = mapped_column(
        ForeignKey("broker_accounts.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    ticket: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    direction: Mapped[str] = mapped_column(String(8), nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lots: Mapped[float] = mapped_column(Float, nullable=False)
    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    exit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    pnl: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    commission: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    swap: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reason: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    # "proven" → opened by the calibrated single-strategy mode; "autonomous"
    # → opened by the free-hand ensemble mode; "manual" → operator clicked
    # Test-сделка / Analyze. Lets the Trades page filter & label rows
    # without joining anything.
    mode: Mapped[str] = mapped_column(String(16), default="manual", nullable=False, index=True)
    # Full markdown explanation that the ensemble emitted - "EMA50>EMA200,
    # ADX 31, +DI > -DI ⇒ LONG with confidence 0.62 (3/4 strategies agree)".
    # Kept as Text so we can render the same reasoning in the history page
    # as we did at open time.
    signal_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Operator's own notes about this trade - written from the Trades page
    # after the fact. "Закрыл руками - был против тренда новостей",
    # "Хорошая работа автономного режима". Free text, no schema.
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
