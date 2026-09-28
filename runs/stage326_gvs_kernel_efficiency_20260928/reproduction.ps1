# Run from D:\softrobot-agent. Uses a NEW output folder; six local NLP solves.
# The retained CSE patch must be applied at entry and is restored in finally.
param([string]$Output = ('runs/stage326_reproduce_' + [guid]::NewGuid().ToString('N')))
$ErrorActionPreference = 'Stop'
$softPython = 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe'
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
$stage326 = 'runs/stage326_gvs_kernel_efficiency_20260928'
$selection = 'runs/stage325_tracking_efficiency_20260928/selected_states.json'
if (Test-Path -LiteralPath $Output) { throw 'Use a fresh comparison directory' }
New-Item -ItemType Directory -Path $Output | Out-Null
git apply --check -R "$stage326/numerical_change.patch"
if ($LASTEXITCODE) { throw 'Numerical patch no longer applies cleanly' }
git apply -R "$stage326/numerical_change.patch"
if ($LASTEXITCODE) { throw 'Could not select original graph' }
try {
    & $softPython examples/gvs_update_comparison.py baseline --output $Output --selection $selection --project-saved-state
    if ($LASTEXITCODE) { throw 'Baseline failed' }
    & $softPython "$stage326/kernel_check.py" baseline $Output
    if ($LASTEXITCODE) { throw 'Baseline kernel check failed' }
} finally {
    git apply "$stage326/numerical_change.patch"
    if ($LASTEXITCODE) { throw 'Restore numerical patch before continuing' }
}
& $softPython "$stage326/kernel_check.py" modified $Output
if ($LASTEXITCODE) { throw 'Numerical equivalence failed' }
& $softPython examples/gvs_update_comparison.py modified --output $Output --selection $selection --project-saved-state
if ($LASTEXITCODE) { throw 'Modified comparison failed' }
git apply -R "$stage326/numerical_change.patch"
if ($LASTEXITCODE) { throw 'Could not select original graph for verification' }
try {
    & $softPython examples/gvs_update_comparison.py verify --output $Output --selection $selection
    if ($LASTEXITCODE) { throw 'Independent plan verification failed' }
} finally {
    git apply "$stage326/numerical_change.patch"
    if ($LASTEXITCODE) { throw 'Restore numerical patch before continuing' }
}
# No provider request or backend rollout in this script.
