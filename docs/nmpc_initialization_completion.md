# Completed bounded NMPC initialization investigation

The single-factor return-budget experiment is complete. It changed only
`feasible_return.budget_s` from 15 to 30 seconds; CPU30s, iteration120,
minimum5s, relative improvement .1, tolerance1e-6, feasibility1e-5 and all
physical/task settings stayed fixed. Reports retain the actual policy and raw
termination. A solve that first hits another condition cannot establish that
extending the return budget is ineffective; no other ceiling is raised automatically.

The model received both new scientific results and submitted native STOP,
choosing no control revision or new simulation. Original decisions and feedback
are preserved separately from factual corrections. This is a completed bounded
investigation with a negative selected-plan result, not a successful controller.

| Same-state comparison at update20 / simulated .20s | 15s budget | 30s budget |
|---|---:|---:|
| Actual stop | budget_best_feasible | budget_best_feasible |
| Raw solver termination | User_Requested_Stop | User_Requested_Stop |
| Solve wall time | 15.583s | 30.685s |
| Iterations | 18 | 37 |
| Raw returned objective | 22.3060 | 18.3768 |
| Raw scaled dynamics violation | .0426871 | .000953761 |
| Retained least-infeasible violation | .0138443 | .000714589 |
| Selected iteration | 0 | 0 |
| Selected objective | 1697.08575 | 1697.08575 |
| Selected violation | 2.93e-14 | 2.93e-14 |
| Selected first six tensions | .2N each | .2N each |

The longer run made raw objective/residual progress, but the recorded improved
candidates still violate dynamics equalities above1e-5. Initial-state consistency
and variable bounds passed. Both runs retained the feasible initialization.
The local selected trajectory is identical: predicted error .18335m and speed .50479m/s
at .21s, error .18045m and speed .36788m/s at .30s. The .35s deadline is outside this
prediction horizon; candidate predicted motion is not a simulator acceptance result.
The feasible initialization is numerically acceptable but poor for this task.

The pair uses one recorded projected state, preceding applied input, absolute
prediction-node time and effective horizon, separate mutable workspaces and a
new constant-previous-input seed with regenerated states. It is not historical
warm replay. The upfront same-time projection check found4.3975mm tip and
.021396m/s velocity-vector differences between reduced kinematics and the saved
full simulator state/Jacobian. It does not isolate a dominant cause or replace
next-step prediction-error analysis.

The [35-update timeline](../evidence/nmpc_initialization_20261010/saved_timeline.json)
preserves execution `21b607607bf442a6b6d9494dda897ea8`, owner
`casadi-nmpc-research-20261010-cl-afc46a23b0c9`, candidate hashes and immutable
source evidence, without recreating the simulation. Holding first enters the
prediction at .20s; horizons shorten at .26s; applied input first changes at .30s.
Historical30 initialization and5 noninitialization selections are distinct from
exception fallback. Old terminal error95.5mm, holding maximum error193.2mm and
speed3.25m/s fail sampled task acceptance. Synchronous solve latency did not skip
virtual-time actions. Missing historical warm vectors/objectives/rejected iterates
prevent unique historical reconstruction.

| New work | Actual | Ceiling |
|---|---:|---:|
| Representative states | 1 | 2 |
| Pairs / local NLP attempts | 1 / 2 | 2 / 4 |
| MuJoCo launches / internal NMPC solves | 0 / 0 | 1 launch |
| Provider sends / public calls | 13 / 19 | 16 / 64 |
| Scientific wall charged, including prep/failures/checks | 114.401s | 3600s |
| Pair complete prep/solve/verification/instrumentation | 78.948s | 300s |
| Host receipt wall charge for that pair | 81.437s | 300s authorized |
| Activity start through sealed closeout, including engineering | 3130.455s | 21600s |
| Full-horizon NLP / BDF / hardware / other models | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |

A reporting defect inherited the native generic60s timeout although the authorized
pair ceiling was300s. Both numerical outputs and snapshots had already been
sealed. Commit `9ab5022a008825f222b761d78e5c1e339945335a` repaired allowance
propagation and migrated the same activity; the sealed output was recovered with
zero numerical retries and no clock/counter reset. The original failed receipt
remains failed. The existing300s operation ceiling is now passed correctly;
solver caps and other authorization limits were not increased.

The model's final STOP correctly read the recovered objective/residual/selection
facts but included inaccurate wording about a redundant rerun and CPU/wall time,
and overgeneralized retained iterates. The separate
[post-STOP correction](../evidence/nmpc_initialization_20261010/post_stop_factual_correction.json)
records that there was only one pair, CPU time differs from wall time, both actual
stops were the return policy, and retained candidates do not cover all unseen
iterates. The original model STOP is unchanged. No unique/dominant cause,
closed-loop improvement, real-time/hardware transfer or global conclusion follows.

Ten focused contracts/fixtures passed. The original timer record7.091s and the
additional reporting-repair timer2.857s are retained in
[focused checks](../evidence/nmpc_initialization_20261010/focused_checks.json).
Actual recovery verified unchanged local/pair/provider/backend counters, retained
failed receipt and implementation compatibility. No full suite or extra numerical
campaign was used. The existing Python3.11.16/CasADi3.7.2/SciPy1.17.1/MuJoCo3.13.0/
Strands1.59.0/Harness0.2.0 environment and lock were reused without upgrades.

The [scientific summary](../evidence/nmpc_initialization_20261010/scientific_summary.json),
raw numerical outputs, initial/returned/selected/rejected snapshots, original
plans/tool feedback, ledger/events and immutable archive/manifest make the result
reviewable. The [case draft](../memory/nmpc_initialization_case_draft.json) and
[recommendation-only procedure](nmpc_initialization_procedure.md) stay drafts:
[actual legacy admission errors](../evidence/nmpc_initialization_20261010/legacy_admission_check.json)
show the mismatch between platform EvidenceRef/SQLite/export provenance and older
ArtifactReference/finalized-run contracts. No validation, human approval or
provenance migration is fabricated.

Direct chat authorization resolved the earlier automatic-review rejections for
DeepSeek payload and the ordinary push to the specified branch. Their zero-work
checkpoint is historical, not the final counts. Source commit remains
`97aced4e75a6c3c6fecd851ae5bb0dc6be112f18`; the isolated delivery branch is
`feat/nmpc-initialization-diagnosis`. Final remote SHA verification is reported
with delivery; source/implementation/delivery commit roles remain separate.
