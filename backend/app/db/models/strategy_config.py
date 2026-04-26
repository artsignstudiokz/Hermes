from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class StrategyConfigRow(Base, TimestampMixin):
    __tablename__ = "strategy_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source: Mapped[str] = mapped_column(String(32), default="manual", nullable=False)
    # manual / preset / optimizer / auto_calibrator
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("strategy_configs.id", ondelete="SET NULL"), nullable=True,
    )
