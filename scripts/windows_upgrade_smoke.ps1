param(
  [Parameter(Mandatory=$true)][string]$PreviousInstaller,
  [Parameter(Mandatory=$true)][string]$NewInstaller,
  [Parameter(Mandatory=$true)][string]$ExpectedVersion
)
$ErrorActionPreference = 'Stop'
$target = Join-Path $env:RUNNER_TEMP 'filingforge-upgrade-smoke'

function Install-App([string]$Installer) {
  $process = Start-Process -FilePath $Installer -ArgumentList @('/S', "/D=$target") -Wait -PassThru
  if ($process.ExitCode -ne 0) { throw "Installer exited $($process.ExitCode)" }
}

function Check-App {
  $exe = Join-Path $target 'FilingForge.exe'
  if (!(Test-Path $exe)) { throw "Installed app missing: $exe" }
  $app = Start-Process -FilePath $exe -PassThru
  try {
    $healthy = $false
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
      if ($app.HasExited) { throw 'Installed app exited before engine became ready' }
      try {
        $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8765/health' -TimeoutSec 1
        if ($health.status -eq 'ok') { $healthy = $true; break }
      } catch { }
      Start-Sleep -Seconds 1
    }
    if (!$healthy) { throw 'Installed app did not start its engine within 60 seconds' }
    Write-Host "Installed app engine healthy: $exe"
  } finally {
    taskkill /PID $app.Id /T /F 2>$null | Out-Null
  }
}

Install-App $PreviousInstaller
Check-App
$before = (Get-Item (Join-Path $target 'FilingForge.exe')).VersionInfo.ProductVersion
Install-App $NewInstaller
$after = (Get-Item (Join-Path $target 'FilingForge.exe')).VersionInfo.ProductVersion
if ($after -ne $ExpectedVersion) { throw "Expected $ExpectedVersion, installed $after" }
Check-App
Write-Host "Windows installer upgrade verified: $before -> $after"
