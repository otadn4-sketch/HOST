# Apply the source in this folder to the running Docker stack (Windows PowerShell).
# Keeps database, vault, and uploaded files. Rebuilds only application code.
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

if (-not (Test-Path "docker-compose.yml")) {
  Write-Error "docker-compose.yml in this folder was not found."
}
if (-not (Test-Path ".env")) {
  Write-Error ".env is missing. Copy it from the previous install. Do not run bootstrap.sh again."
}

Write-Host "This folder will be built into the running containers."
Write-Host "Database, vault, and uploaded files are kept."
Write-Host "Only live_app and live_frontend volumes are recreated."

function Get-MountVolume([string]$service, [string]$destination) {
  $ids = @(docker compose ps -aq $service 2>$null | Where-Object { $_.Trim() -ne "" })
  if ($ids.Count -eq 0) { return $null }
  $name = docker inspect -f "{{range .Mounts}}{{if eq .Destination `"$destination`"}}{{.Name}}{{end}}{{end}}" $ids[0] 2>$null
  if ($name) { return $name.Trim() }
  return $null
}

$liveApp = Get-MountVolume "backend" "/app"
$liveFe = Get-MountVolume "frontend" "/usr/share/nginx/html"

Write-Host "Building images..."
docker compose build backend frontend update-agent
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Stopping app services..."
docker compose stop backend frontend update-agent nginx 2>$null
docker compose rm -f backend frontend update-agent 2>$null

$toRemove = @()
if ($liveApp) { $toRemove += $liveApp }
if ($liveFe) { $toRemove += $liveFe }
$toRemove += @(docker volume ls --format "{{.Name}}" | Where-Object { $_ -match "live_app$|live_frontend$" })
$toRemove = $toRemove | Where-Object { $_ } | Select-Object -Unique
foreach ($vol in $toRemove) {
  Write-Host "Removing code volume: $vol"
  docker volume rm -f $vol | Out-Null
}

Write-Host "Starting stack with new images..."
docker compose up -d --build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Waiting for backend health..."
$ok = $false
for ($i = 0; $i -lt 60; $i++) {
  docker compose exec -T backend python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')" 2>$null | Out-Null
  if ($LASTEXITCODE -eq 0) { $ok = $true; break }
  Start-Sleep -Seconds 2
}
if (-not $ok) {
  docker compose logs --tail=80 backend
  Write-Error "Backend did not become healthy."
}

Write-Host -NoNewline "Running VERSION: "
docker compose exec -T backend python -c "print(open('/app/VERSION',encoding='utf-8').read().strip())"
Write-Host "Source apply finished. The in-app zip installer is not needed for this step."
