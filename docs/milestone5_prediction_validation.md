# Bounded Milestone 5 prediction validation, 2026-10-04

This separately authorized stage is **incomplete and awaiting external-payload
approval**. Historical diagnosis and matched-input development analysis completed.
No new provider attempt, controller solve, reduced rollout, or backend attempt
ran. Automatic approval review rejected the launch because authorization for the
specific historical diagnostics/project payload and external destination was not
established in that review. The prepared native handoff is
[validation_serialized_handoff.json](../evidence/milestone5_validation_20261004/single_context/validation_serialized_handoff.json),
for `https://api.deepseek.com`, model `deepseek-flash`; credentials are excluded.

The [delivery](../evidence/milestone5_validation_20261004/delivery.json) separates
this access restriction from a scientific prediction result. There is no accepted
new candidate plan, prospective forecast, validation outcome, or research-model
final decision. Implementation commit `8b64aac` preceded the rejected launch;
offline recovery and evidence are committed separately. Nothing was pushed.

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

## Question B and prospective validation remain pending

The formal handoff binds the passing 0.05/0.05 incumbent, fixes structure and
terminal weight, and excludes development points 0, 0.05, and 0.10. It asks the
research model to justify one or two new holding weights in the existing [0,1]
domain. No candidate value or scientific conclusion is supplied by an engineer.
Every accepted candidate still requires full evaluation.

The implemented preview mapping compares physical holding-plan maxima, using
position tolerance `1e-6 m` and speed tolerance `1e-4 m/s`. Improvement and
deterioration require signed differences beyond tolerance; practically unchanged
describes an observed within-tolerance difference; unresolved denotes abstention
or insufficient coverage. Cold-preview equality maps to unresolved full-task
prediction, not task equivalence. Local endpoints and planned holding maxima
remain distinct from full closed-loop backend maxima. No absolute acceptance
or overall ordering is assumed.

An opt-in observer seals existing production first-period predictions at both
checkpoints after actual input verification and before `mj_step`. It supplies
no command and changes no solver, horizon, integration, or acceptance setting.
Capture time is included in simulation/update charges. Candidate configuration,
execution identity, and event ordering bind predictions. Embedded production
updates remain separate from additional diagnostic solves/rollouts.

No prospective forecast or outcome exists, so validation coverage, accuracy,
ranking, and acceptance preservation are unavailable, not zero-percent accuracy.
No screening, automatic rejection, structural inference, controller-family
comparison, or single/dual superiority is validated. The research model has not
accepted a final role or next-action decision because its access is blocked.
Operationally, await explicit external-transmission approval; no follow-up run
launches automatically. Milestone 5 is not closed by offline development work.

## Accounting and verification

| Resource | Immutable predecessor | New stage | Cumulative |
|---|---:|---:|---:|
| Provider attempts | 19 | 0 / 24 | 19 |
| Workflow calls | 37 | 3 / 60 | 40 |
| Full backend attempts | 4 | 0 / 2 | 4 |
| Charged seconds | 2230.207 | 10.235 / 9000 | 2240.442 |
| Workers | 0 | 0 / 0 | 0 |

Exact receipts govern arithmetic. New additional controller solves and prediction
rollouts are both zero. Protocol corrections: old 4, new 0, lifetime 4; semantic
corrections: old 3, new 0. One automatic approval rejection occurred before
process creation and is separately retained, not charged as a provider/backend
attempt or platform correction. Offline engineering/test time is separate from
receipt-charged execution time. No reservation remains occupied.

Eight focused checks passed for serialized planning context, imported evidence,
time/input alignment, projection-aware scoring, immutable predecessor state,
and evidence-only recovery. Initial Windows sandbox permissions and an imported
ownership-resolution defect were repaired with authorized filesystem access and
the existing `BoundReader`. Original failures are retained in the verification
record. No paid preflight, sweep, dependency upgrade, historical replay,
worker, or subagent ran.
