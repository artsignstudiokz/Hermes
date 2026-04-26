from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.strategy import (
    PresetOut,
    StrategyConfigOut,
    StrategyParams,
    ValidationIssue,
    ValidationResult,
)
from app.core.strategy.presets import PRESETS
from app.core.strategy.validator import has_errors, validate_strategy
from app.db.models import StrategyConfigRow
from app.deps import get_account_service, get_db_session
from app.services.account_service import AccountService

router = APIRouter()


@router.get("/presets", response_model=list[PresetOut])
async def list_presets() -> list[PresetOut]:
    return [PresetOut(**{
        "id": p.id, "name": p.name, "description": p.description,
        "risk_emoji": p.risk_emoji, "payload": p.payload,
    }) for p in PRESETS]


@router.get("/config", response_model=StrategyConfigOut | None)
async def get_active_config(
    session: AsyncSession = Depends(get_db_session),
) -> StrategyConfigOut | None:
    row = (await session.execute(
        select(StrategyConfigRow).where(StrategyConfigRow.is_active.is_(True)).limit(1),
    )).scalar_one_or_none()
    if not row:
        return None
    return StrategyConfigOut(
        id=row.id, name=row.name, payload=row.payload,
        is_active=row.is_active, source=row.source,
    )


@router.put("/config", response_model=StrategyConfigOut)
async def save_config(
    params: StrategyParams,
    name: str = "Custom",
    source: str = "manual",
    session: AsyncSession = Depends(get_db_session),
    svc: AccountService = Depends(get_account_service),
) -> StrategyConfigOut:
    info = await svc.info()
    equity = info.equity if info else 10_000.0

    issues = validate_strategy(params.model_dump(), equity)
    if has_errors(issues):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"issues": [i.__dict__ for i in issues]},
        )

    # Deactivate previous, save and activate new (parent_id link for rollback).
    current = (await session.execute(
        select(StrategyConfigRow).where(StrategyConfigRow.is_active.is_(True)),
    )).scalars().all()
    parent_id = current[0].id if current else None
    for c in current:
        c.is_active = False

    row = StrategyConfigRow(
        name=name, payload=params.model_dump(), is_active=True,
        source=source, parent_id=parent_id,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)

    return StrategyConfigOut(
        id=row.id, name=row.name, payload=row.payload,
        is_active=row.is_active, source=row.source,
    )


@router.post("/validate", response_model=ValidationResult)
async def validate(
    params: StrategyParams,
    svc: AccountService = Depends(get_account_service),
) -> ValidationResult:
    info = await svc.info()
    equity = info.equity if info else 10_000.0
    issues = validate_strategy(params.model_dump(), equity)
    return ValidationResult(
        issues=[ValidationIssue(field=i.field, severity=i.severity, message=i.message) for i in issues],
        has_errors=has_errors(issues),
    )
