# Local weekly run. No VPS, no API keys.
# From the project folder:
#   powershell -ExecutionPolicy Bypass -File scripts\run_local.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$LogDir = Join-Path $Root "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$LogFile = Join-Path $LogDir ("{0:yyyy-MM-dd_HH-mm-ss}.log" -f (Get-Date))

& python scripts\monitor.py 2>&1 | Tee-Object -FilePath $LogFile
Write-Host "Log: $LogFile"
