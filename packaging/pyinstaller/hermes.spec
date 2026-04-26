# PyInstaller spec for Hermes (BAI Core).
# Build:  pyinstaller packaging/pyinstaller/hermes.spec
#
# Produces a single console-less .exe bundling the FastAPI backend, the React
# frontend (frontend/dist), and PyWebView. Output: dist/Hermes.exe

# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent.parent  # noqa: F821 (defined by PyInstaller)
BACKEND = ROOT / "backend"
FRONTEND_DIST = ROOT / "frontend" / "dist"
ASSETS = ROOT / "packaging" / "windows" / "assets"

block_cipher = None

datas = []
if FRONTEND_DIST.exists():
    datas.append((str(FRONTEND_DIST), "backend/app/static"))
if ASSETS.exists():
    datas.append((str(ASSETS), "packaging/windows/assets"))

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
    # Brokers
    "MetaTrader5",
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
    "win10toast",
    "yfinance",
]

a = Analysis(
    [str(ROOT / "desktop" / "main.py")],
    pathex=[str(ROOT), str(BACKEND)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[str(ROOT / "packaging" / "pyinstaller" / "hooks")],
    runtime_hooks=[str(ROOT / "packaging" / "pyinstaller" / "runtime_hook.py")],
    excludes=["tkinter.test", "test", "unittest"],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="Hermes",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ASSETS / "app-icon.ico"),
    version=str(ROOT / "packaging" / "pyinstaller" / "version_info.txt"),
)
