"""Dev runner — opens the PyWebView window pointing at the Vite dev server.

Skips the bundled-backend startup path because in dev backend runs separately
on :8765 and Vite proxies /api → :8765.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Make sure the repo root is importable.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

import webview  # noqa: E402

from desktop.ipc_bridge import DesktopBridge  # noqa: E402
from desktop.window import create_window  # noqa: E402


def main() -> int:
    url = os.environ.get("HERMES_DEV_URL", "http://127.0.0.1:5173")
    bridge = DesktopBridge()
    icon_candidates = [
        ROOT / "packaging" / "windows" / "assets" / "app-icon.ico",
        ROOT / "frontend" / "public" / "hermes-emblem.svg",
    ]
    icon = next((p for p in icon_candidates if p.exists()), None)
    create_window(url, bridge=bridge, icon_path=icon, title="Hermes — Trading Bot")
    webview.start(debug=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
