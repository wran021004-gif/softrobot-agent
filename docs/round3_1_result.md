# ROUND 3.1 RESULT

Implementation and regression PASS. The first Human-authorized reach_free length
experiment completed 12/12 evaluations, including 5/5 MuJoCo validations. Best
tested length: **0.35 m**. Canonical error: **0.1405118443004635 m**; task outcome:
**TASK_FAILED**. **BOUNDARY_OPTIMUM_OBSERVED**. Bounds remain [0.35, 0.45] m.

Audited branch: `feat/round3-deterministic-improvement-loop`; HEAD:
`c2bebb5b95a409d87e57e62ee880931cfa60b5a7`, matching the request. The initial tracked
workspace was clean; the pre-existing untracked `chatgpt.md` was left untouched.
The Round 3 report, policy/schema/grammar validators, task authority, existing
candidate/search runner, MATLAB tools, MuJoCo runner and artifact service were
reviewed before implementation. Round 3's formal-experiment approval blocker is
resolved only for this explicit Round 3.1 authorization.

Retained [validation artifact](../runs/20260912T061707_948754Z_af3f3803/round3_1_validation.json)
and [manifest](../runs/20260912T061707_948754Z_af3f3803/run.json) contain regression
comparisons, all candidate references, source/artifact hashes, budgets and sensitivity
observations. The formal [experiment parent](../runs/20260912T061721_390989Z_61a4f4f8/run.json)
is separate from baseline and visualization regression runs. Runs remain local in
the existing ignored `runs/` directory. No commit, push or LLM connection.

## VISUALIZATION RESULT

The existing reach command accepts `--debug` and `--visualize`; both default to
false. `--debug` saves MATLAB figures and observational simulation trajectory/plots
without a desktop. `--visualize` displays MATLAB figures and opens a passive MuJoCo
viewer using the exact executed MjModel and MjData. Both flags can be combined.

MATLAB's new helper reads saved model/RobotIR/task/clearance results via a labeled
debug input copy. It shows the base, target, tolerance sphere, PCC centerline and
tip, with length, theta, phi, predicted error and tendon targets. The window figure
also shows the frame, aperture, closest clearance point and predicted minimum
clearance. Existing `analyze_workspace.m`, `plan_pcc_reach.m`, `analyze_clearance.m`
and their numerical ToolResults are unchanged. Figures were generated with real
MATLAB and visually inspected.

The real passive viewer was exercised in
[20260912T061714_261562Z_c5516cf8](../runs/20260912T061714_261562Z_c5516cf8/debug/status.json).
Its debug status has no errors, and the entire canonical metrics/state comparison
matches the headless baseline. Existing red target_site and green tip_site remain
in byte-identical robot.xml. All runs retain the existing 1000 steps, timestep,
run length, C1 commands, solver settings and numerical physics.

MuJoCo's public sync accepts GUI edits even with `state_only=True`. The adapter
therefore preserves full MjData, model buffers and numerical options across
launch/sync/close, discarding GUI edits before numerical execution continues. No
additional mj_step or mj_forward is called on executed data. Tests inject changes
to qpos/qvel/ctrl, applied forces, warm starts, body mass, gravity, timestep and
solver iterations, including a sync exception, and require identical complete
ToolResults. The separate debug tip buffer uses only mj_kinematics. Viewer pacing
changes wall time only. The upstream behavior is documented in the
[MuJoCo passive viewer contract](https://mujoco.readthedocs.io/en/stable/python.html#passive-viewer).

Visualization or recording exceptions remain in debug/status.json and cannot
change ToolResult, canonical status or trace step count. See [usage and sampling
semantics](debug_visualization.md).

## HUMAN AUTHORIZATION

Human-owned [ExperimentPolicy](../configs/experiments/round3_1_reach_free.yaml),
with [authorization record](../configs/experiments/round3_1_human_authorization.md),
transcribes the user's explicit Round 3.1 request. It references reach_free_v1's
existing TaskContract without copying target, tolerance or environment values.

| Authorization | Executed scope |
| --- | --- |
| Variable | total_length_m only; finite, positive, [0.35, 0.45] m |
| Fixed baseline | sections=1; segments=8; body_radius_m=0.02; tendon_count=4; tendon_routing_radius_m=0.015; original robot_family |
| Screening | M1 PCC; minimize model.predicted_position_error_m |
| Canonical comparison | Minimize mujoco.position_error_m; frozen evaluator decides PASS/TASK_FAILED |
| Controller | Legacy C1 open loop only; no C2 |
| Search | Deterministic seed 17; total budget 12; MuJoCo sub-budget 5 |
| Repair | Disabled; iteration budget 0; no actions or route escalation |
| Sensitivity | Lower/baseline/upper length observations reused from screening |
| Scientific scope | Current legacy_v1_surrogate simulator study only; no real-robot validation |

The existing grammar authorization mechanism gained a file-specific authorization
entry for this policy. General `optimization` entries remain denied. The validator
reloads and checks policy/approval/grammar/input hashes for every candidate, permits
only the selected bounded field and rejects every other DesignSpec mutation.
Copying this policy to a different file grants no optimization permission. This
does not expand the general design capability envelope or change TaskContract.

## FORMAL OPTIMIZATION RESULT

[Optimization summary](../runs/20260912T061721_390989Z_61a4f4f8/optimization_summary.json),
[candidate comparison](../runs/20260912T061721_390989Z_61a4f4f8/candidate_comparison.json),
and [complete evaluation history](../runs/20260912T061721_390989Z_61a4f4f8/optimization_history.jsonl).

The existing deterministic algorithm screened baseline, lower endpoint, upper
endpoint and four seed-17 samples. It then validated baseline first, followed by
the four best remaining M1 candidates. There were seven distinct designs and
twelve evaluation records: seven M1-only evaluations followed by five complete
M1/C1/MuJoCo evaluations. The M1 plan is regenerated in each complete validation;
its saved error and RobotIR identity agree with the corresponding screening run.
The inherited M0 necessary reach gate still runs inside each route; M1 alone ranks
candidates. No physics or controller parameter was tuned.

| Screening ID | Exact length (m) | M1 predicted error (m) | MuJoCo actual error (m) | Canonical task result | MuJoCo evaluation ID |
| --- | --- | --- | --- | --- | --- |
| candidate_0000 | 0.4 | 0.08714456960728613 | 0.17116166894090315 | TASK_FAILED | candidate_0007 |
| candidate_0001 | 0.35 | 0.040842775152800576 | 0.1405118443004635 | TASK_FAILED | candidate_0008 |
| candidate_0002 | 0.45 | 0.13299498539352073 | Not executed | NOT_RUN | — |
| candidate_0003 | 0.4021983909712493 | 0.08917054441120133 | 0.17269060861689942 | TASK_FAILED | candidate_0010 |
| candidate_0004 | 0.4306690777118679 | 0.11532679611798849 | 0.19346037697824503 | TASK_FAILED | candidate_0011 |
| candidate_0005 | 0.44604947743238765 | 0.1293905704322603 | Not executed | NOT_RUN | — |
| candidate_0006 | 0.37896253777644656 | 0.06771393347954811 | 0.157204687864888 | TASK_FAILED | candidate_0009 |

Every M1-only run terminates MODEL_ONLY; its prediction is not a canonical verdict.
The NOT_RUN rows have no fabricated MuJoCo outcome. All five actual validations
failed the frozen task tolerance. Parent experiment PASS denotes successful
orchestration, not robot task success.

Best observed canonical improvement over baseline: 0.030649824640439638 m
(approximately 17.91%). This is a comparison within the current surrogate,
not evidence of real-robot improvement or a causal physics explanation.

All child runs refer back to parent `20260912T061721_390989Z_61a4f4f8` through
experiment_context.json. The parent stores each child's manifest hash and complete
artifact hash map in candidate_NNNN_run_reference.json. Design hashes link repeated
evaluations without relying on rounded length values.

| Design ID | M1 child run | MuJoCo child run |
| --- | --- | --- |
| 0000 | [071f4898](../runs/20260912T061721_692722Z_071f4898/run.json) | [5c20f850](../runs/20260912T061729_639301Z_5c20f850/run.json) |
| 0001 | [55515344](../runs/20260912T061723_030824Z_55515344/run.json) | [33cda1c5](../runs/20260912T061731_644930Z_33cda1c5/run.json) |
| 0002 | [39802ab8](../runs/20260912T061724_271464Z_39802ab8/run.json) | Not executed |
| 0003 | [1fbb9514](../runs/20260912T061725_357083Z_1fbb9514/run.json) | [12863423](../runs/20260912T061735_721753Z_12863423/run.json) |
| 0004 | [42aefce1](../runs/20260912T061726_465780Z_42aefce1/run.json) | [cbc69d3a](../runs/20260912T061737_723153Z_cbc69d3a/run.json) |
| 0005 | [e79eb707](../runs/20260912T061727_490915Z_e79eb707/run.json) | Not executed |
| 0006 | [5c58cfa4](../runs/20260912T061728_592954Z_5c58cfa4/run.json) | [9fd92fde](../runs/20260912T061733_671438Z_9fd92fde/run.json) |

| Design ID | RobotIR SHA-256, identical across its M1/MuJoCo evaluations |
| --- | --- |
| 0000 | b31229e81d67798b02e367192cec10dd899d4f9ebb7a79cb3b1108c3eb09d33f |
| 0001 | ef794f7b3a2b0c73eba763bc88fe4bafc8d816e65f8a310538f0fcc52062490d |
| 0002 | 77cbea2f59a31972ae6b5ea6643c47de1835e9dc01eeb0be925c4996ed6f55fd |
| 0003 | 0ea5654fa5fa2fe404446ddac2c73d0ff1c6b9e4ce35116a6f41589752ca333b |
| 0004 | 9efa159f2dbd0a15e05da9c33afbded5623e6abfa657935613cbbc0478bc72fe |
| 0005 | b5a6980ec120e0a33ea43c389029829e967db22cb4fd84d369cba12e41da2210 |
| 0006 | fe5bf8b27eb37b456f7433c035cadf2fbd6006a6fe0f7da1db0c6f85d29e1b8f |

## BOUNDARY RESULT

**BOUNDARY_OPTIMUM_OBSERVED**: both best screened and best canonically evaluated
designs use the authorized lower bound, total_length_m=0.35. The range was not
expanded. This is the best sampled candidate, not a proof of continuous/global
optimality. Human decides whether to authorize another range.

Sensitivity reuses lengths 0.35/0.4/0.45 and respective M1 errors
0.040842775152800576/0.08714456960728613/0.13299498539352073 m. Error increased
across those three sampled lengths. No extra evaluations were executed for this
observation; causal attribution remains UNKNOWN. The 0.45 m endpoint was not
selected for MuJoCo, so no canonical upper-endpoint trend is claimed.

## DEBUG ARTIFACTS

Representative best-candidate debug outputs, all **DEBUG_ONLY / NON_CANONICAL**:

- [MATLAB PCC figure](../runs/20260912T061731_644930Z_33cda1c5/debug/matlab_pcc.png)
- [Trajectory JSON](../runs/20260912T061731_644930Z_33cda1c5/debug/trajectory.json)
- [Tip error](../runs/20260912T061731_644930Z_33cda1c5/debug/tip_error.png)
- [Tip XYZ](../runs/20260912T061731_644930Z_33cda1c5/debug/tip_xyz.png)
- [Tendon tracking](../runs/20260912T061731_644930Z_33cda1c5/debug/tendon_tracking.png)
- [Actuator force](../runs/20260912T061731_644930Z_33cda1c5/debug/actuator_force.png)
- [qpos/qvel](../runs/20260912T061731_644930Z_33cda1c5/debug/qpos_qvel.png)
- [Status and exclusion labels](../runs/20260912T061731_644930Z_33cda1c5/debug/status.json)
- [Window development clearance figure](../runs/20260912T061718_893590Z_626783b6/debug/matlab_clearance.png)

All twelve experiment children have MATLAB PCC figures; the five simulated children
also have 1000-sample trajectories and all five Python plots. Every retained debug
status reports zero errors. Debug files do not enter Gate, optimizer ranking, Skill
admission or causal attribution. The evidence admission API explicitly rejects
debug/ references. No Skill was admitted or changed.

Samples copy each original mj_step's force/tendon work arrays. Time, qpos/qvel and
independent tip kinematics describe the post-integration state; force/tendon arrays
describe the last dynamics evaluation. No extra forward call is inserted to make
them appear simultaneous. Canonical final arrays still come from the existing
final mj_forward. This timing distinction is declared in the schema and artifacts.

Nested debug artifacts are included in run.json's SHA-256 map. All parent/child
artifact hashes, source-snapshot entries and traces were validated. Hashes record
file integrity, not authentication against a writer who could replace a whole run.

| Retained file | SHA-256 |
| --- | --- |
| round3_1_validation.json | 8659852d59556828062adfedcaa02f624ea62e15da0a9b7b6666e398cb84c4a5 |
| Validation run.json | 3eff1a9347c03a7cebee97fa8c5d615e923e298bf78b770568b8d6711186a9a4 |
| Formal experiment run.json | 3d2f1ec53242306fdadbed7773aaa8a7246ac32e58dd71084dc99b7e473d258b |
| Human ExperimentPolicy | affa39dcee689e798a79522b5821efe63c0bba07d2b5e9c598585ef7e2557b13 |

## REGRESSION RESULT

| Route | PCC predicted error (m) | MuJoCo actual error (m) | Status | Artifacts / trace events / Gates |
| --- | --- | --- | --- | --- |
| Before observability | 0.08714456960728613 | 0.17116166894090315 | TASK_FAILED | 32 / 73 / 9 |
| Default headless after | 0.08714456960728613 | 0.17116166894090315 | TASK_FAILED | 32 / 73 / 9 |
| Debug enabled | 0.08714456960728613 | 0.17116166894090315 | TASK_FAILED | 41 / 73 / 9 |
| Debug + real live viewer | 0.08714456960728613 | 0.17116166894090315 | TASK_FAILED | 41 / 73 / 9 |

Before run: `20260912T060423_031774Z_227d4d63` (captured before observability code
changes, after the file-scoped authorization was added). After default run:
`20260912T061708_050220Z_61fc557f`. Debug run:
`20260912T061709_063851Z_ccaaf7e5`. Real live viewer run:
`20260912T061714_261562Z_c5516cf8`.

For each comparison, all model and simulation metrics are exactly equal after
excluding run-identity comparison_context. Ten numerical/input artifacts are
byte-identical: task.yaml, environment.yaml, design_input.yaml, design_final.yaml,
robot_ir.yaml, physics.yaml, robot.xml, controller.json, tendon_command.json and
simulation_state.json. No timestep debug events were added to trace.jsonl.

The window fixture remains NON_CANONICAL / DEVELOPMENT_ONLY. Its retained debug
run has 45 artifacts, 86 events and 15 Gates. Real MATLAB regression also compares
window debug on/off numerics exactly; no benchmark promotion occurred.

Git diff confirms no changes to tasks/, benchmarks/, physics_contracts/, metrics/,
schemas/gate.py, baseline DesignSpec, simulator/run settings, controllers/, or
the three existing numerical MATLAB tools. Harness/MuJoCo code changes add only
optional observations; canonical evaluator/Gate logic is unchanged.

## TEST RESULT

Python 3.11.16 at `C:\Users\gugugaga\miniconda3\envs\softagent\python.exe`;
MATLAB 24.1.0.2537033 (R2024a); MuJoCo 3.13.0; Matplotlib 3.11.1.

| Check | Result |
| --- | --- |
| Existing full suite, real MATLAB enabled | 110 passed, zero skipped; 96.694 s |
| Final full suite, real MATLAB enabled | **120 passed, zero skipped; 126.224 s** |
| New coverage | Disabled baseline; trajectory schema/values; all-step observation versus original buffers; malicious/failing viewer; MATLAB ToolResult isolation; headless mode; Windows paths; exact policy; every non-length mutation rejected; seeded replay; provenance; boundary/no expansion; artifact hashes and debug admission exclusion |
| Retained baseline/debug/live-viewer regression | PASS; exact original metrics and state |
| Formal experiment | 12 evaluations, 5 MuJoCo; all child/source hashes and traces valid |
| Schema export drift / git diff --check | PASS |

Commands used (PowerShell):

```powershell
$env:SOFTROBOT_TEST_MATLAB='1'
$env:MPLCONFIGDIR='D:\softrobot-agent\runs\.matplotlib'
& 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe' -m unittest discover -s tests -q
& 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe' examples/run_reach_pipeline.py
& 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe' -m tools.export_contract_schemas
& 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe' -m unittest tests.test_round3_1 -v
& 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe' examples/validate_round3_1.py --before 20260912T060423_031774Z_227d4d63 --visualize
git diff --check
```

The validation script was executed once after the final full suite passed; it
runs regression before spending the formal experiment budget. Deterministic
end-to-end search replay is tested with the existing TEST_ONLY fixture and is
not an additional formal search. Unit tests use fake viewers, requiring no desktop;
the separate retained validation exercised the real viewer.

The initial sandbox precheck hit the previously documented Windows temporary-dir
permission problem. Reviewed execution outside that sandbox passed the full suite.
Its 94 verified-empty temporary directories were removed within checked workspace
roots, without recursive deletion. Intermediate new tests exposed the existing
native MuJoCo Windows non-ASCII model-path limitation; simulation tests use paths
with spaces, while MATLAB plotting separately passes Chinese output-directory
tests. The native MuJoCo loader behavior was not changed. A test initially rejected
all occurrences of qpos in trace, including legitimate pre-existing diagnostic
peaks; the final test correctly verifies that the complete event-operation sequence
is unchanged and no per-step debug events are added. Numerical baseline assertions
were never relaxed.

## NEXT HUMAN DECISION

Decide whether the observed lower-bound candidate warrants a separately authorized
length range or another explicit experiment. Current authorization stops at 0.35 m.
No additional variable, expanded bound, C2 controller, repair, physics tuning or
causal attribution has been approved automatically. The current best design still
fails the frozen reach task. No real-robot physical validation is claimed.
