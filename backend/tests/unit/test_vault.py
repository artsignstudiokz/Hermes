"""Vault encryption + lockout behaviour."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.core.security.vault import (
    LOCKOUT_FAILURES,
    CredentialVault,
    VaultError,
    VaultLocked,
)


def test_create_and_unlock(vault: CredentialVault) -> None:
    assert not vault.exists()
    vault.create("hunter2-secure")
    assert vault.exists()
    assert vault.is_unlocked

    # Round-trip a value.
    vault.set("mt5:42", {"password": "secret", "server": "Demo"})
    vault.lock()
    assert not vault.is_unlocked

    vault.unlock("hunter2-secure")
    assert vault.get("mt5:42") == {"password": "secret", "server": "Demo"}


def test_wrong_password_then_lockout(vault: CredentialVault) -> None:
    vault.create("correct-horse")
    vault.lock()

    # Three wrong attempts — the third triggers VaultLocked.
    for i in range(LOCKOUT_FAILURES - 1):
        with pytest.raises(VaultError):
            vault.unlock("wrong")
    with pytest.raises(VaultLocked):
        vault.unlock("wrong-yet-again")
    assert vault.lockout_until is not None
    assert vault.lockout_until > datetime.now(timezone.utc)


def test_change_password(vault: CredentialVault) -> None:
    vault.create("old-pwd")
    vault.set("k", "v")
    vault.change_password("old-pwd", "new-pwd")

    vault.lock()
    with pytest.raises(VaultError):
        vault.unlock("old-pwd")
    vault.unlock("new-pwd")
    assert vault.get("k") == "v"


def test_keys_delete(vault: CredentialVault) -> None:
    vault.create("pwd")
    vault.set("a", 1)
    vault.set("b", 2)
    assert sorted(vault.keys()) == ["a", "b"]
    vault.delete("a")
    assert vault.keys() == ["b"]
    vault.delete("missing")  # silent
    assert vault.keys() == ["b"]


def test_locked_access_raises(vault: CredentialVault) -> None:
    vault.create("pwd")
    vault.lock()
    with pytest.raises(VaultError):
        vault.get("anything")
    with pytest.raises(VaultError):
        vault.set("k", "v")
