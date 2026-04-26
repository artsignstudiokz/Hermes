from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class WebPushSubscribeRequest(BaseModel):
    endpoint: str
    p256dh: str
    auth: str


class TelegramSubscribeRequest(BaseModel):
    bot_token: str
    chat_id: str


class NotificationSubOut(BaseModel):
    id: int
    type: Literal["webpush", "telegram"]
    endpoint_short: str           # truncated for display
    enabled: bool


class VapidPublicKey(BaseModel):
    key: str


class TestResult(BaseModel):
    webpush: int
    telegram: int
