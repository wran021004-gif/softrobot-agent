# Real-provider GVS profile use through Route

Route `build` stays solve-free. A controller may declare a scoped
`route_report_tool`; the child receives that tool only if the parent grants it.
After `single-simulation` and `single-evaluation`, the child invokes
`single-profile-report` with `route-executor` attribution. The parent receives
the report reference, owning run and simulation identity, and a compact summary.
Inspection, incumbent selection and explicit delivery retain those fields.
Repeating a sealed request, or running the same immutable build again, reuses
the original child receipts, including reporting.

Profile options in Route context come from authorized controller combinations
and their applicability hooks. Discovery/report authorization is explicit.
The GVS predictor remains distinct from the serial-cell MuJoCo execution model.
The report needs no strategy declaration: it summarizes an execution whether
or not that execution is used for later skill validation.

The dedicated example accepts an explicit public SessionInput with `--input`
(target, initialization, timing and controller recipe), or defaults to the fixed
profile. It uses the existing Host/DeepSeek tool loop and loads only
`DEEPSEEK_API_KEY` as data from the local
credential file (or reuses the process environment). Provider configuration
comes from `configs/deepseek.yaml`; the example uses its 16,384-token limit,
24 maximum model calls, 60 tool calls including children, one backend execution,
and a new 3,600-second project/session grant by default (`--wall-s`). The supplied
task/recipe is frozen before model calls; a changed `--input` on resume is rejected.
Route discovery exposes its declared combination for the model to select.

For the default fixed profile, historical skill revisions and content-addressed evidence are imported as
source-preserving read-only data. Historical snapshots/events live in evidence
artifacts, with their original identities; they are not new session rows,
receipts or authorization. No grant or call ledger is imported. The existing
skill validator reads these explicit historical sources. This does not grant
human approval or validate transfer to another task. The new model receives
the applicable validated development skill automatically in normal context.
Parameterized inputs use their own capability scope assessment; the example
does not import the fixed-profile skill as validation of those changed inputs.

```powershell
Set-Location 'D:\softrobot-agent'
$py = 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe'
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
$out = 'runs/gvs_route_live_reproduction'
& $py examples/gvs_nmpc_route_experiment.py prepare --output $out
& $py examples/gvs_nmpc_route_experiment.py run --output $out
& $py examples/gvs_nmpc_route_experiment.py inspect --output $out
# Parameterized task: supply the same frozen input at prepare/run, in a new folder.
# & $py examples/gvs_nmpc_route_experiment.py run --input runs/my_reach_input.json --output runs/my_live_reach
```

Use a new output directory for a new authorized experiment. `inspect` is
read-only and makes no provider or backend requests. A finished Route is not
rerun by `run`. Do not change dependency-tracked code during an active run.
The Store preserves submitted contexts, raw provider responses, decoded tool
requests, internal child calls, sealed exports, and final provider-authored
Route reason. `behavior_audit.json` indexes observable actions and evidence;
it does not analyze or request hidden reasoning. `summary.json` and `report.md`
derive from the new child execution.

Official reach, sampled settling, feasible plan acceptance, optimizer
convergence and computational deadlines remain separate conclusions.
