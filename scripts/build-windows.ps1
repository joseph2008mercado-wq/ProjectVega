[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
if ($env:OS -ne 'Windows_NT') { throw 'Build Vega on Windows.' }
if (-not (Test-Path -LiteralPath $python)) { throw 'Create the Python 3.13 .venv first; see README.' }
& $python -c 'import sys; assert sys.version_info[:2] == (3, 13), "Python 3.13 required"; import PyInstaller, PySide6, pygame'
if ($LASTEXITCODE -ne 0) { throw 'Install build dependencies: .\.venv\Scripts\python.exe -m pip install -e ".[desktop,packaging]"' }
& $python (Join-Path $PSScriptRoot 'generate-icon.py')
if ($LASTEXITCODE -ne 0) { throw 'Icon generation failed.' }
# These are generated build directories, never an inferred source/workspace root.
$dist = Join-Path $projectRoot 'dist'
$work = Join-Path $projectRoot 'build\pyinstaller'
foreach ($target in @($dist, $work, (Join-Path $dist 'Vega'))) {
    if ((Test-Path -LiteralPath $target) -and ((Get-Item -LiteralPath $target).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw "Refusing a redirected build directory: $target"
    }
}
# Developer tools can put incompatible ICU/Qt DLLs on PATH. Build with only
# Windows and this interpreter on PATH, then restore the caller's environment.
$originalPath = $env:PATH
$originalPythonPath = $env:PYTHONPATH
try {
    $env:PATH = "$env:SystemRoot\System32;$env:SystemRoot;$(Split-Path -Parent $python)"
    $env:PYTHONPATH = $null
    & $python -m PyInstaller --noconfirm --distpath $dist --workpath $work (Join-Path $projectRoot 'packaging\Vega.spec')
    if ($LASTEXITCODE -ne 0) { throw 'Vega build failed; see PyInstaller output above.' }
} finally {
    $env:PATH = $originalPath
    $env:PYTHONPATH = $originalPythonPath
}
$exe = Join-Path $dist 'Vega\Vega.exe'
if (-not (Test-Path -LiteralPath $exe)) { throw "Build did not produce $exe" }
& $python (Join-Path $PSScriptRoot 'collect-licenses.py')
if ($LASTEXITCODE -ne 0) { throw 'License collection failed; do not distribute the incomplete build.' }
Write-Host "Built: $exe"
