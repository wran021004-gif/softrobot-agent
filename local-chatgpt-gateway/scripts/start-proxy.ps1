$ErrorActionPreference = 'Stop'
# Process-local routing; preserve OAuth/DPAPI state and loopback direct access.
$env:HTTP_PROXY = 'http://127.0.0.1:7890'
$env:HTTPS_PROXY = 'http://127.0.0.1:7890'
$env:NO_PROXY = 'localhost,127.0.0.1,::1'
& node --use-env-proxy (Join-Path $PSScriptRoot '../src/cli.mjs') serve
exit $LASTEXITCODE
