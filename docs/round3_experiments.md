# Deterministic Round 3 experiments

TaskContract locates the problem; ExperimentPolicy authorizes a search procedure.
DesignSpec is the candidate. None stores an optimization result, controller tuning
result, diagnosis, Memory or Skill. Production numerical authorization is absent;
see [Human decisions](../proposals/engineer/round3_human_decisions.md).

## Execution and authority

Public callables in tools.experiment_tools:

```python
evaluate_candidate(task_contract, design, policy_path, fidelity, controller_level="C1")
optimize_design(policy_path)
run_parameter_sensitivity(policy_path, fidelity="M1")
run_repair_loop(policy_path)
```

evaluate_candidate returns `(CandidateEvaluation | None, RunArtifacts)`; the other
callables return finalized RunArtifacts. An unapproved policy produces a sealed
BLOCKED_FOR_HUMAN_APPROVAL run without numerical calls; malformed policies produce
ERROR with the reason. Parent PASS means orchestration completed, never canonical
robot task success. Read canonical_task_status and the child's gate_summary.json.

The reusable route extends existing run_reach. M0 stops after the existing
tolerance-aware necessary length HARD gate. M1 adds PCC and applicable clearance.
These terminate MODEL_ONLY with canonical_task_status=NOT_RUN. MUJOCO continues
through the original compiler, controller protocol, run_task, evaluator and
diagnostics. SCREENING failure never becomes a new HARD rejection. Legacy calls
without policy execute the original M0/M1/C1/MuJoCo route and numerical inputs.

Real approved policies and approval records belong under configs/experiments/.
Selected variables/bounds must be a subset of the referenced approved grammar,
including units and constraints. Production grammar authorization remains unchanged;
only its optimizer roadmap note now reflects implemented infrastructure.
TEST_ONLY policies/grammars must be under tests/fixtures/ and can execute only
DEVELOPMENT_ONLY TaskContracts. Their separate synthetic grammar references the
existing development environment without duplicating it. A status flag is repository
authority metadata, not cryptographic Human authentication. No OS sandbox or
untrusted Python executor is added. JSON schemas export with the existing command
`python -m tools.export_contract_schemas`.

## Search, sensitivity and repair

The bounded search evaluates baseline, each selected coordinate's lower/upper
endpoints with other fields fixed, then seeded bounded samples. Integer parameters
use integer sampling. Every attempt consumes total evaluation budget, including
input rejection and tool failure. There is no new optimizer dependency or Toolbox.
The method does not claim global optimality or convergence.

M1 ranking reserves the approved MuJoCo sub-budget. Validation evaluates baseline
first and then model-ranked candidates. Actual canonical PASS outranks FAIL, then
actual error ranks within outcomes. Both baseline and candidate must complete
MuJoCo before comparative physical improvement is supported. Screening FAIL remains
eligible; HARD/runtime failures remain recorded. Model scores cannot replace actual
metrics. All attempts are in optimization_history.jsonl with separate snapshots.

Sensitivity evaluates lower/baseline/upper points one parameter at a time, preserving
other inputs and saving exact perturbations. It reports only finite sampled trends
or UNKNOWN when evidence is missing. Budget truncation is visible in the saved
points. No universal mismatch/tracking threshold or causal conclusion is inferred.

The repair loop evaluates baseline, reads saved evaluation and diagnostics, then
executes the next action from Human-approved repair_actions order. Actions are
next_candidate, optimize_design, synthesize_feedback and run_parameter_sensitivity.
The loop shares total evaluation/MuJoCo budgets and obeys repair_iteration_budget.
Every decision names the exact policy index, evidence files and deterministic rule.
This is authorized exploration with UNKNOWN attribution. TASK_FAILED alone does
not establish a design, model or control cause.

## Feedback taxonomy and equations

Historical C1 means open_loop_length: held PCC targets despite the simulated
actuator's internal length servo. Historical artifacts are unchanged. Forward
taxonomy: C0 passive, C1 legacy open-loop, C2 experimental outer tip feedback,
C3 unimplemented. Methodology should say open-loop versus feedback explicitly;
numeric labels alone are not universal. No MPC, RL or controller tuning tool is added.

For b=[theta*cos(phi),theta*sin(phi)], t=norm(b), a=sin(t)/t and
c=(1-cos(t))/t^2, the approved PCC tip is L*[a,c*b0,c*b1]. tools/pcc_math.py
computes its analytic Jacobian J=d(tip)/db; at the straight limit a=1, c=1/2.
Stable Taylor evaluation near zero avoids cancellation. This is the continuous
geometric limit, not a derivative of MATLAB's tiny numerical straight-limit branch,
nor a physical acceptance threshold. The local derivative also exposes sensitivity
to L and the tendon mapping without introducing another physical model.

At each approved integer update period, delta_b=gain*J^T*(target-observed_tip).
Bound the increment by max_bend_update_rad and project b onto the existing
norm(b)<=pi PCC branch. Commands follow
l_i=L-r_t*[cos(alpha_i),sin(alpha_i)] dot b, bounded by approved positive length
limits and per-update command changes. Internal b is a commanded reference, not
a measured shape estimate. Clipped commands need not describe an attainable PCC
shape. No inverse dynamics, material/EI, damping, friction/slack or stability law
is assumed. No tracking, convergence or robustness guarantee is claimed.

All six controller parameters have no defaults and come from the policy, separate
from DesignSpec. MuJoCo supplies actual current-qpos tip position using mj_kinematics
on a separate MjData buffer. Observation never changes the executed solver state.
The runner validates finite positive commands/order, honors any compiled ctrl
limits, and preserves existing pull-only force limits. Disabled feedback creates
no feedback artifacts and retains the old integration behavior.

feedback_updates.json retains every scheduled update: step/time, observed tip,
error, internal bend, commands and clipping. The high-level trace contains only
a compact summary referencing this artifact. compare_model_sim rejects varying
commands for same-command attribution; check_collision likewise does not compare
an initial PCC shape with a feedback trajectory as same-command evidence. Actual
collision, tracking, force and numerics evidence remains available. Attribution
stays UNKNOWN.

## Provenance

Existing RunArtifacts/TraceWriter services own all persistence. Parent experiments
retain exact policy bytes, input/source hashes, candidate designs/evaluations,
history, summaries and child manifest hashes. Child runs retain policy/context,
TaskContract, TaskSpec, EnvironmentSpec, DesignSpec, RobotIR, backend metrics,
controller, state and diagnostics. Child references include finalized manifest
and artifact hashes. Sources are rechecked before candidates; sealed children
are never rewritten. No second trace framework is added.

Artifact != Trace != Memory != Skill. No automatic Skill/Memory admission or LLM
runtime exists. Synthetic executable choices do not satisfy the requirement for
authorized canonical choices before an Engineer LLM sandbox.

## Backend field/model map

| Consumer | RobotIR | TaskSpec | EnvironmentSpec | Equations, Gate, artifacts |
| --- | --- | --- | --- | --- |
| MATLAB analyze_workspace M0 | section.length_m; identity/frame | target_m; environment_id check; Harness reads tolerance | environment_id, coordinate_frame checks | norm(target)<=L observation; Harness norm(target-base)<=L+tolerance HARD necessity; workspace_result.json |
| MATLAB plan_pcc_reach M1 | section.length_m, tendon_count, tendon_routes.angle_rad, routing radius; sections/family/frame | target_m, position_error_max_m; environment_id check | identity/frame checks | Existing PCC tip and fminbnd theta in [0,pi]; length mapping; execution HARD, prediction SCREENING; model_result.json |
| MATLAB analyze_clearance | section.length_m, body radius, segments, sections/frame; M1 theta/phi | task_type, environment_id, target_m[0] to validate target beyond wall | identity/frame, window position, width, height, thickness, frame_width, plane/normal via shared window_boxes | Sampled PCC swept radius; signed point-box distance minus radius and half arc spacing; SCREENING; clearance_result.json with centerline |
| Python pcc_sensitivity | section.length_m, routing radius/angles | none | none | Analytic geometry derivatives; M1/SCREENING; ToolResult, caller persists |
| MuJoCo compile/run | section segment count/length/body radius, ordered routing offsets, mechanics; family/sections/frame | environment_id, target marker; evaluator target_m, tolerance, task_type, applicable acceptance | gravity, objects, lights, identity/frame; window geometry for contact/aperture | Existing segmented/actuator contracts; SimulatorSpec.timestep_s and RunSettings.steps/seed; robot.xml, mujoco_result.json, simulation_state.json; execution HARD, actual evaluator CANONICAL |

M0/M1 omit loads, gravity, mechanics and contact. Clearance is geometric, excludes
floor/dynamics, and a negative conservative lower bound alone does not prove
intersection. MuJoCo is the legacy surrogate with sampled collision evidence, not
a validated real robot. No duplicate MATLAB task/environment truth is introduced.
