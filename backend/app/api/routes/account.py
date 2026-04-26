from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.broker import AccountInfoOut
from app.deps import get_account_service, get_db_session
from app.services.account_service import AccountService

router = APIRouter()


@router.get("/info", response_model=AccountInfoOut | None)
async def info(svc: AccountService = Depends(get_account_service)) -> AccountInfoOut | None:
    info = await svc.info()
    if info is None:
        return None
    return AccountInfoOut(
        balance=info.balance,
        equity=info.equity,
        margin=info.margin,
        free_margin=info.free_margin,
        profit=info.profit,
        currency=info.currency,
        leverage=info.leverage,
        server=info.server,
        login=info.login,
    )


@router.get("/equity-history")
async def equity_history(
    days: int = 30,
    broker_account_id: int | None = None,
    svc: AccountService = Depends(get_account_service),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    if broker_account_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "broker_account_id required")
    points = await svc.equity_history(session, broker_account_id, days=days)
    return [
        {
            "ts": p.ts.isoformat(),
            "equity": p.equity,
            "balance": p.balance,
            "drawdown_pct": p.drawdown_pct,
        }
        for p in points
    ]
