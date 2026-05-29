from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.broker import TradeOut
from app.db.models import TradeRow
from app.deps import get_db_session


class NotesUpdate(BaseModel):
    notes: str = Field(default="", max_length=4000)

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
            notes=t.notes,
        )
        for t in rows
    ]


@router.patch("/{trade_id}/notes", response_model=TradeOut)
async def update_notes(
    trade_id: int,
    body: NotesUpdate,
    session: AsyncSession = Depends(get_db_session),
) -> TradeOut:
    """Operator's free-form journal entry attached to a single trade.
    Sent as plain text; null/empty clears the existing note.
    """
    row = await session.get(TradeRow, trade_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Trade not found")
    row.notes = body.notes.strip() or None
    await session.commit()
    await session.refresh(row)
    return TradeOut(
        id=row.id, ticket=row.ticket, symbol=row.symbol, direction=row.direction,
        level=row.level, lots=row.lots, entry_price=row.entry_price,
        exit_price=row.exit_price, pnl=row.pnl, commission=row.commission,
        swap=row.swap, opened_at=row.opened_at.isoformat(),
        closed_at=row.closed_at.isoformat() if row.closed_at else None,
        reason=row.reason, mode=row.mode, signal_reason=row.signal_reason,
        notes=row.notes,
    )


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


@router.get("/export.csv")
async def export_csv(
    year: int | None = Query(default=None, ge=2020, le=2100),
    session: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    """Export all closed trades for the given calendar year as CSV
    with FIFO-style per-trade P&L. If `year` is omitted, exports
    every closed trade in the DB. Tax tools (KZ KGD, US 1099-B,
    EU MiFID equivalents) accept this format directly.

    Columns mirror what reporting workflows expect: open/close
    timestamps in ISO 8601, side, lots, prices, gross P&L, commission
    and swap split out, net P&L last.
    """
    stmt = select(TradeRow).where(TradeRow.closed_at.is_not(None))
    if year is not None:
        start = datetime(year, 1, 1, tzinfo=timezone.utc)
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        stmt = stmt.where(TradeRow.opened_at >= start, TradeRow.opened_at < end)
    stmt = stmt.order_by(TradeRow.opened_at.asc())

    rows = (await session.execute(stmt)).scalars().all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "ticket", "symbol", "side", "lots",
        "opened_at_utc", "entry_price",
        "closed_at_utc", "exit_price",
        "gross_pnl", "commission", "swap", "net_pnl",
        "mode", "reason", "signal_reason",
    ])
    for r in rows:
        net = float(r.pnl) - float(r.commission) - float(r.swap)
        writer.writerow([
            r.ticket, r.symbol, r.direction, f"{r.lots:.4f}",
            r.opened_at.isoformat(), f"{r.entry_price:.5f}",
            r.closed_at.isoformat() if r.closed_at else "",
            f"{r.exit_price:.5f}" if r.exit_price is not None else "",
            f"{r.pnl:.2f}", f"{r.commission:.2f}", f"{r.swap:.2f}", f"{net:.2f}",
            r.mode or "", r.reason or "", (r.signal_reason or "")[:200],
        ])
    buf.seek(0)
    label = f"{year}" if year else "all"
    filename = f"hermes-trades-{label}.csv"
    return StreamingResponse(
        iter([buf.getvalue().encode("utf-8")]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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
