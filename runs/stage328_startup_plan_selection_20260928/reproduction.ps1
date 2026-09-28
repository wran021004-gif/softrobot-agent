# Run explicitly to reproduce local experiments in a new evidence directory.
# No rollout or provider request is performed. Historical outputs are never reused.
$ErrorActionPreference = 'Stop'
Set-Location 'D:\softrobot-agent'
$softPython = 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe'
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
$archive = 'runs/stage328_startup_plan_selection_20260928'
$out = 'runs/stage328_reproduction_' + (Get-Date -Format 'yyyyMMdd_HHmmss')
if (Test-Path -LiteralPath $out) { throw 'Fresh output required' }
git diff --quiet
if ($LASTEXITCODE -ne 0) { throw 'Tracked edits present; preserve them before reproduction' }
New-Item -ItemType Directory -Path $out | Out-Null
foreach ($file in @('startup_analysis.py','local_compare.py','decide_local.py','verify_saved_plans.py','local_rule.json')) {
    Copy-Item -LiteralPath (Join-Path $archive $file) -Destination (Join-Path $out $file)
}
& $softPython "$out/startup_analysis.py" freeze
if ($LASTEXITCODE -ne 0) { throw 'Freeze failed' }
& $softPython "$out/startup_analysis.py" diagnostic
if ($LASTEXITCODE -ne 0) { throw 'Diagnostic failed; do not repeat' }
git apply "$archive/withdrawn_selection.patch"
if ($LASTEXITCODE -ne 0) { throw 'Patch did not apply' }
try {
    & $softPython -m unittest discover -s $archive -p test_withdrawn_selection.py -v
    if ($LASTEXITCODE -ne 0) { throw 'Focused checks failed' }
    & $softPython "$out/local_compare.py" baseline
    if ($LASTEXITCODE -ne 0) { throw 'Baseline failed; do not repeat' }
    & $softPython "$out/local_compare.py" revised
    if ($LASTEXITCODE -ne 0) { throw 'Revised failed; do not repeat' }
    & $softPython "$out/decide_local.py"
    if ($LASTEXITCODE -ne 0) { throw 'Local audit failed' }
} finally {
    git apply -R "$archive/withdrawn_selection.patch"
    if ($LASTEXITCODE -ne 0) { throw 'Manual restoration required; retain all evidence' }
}
& $softPython "$out/verify_saved_plans.py"
# Wall-time stopping can yield different plans. This script never authorizes a
# rollout/provider session from a fresh result. The historical local gate failed.
