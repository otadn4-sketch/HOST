# Rebuild and refresh ONLY frontend static files.
# Backend is stopped briefly because it also mounts live_frontend.
# powershell -ExecutionPolicy Bypass -File .\scripts\apply-frontend.ps1
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

if (-not (Test-Path "docker-compose.yml")) { Write-Error "Not the project folder." }
if (-not (Select-String -Path "frontend\src\components\Navbar.tsx" -Pattern "onOpenMenu" -Quiet)) {
  Write-Error "This folder does not contain the mobile layout. Update the source in this folder, keep .env, then rerun."
}

Write-Host "Building frontend with --no-cache (previous build was served from cache)..."
docker compose build --no-cache frontend
if ($LASTEXITCODE -ne 0) { throw "frontend build failed" }

Write-Host "Stopping services that mount live_frontend (frontend, nginx, backend, update-agent)..."
$ErrorActionPreference = "Continue"
docker compose stop frontend nginx backend update-agent 2>$null
docker compose rm -f frontend 2>$null
$vols = @(docker volume ls --format "{{.Name}}" | Where-Object { $_ -match "live_frontend$" })
foreach ($name in $vols) {
  Write-Host "Removing frontend code volume: $name"
  docker volume rm -f $name
}
$ErrorActionPreference = "Stop"

Write-Host "Starting stack..."
docker compose up -d
if ($LASTEXITCODE -ne 0) { throw "up failed" }
Write-Host "Done. Hard-refresh the phone or clear site data so the old PWA cache is dropped."
