# ROUND 1 RESULT

Round 1 implements parameter provenance, deterministic optimization authorization,
MuJoCo execution observations and four evidence-driven diagnostics while preserving
the canonical TASK_FAILED result. No LLM, design optimizer or retuning is introduced.

Branch: feat/round1-physics-diagnostics. Starting HEAD: 2a854280 (architecture
baseline). No commit or push performed.

Primary evidence:
[final diagnostic summary](../runs/20260911T053307_539565Z_13e07e9c/diagnostic_summary.json),
[provenance](../runs/20260911T053307_539565Z_13e07e9c/provenance.json),
[run record and hashes](../runs/20260911T053307_539565Z_13e07e9c/run.json).
This document summarizes those artifacts; it is not primary run truth.

## STAGE RESULTS

| Stage | Result | Implemented / verified | Tests |
| --- | --- | --- | --- |
| 1. Repository audit and regression | PASS | Audited schemas, IR, tasks/environment, contracts, settings, MATLAB/MuJoCo, manifests, artifacts, taxonomy and agent contracts; recorded a fresh pre-change real run | Initial suite: 26 passed, 3 MATLAB tests skipped; real pipeline TASK_FAILED |
| 2. Optimization boundary | PASS | Per-field policy in existing grammar; selection and candidate validators; EngineerOutput validation; all real variables denied pending approval | Five boundary tests including synthetic approved bounds and Windows paths |
| 3. Physics provenance | PASS | Expanded existing provenance.json; values read from executed inputs; resolved engine parameters recorded | Provenance test plus 26 existing tests passed |
| 4. MuJoCo observability | PASS | Per-step streaming force, command, tracking, finite-state and time evidence; warnings; initial/final tip; engine defaults | Real baseline preserved; synthetic saturation, passive, nonfinite and warning cases |
| 5. Diagnostic tools | PASS | compare_model_sim, check_actuator_limits, check_tendon_tracking, inspect_numerics; manifests, docs, callables | 12 diagnostic tests, including malformed evidence and overflow |
| 6. Canonical failure report | PASS | Automatic diagnostic_summary.json and four ToolResults in final run | Real MATLAB/MuJoCo pipeline; input/XML/final-state equality and artifact hashes |
| 7. Permissions and isolation | PASS | Deny-by-default Windows path hardening; Human-owned policy/evidence protection; future isolation activation documented | Role, traversal, absolute escape, ADS, reserved-name, case and separator tests |
| 8. Regression and documentation | PASS | README, family/tool/authority docs and scientific proposal updated | Final full suite: 47/47 including real MATLAB; git diff --check |

Scientific mechanisms requiring new Human decisions remain explicitly deferred;
their nonimplementation does not block the authorized Round 1 scope.

## BASELINE REGRESSION

| Measurement | Before | After |
| --- | --- | --- |
| PCC predicted error (m) | 0.08714456960728613 | 0.08714456960728613 |
| MuJoCo actual error (m) | 0.17116166894090315 | 0.17116166894090315 |
| Task status | TASK_FAILED | TASK_FAILED |

Pre-change run: 20260911T051303_812630Z_06628e02. Final run:
20260911T053307_539565Z_13e07e9c. Runtime: MATLAB R2024a
24.1.0.2537033, MuJoCo 3.13.0. task.yaml, environment.yaml, design_input.yaml,
robot_ir.yaml, robot.xml, tendon_command.json and simulation_state.json are
byte-identical across these two runs. The frozen target [0.25,0,0.15] m and
0.01 m tolerance remain unchanged. Source changes add observation/authorization;
they do not alter PCC equations, physical values, controller behavior or task gate.

## PHYSICS PROVENANCE MAP

| Parameter | Value | Category | Source | Scientific status |
| --- | --- | --- | --- | --- |
| Joint stiffness | 0.1 N m/rad | PHYSICS_MODEL | legacy_v1_surrogate.yaml → RobotIR | legacy_v1_surrogate; unvalidated |
| Joint damping | 0.1 N m s/rad | PHYSICS_MODEL | same profile | legacy_v1_surrogate; unvalidated |
| Capsule density | 1000 kg/m^3 | PHYSICS_MODEL | same profile | legacy_v1_surrogate; unvalidated |
| Tendon servo gain | 1000 N/m | ACTUATOR_MODEL | same profile | legacy_v1_surrogate; unvalidated |
| Pull force limit | 20 N; range [-20,0] N | ACTUATOR_MODEL | same profile + actuator_model_v1.md | legacy_v1_surrogate; unvalidated |
| Gravity | [0,0,-9.81] m/s^2 | ENVIRONMENT | frozen environment.yaml | frozen benchmark fact |
| Timestep | 0.002 s | SIMULATOR_NUMERICAL | configs/simulator.yaml | legacy numerical choice |
| Steps / duration | 1000 / 2 s | RUN_SETTING | configs/run.yaml; steps × dt | legacy run choice; not settling-time validation |
| Seed | 0 | RUN_SETTING | configs/run.yaml | recorded; no random sampling |
| Sections / segments | 1 / 8 | ROBOT_DESIGN | DesignSpec | existing design; examples are not bounds |
| Total length / capsule radius | 0.4 / 0.02 m | ROBOT_DESIGN | DesignSpec | existing design |
| Segment length | 0.05 m | ROBOT_DESIGN | RobotIR, L/segments | approved geometric derivation |
| Tendon count / routing radius | 4 / 0.015 m | ROBOT_DESIGN | DesignSpec | existing design |
| Routing | angle 2πi/4; y-z offset r[cos(angle),sin(angle)] | ROBOT_DESIGN | RobotIR + coordinate/routing contracts | approved geometric mapping |
| Tendon targets | [0.4,0.38198416580296846,0.4,0.4180158341970316] m | CONTROLLER | M1 → tendon_command.json | kinematic command; open-loop hold |
| Task target / tolerance | [0.25,0,0.15] / 0.01 m | TASK | frozen task.yaml | frozen benchmark facts |
| Floor geometry and masks | Full values in provenance.json | ENVIRONMENT | frozen environment.yaml | frozen benchmark facts |
| Body mass/inertia | Full per-body arrays in provenance.json | PHYSICS_MODEL | loaded MJCF, capsule geometry and density | engine-derived; surrogate inputs; not experimentally validated |
| Contact coefficients, masks, joint/tendon defaults | Full resolved arrays in provenance.json | PHYSICS_MODEL / ROBOT_DESIGN / ACTUATOR_MODEL | loaded MJCF and recorded MuJoCo defaults | legacy representation/defaults, not validated physical laws |
| Solver/integrator/contact numerical settings | Full resolved values in provenance.json | SIMULATOR_NUMERICAL | loaded MJCF and recorded MuJoCo defaults | engine numerical choices |

No material/EI stiffness or damping law has become physics-derived this round.
Geometric derivation and engine mass/inertia calculation are explicitly distinguished
from identified or experimentally validated mechanics. Marker sizes/colors remain
representation-only constants identified in the existing source provenance map.

## OPTIMIZATION BOUNDARY

There are currently no approved optimization variables. Grammar entries contain
category/unit, optimizable=false, null lower/upper bounds, constraints, provenance
and scientific_status=human_approval_required. Field keys supply variable names.

Human owns variables, bounds, units, constraints and objective authority. Engineer
may select only approved names; a future optimizer may return only approved values.
Candidate validation reloads policy, rejects unselected changes and out-of-bounds
values, and applies DesignSpec/grammar checks. There are no caller-supplied bound
or objective overrides. Frozen task/environment/metrics/tolerances and simulator
settings cannot enter the design-variable mechanism. Coding cannot modify policy,
objective, bounds, benchmark or evidence. optimize_design remains PLANNED.

## DIAGNOSTIC RESULT FOR CURRENT FAILURE

M1 predicts tip [0.31053385572145686, ~0, 0.2126883428041688] m and already
predicts tolerance failure. Actual tip is [0.3844450937959572, ~0,
0.04407156345517224] m. The Euclidean prediction-to-simulation discrepancy is
**0.1841045610291436 m**; this differs from subtracting the two task errors.

| Tendon index (zero-based) | Target (m) | Actual final length (m) | Signed tracking error (mm) | Absolute relative error |
| --- | --- | --- | --- | --- |
| 0 | 0.4 | 0.40000000000000013 | ~0 | ~0 |
| 1 | 0.38198416580296846 | 0.38883139468060196 | +6.8472288776 | 1.7925426% |
| 2 | 0.4 | 0.40000000000000013 | ~0 | ~0 |
| 3 | 0.4180158341970316 | 0.41132435119029287 | -6.6914830067 | 1.6007726% |

All actuators have force range [-20,0] N. Actuator 1 peaks at
18.015834197031495 N in absolute pulling force; actuators 0/2 peak at approximately
2.27e-13 N, actuator 3 at 0 N. No actuator reaches the -20 N bound in 1000 active
samples (0% / 0 s sampled exposure). Upper zero-bound occupancy is respectively
69.5%, 0%, 69.9%, 100%. A zero-bound observation alone proves neither active
clipping, physical cable slack nor maximum-pull saturation.

Numerics: 1000/1000 steps, dt=0.002 s; qpos/qvel/force/tendon length remain finite;
all recorded warning counters are zero, no time-advance anomaly. Peak |qpos| is
0.6140460194010043 rad and peak |qvel| is 2.2575461555606604 rad/s. There is no
approved large-qvel threshold or stability certificate.

Supported outcome: TASK_FAILED, with measured model and tracking discrepancies.
Causal attribution stays UNKNOWN. Current evidence does not establish
MODEL_MISMATCH, CONTROL_FAILURE or maximum-pull ACTUATOR_LIMIT as the cause.

## TOOL STATUS CHANGES

- PLANNED → IMPLEMENTED: compare_model_sim, check_actuator_limits,
  check_tendon_tracking, inspect_numerics.
- Still PLANNED: optimize_design, fit_model_parameters, run_parameter_sensitivity,
  check_tendon_slack, check_collision and the other existing roadmap capabilities.
- PHYSICS_ASSUMPTION_REQUIRED: material/EI mapping, new damping/cable/actuator laws,
  actual optimizer/sensitivity ranges and scientific mismatch/acceptance criteria.
  Existing legacy V1 execution continues without inventing those assumptions.

## PERMISSION / ISOLATION STATUS

Application-level permission: implemented and tested. OS/process isolation:
not implemented. Before autonomous Coding LLM write access, require isolated
worktree + permission-enforcing executor + post-run git diff allowlist + Human
review. Separate OS user/WSL2/container/VM with Human-owned inputs read-only is
optional stronger isolation. No autonomous writer/executor was introduced.

## TEST RESULT

Commands used the installed C:\Users\gugugaga\miniconda3\envs\softagent\python.exe:

| Actual command arguments | Result |
| --- | --- |
| -m unittest discover -s tests -v (before changes) | 26 pass, 3 opt-in skips |
| -m unittest tests.test_round1_boundaries -v | 5 pass |
| -m unittest tests.test_provenance tests.test_architecture -q | 27 pass |
| -m unittest tests.test_diagnostics -v | 11 pass at that stage; subsequently expanded to 12 |
| -m unittest discover -s tests -q (default, intermediate) | 43 pass, 3 opt-in skips |
| $env:SOFTROBOT_TEST_MATLAB='1'; python -m unittest discover -s tests -q (final, same interpreter) | 47/47 pass, 18.902 s |
| examples/run_reach_pipeline.py (before and after) | exit 1 for recorded TASK_FAILED, as intended |
| git diff --check | PASS |

First sandboxed conda test attempt could not write into newly created test
directories. The same tests passed with approved process/filesystem access;
the 14 abandoned temporary directories were removed after verifying exact paths.
No test expectation or scientific value was changed to address that environment
limitation. The final real tests verify MATLAB coordinates, single-tendon behavior,
Expat-compatible MJCF compilation, PCC/MuJoCo numerical regression, diagnostic
arithmetic, artifact hashes and source_snapshot.zip contents.

## OPEN SCIENTIFIC QUESTIONS

- Human-approved continuum material/backbone/EI mapping and discretization assumptions.
- Damping, tendon elasticity/slack/friction and calibrated actuator laws/sources.
- Legitimate optimization and diagnostic sensitivity variables, bounds, constraints
  and objective authority.
- Justified MODEL_MISMATCH criterion, tracking acceptance and numerical anomaly
  thresholds, including the required physical validation context.

Details and candidate assumptions are in
[the scientific proposal](../proposals/engineer/round1_physics_questions.md).

## FILES CHANGED

- Architecture/contracts: agents/contracts/{optimization.py,outputs.py,permissions.py};
  family grammar.yaml. No scientific schema, taxonomy, frozen input or physics value changed.
- Tools: tools/{provenance.py,mujoco_evidence.py,diagnostic_tools.py,mujoco_tools.py,harness.py};
  diagnostics/MuJoCo manifests; examples/run_reach_pipeline.py.
- Tests: test_round1_boundaries.py, test_provenance.py, test_diagnostics.py,
  test_matlab_integration.py.
- Docs: README.md, agents/contracts/README.md, family FAMILY.md,
  diagnostics/MuJoCo TOOL.md, scientific proposal and this report.

Runs remain local factual artifacts under the existing ignored runs/ directories.
No commit or push.
