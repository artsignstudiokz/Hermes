from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class PairRegimeOut(BaseModel):
    symbol: str
    regime: Literal["trend", "flat", "high_vol"]
    adx: float
    atr_pct: float
    ema_aligned: bool
    hurst: float | None
    confidence: float


class GlobalRegimeOut(BaseModel):
    regime: Literal["trend", "flat", "high_vol"]
    counts: dict[str, int]
    per_pair: list[PairRegimeOut]


class CalibrationRunOut(BaseModel):
    id: int
    ts: str
    regime: str
    challenger_won: bool
    applied: bool
    walk_forward_score: float
    before_params: dict
    after_params: dict


class BacktestRunOut(BaseModel):
    id: int
    status: str
    params: dict
    metrics: dict | None
    started_at: str | None
    finished_at: str | None


class BacktestStartRequest(BaseModel):
    params: dict
    symbols: list[str]
    days: int = 90


class OptimizeStartRequest(BaseModel):
    base_params: dict
    symbols: list[str]
    n_trials: int = 100
    days: int = 90
