# Shared path/ownership checks for the per-user installer. No admin changes.
$ErrorActionPreference = 'Stop'
$VegaOwner = 'ProjectVega.local.v1'

function Get-VegaInstallRoot {
    return Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'Programs\Vega'
}

function Get-VegaChild([string]$Root, [string]$Relative) {
    $base = [IO.Path]::GetFullPath($Root).TrimEnd('\') + '\'
    $child = [IO.Path]::GetFullPath((Join-Path $Root $Relative))
    if (-not $child.StartsWith($base, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Path is outside the Vega installation: $child"
    }
    return $child
}

function Assert-VegaDirectory([string]$Path) {
    # Reject junctions/symlinks in the root, its parents, and existing children.
    $cursor = [IO.Path]::GetFullPath($Path)
    while ($cursor) {
        if ((Test-Path -LiteralPath $cursor) -and ((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
            throw "Refusing redirected installation path: $cursor"
        }
        $cursor = Split-Path -Parent $cursor
    }
    if (Test-Path -LiteralPath $Path) {
        $redirected = Get-ChildItem -LiteralPath $Path -Recurse -Force | Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint }
        if ($redirected) { throw "Redirected files found inside $Path" }
    }
}

function Read-VegaInstall([string]$Root) {
    Assert-VegaDirectory $Root
    $marker = Join-Path $Root 'install.json'
    if (-not (Test-Path -LiteralPath $marker)) {
        if ((Test-Path -LiteralPath $Root) -and (Get-ChildItem -LiteralPath $Root -Force)) {
            throw "Directory is not a managed Vega installation: $Root"
        }
        return $null
    }
    $info = Get-Content -LiteralPath $marker -Raw | ConvertFrom-Json
    if ($info.Owner -ne $VegaOwner) { throw 'Unrecognized installation marker.' }
    return $info
}

function Assert-VegaStopped([string]$Root) {
    $prefix = [IO.Path]::GetFullPath($Root).TrimEnd('\') + '\'
    foreach ($process in @(Get-Process -Name Vega -ErrorAction SilentlyContinue)) {
        if ($process.Path -and $process.Path.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
            throw 'Close the installed Vega application before updating or uninstalling.'
        }
    }
}

function Get-VegaShortcutPaths {
    return @(
        (Join-Path ([Environment]::GetFolderPath('DesktopDirectory')) 'Vega.lnk'),
        (Join-Path ([Environment]::GetFolderPath('Programs')) 'Vega.lnk')
    )
}
