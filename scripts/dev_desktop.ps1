# Dev: launch the full Hermes stack — backend + frontend + PyWebView shell.
# Backend and frontend run in background terminals; PyWebView opens the Vite dev URL.
# Usage: .\scripts\dev_desktop.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

Write-Host "▸ Starting backend (port 8765)…" -ForegroundColor Cyan
Start-Process pwsh -ArgumentList "-NoExit", "-File", (Join-Path $PSScriptRoot "dev_backend.ps1") -WindowStyle Normal

Write-Host "▸ Starting frontend dev server (port 5173)…" -ForegroundColor Cyan
Start-Process pwsh -ArgumentList "-NoExit", "-File", (Join-Path $PSScriptRoot "dev_frontend.ps1") -WindowStyle Normal

Start-Sleep -Seconds 3
Write-Host "▸ Launching Hermes desktop window…" -ForegroundColor Yellow

$env:HERMES_DEV_URL = "http://127.0.0.1:5173"
Set-Location (Join-Path $root "desktop")
python .\dev_runner.py
