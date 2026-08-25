# Interactive first-admin creation for Windows PowerShell.
# Do not put username or password in this file.
# If PowerShell blocks the file, use:
#   powershell -ExecutionPolicy Bypass -File .\scripts\create-admin.ps1
#   .\scripts\create-admin.cmd
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

Write-Host "This file must not be edited. Type answers at the prompts."
Write-Host "Username is Latin (example: admin)."
Write-Host "Type the password only at the password prompt; it stays hidden."
Write-Host "Password: at least 12 characters, upper, lower, digit, and a special character."
Write-Host ""

if (-not (Test-Path "docker-compose.yml")) {
  Write-Error "docker-compose.yml was not found. Run this from the project folder."
}
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
  Write-Error "Docker was not found. Start Docker Desktop, then run this again."
}

function Read-Secret([string]$Prompt) {
  $secure = Read-Host $Prompt -AsSecureString
  $bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
  try {
    return [System.Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
  } finally {
    [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) | Out-Null
  }
}

$Username = (Read-Host "username").Trim()
$FullName = (Read-Host "full name").Trim()
$Email = (Read-Host "email").Trim()
$Password = Read-Secret "password"
$Password2 = Read-Secret "password again"

if (-not $Username -or -not $FullName -or -not $Email -or -not $Password) {
  Write-Error "Username, full name, email, and password are required."
}
if ($Password -cne $Password2) {
  Write-Error "Passwords do not match."
}

$prev = $ErrorActionPreference
$ErrorActionPreference = "Continue"
docker compose ps -q backend 2>$null | Out-Null
$backendRunning = $LASTEXITCODE -eq 0 -and ((docker compose ps -q backend 2>$null | Where-Object { $_.Trim() -ne "" }).Count -gt 0)
$ErrorActionPreference = $prev
if (-not $backendRunning) {
  Write-Error "The backend container is not running. Start Docker Desktop, then: docker compose up -d"
}

Write-Host "Creating admin user..."
$cli = @(
  "compose", "exec", "-T", "backend", "python", "-m", "app.cli", "create-admin",
  "--username", $Username,
  "--full-name", $FullName,
  "--email", $Email,
  "--password", $Password
)
& docker @cli
if ($LASTEXITCODE -ne 0) {
  exit $LASTEXITCODE
}
Write-Host "Admin created. Sign in with that username and password."
