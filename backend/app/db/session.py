"""Async SQLAlchemy engine + session factory bound to data/app.db (SQLite WAL)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.settings import get_settings


def _db_url() -> str:
    return f"sqlite+aiosqlite:///{get_settings().db_path}"


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    engine = create_async_engine(
        _db_url(),
        echo=False,
        future=True,
        pool_pre_ping=True,
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    return engine


@lru_cache(maxsize=1)
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency."""
    async with get_sessionmaker()() as session:
        yield session


async def init_db() -> None:
    """Create tables on first run. For schema migrations use Alembic."""
    from app.db.base import Base
    # Import all model modules so they register with Base.metadata.
    from app.db import models  # noqa: F401

    async with get_engine().begin() as conn:
        # Enable WAL mode for concurrent readers (UI vs trading worker).
        await conn.exec_driver_sql("PRAGMA journal_mode=WAL")
        await conn.exec_driver_sql("PRAGMA foreign_keys=ON")
        await conn.run_sync(Base.metadata.create_all)
