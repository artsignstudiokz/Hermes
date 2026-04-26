"""WebSocket pub/sub manager — pure logic, no actual sockets."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest

from app.api.ws.manager import WebSocketManager


class FakeSocket:
    def __init__(self) -> None:
        self.received: list[str] = []
        self.alive = True

    async def send_text(self, msg: str) -> None:
        if not self.alive:
            raise RuntimeError("disconnected")
        self.received.append(msg)


@pytest.mark.asyncio
async def test_join_and_broadcast() -> None:
    mgr = WebSocketManager()
    a, b = FakeSocket(), FakeSocket()
    await mgr.join("equity", a)         # type: ignore[arg-type]
    await mgr.join("equity", b)         # type: ignore[arg-type]
    await mgr.broadcast("equity", {"ts": "2026-04-27", "equity": 10_000})
    assert len(a.received) == 1
    assert len(b.received) == 1
    payload: dict[str, Any] = json.loads(a.received[0])
    assert payload["equity"] == 10_000


@pytest.mark.asyncio
async def test_broken_socket_pruned() -> None:
    mgr = WebSocketManager()
    healthy, dead = FakeSocket(), FakeSocket()
    dead.alive = False
    await mgr.join("logs", healthy)     # type: ignore[arg-type]
    await mgr.join("logs", dead)        # type: ignore[arg-type]
    await mgr.broadcast("logs", "hello")
    assert healthy.received == ['"hello"']
    # Dead socket should have been removed from the room.
    await asyncio.sleep(0)              # let the prune-task finish
    assert mgr.stats().get("logs", 0) == 1


@pytest.mark.asyncio
async def test_leave_unsubscribes() -> None:
    mgr = WebSocketManager()
    s = FakeSocket()
    await mgr.join("signals", s)        # type: ignore[arg-type]
    await mgr.leave("signals", s)       # type: ignore[arg-type]
    await mgr.broadcast("signals", {"x": 1})
    assert s.received == []
