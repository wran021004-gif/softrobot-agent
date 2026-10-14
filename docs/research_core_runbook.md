# Current research chain

Run from the isolated repository root with the existing research interpreter; the RL bridge retains its separate `D:/softrobot-agent/.rl-pilot-env/Scripts/python.exe`. No environment rebuild is needed. Preserve the bridge's Windows system environment inheritance.

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

Active topology is two flexible segments `near/distal1`, six independent ideal tensions 0..8N. Lengths can vary independently within source-relative ?5% (.152..168 and .1045..1155m), or use declared fixed-total allocation; optional aggregate bounds are checked directly. Each segment has section scale .95..1.05, material scenario baseline/compliant/stiff (modulus1/.9/1.1), and routing scale .98..1.02. Routing ownership follows existing `routing_radius.locations`: a rigid guide is owned by its upstream flexible segment, so all mid-guide holes belong to `near`; shared holes change once, transverse offsets only. Archived shared generator fields retain their historical semantics. The speed weights remain .025..10; supported PPO/reward fields use the existing RL schema. Task thresholds, solver recipes, force limits and topology cannot change. Materials are simulation scenarios, not a material database.

Native `research_analysis` offers target equilibrium and actual tension margins, local linearization/controllability, finite-time unilateral endpoint capability, and terminal braking. It uses typed, frozen protocols and explicit points or exact candidate-bound saved-state artifacts, without a Route/build-node/session fabrication. Public historical mathematical callers share the extracted calculations; kernels remain unchanged. A bounded static failure is not global infeasibility, endpoint certificates concern the frozen local model, and terminal speed does not prove the inclusive holding window. Jacobians describe state/input derivatives, not design sensitivity.

`research_plan search` defaults to mathematical evaluation only. The model chooses legal variables, bounds/options, point and objective: maximize minimum held position Gramian eigenvalue or minimize bounded target-equilibrium position residual. Backend-task search is an explicit alternative. The existing decoder, coordinate proposal and checkpoint loop are reused. Changing objective/point/protocol changes search identity. Proxy results report computation, local constraints, values and evidence separately; task acceptance is unmeasured and cannot enable confirmation. The incumbent can remain best; do not choose a worse structure just to claim novelty.

Prepare the ledger before real engineering preflight. Every candidate analysis (including internal search evaluations, failed attempts and preflight) charges the same24-evaluation/24000-second assignment ceiling. Its internal solves are listed in evidence. Actual construction time also accumulates. Reads and completed-operation reuse incur no additional scientific charge. Live clock starts once at model dispatch while engineering counts/time remain intact. Unknown termination retains reservations; recovery packages existing output and never repeats a completed solve. A code repair needs commit plus explicit `migrate --reason ...`, preserving identity, budget and counters.

For a new study, create a specification with a new ID, evidence destination, explicit nominal source, reference values, grants/constraints, frozen protocol/task and authorized cumulative limits. Do not edit or reopen a stopped study. Current checked-in identity is single-use. Large checkpoints and intermediate files stay under ignored `runs/<study_id>`; export uses the established immutable artifact archive and manifest.

Legacy co-design changes only its declared .16+.0055d/.11-.0055d length family and is admitted only when the exact physical configuration is represented. Other candidates retain direct RL and NMPC. Residual RL needs exact candidate/task/channel/timing/unit/bound identity; no relabeling, clipping or resampling of another robot's reference. Offline feasibility and verification remain distinct from backend acceptance. A passing development result freezes the exact design/controller/checkpoint, then two fresh confirmations are required; preserve failures and do not hunt for success. Structural search completion, finding a better design, and delivering a new confirmed design are separate outcomes. Next boundary: validated broader structural optimization and generic design sensitivity; no robustness, real-time or hardware claim.
