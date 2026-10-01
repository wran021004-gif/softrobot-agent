# Stage 3.43: bounded diagnostic feedback

The live attempt **failed before the initial diagnosis request**. Implementation
commit `e99f00c` made ten real DeepSeek calls, all decoded legally: eight two-read
batches, one single read, and one three-read batch. The resulting twenty evidence
reads exhausted the frozen ten-call design allocation. Stop reason:
`BUDGET_EXHAUSTED: session`. The project still had fourteen provider attempts,
but the design allocation and one-shot guard were not reset or replaced.

There is no design-authored diagnosis request, diagnostic report, design
response, selected check, feedback consumed by a model, local comparison,
backend variant, adoption decision, or final model review in this attempt.
Those phases are incomplete; no report references are fabricated. The actual
decisions, receipts and provider payload/response references are retained in
the compact evidence and original local SQLite artifact store.

The live run validates bounded sequential read batching, separate receipts and
enforcement of the design budget. Effective timeout shrinking under a subgrant,
role transitions, selector validation and check-feedback-report linkage passed
offline checks; they did not receive live validation here. The model repeatedly
paged the binding and full profile despite supplied identities and summary
references. This is a handoff failure, not scientific evidence about the robot.
No causal robot hypothesis was established or ruled out by the new run.

After retaining the failure, an offline repair in the current implementation
inlines the existing deterministic summary, exposes recent actions and phase
progress, and adds an opt-in design evidence-turn allowance. Two initial read
turns are followed by a delivery-only tool phase; design responses and final
review receive immutable report/result content directly. Host enforces the same
subset it advertises. Older contexts without this option retain their evidence
tools. This repair has **not** been tested with another paid attempt. The exact
live source snapshot remains under the new run directory.

Usage: **10/24 provider attempts, 21/60 tools** (including one initial summary
inspection), **0/2 backend attempts, 0/6 local solves, 0/24 prediction/braking
evaluations, 124.484/3600 charged seconds, 0 workers**. No protocol correction
was needed. The successful Stage 3.41 baseline remains unchanged:

| Outcome | Baseline retained |
| --- | --- |
| Reach | Pass: 0.0076426086 m, tolerance 0.01 m |
| Sampled settling | Fail: late maximum error 0.0581381043 m; speed 1.581015274 m/s |
| Terminal tip speed | 0.635172609 m/s |
| Computation | Mean update 17.075238 s; 35/35 deadline misses; real time unproven |
| Force violations / solver errors | 0 / 0 |

The final prelaunch focused run passed 19 tests in 74.754 s. A separate affected
legacy correction check passed in a five-test run (four overlapping tests).
The post-live repair passed five focused tests in 25.560 s, including the new
read-allowance test. No scientific work is hidden in these tests. The previous
Stage 3.42 aggregate of 22 tests with 10 failures and 6 errors was inspected;
its individual combined traceback log was not retained in the stage files.
The relevant protocol wording regression was reproduced and fixed. The broad
historical route-fixture suite remains uncertified and was not rerun.

All 116 recorded Stage 3.41/3.42 source/evidence files were verified byte-for-byte
unchanged. Compact evidence is sealed against staged Git blob bytes. The next
physical parameter group remains tendon routing/guide lever arms, unopened:
prerequisites are a successful live handoff, consumed discriminating-check
feedback, matched controller/backend verification, and model-scoped braking
evidence at multiple operating points. No mathematical capability gained new
scientific validation in this attempt.

This is a new experiment with its own frozen project ledger and one-shot guard.
Stage 3.41 remains the physical baseline; Stage 3.42's failed attempt is preserved.
The entrypoint is `examples/stage343_diagnostic_feedback.py` (`prepare`, `run`,
`export`) in the existing `softagent` environment. Local artifacts are in
`runs/stage343_diagnostic_cycle_20261001`; compact evidence uses the same basename
under `evidence/`.

The initial design request, saved-evidence report and explicit design response
must exist before numerical work. The same diagnostic session then chooses a
typed check, yields to the sequential coordinator, consumes its receipt/result,
and submits a revision linked to the earlier report. The design role responds
again and reviews any verification. Original reports and responses remain in
the immutable artifact store and handoff history. No workers are started.

Provider recovery instructions name the current role's delivery tools. Each
phase advertises and enforces its actual tool grant. Cumulative correction
usage transfers across roles and feedback; only a completed legal call clears
consecutive usage. The existing four total/two consecutive limits are retained.

The opt-in `readonly_batch_limit=3` accepts only independent `evidence.read` and
`diagnosis.inspect_evidence` calls. All envelopes and domain schemas are checked
before execution. Calls execute sequentially with distinct durable request IDs,
receipts and charges. Handoffs, mutations and numerical work remain standalone.
Absent this setting, old frozen configurations retain strict single-call decoding.

Provider capability check (2026-10-01): the official [Chat Completions schema](https://api-docs.deepseek.com/api/create-chat-completion/)
does not document disabling parallel calls; [Responses compatibility](https://api-docs.deepseek.com/guides/responses_api/)
says `parallel_tool_calls` is ignored. No undocumented parameter is sent and no
provider/model migration is made. The inherited `deepseek-flash` configuration,
credential loader and transport remain in use.

Provider timeout is the minimum of configured maximum, remaining project time,
session time and diagnostic subgrant time. Encoding, transport and reservation
use that timeout, including correction/length recovery. Known completions settle
actual cost; uncertain work retains the existing reservation contract. Model
contexts show project, role, numerical and correction budgets. Model roles use
a 30-second read reservation instead of the executor's 900-second ceiling.

The frozen ceilings are 24 provider attempts, 60 tools, two full backend attempts
(at most one recording and one variant), six local solves, 24 prediction/braking
evaluations, 3,600 charged seconds and zero workers. Diagnostic allocation is at
most 14 attempts/32 tools/1,200 seconds; design has ten attempts. Requests below
the declared workflow minimum or leaving no design-review capacity are rejected.

Checks bind an operation, chosen update, exact projected state, current applied
input (braking) or previous input (local initialization), hypotheses, numerical
settings, receipt and result. A second check needs the first feedback reference
and a specific unresolved need. Local comparisons require explicit adoption of
the same parameter/value and use regenerated cold seeds, not historical plans.
Only `terminal_tip_speed_weight` or `holding_tip_speed_weight` in [0.0001, 1]
may change. Physical design, task, solver limits and integration stay fixed.

The existing improvement gate is retained: reach must pass, late maximum speed
must fall at least 20%, terminal speed and late error may increase at most 10%,
mean update time at most 25%, and forces/errors must remain valid. A partial
speed improvement is separate from sampled settling. Failed variants cannot
replace the baseline. `backends.py` computes the command before fixed-count
MuJoCo stepping; wall-clock misses do not inject simulated physical delay.

Final live outcome and exact usage are recorded in the compact `outcome.json`,
`verification.json` and `final_review.json` when those phases complete. An absent
artifact means that phase did not complete, not a scripted success.
