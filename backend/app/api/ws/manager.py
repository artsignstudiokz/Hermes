"""WebSocketManager — pub/sub broadcast across topic rooms.

Topics map 1:1 to URLs (positions, equity, signals, logs). Services call
`broadcast(topic, payload)`; clients subscribe via WS and receive JSON.
Disconnects are tolerated — broken sockets are skipped, not raised.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self) -> None:
        self._rooms: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def join(self, topic: str, ws: WebSocket) -> None:
        async with self._lock:
            self._rooms[topic].add(ws)
        logger.debug("WS join %s (%d total)", topic, len(self._rooms[topic]))

    async def leave(self, topic: str, ws: WebSocket) -> None:
        async with self._lock:
            self._rooms[topic].discard(ws)

    async def broadcast(self, topic: str, payload: Any) -> None:
        msg = json.dumps(payload, default=str)
        # Snapshot subscribers under the lock, then send without holding it.
        async with self._lock:
            subscribers = list(self._rooms.get(topic, ()))
        if not subscribers:
            return
        dead: list[WebSocket] = []
        for ws in subscribers:
            try:
                await ws.send_text(msg)
            except Exception:  # noqa: BLE001
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    self._rooms[topic].discard(ws)

    def stats(self) -> dict[str, int]:
        return {topic: len(subs) for topic, subs in self._rooms.items()}


# Process-wide singleton.
_manager: WebSocketManager | None = None


def get_ws_manager() -> WebSocketManager:
    global _manager
    if _manager is None:
        _manager = WebSocketManager()
    return _manager
