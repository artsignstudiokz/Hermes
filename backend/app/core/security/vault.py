"""CredentialVault - encrypted storage for broker creds and API keys.

File layout (`credentials.enc`):
    {
      "v": 1,
      "salt": "<base64>",
      "ciphertext": "<base64 Fernet token wrapping JSON {key: value}>"
    }

The plaintext payload is `dict[str, Any]`. Typical keys:
    "mt5:account_42": {"server": "...", "login": 42, "password": "..."}
    "ccxt:binance:default": {"api_key": "...", "secret": "...", "testnet": false}
"""

from __future__ import annotations

import base64
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.core.security.kdf import derive_key, new_salt

logger = logging.getLogger(__name__)

VAULT_VERSION = 1
LOCKOUT_FAILURES = 3
LOCKOUT_MINUTES = 10


class VaultError(Exception):
    """Generic vault failure (wrong password, corrupted file, etc.)."""


class VaultLocked(VaultError):
    """Vault is currently locked out due to repeated failed unlock attempts."""


class CredentialVault:
    """Stateful vault: locked at construction, unlocked via master password.

    NOT thread-safe - guard with a lock if accessed from multiple threads.
    The decrypted payload lives in memory between unlock() and lock().
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._key: bytes | None = None
        self._payload: dict[str, Any] = {}
        self._fail_count = 0
        self._lockout_until: datetime | None = None

    # ── State ────────────────────────────────────────────────────────────────
    def exists(self) -> bool:
        return self._path.exists()

    @property
    def is_unlocked(self) -> bool:
        return self._key is not None

    @property
    def lockout_until(self) -> datetime | None:
        if self._lockout_until and self._lockout_until <= datetime.now(timezone.utc):
            self._lockout_until = None
            self._fail_count = 0
        return self._lockout_until

    # ── Lifecycle ────────────────────────────────────────────────────────────
    def create(self, master_password: str) -> None:
        if self.exists():
            raise VaultError("Vault already exists")
        salt = new_salt()
        key = derive_key(master_password, salt)
        self._key = key
        self._payload = {}
        self._write(salt)
        logger.info("Vault created at %s", self._path)

    # ── Passwordless mode (v1.0.31+) ────────────────────────────────────────
    # The operator complained the master-password step was friction with no
    # real value on a single-user desktop app: the file already lives in
    # user-only ACL'd %APPDATA%, and the OS protects it. Passwordless mode
    # creates a vault encrypted with a fixed app-derived key (still safer
    # than plaintext, but no human password to remember). Existing
    # password-protected vaults keep working through the original
    # create/unlock path - no forced migration.

    # Stable per-install key - mixes the absolute vault path so two
    # different Hermes installs on the same machine don't share the key.
    _APP_PASSPHRASE_BASE = "hermes-bai-core-passwordless-v1"

    def _app_passphrase(self) -> str:
        return f"{self._APP_PASSPHRASE_BASE}:{self._path.resolve()}"

    def create_passwordless(self) -> None:
        """Create a vault encrypted with the fixed app-derived key.

        Idempotent on already-passwordless vaults: if the vault opens
        with the fixed key, we just unlock without rewriting. On a
        truly-fresh install we generate a new salt and write.
        """
        if self.exists():
            # Try to unlock with the fixed key. If it works, we're done.
            try:
                self._unlock_with_passphrase(self._app_passphrase())
                return
            except (VaultError, InvalidToken):
                raise VaultError(
                    "Vault exists but is password-protected. Unlock with the "
                    "master password instead of switching to passwordless.",
                )
        salt = new_salt()
        key = derive_key(self._app_passphrase(), salt)
        self._key = key
        self._payload = {}
        self._write(salt)
        logger.info("Passwordless vault created at %s", self._path)

    def try_auto_unlock(self) -> bool:
        """Attempt to unlock with the fixed app key. Returns True on
        success, False if the vault was created with a user password.
        """
        if not self.exists():
            return False
        try:
            self._unlock_with_passphrase(self._app_passphrase())
            return True
        except Exception:
            return False

    def _unlock_with_passphrase(self, passphrase: str) -> None:
        """Lower-level unlock used by both the public unlock() path and
        the auto-unlock flow. Does NOT bump the lockout counter - we
        only count human-entered passwords.
        """
        if not self.exists():
            raise VaultError("Vault does not exist")
        raw = json.loads(self._path.read_text(encoding="utf-8"))
        salt = base64.b64decode(raw["salt"])
        token = raw["ciphertext"].encode("ascii")
        key = derive_key(passphrase, salt)
        plaintext = Fernet(_b64key(key)).decrypt(token)
        self._key = key
        self._payload = json.loads(plaintext.decode("utf-8"))

    def unlock(self, master_password: str) -> None:
        if self.lockout_until is not None:
            raise VaultLocked(f"Locked until {self._lockout_until.isoformat()}")
        if not self.exists():
            raise VaultError("Vault does not exist - call create() first")

        raw = json.loads(self._path.read_text(encoding="utf-8"))
        salt = base64.b64decode(raw["salt"])
        token = raw["ciphertext"].encode("ascii")

        key = derive_key(master_password, salt)
        try:
            plaintext = Fernet(_b64key(key)).decrypt(token)
        except InvalidToken as exc:
            self._fail_count += 1
            if self._fail_count >= LOCKOUT_FAILURES:
                self._lockout_until = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES)
                self._fail_count = 0
                raise VaultLocked(
                    f"Too many failed attempts; locked for {LOCKOUT_MINUTES} minutes",
                ) from exc
            raise VaultError("Wrong master password") from exc

        self._key = key
        self._payload = json.loads(plaintext.decode("utf-8"))
        self._fail_count = 0
        logger.info("Vault unlocked (%d secrets loaded)", len(self._payload))

    def lock(self) -> None:
        # Best-effort key zeroing - Python doesn't guarantee, but we drop the ref.
        self._key = None
        self._payload = {}
        logger.info("Vault locked")

    def change_password(self, old_password: str, new_password: str) -> None:
        if not self.exists():
            raise VaultError("Vault does not exist")
        # Verify old password by attempting unlock against current ciphertext.
        was_unlocked = self.is_unlocked
        if not was_unlocked:
            self.unlock(old_password)
        salt = new_salt()
        new_key = derive_key(new_password, salt)
        self._key = new_key
        self._write(salt)
        logger.info("Master password changed")

    # ── CRUD ─────────────────────────────────────────────────────────────────
    def get(self, key: str, default: Any | None = None) -> Any:
        self._require_unlocked()
        return self._payload.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._require_unlocked()
        self._payload[key] = value
        # Re-encrypt with the existing salt - read salt from file.
        raw = json.loads(self._path.read_text(encoding="utf-8"))
        salt = base64.b64decode(raw["salt"])
        self._write(salt)

    def delete(self, key: str) -> None:
        self._require_unlocked()
        if key in self._payload:
            del self._payload[key]
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            salt = base64.b64decode(raw["salt"])
            self._write(salt)

    def keys(self) -> list[str]:
        self._require_unlocked()
        return list(self._payload.keys())

    # ── Internals ────────────────────────────────────────────────────────────
    def _require_unlocked(self) -> None:
        if self._key is None:
            raise VaultError("Vault is locked")

    def _write(self, salt: bytes) -> None:
        assert self._key is not None
        ciphertext = Fernet(_b64key(self._key)).encrypt(json.dumps(self._payload).encode("utf-8"))
        body = {
            "v": VAULT_VERSION,
            "salt": base64.b64encode(salt).decode("ascii"),
            "ciphertext": ciphertext.decode("ascii"),
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp.write_text(json.dumps(body), encoding="utf-8")
        tmp.replace(self._path)


def _b64key(raw_key: bytes) -> bytes:
    """Wrap a raw 32-byte key into Fernet's expected url-safe base64 form."""
    return base64.urlsafe_b64encode(raw_key)
