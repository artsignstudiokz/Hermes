"""Argon2id key derivation."""

from __future__ import annotations

import pytest

from app.core.security.kdf import KEY_LEN, SALT_LEN, derive_key, new_salt


def test_salt_size() -> None:
    salt = new_salt()
    assert len(salt) == SALT_LEN
    assert salt != new_salt()        # randomness


def test_derive_key_deterministic_per_salt() -> None:
    salt = new_salt()
    k1 = derive_key("password", salt)
    k2 = derive_key("password", salt)
    assert k1 == k2
    assert len(k1) == KEY_LEN


def test_derive_key_diverges_on_password() -> None:
    salt = new_salt()
    assert derive_key("pwd-A", salt) != derive_key("pwd-B", salt)


def test_derive_key_diverges_on_salt() -> None:
    s1, s2 = new_salt(), new_salt()
    assert derive_key("pwd", s1) != derive_key("pwd", s2)


def test_empty_password_rejected() -> None:
    with pytest.raises(ValueError):
        derive_key("", new_salt())


def test_wrong_salt_size_rejected() -> None:
    with pytest.raises(ValueError):
        derive_key("pwd", b"too-short")
