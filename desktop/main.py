"""Hermes desktop entry point.

Boot sequence:
  1. Ensure single instance (named mutex / lock-file).
  2. Show native splash (Tkinter) so the user sees feedback in <100 ms.
  3. Pick an ephemeral loopback port and start uvicorn in a daemon thread.
  4. Poll /api/system/health until ready (10s timeout).
  5. Create the frameless PyWebView window, hide the splash, hand off.
  6. On window close — graceful shutdown of backend.
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
from pathlib import Path

import httpx
import uvicorn
import webview

from desktop.ipc_bridge import DesktopBridge
from desktop.port_finder import find_free_port
from desktop.single_instance import SingleInstance
from desktop.splash import SplashWindow
from desktop.window import create_window

# ── Resolve resource paths (handles both `python desktop/main.py` and PyInstaller bundle) ──
def _resource_root() -> Path:
    if getattr(sys, "frozen", False):
        # PyInstaller onefile: resources live under sys._MEIPASS.
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parent.parent


ROOT = _resource_root()
ASSETS_DIR = ROOT / "packaging" / "windows" / "assets"
SPLASH_LOGO = ASSETS_DIR / "splash.png"
APP_ICON = ASSETS_DIR / "app-icon.ico"

# Ensure backend package is importable.
sys.path.insert(0, str(ROOT / "backend"))


def _start_backend(port: int) -> threading.Thread:
    """Run uvicorn in a daemon thread bound to 127.0.0.1:<port>."""
    # Tell the FastAPI app where the static frontend lives.
    static_candidates = [
        ROOT / "backend" / "app" / "static",  # production bundle
        ROOT / "frontend" / "dist",  # dev bundle
    ]
    for cand in static_candidates:
        if cand.exists():
            os.environ["BCT_STATIC_DIR"] = str(cand)
            break

    os.environ.setdefault("BCT_HOST", "127.0.0.1")
    os.environ["BCT_PORT"] = str(port)

    def _run() -> None:
        from app.main import app  # imported lazily so settings env vars take effect

        config = uvicorn.Config(
            app,
            host="127.0.0.1",
            port=port,
            log_level="info",
            access_log=False,
            lifespan="on",
        )
        server = uvicorn.Server(config)
        server.run()

    t = threading.Thread(target=_run, daemon=True, name="hermes-backend")
    t.start()
    return t


def _wait_for_ready(port: int, timeout: float = 15.0) -> bool:
    """Poll /api/system/health until 200 or timeout."""
    deadline = time.time() + timeout
    url = f"http://127.0.0.1:{port}/api/system/health"
    while time.time() < deadline:
        try:
            r = httpx.get(url, timeout=0.6)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.15)
    return False


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    log = logging.getLogger("hermes")

    # 1. Single instance.
    from app.settings import get_settings  # noqa: E402

    settings = get_settings()
    instance = SingleInstance(settings.data_dir)
    if not instance.acquire():
        log.warning("Another Hermes instance is already running. Exiting.")
        return 0

    # 2. Splash.
    splash = SplashWindow(SPLASH_LOGO, brand="Hermes — Trading Bot")
    splash.show()

    try:
        # 3. Backend.
        port = find_free_port()
        log.info("Starting backend on 127.0.0.1:%d", port)
        _start_backend(port)

        # 4. Wait for ready.
        if not _wait_for_ready(port):
            log.error("Backend failed to start within timeout")
            splash.close()
            return 2

        # 5. Webview.
        bridge = DesktopBridge()
        url = f"http://127.0.0.1:{port}/"
        log.info("Opening main window → %s", url)
        create_window(url, bridge=bridge, icon_path=APP_ICON if APP_ICON.exists() else None)

        # Close splash once webview is up.
        def _on_loaded() -> None:
            splash.close()

        webview.windows[0].events.loaded += _on_loaded
        webview.start(debug=settings.dev_mode)
    finally:
        splash.close()
        instance.release()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
