param(
    [Parameter(Mandatory=$true)][string]$Python,
    [string]$Matlab = 'matlab',
    [string]$ReferenceRoot = (Join-Path $env:TEMP 'softrobot-sorosim-24d573a3'),
    [string]$OutputDir = (Join-Path $PSScriptRoot ('evidence\run_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))),
    [switch]$DirectHttps
)
$ErrorActionPreference = 'Stop'
$reference = & (Join-Path $PSScriptRoot 'setup_reference.ps1') -ReferenceRoot $ReferenceRoot -DirectHttps:$DirectHttps
$reference = @($reference)[-1]
$output = [IO.Path]::GetFullPath($OutputDir)
if (Test-Path -LiteralPath $output) { throw 'Choose a new output directory to preserve prior evidence.' }
New-Item -ItemType Directory -Path $output | Out-Null
$started = Get-Date
Push-Location ([IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..')))
try {
    foreach ($case in @('one_segment', 'two_segment')) {
        & $Python (Join-Path $PSScriptRoot 'run_gvs.py') --case $case --output $output
        if ($LASTEXITCODE -ne 0) { throw "GVS failed: $case" }
        $mHere = $PSScriptRoot.Replace('\','/').Replace("'","''")
        $mReference = $reference.Replace('\','/').Replace("'","''")
        $mOutput = $output.Replace('\','/').Replace("'","''")
        $expression = "addpath('$mHere'); sv_run('$mReference','$mOutput','$case');"
        & $Matlab -logfile (Join-Path $output "matlab_$case.log") -batch $expression
        if ($LASTEXITCODE -ne 0) { throw "MATLAB failed: $case" }
        & $Python (Join-Path $PSScriptRoot 'compare.py') --case $case --output $output
        if ($LASTEXITCODE -ne 0) { throw "Validation gate failed: $case" }
    }
    & $Python (Join-Path $PSScriptRoot 'test_validation.py') --evidence $output
    if ($LASTEXITCODE -ne 0) { throw 'Independent invariant checks failed.' }
    & $Python (Join-Path $PSScriptRoot 'provenance.py') --reference $reference --output $output
    if ($LASTEXITCODE -ne 0) { throw 'Provenance capture failed.' }
    @{
        started_at = $started.ToString('o')
        finished_at = (Get-Date).ToString('o')
        elapsed_seconds = ((Get-Date)-$started).TotalSeconds
        evidence_directory = $output
        status = 'passed'
    } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $output 'run_status.json') -Encoding UTF8
} catch {
    @{
        started_at = $started.ToString('o')
        finished_at = (Get-Date).ToString('o')
        elapsed_seconds = ((Get-Date)-$started).TotalSeconds
        status = 'failed'
        error = $_.Exception.Message
    } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $output 'run_status.json') -Encoding UTF8
    throw
} finally { Pop-Location }
