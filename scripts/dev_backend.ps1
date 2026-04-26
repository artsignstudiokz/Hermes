# Dev: run FastAPI backend on a fixed port for the Vite proxy.
# Usage: .\scripts\dev_backend.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location (Join-Path $root "backend")

$env:BCT_PORT = "8765"
$env:BCT_HOST = "127.0.0.1"
$env:BCT_DEV_MODE = "true"

Write-Host "Hermes backend → http://127.0.0.1:8765" -ForegroundColor Yellow
python -m uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload
