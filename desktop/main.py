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
import traceback
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


_BACKEND_ERROR: Exception | None = None


def _start_backend(port: int) -> threading.Thread:
    """Run uvicorn in a daemon thread bound to 127.0.0.1:<port>."""
    # Tell the FastAPI app where the static frontend lives.
    # Frozen bundle: _MEIPASS/app/static (set by hermes.spec datas).
    # Dev: frontend/dist exists once `npm run build` was run.
    static_candidates = [
        ROOT / "app" / "static",
        ROOT / "backend" / "app" / "static",
        ROOT / "frontend" / "dist",
    ]
    for cand in static_candidates:
        if cand.exists():
            os.environ["BCT_STATIC_DIR"] = str(cand)
            break

    os.environ.setdefault("BCT_HOST", "127.0.0.1")
    os.environ["BCT_PORT"] = str(port)

    log = logging.getLogger("hermes.backend")

    def _run() -> None:
        global _BACKEND_ERROR
        try:
            log.info("Importing app.main…")
            from app.main import app  # imported lazily so settings env vars take effect

            log.info("Starting uvicorn on 127.0.0.1:%d", port)
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
        except Exception as e:  # noqa: BLE001 — capture *anything* and surface it
            _BACKEND_ERROR = e
            log.error("Backend crashed: %s\n%s", e, traceback.format_exc())

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


def _setup_logging() -> Path:
    """Configure logging to BOTH stderr and a file the user can find.

    Returns the log file path (caller may show it in error dialogs).

    PyInstaller --windowed apps have no console, so stderr is /dev/null on
    Windows. Without file logging, any startup failure is invisible: the
    splash flashes, the window never appears, and the user has no
    diagnostic to copy/paste. We resolve the logs dir from BCT_LOGS_DIR
    (set by runtime_hook.py) — same location app.settings._logs_root uses.
    """
    logs_dir = Path(os.environ.get("BCT_LOGS_DIR") or (Path.home() / ".hermes" / "logs"))
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "hermes.log"

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    # Reset any prior handlers (re-runs in same process, e.g. tests).
    root.handlers.clear()

    fh = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    fh.setFormatter(fmt)
    root.addHandler(fh)

    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    root.addHandler(sh)

    return log_file


def _show_error_dialog(title: str, message: str, log_file: Path | None) -> None:
    """Show a native error dialog so the user sees *why* the app exited."""
    full = message
    if log_file is not None:
        full += f"\n\nПолный лог: {log_file}"
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(title, full)
        root.destroy()
    except Exception:  # noqa: BLE001
        # Tkinter unavailable — fall back to MessageBoxW on Windows.
        if sys.platform == "win32":
            try:
                import ctypes

                ctypes.windll.user32.MessageBoxW(0, full, title, 0x10)
            except Exception:
                pass


def main() -> int:
    log_file = _setup_logging()
    log = logging.getLogger("hermes")
    log.info("=" * 60)
    log.info("Hermes starting (frozen=%s, exe=%s)", getattr(sys, "frozen", False), sys.executable)
    log.info("Logs: %s", log_file)

    # 1. Single instance.
    try:
        from app.settings import get_settings  # noqa: E402

        settings = get_settings()
    except Exception as e:  # noqa: BLE001
        log.error("Failed to load settings: %s\n%s", e, traceback.format_exc())
        _show_error_dialog(
            "Hermes — ошибка запуска",
            f"Не удалось загрузить настройки приложения:\n\n{type(e).__name__}: {e}",
            log_file,
        )
        return 3

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
            splash.close()
            err = _BACKEND_ERROR
            if err is not None:
                log.error("Backend failed to start: %s", err)
                _show_error_dialog(
                    "Hermes — backend не запустился",
                    f"Backend упал при старте:\n\n{type(err).__name__}: {err}",
                    log_file,
                )
            else:
                log.error("Backend did not become ready within timeout (no exception captured)")
                _show_error_dialog(
                    "Hermes — backend не отвечает",
                    "Backend не ответил на /api/system/health в течение 15 секунд.\n"
                    "Возможно, занят порт или антивирус блокирует процесс.",
                    log_file,
                )
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
    except Exception as e:  # noqa: BLE001
        log.error("Unhandled exception in main(): %s\n%s", e, traceback.format_exc())
        _show_error_dialog(
            "Hermes — критическая ошибка",
            f"{type(e).__name__}: {e}",
            log_file,
        )
        return 4
    finally:
        splash.close()
        instance.release()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
