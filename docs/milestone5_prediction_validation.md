# Bounded Milestone 5 prediction validation, 2026-10-04

The existing bounded stage is **completed with mixed local evidence and no
resolved full-task discrimination**. Explicit user authorization resumed the same
ledger and permitted the updated project payload and necessary follow-up requests
to the existing DeepSeek endpoint. The original automatic rejection is preserved
in [delivery_before_resume.json](../evidence/milestone5_validation_20261004/delivery_before_resume.json).
No usage was reset. No historical simulation was replayed, worker or subagent
used, or change pushed.

The research model selected holding weights **0.075 and 0.15**, terminal weight
0.05, on the fixed incumbent structure. Both received complete evaluation.
The accepted final role is **local diagnostic evidence** of the embedded
first-period predictor on this structure. Full-task discrimination and execution
ordering remain unsupported. The accepted next action is finish/stop with zero
future budget, retaining the Milestone 4 incumbent without promoting a candidate.
Milestones 2, 3, and 4 remain closed; the overall Milestone 5 remains open.

See [delivery](../evidence/milestone5_validation_20261004/delivery.json),
[unchanged forecasts](../evidence/milestone5_validation_20261004/single_context/forecast_seal.json),
[assessment](../evidence/milestone5_validation_20261004/single_context/prediction_assessment.json),
and [accepted model decision](../evidence/milestone5_validation_20261004/single_context/final_response.json).

## Preserved scientific state

Milestones 2, 3, and 4 remain closed; Milestone 5 remains open. The accepted
selection remains `batch-ebbeadbdaca10732-0`, execution
`91c3ba1b01d6499fb26df8f95409401b`, holding/terminal weights 0.05/0.05.
The passing pre-adaptation reference is `bebcfd47274940fb88a55ce5a2457c4c`,
weights 0/0.05. The 0.10/0.05 result `110dc2c9c1d642dcb018664a65c62c30`
failed holding speed. All use near/far 0.16/0.11 m, section scale 0.95,
compliant numerical material, and controller 7. The selected adaptation is a
small position/speed/computation tradeoff, not dominance over pre-adaptation.
Retained baseline, structural source, latest tested, and selected deliverable
remain distinct. No historical simulation was replayed. The predecessor's
forecast seal, terminal states, and exact usage remain immutable.

## Historical diagnosis

Exact manifests locate controller observations, applied commands, serial backend
q/qdot, XML, and trajectories. Historical warm plans and optimizer snapshots were
not saved and were not reconstructed. Projected state, one-step predictions,
timing, selected iterations, and raw/policy stops are available.

| Development execution | Holding weight | Command divergence vs 0/0.05 | Tip divergence | Holding speed peak | Peak, m/s |
|---|---:|---:|---:|---:|---:|
| `bebcfd47274940fb88a55ce5a2457c4c` | 0 | Reference | Reference | 0.35 s | 0.012735678 |
| `91c3ba1b01d6499fb26df8f95409401b` | 0.05 | 0.20 s | 0.21 s | 0.35 s | 0.012750256 |
| `110dc2c9c1d642dcb018664a65c62c30` | 0.10 | 0.20 s | 0.21 s | 0.31 s | 0.022128675 |

Command divergence uses max-channel difference > `1e-9 N`; trajectory divergence
uses Euclidean tip difference > `1e-9 m`. Requested and applied tensions match
exactly in all three runs. Observations are current interval-start states;
commands apply for that interval; the next trajectory sample follows 0.01 s
later. Every selected iteration and stopping condition is retained in
[historical_diagnosis.json](../evidence/milestone5_validation_20261004/single_context/historical_diagnosis.json).

All three runs selected iteration zero at 0.24–0.29 and 0.31–0.34 s through
`verified_settled_seed`. At 0.30 s, reference and selected adaptation chose
iteration 7; the 0.10 recipe chose iteration 11, all with
`relative_seed_improvement`. At 0.00, 0.01, 0.05, and 0.06 s initialization was
selected with `budget_best_feasible`; other active updates selected later iterates.

The observation rule selects **0.20 s**, the first command divergence, and
**0.30 s**, the active holding-entry update, before new numerical results.
The original 0.34 s snapshot omitted both events and the 0.10 speed maximum,
and had only one period left. The proposed cold preview retains effective
horizons 10 and 5 periods, production early stops, and candidate-specific state
regeneration. A repeated previous-input cold seed is explicitly distinct from
a historical production warm plan.

## Question A: matched local dynamics development evidence

Recorded production first-period predictions were compared with the following
backend samples under identical applied tensions. Backend velocity is reconstructed
by the existing `J_site(q_backend) @ qdot_backend` method using sealed XML and
serial states, without stepping. Reduced initial tip kinematics use the recorded
GVS projection, evaluated directly without a solve or rollout. Quantities are
world-frame metres and metres/second.

| Recipe | Interval, s | Predicted speed change, m/s | Backend speed change, m/s | Endpoint speed error, m/s |
|---|---|---:|---:|---:|
| 0/0.05 | 0.20–0.21 | +0.014001709 | +0.012093397 | −0.000507229 |
| 0.05/0.05 | 0.20–0.21 | +0.014002283 | +0.012093900 | −0.000507159 |
| 0.10/0.05 | 0.20–0.21 | +0.014002846 | +0.012094393 | −0.000507089 |
| 0/0.05 | 0.30–0.31 | −0.006371582 | −0.002543147 | −0.003732506 |
| 0.05/0.05 | 0.30–0.31 | −0.007125222 | −0.003174943 | −0.003907564 |
| 0.10/0.05 | 0.30–0.31 | +0.003555963 | +0.009732788 | −0.006185487 |

Six development signs agree; none meets the frozen `1e-4 m/s` endpoint-speed
tolerance. Initial projected position differs by 2.69–2.72 mm; initial projected
speed differs by −0.002416 m/s at 0.20 s and −0.0000087 to +0.0000959 m/s at
0.30 s. Initial projection offset and subsequent error are separately recorded;
these are not complete-state agreement or isolated dynamics error. The three
0.20 s intervals share their starting history and are not independent repeats.
Tolerances are numerical rules, not statistical confidence or repeatability.
Bindings and vector discrepancies are in
[development_fidelity.json](../evidence/milestone5_validation_20261004/single_context/development_fidelity.json).
This supports a narrow development diagnostic observation, without prospective
validation or a research-model acceptance of that role.

## Candidate-specific cold preview and prospective full-task scoring

The actual refreshed outbound handoff included all six historical matched
intervals, their systematic underestimation, projection discrepancies, the
0.31 s threshold warning, development exclusions, remaining capacity, and explicit
external authorization. The original handoff is version 1; the actual authorized
handoff is version 2. Detailed artifacts and both payload versions are retained.

Six additional controller solves and six reduced rollouts covered the incumbent
and both new recipes at 0.20 and 0.30 s. Initialization was a common cold repeated
previous-input seed with independently regenerated candidate state, not a
reconstructed historical warm plan. Production early stops and effective horizons
10/5 were preserved. At 0.20 s all three selected iteration 5 through
`relative_seed_improvement`; their small plan differences are development-state
preview observations. At 0.30 s all selected iteration zero through
`verified_settled_seed`, with identical holding-plan maximum speed
**0.01991554683358343 m/s**. This latter checkpoint defines the full-task mapping.

The predeclared rules use position tolerance 1e-6 m and speed tolerance 1e-4 m/s.
Cold-preview equality maps to abstention about full-task directions. The limited
secondary speed-order rule uses the same comparable 0.30 s plans and tolerance:
tie or invalid coverage means abstention; actual ties remain explicit. This rule
was implemented and tested, rather than represented by an always-empty field.
It predicts neither overall design ranking nor joint acceptance. The frozen
joint-acceptance forecast remained unresolved.

The forecast seal event was sequence 115; backend reservations were sequences
122 and 150. Exact plan, prepared/scientific configuration, execution, numerical
dependency and implementation bindings passed chronology checks. No mapping,
checkpoint, tolerance or forecast was revised after observing outcomes.

| Holding weight | Frozen error/speed directions | Observed directions vs .05 incumbent | Full-task holding error, m | Full-task holding speed, m/s | Actual joint acceptance |
|---|---|---|---:|---:|---|
| 0.075 | Both unresolved | Both deterioration | 0.002905756 | 0.023285948 | lost |
| 0.15 | Both unresolved | Both deterioration | 0.002746094 | 0.012939198 | preserved |

The executions were `2413ff2a56de422dac47b7fd78717563` (0.075) and
`9865f1636266479c93817cad42a65353` (0.15). Both passed terminal reach and holding
position. Only 0.075 failed the 0.020000 m/s holding-speed requirement.
The 0.15 candidate preserved sampled acceptance but traded improved terminal
error against worsened holding error and speed relative to the incumbent.
It was not promoted. Both had 35/35 deadline misses; mean complete updates were
8.514238 s and 8.510688 s at a 0.01 s period. Timing failure remains separate
from sampled physical acceptance.

Full-task direction scoring is **0 correct, 0 incorrect, 4 unresolved**;
resolved coverage is zero and conditional accuracy is **undefined**.
The predicted speed-order status was tie (abstention); actual speed order resolved
0.15 ahead of 0.075, separated by 0.010346749 m/s. Ordering verdict is unresolved;
this is not demonstrated ordering usefulness or an overall candidate ranking.
The model's original plan expected 0.075 to pass and 0.15 to fail; both pointwise
expectations were contradicted. This research hypothesis is separate from the
reduced predictor's abstentions. These points establish no continuous boundary,
general screening reliability or dominant causal mechanism.

## Prospective local dynamics under actual applied input

The observer verified the actual input and sealed the existing production
first-period prediction before backend advancement at each checkpoint. Local
seal sequences were 128/129 and 156/157; simulation completions were 130 and 158.
The subsequent physical samples and exact execution/configuration bindings were
verified. Capture overhead was charged normally. This instrumentation supplied no
command and added no diagnostic solve or rollout. Embedded production updates
remain separate from the six additional diagnostic solves.

| Holding weight | Interval, s | Predicted speed, m/s | Observed speed, m/s | Signed endpoint error, m/s | Local direction | Within 1e-4 m/s? |
|---|---|---:|---:|---:|---|---|
| 0.075 | 0.20-0.21 | 0.038326588 | 0.038833712 | -0.000507124 | increasing, correct | No |
| 0.075 | 0.30-0.31 | 0.016953566 | 0.023285948 | -0.006332381 | increasing, correct | No |
| 0.15 | 0.20-0.21 | 0.038327398 | 0.038834415 | -0.000507016 | increasing, correct | No |
| 0.15 | 0.30-0.31 | 0.005830076 | 0.011023132 | -0.005193056 | decreasing, correct | No |

These **four new prospective intervals** had 4/4 correct speed-change directions
and 0/4 numerical endpoint passes. All four speeds were underestimated. Local
increasing/decreasing labels describe dynamics; acceleration before holding is
not automatically task deterioration. The .075 prediction at 0.31 s was
0.016954 m/s versus 0.023286 m/s observed, crossing the 0.020000 requirement despite
correct acceleration direction. The historical .10 warning remains separate:
0.015943 predicted versus 0.022129 observed at 0.31 s. Projection discrepancies
are recorded separately from endpoint errors. Correct direction does not establish
threshold classification, numerical accuracy, repeatability or general reliability.

The accepted model decision supports local diagnostic evidence only. It defers
full-task discrimination and execution-ordering use, retains full evaluations,
and stops this stage. The original Milestone 5 gates remain unmet: accurate local
numerics, useful resolved full-task discrimination/order, broader repeatability,
and real-time feasibility have not been demonstrated. No automatic rejection,
structural inference, controller-family comparison, hardware or continuous-time
guarantee follows. Proposed future research authorizes no further run.

## Accounting, corrections and verification

| Resource | Immutable predecessor | Current stage | Cumulative |
|---|---:|---:|---:|
| Provider attempts | 19 | 9 / 24 | 28 |
| Workflow calls | 37 | 18 / 60 | 55 |
| Full backend attempts | 4 | 2 / 2 | 6 |
| Charged seconds | 2230.207 | 971.706 / 9000 | 3201.913 |
| Workers | 0 | 0 / 0 | 0 |

Exact receipts govern arithmetic and match the complete call ledger. Additional
local solves/rollouts: old 3/3, current 6/6, cumulative 9/9. Embedded controller
updates: old 140, current 70, cumulative 210, accounted separately. Preview receipt
cost was 73.313 s; complete candidate evaluations cost 605.937 s. No reservation
remains occupied. The current 12-solve/24-rollout ceilings were not exhausted.

Protocol corrections: old 4, current 2, lifetime 6; current corrections were
nonconsecutive `CANDIDATE_DISPOSITION_SELECTION_MISMATCH` repairs. Semantic
corrections: old 3, current 2, lifetime 5. The original final interpretation
confused historical and prospective evidence, used the wrong checkpoint maximum,
claimed unsupported ordering usefulness, and overstated a boundary inference.
Its first semantic repair exposed an old-baseline selection binding; the second
repair bound retention to the exact M4 incumbent. Original responses, rejected
interpretations, protocol feedback and all charges are preserved.

One provider attempt failed with `IncompleteRead(0 bytes read)` after the six
previews. A targeted same-project context migration reused those saved previews
and the accepted plan; it reset no budget or recovery allowance and repeated no
numerical or backend work. Offline handoff refresh also repaired the restored
historical feedback field. The original automatic rejection remains recorded as
a pre-process event, not a provider attempt; the later explicit authorization
resolved it. Provider/model/token/TLS settings and authentication handling stayed
unchanged; no credentials are in evidence.

The previous eight focused checks were reused. Four resume checks passed for the
actual six-interval outbound payload and budget, neutral local labels, and
ordering ties/coverage/scoring. Final identity, prospective chronology, unchanged
rules, full receipt sums, predecessor immutability and sealed Git bytes were
checked. No broad suite, paid preflight, parameter sweep, dependency upgrade,
historical replay, worker or subagent ran. Offline engineering time is separate
from receipt-charged execution time.

Implementation/resume commits: `4d2145f`, `72dfeb5`; final delivery commits are
reported in the final response and Git history. All commits are local.
