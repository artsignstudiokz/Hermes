"""Cross-platform single-instance guard.

Windows: named mutex via ctypes (no extra deps).
macOS / Linux: lock-file with fcntl.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

LOCK_NAME = "BaiCoreTrader.lock"


class SingleInstance:
    """Acquire on construction; release on close()."""

    def __init__(self, lock_dir: Path) -> None:
        self._lock_dir = lock_dir
        self._handle = None
        self._acquired = False
        self._lock_path: Path | None = None

    def acquire(self) -> bool:
        if sys.platform == "win32":
            return self._acquire_windows()
        return self._acquire_posix()

    def _acquire_windows(self) -> bool:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]

        ERROR_ALREADY_EXISTS = 183
        self._handle = kernel32.CreateMutexW(None, False, "Global\\BaiCoreTraderMutex")
        last_err = ctypes.get_last_error()
        if last_err == ERROR_ALREADY_EXISTS:
            return False
        self._acquired = True
        return True

    def _acquire_posix(self) -> bool:
        import fcntl

        self._lock_dir.mkdir(parents=True, exist_ok=True)
        self._lock_path = self._lock_dir / LOCK_NAME
        # Open in append-create mode and try to grab an exclusive non-blocking lock.
        fd = os.open(self._lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            os.close(fd)
            return False
        self._handle = fd
        self._acquired = True
        return True

    def release(self) -> None:
        if not self._acquired:
            return
        if sys.platform == "win32":
            import ctypes

            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            if self._handle:
                kernel32.ReleaseMutex(self._handle)
                kernel32.CloseHandle(self._handle)
        else:
            import fcntl

            if self._handle is not None:
                try:
                    fcntl.flock(self._handle, fcntl.LOCK_UN)
                finally:
                    os.close(self._handle)
        self._acquired = False
        self._handle = None
