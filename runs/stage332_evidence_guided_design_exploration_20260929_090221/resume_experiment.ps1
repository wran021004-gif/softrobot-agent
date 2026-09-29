# Reuse the frozen replacement after direct DeepSeek transfer authorization.
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
$taskInterpreter='C:\Users\gugugaga\miniconda3\envs\softagent\python.exe'
Set-Location -LiteralPath 'D:\softrobot-agent'
& $taskInterpreter examples/gvs_nmpc_route_experiment.py run --output runs/stage332_evidence_guided_design_exploration_20260929_090221/live_network --input runs/stage332_evidence_guided_design_exploration_20260929_090221/replacement_input.json --historical-failure runs/stage331_autonomous_revision_execution_20260929_014645 --historical-candidate rev_compliant_max --historical-candidate c2_stiff_scale1p01 --historical-candidate c3_compliant_scale1p02
