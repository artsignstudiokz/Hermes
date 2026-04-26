#!/usr/bin/env bash
# Build Hermes.app bundle on macOS via PyInstaller.
#
# Usage:
#   cd <repo root>
#   bash packaging/macos/build_app.sh
#
# Produces: dist/Hermes.app

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

echo "▸ [1/3] Building frontend (Vite)…"
pushd "$ROOT/frontend" >/dev/null
[ -d node_modules ] || npm install
npm run build
popd >/dev/null

echo "▸ [2/3] PyInstaller .app bundle…"
pyinstaller --noconfirm --clean \
  --windowed \
  --name "Hermes" \
  --osx-bundle-identifier "kz.baicore.hermes" \
  --icon "$ROOT/packaging/macos/app-icon.icns" \
  --add-data "$ROOT/frontend/dist:backend/app/static" \
  --add-data "$ROOT/packaging/windows/assets:packaging/windows/assets" \
  --hidden-import uvicorn \
  --hidden-import fastapi \
  --hidden-import ccxt \
  --hidden-import ccxt.async_support \
  --hidden-import optuna \
  --hidden-import aiosqlite \
  --hidden-import argon2 \
  --hidden-import argon2._ffi \
  --hidden-import pywebpush \
  --hidden-import qrcode \
  --hidden-import pyngrok \
  --hidden-import apscheduler \
  --hidden-import scipy \
  --hidden-import pync \
  --runtime-hook "$ROOT/packaging/pyinstaller/runtime_hook.py" \
  --paths "$ROOT" --paths "$ROOT/backend" \
  "$ROOT/desktop/main.py"

APP="$ROOT/dist/Hermes.app"
if [ ! -d "$APP" ]; then
  echo "ERROR: PyInstaller did not produce $APP" >&2
  exit 2
fi

echo "▸ [3/3] Patching Info.plist…"
PLIST="$APP/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Set :CFBundleName Hermes" "$PLIST" || true
/usr/libexec/PlistBuddy -c "Set :CFBundleDisplayName Hermes" "$PLIST" || true
/usr/libexec/PlistBuddy -c "Set :NSHumanReadableCopyright '© BAI Core. All rights reserved.'" "$PLIST" || \
  /usr/libexec/PlistBuddy -c "Add :NSHumanReadableCopyright string '© BAI Core. All rights reserved.'" "$PLIST"
/usr/libexec/PlistBuddy -c "Set :LSMinimumSystemVersion 12.0" "$PLIST" || \
  /usr/libexec/PlistBuddy -c "Add :LSMinimumSystemVersion string 12.0" "$PLIST"

# ATS exception so PyWebView (WKWebView) can talk to http://127.0.0.1:<port>.
/usr/libexec/PlistBuddy -c "Add :NSAppTransportSecurity dict" "$PLIST" 2>/dev/null || true
/usr/libexec/PlistBuddy -c "Add :NSAppTransportSecurity:NSAllowsLocalNetworking bool true" "$PLIST" 2>/dev/null || true

# ── Codesign ───────────────────────────────────────────────────────────────
# Three modes, in priority order:
#   1. Developer ID (env HERMES_SIGN_IDENTITY) — full Gatekeeper-friendly signature.
#   2. Ad-hoc       (default, no env)         — free, no Apple ID required.
#                                               Removes "broken binary" errors and
#                                               makes the app launchable after the
#                                               user explicitly allows it once via
#                                               System Settings → Privacy & Security.
#   3. None         (HERMES_SIGN_SKIP=1)     — only for debugging.
if [ "${HERMES_SIGN_SKIP:-}" = "1" ]; then
  echo "▸ codesign skipped (HERMES_SIGN_SKIP=1)"
elif [ -n "${HERMES_SIGN_IDENTITY:-}" ]; then
  echo "▸ codesign with Developer ID ${HERMES_SIGN_IDENTITY}"
  codesign --deep --force --sign "$HERMES_SIGN_IDENTITY" \
           --options runtime \
           --entitlements "$ROOT/packaging/macos/entitlements.plist" \
           "$APP"
else
  echo "▸ ad-hoc codesign (no Apple Developer ID — see docs/USER_GUIDE_RU.md)"
  codesign --deep --force --sign - \
           --entitlements "$ROOT/packaging/macos/entitlements.plist" \
           "$APP"
fi

# Verify signature is structurally valid.
codesign --verify --deep --strict --verbose=2 "$APP" 2>&1 | tail -5 || true

echo ""
echo "✓ Hermes.app built: $APP"
