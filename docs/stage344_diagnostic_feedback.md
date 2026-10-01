# Stage 3.44: bounded diagnostic handoff and saved-state feedback

This stage uses the existing sequential provider loop and public handoff tools.
The implementation is frozen at `b509bbe`. The new store is
`runs/stage344_diagnostic_cycle_20261002`; portable evidence is under
`evidence/stage344_diagnostic_cycle_20261002`. The entrypoint is
`examples/stage344_diagnostic_feedback.py` (`prepare`, `run`, `export`).

The project ceilings are 24 provider attempts, 60 tool calls, 3,600 charged
seconds, zero backend solves, and zero workers. Design has ten attempts;
diagnosis has fourteen. Numerical ceilings remain six local solves and 24
prediction evaluations, with at most one saved-state check executed. These
ceilings do not authorize using all numerical units or running a backend variant.

Opt-in phase budgets are enforced atomically at reservation time. Availability
is the minimum of remaining project capacity, the session/request grant, the
phase ceiling, and protected downstream allocations. Provider transport timeouts
use the same available time as reservations. The initial diagnostic report has
at most four attempts, including corrections; at least six diagnostic attempts
and four design attempts are protected for later work. Tool and time reserves
are frozen in `freeze.json`, including the executor and final responses.

Successful read turns are distinct from provider attempts and protocol
corrections. A legal sequential batch counts once; every contained call is
charged. After two successful read turns, only the current delivery tool remains.
Prediction and motion/plan views are required before initial submission. After
the one check returns, only revised-report submission remains. Advertised tools,
host enforcement, and correction instructions share that same phase selection.
Rejected model tools consume available tool capacity in opt-in phases. Historical
contexts retain their existing permissions and accounting.

The same diagnostic session continues through check selection and revision;
usage and recovery counters remain cumulative. Revised reports must link the
previous report and feedback. Design must reference the current report. The
coordinator rejects stale handoffs instead of treating an earlier submission as
a completed later phase. Full check results remain immutable; inline feedback
retains scalar values, units, references, and provenance without full trajectories.

The Stage 3.41 source is imported through the existing ownership-preserving
binding. Its terminal error is 0.007642608585867386 m, terminal speed
0.6351726092425104 m/s, final-window maximum speed 1.5810152739742807 m/s,
mean update time 17.075238151415917 s, and deadline misses 35/35. Reach passed;
sampled settling and timing failed. These observations do not identify causes.

Focused verification covered ten distinct tests. The first executable run passed
nine and exposed uncharged rejected phase calls. After that repair, both affected
checks passed (13.429 s); the other eight were not repeated. Initial sandbox
fixture failures were environmental and reached no assertions. Exact logs and
results are retained in `focused_checks.json`. The broad historical combination
suite was not rerun and remains uncertified.

The single live attempt **stopped before the first design response**. It produced
a real design-authored request (`3cf9771078c4de756e6f7a90d7a3e7b8306655a2c331fbad6d6cc5a08380cc50`)
and a validated diagnostic report (`e96842cd55baef86923693e9899f7a6622ac722746f24c9afb9dd27abc38ecc2`).
Diagnosis read prediction and motion views in one sequential batch, then submitted
four facts with exact selectors, separate hypotheses, missing evidence, and
advisory recommendations. It used two attempts, leaving its later capacity intact.

The first design response combined `disposition=defer` with
`next_action=bounded_verification`, which the existing adoption contract rejected.
Its second attempt put `next_action` outside the `arguments` envelope. Protocol
recovery scheduled a correction, but the frozen two-attempt initial response phase
had no remaining provider capacity. The exact stop was
`MODEL_PROTOCOL_CORRECTION_BUDGET_EXHAUSTED: BUDGET_EXHAUSTED: active phase / protected downstream capacity`.
Neither the phase limit nor the one-shot guard was reset.

| Requested outcome | Live result |
| --- | --- |
| Model-authored request | Completed; `diagnosis_request.json` |
| Initial diagnostic report | Completed; `saved_diagnosis_report.json` |
| Explicit initial design response / complete handoff | Not completed |
| Check selected and executed | Not completed; zero numerical evaluations |
| Feedback consumed and revised report validated | Not completed |
| Design response to revised report | Not completed |
| Physical improvement | Not evaluated |

Exact usage was **6/24 provider attempts, 8/60 tool calls,
140.71699999971315/3600 charged seconds, zero backend solves, zero local solves,
zero prediction evaluations, and zero workers**. Design used four attempts;
diagnosis used two. One protocol correction was scheduled but its next provider
request was blocked by the phase ceiling. Raw payloads/responses and tool receipts
are retained in the portable artifact bundle and the original SQLite store.

The report observes one-step endpoint differences of 0.006240614340723002 m at
update 30 and 0.001183439178222365 m at update 34. These are saved observations,
not new numerical validation. Competing model-mismatch and controller-objective
hypotheses remain unresolved. This attempt does **not** provide the requested
consumed check evidence or explicit design decision to justify a subsequent
single-factor matched control comparison. The Stage 3.41 baseline remains intact.

A subsequent **offline-only repair** clarifies legal design-response combinations:
defer/reject requires `next_action=stop`; bounded verification requires adoption.
It explains that declining verification does not stop the coordinator's diagnostic
check phase, and that corrections must resend the complete tool envelope. The
same instruction now appears in normal role prompts and correction prompts.
One affected regression test passed; this repair has not been live-validated.

The initial launch was blocked by automatic approval review over external payload
authorization. After inspecting the attachment's explicit paid DeepSeek permission
and the exact destination/payload, the reviewer permitted the same frozen launch.
The rejected launch created no guard or provider call; only one live attempt ran.
