"""High-level smoke walk through the REST API via httpx ASGI transport."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_health(http_client) -> None:
    r = await http_client.get("/api/system/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["product"] == "BAI Core Trader" or "Hermes" in body["product"]


@pytest.mark.asyncio
async def test_first_run_setup_unlock(http_client) -> None:
    state = (await http_client.get("/api/auth/state")).json()
    assert state["first_run"] is True
    assert state["locked"] is True

    r = await http_client.post(
        "/api/auth/setup-master-password", json={"master_password": "test-pwd-123"},
    )
    assert r.status_code == 200
    token = r.json()["token"]
    assert token

    state2 = (await http_client.get("/api/auth/state")).json()
    assert state2["first_run"] is False

    # Lock then unlock with the same password.
    await http_client.post("/api/auth/lock")
    r2 = await http_client.post(
        "/api/auth/unlock", json={"master_password": "test-pwd-123"},
    )
    assert r2.status_code == 200


@pytest.mark.asyncio
async def test_strategy_presets_listed(http_client) -> None:
    presets = (await http_client.get("/api/strategy/presets")).json()
    assert len(presets) >= 4
    ids = {p["id"] for p in presets}
    assert {"conservative", "balanced", "aggressive", "auto"} <= ids


@pytest.mark.asyncio
async def test_mt5_servers_returns_list(http_client) -> None:
    r = await http_client.get("/api/onboarding/mt5/servers")
    assert r.status_code == 200
    servers = r.json()
    assert isinstance(servers, list)
    assert len(servers) >= 1     # at least the bundled fallback


@pytest.mark.asyncio
async def test_validation_blocks_dangerous_params(http_client) -> None:
    # Set up master password so vault deps are happy where needed.
    await http_client.post(
        "/api/auth/setup-master-password", json={"master_password": "test-pwd-123"},
    )
    r = await http_client.post(
        "/api/strategy/validate",
        json={
            "base_lot_size": 5.0,
            "lot_multiplier": 2.0,
            "max_grid_levels": 8,
            "fix_take_profit_pct": 2.0,
            "stop_drawdown_pct": 10.0,
            "max_portfolio_drawdown_pct": 20.0,
            "trend_filter_enabled": True,
            "ema_fast": 50,
            "ema_slow": 200,
            "session_filter_enabled": True,
            "risk_per_trade_pct": 1.0,
            "max_simultaneous_pairs": 5,
            "symbols": ["EURUSD"],
            "timeframe": "1h",
            "base_time_delay_seconds": 1800,
            "time_delay_multiplier": 2.0,
            "atr_period": 14,
            "atr_multiplier": 1.0,
            "correlation_filter_enabled": True,
            "correlation_window": 100,
            "correlation_threshold": 0.85,
            "max_correlated_positions": 2,
            "session_start_utc": 7,
            "session_end_utc": 21,
            "dynamic_lot_enabled": True,
            "equity_base": 10000,
            "base_cooldown_hours": 2,
            "max_cooldown_hours": 24,
            "grid_distance_multiplier": 1.4,
            "base_grid_distance_pips": 30,
            "timezone_offset_utc": 3,
        },
    )
    assert r.status_code == 200
    payload = r.json()
    assert payload["has_errors"] is True
