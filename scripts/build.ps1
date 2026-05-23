Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

pyinstaller MonitorReminder.spec --noconfirm --distpath . --workpath build