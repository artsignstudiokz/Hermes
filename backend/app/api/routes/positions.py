from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.broker import PositionOut
from app.core.brokers.registry import BrokerRegistry
from app.db.models import TradeRow
from app.deps import get_broker_registry, get_db_session
from app.services.account_service import AccountService

router = APIRouter()


@router.get("", response_model=list[PositionOut])
async def list_positions(
    registry: BrokerRegistry = Depends(get_broker_registry),
) -> list[PositionOut]:
    svc = AccountService(registry)
    positions = await svc.positions()
    return [
        PositionOut(
            ticket=p.ticket,
            symbol=p.symbol,
            direction=p.direction.value,
            lot_size=p.lot_size,
            entry_price=p.entry_price,
            current_price=p.current_price,
            unrealized_pnl=p.unrealized_pnl,
            swap=p.swap,
            commission=p.commission,
            opened_at=p.opened_at.isoformat(),
        )
        for p in positions
    ]


@router.post("/{ticket}/close")
async def close_position(
    ticket: str,
    registry: BrokerRegistry = Depends(get_broker_registry),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, bool]:
    adapter = registry.get_active()
    if not adapter:
        raise HTTPException(status.HTTP_409_CONFLICT, "No active broker")
    # Snapshot the position BEFORE closing so we can record exit_price
    # and per-trade P&L on the matching TradeRow. After close the
    # ticket disappears from positions_get, so this has to happen first.
    positions = await adapter.get_positions()
    pos = next((p for p in positions if str(p.ticket) == str(ticket)), None)
    ok = await adapter.close_position(ticket)
    if ok:
        await _mark_trade_closed(
            session,
            ticket=ticket,
            exit_price=float(pos.current_price) if pos else None,
            pnl=float(pos.unrealized_pnl) if pos else None,
            reason="manual",
        )
    return {"ok": ok}


async def _mark_trade_closed(
    session: AsyncSession, *, ticket: str,
    exit_price: float | None, pnl: float | None, reason: str,
) -> None:
    """Centralised "the broker closed this ticket, update the row"
    routine. Used by manual close, kill switch, and the worker's
    reconciliation pass.
    """
    rows = (await session.execute(
        select(TradeRow).where(
            TradeRow.ticket == str(ticket),
            TradeRow.closed_at.is_(None),
        ),
    )).scalars().all()
    if not rows:
        return
    now = datetime.now(timezone.utc)
    for row in rows:
        row.closed_at = now
        if exit_price is not None:
            row.exit_price = exit_price
        if pnl is not None:
            row.pnl = pnl
        row.reason = reason
    await session.commit()
