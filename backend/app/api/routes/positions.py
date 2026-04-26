from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.schemas.broker import PositionOut
from app.core.brokers.registry import BrokerRegistry
from app.deps import get_broker_registry
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
) -> dict[str, bool]:
    adapter = registry.get_active()
    if not adapter:
        raise HTTPException(status.HTTP_409_CONFLICT, "No active broker")
    ok = await adapter.close_position(ticket)
    return {"ok": ok}
