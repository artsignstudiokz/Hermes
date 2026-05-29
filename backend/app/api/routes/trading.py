from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.schemas.trading import KillSwitchResult, StartRequest, TradingStatus
from app.deps import require_unlocked_vault
from app.services.trading_service import TradingService, get_trading_service

router = APIRouter()


class ManualOpenRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    direction: str = Field(pattern="^(long|short)$")
    lot_size: float = Field(gt=0, le=100)
    comment: str = "manual_test"


class ManualOpenResult(BaseModel):
    ticket: str
    symbol: str
    direction: str
    lot_size: float
    entry_price: float | None = None


class AnalyzeRequest(BaseModel):
    lot_size: float = Field(default=0.01, gt=0, le=100)
    dry_run: bool = False


class AnalyzeResult(BaseModel):
    opened: bool
    reason: str
    ticket: str | None = None
    best: dict | None = None
    reports: list[dict]


@router.get("/status", response_model=TradingStatus)
async def status_(
    svc: TradingService = Depends(get_trading_service),
) -> TradingStatus:
    return TradingStatus(**svc.status)


@router.post("/start", response_model=TradingStatus)
async def start(
    req: StartRequest,
    svc: TradingService = Depends(get_trading_service),
    _vault = Depends(require_unlocked_vault),
) -> TradingStatus:
    try:
        return TradingStatus(**(await svc.start(req.broker_account_id)))
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e


@router.post("/stop", response_model=TradingStatus)
async def stop(svc: TradingService = Depends(get_trading_service)) -> TradingStatus:
    return TradingStatus(**(await svc.stop()))


@router.post("/pause", response_model=TradingStatus)
async def pause(svc: TradingService = Depends(get_trading_service)) -> TradingStatus:
    return TradingStatus(**(await svc.pause()))


@router.post("/resume", response_model=TradingStatus)
async def resume(svc: TradingService = Depends(get_trading_service)) -> TradingStatus:
    return TradingStatus(**(await svc.resume()))


@router.post("/kill-switch", response_model=KillSwitchResult)
async def kill_switch(svc: TradingService = Depends(get_trading_service)) -> KillSwitchResult:
    closed = await svc.kill_switch()
    return KillSwitchResult(closed_count=closed)


@router.post("/enable-trading", response_model=TradingStatus)
async def enable_trading(
    svc: TradingService = Depends(get_trading_service),
    _vault = Depends(require_unlocked_vault),
) -> TradingStatus:
    try:
        return TradingStatus(**svc.enable_trading())
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e


@router.post("/disable-trading", response_model=TradingStatus)
async def disable_trading(
    svc: TradingService = Depends(get_trading_service),
) -> TradingStatus:
    try:
        return TradingStatus(**svc.disable_trading())
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e


@router.post("/analyze", response_model=AnalyzeResult)
async def analyze(
    req: AnalyzeRequest,
    svc: TradingService = Depends(get_trading_service),
    _vault = Depends(require_unlocked_vault),
) -> AnalyzeResult:
    """Scan all symbols from the active config, run the indicator
    ensemble, pick the best signal, and either open the position
    (dry_run=false) or return only the analysis (dry_run=true).
    """
    try:
        result = await svc.analyze_and_trade(req.lot_size, req.dry_run)
        return AnalyzeResult(
            opened=result.get("opened", False),
            reason=result.get("reason", ""),
            ticket=result.get("ticket"),
            best=result.get("best"),
            reports=result.get("reports", []),
        )
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e


@router.post("/test-order", response_model=ManualOpenResult)
async def test_order(
    req: ManualOpenRequest,
    svc: TradingService = Depends(get_trading_service),
    _vault = Depends(require_unlocked_vault),
) -> ManualOpenResult:
    try:
        result = await svc.manual_open(req.symbol, req.direction, req.lot_size, req.comment)
        return ManualOpenResult(**result)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e
