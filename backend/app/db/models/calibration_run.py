from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CalibrationRun(Base):
    __tablename__ = "calibration_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    regime: Mapped[str] = mapped_column(String(16), nullable=False)
    before_params: Mapped[dict] = mapped_column(JSON, nullable=False)
    after_params: Mapped[dict] = mapped_column(JSON, nullable=False)
    walk_forward_score: Mapped[float] = mapped_column(Float, nullable=False)
    challenger_won: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    applied: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
