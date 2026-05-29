from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.broker import TradeOut
from app.db.models import TradeRow
from app.deps import get_db_session

router = APIRouter()


@router.get("", response_model=list[TradeOut])
async def list_trades(
    limit: int = Query(default=200, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
    symbol: str | None = None,
    days: int = Query(default=30, ge=1, le=365),
    session: AsyncSession = Depends(get_db_session),
) -> list[TradeOut]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    conditions = [TradeRow.opened_at >= since]
    if symbol:
        conditions.append(TradeRow.symbol == symbol)
    stmt = (
        select(TradeRow)
        .where(and_(*conditions))
        .order_by(TradeRow.opened_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [
        TradeOut(
            id=t.id,
            ticket=t.ticket,
            symbol=t.symbol,
            direction=t.direction,
            level=t.level,
            lots=t.lots,
            entry_price=t.entry_price,
            exit_price=t.exit_price,
            pnl=t.pnl,
            commission=t.commission,
            swap=t.swap,
            opened_at=t.opened_at.isoformat(),
            closed_at=t.closed_at.isoformat() if t.closed_at else None,
            reason=t.reason,
            mode=t.mode,
            signal_reason=t.signal_reason,
        )
        for t in rows
    ]


@router.get("/stats")
async def stats(
    days: int = Query(default=30, ge=1, le=365),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = select(
        func.count(TradeRow.id),
        func.coalesce(func.sum(TradeRow.pnl), 0.0),
        func.coalesce(func.sum(TradeRow.commission), 0.0),
    ).where(TradeRow.opened_at >= since)
    total, pnl_sum, commission_sum = (await session.execute(stmt)).one()

    win_stmt = select(func.count(TradeRow.id)).where(
        TradeRow.opened_at >= since, TradeRow.pnl > 0,
    )
    wins = (await session.execute(win_stmt)).scalar_one()

    return {
        "total": total,
        "wins": wins,
        "win_rate": (wins / total) if total else 0.0,
        "pnl_total": float(pnl_sum),
        "commission_total": float(commission_sum),
    }


@router.get("/stats-by-mode")
async def stats_by_mode(
    days: int = Query(default=30, ge=1, le=365),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Per-mode rollup so the Dashboard can show "Проверенный: +$120, 4
    сделок" and "Автономный: -$30, 7 сделок" as separate cards."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = (
        select(
            TradeRow.mode,
            func.count(TradeRow.id),
            func.coalesce(func.sum(TradeRow.pnl), 0.0),
            func.coalesce(
                func.sum(case((TradeRow.pnl > 0, 1), else_=0)), 0,
            ),
        )
        .where(TradeRow.opened_at >= since)
        .group_by(TradeRow.mode)
    )
    rows = (await session.execute(stmt)).all()
    by_mode: dict[str, dict] = {}
    for mode, total, pnl_sum, wins in rows:
        by_mode[mode] = {
            "total": int(total),
            "wins": int(wins),
            "win_rate": (wins / total) if total else 0.0,
            "pnl_total": float(pnl_sum),
        }
    # Ensure every known mode is present (frontend can render zero-state).
    for m in ("proven", "autonomous", "manual"):
        by_mode.setdefault(m, {"total": 0, "wins": 0, "win_rate": 0.0, "pnl_total": 0.0})
    return {"days": days, "modes": by_mode}
