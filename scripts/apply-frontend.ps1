# Rebuild and refresh ONLY the frontend. Backend, database, and files stay up.
# powershell -ExecutionPolicy Bypass -File .\scripts\apply-frontend.ps1
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

if (-not (Test-Path "docker-compose.yml")) { Write-Error "Not the project folder." }
if (-not (Select-String -Path "frontend\src\components\Navbar.tsx" -Pattern "onOpenMenu" -Quiet)) {
  Write-Error "This folder does not contain the mobile layout (1.2.4). Get the latest source into this folder first, keep .env, then run this script again."
}

Write-Host "Building frontend image (site stays up)..."
docker compose build frontend
if ($LASTEXITCODE -ne 0) { throw "frontend build failed" }

$ErrorActionPreference = "Continue"
$ids = @(docker compose ps -aq frontend 2>$null | Where-Object { $_.Trim() -ne "" })
$vol = $null
if ($ids.Count -gt 0) {
  $raw = docker inspect $ids[0] 2>$null
  if ($raw) {
    $info = $raw | ConvertFrom-Json
    foreach ($mount in @($info.Mounts)) {
      if ($mount.Destination -eq "/usr/share/nginx/html") { $vol = [string]$mount.Name }
    }
  }
}
docker compose stop frontend nginx 2>$null
docker compose rm -f frontend 2>$null
$vols = @()
if ($vol) { $vols += $vol }
$vols += @(docker volume ls --format "{{.Name}}" | Where-Object { $_ -match "live_frontend$" })
$vols = $vols | Where-Object { $_ } | Select-Object -Unique
foreach ($name in $vols) {
  Write-Host "Removing frontend code volume: $name"
  docker volume rm -f $name | Out-Null
}
$ErrorActionPreference = "Stop"

Write-Host "Starting frontend..."
docker compose up -d frontend nginx
if ($LASTEXITCODE -ne 0) { throw "frontend up failed" }
Write-Host "Frontend 1.2.4 is up. Hard-refresh the phone (or clear site data) so the old PWA cache is dropped."
