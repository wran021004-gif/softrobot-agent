# Current research chain

Run from the isolated repository root with the existing research interpreter; the RL bridge retains its separate `D:/softrobot-agent/.rl-pilot-env/Scripts/python.exe`. No environment rebuild is needed. Preserve the bridge's Windows system environment inheritance. The new stopping/failure-feedback assignment uses `examples/research_chain/feedback_design_study.json`; the earlier `specification.json` study remains sealed.

```powershell
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
$researchPython='D:/softrobot-agent/.mainline5-env/Scripts/python.exe'
& $researchPython -m tools.research.core prepare --spec examples/research_chain/specification.json
# Commit scoped implementation/configuration before binding or scientific dispatch.
& $researchPython -m tools.research.core bind --spec examples/research_chain/specification.json
& $researchPython -m tools.research.core live --spec examples/research_chain/specification.json
& $researchPython -m tools.research.core status --spec examples/research_chain/specification.json
& $researchPython -m tools.research.core recover --spec examples/research_chain/specification.json
& $researchPython -m tools.research.core export --spec examples/research_chain/specification.json
```

`core` owns native Strands conversation, admission, waiting, STOP and the existing Host/Store. `design` constructs immutable candidates and invokes the existing `tools/design_optimization.py`. `analysis` owns candidate-bound mathematics, artifacts and settlement. `mechanics` owns the explicit legacy offline adapter and exact solved-configuration handoff. `rl` binds canonical configurations to the existing training machinery. `feedback` reports facts and confirmation eligibility; workers retain process containment. `diagnostic`, `numerics` and `experience` retain saved-state checks and evidence access. Historical demo/delivery scripts remain callers of the moved implementation; old entry modules are removed.

The single complete nominal source is `examples/research_chain/nominal.json`, resolved from the latest contained chain's initial candidate, with archive reference and SHA. Zero parameter changes preserve its robot geometry, mass, stiffness, routes, task and mesh. Candidate identity also freezes controller, model, input order, initialization, timing, source and evaluation profile. Analysis, NMPC and RL consume the saved candidate configuration. Builds always start from the immutable source.

Active topology is two flexible segments `near/distal1`, six independent ideal tensions 0..8N. Lengths can vary independently within source-relative ?5% (.152..168 and .1045..1155m), or use declared fixed-total allocation; optional aggregate bounds are checked directly. Each segment has section scale .95..1.05, material scenario baseline/compliant/stiff (modulus1/.9/1.1), and routing scale .98..1.02. Routing ownership follows existing `routing_radius.locations`: a rigid guide is owned by its upstream flexible segment, so all mid-guide holes belong to `near`; shared holes change once, transverse offsets only. Archived shared generator fields retain their historical semantics. The speed weights remain 0.025..0.10; supported PPO/reward fields use the existing RL schema. Task thresholds, solver recipes, force limits and topology cannot change. Materials are simulation scenarios, not a material database.

Native `research_analysis` offers target equilibrium and actual tension margins, local linearization/controllability, finite-time unilateral endpoint capability, and terminal braking. It uses typed, frozen protocols and explicit points or exact candidate-bound saved-state artifacts, without a Route/build-node/session fabrication. Public historical mathematical callers share the extracted calculations; kernels remain unchanged. A bounded static failure is not global infeasibility, endpoint certificates concern the frozen local model, and terminal speed does not prove the inclusive holding window. Jacobians describe state/input derivatives, not design sensitivity.

`research_plan search` defaults to mathematical evaluation only. The model chooses legal variables, bounds/options, point and objective: maximize minimum held position Gramian eigenvalue or minimize bounded target-equilibrium position residual. Backend-task search is an explicit alternative. The existing decoder, coordinate proposal and checkpoint loop are reused. Changing objective/point/protocol changes search identity. Proxy results report computation, local constraints, values and evidence separately; task acceptance is unmeasured and cannot enable confirmation. The incumbent can remain best; do not choose a worse structure just to claim novelty.

Prepare the ledger before real engineering preflight. Every candidate analysis (including internal search evaluations, failed attempts and preflight) charges the same24-evaluation/24000-second assignment ceiling. Its internal solves are listed in evidence. Actual construction time also accumulates. Reads and completed-operation reuse incur no additional scientific charge. Live clock starts once at model dispatch while engineering counts/time remain intact. Unknown termination retains reservations; recovery packages existing output and never repeats a completed solve. A code repair needs commit plus explicit `migrate --reason ...`, preserving identity, budget and counters.

For a new study, create a specification with a new ID, evidence destination, explicit nominal source, reference values, grants/constraints, frozen protocol/task and authorized cumulative limits. Do not edit or reopen a stopped study. Current checked-in identity is single-use. Large checkpoints and intermediate files stay under ignored `runs/<study_id>`; export uses the established immutable artifact archive and manifest.

Legacy co-design changes only its declared .16+.0055d/.11-.0055d length family and is admitted only when the exact physical configuration is represented. Other candidates retain direct RL and NMPC. Residual RL needs exact candidate/task/channel/timing/unit/bound identity; no relabeling, clipping or resampling of another robot's reference. Offline feasibility and verification remain distinct from backend acceptance. A fresh passing development result freezes the exact design/controller/checkpoint, then two fresh confirmations are required. Historical/imported results never satisfy either fresh gate. Confirmation history follows resolved scientific configuration and policy content SHA, so new result references, candidate provenance, checkpoint paths or training bookkeeping cannot erase a failure. Historical failures remain binding while historical passes consume no current confirmation allowance.

After a failed or invalid confirmation, an active study may develop a genuinely changed solution. Select its freshly passing development result with `research_plan action=confirm`, `selected_execution` and `revise_selection=true`. Admission checks capacity for that solution's own two confirmations. The explicit transition retains the previous selection/progress in `selection_history`, every result and all cumulative counters; a failure for the same scientific identity remains ineligible. Selection stays immutable during a confirmation attempt. RL development admission again protects two confirmations after failure. Two successful fresh confirmations automatically seal the study; accepted STOP remains sealed. Structural search completion, finding a better design, and delivering a new confirmed design are separate outcomes. Next boundary: validated broader structural optimization and generic design sensitivity; no robustness, real-time or hardware claim.

Reading or importing a historical state performs no mathematical solve and incurs no new scientific charge. Running a new analysis of that exact historical binding consumes one current assignment mathematical evaluation and its measured numerical time, including failures/timeouts. The existing operation receipt/recovery path settles it once; later reads and receipt reuse add zero. Historical provenance does not exempt new computation from current budgets or make its output fresh backend acceptance evidence.

Current single-use study `research-chain-20261014` is stopped after a valid failed confirmation. The model selected six target-equilibrium proxy evaluations over independent lengths and section scales; five candidates had real structural changes. It chose lengths .16/.11m, distal1 section scale1.025, all other structural settings nominal and NMPC weights .10/.10. Development passed (terminal3.409mm, holding3.478mm, speed.007281m/s); the first fresh confirmation failed holding speed(.047412m/s), while holding3.821mm and terminal3.403mm passed. Existing eligibility blocked the second confirmation, and no retry occurred. No new confirmed design was delivered and superiority over the nominal was not established. The original model's region-wide absence claim and its mixed-unit residual comparison are qualified in `evidence/research_chain_20261014/factual_qualifications.json`.

The cumulative assignment used12 provider requests,21 public operations,14 mathematical evaluations (8 engineering/6 model search),2 NMPC episodes and1075.195 numerical seconds, including final engineering verification. No RL training, legacy offline solve or independent integration was selected. Earlier contained-study1933.210 numerical seconds remain historical and were not transferred. Scientific execution was frozen at281918bd; subsequent delivery-only factual/compatibility edits did not launch additional science. Exact archive, counters, original decisions and metrics are in the [machine summary](../evidence/research_chain_20261014/scientific_summary.json); focused checks are in [verification](../evidence/research_chain_20261014/verification.json). Start any future experiment as a separately authorized new study, never by reopening this accepted STOP.

Current mainline NMPC derives its recipe through `current_nmpc_recipe` and the existing `controller_recipe` path. The explicit starting policy is `research_work_v1`, 120 iterations, tolerance 1e-6, `max_cpu_s=null`, `feasible_return=null`. At the IpoptSolver boundary `max_wall_s` is also null; it is not a trajectory-schema field. Normal solves stop on convergence/acceptable convergence or the iteration ceiling. Elapsed-time measurement and the enclosing execution watchdog remain. External timeout is incomplete evidence, never a successful command. Independently feasible iteration-limited plans remain usable and suboptimal, with raw termination and selected iteration retained; recovery remains independently checked.

The nominal archive retains its historical recipe verbatim. New candidates, backend execution, diagnostic stopping, metadata and scientific identity consume the effective policy. Historical artifacts are read under their original candidate/profile, never relabeled as current candidates. The generic timed solver feature remains required by the registered bounded NMPC controller (`gvs_bounded_nmpc.py`), control-comparison/diagnostic tools, and offline CasADi co-design workers. They are not alternative current research routes. The native LocalDiagnostic interface exposes `research_policy` (exact serialized problem) and `research_current` (explicit current-workspace reconstruction), without production timers, caller-chosen iteration caps, solver reuse or tail-preparation switches.

Prepare and commit scoped code/configuration before scientific binding. For this assignment:

```powershell
$spec='examples/research_chain/feedback_design_study.json'
& $researchPython -m tools.research.core prepare --spec $spec
& $researchPython -m tools.research.core bind --spec $spec
# Write the exact failed execution EvidenceRef to ignored runs/<study_id>/source.json.
& $researchPython -m tools.research.numerics import --spec $spec `
  --archive evidence/research_chain_20261014 `
  --execution runs/feedback-design-20261014/source.json --updates 0 29 30
& $researchPython -m tools.research.core execute --spec $spec `
  --plan examples/research_chain/nmpc_repeatability.json --request-id engineering-repeatability
```

Archive/member hashes, serialized model identity, exact historical candidate and profile are checked. Importing reads evidence only, costs no new solve, and registers the original candidate through the existing historical admission path. New backend admission still requires the current profile. Local comparison uses two new processes with the same single-thread numerical environment and exact original expression, bounds, initialized vector, scaling, previous input and recovery. Only stopping settings change. Each solve has a 300s external watchdog; the cumulative allowance is four attempts and 1200s, including failures. Report raw/selected/delivered plans, first commands, objective, independently checked residual, initialization/problem identities and actual cost. Local agreement supports this saved problem only.

For historical failure-state analysis, the existing native request now accepts:

```json
{
  "candidate": {"artifact_id": "exact original candidate hash", "media_type": "application/json"},
  "execution": {"artifact_id": "exact execution result hash", "media_type": "application/json"},
  "update_id": 30,
  "operation": "braking",
  "operating_point": "saved_state",
  "protocol": "replace with the complete frozen analysis_protocol object"
}
```

The protocol in a real request is an object, not the explanatory placeholder above. Alternatively use the existing `saved_state` reference; the two state-source forms are mutually exclusive. Do not hand-author physical state or provenance. The same resolver handles new executions through ControlEvidence and explicitly imported archived executions. Candidate, physical configuration, coordinate order, tendon order and timestamps must match exactly. Missing original problem/state is an explicit limitation; reconstruction must not be called exact.

The projected interval-start state precedes the new command. Linearization uses the previous applied input in N; the newly computed command is recorded separately. Update29 at t=.29s has .06s remaining and update30 at t=.30s has .05s remaining. Terminal duration is zero, never an invented positive horizon. Recorded backend tip position/velocity are measurements; the calculated endpoint/braking and tension margins describe the GVS model at the projected MuJoCo state. A local terminal braking witness does not prove inclusive holding, and local solver failure does not establish global infeasibility.

Historical reads/imports retain zero additional scientific cost. New analysis on historical inputs charges one mathematical allocation and actual contained-worker time through the existing once-only settlement/recovery path. Preflight and model research use one study ledger; no separate budget transfer/reset is needed. Native feedback includes failed criteria with units/thresholds/times, raw solver outcome counts, execution timing and mathematical references.

After preflight, use `core live --spec $spec` for one fresh model-led study. The packet contains compact historical feedback, diagnostic results and state mathematics; the model selects variables, supported search objectives, backend route and revise/STOP decisions. Preserve capacity for two fresh confirmations. A structural milestone needs actual evaluation of a model-selected structural change; task performance alone cannot establish structural improvement without a comparable nominal evaluation. Existing `revise_selection=true`, failure retention, freshness gates and sealed STOP semantics remain authoritative.

Export with `core export --spec $spec`. The immutable artifact archive/manifest, state, calls, ledger and final packet retain exact evidence and all costs. Commit compact nonsecret summaries and necessary immutable artifacts; leave environments, credentials and transient run directories untracked. Record implementation SHA and effective policy before model dispatch; repairs use committed explicit migration with unchanged budgets and retained evidence.
