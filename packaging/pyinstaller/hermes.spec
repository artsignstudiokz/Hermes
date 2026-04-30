# PyInstaller spec for Hermes (BAI Core).
# Build:  pyinstaller packaging/pyinstaller/hermes.spec
#
# onedir mode — produces dist/Hermes/ folder with Hermes.exe + all DLLs/PYDs.
# Inno Setup ships the whole folder so install UX is unchanged for the user.

# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

ROOT = Path(SPECPATH).resolve().parent.parent  # noqa: F821
BACKEND = ROOT / "backend"
FRONTEND_DIST = ROOT / "frontend" / "dist"
ASSETS = ROOT / "packaging" / "windows" / "assets"

block_cipher = None
IS_WIN = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"

# ── Bundled data ──────────────────────────────────────────────────────────
datas = []
binaries = []
hidden_imports = []
# Frontend SPA destination MUST be `app/static/` so it matches
# app.main._default_static_dir() = Path(__file__).parent / "static"
# (which is _internal/app/static/ in the frozen bundle).
if FRONTEND_DIST.exists():
    datas.append((str(FRONTEND_DIST), "app/static"))
if ASSETS.exists():
    datas.append((str(ASSETS), "packaging/windows/assets"))

# ── collect_all walks the whole package tree, finds:
#     - data files (datas)
#     - binary files like .so / .pyd (binaries)
#     - submodules to mark as hidden imports (hiddenimports)
#
# CRITICAL: we MUST extend hidden_imports with the result, not discard it!
# The previous version of this spec dropped the `h` return value silently,
# which is why httpx kept "missing" at runtime even after being listed here.

COLLECT_ALL_PKGS = (
    # HTTP stack — main.py imports httpx directly.
    "httpx",
    "httpcore",
    "h11",
    "anyio",
    "sniffio",
    "certifi",
    "idna",
    # Web server.
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
)

# h2 is optional — depends on httpx version. Try collect_all but don't crash if missing.
OPTIONAL_PKGS = ("h2", "multipart", "python_multipart")

print("=" * 60)
print("Hermes spec: collect_all phase")
print("=" * 60)

for pkg in COLLECT_ALL_PKGS:
    try:
        d, b, h = collect_all(pkg)
        datas.extend(d)
        binaries.extend(b)
        hidden_imports.extend(h)
        print(f"  collect_all('{pkg}'): {len(d)} data, {len(b)} binaries, {len(h)} hidden")
    except Exception as e:
        print(f"  WARN  collect_all('{pkg}') failed: {type(e).__name__}: {e}")

for pkg in OPTIONAL_PKGS:
    try:
        d, b, h = collect_all(pkg)
        datas.extend(d)
        binaries.extend(b)
        hidden_imports.extend(h)
        print(f"  optional collect_all('{pkg}'): {len(h)} hidden")
    except Exception:
        pass

print(f"  Total hidden imports after collect_all: {len(hidden_imports)}")
print("=" * 60)

# ── Manual hidden imports — names PyInstaller might miss even with collect_all
hidden_imports += [
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.lifespan.on",
    "uvicorn.loops.asyncio",
    "ccxt.async_support.binance",
    "ccxt.async_support.bybit",
    "ccxt.async_support.okx",
    "scipy.stats",
    "scipy.special",
    "scipy.signal",
    "sqlalchemy.dialects.sqlite",
    "cryptography.hazmat.backends.openssl",
    "argon2._ffi",
    "argon2.low_level",
    "jwt.algorithms",
    "qrcode.image.pil",
    "apscheduler.schedulers.asyncio",
    "apscheduler.triggers.cron",
    "apscheduler.triggers.interval",
]

# Platform-conditional hidden imports.
if IS_WIN:
    hidden_imports += ["MetaTrader5", "win10toast"]
if IS_MAC:
    hidden_imports += ["pync"]

# ── Excludes — heavy or platform-specific deps that aren't needed at runtime.
excludes = [
    "tkinter.test",
    "test",
    "unittest",
    "yfinance",
    "matplotlib",
    "matplotlib.pyplot",
    "seaborn",
]

# Dedupe to keep the analysis fast.
hidden_imports = sorted(set(hidden_imports))
print(f"Final hidden_imports count: {len(hidden_imports)}")
print("=" * 60)

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
