"""Shared pytest fixtures.

Each test gets:
  * an isolated temp data dir (so credentials.enc / app.db don't collide),
  * an in-memory SQLite engine bound to the same metadata,
  * an HTTPX AsyncClient pointing at a freshly-built FastAPI app.
"""

from __future__ import annotations

import asyncio
import os
import sys
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio

# Make the legacy package importable so StrategyRunner can lazy-import it.
_BACKEND = Path(__file__).resolve().parents[1]
_REPO = _BACKEND.parent
for p in (_REPO, _BACKEND, _REPO / "legacy"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


@pytest.fixture(scope="session")
def event_loop():
    """Session-scoped loop for async fixtures."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def tmp_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Override BCT_DATA_DIR / BCT_LOGS_DIR for the duration of the test."""
    data = tmp_path / "data"
    logs = tmp_path / "logs"
    data.mkdir()
    logs.mkdir()
    monkeypatch.setenv("BCT_DATA_DIR", str(data))
    monkeypatch.setenv("BCT_LOGS_DIR", str(logs))

    # Reset cached singletons so settings re-read env vars.
    from app import deps, settings as settings_mod
    settings_mod.get_settings.cache_clear()
    deps.get_vault.cache_clear()
    deps.get_broker_registry.cache_clear()
    return data


@pytest.fixture
def settings(tmp_data_dir: Path):
    from app.settings import get_settings
    return get_settings()


@pytest.fixture
def vault(tmp_data_dir: Path):
    from app.core.security.vault import CredentialVault
    return CredentialVault(tmp_data_dir / "credentials.enc")


@pytest_asyncio.fixture
async def db_engine(tmp_data_dir: Path):
    """Per-test in-memory SQLite. Recreates schema on each test."""
    from app.db.base import Base
    from app.db.session import get_engine, get_sessionmaker

    # Reset cached engine for new data dir.
    get_engine.cache_clear()
    get_sessionmaker.cache_clear()

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()


@pytest_asyncio.fixture
async def http_client(tmp_data_dir: Path) -> AsyncIterator:
    """Live FastAPI app with an HTTPX AsyncClient connected via ASGI transport."""
    from httpx import ASGITransport, AsyncClient

    from app.main import create_app
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Trigger startup once so the lifespan finishes; lifespan is opt-in via
        # the manager-style hook that ASGITransport calls.
        async with app.router.lifespan_context(app):
            yield client


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip stray BCT_* envs that leaked from previous tests."""
    for k in list(os.environ):
        if k.startswith("BCT_") and k not in ("BCT_DATA_DIR", "BCT_LOGS_DIR"):
            monkeypatch.delenv(k, raising=False)
