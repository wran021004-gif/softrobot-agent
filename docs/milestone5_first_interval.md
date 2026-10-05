# Milestone 5 shared first interval and recovered research handoff, 2026-10-05

The bounded stage is completed and stopped. Both actual configured DeepSeek
research handoffs succeeded through the native `research.milestone5_preparation`
tool. Numerical refinement materially reduces the earliest velocity-vector error
by **81.406%**, from 0.0540802209622 to 0.0100556261030 m/s. However, successive
velocity-vector and speed differences still exceed the unchanged 1e-4 m/s
tolerance. There is **no supported stabilized first-interval reference** within
this stage. The accepted final research judgment selects **C: establish local
numerical stability as the unresolved prerequisite**, and defers screening.

Milestones 2-4 remain closed; Milestone 5 remains open. The incumbent is unchanged:
`batch-ebbeadbdaca10732-0`, execution `91c3ba1b01d6499fb26df8f95409401b`,
near/far .16/.11 m, .95 section scale, compliant material, holding/terminal
.05/.05, `controller.gvs_nmpc@7.0.0`. Its accurate sampled completion does not
establish real-time control: all 35 deadlines were missed.

See [delivery](../evidence/milestone5_first_interval_20261005/delivery.json),
[specification](../evidence/milestone5_first_interval_20261005/specification.json),
[calculation](../evidence/milestone5_first_interval_20261005/calculation.json),
[accepted corrected interpretation](../evidence/milestone5_first_interval_20261005/interpretation_response.json),
[protocol](../evidence/milestone5_first_interval_20261005/protocol.json),
[readiness](../evidence/milestone5_first_interval_20261005/readiness.json), and
[accounting](../evidence/milestone5_first_interval_20261005/accounting.json).

## Actual handoffs and preserved history

The user's attachment `81550312-c87d-421b-b023-6a8081d8e041` explicitly authorized
the compact project-evidence transmission to `https://api.deepseek.com`, normal
credential authentication, and commit/push to origin `feat/gvs-dynamics` without
force. This authorization is recorded in the new stage. The existing
deepseek-flash endpoint, reasoning, context/token limits, TLS and transport were
preserved. Credentials were neither printed nor placed in evidence.

The initial model retained .075/.15, terminal .05, as a conditional future
comparison and deferred screening execution. It considered earlier local
references, the .075 false-safe prediction, ranking abstention at the unchanged
1e-4 margin, and adverse costs. These are accepted research judgments, not
validated screening capability. Reset-clock checkpoint scenarios remain distinct
from historical warm continuation.

The initial accepted selection artifact is
`d26ea6a3185b5d0483126f9133dfbc85a81dee2c0493298e56f52cfbf24ed396`.
The final corrected accepted interpretation is
`019bbbd90cd99e9618f1194bbddaeaa4ee93852a121da84a7d44aeba3a2a1726`.
The shared protocol finalizer verifies their completed native-tool receipts and
matching recipe pair. Both research completion flags are true; prospective
scientific readiness remains false. The protocol/seal link to the previous
recovery revision and both earlier approval rejections, which remain unchanged.

Fourteen holding-entry integrations, six earlier reference integrations, two
complete historical previews and the five passed recovery checks were reused.
No earlier calculation, controller optimization or preview was repeated. The
preceding preparation/recovery ledgers, sessions, calls and evidence hashes were
checked unchanged. Prior reports, protocols, seals and rejections remain
historical records; only the current-status pointer is updated.

## One genuinely shared original interval

The exact bound manifests identify .075 execution
`2413ff2a56de422dac47b7fd78717563` and .15 execution
`9865f1636266479c93817cad42a65353`. Their robot, environment, initializer, seed,
basis, XML, physics, compiled indices, original physical state, first applied
tension, time interval, tip definition and backend endpoint match. Their
fixed-input dynamics agree despite different controller objective weights.
Shared identity:
`661f70b26939cf83277a9e429ce97772fea568903623ac30d87cec5574c9f3c3`.

The original task clock is 0.00-0.01 s. Its 24-component reduced state is zero
and exactly matches the saved preview/controller starting state. Full backend
coordinates, velocities, actuator state and clock were reconstructed in fresh
MjData from the original saved experiment-scene initializer, following the
historical initialization path. This is the original initial physical condition;
a historical integration-cache snapshot was not retained. It is not either
reset-checkpoint future scenario. Backend forward kinematics and the existing
world site-Jacobian velocity path were used without advancing backend time.

Held direct ideal tensions, in near_t0/t1/t2 then far_t0/t1/t2 order, are
`[1.7512764858409064, 4.755852667139922, 3.1031566686630025,
3.218253612486097, 0.7859357597552847, 0.6315302379791942] N`.
Desired, requested, actual and trajectory tensions agree. Observation row zero
is the interval start; trajectory row zero is the .01 s endpoint. All outputs
refer to the same world-frame tip. Initial instantaneous output agreement is
1.11e-16 m in position and exactly zero in velocity.

The saved backend endpoint is position
`[0.2979194519722485, 0.001318325730051994, 0.15133566194286324] m`,
velocity `[-0.022306392104925403, 0.18789548765804737, 0.20896934027946673] m/s`,
speed `0.2819050808123714 m/s`. Preview/backend command difference is zero for
this interval. Own-history commands first separate at .02 s; the two weight
previews first separate from each other at .20 s. Those are distinct events.

The immutable specification was saved before calculation. One shared calculation
receipt contains six propagation attempts and is referenced by both cases.
Reduced dynamics, input, duration, initial state and output definitions were
held fixed. The narrowly scoped diagnostic permits at most 320 substeps; the
existing 80-substep helper and production controller defaults are unchanged.

## Endpoint results and numerical stability

All six roots were finite, with verified scaled residuals below 1e-5; the maximum
was 5.893864e-11. The coarse endpoint reproduces the saved state, position and
velocity **exactly**. Costs include model construction and propagation, nested
once inside the outer charged receipt.

| Step (s) | Substeps | Vector error (m/s) | Signed speed error (m/s) | Position error (m) | Complete cost (s) |
|---|---:|---:|---:|---:|---:|
| .01 | 1 | .054080221 | -.053963112 | .000414377767 | 7.191 |
| .0005 | 20 | .008953288 | -.000252438 | .000057611704 | 4.741 |
| .00025 | 40 | .009376651 | +.001652372 | .000052060629 | 9.275 |
| .000125 | 80 | .009731710 | +.002620183 | .000050718446 | 18.561 |
| .0000625 | 160 | .009942401 | +.003108056 | .000050467866 | 37.534 |
| .00003125 | 320 | .010055626 | +.003352997 | .000050452902 | 74.612 |

The coarse preview position is
`[0.29789816183365814, 0.0015026660616180238, 0.15170616741663479] m`,
velocity `[-0.020362428916033824, 0.1501641098643366, 0.17027522656396257] m/s`,
speed `0.22794196889585266 m/s`. The finest tested endpoint is position
`[0.29791968722923434, 0.0012748634265295372, 0.15136128357679507] m`,
velocity `[-0.022479249196063443, 0.18293826365720198, 0.2177164350517126] m/s`,
speed `0.28525807796792935 m/s`.

Vector error decreases by .0440245948592 m/s, or 81.4060927931%, relative to
coarse. Position error falls from .414378 to .050453 mm. Agreement subsequently
**worsens across every fine halving** in vector error and signed speed error;
the .0005 speed match is not evidence of a stabilized solution.

| Fine halving (s) | Successive vector difference (m/s) | Successive speed difference (m/s) |
|---|---:|---:|
| .0005 to .00025 | .001926410 | .001904811 |
| .00025 to .000125 | .000978776 | .000967811 |
| .000125 to .0000625 | .000493392 | .000487873 |
| .0000625 to .00003125 | .000247710 | .000244941 |

Stability requires both quantities at or below 1e-4 in the last two successive
fine comparisons. It remained unresolved after the first four attempts, which
justified the last two. It remains unresolved at the cap. Last position
sensitivity is 1.941115e-6 m. These are observed resolution differences, not a
proven uncertainty bound. Near-two difference ratios are consistent with
first-order scaling; they establish neither tolerance satisfaction nor numerical
dominance of the remaining physical disagreement. Small root residuals alone
establish neither stability nor backend accuracy. No finest supported endpoint
can therefore be reported; the table's final row is **finest tested only**.

## Instantaneous output and evolution accounting

The reduced output evaluated at the projected observed backend endpoint is
position `[0.2979277173870012, 0.0011605973455394484, 0.15114002448194674] m`,
velocity `[-0.0201441395921505, 0.1672131070565681, 0.18198103979427466] m/s`,
speed `.247957876212926 m/s`. A substantial discrepancy is already present in
this instantaneous endpoint representation/output comparison, although no such
discrepancy exists at time zero.

At the finest tested resolution, the exact ordered identity is
`predicted - backend = (predicted - projected observed output) +
(projected observed output - backend)`:

| Velocity term | World vector (m/s) | Norm (m/s) |
|---|---|---:|
| Evolution | [-.002335109604, .015725156601, .035735395257] | .039112041128 |
| Instantaneous projection/output | [.002162252513, -.020682380601, -.026988300485] | .034070582125 |
| Total | [-.000172857091, -.004957224001, .008747094772] | .010055626103 |

The position term norms are .000249152178 m evolution, .000251437023 m
instantaneous projection/output, and .000050452902 m total. Both exact identity
residuals are zero; full vectors for every resolution are in calculation.json.
Opposing terms partially cancel in both position and velocity. Evolution
contains representation, model and unresolved numerical effects; the
instantaneous term does not identify a projection implementation bug. Neither
term supports a unique causal percentage. No fitted material, scalar correction
or changed output definition was introduced.

## Accepted next direction and status

The corrected actual model selects **C**. Its precise prerequisite is a local
reference satisfying successive vector **and** speed differences <=1e-4 with
finite roots and scaled residual <=1e-5. It proposes one unexecuted investigation:
continue halving below the already tested .00003125 s step on this same original
.01 s fixed-input interval, for example .000015625 then .0000078125 s, with its
own separately authorized cap and budget. None of that follow-up ran here.
Persistent resolution sensitivity, nonfinite roots or residual failure would
falsify the proposed local-reference adequacy. Worsening backend agreement alone
does not falsify numerical self-consistency; it addresses physical accuracy.

Research handoff and first-interval calculation are complete. Numerical stability
is unresolved. Backend agreement improved relative to coarse but endpoint
accuracy is unestablished. Instantaneous output mismatch is substantial and
state dependent. Complete-history discrimination remains unvalidated; the prior
screen abstained and had a false-safe outcome. The .075/.15 pair remains
conditional, screening readiness false, and Milestone 5 open. The inherited
readiness check named `numerical_reference_stable` concerns the earlier
holding-entry reference; current first-interval stability is explicitly false
in the separate readiness dimensions. One shared retrospective interval cannot
rank weights or establish generalized, economical prospective screening.

## Receipts, interventions and verification

| Usage | Historical | This stage | Cumulative |
|---|---:|---:|---:|
| Provider attempts | 37 | 3 | 40 |
| Workflow calls | 71 | 5 | 76 |
| Backend attempts | 6 | 0 | 6 |
| Charged seconds | 4458.552 | 225.750 | 4684.302 |
| Controller optimization attempts | 79 | 0 | 79 |
| Standalone integrations | 35 | 6 | 41 |
| Historical backend controller updates | 210 | 0 | 210 |

Ceilings were 6 provider attempts, 20 workflow calls, 6 integrations and 1800
charged seconds, with zero controller attempts, complete previews, backend
steps, workers or subagents. Receipt charges sum exactly to the ledger and no
reservation remains occupied. The numerical outer call cost 153.172 s; nested
propagation costs are not charged again. Offline engineering reads, edits,
tests and exports follow the established accounting convention. The nominal
admission protected 665 s for interpretation/handoff/export before numerical
work; total nominal reservations were 1770 s.

Three interventions are preserved. A partial preparation initially looked for
the incumbent in the preparation Store; it was recovered using the exact
`source_store` binding, without resetting the grant or consuming model/numerical
work. The first provider returned a valid native decision, but its artifact-only
handoff was rejected by an inherited 600 s tool reservation after provider time
had been consumed. A linked session under the same project grant narrowed that
handoff/read reservation to 5 s and replayed the exact saved model-authored
business fields through the existing pending-action loop, without a provider
resend. The rejected receipt, original output, counters and provenance remain.

The initial accepted rationale invented small scatter and blurred the .02/.20
timestamps. A deterministic annotation corrected those facts, and the final
model explicitly adopted the correction. The nominal final model response then
mislabeled the coarse endpoint as backend, blurred decomposition resolution,
overinterpreted halving ratios and proposed already computed steps with a
confused stability gate. One additional semantic correction provider attempt
produced the accepted corrected final judgment; the original accepted final
artifact and receipt remain archived. No calculation was repeated. Runtime
protocol corrections: 0 total/0 consecutive; business rejections: 1; semantic
provider corrections: 1; deterministic initial annotation: 1. These are distinct
recorded categories, not reset or hidden failures.

Three focused tests passed: exact original shared alignment; coarse reproduction,
vector convergence and output identity; and actual accepted-decision binding
plus receipt reuse without another invocation/charge. The predecessor snapshots
also match. Existing recovery checks were reused; no broad suite, API preflight,
simulation or parameter sweep ran. Export retains raw provider/native receipts,
failed records, linked manifests, implementation snapshots and SHA-256 evidence
hashes. Every new stage session is stopped with operational action `finish_stop`.

The stage began on clean `feat/gvs-dynamics` at
`c98e027edc4eec3a22086b4db0e676e7986aac29`. Only task-related changes are committed.
The authorized non-force push and remote-containment verification are recorded
in the delivery message and a publication receipt after the computation commit;
publication does not authorize follow-up experiments.
