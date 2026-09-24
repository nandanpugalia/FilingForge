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

function Check-App([bool]$CheckBse = $false) {
  $exe = Join-Path $target 'FilingForge.exe'
  if (!(Test-Path $exe)) { throw "Installed app missing: $exe" }
  $app = Start-Process -FilePath $exe -PassThru
  try {
    $healthy = $false
    $deadline = (Get-Date).AddSeconds(60)
    while ((Get-Date) -lt $deadline) {
      if ($app.HasExited) { throw 'Installed app exited before engine became ready' }
      # Tauri picks a free port, and PyInstaller adds a worker below the sidecar.
      # Only trust listeners owned by descendants of the app we just launched.
      $processes = @(Get-CimInstance Win32_Process)
      $owned = [System.Collections.Generic.HashSet[int]]::new()
      [void]$owned.Add($app.Id)
      do {
        $added = $false
        foreach ($process in $processes) {
          if ($owned.Contains([int]$process.ParentProcessId)) {
            if ($owned.Add([int]$process.ProcessId)) { $added = $true }
          }
        }
      } while ($added)
      $listeners = @(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
        Where-Object { $_.LocalAddress -eq '127.0.0.1' -and $_.LocalPort -ge 8765 -and
          $_.LocalPort -le 8775 -and $owned.Contains([int]$_.OwningProcess) })
      foreach ($listener in $listeners) {
        try {
          $base = "http://127.0.0.1:$($listener.LocalPort)"
          $health = Invoke-RestMethod -Uri "$base/health" -TimeoutSec 1
          if ($health.status -eq 'ok') { $healthy = $true; break }
        } catch { }
      }
      if ($healthy) { break }
      Start-Sleep -Seconds 1
    }
    if (!$healthy) { throw 'Installed app did not start its engine within 60 seconds' }
    Write-Host "Installed app engine healthy: $exe ($base, owned by app PID $($app.Id))"
    if ($CheckBse) {
      $resolved = Invoke-RestMethod -Method Post -Uri "$base/resolve" -ContentType 'application/json' `
        -Body '{"company":"HCC"}' -TimeoutSec 120
      if (@($resolved.candidates | Where-Object { $_.scrip_code -eq '500185' }).Count -eq 0) {
        throw 'Packaged BSE search did not resolve HCC to scrip 500185'
      }
      $request = @{ scrip_code='500185'; ticker='HCC'; years=1; categories=@('results');
        everything=$false; dest=(Join-Path $env:RUNNER_TEMP 'filingforge-bse-preview') } | ConvertTo-Json
      $preview = Invoke-RestMethod -Method Post -Uri "$base/preview" -ContentType 'application/json' `
        -Body $request -TimeoutSec 180
      if ($preview.total -lt 1) { throw 'Packaged BSE preview returned no HCC financial results' }
      Write-Host "Packaged BSE search and preview verified: HCC, $($preview.total) financial results"
    }
  } finally {
    taskkill /PID $app.Id /T /F 2>$null | Out-Null
  }
}

Install-App $PreviousInstaller
$before = (Get-Item (Join-Path $target 'FilingForge.exe')).VersionInfo.ProductVersion
if ([version]$before -ge [version]$ExpectedVersion) {
  throw "Upgrade baseline $before must be older than target $ExpectedVersion"
}
Check-App
Install-App $NewInstaller
$after = (Get-Item (Join-Path $target 'FilingForge.exe')).VersionInfo.ProductVersion
if ($after -ne $ExpectedVersion) { throw "Expected $ExpectedVersion, installed $after" }
Check-App -CheckBse $true
Write-Host "Windows installer upgrade verified: $before -> $after"
