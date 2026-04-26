"""Argon2id key derivation for the master password.

We derive a 32-byte key from (password, salt) and feed it into Fernet for
symmetric encryption. The salt is stored alongside the ciphertext; the
derived key is held in memory only while the vault is unlocked.
"""

from __future__ import annotations

import os

from argon2.low_level import Type, hash_secret_raw

KEY_LEN = 32  # Fernet expects 32 bytes after base64 encoding
SALT_LEN = 16

# Conservative defaults for an interactive desktop app on a laptop:
#   memory ~= 64 MB, 3 passes, 4 lanes — ~250 ms on a recent CPU.
TIME_COST = 3
MEMORY_COST = 65_536  # KiB
PARALLELISM = 4


def new_salt() -> bytes:
    return os.urandom(SALT_LEN)


def derive_key(password: str, salt: bytes) -> bytes:
    """Return a raw 32-byte key suitable for Fernet (after base64 wrapping)."""
    if not password:
        raise ValueError("password must not be empty")
    if len(salt) != SALT_LEN:
        raise ValueError(f"salt must be {SALT_LEN} bytes, got {len(salt)}")
    return hash_secret_raw(
        secret=password.encode("utf-8"),
        salt=salt,
        time_cost=TIME_COST,
        memory_cost=MEMORY_COST,
        parallelism=PARALLELISM,
        hash_len=KEY_LEN,
        type=Type.ID,
    )
