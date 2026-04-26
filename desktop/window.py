"""PyWebView window factory — frameless native window with Hermes branding."""

from __future__ import annotations

import logging
from pathlib import Path

import webview

from desktop.ipc_bridge import DesktopBridge

logger = logging.getLogger(__name__)


def create_window(
    url: str,
    *,
    bridge: DesktopBridge,
    icon_path: Path | None = None,
    title: str = "Hermes — Trading Bot",
) -> webview.Window:
    """Create the main app window. Caller is responsible for `webview.start()`."""
    window = webview.create_window(
        title=title,
        url=url,
        width=1440,
        height=900,
        min_size=(1024, 640),
        frameless=True,
        easy_drag=False,  # custom drag region in React title bar
        background_color="#FBF7EC",  # marble while content boots
        text_select=True,
        confirm_close=False,
        js_api=bridge,
    )
    bridge.attach(window)

    if icon_path and icon_path.exists():
        try:
            window.icon = str(icon_path)  # type: ignore[attr-defined]
        except Exception:
            logger.debug("Setting window icon is not supported on this platform")
    return window
