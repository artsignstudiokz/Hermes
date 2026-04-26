from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.adaptive import (
    CalibrationRunOut,
    GlobalRegimeOut,
    PairRegimeOut,
)
from app.core.adaptive.calibrator import rollback_to_parent, run_calibration
from app.core.adaptive.regime import classify_global, classify_pair
from app.core.brokers.registry import BrokerRegistry
from app.db.models import CalibrationRun, StrategyConfigRow
from app.deps import get_broker_registry, get_db_session

router = APIRouter()


@router.get("/regime", response_model=GlobalRegimeOut)
async def regime(
    registry: BrokerRegistry = Depends(get_broker_registry),
    session: AsyncSession = Depends(get_db_session),
) -> GlobalRegimeOut:
    adapter = registry.get_active()
    if adapter is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "No active broker")

    cfg = (await session.execute(
        select(StrategyConfigRow).where(StrategyConfigRow.is_active.is_(True)).limit(1),
    )).scalar_one_or_none()
    symbols = (cfg.payload.get("symbols") if cfg else None) or [
        "EURUSD", "GBPUSD", "EURCHF", "EURJPY", "USDCHF", "USDJPY",
    ]

    per_pair = []
    for s in symbols:
        try:
            df = await adapter.get_ohlcv(s, "4h", 200)
            per_pair.append(classify_pair(s, df))
        except Exception:
            continue

    g = classify_global(per_pair)
    return GlobalRegimeOut(
        regime=g.regime,
        counts=g.counts,
        per_pair=[PairRegimeOut(**p.__dict__) for p in g.per_pair],
    )


@router.get("/calibration/runs", response_model=list[CalibrationRunOut])
async def list_runs(
    limit: int = 20,
    session: AsyncSession = Depends(get_db_session),
) -> list[CalibrationRunOut]:
    rows = (await session.execute(
        select(CalibrationRun).order_by(desc(CalibrationRun.ts)).limit(limit),
    )).scalars().all()
    return [
        CalibrationRunOut(
            id=r.id, ts=r.ts.isoformat(), regime=r.regime,
            challenger_won=r.challenger_won, applied=r.applied,
            walk_forward_score=r.walk_forward_score,
            before_params=r.before_params, after_params=r.after_params,
        )
        for r in rows
    ]


@router.post("/calibration/run-now")
async def run_now(
    registry: BrokerRegistry = Depends(get_broker_registry),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    adapter = registry.get_active()
    if adapter is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "No active broker")
    cfg = (await session.execute(
        select(StrategyConfigRow).where(StrategyConfigRow.is_active.is_(True)).limit(1),
    )).scalar_one_or_none()
    if cfg is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "No active strategy config")
    symbols = cfg.payload.get("symbols") or [
        "EURUSD", "GBPUSD", "EURCHF", "EURJPY", "USDCHF", "USDJPY",
    ]

    asyncio.create_task(run_calibration(adapter, cfg.payload, symbols))
    return {"started": True}


@router.post("/calibration/rollback")
async def rollback() -> dict[str, bool]:
    ok = await rollback_to_parent()
    return {"ok": ok}
