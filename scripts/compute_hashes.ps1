# Compute SHA-256 + size for every release artefact in dist/.
# Output: dist/SHA256SUMS.txt — published alongside binaries on the
# download page so users can verify integrity without a code-signing cert.
#
# Usage:  .\scripts\compute_hashes.ps1 [-Out path\SHA256SUMS.txt]

[CmdletBinding()]
param(
    [string]$Out = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$dist = Join-Path $root "dist"
if (-not (Test-Path $dist)) {
    Write-Error "$dist not found — run build_release.ps1 first."
}

if ([string]::IsNullOrEmpty($Out)) {
    $Out = Join-Path $dist "SHA256SUMS.txt"
}

$lines = @(
    "# Hermes — SHA-256 checksums",
    "# Verify before installing:",
    "#   PowerShell:  Get-FileHash <file> -Algorithm SHA256",
    "#   bash:        shasum -a 256 <file>",
    ""
)

$artefacts = Get-ChildItem -Path $dist -Recurse -Include `
    "Hermes.exe", "Hermes-Setup-*.exe", "Hermes-*.pkg", "Hermes.app.zip" `
    -ErrorAction SilentlyContinue

if (-not $artefacts -or $artefacts.Count -eq 0) {
    Write-Warning "No artefacts found under $dist"
} else {
    foreach ($f in $artefacts | Sort-Object FullName) {
        $hash = (Get-FileHash $f.FullName -Algorithm SHA256).Hash.ToLower()
        $size = "{0:N0}" -f $f.Length
        $rel = $f.FullName.Substring($dist.Length).TrimStart('\','/')
        $lines += "$hash  $rel  ($size bytes)"
        Write-Host "  $rel" -ForegroundColor DarkGray
        Write-Host "    sha256: $hash"
    }
}

$lines += ""
$lines += "Generated $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')"
$lines | Set-Content -Path $Out -Encoding utf8

Write-Host ""
Write-Host "✓ SHA256SUMS written to $Out" -ForegroundColor Green
