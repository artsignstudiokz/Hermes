"""Broker management — CRUD + connectivity test."""

from __future__ import annotations

import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.broker import (
    BrokerCreateRequest,
    BrokerOut,
    BrokerTestRequest,
    BrokerTestResult,
)
from app.core.brokers.models import BrokerCredentials, BrokerType
from app.core.brokers.registry import BrokerRegistry
from app.core.security.vault import CredentialVault
from app.db.models import BrokerAccount
from app.deps import get_broker_registry, get_db_session, require_unlocked_vault

router = APIRouter()
logger = logging.getLogger(__name__)


def _build_creds(req: BrokerTestRequest) -> BrokerCredentials:
    return BrokerCredentials(
        type=BrokerType(req.type),
        server=req.server,
        login=req.login,
        password=req.password,
        api_key=req.api_key,
        api_secret=req.api_secret,
        api_passphrase=req.api_passphrase,
        testnet=req.testnet,
    )


@router.post("/test", response_model=BrokerTestResult)
async def test(
    req: BrokerTestRequest,
    registry: BrokerRegistry = Depends(get_broker_registry),
    _vault: CredentialVault = Depends(require_unlocked_vault),
) -> BrokerTestResult:
    """Try connecting + fetching balance, then disconnect. Doesn't persist anything."""
    creds = _build_creds(req)
    adapter = registry._build(creds)  # noqa: SLF001 — local build, not registered
    try:
        await adapter.connect()
        info = await adapter.get_account()
        await adapter.disconnect()
        return BrokerTestResult(
            ok=True,
            balance=info.balance,
            currency=info.currency,
            leverage=info.leverage,
            server=info.server,
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("Broker test failed")
        return BrokerTestResult(ok=False, error=str(e))


@router.get("", response_model=list[BrokerOut])
async def list_brokers(
    session: AsyncSession = Depends(get_db_session),
) -> list[BrokerOut]:
    rows = (await session.execute(select(BrokerAccount).order_by(BrokerAccount.id))).scalars().all()
    return [
        BrokerOut(
            id=r.id, type=r.type, name=r.name, server=r.server, login=r.login,
            is_active=r.is_active, is_testnet=r.is_testnet,
        )
        for r in rows
    ]


@router.post("", response_model=BrokerOut, status_code=status.HTTP_201_CREATED)
async def create_broker(
    req: BrokerCreateRequest,
    vault: CredentialVault = Depends(require_unlocked_vault),
    session: AsyncSession = Depends(get_db_session),
) -> BrokerOut:
    vault_key = f"{req.type}:{secrets.token_hex(8)}"
    vault.set(vault_key, {
        "password": req.password,
        "api_key": req.api_key,
        "api_secret": req.api_secret,
        "api_passphrase": req.api_passphrase,
    })
    row = BrokerAccount(
        type=req.type,
        name=req.name,
        server=req.server,
        login=str(req.login) if req.login else None,
        vault_key=vault_key,
        is_active=False,
        is_testnet=req.testnet,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return BrokerOut(
        id=row.id, type=row.type, name=row.name, server=row.server, login=row.login,
        is_active=row.is_active, is_testnet=row.is_testnet,
    )


@router.delete("/{broker_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_broker(
    broker_id: int,
    vault: CredentialVault = Depends(require_unlocked_vault),
    session: AsyncSession = Depends(get_db_session),
    registry: BrokerRegistry = Depends(get_broker_registry),
) -> None:
    row = await session.get(BrokerAccount, broker_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Broker not found")
    await registry.disconnect(broker_id)
    vault.delete(row.vault_key)
    await session.delete(row)
    await session.commit()


@router.post("/{broker_id}/activate", response_model=BrokerOut)
async def activate_broker(
    broker_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> BrokerOut:
    row = await session.get(BrokerAccount, broker_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Broker not found")
    # Deactivate others, activate this one.
    others = (await session.execute(
        select(BrokerAccount).where(BrokerAccount.is_active.is_(True)),
    )).scalars().all()
    for o in others:
        o.is_active = False
    row.is_active = True
    await session.commit()
    return BrokerOut(
        id=row.id, type=row.type, name=row.name, server=row.server, login=row.login,
        is_active=row.is_active, is_testnet=row.is_testnet,
    )
