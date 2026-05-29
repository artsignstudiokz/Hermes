"""Application startup/shutdown hooks."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.brokers.registry import BrokerRegistry
from app.core.notifications.service import init_notification_service
from app.core.scheduler.apscheduler import init_scheduler
from app.db.session import init_db
from app.deps import get_broker_registry, get_vault
from app.services.backtest_service import init_backtest_service
from app.services.optimize_service import init_optimize_service
from app.services.trading_service import init_trading_service
from app.settings import get_settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.ensure_dirs()
    logger.info("Hermes backend starting (data_dir=%s)", settings.data_dir)

    # DB
    await init_db()

    # Vault + broker registry + trading/backtest/optimize service singletons.
    vault = get_vault()

    # Passwordless mode (v1.0.31+): no master-password screen for fresh
    # installs. Create or auto-unlock with the fixed app-derived key so
    # the operator goes straight from splash to Dashboard. Users who
    # previously set a master password keep the old unlock flow - we
    # never overwrite or migrate their vault without consent.
    if not vault.exists():
        try:
            vault.create_passwordless()
            logger.info("Auto-created passwordless vault on first run")
        except Exception:  # noqa: BLE001
            logger.exception("Failed to auto-create passwordless vault")
    else:
        if vault.try_auto_unlock():
            logger.info("Auto-unlocked vault with app key (passwordless mode)")
        else:
            logger.info("Vault is password-protected; awaiting user unlock")

    registry: BrokerRegistry = get_broker_registry()
    notifier = init_notification_service(vault, settings)
    init_trading_service(registry, vault, notifier)
    init_backtest_service(registry)
    init_optimize_service(registry)
    scheduler = init_scheduler(registry)

    app.state.scheduler = scheduler
    app.state.settings = settings
    app.state.is_ready = True

    # If vault auto-unlocked (passwordless mode), bring up the active
    # broker so the Dashboard renders with balance/positions on first
    # load - mirrors what /api/auth/unlock does for password vaults.
    if vault.is_unlocked:
        try:
            from app.api.routes.auth import _autoconnect_active_broker
            from app.db.session import get_sessionmaker

            sm = get_sessionmaker()
            async with sm() as session:
                await _autoconnect_active_broker(vault, registry, session)
        except Exception:  # noqa: BLE001
            logger.exception("Auto-connect on lifespan failed (non-fatal)")

    try:
        yield
    finally:
        logger.info("Hermes backend shutting down")
        try:
            from app.services.trading_service import get_trading_service
            await get_trading_service().stop()
        except Exception:  # noqa: BLE001
            logger.exception("Error stopping trading service")
        try:
            await registry.disconnect_all()
        except Exception:  # noqa: BLE001
            logger.exception("Error disconnecting brokers")
        try:
            scheduler.shutdown()
        except Exception:  # noqa: BLE001
            logger.exception("Error shutting down scheduler")
        try:
            from app.services.tunnel_service import get_tunnel_service
            get_tunnel_service().stop()
        except Exception:  # noqa: BLE001
            pass
        vault.lock()
        app.state.is_ready = False
