# Reusable GVS NMPC free-reach profile

`gvs_nmpc_free_reach_v1` is available as `controller.gvs_nmpc@2.0.0` with the
`family.gvs_profile_control` Payload. It reproduces the Stage 3.15 combination
for one fixed robot and original 350 ms task. The older controller remains
available under version 1.0.0.

The predictor is `model.gvs` with a structural-linear basis. Execution remains
`model.serial_bending_cells` in MuJoCo, with 12 cells per segment, direct ideal
tensions, 10 ms command holds and 0.5 ms physics steps. The target is
`[0.29, 0.035, 0.19]` m with the original 10 mm endpoint criterion. Dimensions,
coordinate order and tendon order resolve from the design. No motor states or
contact validation are implied.

The declarative configuration and explicit numerical import are in
`extensions/tendon_family/profiles/gvs_nmpc_free_reach_v1.json`. The bundled
nominal point and first Stage 3.15 plan retain source paths, source hashes and
JSON pointers. They do not require historical Store sessions or experiment
module imports. `control.profile_describe` imports their content-addressed data
into a fresh project Store and returns compact evidence pointers. The execution
preparation hook performs the same import when describe has not been called.
Package assets participate in dependency identity checks.

The imported nominal state is metadata. The imported trajectory is a numerical
guess. At each update, actual backend measurements and the previously applied
input constrain the optimization. The existing implementation regenerates every
warm state and independently checks the selected plan. Workspaces and warm state
are private to each v2 controller execution; graph/solver construction is reused
within that execution. Build/loading performs no numerical solve.

The profile preserves all Stage 3.15 effective solver and objective settings,
including horizon 10, reverse constraint differentiation, one integration
substep, terminal rate penalty, whole-trajectory regeneration, feasible return
policy (5 s minimum, 15 s budget, 10% improvement), and three consecutive unusable
updates before stopping. Hold-last bounded tension is the sole failure response.
Every applied hold is recorded. This is offline simulation: historical mean
delivery was 25.073 s per 10 ms update, with all 35 deadlines missed.

## Public reproduction

Use a new output directory for each acceptance. No private cache seeding, paid
model call, full GVS rollout or historical investigation is needed.

```powershell
Set-Location 'D:\softrobot-agent'
$py = 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe'
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
$out = 'runs/gvs_profile_reproduction'
& $py examples/gvs_nmpc_profile.py prepare --output $out
& $py examples/gvs_nmpc_profile.py run --output $out
& $py examples/gvs_nmpc_profile.py inspect --output $out
```

Each command runs in a fresh process. `prepare` is optional: `run` prepares a new
Store when needed. The saved workflow identity makes repeated invocation recover
the sealed requests instead of starting another simulation. Use another output
directory to request another execution. The example invokes ordinary public
`simulation.run` and unchanged `evaluation.run`, with budget for both calls;
the host reserves the per-call timeout even for evaluation.

For other Host/Route clients, `profile_input(new_run_id)` provides the frozen
SessionInput. The declared controller Binding can be used in a Route combination
with the profile's backend and execution-model bindings, preserving the profile
robot/task/discretization. Route build remains zero-solve. Registry metadata and
Route overview point to `control.profile_describe`; the public reporting tool is
`control.profile_report` with the simulation and evaluation request IDs.

## Evidence and experience

The report consumes sealed receipts and immutable backend exports. It reports
valid complete execution, official success, independently accepted plans, raw
termination, selected initialization, hold-last responses, force limits, projection
residuals and construction/preparation/solve/validation/delivery times separately.
The extra settling check uses the final 50 ms sampled window: error <= 10 mm and
tip speed <= 0.02 m/s. Missing or incomplete data is unavailable. It is not a
continuous-time guarantee and does not change the authoritative evaluator.

The example proposes one scoped engineering Skill before execution and binds its
strategy hash with `control.profile_declare_strategy`. The trusted report emits
strategy validation evidence only for the new matching execution, then the
ordinary `skills.validate` path records the result. The skill remains an
unapproved development recommendation. `allow_development_skills=true` is required
for retrieval; a fresh session demonstrates both `skills.search` and Host context
delivery. Two memory notes explain inspection, never self-certify performance.

The skill covers profile selection, measured-state warm regeneration, feasible
early-stop interpretation, reach/settling/timing distinctions, full delivery cost
and preservation of pre-reset trajectory boundaries. Exact design, environment,
goal, initialization, timing, predictor/controller, execution representation and
seed scope carry validation. Changed configurations are explicitly unvalidated
starting points; incompatible model/backend/controller families are excluded.
Profile execution itself rejects scope changes. Local model-agreement evidence
remains separate from this closed-loop task evidence.

The new report generator derives statements from saved evidence. Historical
Stage 3.15 scripts, sealed evidence and reports are preserved. Combined settings
do not isolate individual causal effects; one successful task does not establish
neighboring-task transfer, global stability, robustness or actuator realism.

Focused checks:

```powershell
& $py -m unittest tests.test_gvs_profile tests.test_platform.PlatformTests.test_skill_existing_lifecycle_and_next_context -v
```
