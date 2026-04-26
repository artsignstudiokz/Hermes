"""FastAPI application factory for Hermes (BAI Core)."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api.routes import (
    account, adaptive, auth, backtest, brokers, notifications, onboarding,
    optimize, positions, strategy, system, trades, trading, tunnel,
)
from app.api.ws.routes import router as ws_router
from app.lifecycle import lifespan
from app.settings import get_settings

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    app = FastAPI(
        title="Hermes (BAI Core)",
        version=__version__,
        docs_url="/api/docs" if settings.dev_mode else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if settings.dev_mode else None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_origin_regex=r"https?://(127\.0\.0\.1|localhost)(:\d+)?",
    )

    # REST routers
    app.include_router(system.router, prefix="/api/system", tags=["system"])
    app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
    app.include_router(brokers.router, prefix="/api/brokers", tags=["brokers"])
    app.include_router(account.router, prefix="/api/account", tags=["account"])
    app.include_router(positions.router, prefix="/api/positions", tags=["positions"])
    app.include_router(trades.router, prefix="/api/trades", tags=["trades"])
    app.include_router(strategy.router, prefix="/api/strategy", tags=["strategy"])
    app.include_router(trading.router, prefix="/api/trading", tags=["trading"])
    app.include_router(onboarding.router, prefix="/api/onboarding", tags=["onboarding"])
    app.include_router(notifications.router, prefix="/api/notifications", tags=["notifications"])
    app.include_router(tunnel.router, prefix="/api/tunnel", tags=["tunnel"])
    app.include_router(adaptive.router, prefix="/api/adaptive", tags=["adaptive"])
    app.include_router(backtest.router, prefix="/api/backtest", tags=["backtest"])
    app.include_router(optimize.router, prefix="/api/optimize", tags=["optimize"])

    # WebSocket
    app.include_router(ws_router, prefix="/ws")

    # Static SPA fallback (built React).
    static_dir = settings.static_dir or _default_static_dir()
    if static_dir and static_dir.exists():
        index_html = static_dir / "index.html"
        assets_dir = static_dir / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def spa_fallback(full_path: str):
            target = static_dir / full_path
            if full_path and target.is_file():
                return FileResponse(target)
            return FileResponse(index_html)
    else:
        logger.warning("Frontend static dir not found at %s — running API-only", static_dir)

    return app


def _default_static_dir() -> Path:
    return Path(__file__).resolve().parent / "static"


app = create_app()
