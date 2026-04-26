# Full release pipeline for Hermes (Windows).
# 1. Build the React frontend → frontend/dist/
# 2. PyInstaller bundles desktop/main.py + frontend/dist → dist/Hermes.exe
# 3. Inno Setup wraps Hermes.exe into Hermes-Setup-1.0.0.exe (browser-like installer)
#
# Prerequisites:
#   - Node.js >= 20
#   - Python >= 3.11 with backend deps installed (`pip install -e backend[desktop]`)
#   - Inno Setup 6 on PATH (`iscc`)
#
# Usage:  .\scripts\build_release.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "▸ [1/3] Building frontend (Vite)…" -ForegroundColor Cyan
Set-Location (Join-Path $root "frontend")
if (-not (Test-Path "node_modules")) { npm install }
npm run build
Set-Location $root

Write-Host "▸ [2/3] Bundling executable (PyInstaller)…" -ForegroundColor Cyan
pyinstaller --noconfirm --clean (Join-Path "packaging" "pyinstaller" "hermes.spec")

if (-not (Test-Path (Join-Path $root "dist" "Hermes.exe"))) {
    Write-Error "PyInstaller did not produce dist\Hermes.exe"
    exit 2
}

Write-Host "▸ [3/3] Building installer (Inno Setup)…" -ForegroundColor Cyan
$iscc = Get-Command iscc -ErrorAction SilentlyContinue
if (-not $iscc) {
    Write-Warning "Inno Setup (iscc) not on PATH — skipping installer build."
    Write-Warning "Install Inno Setup 6 from https://jrsoftware.org/isdl.php and add it to PATH."
    Write-Host "Standalone executable ready: dist\Hermes.exe" -ForegroundColor Green
    exit 0
}
& iscc (Join-Path $root "packaging" "windows" "installer.iss")

# Optional code-signing — only runs if HERMES_SIGNTOOL_PFX + HERMES_SIGNTOOL_PASSWORD are set.
# Without these, the installer ships unsigned (SmartScreen will warn until reputation builds up).
if ($env:HERMES_SIGNTOOL_PFX -and $env:HERMES_SIGNTOOL_PASSWORD) {
    $signtool = Get-Command signtool -ErrorAction SilentlyContinue
    if ($signtool) {
        Write-Host "▸ [4/4] Signing executables (signtool)…" -ForegroundColor Cyan
        & signtool sign /f $env:HERMES_SIGNTOOL_PFX /p $env:HERMES_SIGNTOOL_PASSWORD `
                   /tr http://timestamp.digicert.com /td sha256 /fd sha256 `
                   "$root\dist\Hermes.exe"
        Get-ChildItem "$root\dist\installer\Hermes-Setup-*.exe" | ForEach-Object {
            & signtool sign /f $env:HERMES_SIGNTOOL_PFX /p $env:HERMES_SIGNTOOL_PASSWORD `
                       /tr http://timestamp.digicert.com /td sha256 /fd sha256 $_.FullName
        }
    } else {
        Write-Warning "signtool not on PATH — cannot sign even though cert is configured."
    }
} else {
    Write-Host "▸ Code-signing skipped (no HERMES_SIGNTOOL_PFX env var)." -ForegroundColor DarkYellow
    Write-Host "  Releasing unsigned. SmartScreen will warn users until reputation builds." -ForegroundColor DarkYellow
    Write-Host "  Workarounds documented in docs/USER_GUIDE_RU.md and on landing FAQ."     -ForegroundColor DarkYellow
}

# Compute hashes so we can publish them next to the download links.
& "$PSScriptRoot\compute_hashes.ps1"

Write-Host ""
Write-Host "✓ Hermes release built successfully." -ForegroundColor Green
Write-Host "  Standalone exe: dist\Hermes.exe"
Write-Host "  Installer:      dist\installer\Hermes-Setup-1.0.0.exe"
Write-Host "  Hashes:         dist\SHA256SUMS.txt"
