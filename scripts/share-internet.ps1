# Temporary public HTTPS URL for the local Docker stack (Windows PowerShell).
# Origin is http://127.0.0.1:80. Cloudflare terminates HTTPS for visitors.
# Stop with Ctrl+C. This exposes the live login page to the internet; use only briefly.
# If PowerShell blocks the file, use:
#   powershell -ExecutionPolicy Bypass -File .\scripts\share-internet.ps1
#   .\scripts\share-internet.cmd

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

Write-Host "This publishes the local Eytan stack on a temporary public HTTPS URL."
Write-Host "Anyone with the URL can reach the login page. Stop with Ctrl+C."
Write-Host ""

try {
  Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1/api/health" -TimeoutSec 5 | Out-Null
} catch {
  Write-Host "http://127.0.0.1/api/health is not reachable."
  Write-Host "Start the stack first: docker compose up -d"
  Write-Host "If this folder is a new zip, also run: .\scripts\apply-source.ps1"
  exit 1
}

$dir = Join-Path $env:LOCALAPPDATA "eytan-tools"
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$exe = Join-Path $dir "cloudflared.exe"
if (-not (Test-Path $exe)) {
  Write-Host "Downloading cloudflared (Cloudflare quick tunnel)..."
  Invoke-WebRequest -Uri "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe" -OutFile $exe
}

Write-Host "Starting tunnel. The public URL is printed below (https://....trycloudflare.com)."
Write-Host ""
& $exe tunnel --url http://127.0.0.1:80 --no-autoupdate
