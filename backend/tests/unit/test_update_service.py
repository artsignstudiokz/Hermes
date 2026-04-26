"""Auto-update — semver compare + transport mock."""

from __future__ import annotations

import json

import httpx
import pytest

from app.services import update_service
from app.services.update_service import _semver_tuple, check_for_update


def test_semver_tuple() -> None:
    assert _semver_tuple("1.0.0") == (1, 0, 0)
    assert _semver_tuple("2.10.5") == (2, 10, 5)
    assert _semver_tuple("1.0.1-rc.2") == (1, 0, 1)


def test_semver_compare() -> None:
    assert _semver_tuple("1.0.1") > _semver_tuple("1.0.0")
    assert _semver_tuple("1.10.0") > _semver_tuple("1.9.9")


@pytest.mark.asyncio
async def test_check_for_update_handles_unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    class _BoomTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("offline", request=request)

    def _client_factory(*args, **kwargs):
        return httpx.AsyncClient(transport=_BoomTransport(), **kwargs)

    monkeypatch.setattr(update_service.httpx, "AsyncClient", _client_factory)
    info = await check_for_update()
    assert info.has_update is False
    assert info.asset is None


@pytest.mark.asyncio
async def test_check_for_update_finds_newer(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "version": "9.9.9",
        "released_at": "2026-12-31T00:00:00Z",
        "windows": {
            "url": "https://baicore.kz/releases/Hermes-Setup-9.9.9.exe",
            "sha256": "abc",
            "size": 80_000_000,
        },
        "macos": {"url": "https://baicore.kz/releases/Hermes-9.9.9.pkg", "sha256": "def", "size": 85_000_000},
        "notes": "* Test\n* Note",
    }

    class _OkTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=json.dumps(payload).encode())

    monkeypatch.setattr(
        update_service.httpx, "AsyncClient",
        lambda *a, **kw: httpx.AsyncClient(transport=_OkTransport(), **kw),
    )
    info = await check_for_update()
    assert info.has_update is True
    assert info.latest_version == "9.9.9"
    assert info.asset is not None
    assert info.asset.url.endswith(".exe") or info.asset.url.endswith(".pkg")
