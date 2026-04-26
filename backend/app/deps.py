"""Dependency injection helpers shared by routers and services."""

from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.brokers.registry import BrokerRegistry
from app.core.security.vault import CredentialVault
from app.db.session import get_session
from app.services.account_service import AccountService
from app.settings import Settings, get_settings


@lru_cache(maxsize=1)
def get_vault() -> CredentialVault:
    settings = get_settings()
    return CredentialVault(settings.vault_path)


@lru_cache(maxsize=1)
def get_broker_registry() -> BrokerRegistry:
    return BrokerRegistry()


def get_app_settings() -> Settings:
    return get_settings()


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async for session in get_session():
        yield session


def get_account_service(registry: BrokerRegistry = Depends(get_broker_registry)) -> AccountService:
    return AccountService(registry)


def require_unlocked_vault(vault: CredentialVault = Depends(get_vault)) -> CredentialVault:
    """Routes that touch broker credentials must be guarded by this dep."""
    from fastapi import HTTPException, status
    if not vault.is_unlocked:
        raise HTTPException(status.HTTP_423_LOCKED, "Vault is locked")
    return vault
