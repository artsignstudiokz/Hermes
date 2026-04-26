from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.onboarding import (
    MT5InstallationOut,
    MT5ServerOut,
    OnboardingStatus,
)
from app.core.brokers.mt5_servers import list_installations, list_servers
from app.core.security.vault import CredentialVault
from app.deps import get_db_session, get_vault
from app.services.onboarding_service import compute_status
from app.services.trading_service import get_trading_service

router = APIRouter()


@router.get("/status", response_model=OnboardingStatus)
async def status(
    session: AsyncSession = Depends(get_db_session),
    vault: CredentialVault = Depends(get_vault),
) -> OnboardingStatus:
    is_running = bool(get_trading_service().status.get("worker", {}).get("running"))
    return await compute_status(session, vault, is_running)


@router.get("/mt5/servers", response_model=list[MT5ServerOut])
async def mt5_servers() -> list[MT5ServerOut]:
    return [MT5ServerOut(name=s.name, broker=s.broker, terminal_path=s.terminal_path)
            for s in list_servers()]


@router.get("/mt5/installations", response_model=list[MT5InstallationOut])
async def mt5_installations() -> list[MT5InstallationOut]:
    return [MT5InstallationOut(path=i.path, data_dir=i.data_dir, is_portable=i.is_portable)
            for i in list_installations()]
