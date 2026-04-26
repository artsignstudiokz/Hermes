from __future__ import annotations

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class NotificationSub(Base, TimestampMixin):
    __tablename__ = "notification_subs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[str] = mapped_column(String(16), nullable=False)         # webpush / telegram
    endpoint: Mapped[str] = mapped_column(Text, nullable=False)           # full URL or chat_id
    p256dh: Mapped[str | None] = mapped_column(Text, nullable=True)        # webpush public key
    auth: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
