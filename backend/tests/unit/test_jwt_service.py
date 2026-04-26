"""JWT issuance + decode."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.core.security.jwt_service import decode_token, issue_token


def test_round_trip() -> None:
    expires = datetime.now(timezone.utc) + timedelta(hours=1)
    token = issue_token(expires_at=expires, subject="alice")
    payload = decode_token(token)
    assert payload["sub"] == "alice"
    assert "exp" in payload


def test_expired_token_rejected() -> None:
    expires = datetime.now(timezone.utc) - timedelta(seconds=1)
    token = issue_token(expires_at=expires)
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(token)


def test_tampered_token_rejected() -> None:
    expires = datetime.now(timezone.utc) + timedelta(hours=1)
    token = issue_token(expires_at=expires)
    bad = token[:-2] + ("AA" if not token.endswith("AA") else "BB")
    with pytest.raises(jwt.InvalidSignatureError):
        decode_token(bad)
