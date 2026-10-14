[CmdletBinding()]
param()
. (Join-Path $PSScriptRoot 'local-common.ps1')
$installRoot = Get-VegaInstallRoot
$info = Read-VegaInstall $installRoot
if (-not $info) { Write-Host 'No managed Vega installation found.'; return }
Assert-VegaStopped $installRoot
# Validate every target before deleting anything. Never recursively erase the
# install root: the manifest lists only the files this installer copied.
$targets = @()
$releases = @()
foreach ($entry in @($info.Releases)) {
    if ($entry.Directory -notmatch '^releases\\[a-f0-9]{64}$') { throw 'Invalid release directory in manifest.' }
    $release = Get-VegaChild $installRoot $entry.Directory
    $releases += $release
    foreach ($file in @($entry.Files)) { $targets += Get-VegaChild $release $file }
}
$shell = New-Object -ComObject WScript.Shell
foreach ($link in @(Get-VegaShortcutPaths)) {
    if (Test-Path -LiteralPath $link) {
        $target = $shell.CreateShortcut($link).TargetPath
        if ($target.StartsWith($installRoot + '\', [StringComparison]::OrdinalIgnoreCase)) {
            Remove-Item -LiteralPath $link
        }
    }
}
foreach ($target in $targets) {
    if (Test-Path -LiteralPath $target -PathType Leaf) { Remove-Item -LiteralPath $target -Force }
}
# Only empty directories are removed; unexpected user files are preserved.
foreach ($release in $releases) {
    if (Test-Path -LiteralPath $release) {
        $directories = @(Get-ChildItem -LiteralPath $release -Directory -Recurse | Sort-Object { $_.FullName.Length } -Descending)
        foreach ($directory in $directories) {
            if (-not (Get-ChildItem -LiteralPath $directory.FullName -Force)) { Remove-Item -LiteralPath $directory.FullName }
        }
        if (-not (Get-ChildItem -LiteralPath $release -Force)) { Remove-Item -LiteralPath $release }
    }
}
Remove-Item -LiteralPath (Join-Path $installRoot 'install.json')
$releaseRoot = Get-VegaChild $installRoot 'releases'
if ((Test-Path -LiteralPath $releaseRoot) -and -not (Get-ChildItem -LiteralPath $releaseRoot -Force)) { Remove-Item -LiteralPath $releaseRoot }
if (-not (Get-ChildItem -LiteralPath $installRoot -Force)) { Remove-Item -LiteralPath $installRoot }
Write-Host 'Removed Vega installed files and matching shortcuts. User settings and any unlisted files were preserved.'
