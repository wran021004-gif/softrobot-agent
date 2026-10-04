# Milestone 5 recovery and historical-history diagnosis, 2026-10-05

The bounded local work is completed and stopped. **The research handoff remains
blocked**, and the full requested model-led stage could not be completed. The
first configured DeepSeek attempt failed with `DEEPSEEK_NETWORK_ERROR`. Automatic
approval review then rejected the elevated runner before its process started,
stating: "The command sends internal saved project evidence to the untrusted
external DeepSeek API, but the user did not explicitly authorize that specific
payload and destination." The attachment explicitly authorizes this transmission;
the rejection nevertheless takes precedence. Direct confirmation was requested
in chat. No workaround, further provider call or substituted model response ran.

The model therefore has **no accepted recovery judgment, recipe selection or
final interpretation**. The provisional .075/.15 pair remains provisional.
All scientific recommendations below are engineering assessments of the saved
and newly calculated evidence, clearly separate from a research-model decision.

The incumbent remains `batch-ebbeadbdaca10732-0`, execution
`91c3ba1b01d6499fb26df8f95409401b`, near/far .16/.11 m, .95 section scale,
compliant material, holding/terminal .05/.05, `controller.gvs_nmpc@7.0.0`.
Milestones 2–4 remain closed; Milestone 5 remains open. Starting branch
`feat/gvs-dynamics` was clean at `f2aaad3`; no reset, push, worker, subagent,
dependency upgrade, MATLAB validation or backend advancement occurred.

See [delivery](../evidence/milestone5_recovery_20261005/delivery.json),
[aligned histories](../evidence/milestone5_recovery_20261005/align.json),
[controlled comparisons](../evidence/milestone5_recovery_20261005/compare.json),
[engineering judgment](../evidence/milestone5_recovery_20261005/final_local_review.json),
[linked protocol](../evidence/milestone5_recovery_20261005/protocol.json), and
[accounting](../evidence/milestone5_recovery_20261005/accounting.json).

## Recovery repairs and preservation

Admission now checks completed receipts against their original immutable request
protocols and ledger receipts before reserving work. Unfinished histories alone
consume preview time and controller capacity. The actual completed pair requires
zero further controller attempts and **660 s**, rather than 3060 s, against the
predecessor's 2827.016 s remaining. Failed or incorrectly bound saved calls are
rejected rather than replayed. The six completed reference integrations and both
35-update complete previews were reused without recomputation or new charges.

Normal and blocked protocol construction now share one finalization path. It
retains scenario/recipe identities, versions, implementation hashes, numerical
results/provenance, commands, budgets, limitations and supersession. Selection
and interpretation completion require the actual successful research handoff
receipts and matching decision artifacts. Missing selection defaults to false.
Readiness also requires a worthwhile prospective hypothesis independently of
field completeness. A normal valid handoff alone does not establish that flag.

The new stage uses its own linked 2400 s ledger. Hashes, session states, calls and
usage verify the entire completed preparation unchanged. Its blocked protocol,
seal, serialized handoff and rejection remain historical evidence. The new
protocol seal links to them; neither is a prospective forecast seal.

## Matching historical trajectories

Each preview is compared with its own original historical initializer and recipe:
.075 with execution `2413ff2a56de422dac47b7fd78717563`, and .15 with
`9865f1636266479c93817cad42a65353`. Exact bound manifests identify the controller
observations, trajectory, compiled body indices, physics and XML. No unrelated
campaign was searched. The source initializer is the original zero state,
independently checked against the first recorded controller state.

Observation `i` and command application are at the interval start; trajectory
`i` is its endpoint and retains that interval's command. Trajectory `i-1` supplies
the next row's observed starting state. All 70 rows verify this indexing, projected
state consistency, command equality, timestamps and saved-body reconstruction.
Endpoint velocity is world `J_site(q) @ qdot`; no backend step is used. Saved
`actual_tension_n` is held direct ideal tension available after interval-start
forward dynamics and before stepping, not a later measured average.

The aligned table includes both starting and ending reduced states, actual
projected states, positions, velocity vectors and speed norms, commands, previous
commands, selections/stops, one-step predictions, all saved body origins,
holding membership and artifact pointers. Coordinate differences are mapped to
represented cell angles in radians and cell rates in radians/s and reported
separately; no mixed unscaled state norm is interpreted.

Both cases have the same early timeline:

| Endpoint | Command gap at interval start | Accumulated tip error | Velocity-vector error | Preview / backend selected iteration |
|---|---:|---:|---:|---|
| .01 s | 0 N | .4144 mm | .0540802 m/s | 0 / 0 |
| .02 s | 0 N | .2564 mm | .0464368 m/s | 0 / 0 |
| .03 s | 2.00003 N, applied at .02 s | 2.6015 mm | .474423 m/s | 0 / 16 |
| .07 s | see full timeline | 12.7685 mm, maximum | see full timeline | see aligned row |
| .20 s | .229479 N | 3.2231 mm | .0310841 m/s | 0 / 3 |

Thus shared-input errors appear immediately, followed by a distinct state/input
and optimizer-path transition at .02–.03 s. The **two previews diverging from
each other at .20 s** is a different event from each preview diverging from its
backend at .02 s. Error is nonmonotonic; the complete timeline is retained.
Preview iteration-zero counts are 21/35 for both, versus 13/35 and 14/35 actual.
Exact historical warm plans are unavailable, preventing warm-path reconstruction.

At .02 s the represented serial shape has .8110 mm maximum body-origin error
despite .2564 mm continuous-model tip error. A small tip error can hide a larger
distributed discrepancy, but this example remains below 1 mm. Overall maximum
shape discrepancy is 9.3207 mm, below the 12.7685 mm tip maximum. The shape
comparison uses serial kinematics of discretized reduced coordinates; it is
separate from continuous-model tip prediction and establishes no projection defect.

## Controlled holding-entry decomposition

The selection rule was saved before propagation: use the first .30–.31 s
holding-entry interval for each historical execution. It is holding-critical and
allows exact reuse of already stable observed-state/input references; earlier
onset remains documented. The same model, original task clock/target, duration
and held direct input semantics apply throughout.

A propagates the preview start/input at .01 s. B changes only integration step.
C also substitutes the projected actual starting state. D also substitutes the
actual interval-start input. A reproduces the saved preview. B and C use
.0005/.00025/.000125 s; both successive scalar and vector differences pass the
unchanged 1e-4 m/s reporting tolerance in every case. D reuses the exactly bound
six preparation integrations, not six additional computations. Last B vector
differences are 2.856e-6/2.923e-6 m/s; C differences are
4.587e-5/4.467e-5 m/s. This supports local successive-resolution stability only,
not a proven error bound or whole-history numerical reliability.

| Quantity at .31 s | .075 | .15 |
|---|---:|---:|
| A speed | .005969436 | .005966958 |
| B speed | .005986619 | .005982568 |
| C speed | .015265007 | .015600940 |
| D speed | .018801501 | .007039089 |
| Observed speed | .023285948 | .011023132 |
| A−B speed | −.000017183 | −.000015611 |
| B−C speed | −.009278389 | −.009618372 |
| C−D speed | −.003536494 | +.008561851 |
| D−observed speed | −.004484447 | −.003984044 |
| Norm of A−B velocity vector | .000123897 | .000127004 |
| Norm of B−C velocity vector | .012392407 | .012715826 |
| Norm of C−D velocity vector | .033957033 | .021310451 |
| Norm of D−observed velocity vector | .006823542 | .007304575 |

Speeds and vector norms have units m/s. The vector numerical effect slightly
exceeds reporting tolerance even though its scalar effect is small. State/input
effects are much larger locally. Contributions oppose in vector space and the
.15 scalar input term cancels much of its state term. Full vector telescoping
identities close below 4e-18 m/s; position identities also close. These are ordered
accounting differences, **not unique causal percentages**. Coupled histories,
substitution order, projection, model and input representation limit attribution.
The .075 fine observed-state/input result remains false-safe at .02 m/s.
Remaining position errors are 2.7274/2.7286 mm. No repairable physical defect or
global numerical explanation is established by these two holding intervals.

## One primary action and unexecuted handoff

The engineering primary action is **retain local diagnosis and defer screening**.
No production or complete-preview propagation patch is adopted. Fixed-command
fine propagation is an isolated diagnostic prototype: it changes simulated-plant
integration only; controller optimization transcription remains unchanged.
These local results do not demonstrate benefit for a complete modified history.

The next targeted investigation is the shared original .00–.01 s interval:
refine propagation from the identical zero start and identical actual/preview
input, then compare with its saved endpoint, reporting projection and endpoint
position/vector/speed discrepancies separately. This would distinguish an early
numerical contribution from a substantial residual before command divergence.
A stable fine reference retaining the large first-endpoint vector error would
weaken numerical propagation as its explanation. It requires only a few short
propagations in a separately authorized stage, without controller solves, complete
previews or backend advancement. It is proposed, not executed here.

The reset-checkpoint scenarios remain new episodes from incumbent .20/.30 s
coordinates/velocities, at a **new zero task clock**, with controller history and
integrator state reset. They would test reset-episode predictions, not exact
historical warm continuations. The .075/.15 weights are historical; these new
scenario/recipe outcomes are unobserved. Their justification still awaits the
blocked research model. There is no supported worthwhile screening batch now.

The linked deferred protocol preserves a concrete conditional first batch:
scenario `incumbent_checkpoint_20_new_clock`, both recipes, complete .0–.35 s
previews, .30–.35 s holding predictions, unchanged 1e-4 ordering/abstention
margin, .01 m position and .02 m/s speed limits, threshold-error/false-safe
reporting, and local .20/.30 checkpoints. It retains this order: both previews;
immutable forecasts/pair ranking seal; both complete evaluations including a
rejected candidate; local forecast seals before advances; separate capability
assessments; interpretation/export/stop. Later measured inputs stay retrospective.
The second scenario remains conditional on the frozen stop/continuation rule;
method changes make batch one development data for the revision.

Recalculation using unchanged public reservation rules yields 2590 s for two
complete evaluations/preparation and protected interpretation, plus 3000 s for
two previews, 180 s checkpoint overhead and 60 s export: **5830 s**. The historical
6000 s ceiling is a planning value, not a grant. Measured preview/evaluation pair
costs remain 694.427/605.937 s. No economical screening benefit is established;
changed propagation would need new measured costs and reservation calculation.
No grant, new-scenario complete forecast or batch execution was created.

Readiness separately reports receipt recovery and implementation complete, local
numerical support at checked intervals, research handoff incomplete, physical
accuracy/discrimination/cost usefulness unmet, prospective screening readiness
false, and Milestone acceptance false.

## Accounting, corrections and verification

| Usage | Historical cumulative | This stage | New cumulative |
|---|---:|---:|---:|
| Provider attempts | 36 | 1 failed | 37 |
| Workflow calls | 67 | 4 | 71 |
| Backend attempts | 6 | 0 | 6 |
| Charged seconds | 4171.068 | 287.484 | 4458.552 |
| Additional controller attempts | 79 | 0 | 79 |
| Standalone integrations | 21 | 14 | 35 |
| Historical backend controller updates | 210 | 0 | 210 |

Exact receipts reconcile with the ledger; occupied reservations are empty.
Reused reference integrations are six unique computations referenced both at
admission and D, and both complete previews are reused. They incur zero new
charge. All 14 new integrations succeeded, including seven saved before a
failed outer workflow call; recovery reused those seven rather than rerunning.
Nested work is charged only through its outer receipt. Offline reading, edits,
exports and tests follow existing engineering accounting conventions.

Two failed local workflow calls are retained. The first shape check incorrectly
included the fixed-base body; correction uses exact compiled `body_ids` and
verifies all saved positions. The second compared .010000000000000009 s exactly
with .01 s; correction uses the existing alignment tolerance. Fresh linked
snapshots retain the same stage grant, old sessions, counters and receipts.
An export failure was repaired by distinguishing typed string EvidenceRefs from
nested identity dictionaries, without provider or numerical replay. Protocol
corrections and business corrections remain zero; all interventions are recorded.

Five focused tests passed: saved request/receipt binding and outstanding-only
admission; common accepted-decision finalization and missing-selection behavior;
all-history alignment and decomposition arithmetic; production/public-rule
isolation; and blocked-protocol rejection before forecasts/backend calls. Static
readiness correctly fails. No broad suite or provider preflight was repeated.
The outstanding blocker is the actual platform transmission rejection. The
operational next action is **finish/stop** this stage.
