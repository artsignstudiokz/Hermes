# Hermes smoke test — boots the standalone backend, walks through the
# happy path, asserts each step. Designed to run on a clean Windows VM
# after `build_release.ps1`.
#
# Usage:  .\scripts\smoke.ps1 [-Exe path\to\Hermes.exe]
#
# The script does NOT spawn the PyWebView window — it talks to the
# backend directly via REST so it works headless on a CI runner.

[CmdletBinding()]
param(
    [string]$Exe = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
if ([string]::IsNullOrEmpty($Exe)) {
    $Exe = Join-Path $root "dist\Hermes.exe"
}
if (-not (Test-Path $Exe)) {
    Write-Error "Hermes.exe not found at $Exe — build it first via build_release.ps1"
}

# Pick a port we can talk to.
$port = 8765
$env:BCT_PORT = "$port"
$env:BCT_HOST = "127.0.0.1"
$env:BCT_DEV_MODE = "true"

Write-Host "▸ Smoke test: launching $Exe on port $port" -ForegroundColor Cyan

# Use a temporary data directory so we don't pollute %APPDATA%.
$dataDir = Join-Path $env:TEMP ("hermes-smoke-" + [guid]::NewGuid().ToString("N").Substring(0,8))
New-Item -ItemType Directory -Force -Path $dataDir | Out-Null
$env:BCT_DATA_DIR = $dataDir

$proc = Start-Process -FilePath $Exe -PassThru -WindowStyle Hidden
try {
    # Poll /api/system/health up to 30 s.
    $base = "http://127.0.0.1:$port"
    $ready = $false
    for ($i = 0; $i -lt 60; $i++) {
        try {
            $r = Invoke-RestMethod -Uri "$base/api/system/health" -TimeoutSec 1 -ErrorAction Stop
            if ($r.ok) { $ready = $true; break }
        } catch { }
        Start-Sleep -Milliseconds 500
    }
    if (-not $ready) { throw "Backend did not become ready within 30 s" }
    Write-Host "  ✓ /api/system/health → OK ($($r.product) $($r.version))" -ForegroundColor Green

    # Auth state — first-run expected.
    $state = Invoke-RestMethod "$base/api/auth/state"
    if (-not $state.first_run) { throw "Expected first_run=true, got $($state.first_run)" }
    Write-Host "  ✓ /api/auth/state → first_run=true" -ForegroundColor Green

    # Setup master password.
    $body = @{ master_password = "smoke-test-1234" } | ConvertTo-Json
    $token = Invoke-RestMethod -Method Post -Uri "$base/api/auth/setup-master-password" `
                               -Body $body -ContentType "application/json"
    if (-not $token.token) { throw "No token returned" }
    Write-Host "  ✓ /api/auth/setup-master-password → token issued" -ForegroundColor Green

    $headers = @{ Authorization = "Bearer $($token.token)" }

    # Onboarding status.
    $onb = Invoke-RestMethod "$base/api/onboarding/status" -Headers $headers
    if (-not $onb.vault_initialised) { throw "Vault should be initialised" }
    Write-Host "  ✓ /api/onboarding/status → vault initialised, next=$($onb.next_step)" -ForegroundColor Green

    # MT5 server autodetect (always succeeds — falls back to bundled list).
    $servers = Invoke-RestMethod "$base/api/onboarding/mt5/servers"
    Write-Host "  ✓ /api/onboarding/mt5/servers → $($servers.Count) servers" -ForegroundColor Green

    # Strategy presets.
    $presets = Invoke-RestMethod "$base/api/strategy/presets"
    if ($presets.Count -lt 4) { throw "Expected ≥4 presets, got $($presets.Count)" }
    Write-Host "  ✓ /api/strategy/presets → $($presets.Count) presets" -ForegroundColor Green

    # VAPID key for Web Push.
    $vapid = Invoke-RestMethod "$base/api/notifications/vapid-public" -Headers $headers
    if (-not $vapid.key) { throw "VAPID key missing" }
    Write-Host "  ✓ /api/notifications/vapid-public → key issued" -ForegroundColor Green

    Write-Host ""
    Write-Host "✓ All smoke checks passed." -ForegroundColor Green
}
finally {
    if ($proc -and -not $proc.HasExited) {
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    }
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue $dataDir
}
