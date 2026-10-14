# Read-only boundary tests plus a small, disposable ownership marker fixture.
. (Join-Path (Split-Path -Parent $PSScriptRoot) 'scripts\local-common.ps1')
$fixture = Join-Path ([IO.Path]::GetTempPath()) ('vega-helper-test-' + [guid]::NewGuid().ToString('N'))
$null = New-Item -ItemType Directory -Path $fixture
try {
    $child = Get-VegaChild $fixture 'releases\example\Vega.exe'
    if (-not $child.StartsWith($fixture + '\')) { throw 'Valid child path was not resolved.' }
    $rejected = $false
    try { Get-VegaChild $fixture '..\outside.exe' | Out-Null } catch { $rejected = $true }
    if (-not $rejected) { throw 'Parent traversal was accepted.' }
    if ($null -ne (Read-VegaInstall $fixture)) { throw 'Empty fixture should not be installed.' }
    Set-Content -LiteralPath (Join-Path $fixture 'unrelated.txt') -Value 'preserve'
    $rejected = $false
    try { Read-VegaInstall $fixture | Out-Null } catch { $rejected = $true }
    if (-not $rejected) { throw 'Unmanaged directory was accepted.' }
    @{ Owner = $VegaOwner; Releases = @() } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $fixture 'install.json')
    if ((Read-VegaInstall $fixture).Owner -ne $VegaOwner) { throw 'Ownership was not recognized.' }
    Write-Host 'Local-install path and ownership checks passed.'
} finally {
    # Exact files created above; never recursively delete a computed temp root.
    foreach ($name in @('unrelated.txt', 'install.json')) {
        $path = Get-VegaChild $fixture $name
        if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path }
    }
    Remove-Item -LiteralPath $fixture
}
