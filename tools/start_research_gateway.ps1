param(
    [Parameter(Mandatory = $true)]
    [string]$GatewayRoot,
    [ValidateRange(1, 65535)]
    [int]$ProxyPort = 7890
)

$ErrorActionPreference = 'Stop'
$entry = Join-Path (Resolve-Path -LiteralPath $GatewayRoot).Path 'src\cli.mjs'
if (-not (Test-Path -LiteralPath $entry -PathType Leaf)) {
    throw 'Existing Gateway src/cli.mjs is required.'
}

# Process-local settings; no global proxy, credentials or account changes.
$names = @('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'NO_PROXY', 'NODE_USE_ENV_PROXY')
$previous = @{}
foreach ($name in $names) { $previous[$name] = [Environment]::GetEnvironmentVariable($name, 'Process') }
try {
    $env:HTTP_PROXY = "http://127.0.0.1:$ProxyPort"
    $env:HTTPS_PROXY = $env:HTTP_PROXY
    $env:ALL_PROXY = $env:HTTP_PROXY
    $env:NO_PROXY = 'localhost,127.0.0.1,::1'
    $env:NODE_USE_ENV_PROXY = '1'
    & node --use-env-proxy $entry serve
    if ($LASTEXITCODE -ne 0) { throw "Gateway exited with code $LASTEXITCODE" }
} finally {
    foreach ($name in $names) { [Environment]::SetEnvironmentVariable($name, $previous[$name], 'Process') }
}
