param(
    [Parameter(Mandatory=$true)][string]$Python,
    [string]$Matlab = 'matlab',
    [string]$ReferenceRoot = (Join-Path $env:TEMP 'softrobot-sorosim-24d573a3'),
    [string]$OutputDir = '',
    [switch]$DirectHttps,
    [switch]$V2
)
$ErrorActionPreference = 'Stop'
$reference = & (Join-Path $PSScriptRoot 'setup_reference.ps1') -ReferenceRoot $ReferenceRoot -DirectHttps:$DirectHttps
$reference = @($reference)[-1]
if (-not $OutputDir) {
    $prefix = if ($V2) { 'run_v2_' } else { 'run_' }
    $OutputDir = Join-Path $PSScriptRoot ('evidence\' + $prefix + (Get-Date -Format 'yyyyMMdd_HHmmss'))
}
$output = [IO.Path]::GetFullPath($OutputDir)
if (Test-Path -LiteralPath $output) { throw 'Choose a new output directory to preserve prior evidence.' }
New-Item -ItemType Directory -Path $output | Out-Null
$started = Get-Date
$versionArgs = @()
if ($V2) { $versionArgs = @('--v2') }
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'cases.json') -Destination (Join-Path $output 'cases_snapshot.json')
Push-Location ([IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..')))
try {
    foreach ($case in @('one_segment', 'two_segment')) {
        & $Python (Join-Path $PSScriptRoot 'run_gvs.py') --case $case --output $output @versionArgs
        if ($LASTEXITCODE -ne 0) { throw "GVS failed: $case" }
        $mHere = $PSScriptRoot.Replace('\','/').Replace("'","''")
        $mReference = $reference.Replace('\','/').Replace("'","''")
        $mOutput = $output.Replace('\','/').Replace("'","''")
        $matlabVersionArg = if ($V2) { ',2' } else { '' }
        $expression = "addpath('$mHere'); sv_run('$mReference','$mOutput','$case'$matlabVersionArg);"
        $matlabStarted = Get-Date
        & $Matlab -logfile (Join-Path $output "matlab_$case.log") -batch $expression
        if ($LASTEXITCODE -ne 0) { throw "MATLAB failed: $case" }
        @{process_seconds=((Get-Date)-$matlabStarted).TotalSeconds; started_at=$matlabStarted.ToUniversalTime().ToString('o')} | ConvertTo-Json |
            Set-Content -LiteralPath (Join-Path $output "matlab_process_$case.json") -Encoding UTF8
        & $Python (Join-Path $PSScriptRoot 'compare.py') --case $case --output $output @versionArgs
        if ($LASTEXITCODE -ne 0) { throw "Validation gate failed: $case" }
    }
    & $Python (Join-Path $PSScriptRoot 'test_validation.py') --evidence $output @versionArgs
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
