"""Web Push (VAPID) — generate keypair on first use, dispatch payloads."""

from __future__ import annotations

import base64
import json
import logging
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

logger = logging.getLogger(__name__)


def _b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")


def ensure_vapid_keys(path: Path) -> dict[str, str]:
    """Return {private_pem, public_b64url}. Generates the keypair on first call."""
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        return data

    private_key = ec.generate_private_key(ec.SECP256R1())
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("ascii")

    public_numbers = private_key.public_key().public_numbers()
    public_bytes = b"\x04" + public_numbers.x.to_bytes(32, "big") + public_numbers.y.to_bytes(32, "big")
    public_b64url = _b64url(public_bytes)

    data = {"private_pem": private_pem, "public_b64url": public_b64url}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    return data


def send_webpush(
    *,
    endpoint: str,
    p256dh: str,
    auth: str,
    payload: dict,
    vapid_private_pem: str,
    vapid_subject: str = "mailto:info@baicore.kz",
) -> bool:
    try:
        from pywebpush import WebPushException, webpush
    except ImportError:
        logger.warning("pywebpush not installed; skipping web push")
        return False
    try:
        webpush(
            subscription_info={
                "endpoint": endpoint,
                "keys": {"p256dh": p256dh, "auth": auth},
            },
            data=json.dumps(payload),
            vapid_private_key=vapid_private_pem,
            vapid_claims={"sub": vapid_subject},
        )
        return True
    except WebPushException as e:
        logger.warning("web push failed: %s", e)
        return False
