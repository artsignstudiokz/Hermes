# Dev: run Vite dev server with HMR. Proxies /api and /ws to backend on 8765.
# Usage: .\scripts\dev_frontend.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location (Join-Path $root "frontend")

if (-not (Test-Path "node_modules")) {
    Write-Host "Installing dependencies (first run)…" -ForegroundColor Yellow
    npm install
}

Write-Host "Hermes frontend → http://127.0.0.1:5173" -ForegroundColor Yellow
npm run dev
