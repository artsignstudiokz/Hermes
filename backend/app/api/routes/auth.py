"""Auth + master-password endpoints. Backed by CredentialVault (Argon2id + Fernet)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.security.jwt_service import issue_token
from app.core.security.vault import CredentialVault, VaultError, VaultLocked
from app.deps import get_app_settings, get_vault
from app.settings import Settings

router = APIRouter()


class AuthState(BaseModel):
    first_run: bool
    locked: bool
    lockout_until: datetime | None = None


class SetupRequest(BaseModel):
    master_password: str = Field(min_length=6, max_length=128)


class UnlockRequest(BaseModel):
    master_password: str = Field(min_length=1, max_length=128)


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6, max_length=128)


class TokenResponse(BaseModel):
    token: str
    expires_at: datetime


@router.get("/state", response_model=AuthState)
async def state(vault: CredentialVault = Depends(get_vault)) -> AuthState:
    return AuthState(
        first_run=not vault.exists(),
        locked=not vault.is_unlocked,
        lockout_until=vault.lockout_until,
    )


@router.post("/setup-master-password", response_model=TokenResponse)
async def setup(
    body: SetupRequest,
    vault: CredentialVault = Depends(get_vault),
    settings: Settings = Depends(get_app_settings),
) -> TokenResponse:
    if vault.exists():
        raise HTTPException(status.HTTP_409_CONFLICT, "Master password already set")
    vault.create(body.master_password)
    return _issue(settings)


@router.post("/unlock", response_model=TokenResponse)
async def unlock(
    body: UnlockRequest,
    vault: CredentialVault = Depends(get_vault),
    settings: Settings = Depends(get_app_settings),
) -> TokenResponse:
    try:
        vault.unlock(body.master_password)
    except VaultLocked as e:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, str(e)) from e
    except VaultError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(e)) from e
    return _issue(settings)


@router.post("/lock")
async def lock(vault: CredentialVault = Depends(get_vault)) -> dict[str, bool]:
    vault.lock()
    return {"locked": True}


@router.post("/change-master-password", response_model=TokenResponse)
async def change_password(
    body: ChangePasswordRequest,
    vault: CredentialVault = Depends(get_vault),
    settings: Settings = Depends(get_app_settings),
) -> TokenResponse:
    try:
        vault.change_password(body.old_password, body.new_password)
    except VaultError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(e)) from e
    return _issue(settings)


def _issue(settings: Settings) -> TokenResponse:
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_ttl_minutes)
    return TokenResponse(token=issue_token(expires_at=expires), expires_at=expires)
