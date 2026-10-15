<## Compile a separately identified test installer; never target the real Vega install.
    It uses the production script/payload, changing only identity/names/destination.
    Generated setup, logs and reports remain in build/installer-validation for audit.
##>
[CmdletBinding()]
param([string]$Compiler = '')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
if (-not $Compiler) { $Compiler = Join-Path $projectRoot 'build\tools\inno\ISCC.exe' }
if (-not (Test-Path -LiteralPath $Compiler)) { throw 'Supply -Compiler pointing to ISCC.exe.' }
$exe = Join-Path $projectRoot 'dist\Vega\Vega.exe'
if (-not (Test-Path -LiteralPath $exe)) { throw 'Build Vega first.' }
$id = [guid]::NewGuid().ToString('N')
$name = "Vega-Validation-$id"
$testRoot = [IO.Path]::GetFullPath((Join-Path $projectRoot "build\installer-validation\$id"))
$install = Join-Path $testRoot 'installed'
$expectedPrefix = [IO.Path]::GetFullPath((Join-Path $projectRoot 'build\installer-validation')) + '\'
if (-not $testRoot.StartsWith($expectedPrefix, [StringComparison]::OrdinalIgnoreCase) -or (Test-Path -LiteralPath $testRoot)) {
    throw 'Unsafe or existing validation destination.'
}
$null = New-Item -ItemType Directory -Path $testRoot
$version = (Get-Item -LiteralPath $exe).VersionInfo.ProductVersion
& $Compiler "/DAppVersion=$version" "/DAppIdentity=ProjectVega.Validation.$id" "/DShortcutName=$name" "/DInstallFolder=$name" "/DSetupName=$name" "/O$testRoot" (Join-Path $projectRoot 'packaging\Vega.iss')
if ($LASTEXITCODE -ne 0) { throw 'Validation setup compile failed.' }
$setup = Join-Path $testRoot "$name.exe"
$desktop = Join-Path ([Environment]::GetFolderPath('Desktop')) "$name.lnk"
$start = Join-Path ([Environment]::GetFolderPath('Programs')) "$name.lnk"
$userSettings = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'ProjectVega\settings.json'
$beforeSettings = if (Test-Path -LiteralPath $userSettings) { (Get-FileHash -LiteralPath $userSettings).Hash } else { '' }

function Invoke-ValidationProcess([string]$File, [string[]]$Arguments) {
    $process = Start-Process -FilePath $File -ArgumentList $Arguments -WindowStyle Hidden -PassThru
    if (-not $process.WaitForExit(45000)) { throw "Validation process timed out: $File (PID $($process.Id))" }
    if ($process.ExitCode -ne 0) { throw "Validation process failed: $File, code $($process.ExitCode)" }
}

foreach ($tasks in @('', 'desktopicon')) {
    $log = Join-Path $testRoot $(if ($tasks) { 'upgrade.log' } else { 'install.log' })
    Invoke-ValidationProcess $setup @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-',
        ('/DIR="' + $install + '"'), ('/TASKS="' + $tasks + '"'), ('/LOG="' + $log + '"'))
    if (-not (Test-Path -LiteralPath (Join-Path $install 'Vega.exe'))) { throw 'Installed executable missing.' }
    if (-not (Test-Path -LiteralPath $start)) { throw 'Start Menu shortcut missing.' }
    if ([bool](Test-Path -LiteralPath $desktop) -ne [bool]$tasks) { throw 'Desktop task result incorrect.' }
    $shell = New-Object -ComObject WScript.Shell
    if ($shell.CreateShortcut($start).TargetPath -ne (Join-Path $install 'Vega.exe')) { throw 'Incorrect shortcut target.' }
}
$report = Join-Path $testRoot 'installed-smoke.json'
$oldPath = $env:PATH
$oldPythonPath = $env:PYTHONPATH
$oldAudio = $env:SDL_AUDIODRIVER
try {
    $env:PATH = "$env:SystemRoot\System32;$env:SystemRoot"
    $env:PYTHONPATH = $null
    $env:SDL_AUDIODRIVER = 'dummy'
    Invoke-ValidationProcess (Join-Path $install 'Vega.exe') @('--smoke-test-report', ('"' + $report + '"'))
} finally {
    $env:PATH = $oldPath
    $env:PYTHONPATH = $oldPythonPath
    $env:SDL_AUDIODRIVER = $oldAudio
}
$smoke = Get-Content -LiteralPath $report -Raw | ConvertFrom-Json
if (-not ($smoke.frozen -and $smoke.gui_initialized -and $smoke.muted -and $smoke.icon_present)) { throw 'Installed startup failed.' }
# This uninstaller belongs to the GUID-scoped destination compiled above.
$uninstaller = [IO.Path]::GetFullPath((Join-Path $install 'unins000.exe'))
if (-not $uninstaller.StartsWith($testRoot + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Unsafe uninstall target.' }
Invoke-ValidationProcess $uninstaller @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', ('/LOG="' + (Join-Path $testRoot 'uninstall.log') + '"'))
if ((Test-Path -LiteralPath (Join-Path $install 'Vega.exe')) -or (Test-Path -LiteralPath $desktop) -or (Test-Path -LiteralPath $start)) {
    throw 'Uninstall left an application file or shortcut.'
}
# Reproduce the pre-Setup developer install, including both existing shortcuts.
# These are disposable fixtures, not the user's actual legacy installation.
$legacyRelative = 'releases\' + ('a' * 64)
$legacyDirectory = Join-Path $install $legacyRelative
$null = New-Item -ItemType Directory -Path $legacyDirectory -Force
$legacyExe = Join-Path $legacyDirectory 'Vega.exe'
Copy-Item -LiteralPath $exe -Destination $legacyExe
@{ Owner = 'ProjectVega.local.v1'; Releases = @(@{ Directory = $legacyRelative; Files = @('Vega.exe') }) } |
    ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $install 'install.json') -Encoding UTF8
foreach ($linkPath in @($start, $desktop)) {
    $link = $shell.CreateShortcut($linkPath)
    $link.TargetPath = $legacyExe
    $link.Save()
}
Invoke-ValidationProcess $setup @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-',
    ('/DIR="' + $install + '"'), '/TASKS=""', ('/LOG="' + (Join-Path $testRoot 'legacy-upgrade.log') + '"'))
foreach ($linkPath in @($start, $desktop)) {
    if ($shell.CreateShortcut($linkPath).TargetPath -ne (Join-Path $install 'Vega.exe')) {
        throw 'Legacy shortcut was not upgraded in place.'
    }
}
if (-not (Test-Path -LiteralPath $legacyExe)) { throw 'Legacy backup was unexpectedly removed.' }
Invoke-ValidationProcess $uninstaller @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART',
    ('/LOG="' + (Join-Path $testRoot 'legacy-uninstall.log') + '"'))
if ((Test-Path -LiteralPath (Join-Path $install 'Vega.exe')) -or (Test-Path -LiteralPath $desktop) -or (Test-Path -LiteralPath $start)) {
    throw 'Legacy-upgrade uninstall left a current app/shortcut.'
}
if (-not (Test-Path -LiteralPath $legacyExe)) { throw 'Uninstall did not preserve the legacy backup.' }
$afterSettings = if (Test-Path -LiteralPath $userSettings) { (Get-FileHash -LiteralPath $userSettings).Hash } else { '' }
if ($beforeSettings -ne $afterSettings) { throw 'Personal settings changed during validation.' }
Write-Host "PASS: fresh install, upgrade, both Desktop choices, standalone startup, legacy in-place migration/shortcut retargeting, uninstall, backup/settings preservation. Evidence: $testRoot"
