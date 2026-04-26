from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.adaptive import BacktestRunOut, BacktestStartRequest
from app.db.models import BacktestRun
from app.deps import get_db_session
from app.services.backtest_service import BacktestService, get_backtest_service

router = APIRouter()


@router.post("/run")
async def run(
    req: BacktestStartRequest,
    svc: BacktestService = Depends(get_backtest_service),
) -> dict[str, int]:
    run_id = await svc.submit(req.params, req.symbols, req.days)
    return {"run_id": run_id}


@router.get("/runs", response_model=list[BacktestRunOut])
async def list_runs(
    limit: int = 20,
    session: AsyncSession = Depends(get_db_session),
) -> list[BacktestRunOut]:
    rows = (await session.execute(
        select(BacktestRun).order_by(desc(BacktestRun.id)).limit(limit),
    )).scalars().all()
    return [
        BacktestRunOut(
            id=r.id, status=r.status, params=r.params, metrics=r.metrics,
            started_at=r.started_at.isoformat() if r.started_at else None,
            finished_at=r.finished_at.isoformat() if r.finished_at else None,
        )
        for r in rows
    ]


@router.get("/{run_id}", response_model=BacktestRunOut)
async def get_run(
    run_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> BacktestRunOut:
    row = await session.get(BacktestRun, run_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found")
    return BacktestRunOut(
        id=row.id, status=row.status, params=row.params, metrics=row.metrics,
        started_at=row.started_at.isoformat() if row.started_at else None,
        finished_at=row.finished_at.isoformat() if row.finished_at else None,
    )
