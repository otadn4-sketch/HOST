# Temporary public HTTPS URL for the local Docker stack (Windows PowerShell).
# Tries Cloudflare quick tunnel first; if that network is blocked (common when
# api.trycloudflare.com resolves to 10.x), falls back to an SSH tunnel on 443.
# Stop with Ctrl+C. This exposes the live login page; use only briefly.
# If PowerShell blocks the file:
#   powershell -ExecutionPolicy Bypass -File .\scripts\share-internet.ps1
#   .\scripts\share-internet.cmd

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

Write-Host "This publishes the local Eytan stack on a temporary public HTTPS URL."
Write-Host "Anyone with the URL can reach the login page. Stop with Ctrl+C."
Write-Host ""

try {
  Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1/api/health" -TimeoutSec 5 -MaximumRedirection 0 | Out-Null
  Write-Host "Origin HTTP health is OK."
} catch {
  Write-Host "Warning: http://127.0.0.1/api/health did not return 200."
  Write-Host "The tunnel will still start. If the public page fails, run: docker compose up -d nginx"
}

function Test-CloudflareReachable {
  try {
    $addrs = [System.Net.Dns]::GetHostAddresses("api.trycloudflare.com")
    foreach ($addr in $addrs) {
      $ip = $addr.IPAddressToString
      if ($ip.StartsWith("10.") -or $ip.StartsWith("127.")) {
        Write-Host "Cloudflare DNS is hijacked ($ip). Quick tunnel will not work on this network."
        return $false
      }
    }
  } catch {
    Write-Host "Could not resolve api.trycloudflare.com."
    return $false
  }
  return $true
}

function Start-SshFallback {
  Write-Host ""
  Write-Host "Starting SSH tunnel on port 443 (Pinggy). A public URL will be printed."
  Write-Host "If Windows asks about OpenSSH, install 'OpenSSH Client' from Optional Features."
  Write-Host ""
  & ssh -p 443 -o StrictHostKeyChecking=accept-new -o ServerAliveInterval=30 -R0:127.0.0.1:80 a.pinggy.io
}

$useCloudflare = Test-CloudflareReachable
if ($useCloudflare) {
  $dir = Join-Path $env:LOCALAPPDATA "eytan-tools"
  New-Item -ItemType Directory -Force -Path $dir | Out-Null
  $exe = Join-Path $dir "cloudflared.exe"
  if (-not (Test-Path $exe)) {
    Write-Host "Downloading cloudflared (Cloudflare quick tunnel)..."
    Invoke-WebRequest -Uri "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe" -OutFile $exe
  }
  Write-Host "Starting Cloudflare tunnel..."
  Write-Host ""
  $ErrorActionPreference = "Continue"
  & $exe tunnel --url http://127.0.0.1:80 --no-autoupdate
  $cfExit = $LASTEXITCODE
  $ErrorActionPreference = "Stop"
  if ($cfExit -eq 0) { exit 0 }
  Write-Host ""
  Write-Host "Cloudflare tunnel failed. Falling back to SSH..."
}

Start-SshFallback
