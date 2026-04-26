from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, JSON, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class BacktestRun(Base, TimestampMixin):
    __tablename__ = "backtest_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    params: Mapped[dict] = mapped_column(JSON, nullable=False)
    metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    equity_blob: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)  # gzipped CSV
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
