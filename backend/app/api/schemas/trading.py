from __future__ import annotations

from pydantic import BaseModel, Field


class StartRequest(BaseModel):
    broker_account_id: int = Field(ge=1)


class TradingStatus(BaseModel):
    broker_account_id: int | None
    worker: dict | None


class KillSwitchResult(BaseModel):
    closed_count: int
