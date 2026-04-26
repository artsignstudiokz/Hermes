#!/usr/bin/env bash
# Wrap the existing Hermes.app bundle into an installer .pkg.
#
# Run AFTER build_app.sh. Output: dist/installer/Hermes-1.0.0.pkg
#
# To produce a notarized package on a build server:
#   export HERMES_SIGN_IDENTITY="Developer ID Application: BAI Core (TEAMID)"
#   export HERMES_INSTALLER_IDENTITY="Developer ID Installer: BAI Core (TEAMID)"
#   bash packaging/macos/build_app.sh && bash packaging/macos/build_pkg.sh

set -euo pipefail

VERSION="${HERMES_VERSION:-1.0.0}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
APP="$ROOT/dist/Hermes.app"
OUT_DIR="$ROOT/dist/installer"
OUT="$OUT_DIR/Hermes-$VERSION.pkg"

if [ ! -d "$APP" ]; then
  echo "ERROR: $APP not found. Run build_app.sh first." >&2
  exit 2
fi

mkdir -p "$OUT_DIR"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

ROOT_PAYLOAD="$TMP/root"
mkdir -p "$ROOT_PAYLOAD/Applications"
cp -R "$APP" "$ROOT_PAYLOAD/Applications/"

echo "▸ pkgbuild — component package"
pkgbuild --root "$ROOT_PAYLOAD" \
         --identifier kz.baicore.hermes \
         --version "$VERSION" \
         --install-location "/" \
         "$TMP/component.pkg"

echo "▸ productbuild — distribution"
PRODUCT_FLAGS=( --distribution "$ROOT/packaging/macos/Distribution.xml"
                --package-path "$TMP"
                --resources "$ROOT/packaging/macos" )

if [ -n "${HERMES_INSTALLER_IDENTITY:-}" ]; then
  PRODUCT_FLAGS+=( --sign "$HERMES_INSTALLER_IDENTITY" )
fi

productbuild "${PRODUCT_FLAGS[@]}" "$OUT"

echo ""
echo "✓ Installer built: $OUT"
echo "  (For Gatekeeper-friendly distribution, run:"
echo "     xcrun notarytool submit \"$OUT\" --keychain-profile <profile> --wait"
echo "     xcrun stapler staple \"$OUT\")"
