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
    """Create tables on first run + apply lightweight in-place migrations.

    We don't run Alembic on startup because end-users have an opaque
    `data/app.db` from older releases and shipping the alembic CLI in
    a frozen build is fragile. Instead this function:

      1. Creates any missing tables (no-op for existing installs).
      2. Inspects critical tables and ALTERs in new columns that the
         current code expects but older DBs lack. SQLite supports
         `ALTER TABLE ADD COLUMN` for nullable / defaulted columns,
         which covers the additive evolutions we ship.

    Order matters: create_all first (so brand-new installs get the
    full schema), then patch existing tables.
    """
    from sqlalchemy import inspect

    from app.db.base import Base
    # Import all model modules so they register with Base.metadata.
    from app.db import models  # noqa: F401

    async with get_engine().begin() as conn:
        # Enable WAL mode for concurrent readers (UI vs trading worker).
        await conn.exec_driver_sql("PRAGMA journal_mode=WAL")
        await conn.exec_driver_sql("PRAGMA foreign_keys=ON")
        await conn.run_sync(Base.metadata.create_all)

        def _patch(sync_conn):
            insp = inspect(sync_conn)
            if "trades" not in insp.get_table_names():
                return
            cols = {c["name"] for c in insp.get_columns("trades")}
            if "mode" not in cols:
                sync_conn.exec_driver_sql(
                    "ALTER TABLE trades ADD COLUMN mode VARCHAR(16) NOT NULL DEFAULT 'manual'"
                )
                sync_conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_trades_mode ON trades(mode)")
            if "signal_reason" not in cols:
                sync_conn.exec_driver_sql("ALTER TABLE trades ADD COLUMN signal_reason TEXT")

        await conn.run_sync(_patch)
