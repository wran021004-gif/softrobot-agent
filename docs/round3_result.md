# ROUND 3 RESULT

Stages 1–12 PASS. Stage 13 BLOCKED_FOR_HUMAN_APPROVAL. Deterministic multi-fidelity
evaluation, bounded design search, geometric sensitivity, actual MuJoCo tip feedback
and bounded repair are implemented. No production numerical authorization was
invented. No LLM runtime, new physics law, commit or push.

Audited baseline: branch feat/round3-stage0-task-contract, HEAD 928547d. Initial
tracked workspace was clean. Read the Round 1/1.5/2/2.5/3 Stage 0 reports,
TaskContract and trace architecture, agent contracts, physics contracts, family
grammar/docs and tool manifests before implementation. No approved experiment or
feedback numerical policy existed. The production grammar still denies all design
optimization variables; only its descriptive optimizer status note changed.

Primary retained evidence:
[validation artifact](../runs/20260911T114748_154344Z_136987eb/round3_validation.json),
[validation run manifest](../runs/20260911T114748_154344Z_136987eb/run.json),
[final reach_free run](../runs/20260911T114748_260596Z_abde9986/run.json).
The validation artifact contains before/after manifests, all artifact hashes,
trace/Gate counts and exact child references for real backend software tests.
Its SHA-256 is fb6aaf797c5feb49bfc02c5e6b1f19386fa31794cedf7925258648b6da3fb18f.
Runs remain local under the existing ignored runs/ directory.

## STAGE RESULTS

| Stage | Result | Concrete evidence |
| --- | --- | --- |
| 1 Audit + pre-change regression | PASS | 92/92 existing tests with real MATLAB; fresh run 20260911T112523_097439Z_2f0780d4 reproduces baseline |
| 2 Experiment policy + Human boundary | PASS | schemas/experiment_policy.py; file-owned validator; exported JSON Schema; unapproved proposal and explicit Human decision list |
| 3 Reusable candidate evaluator | PASS | run_reach optional M0/M1/MUJOCO routes; evaluate_candidate; strict CandidateEvaluation; test verifies model/canonical separation and source hashes |
| 4 optimize_design infrastructure | PASS | Callable, manifest and artifacts; baseline/endpoints/seeded bounded search; deterministic replay, rejection and failure retention tests |
| 5 Model sensitivity without new physics | PASS | tools/pcc_math.py PCC/tendon derivatives; finite-difference and straight-limit tests; actual MATLAB tip consistency |
| 6 Feedback infrastructure | PASS | PCCTipFeedback, FeedbackParameters/Artifact/Update schemas, manifest, timing/command-bound tests; no production numerical defaults |
| 7 MuJoCo feedback execution | PASS | Actual current-qpos tip observations; deterministic C2 replay; 50 updates in retained TEST_ONLY real-backend run |
| 8 Parameter sensitivity + diagnostics | PASS | Callable and manifest; exact perturbation/evidence artifacts; existing diagnostic tools retained; varying-command comparisons explicitly unavailable |
| 9 Bounded deterministic repair | PASS | Explicit Python loop; shared total/MuJoCo budgets; policy-order decisions; zero/one/shared-budget tests |
| 10 Trace/artifact/provenance | PASS | Existing RunArtifacts/TraceWriter only; candidate/decision spans; all parent/child hashes and traces verified; partial-failure retention test |
| 11 Agent contract integration | PASS | Engineer/Diagnosis/Coding contracts updated; no runtime, permission expansion or Skill admission |
| 12 Full tests + real backend regression | PASS | Final 110/110 tests; real MATLAB/MuJoCo validation script; two legacy routes preserve all metrics and 10 numerical artifact files each |
| 13 Real authorized experiments | BLOCKED_FOR_HUMAN_APPROVAL | No approved production variables/bounds, numerical controller policy or budgets; retained blocked run 20260911T114750_139123Z_76a2b99a has no numerical execution |

## HUMAN DECISIONS

The complete reviewable proposal is
[round3_human_decisions.md](../proposals/engineer/round3_human_decisions.md), with
[machine-readable PROPOSED policy](../proposals/engineer/round3_experiment_policy.yaml).

1. Select permitted DesignSpec variables and approve units, finite bounds,
   positive/integer constraints and scientific sources in the Human-owned grammar.
2. Approve the experiment subset, model ranking objective reference and canonical
   MuJoCo comparison objective reference. Task target/tolerance remain referenced.
3. Approve M0/M1 and C1/C2 routes, seed, total candidate evaluation budget and
   MuJoCo validation sub-budget, including baseline comparison allocation.
4. For feedback, approve the Jacobian-transpose experiment and all six fixed
   parameters: gain_rad2_per_m2, update_every_steps, max_bend_update_rad,
   max_command_update_m, min_tendon_length_m, max_tendon_length_m.
5. Approve sensitivity variables/ranges and model/simulation route.
6. Approve repair action order, iteration budget and stop conditions. Every action
   shares the experiment budgets and must cite policy permission.
7. Supply the Human approval record and reviewed policy under configs/experiments/.

Separate deferred scientific decisions remain material/EI, damping, tendon
elasticity/slack/friction, calibrated actuator dynamics, multi-section coupling
and justified causal mismatch/tracking/anomaly criteria. Their absence does not
block the implemented geometric algorithms. Formal reach_window geometry,
acceptance and initial-state approval remain outstanding under the existing
benchmark proposal; nothing promotes it automatically.

## OPTIMIZATION RESULT

| Required field | Formal reach_free result |
| --- | --- |
| Implemented? | Yes: tools.experiment_tools.optimize_design; IMPLEMENTED manifest and focused tests |
| Authorized? | No; BLOCKED_FOR_HUMAN_APPROVAL |
| Executed? | No real reach_free design search; blocked attempt persisted |
| Variables? | None approved in production grammar |
| Bounds source? | No approved numerical bounds; proposal leaves values unset |
| Evaluation budget? | Unapproved/unset |
| Best candidate? | BLOCKED; no formal optimized candidate |
| Model metric? | BLOCKED for optimization; unchanged legacy metric below |
| MuJoCo metric? | BLOCKED for optimization; unchanged legacy metric below |
| Canonical task status? | No optimized formal result; legacy TASK_FAILED |

Separate software validation, **TEST_ONLY / DEVELOPMENT_ONLY**, used the exact
synthetic [fixture policy](../tests/fixtures/round3/policy.yaml) and its own grammar.
Real MATLAB/MuJoCo executed 6 evaluations: 4 M1 and 2 canonical validations.
Variable total_length_m used synthetic [0.35,0.45] m, seed 17. Other DesignSpec
fields remained fixed. The best tested candidate was length 0.35 m, model error
0.040842775152800576 m and simulated error 0.1405118443004635 m, TASK_FAILED.
These values demonstrate executable search, not an approved reach_free result.
Parent run: [optimization summary](../runs/20260911T114750_210158Z_e0552e23/optimization_summary.json).
Candidate_0005 links to actual child 20260911T114754_646505Z_5c4795fc.

The bounded method is baseline, coordinate endpoints and seeded samples, without
a new dependency. It does not claim global optimality. SCREENING failures remain
eligible for simulation; actual canonical outcome/error ranks physical results.
All failed and rejected candidates remain visible in snapshots/history.

## CONTROL RESULT

Legacy C1 open_loop_length retains its historical meaning: hold the original PCC
tendon targets [0.4,0.38198416580296846,0.4,0.4180158341970316] m. Those commands
come from unchanged MATLAB M1, not new controller gains. The existing inner
actuator kp=1000 N/m and pull range [-20,0] N remain sourced from the approved
legacy surrogate Physics Contract. They were neither tuned nor reclassified.

C2 is new outer tip feedback; C0 remains passive and C3 unimplemented. Production
C2 execution/tuning is BLOCKED_FOR_HUMAN_APPROVAL. Parameters are separate from
DesignSpec and have no numerical defaults.

| Route and scope | Model error (m) | Actual MuJoCo error (m) | Task result |
| --- | --- | --- | --- |
| Formal legacy reach_free C1 | 0.08714456960728613 | 0.17116166894090315 | TASK_FAILED |
| Formal reach_free C2 | BLOCKED | BLOCKED | NOT_RUN |
| TEST_ONLY development C1 | 0.08714456960728613 | 0.17116166894090315 | TASK_FAILED |
| TEST_ONLY development C2 | Initial PCC 0.08714456960728613; not a prediction of closed-loop outcome | 0.15318050153888021 | TASK_FAILED |

Exact synthetic parameter source: tests/fixtures/round3/policy.yaml#feedback_parameters.
Gain 0.3 rad²/m²; period 20 steps; maximum bend increment 0.01 rad; maximum tendon
command increment 0.0001 m; tendon command bounds [0.2,0.6] m. These test numbers
are not Human-approved real experimental values. Real TEST_ONLY feedback child
[20260911T114759_882625Z_c13773b9](../runs/20260911T114759_882625Z_c13773b9/feedback_controller.json)
saved 50 updates; largest observed command increment was
9.999999999998899e-05 m. The high-level trace has 90 events, not 1000 per-step logs.
Two real-MuJoCo test replays had identical update records and final state.

The controller differentiates existing PCC geometry and tendon mapping, uses actual
MuJoCo current-qpos tip observations from an independent kinematics buffer, and
bounds updates/commands. No solver-state observation mutation, new mechanics law,
MPC, RL, stability certificate or tuning optimizer is introduced.

## DIAGNOSTIC / REPAIR RESULT

Legacy observations remain: model-to-simulator tip discrepancy
0.1841045610291436 m; largest final tendon tracking difference
0.006847228877633504 m; no sampled maximum-pull saturation; 1000 finite completed
steps and zero simulator warnings. These support measured discrepancies and
TASK_FAILED, not MODEL_MISMATCH, CONTROL_FAILURE or a universal causal explanation.
Attribution remains UNKNOWN; no new thresholds were inferred.

TEST_ONLY sensitivity varied length alone over 0.35, 0.4, 0.45 m through real M1.
Observed errors were 0.040842775152800576, 0.08714456960728613 and
0.13299498539352073 m, a sampled nondecreasing effect. This is evidence only.
[Sensitivity artifact](../runs/20260911T114755_843527Z_d6914d6f/sensitivity_evidence.json).

No formal repair was executed. The TEST_ONLY repair parent
[20260911T114758_432862Z_d85c411b](../runs/20260911T114758_432862Z_d85c411b/repair_summary.json)
executed exactly one C1-to-C2 experiment, authorized by fixture policy
repair_actions[0]=synthesize_feedback and repair_iteration_budget=1. It read the
baseline evaluation and saved diagnostic reference. Two total evaluations consumed
two MuJoCo slots. The decision used explicit policy order, not a claimed diagnosis.
Final task remained TASK_FAILED. Same-command model/clearance comparisons return
unavailable under varying commands; actual collision/force/tracking/numerics data
remain available. No canonical override or Skill admission occurred.

## MATLAB / MUJOCO CONSISTENCY

| Backend/tool | RobotIR consumed | TaskSpec consumed | EnvironmentSpec consumed |
| --- | --- | --- | --- |
| MATLAB M0 analyze_workspace | section.length_m, frame/family checks | target_m, environment_id identity; Harness also uses tolerance | environment_id/coordinate_frame checks; gravity/objects omitted |
| MATLAB M1 plan_pcc_reach | section.length_m, tendon count/routing radius, ordered route angles, sections/frame/family checks | target_m, position_error_max_m, environment_id | identity/frame checks; gravity/objects omitted |
| MATLAB analyze_clearance | section length/body radius/segments, M1 theta/phi, frame/sections | task_type, environment_id, target_m[0] for beyond-wall check | window position/dimensions/plane/normal, identity/frame, shared box geometry |
| MuJoCo compile/run | section discretization/body radius, ordered route offsets, mechanics, frame/family | environment_id, target marker; canonical target/tolerance/task_type/acceptance | gravity, objects, lights, frame/identity; same window for distance/contact/aperture |

M0 is geometric reach; M1 is approved PCC; clearance uses existing sampled
swept-radius geometry. MuJoCo uses existing segmented and actuator contracts,
SimulatorSpec.timestep_s and RunSettings.steps/seed. Detailed equations, assumptions,
Gate semantics, limitations and output artifacts are in the model manifests and
[backend field/model map](round3_experiments.md#backend-fieldmodel-map).
No MATLAB-specific task/environment truth file was introduced.

## SOURCE-OF-TRUTH CHECK

| Concept | Source and result |
| --- | --- |
| Task | tasks/reach_free TaskContract/TaskSpec unchanged; target/tolerance/evaluator authority preserved |
| Environment | Existing EnvironmentSpec unchanged; XML remains derived representation; development fixtures unpromoted |
| Design | Independent baseline DesignSpec unchanged; selected candidates only under policy/grammar authority |
| RobotIR | Same deterministic compiler/approved mapping; candidate-specific hashes retained |
| Physics | All physics_contracts unchanged; no new material, EI, damping, cable, actuator or multi-section law |
| Experiment/Search policy | New independent Human-owned schema and PROPOSED file; synthetic policies isolated in tests/fixtures |
| Controller | Legacy C1 unchanged; C2 parameters in separate policy/controller artifact, never DesignSpec |
| Simulator/run settings | configs/simulator.yaml and configs/run.yaml unchanged; no hidden step/duration/solver tuning |
| Metrics/Gates | metrics/ and schemas/gate.py unchanged; existing canonical logic preserved; MODEL_ONLY is an execution termination label |
| Artifacts | Existing sealed manifests, source snapshots, hashes and traces; parent/child references verified |
| Skill/Memory | No automatic finding/Skill admission, Memory mutation, or production Skill content |

## REGRESSION RESULT

| Measurement | Before | After |
| --- | --- | --- |
| reach_free PCC error (m) | 0.08714456960728613 | 0.08714456960728613 |
| reach_free actual error (m) | 0.17116166894090315 | 0.17116166894090315 |
| reach_free status | TASK_FAILED | TASK_FAILED |
| reach_free artifacts / trace events / Gates | 32 / 73 / 9 | 32 / 73 / 9 |
| Original window development artifacts / events / Gates | 35 / 86 / 15 | 35 / 86 / 15 |

Fresh reach_free before: 20260911T112523_097439Z_2f0780d4. After:
20260911T114748_260596Z_abde9986. Original development comparison uses retained
Stage 0 run 20260911T101011_362815Z_5c41864c and new run
20260911T114749_224330Z_4bab8012; it is not a fresh pre-change development run.
Both development errors also remain exactly the legacy values above.

All model/simulation/clearance metrics equal before/after, excluding run identity
comparison_context. Per pair, 10 files are byte-identical: task.yaml,
environment.yaml, design_input.yaml, design_final.yaml, robot_ir.yaml, physics.yaml,
robot.xml, controller.json, tendon_command.json and simulation_state.json.
Every registered artifact/source hash and trace validates for retained runs.

Representative unchanged hashes:

| Artifact | SHA-256 |
| --- | --- |
| robot_ir.yaml | b31229e81d67798b02e367192cec10dd899d4f9ebb7a79cb3b1108c3eb09d33f |
| robot.xml | 8bcfda19d7c5e57da57688a694eed8e27477b1cfcd449afcfc21af27059d211d |
| controller.json | c21bf763d6e1a2e1d01b9cb490c590900e7c80a2948f7d7208958c8421cc8c6a |
| simulation_state.json | e98d6131cf7f8243e3a3ca550f227c9c349306d9a00bd68fe1db9d5244ce6399 |

## TEST RESULT

Interpreter: C:\Users\gugugaga\miniconda3\envs\softagent\python.exe (Python 3.11.16).
MATLAB 24.1.0.2537033 (R2024a); MuJoCo 3.13.0.

Exact PowerShell commands (the full interpreter path applies to each Python call):

```powershell
$env:SOFTROBOT_TEST_MATLAB='1'
& 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe' -m unittest discover -s tests -q
& 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe' examples/run_reach_pipeline.py
& 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe' -m tools.export_contract_schemas
& 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe' -m unittest tests.test_round3 -q
& 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe' -m unittest tests.test_round3 tests.test_round1_boundaries tests.test_architecture -q
& 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe' examples/validate_round3.py --before 20260911T112523_097439Z_2f0780d4 --before-window 20260911T101011_362815Z_5c41864c --include-synthetic
git diff --check
```

| Check | Result |
| --- | --- |
| Pre-change full suite, MATLAB enabled | 92 passed, no skips; 55.751 s |
| Fresh pre-change real pipeline | TASK_FAILED recorded; CLI exit 1 is the intended task result |
| Initial focused Round 3, MATLAB opt-in unset | 15 passed, 1 skipped; 24.981 s |
| Intermediate full suite, MATLAB enabled | 108 passed, no skips; 88.851 s |
| Final focused suite after interruption/shared-budget tests, MATLAB opt-in unset | 48 passed, 1 skipped; 30.800 s |
| Final full suite, MATLAB enabled | **110 passed, no skips; 94.182 s** |
| Retained real backend validation command | PASS; exact baseline/development comparison plus TEST_ONLY search/sensitivity/repair |
| Exported schema drift tests / git diff --check | PASS |

The first sandboxed pre-change suite hit the existing Windows temporary-directory
access problem (87 tests discovered, permission/import failures). The same command
under reviewed execution permissions completed all 92 tests. No expectations were
changed for this issue. Its 60 verified-empty temporary directories were removed
using exact native PowerShell paths without recursive deletion. The three existing
roadmap assertions changed only to reflect implemented optimize_design and use
still-PLANNED fit_model_parameters when testing planned-tool rejection; numerical
expectations were never changed.

## LLM READINESS

Two distinct executable choices exist and are verified with actual backends in
isolated TEST_ONLY fixtures. No Human-approved real optimization/control policy
or formal second-route canonical evidence exists. Passing software tests and
development metrics do not establish readiness for scientific LLM execution.
Production Skill library remains empty. No commit. No push.

NOT_READY_FOR_LLM
