param(
    [string]$ReferenceRoot = (Join-Path $env:TEMP 'softrobot-sorosim-24d573a3'),
    [switch]$DirectHttps
)
$ErrorActionPreference = 'Stop'
$cfg = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'cases.json') -Raw | ConvertFrom-Json
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$reference = [IO.Path]::GetFullPath($ReferenceRoot)
if ($reference.Equals($repo, [StringComparison]::OrdinalIgnoreCase) -or
    $reference.StartsWith($repo + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'The upstream checkout must be outside this repository.'
}
$gitOptions = @('-c', 'http.sslBackend=openssl')
if ($DirectHttps) { $gitOptions += @('-c', 'http.proxy=') }
if (-not (Test-Path -LiteralPath $reference)) {
    & git @gitOptions clone --no-checkout --depth 1 https://github.com/GVSRobotics/SoRoSim.git $reference
    if ($LASTEXITCODE -ne 0) { throw 'Reference clone failed.' }
    & git -C $reference cat-file -e ($cfg.upstream_sha + '^{commit}') 2>$null
    if ($LASTEXITCODE -ne 0) {
        & git @gitOptions -C $reference fetch --depth 1 origin $cfg.upstream_sha
        if ($LASTEXITCODE -ne 0) { throw 'Pinned revision fetch failed.' }
    }
    & git -C $reference checkout --detach $cfg.upstream_sha
    if ($LASTEXITCODE -ne 0) { throw 'Pinned checkout failed.' }
}
$actual = & git -C $reference rev-parse HEAD
if ($LASTEXITCODE -ne 0 -or $actual -ne $cfg.upstream_sha) {
    throw 'Existing reference is not at the pinned revision; select a new external directory.'
}
$remote = & git -C $reference remote get-url origin
if ($remote -ne 'https://github.com/GVSRobotics/SoRoSim.git') { throw 'Unexpected reference remote.' }
$dirty = & git -C $reference status --porcelain
if ($dirty) { throw 'Reference checkout is dirty; preserve it and select a clean external checkout.' }
Write-Output $reference
