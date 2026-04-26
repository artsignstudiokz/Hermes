"""Tiny JWT helper bound to the running process.

The signing secret is derived once per process from os.urandom — tokens
are invalidated on every restart, which is the right behaviour for a
locally-running desktop app: closing the window logs you out.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from functools import lru_cache

import jwt

ALGO = "HS256"


@lru_cache(maxsize=1)
def _secret() -> bytes:
    return os.urandom(32)


def issue_token(*, expires_at: datetime, subject: str = "user") -> str:
    payload = {
        "sub": subject,
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    return jwt.encode(payload, _secret(), algorithm=ALGO)


def decode_token(token: str) -> dict:
    return jwt.decode(token, _secret(), algorithms=[ALGO])
