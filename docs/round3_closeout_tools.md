# Closeout tools, parameters and operating commands

This session's permission is recorded in [authorization](../configs/experiments/round3_closeout_authorization.yaml),
which cites the verbatim user instruction and previous envelope. No artificial signature,
global permission bypass, hardware driver or Skill admission is introduced.

| Entry | Inputs → outputs | Units / frame | Dependencies / assumptions | Implemented | Validated evidence | Calibrated / gap |
|---|---|---|---|---|---|---|
| `tools.pcc_math.tip_and_jacobian`, `analytic_target_matching_length` | length/bend or target → tip/J/analytic length | m, rad; base +x, yz bending | Python; PCC, inextensible branch [0,pi] | yes | regression straight limit, finite differences, sign and target tests | no force/torque inference |
| `MatlabTools.plan_pcc_reach`, `pcc_centerline` | IR/task → bounded fit, commands, shape | m/rad, same frame | MATLAB fminbnd; geometric model | yes | real MATLAB regression and all formal candidates | geometric only |
| `tools.actuation_tools.analyze_actuation` | IR/PCC → tendon lengths, stroke, Jacobian rank/SVD | m, m/rad | NumPy; geometric routing | yes | 3–8 tendons and actual campaign artifacts | no required tension/motor torque |
| `tools.mechanics_tools.export_parameters` | XML/IR → compiled mass/inertia/stiffness/damping + source hash | kg, kg m², N m/rad, N m s/rad | MuJoCo load only; no rollout | yes | actual baseline export and COM/frame checks | surrogate input, not calibrated material EI |
| `MechanicsTools.solve(operation='static')` | AnalysisSpec, nonnegative tensions + force → centerline, tip, q, residual, reason | SI; planar world xz | MATLAB one-mode discrete rod, fixed base | yes | zero load, gravity, known force and tendon responses; [validation](round3_closeout_validation.md) | no contact, out-of-plane DOF, length servo or physical calibration |
| `MechanicsTools.solve(operation='dynamic')` | same mechanics, IC, time-varying tension/force → state, tip, energy/residual history | SI; same planar frame | MATLAB ode15s, nonlinear reduced mass, damping | yes | rest, decay, tendon pulse, external-force pulse | energy may change under time-varying input; no collision semantics |
| `MechanicsTools.solve(operation='fit')` | frozen training/validation q/forces → bounded stiffness scale and separate validation loss | residual N m; loss (N m)² | MATLAB bounded fit; no validation-set selection | yes | truth=1.4 recovered as 1.3999999839206634; independent validation MSE 7.25e-21 | SYNTHETIC_VALIDATION, no real calibration or uniqueness claim |
| `resolve_analysis_capability` | AnalysisSpec → input/authority/dependency resolution | input SI | scoped approval, actual .m file and Engine package checked; license requires startup | yes | schema rejection, runtime environment and callable manifest checks | no fallback to an unrequested model |
| `compile_mujoco`, `run_task` | DesignSpec→IR→XML / controller → actual canonical result | m, N, rad; world base frame | real MuJoCo, frozen inner servo/physics | yes | full regression; observation invariance; formal attempts | uncalibrated legacy surrogate |
| `PCCTipFeedback` | actual observed tip + initial PCC → bounded changing length command | m/rad; 20 steps = 0.04 s | exact closeout policy, C2 starts at step 0 | yes | real development pair, timing/bounds tests and formal pairs | fixed gain is no stability proof; command bounds are not hardware stroke |
| `run_task(disturbances=...)` | body, world frame, time interval, force → dev response | seconds, N | closeout analysis permission; each component ≤5 N; separate from main | yes | independent 1 N world +z pulse | no platform motion/real device driver |
| `ReplayAdapter`, `replay` | saved trajectory → observation stream/CSV | saved SI timestamps | LOG_REPLAY; action sending rejected | yes | interface lifecycle test and saved normal trajectory | no real hardware started |
| `run_round3_closeout.py` | frozen policy/plan → parent state, attempts, decisions, best, reproduction | canonical metric m | existing Harness/RunArtifacts/TraceWriter; stage-specific budgets | yes | focused state/recovery tests, real formal campaign | candidate-boundary resume only; changed source revision rejected |
| `closeout_audit.audit`, `audit_bundle` | portable raw artifacts → recomputed metrics, hash/pair/budget checks | recorded units/frame | Python, NumPy, Pydantic/YAML; no numerical backend startup | yes | normal bundle + controlled corrupted copy | hashes are consistency checks, not tamper-proof signatures |

Normal `trajectory.json.gz` stores every step's tip, qpos/qvel, command, solver-stage
tendon length/force and contact count. `time_s` refers to post-integration state;
`solver_time_s` identifies force/tendon/contact sampling. A separate kinematics buffer
observes the post-step tip without touching the executed warm start. All final
canonical values still come from the existing final `mj_forward` and evaluator.
C2 update artifacts record observations, actual commands and clipping; the initial
PCC shape is not compared as a same-command prediction of its final state.

The old `StudyLedger` remains explicitly an invocation-local convenience, with an
expanded execution key. It is not used for closeout recovery. `CampaignState` persists
exact-fingerprint references and validates the original manifest/data before reuse.
It reserves each attempt before a worker launches and retains interrupted attempts.
Plan/source changes reject resume rather than silently mixing execution revisions.

## Authoritative parameters and assumptions

| Category | Authoritative source | Interpretation |
|---|---|---|
| Task / environment | [TaskContract](../tasks/reach_free/contract.yaml) → task.yaml/environment.yaml/mujoco.xml, benchmark/evaluator | frozen target [0.25,0,0.15] m, 0.01 m tolerance; original gravity/contact/IC |
| Design | [DesignSpec](../schemas/design_spec.py), [envelope](../capabilities/robot_families/tendon_driven_continuum/envelope.yaml), candidate inputs | main fixed sections=1, body radius=.020 m, segments=8; bounded L/r/count |
| Main physics / actuator | [legacy parameters](../physics_contracts/legacy_v1_surrogate.yaml), compiled XML/IR | stiffness=.1, damping=.1, density=1000, servo kp=1000, tensile limit=20 N; unvalidated assumptions |
| Geometry | [PCC](../physics_contracts/tendon_driven_pcc_v1.md), tendon mapping, coordinate contract | no static/dynamic force inference from geometry |
| Independent analysis | [analysis contract](../physics_contracts/closeout_analysis_v1.md), compiled exports in artifacts | equal hinge bends, nonlinear one-coordinate kinematics/mass; source-derived parameters, no second hand-copied physics truth |
| Control | [closeout policy](../configs/experiments/round3_closeout.yaml), controller/input artifacts | fixed C2 gain=.3, every20 steps, bend increment≤.01 rad, command increment≤.0001 m, commands [.001,1] m |
| Numerics | [simulator](../configs/simulator.yaml), [run settings](../configs/run.yaml), runtime versions | dt=.002 s, 1000 steps=2 s; simulator seed remains0; proposal seed17 |
| Identification | frozen split artifact and analysis contract | multiplier bounds [.5,2]; training ±.03/±.06 N; held-out ±.045 N; analysis-only new version |

## Task coverage

| Task | Current status | Reusable tools | Remaining semantics |
|---|---|---|---|
| reach / reach_free | formal frozen benchmark; this campaign | all main reach tools and conditional parallel analysis | physical calibration; failure attribution remains UNKNOWN |
| reach_window | existing DEVELOPMENT_ONLY fixture | PCC clearance, MuJoCo window contact, existing evaluator | frozen geometry/initial side and Human benchmark promotion |
| catch_drop | not executable task | geometric reach, reduced gravity/force pulse, MuJoCo compilation | falling object, contact/capture criteria, timing, task contract/evaluator |
| catch_ramp | not executable task | geometric planning, forced dynamics and disturbance recording | ramp/object friction/contact, release and capture semantics |
| stabilize_tip | not executable task | tip Jacobian/C2, disturbance response, state replay | approved time-window metric, perturbation protocol and stability criteria |

## PowerShell commands

```powershell
conda activate softagent
python examples/run_round3_closeout.py environment
python examples/run_round3_closeout.py plan-only
# Execute once only after code/tests are frozen. Existing campaign registry rejects a second campaign.
python examples/run_round3_closeout.py execute configs/experiments/round3_closeout_plan.json
python examples/run_round3_closeout.py resume runs/<parent_id>
python examples/run_round3_closeout.py inspect runs/<parent_id>
python examples/run_round3_closeout.py report runs/<parent_id> --output docs/round3_deterministic_closeout_result.md
python examples/run_round3_closeout.py audit docs/evidence/round3_closeout_evidence.zip
python examples/run_round3_closeout.py replay runs/<child_id> --output runs/replayed_tip.csv
# The following are validation commands, not formal experiment candidates.
python examples/validate_closeout.py real
python examples/validate_closeout.py analyze runs/<parent_id>
python -m unittest tests.test_closeout -v
python examples/validate_closeout.py full-suite
```

Recovery resumes unfinished candidate boundaries and retains budget history.
Reproduction is a fresh numerical run of a selected result; main E checks entire
trajectories and final metrics at atol=rtol=1e-9. Replay reads existing data and
does not run a solver. They are distinct operations. Do not rerun `real`, `analyze`
or full regression to re-prove a completed delivery; the persistent development
ledger counts all new solves. The full-suite wrapper refuses a second invocation.

MATLAB uses the existing softagent environment and Expat-before-MATLAB DLL import
order. No installation changes are required. Windows restricted process/temp ACLs
may prevent backend startup; use a normal PowerShell under the existing account.
Each candidate worker has a 180 s timeout; MuJoCo stepping has its own 120 s bound.
The math solver has iteration/time bounds as specified in its contract.
