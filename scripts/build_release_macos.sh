#!/usr/bin/env bash
# Full macOS release pipeline: frontend → .app → .pkg.
# Run this on a Mac host (PyInstaller + pkgbuild are macOS-native).

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

bash packaging/macos/build_app.sh
bash packaging/macos/build_pkg.sh

echo ""
echo "✓ macOS release built:"
echo "  dist/Hermes.app"
echo "  dist/installer/Hermes-${HERMES_VERSION:-1.0.0}.pkg"
