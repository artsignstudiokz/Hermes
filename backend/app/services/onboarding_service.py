"""Onboarding state — derived from existing artefacts (vault, brokers, strategy)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.onboarding import OnboardingStatus
from app.core.security.vault import CredentialVault
from app.db.models import BrokerAccount, StrategyConfigRow


async def compute_status(
    session: AsyncSession,
    vault: CredentialVault,
    is_running: bool,
) -> OnboardingStatus:
    vault_initialised = vault.exists()
    if not vault_initialised:
        return OnboardingStatus(
            first_run=True, vault_initialised=False, has_broker=False,
            has_strategy=False, is_running=False, next_step="master_password",
        )

    broker_count = (await session.execute(
        select(BrokerAccount.id).limit(1),
    )).first()
    has_broker = broker_count is not None

    strategy = (await session.execute(
        select(StrategyConfigRow.id).where(StrategyConfigRow.is_active.is_(True)).limit(1),
    )).first()
    has_strategy = strategy is not None

    if not has_broker:
        next_step = "broker"
    elif not has_strategy:
        next_step = "strategy"
    elif not is_running:
        next_step = "start"
    else:
        next_step = "done"

    return OnboardingStatus(
        first_run=False,
        vault_initialised=vault_initialised,
        has_broker=has_broker,
        has_strategy=has_strategy,
        is_running=is_running,
        next_step=next_step,
    )
