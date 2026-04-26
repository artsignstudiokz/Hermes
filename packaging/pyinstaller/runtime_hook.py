"""PyInstaller runtime hook — sets BCT_DATA_DIR before the app loads settings."""

from __future__ import annotations

import os

from platformdirs import user_data_dir, user_log_dir

APP_NAME = "Hermes"
APP_AUTHOR = "BAI Core"

os.environ.setdefault("BCT_DATA_DIR", user_data_dir(APP_NAME, APP_AUTHOR, roaming=True))
os.environ.setdefault("BCT_LOGS_DIR", user_log_dir(APP_NAME, APP_AUTHOR))
