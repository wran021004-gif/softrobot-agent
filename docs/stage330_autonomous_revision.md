# Stage 3.30: autonomous design revision from supplied historical failure evidence

The Stage 3.29 failed live execution is a supplied prior case, not a new-session
execution. `historical_failure.bind_failure` reads that case's sealed artifacts,
checks original ownership and unchanged scientific conditions, and saves only a
small immutable record in the new store. It does not import old sessions or their
provider conclusions. Historical source hashes may differ from reporting code.

`delivery_facts.bound_result_facts` dispatches to tracking or free-reach facts.
Reach context, comparison, diagnosis, delivery validation and Markdown exports use
the same projection. Signed errors are measured world tip minus target. Missing
measurements are not inferred. Pre-multiphysics legacy reports without the required
fields retain their old view. Tracking retains its existing contract. Structured
agreement is not a prose audit; finish mismatches produce normal tool feedback.

`examples/gvs_revision_input.py` derives the Stage 3.30 input from the original
frozen baseline and changes only the assignment and resource limits. Use the
existing launcher to prepare and run:

```powershell
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
$py='C:\Users\gugugaga\miniconda3\envs\softagent\python.exe'
$old='runs/stage329_multiphysics_design_20260928_202221'
$new='runs/stage330_autonomous_design_revision_<timestamp>'
& $py examples/gvs_revision_input.py --source $old --output "$new/frozen_input.json"
& $py examples/gvs_nmpc_route_experiment.py prepare --output "$new/live" --input "$new/frozen_input.json" --historical-failure $old
& $py examples/gvs_nmpc_route_experiment.py run --output "$new/live" --input "$new/frozen_input.json" --historical-failure $old
```

Freeze implementation before preparation. The original launcher, credential loader,
DeepSeek adapter and transport are reused. The provider chooses each design and
receives comparisons automatically. No additional model loop or optimization solve
was added. Current evaluated-candidate count and remaining backend attempts are
explicit context fields; the prior execution does not increment them.

Focused checks: three `test_stage330_revision` tests; Stage 3.25 tracking shared-fact
compatibility; Stage 3.23 retained-evidence/context check; Stage 3.29 saved one-step
alignment. These use saved evidence and fresh empty stores, with no paid requests
or backend executions. Windows test directories use normal inherited permissions
and collect closed SQLite handles before cleanup.

Keep the experiment's four acceptance outcomes separate: integration, autonomous
revision plus evaluation, covered original-task success, and structured/prose
accuracy. Preserve the original provider explanation even when its audit fails.
