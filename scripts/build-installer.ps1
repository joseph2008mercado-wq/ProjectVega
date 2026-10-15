[CmdletBinding()]
param([string]$Compiler = '')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$exe = Join-Path $projectRoot 'dist\Vega\Vega.exe'
foreach ($required in @($exe, (Join-Path $projectRoot 'dist\Vega\LICENSE'),
    (Join-Path $projectRoot 'dist\Vega\THIRD_PARTY_NOTICES.md'),
    (Join-Path $projectRoot 'src\vega\app\resources\vega.ico'))) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) { throw "Missing $required. Run scripts\build-windows.ps1 first." }
}
if (-not $Compiler) {
    $command = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    $candidates = @(
        $(if ($command) { $command.Source }),
        (Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe'),
        (Join-Path $projectRoot 'build\tools\inno\ISCC.exe')
    )
    $Compiler = $candidates | Where-Object { $_ -and (Test-Path -LiteralPath $_ -PathType Leaf) } | Select-Object -First 1
}
if (-not $Compiler -or -not (Test-Path -LiteralPath $Compiler -PathType Leaf)) {
    throw 'Inno Setup 6 compiler not found. Install it from https://jrsoftware.org/isdl.php or supply -Compiler C:\path\ISCC.exe.'
}
$version = (Get-Item -LiteralPath $exe).VersionInfo.ProductVersion
if ($version -notmatch '^\d+\.\d+\.\d+$') { throw 'Packaged Vega has invalid version metadata.' }
& (Join-Path $projectRoot '.venv\Scripts\python.exe') (Join-Path $PSScriptRoot 'generate-installer-art.py')
if ($LASTEXITCODE -ne 0) { throw 'Installer artwork generation failed.' }
& $Compiler "/DAppVersion=$version" (Join-Path $projectRoot 'packaging\Vega.iss')
if ($LASTEXITCODE -ne 0) { throw 'Inno Setup compilation failed.' }
Write-Host "Built: $(Join-Path $projectRoot 'dist\installer\Vega-Setup.exe')"
