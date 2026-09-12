# ROUND 3 DETERMINISTIC CLOSEOUT RESULT

workflow_status: **COMPLETED**; canonical_task_status: **TASK_FAILED**.
scientific_status: **PHYSICS_MODEL_REFINEMENT_REQUIRED**; failure_attribution: **UNKNOWN**.

The frozen reach target, 0.01 m tolerance, 1000 steps / 2 s, gravity, initial state, inner servo and unilateral limits remain unchanged. New permission covers this C2 experiment and independent analysis only; see [authorization](../configs/experiments/round3_closeout_authorization.yaml).

Execution commit: `65b8d2acd05a4df72897362764fec0cabdbd9d1d`. Parent: `20260912T081952_082199Z_ce91267e`. Delivery commit is the commit containing this report; it is not the execution revision.

Best observed error: **0.100496404619 m**. Improvement vs baseline: 0.070665264322 m; vs historical-best design re-evaluated on this revision: 0.008424211393 m. improvement_observed=true.

Stop: `TWO_IMPROVEMENT_ROUNDS_EXHAUSTED`. Finite samples are not global optimization or real robot validation.

## All executed candidates

| Attempt / run | Stage / route | L m | routing r m | tendons | body r m | segments / sections | M1 error m | actual error m | status |
|---|---|---:|---:|---:|---:|---|---:|---:|---|
| attempt_000 / 20260912T081954_876575Z_225c35c3 | A / M1 / C1 | 0.4 | 0.015 | 4 | 0.02 | 8 / 1 | 0.08714456960728613 | None | NOT_RUN |
| attempt_001 / 20260912T082002_895497Z_10d68758 | A / MUJOCO / C1 | 0.4 | 0.015 | 4 | 0.02 | 8 / 1 | 0.08714456960728613 | 0.17116166894090315 | TASK_FAILED |
| attempt_002 / 20260912T082011_234469Z_8dc317e1 | A / M1 / C1 | 0.29 | 0.018 | 8 | 0.02 | 8 / 1 | 0.015221644271566406 | None | NOT_RUN |
| attempt_003 / 20260912T082019_266844Z_7bb2514a | A / MUJOCO / C1 | 0.29 | 0.018 | 8 | 0.02 | 8 / 1 | 0.015221644271566406 | 0.1089206160124638 | TASK_FAILED |
| attempt_004 / 20260912T082027_627792Z_dc4dcf37 | A / M1 / C1 | 0.30623771682 | 0.015 | 4 | 0.02 | 8 / 1 | 4.619873470669785e-08 | None | NOT_RUN |
| attempt_005 / 20260912T082035_720275Z_b7f83a9d | A / MUJOCO / C1 | 0.30623771682 | 0.015 | 4 | 0.02 | 8 / 1 | 4.619873470669785e-08 | 0.12331917480644342 | TASK_FAILED |
| attempt_006 / 20260912T082044_076323Z_54e7e92d | A / M1 / C1 | 0.29 | 0.018 | 4 | 0.02 | 8 / 1 | 0.015221644271566406 | None | NOT_RUN |
| attempt_007 / 20260912T082052_028987Z_c5741afb | A / MUJOCO / C1 | 0.29 | 0.018 | 4 | 0.02 | 8 / 1 | 0.015221644271566406 | 0.11521091964058727 | TASK_FAILED |
| attempt_008 / 20260912T082100_416314Z_ec81e296 | B / M1 / C1 | 0.282 | 0.018 | 8 | 0.02 | 8 / 1 | 0.022733528534614602 | None | NOT_RUN |
| attempt_009 / 20260912T082108_437887Z_66f0446d | B / M1 / C1 | 0.286 | 0.018 | 8 | 0.02 | 8 / 1 | 0.018976576868270284 | None | NOT_RUN |
| attempt_010 / 20260912T082116_547914Z_92046480 | B / M1 / C1 | 0.294 | 0.018 | 8 | 0.02 | 8 / 1 | 0.011468754781987176 | None | NOT_RUN |
| attempt_011 / 20260912T082124_661631Z_af0aecb9 | B / M1 / C1 | 0.3 | 0.018 | 8 | 0.02 | 8 / 1 | 0.005843304875743583 | None | NOT_RUN |
| attempt_012 / 20260912T082132_683770Z_25849aba | B / M1 / C1 | 0.30623771682 | 0.018 | 8 | 0.02 | 8 / 1 | 4.619873470669785e-08 | None | NOT_RUN |
| attempt_013 / 20260912T082140_662719Z_5370b777 | B / M1 / C1 | 0.32 | 0.018 | 8 | 0.02 | 8 / 1 | 0.012873503520533085 | None | NOT_RUN |
| attempt_014 / 20260912T082148_951989Z_27c0f4e9 | B / M1 / C1 | 0.29 | 0.006 | 8 | 0.02 | 8 / 1 | 0.015221644271566406 | None | NOT_RUN |
| attempt_015 / 20260912T082156_991028Z_8509a9a4 | B / M1 / C1 | 0.29 | 0.012 | 8 | 0.02 | 8 / 1 | 0.015221644271566406 | None | NOT_RUN |
| attempt_016 / 20260912T082205_194147Z_833773ea | B / M1 / C1 | 0.29 | 0.018 | 3 | 0.02 | 8 / 1 | 0.015221644271566406 | None | NOT_RUN |
| attempt_017 / 20260912T082213_187359Z_182333ba | B / M1 / C1 | 0.29 | 0.018 | 5 | 0.02 | 8 / 1 | 0.015221644271566406 | None | NOT_RUN |
| attempt_018 / 20260912T082221_232154Z_437e3d3b | B / M1 / C1 | 0.29 | 0.015 | 6 | 0.02 | 8 / 1 | 0.015221644271566406 | None | NOT_RUN |
| attempt_019 / 20260912T082229_262160Z_d54e7108 | B / M1 / C1 | 0.29 | 0.015 | 7 | 0.02 | 8 / 1 | 0.015221644271566406 | None | NOT_RUN |
| attempt_020 / 20260912T082237_244670Z_0ca6475d | B / M1 / C1 | 0.301835389 | 0.016066908 | 5 | 0.02 | 8 / 1 | 0.0041234320787216895 | None | NOT_RUN |
| attempt_021 / 20260912T082245_189645Z_fcf788fd | B / M1 / C1 | 0.293005764 | 0.015661074 | 8 | 0.02 | 8 / 1 | 0.012401377112993753 | None | NOT_RUN |
| attempt_022 / 20260912T082253_135666Z_35304f38 | B / M1 / C1 | 0.302527045 | 0.010782765 | 3 | 0.02 | 8 / 1 | 0.0034754231758036993 | None | NOT_RUN |
| attempt_023 / 20260912T082301_193025Z_f4cf7a04 | B / M1 / C1 | 0.291458318 | 0.016151861 | 6 | 0.02 | 8 / 1 | 0.013853179765479774 | None | NOT_RUN |
| attempt_024 / 20260912T082309_237387Z_a964e486 | B / MUJOCO / C1 | 0.30623771682 | 0.018 | 8 | 0.02 | 8 / 1 | 4.619873470669785e-08 | 0.1102010144381975 | TASK_FAILED |
| attempt_025 / 20260912T082317_602809Z_2b8bb83b | B / MUJOCO / C1 | 0.29 | 0.006 | 8 | 0.02 | 8 / 1 | 0.015221644271566406 | 0.14301422904589867 | TASK_FAILED |
| attempt_026 / 20260912T082325_996285Z_9be26cea | B / MUJOCO / C1 | 0.29 | 0.018 | 3 | 0.02 | 8 / 1 | 0.015221644271566406 | 0.12276808997048652 | TASK_FAILED |
| attempt_027 / 20260912T082334_275645Z_892da213 | B / MUJOCO / C1 | 0.302527045 | 0.010782765 | 3 | 0.02 | 8 / 1 | 0.0034754231758036993 | 0.14639227761223184 | TASK_FAILED |
| attempt_028 / 20260912T082342_591463Z_c92bb787 | C / MUJOCO / C2 | 0.4 | 0.015 | 4 | 0.02 | 8 / 1 | 0.08714456960728613 | 0.15318050153888021 | TASK_FAILED |
| attempt_029 / 20260912T082350_852614Z_067c75d9 | C / MUJOCO / C2 | 0.29 | 0.018 | 8 | 0.02 | 8 / 1 | 0.015221644271566406 | 0.1012090754169927 | TASK_FAILED |
| attempt_030 / 20260912T082359_330498Z_2adf85fd | C / MUJOCO / C2 | 0.30623771682 | 0.015 | 4 | 0.02 | 8 / 1 | 4.619873470669785e-08 | 0.11336211447962491 | TASK_FAILED |
| attempt_031 / 20260912T082408_355296Z_7d6b7d3f | D / M1 / C1 | 0.29 | 0.016 | 8 | 0.02 | 8 / 1 | 0.015221644271566406 | None | NOT_RUN |
| attempt_032 / 20260912T082416_295290Z_1df4b315 | D / M1 / C1 | 0.29 | 0.018 | 7 | 0.02 | 8 / 1 | 0.015221644271566406 | None | NOT_RUN |
| attempt_033 / 20260912T082424_288079Z_305a1161 | D / MUJOCO / C1 | 0.294 | 0.018 | 8 | 0.02 | 8 / 1 | 0.011468754781987176 | 0.10905302171139841 | TASK_FAILED |
| attempt_034 / 20260912T082432_673227Z_0d8757b2 | D / MUJOCO / C2 | 0.294 | 0.018 | 8 | 0.02 | 8 / 1 | 0.011468754781987176 | 0.10080167338849678 | TASK_FAILED |
| attempt_035 / 20260912T082441_448735Z_b66ea500 | D / M1 / C1 | 0.298 | 0.018 | 8 | 0.02 | 8 / 1 | 0.007717932810237183 | None | NOT_RUN |
| attempt_036 / 20260912T082449_515942Z_dce6742a | D / M1 / C1 | 0.294 | 0.016 | 8 | 0.02 | 8 / 1 | 0.011468754781987176 | None | NOT_RUN |
| attempt_037 / 20260912T082502_824834Z_2079a07c | D / M1 / C1 | 0.294 | 0.018 | 7 | 0.02 | 8 / 1 | 0.011468754781987176 | None | NOT_RUN |
| attempt_038 / 20260912T082510_835553Z_9e140aae | D / MUJOCO / C1 | 0.298 | 0.018 | 8 | 0.02 | 8 / 1 | 0.007717932810237183 | 0.10930748356023394 | TASK_FAILED |
| attempt_039 / 20260912T082519_263560Z_eb328077 | D / MUJOCO / C2 | 0.298 | 0.018 | 8 | 0.02 | 8 / 1 | 0.007717932810237183 | 0.10049640461909048 | TASK_FAILED |
| attempt_040 / 20260912T082527_669714Z_ad1b8084 | E / MUJOCO / C2 | 0.298 | 0.018 | 8 | 0.02 | 8 / 1 | 0.007717932810237183 | 0.10049640461909048 | TASK_FAILED |

Every row uses legacy_v1_surrogate; model values are MODEL/SCREENING evidence, actual values are SIM_TO_SIM canonical surrogate evidence.

## Same-design C1/C2 comparisons

| L / r / count | C1 error m | C2 error m | C1 minus C2 m | Attempts |
|---|---:|---:|---:|---|
| 0.4 / 0.015 / 4 | 0.171161668941 | 0.153180501539 | 0.017981167402 | attempt_001 / attempt_028 |
| 0.29 / 0.018 / 8 | 0.108920616012 | 0.101209075417 | 0.007711540595 | attempt_003 / attempt_029 |
| 0.3062377168199977 / 0.015 / 4 | 0.123319174806 | 0.113362114480 | 0.009957060327 | attempt_005 / attempt_030 |
| 0.294 / 0.018 / 8 | 0.109053021711 | 0.100801673388 | 0.008251348323 | attempt_033 / attempt_034 |
| 0.298 / 0.018 / 8 | 0.109307483560 | 0.100496404619 | 0.008811078941 | attempt_038 / attempt_039 |

| Attempt | final max tendon tracking error m | peak force N | max-pull limit sampled | C2 updates / clipped |
|---|---:|---:|---|---|
| attempt_001 | 0.006847228877633504 | 18.015834197031495 | False | 0 / 0 |
| attempt_003 | 0.0025518938854275364 | 19.12128011044814 | False | 0 / 0 |
| attempt_005 | 0.005271353485709451 | 16.21258033258232 | False | 0 / 0 |
| attempt_028 | 0.008626680792592156 | 18.11583419703146 | False | 50 / 50 |
| attempt_029 | 0.0031429861642268686 | 19.221280110448106 | False | 50 / 1 |
| attempt_030 | 0.006488584418934185 | 16.312445967284987 | False | 50 / 0 |
| attempt_033 | 0.002579883717259479 | 19.20250877660345 | False | 0 / 0 |
| attempt_034 | 0.003192967321418605 | 19.302508776603474 | False | 50 / 1 |
| attempt_038 | 0.0026082739185862014 | 19.284388198888735 | False | 0 / 0 |
| attempt_039 | 0.0032445591053286704 | 19.3843881988887 | False | 50 / 2 |

Paired effects compare identical design/initial PCC command/initial state/physics/numerics. Joint design and controller effects are separate. C2 shape mismatch is NOT_APPLICABLE_TIME_VARYING_COMMAND. Improved feedback does not identify the sole cause of previous failures.

Relative to historical-best C1, the joint improvement is 8.424211 mm. At fixed
historical design C2 accounts for an observed 7.711541 mm improvement; the two
subsequent length changes under fixed C2 add 0.712671 mm. At the final design,
C2 improves over same-design C1 by 8.811079 mm. The final design with C1 is actually
0.386868 mm worse than historical-best C1; these are conditional paired observations,
not a claim that changing length alone improved all controllers.

## Decisions and stop

- `decision_000.json`: `B_GEOMETRIC_DIVERSITY` read 16 persisted evidence files before the next action; hashes, observations and remaining budgets are in the bundle.
- `decision_001.json`: `D_TASK_FAILED_LOCAL_NEIGHBORS` read 2 persisted evidence files before the next action; hashes, observations and remaining budgets are in the bundle.
- `decision_002.json`: `D_MODEL_RANK_PAIRED_ACTUAL` read 4 persisted evidence files before the next action; hashes, observations and remaining budgets are in the bundle.
- `decision_003.json`: `D_TASK_FAILED_LOCAL_NEIGHBORS` read 2 persisted evidence files before the next action; hashes, observations and remaining budgets are in the bundle.
- `decision_004.json`: `D_MODEL_RANK_PAIRED_ACTUAL` read 3 persisted evidence files before the next action; hashes, observations and remaining budgets are in the bundle.
- `decision_005.json`: `E_INDEPENDENT_REPRODUCTION` read 1 persisted evidence files before the next action; hashes, observations and remaining budgets are in the bundle.

## Evidence and budgets

41 candidate attempts: 25 M1 routes and 16 MuJoCo routes; 0 retries, 2 exact cache reads. Backend calls: `{"analyze_workspace": 41, "plan_pcc_reach": 41, "pcc_centerline": 41, "compile_mujoco": 16, "run_task": 16}`.

The compressed [portable evidence bundle](evidence/round3_closeout_evidence.tar.xz) contains all referenced numerical artifacts, source snapshots, manifests, trajectories, frozen plan, decisions and historical raw sources. Run `python examples/run_round3_closeout.py audit docs/evidence/round3_closeout_evidence.tar.xz` without MATLAB/MuJoCo execution.

Numerical reproduction checks full saved trajectory plus final state, tip, lengths and forces at atol=rtol=1e-9; these are reproduction tolerances, not task tolerances.

See [capability and parameter matrix](round3_closeout_tools.md) and [validation record](round3_closeout_validation.md) for the independent mechanics tests, recovery demonstration, damaged-copy audit and backend accounting.

## Limitations / next phase

The independent analysis parent `20260912T082624_505318Z_6c8bf663` completed three
static solves using observed final tensions. Three observed-force dynamic replays
returned domain failures; no completed dynamic prediction is claimed for these
inputs. Development rest/decay/tendon-pulse/force-pulse cases did complete. Main
trajectories contain contact, which the reduced model omits. It cannot currently
predict this main simulation under equivalent boundary conditions. Static results
are not C1 length-servo predictions or estimates of 2-second transient accuracy.

Validation: one full regression, 139 passed, zero skipped, real MATLAB enabled.
Development: four MuJoCo rollouts and 21 mechanics solves, including three explicit
domain failures. Focused persistence/authority tests and two post-execution recovery
tests passed. Offline audit recomputes 16 canonical metrics, verifies five C1/C2
pairs, six saved decisions, budgets, per-controller incumbents and reproduction.

Three unused hello-example sources indexed by the plan were initially absent from
run snapshots. The delivery auditor/package includes their exact hash-matching
originals as auxiliary planned sources; no sealed run was changed. A later recovery
path fix routes interrupted MuJoCo retries to E. These changes do not alter any
executed simulation; all formal results bind execution commit 65b8d2a. The original
untracked user prompt was preserved, explaining the recorded dirty flag despite
committed execution sources.

All physical parameters remain uncalibrated. The independent planar single-mode model omits contact, out-of-plane bending, shear, extension and torsion. Its static equilibria are not equivalent to a 2-second transient final pose. Synthetic stiffness recovery validates software under known assumptions, not physical identifiability. Next steps require measured mass/inertia, tendon/actuator response, shape observations and an approved calibrated PhysicsContract. A future restricted Agent can use these bounded tools after executor isolation and write permissions are enforced; no LLM or hardware integration is claimed.
