[CmdletBinding()]
param([switch]$Build)
. (Join-Path $PSScriptRoot 'local-common.ps1')
$projectRoot = Split-Path -Parent $PSScriptRoot
if ($Build) { & (Join-Path $PSScriptRoot 'build-windows.ps1') }
$source = Join-Path $projectRoot 'dist\Vega'
$exe = Join-Path $source 'Vega.exe'
if (-not (Test-Path -LiteralPath $exe)) { throw 'Build first with .\scripts\build-windows.ps1, or pass -Build.' }
Assert-VegaDirectory $source
$installRoot = Get-VegaInstallRoot
$previous = Read-VegaInstall $installRoot
Assert-VegaStopped $installRoot
$shell = New-Object -ComObject WScript.Shell
$shortcuts = @(Get-VegaShortcutPaths)
foreach ($link in $shortcuts) {
    if (Test-Path -LiteralPath $link) {
        $existingTarget = $shell.CreateShortcut($link).TargetPath
        if (-not $existingTarget.StartsWith($installRoot + '\', [StringComparison]::OrdinalIgnoreCase)) {
            throw "A shortcut named Vega already belongs to another app: $link"
        }
    }
}
# A new directory per build prevents mixing old DLLs with a new build.
$buildId = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLowerInvariant()
$relativeRelease = 'releases\' + $buildId
$release = Get-VegaChild $installRoot $relativeRelease
if (Test-Path -LiteralPath $release) { throw 'This build is already installed. Uninstall first to reinstall the same build.' }
$files = @(Get-ChildItem -LiteralPath $source -Recurse -File | ForEach-Object {
    $_.FullName.Substring($source.Length).TrimStart('\')
})
$null = New-Item -ItemType Directory -Path (Join-Path $installRoot 'releases') -Force
Copy-Item -LiteralPath $source -Destination $release -Recurse
$releases = @()
if ($previous) { $releases += @($previous.Releases) }
$releases += [PSCustomObject]@{ Directory = $relativeRelease; Files = $files }
$info = [PSCustomObject]@{ Owner = $VegaOwner; Releases = $releases }
$info | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $installRoot 'install.json') -Encoding UTF8
$target = Join-Path $release 'Vega.exe'
foreach ($link in $shortcuts) {
    $null = New-Item -ItemType Directory -Path (Split-Path -Parent $link) -Force
    $shortcut = $shell.CreateShortcut($link)
    $shortcut.TargetPath = $target
    $shortcut.WorkingDirectory = $release
    $shortcut.IconLocation = "$target,0"
    $shortcut.Description = 'Project Vega Guitar Control Panel'
    $shortcut.Save()
}
Write-Host "Installed: $target"
Write-Host 'Created Vega shortcuts on the desktop and in the Start Menu. Settings were preserved.'
