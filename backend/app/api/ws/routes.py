"""WebSocket routes — clients connect to /ws/<topic> and receive JSON broadcasts."""

from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.ws.manager import get_ws_manager

router = APIRouter()
logger = logging.getLogger(__name__)

ALLOWED_TOPICS = {"positions", "equity", "signals", "logs", "prices", "system", "calibration"}


def _is_topic_allowed(topic: str) -> bool:
    return (
        topic in ALLOWED_TOPICS
        or topic.startswith("backtest_")
        or topic.startswith("optimize_")
    )


@router.websocket("/{topic}")
async def topic_socket(ws: WebSocket, topic: str) -> None:
    if not _is_topic_allowed(topic):
        await ws.close(code=4404)
        return

    manager = get_ws_manager()
    await ws.accept()
    await manager.join(topic, ws)
    try:
        # Idle: just keep the connection alive. We don't accept client messages
        # (server-push only).
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001
        logger.exception("WS error on topic=%s", topic)
    finally:
        await manager.leave(topic, ws)
