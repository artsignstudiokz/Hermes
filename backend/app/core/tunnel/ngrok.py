"""ngrok tunnel — opens a public URL pointing at our local FastAPI port.

Auth-tokened by default (env BCT_NGROK_AUTHTOKEN); we degrade gracefully
to anonymous tunnels when no token is provided (lower bandwidth, ngrok
brand splash on first visit).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TunnelHandle:
    url: str
    public_url: str


class NgrokTunnel:
    def __init__(self) -> None:
        self._tunnel = None

    @property
    def is_active(self) -> bool:
        return self._tunnel is not None

    @property
    def url(self) -> str | None:
        return getattr(self._tunnel, "public_url", None) if self._tunnel else None

    def start(self, port: int) -> str:
        from pyngrok import conf, ngrok

        token = os.environ.get("BCT_NGROK_AUTHTOKEN")
        if token:
            conf.get_default().auth_token = token

        if self._tunnel is not None:
            return self._tunnel.public_url

        self._tunnel = ngrok.connect(port, "http")
        logger.info("ngrok tunnel opened → %s (port %d)", self._tunnel.public_url, port)
        return self._tunnel.public_url

    def stop(self) -> None:
        if self._tunnel is None:
            return
        try:
            from pyngrok import ngrok

            ngrok.disconnect(self._tunnel.public_url)
            ngrok.kill()
        except Exception:  # noqa: BLE001
            logger.exception("Error closing ngrok tunnel")
        finally:
            self._tunnel = None
