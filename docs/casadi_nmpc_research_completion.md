# Candidate-to-NMPC research completion, 2026-10-10

The bounded research workflow completed with an **accepted native STOP**.
The model chose **closed-loop evaluation with default weights → STOP**.
The complete saved-candidate → resolved configuration → NMPC → MuJoCo →
evaluation/profile → model-feedback path executed. The tested robot/controller
**failed task acceptance**; numerical plan delivery and task success remain separate.

Fetched source was `056707b4499327ad944df8b7f25460e79dabdee1`, unchanged from
the requested source. The isolated branch is `feat/casadi-nmpc-research`; live
dispatch was bound to implementation `63620abf`. The existing Windows environment
was reused unchanged. The [runbook](casadi_nmpc_research_runbook.md) and
[frozen specification](../examples/casadi_nmpc/specification.json) record the action
menu, physics, task, clocks and ceilings. The start at 19:12:47 Asia/Shanghai
includes engineering; no historical STOP was reopened or allowance reset.

The first scientific choice was the model's, after four provider sends that read
imported evidence. Its [original plan](../evidence/casadi_nmpc_research_20261010/plan_00_closed_loop.json)
selected candidate `0e16077e…`, the initial 22-iteration converged export, with
`d=0`, lengths `[0.16, 0.11]` m and holding/terminal speed weights `0.05 / 0.10`.
No structural or control revision was executed. The adapter read exact values and
source configuration from immutable candidate/checkpoint provenance, materialized
the full configuration, then used `changes={}`. Named ordering, units, 12 reduced
coordinates, 24 state entries, 48 backend joint positions and six tendon inputs
were validated. All physical initial positions and velocities were zero; 0.2 N
pretensions were numerical guesses. The old open-loop schedule was not used as
the NMPC reference or applied command sequence.

| Closed-loop result | Actual | Frozen limit |
|---|---:|---:|
| Terminal position error | 0.095524879 m | 0.01 m |
| Holding maximum position error | 0.193152079 m | 0.01 m |
| Holding maximum speed | 3.249830481 m/s | 0.02 m/s |
| Simulated duration / applied updates | 0.35 s / 35 | Complete horizon |
| Holding coverage | Six samples, including 0.35 s | Inclusive 0.01 s grid |
| Applied tension range / bound violation | 0–8 N / 0 N | 0–8 N |

Evaluation validity, complete execution, force bounds, solver-error check and
holding coverage passed. Terminal/task, holding position and holding speed checks
failed, producing `valid_failure`. This is a scientific failure with complete
evidence, not an engineering exception or missing-data success.

All 35 control plans were accepted: 4 converged, 31 intentionally early-stopped,
30 selected initialization, and 5 selected a non-initialization plan. These counts
overlap. There were zero unusable plans, solver exceptions and fallback holds.
Raw terminations were 4 `Solve_Succeeded` and 31 `User_Requested_Stop`; stopping
reasons were 30 `budget_best_feasible` and 1 `relative_seed_improvement`.
Maximum normalized plan violation was `4.000478e-6`. Mean complete update time was
19.292457 s; all 35 missed the 10 ms wall deadline. Real-time deployment was not
an acceptance requirement. Synchronous simulated-time commands were still applied
at every configured interval.

All 35 short-horizon predictions matched the next timestamp and applied input,
with no missing position or velocity matches. Maximum position disagreement was
9.445293 mm, maximum velocity-vector disagreement 0.222288267 m/s, and maximum
speed-magnitude difference 0.166410975 m/s. Maximum position and rate projection
residuals were 2.871927 rad/m and 89.714889 rad/(m·s). The six holding samples show
substantial motion and changing error; they do not identify a unique cause.
Per-tendon utilization and complete controller observations remain in the
[feedback](../evidence/casadi_nmpc_research_20261010/closed_loop_01_feedback.json).

Construction cost was 0.462477 s, simulation 680.594 s, evaluation 1.687 s and
profile 3.172 s: total 685.915477 s. Control updates, graph/solver construction,
physics and initialization are included in simulation cost, not added again.
The shared project ledger charged one launch; 35 rolling NMPC solves did not
consume standalone offline NLP slots.

On provider send 5, feedback changed the model's next action to STOP. Its
[original disposition](../evidence/casadi_nmpc_research_20261010/model_original_final_disposition.json)
cites the new result and imported failures. It was accepted; no request followed
acceptance. The [separate factual correction](../evidence/casadi_nmpc_research_20261010/post_stop_correction.json)
preserves that decision but corrects overclaims: wall overruns do not demonstrate
simulated control starvation or actuator delay, not all early stops were budget
stops, vector and speed-magnitude errors differ, and untested weights cannot be
declared incapable of improving the outcome. STOP is a bounded research decision,
not a validated causal explanation or proof that remaining options cannot work.

| Resource consumed | Actual | Ceiling |
|---|---:|---:|
| New offline NLP / BDF attempts | 0 / 0 | 2 / 3 |
| MuJoCo launches / internal NMPC solves | 1 / 35 | 2 launches |
| Actual provider sends / public calls | 5 / 9 | 16 / 64 |
| Scientific computation and focused checks | 720.954477 s | 7,200 s |
| Focused-check unittest timers | 35.039 s | Included above |
| Sealed activity elapsed snapshot | 2,175.329847 s | 21,600 s |
| Other research LLMs / real hardware | 0 / 0 | 0 / 0 |

Provider elapsed time was 90.141 s; reported usage was 81,231 prompt and 18,619
completion tokens, 99,850 total (24,576 cache-hit and 56,655 cache-miss prompt
tokens). Monetary charge was not reported. Remaining ceilings are unused, not
permission to restart this stopped activity. The sealed elapsed snapshot precedes
final delivery reporting and ordinary Git delivery; the original clock remains
the overall six-hour authority.

Seventeen distinct focused fixtures were checked, with only concrete repairs
rerun. They cover saved/nonzero-length wiring, same-state model consistency,
first-action/revision/STOP choices, velocity reconstruction/alignment, checkpoints,
protected native context and partial failure feedback. No fixture advanced a hidden
simulation or invoked a real NMPC solve. After STOP, delivery-only repairs removed
the irrelevant NLP batch label from other actions and added compact partial
saved-state feedback for failed tool stages; two affected fixtures passed after
fixture corrections. These repairs did not change or repeat the live experiment.

Both imported candidates still fail independent open-loop acceptance. Their BDF
holding speeds remain approximately 0.04312197 and 0.04218082 m/s on a 0.0005 s
dense grid. The second export was retained iteration 3 of a CPU-limited 34-iteration
solve; the approximately 2.18% replay improvement does not isolate the objective
effect because initialization also changed and convergence was not established.
The new sampled NMPC execution measures a different control/plant path and does
not relabel either old schedule. Only one fixed structure and default controller
were tested; control-weight sensitivity, alternatives, continuous-time performance,
hardware transfer, global optimization and LLM superiority remain unestablished.

Evidence: [machine summary](../evidence/casadi_nmpc_research_20261010/result_summary.json),
[resolved configuration](../evidence/casadi_nmpc_research_20261010/closed_loop_01_configuration.json),
[wiring/provenance](../evidence/casadi_nmpc_research_20261010/closed_loop_01_wiring.json),
[aligned predictions](../evidence/casadi_nmpc_research_20261010/closed_loop_01_aligned_predictions.json),
[holding trace](../evidence/casadi_nmpc_research_20261010/closed_loop_01_holding_trace.json),
[decision trace](../evidence/casadi_nmpc_research_20261010/decision_trace.json),
[archive manifest](../evidence/casadi_nmpc_research_20261010/archive_manifest.json), and
[delivery repairs](../evidence/casadi_nmpc_research_20261010/delivery_repair.json).
Original requests, interpretations, immutable results, imported plans and corrections
are separate artifacts. The post-STOP correction was not sent to the model.
