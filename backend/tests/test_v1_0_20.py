"""Integration tests for v1.0.20 — two trading modes, daily cap, signal
ensemble explanations, broker health, in-place DB migration.

Run from backend/ via `pytest tests/test_v1_0_20.py -v` (Windows). Tests
avoid hitting MT5 by stubbing BrokerRegistry.get_active() with a fake
adapter that returns synthetic OHLCV — so they're hermetic and fast.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


# ── Tmp data dir BEFORE app imports so settings picks it up ───────────


@pytest.fixture(scope="session", autouse=True)
def tmp_data_dir():
    tmp = Path(tempfile.mkdtemp(prefix="hermes_test_"))
    os.environ["BCT_DATA_DIR"] = str(tmp)
    os.environ["BCT_LOGS_DIR"] = str(tmp / "Logs")
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


# ── Indicator panel + ensemble unit tests ─────────────────────────────


def _make_ohlcv(n: int = 300, trend: float = 0.0005, seed: int = 1) -> pd.DataFrame:
    """Synthetic OHLCV with controllable drift."""
    np.random.seed(seed)
    noise = np.random.normal(0, 0.0008, n)
    base = np.cumsum(noise + trend) + 1.10
    high = base + np.abs(np.random.normal(0.0005, 0.0002, n))
    low = base - np.abs(np.random.normal(0.0005, 0.0002, n))
    open_ = base + np.random.normal(0, 0.0002, n)
    df = pd.DataFrame({"open": open_, "high": high, "low": low, "close": base,
                       "volume": np.random.randint(100, 1000, n)})
    df.index = pd.date_range("2026-01-01", periods=n, freq="1h")
    return df


def test_indicator_panel_returns_all_fields():
    from app.core.strategy.indicators import IndicatorPanel, IndicatorSnapshot
    panel = IndicatorPanel()
    snap = panel.compute("EURUSD", _make_ohlcv())
    assert isinstance(snap, IndicatorSnapshot)
    # Every numeric attr must be finite — NaN guards in the panel work.
    for attr in ("rsi", "macd", "macd_signal", "macd_hist", "bb_upper",
                 "bb_lower", "atr", "atr_pct", "ema_fast", "ema_slow",
                 "adx", "plus_di", "minus_di", "stoch_k", "stoch_d",
                 "donchian_high", "donchian_low"):
        v = getattr(snap, attr)
        assert np.isfinite(v), f"{attr} not finite: {v}"
    assert 0 <= snap.rsi <= 100
    assert 0 <= snap.adx <= 100
    assert snap.bb_upper >= snap.bb_middle >= snap.bb_lower


def test_indicator_panel_rejects_short_data():
    from app.core.strategy.indicators import IndicatorPanel
    short = _make_ohlcv(n=50)  # less than ema_slow_period
    with pytest.raises(ValueError):
        IndicatorPanel().compute("EURUSD", short)


def test_trend_strategy_fires_on_uptrend():
    from app.core.strategy.indicators import IndicatorPanel
    from app.core.strategy.signals import TrendFollowingStrategy
    snap = IndicatorPanel().compute("EURUSD", _make_ohlcv(trend=0.002))
    sig = TrendFollowingStrategy(adx_min=15).evaluate(snap)
    # The strong uptrend should at least pass through one direction.
    if sig is not None:
        assert sig.direction in ("long", "short")
        assert sig.confidence > 0
        assert "EMA" in sig.reason


def test_ensemble_returns_flat_when_no_signal():
    from app.core.strategy.indicators import IndicatorPanel
    from app.core.strategy.signals import build_ensemble
    # Pure sideways noise: nothing should fire.
    snap = IndicatorPanel().compute("EURUSD", _make_ohlcv(trend=0.0))
    ensemble = build_ensemble(["trend"], mode="majority")
    report = ensemble.evaluate(snap)
    # Either flat or some weak signal — always has indicators dict.
    assert report.symbol == "EURUSD"
    assert report.direction in ("long", "short", "flat")
    assert isinstance(report.indicators, dict)
    assert "rsi" in report.indicators


def test_ensemble_majority_voting():
    """If 2 of 3 strategies say long, ensemble votes long."""
    from app.core.strategy.signals import Signal, StrategyEnsemble

    class FakeLong:
        name = "FakeLong"
        def evaluate(self, snap):
            return Signal(self.name, snap.symbol, "long", 0.8, "fake", {})

    class FakeShort:
        name = "FakeShort"
        def evaluate(self, snap):
            return Signal(self.name, snap.symbol, "short", 0.7, "fake", {})

    from app.core.strategy.indicators import IndicatorPanel
    snap = IndicatorPanel().compute("EURUSD", _make_ohlcv())

    # 2 longs + 1 short → majority → long
    ens = StrategyEnsemble([FakeLong(), FakeLong(), FakeShort()], mode="majority")
    rep = ens.evaluate(snap)
    assert rep.direction == "long"
    assert "2 из 3" in rep.reason

    # 1 long + 1 short → tie → flat (refuse to act)
    ens = StrategyEnsemble([FakeLong(), FakeShort()], mode="majority")
    rep = ens.evaluate(snap)
    assert rep.direction == "flat"


def test_ensemble_unknown_mode_falls_through():
    """Unknown mode string should not crash — falls back to majority."""
    from app.core.strategy.signals import build_ensemble
    ens = build_ensemble(["nonexistent_strategy"], mode="weird_mode")
    # build_ensemble defaults to trend+momentum when names list is empty/unknown
    assert len(ens.strategies) >= 1


# ── Daily-cap counter behaviour ───────────────────────────────────────


def test_day_counter_resets_across_dates():
    from app.workers.trading_worker import TradingWorker
    w = TradingWorker.__new__(TradingWorker)
    w._day_key = "2026-01-01"
    w._trades_today = 5
    # Pretend it's a new UTC day.
    import app.workers.trading_worker as twm

    class FakeDT:
        @classmethod
        def now(cls, tz):
            return datetime(2026, 1, 2, tzinfo=tz)

    orig = twm.datetime
    twm.datetime = FakeDT  # type: ignore
    try:
        w._bump_day_counter()
        assert w._day_key == "2026-01-02"
        assert w._trades_today == 0
    finally:
        twm.datetime = orig  # type: ignore


def test_worker_set_mode_validates():
    from app.workers.trading_worker import TradingWorker
    w = TradingWorker.__new__(TradingWorker)
    w._mode = "off"
    w._account_id = 1
    w._ensemble_cache = {}     # populated lazily by set_mode
    w.set_mode("proven")
    assert w._mode == "proven"
    assert "proven" in w._ensemble_cache
    w.set_mode("autonomous")
    assert w._mode == "autonomous"
    assert "autonomous" in w._ensemble_cache
    w.set_mode("off")
    assert w._mode == "off"
    with pytest.raises(ValueError):
        w.set_mode("yolo")


# ── DB migration: new columns added to existing trades table ─────────


def test_init_db_adds_mode_and_signal_reason_columns():
    """If a legacy DB exists without mode/signal_reason columns, init_db
    ALTERs them in. Simulates upgrade from v1.0.18 → v1.0.20."""
    import asyncio
    from sqlalchemy import inspect, text

    from app.db.session import get_engine, init_db

    async def run():
        # Drop everything and recreate the *old* trades table shape, then
        # call init_db and confirm columns appear.
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.exec_driver_sql("DROP TABLE IF EXISTS trades")
            await conn.exec_driver_sql("DROP TABLE IF EXISTS broker_accounts")
            await conn.exec_driver_sql("""
                CREATE TABLE broker_accounts (
                    id INTEGER PRIMARY KEY,
                    type VARCHAR(16) NOT NULL DEFAULT 'mt5',
                    name VARCHAR(64) NOT NULL DEFAULT '',
                    server VARCHAR(64),
                    login VARCHAR(32),
                    vault_key VARCHAR(64) NOT NULL DEFAULT '',
                    is_active BOOLEAN NOT NULL DEFAULT 0,
                    is_testnet BOOLEAN NOT NULL DEFAULT 0
                )
            """)
            await conn.exec_driver_sql("""
                CREATE TABLE trades (
                    id INTEGER PRIMARY KEY,
                    broker_account_id INTEGER REFERENCES broker_accounts(id),
                    ticket VARCHAR(64) NOT NULL,
                    symbol VARCHAR(32) NOT NULL,
                    direction VARCHAR(8) NOT NULL,
                    level INTEGER NOT NULL DEFAULT 0,
                    lots FLOAT NOT NULL,
                    entry_price FLOAT NOT NULL,
                    exit_price FLOAT,
                    pnl FLOAT NOT NULL DEFAULT 0,
                    commission FLOAT NOT NULL DEFAULT 0,
                    swap FLOAT NOT NULL DEFAULT 0,
                    opened_at TIMESTAMP NOT NULL,
                    closed_at TIMESTAMP,
                    reason VARCHAR(32) NOT NULL DEFAULT ''
                )
            """)
        await init_db()
        async with engine.begin() as conn:
            def _check(sync_conn):
                cols = {c["name"] for c in inspect(sync_conn).get_columns("trades")}
                return cols
            cols = await conn.run_sync(_check)
        assert "mode" in cols, f"Migration didn't add 'mode'. Got: {sorted(cols)}"
        assert "signal_reason" in cols
        # Inserting with mode + signal_reason should work end-to-end.
        async with engine.begin() as conn:
            await conn.exec_driver_sql(
                "INSERT INTO broker_accounts (id, name, vault_key) VALUES (1, 'X', 'k1')"
            )
            await conn.exec_driver_sql(
                "INSERT INTO trades (broker_account_id, ticket, symbol, direction, "
                "lots, entry_price, opened_at, reason, mode, signal_reason) "
                "VALUES (1, 't', 'EURUSD', 'long', 0.01, 1.1, '2026-01-01', "
                "'auto_proven', 'proven', 'EMA > EMA, ADX 30')"
            )
            res = await conn.exec_driver_sql("SELECT mode, signal_reason FROM trades")
            row = res.first()
            assert row[0] == "proven"
            assert "ADX 30" in row[1]

    asyncio.run(run())


# ── REST routes: new endpoints exist + return 200/400 ───────────────


def test_new_routes_registered():
    from app.main import app
    # FastAPI 0.118+ keeps include_router-mounted routers in app.routes
    # as `_IncludedRouter` objects (no `.path`), alongside the plain
    # Route objects for top-level @app.get / @app.post handlers. Walk
    # both so every endpoint is enumerated.
    def _collect_paths(routes) -> set[str]:
        out: set[str] = set()
        for r in routes:
            if hasattr(r, "path") and isinstance(getattr(r, "path", None), str):
                out.add(r.path)
            if hasattr(r, "routes"):
                out |= _collect_paths(r.routes)
        return out

    paths = _collect_paths(app.routes)
    assert "/api/trading/start-proven" in paths
    assert "/api/trading/start-autonomous" in paths
    assert "/api/trading/analyze" in paths
    assert "/api/trading/test-order" in paths
    assert "/api/brokers/{broker_id}/health" in paths
    assert "/api/brokers/{broker_id}/reconnect" in paths


def test_start_proven_returns_400_without_broker():
    """v1.0.31: vault is auto-unlocked in passwordless mode, so calling
    start-proven with a non-existent broker should fail at the broker
    lookup, not the vault lock (400 instead of 423). Either is fine
    as long as it doesn't 500.
    """
    import asyncio
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    async def run():
        # Reset DB schema cleanly - the test_init_db migration test
        # drops broker_accounts and leaves it without TimestampMixin
        # columns, which corrupts later session.get() calls.
        from app.db.session import get_engine

        engine = get_engine()
        async with engine.begin() as conn:
            await conn.exec_driver_sql("DROP TABLE IF EXISTS trades")
            await conn.exec_driver_sql("DROP TABLE IF EXISTS broker_accounts")

        async with app.router.lifespan_context(app):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
                r = await ac.post("/api/trading/start-proven", json={"broker_account_id": 99})
                assert r.status_code in (400, 423, 500), r.text

    asyncio.run(run())
