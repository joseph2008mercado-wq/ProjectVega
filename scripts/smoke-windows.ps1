[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$exe = Join-Path $projectRoot 'dist\Vega\Vega.exe'
if (-not (Test-Path -LiteralPath $exe)) { throw 'Build Vega first.' }
$bytes = [IO.File]::ReadAllBytes($exe)
$peOffset = [BitConverter]::ToInt32($bytes, 0x3c)
$subsystem = [BitConverter]::ToUInt16($bytes, $peOffset + 24 + 68)
if ($subsystem -ne 2) { throw 'Executable is not a Windows GUI application.' }
if ((Get-Item -LiteralPath $exe).VersionInfo.ProductName -ne 'Vega') { throw 'Product metadata is missing.' }
$report = Join-Path $projectRoot ('build\smoke-' + [guid]::NewGuid().ToString('N') + '.json')
$null = New-Item -ItemType Directory -Path (Split-Path -Parent $report) -Force
$process = Start-Process -FilePath $exe -ArgumentList @('--smoke-test-report', ('"' + $report + '"')) -WorkingDirectory (Split-Path -Parent $exe) -WindowStyle Hidden -PassThru
if (-not $process.WaitForExit(20000)) {
    Stop-Process -Id $process.Id
    throw 'Vega smoke check timed out; the diagnostic process was stopped.'
}
if (-not (Test-Path -LiteralPath $report)) { throw "Vega failed to write its smoke report: $report" }
$result = Get-Content -LiteralPath $report -Raw | ConvertFrom-Json
if ($process.ExitCode -ne 0 -or $result.error) { throw "Vega startup failed: $($result.error). Report: $report" }
if (-not ($result.frozen -and $result.gui_initialized -and $result.icon_present -and $result.muted) -or $result.console_attached) {
    throw "Packaged startup check failed. Inspect $report"
}
$result | Format-List
Write-Host "Packaged startup passed. Report: $report"
