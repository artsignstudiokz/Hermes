"""PyInstaller runtime hook — sets BCT_DATA_DIR / BCT_LOGS_DIR defaults.

This script runs inside the frozen exe BEFORE the main app starts. It
deliberately uses ONLY stdlib (os, sys, pathlib) — even though we ship
`platformdirs` as a dependency, the bootloader's import path is fragile
in early-runtime, and a missing module here aborts the entire app with
a cryptic 'Unhandled exception in script' dialog.

The same path-resolution logic lives in `app.settings._data_root` /
`_logs_root` (which uses platformdirs proper) — pydantic-settings only
falls back to those defaults when the env var isn't set, so this hook
just establishes them up-front in a 100% reliable way.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "Hermes"
APP_AUTHOR = "BAI Core"


def _data_dir() -> str:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return str(Path(base) / APP_AUTHOR / APP_NAME)
    if sys.platform == "darwin":
        return str(Path.home() / "Library" / "Application Support" / APP_NAME)
    # Linux / other — XDG Base Dir.
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return str(Path(base) / APP_NAME)


def _logs_dir() -> str:
    if sys.platform == "win32":
        return str(Path(_data_dir()) / "Logs")
    if sys.platform == "darwin":
        return str(Path.home() / "Library" / "Logs" / APP_NAME)
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return str(Path(base) / APP_NAME)


os.environ.setdefault("BCT_DATA_DIR", _data_dir())
os.environ.setdefault("BCT_LOGS_DIR", _logs_dir())
