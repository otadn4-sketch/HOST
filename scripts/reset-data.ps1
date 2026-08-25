# Destructive, opt-in wipe of application users, database, vault, quarantine,
# and local encrypted backups. Does not delete source, .env, TLS certs,
# ClamAV signatures, or the live_app / live_frontend code volumes.
# If PowerShell blocks the file, use:
#   powershell -ExecutionPolicy Bypass -File .\scripts\reset-data.ps1 --i-understand-this-deletes-all-users-and-files
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

$ConfirmationPhrase = "RESET-EYTAN-DATA"
$RequiredFlag = "--i-understand-this-deletes-all-users-and-files"
$DryRun = $false
$ConfirmedFlag = $false

function Show-Usage {
  Write-Host "Usage:"
  Write-Host "  .\scripts\reset-data.ps1 --dry-run"
  Write-Host "  .\scripts\reset-data.ps1 $RequiredFlag"
  Write-Host ""
  Write-Host "This permanently deletes users, files, audit logs, vault contents,"
  Write-Host "quarantine, and local encrypted backups on this Docker stack."
  Write-Host "After a successful wipe: .\scripts\create-admin.sh  (or Git Bash)"
  Write-Host "Non-interactive: `$env:EYTAN_CONFIRM_RESET='$ConfirmationPhrase'"
}

foreach ($arg in $args) {
  switch ($arg) {
    "--dry-run" { $DryRun = $true }
    "--help" { Show-Usage; exit 0 }
    "-h" { Show-Usage; exit 0 }
    $RequiredFlag { $ConfirmedFlag = $true }
    default {
      Write-Error "unknown argument: $arg"
    }
  }
}

if (-not $DryRun -and -not $ConfirmedFlag) {
  Show-Usage
  exit 2
}

if (-not (Test-Path "docker-compose.yml")) {
  Write-Error "docker-compose.yml in this folder was not found."
}

function Get-MountVolume([string]$service, [string]$destination) {
  $prev = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
    $ids = @(docker compose ps -aq $service 2>$null | Where-Object { $_.Trim() -ne "" })
    if ($ids.Count -eq 0) { return $null }
    $raw = docker inspect $ids[0] 2>$null
    if (-not $raw) { return $null }
    $info = $raw | ConvertFrom-Json
    foreach ($mount in @($info.Mounts)) {
      if ($mount.Destination -eq $destination) { return [string]$mount.Name }
    }
  } catch {
    return $null
  } finally {
    $ErrorActionPreference = $prev
  }
  return $null
}

function Get-ProjectName {
  $prev = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
    $raw = docker compose config --format json 2>$null
    if ($raw) {
      $cfg = $raw | ConvertFrom-Json
      if ($cfg.name) { return [string]$cfg.name }
    }
  } catch {}
  finally { $ErrorActionPreference = $prev }
  return (Split-Path -Leaf (Get-Location)).ToLowerInvariant()
}

$dockerOk = [bool](Get-Command docker -ErrorAction SilentlyContinue)
$targets = New-Object System.Collections.Generic.List[string]
function Add-Target([string]$name) {
  if (-not $name) { return }
  if (-not $targets.Contains($name)) { $targets.Add($name) }
}

if ($dockerOk) {
  Add-Target (Get-MountVolume "db" "/var/lib/postgresql/data")
  Add-Target (Get-MountVolume "backend" "/var/lib/eytan/vault")
  Add-Target (Get-MountVolume "backend" "/var/lib/eytan/quarantine")
  Add-Target (Get-MountVolume "backend" "/var/lib/eytan/backups")
  $project = Get-ProjectName
  Add-Target "${project}_pgdata"
  Add-Target "${project}_vault"
  Add-Target "${project}_quarantine"
  Add-Target "${project}_backups"
}

$localDirs = @(
  (Join-Path (Get-Location) "data\vault"),
  (Join-Path (Get-Location) "data\quarantine"),
  (Join-Path (Get-Location) "data\backups")
)

Write-Host "This will permanently delete application data on this host:"
Write-Host "  - PostgreSQL volume (users, files metadata, audit logs)"
Write-Host "  - vault files"
Write-Host "  - quarantine"
Write-Host "  - local encrypted backups"
Write-Host "Kept: source, .env, TLS certs, ClamAV DB, live_app, live_frontend, staging, releases."
Write-Host ""
if ($dockerOk) {
  Write-Host "Docker volumes to remove:"
  if ($targets.Count -eq 0) {
    Write-Host "  (none discovered yet; compose names will still be attempted)"
  } else {
    foreach ($vol in $targets) { Write-Host "  - $vol" }
  }
} else {
  Write-Host "Docker is not installed in this environment; compose volumes cannot be removed here."
}
Write-Host "Local directories to empty:"
foreach ($dir in $localDirs) { Write-Host "  - $dir" }
Write-Host "External BACKUP_EXTERNAL_PATH is not touched automatically."

if ($DryRun) {
  Write-Host "dry-run only; nothing deleted."
  exit 0
}

$got = $env:EYTAN_CONFIRM_RESET
if (-not $got) {
  $got = Read-Host "Type $ConfirmationPhrase to continue"
}
if ($got -ne $ConfirmationPhrase) {
  Write-Host "aborted."
  exit 1
}

if ($dockerOk) {
  Write-Host "Stopping stack so data volumes can be removed..."
  docker compose down
  foreach ($vol in $targets) {
    docker volume inspect $vol 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
      Write-Host "Removing volume: $vol"
      docker volume rm -f $vol | Out-Null
    }
  }
} else {
  Write-Host "Docker is missing; compose volumes were not removed."
}

foreach ($dir in $localDirs) {
  New-Item -ItemType Directory -Force -Path $dir | Out-Null
  Get-ChildItem -Force -Path $dir | Remove-Item -Recurse -Force
  Write-Host "Emptied $dir"
}

if (-not $dockerOk) {
  Write-Error "Local folders emptied. Install Docker on the machine that runs the stack and re-run this script there."
}

Write-Host "Starting empty stack..."
docker compose up -d
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

Write-Host "Data wipe complete. Create a new admin with ./scripts/create-admin.sh"
