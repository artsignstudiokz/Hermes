"""TunnelService — single ngrok tunnel + PIN-protected access for remote devices."""

from __future__ import annotations

import logging
import secrets
import time

from app.core.tunnel.ngrok import NgrokTunnel
from app.core.tunnel.qr import make_qr

logger = logging.getLogger(__name__)

LOCKOUT_AFTER = 5
LOCKOUT_SECONDS = 60 * 10
PIN_TTL_HOURS = 24


class TunnelService:
    def __init__(self) -> None:
        self._tunnel = NgrokTunnel()
        self._pin: str | None = None
        self._pin_issued_at: float = 0.0
        self._failures = 0
        self._lockout_until = 0.0

    @property
    def status(self) -> dict:
        url = self._tunnel.url
        return {
            "active": self._tunnel.is_active,
            "url": url,
            "qr": make_qr(url) if url else None,
            "pin": self._pin,
            "pin_age_hours": (time.time() - self._pin_issued_at) / 3600 if self._pin else 0,
        }

    def start(self, port: int) -> dict:
        self._tunnel.start(port)
        self._regenerate_pin()
        self._failures = 0
        self._lockout_until = 0.0
        return self.status

    def stop(self) -> None:
        self._tunnel.stop()
        self._pin = None

    def regenerate_pin(self) -> str:
        self._regenerate_pin()
        return self._pin or ""

    def _regenerate_pin(self) -> None:
        self._pin = f"{secrets.randbelow(10**6):06d}"
        self._pin_issued_at = time.time()
        logger.info("Tunnel PIN regenerated")

    def _maybe_rotate(self) -> None:
        if self._pin and (time.time() - self._pin_issued_at) > PIN_TTL_HOURS * 3600:
            self._regenerate_pin()

    def verify_pin(self, supplied: str | None) -> bool:
        self._maybe_rotate()
        if self._lockout_until > time.time():
            return False
        if supplied is None or self._pin is None:
            return False
        if not secrets.compare_digest(supplied, self._pin):
            self._failures += 1
            if self._failures >= LOCKOUT_AFTER:
                self._lockout_until = time.time() + LOCKOUT_SECONDS
                logger.warning("Tunnel locked out for %d minutes after %d failures",
                               LOCKOUT_SECONDS // 60, self._failures)
            return False
        self._failures = 0
        return True


_service: TunnelService | None = None


def get_tunnel_service() -> TunnelService:
    global _service
    if _service is None:
        _service = TunnelService()
    return _service
