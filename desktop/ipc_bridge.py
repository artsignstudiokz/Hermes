"""JS ↔ Python bridge exposed inside the webview.

In React: `window.pywebview.api.<method>(...)` (Promise-based).
"""

from __future__ import annotations

import logging
import sys
import webbrowser
from typing import Any

logger = logging.getLogger(__name__)


class DesktopBridge:
    """Methods callable from the React frontend via `window.pywebview.api`."""

    def __init__(self) -> None:
        self._window: Any | None = None

    def attach(self, window: Any) -> None:
        self._window = window

    # ── Window controls ─────────────────────────────────────────────────────
    def minimize(self) -> None:
        if self._window:
            self._window.minimize()

    def maximize(self) -> None:
        if self._window:
            try:
                self._window.toggle_fullscreen()
            except Exception:
                # Fallback for older pywebview: maximize via JS not available.
                logger.debug("toggle_fullscreen unsupported; ignoring")

    def close(self) -> None:
        if self._window:
            self._window.destroy()

    # ── Native helpers ──────────────────────────────────────────────────────
    def open_external(self, url: str) -> None:
        """Open an external URL in the system browser (e.g. baicore.kz)."""
        if not url.startswith(("http://", "https://")):
            return
        webbrowser.open(url)

    def show_native_notification(self, title: str, body: str) -> None:
        """Best-effort native toast — falls back silently on unsupported OSes."""
        try:
            if sys.platform == "win32":
                from win10toast import ToastNotifier  # type: ignore

                ToastNotifier().show_toast(title, body, duration=5, threaded=True)
            elif sys.platform == "darwin":
                import pync  # type: ignore

                pync.notify(body, title=title, sound="default")
        except Exception as e:
            logger.debug("native notification failed: %s", e)

    def get_platform(self) -> dict[str, str]:
        return {"os": sys.platform}
