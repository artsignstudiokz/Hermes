# PyInstaller spec for Hermes (BAI Core).
# Build:  pyinstaller packaging/pyinstaller/hermes.spec
#
# Single console-less .exe that bundles the FastAPI backend, the React
# frontend (frontend/dist), and PyWebView. Windows: dist/Hermes.exe.
# macOS:   dist/Hermes.app via the `--windowed` flag in build_app.sh.

# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

ROOT = Path(SPECPATH).resolve().parent.parent  # noqa: F821 (SPECPATH defined by PyInstaller)
BACKEND = ROOT / "backend"
FRONTEND_DIST = ROOT / "frontend" / "dist"
ASSETS = ROOT / "packaging" / "windows" / "assets"

block_cipher = None
IS_WIN = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"

# ── Bundled data ──────────────────────────────────────────────────────────
datas = []
binaries = []
if FRONTEND_DIST.exists():
    datas.append((str(FRONTEND_DIST), "backend/app/static"))
if ASSETS.exists():
    datas.append((str(ASSETS), "packaging/windows/assets"))

# ── collect_all for packages that have data files / dynamic submodules ───
# These are notoriously hard for PyInstaller's static analysis to fully
# pick up. Using collect_all walks the package tree and adds everything.
COLLECT_ALL_PKGS = (
    # HTTP stack — main.py imports httpx directly; uvicorn/fastapi pull
    # in starlette + websockets + h11 + anyio + sniffio under the hood.
    "httpx",
    "httpcore",
    "h11",
    "h2",
    "anyio",
    "sniffio",
    "certifi",
    "idna",
    "uvicorn",
    "fastapi",
    "starlette",
    "websockets",
    # Settings / models / serialization.
    "pydantic",
    "pydantic_settings",
    "pydantic_core",
    # Storage.
    "sqlalchemy",
    "aiosqlite",
    "alembic",
    # Security.
    "argon2",
    "cryptography",
    "jwt",
    # Trading + ML.
    "ccxt",
    "optuna",
    "pandas",
    "numpy",
    "scipy",
    # Notifications + tunnel.
    "pywebpush",
    "py_vapid",
    "qrcode",
    "PIL",
    "pyngrok",
    # Scheduler.
    "apscheduler",
    # Misc.
    "platformdirs",
    "webview",
    "multipart",
)

for pkg in COLLECT_ALL_PKGS:
    try:
        d, b, h = collect_all(pkg)
        datas.extend(d)
        binaries.extend(b)
    except Exception:
        # Package may not be installed (e.g. webview on macOS via different name).
        pass

# ── Hidden imports (only those PyInstaller's static analysis misses) ──────
hidden_imports = [
    # Web stack
    "uvicorn",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.lifespan.on",
    "uvicorn.loops.asyncio",
    "fastapi",
    "websockets",
    "websockets.legacy",
    "websockets.legacy.server",
    "h11",
    "starlette",

    # Brokers (cross-platform: ccxt). MT5 added below for Windows only.
    "ccxt",
    "ccxt.async_support",
    "ccxt.async_support.binance",
    "ccxt.async_support.bybit",
    "ccxt.async_support.okx",

    # ML / numerics
    "optuna",
    "optuna.samplers",
    "optuna.pruners",
    "scipy",
    "scipy.stats",
    "scipy.special",
    "scipy.signal",
    "pandas",
    "numpy",

    # Storage
    "aiosqlite",
    "sqlalchemy.dialects.sqlite",
    "alembic",

    # Security
    "cryptography.hazmat.backends.openssl",
    "argon2",
    "argon2._ffi",
    "argon2.low_level",
    "jwt",
    "jwt.algorithms",

    # Notifications + tunnel
    "pywebpush",
    "py_vapid",
    "qrcode",
    "qrcode.image.pil",
    "PIL",
    "pyngrok",

    # Scheduler
    "apscheduler",
    "apscheduler.schedulers.asyncio",
    "apscheduler.triggers.cron",
    "apscheduler.triggers.interval",

    # Misc
    "platformdirs",
]

# Platform-conditional hidden imports — adding non-installed packages to this
# list aborts PyInstaller's analysis on the wrong platform.
if IS_WIN:
    hidden_imports += ["MetaTrader5", "win10toast"]
if IS_MAC:
    hidden_imports += ["pync"]

# ── Excludes — heavy or platform-specific deps that the legacy code
#     references lazily. They are not needed for the desktop runtime
#     and would bloat the bundle by tens of megabytes if pulled in.
excludes = [
    "tkinter.test",
    "test",
    "unittest",
    "yfinance",            # legacy backtester historic data — runtime-optional
    "matplotlib",          # legacy reporting — not used by the desktop app
    "matplotlib.pyplot",
    "seaborn",
]

# Add submodules from packages that frequently miss their dynamic imports.
for sub_pkg in (
    "platformdirs",
    "pydantic",
    "pydantic_settings",
    "argon2",
    "httpx",
    "httpcore",
    "anyio",
    "uvicorn",
    "starlette",
    "websockets",
    "sqlalchemy",
    "alembic",
):
    try:
        hidden_imports.extend(collect_submodules(sub_pkg))
    except Exception:
        pass

a = Analysis(
    [str(ROOT / "desktop" / "main.py")],
    pathex=[str(ROOT), str(BACKEND)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    runtime_hooks=[str(ROOT / "packaging" / "pyinstaller" / "runtime_hook.py")],
    excludes=excludes,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

icon_file = ASSETS / "app-icon.ico"
version_file = ROOT / "packaging" / "pyinstaller" / "version_info.txt"

# onedir mode — produces dist/Hermes/ folder with Hermes.exe + all DLLs/PYDs
# loose. This is dramatically more reliable than onefile because PyInstaller
# doesn't unpack to a temp dir at runtime — every package is just present
# on disk where Python's import machinery expects it. Inno Setup ships the
# whole folder so the user-visible install experience is identical.
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Hermes",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon_file) if icon_file.exists() else None,
    version=str(version_file) if (IS_WIN and version_file.exists()) else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Hermes",
)
