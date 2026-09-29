$ErrorActionPreference='Stop'
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
$taskInterpreter='C:\Users\gugugaga\miniconda3\envs\softagent\python.exe'
Set-Location -LiteralPath 'D:\softrobot-agent'
$phaseRoot='runs/stage333_bounded_recovery_independent_lengths_20260929_114923'
& $taskInterpreter examples/gvs_stage333.py verify --output $phaseRoot
if ($LASTEXITCODE -ne 0) { throw 'Frozen verification failed' }
& $taskInterpreter examples/gvs_nmpc_route_experiment.py run --output "$phaseRoot/live" --input "$phaseRoot/frozen_input.json" --historical-sources "$phaseRoot/historical_sources.json"
if ($LASTEXITCODE -ne 0) { throw 'Experiment launcher failed; preserve ledger before any continuation' }
