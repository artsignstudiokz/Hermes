from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.deps import require_unlocked_vault
from app.services.tunnel_service import TunnelService, get_tunnel_service
from app.settings import Settings, get_settings

router = APIRouter()


class TunnelStatus(BaseModel):
    active: bool
    url: str | None
    qr: str | None
    pin: str | None
    pin_age_hours: float


@router.get("/status", response_model=TunnelStatus)
async def status(svc: TunnelService = Depends(get_tunnel_service)) -> TunnelStatus:
    return TunnelStatus(**svc.status)


@router.post("/start", response_model=TunnelStatus)
async def start(
    settings: Settings = Depends(get_settings),
    svc: TunnelService = Depends(get_tunnel_service),
    _vault = Depends(require_unlocked_vault),
) -> TunnelStatus:
    if settings.port <= 0:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Backend port unknown")
    try:
        return TunnelStatus(**svc.start(settings.port))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(e)) from e


@router.post("/stop")
async def stop(svc: TunnelService = Depends(get_tunnel_service)) -> dict[str, bool]:
    svc.stop()
    return {"ok": True}


@router.post("/regenerate-pin", response_model=TunnelStatus)
async def regenerate_pin(svc: TunnelService = Depends(get_tunnel_service)) -> TunnelStatus:
    svc.regenerate_pin()
    return TunnelStatus(**svc.status)
