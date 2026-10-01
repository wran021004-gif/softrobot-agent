# Stage 3.43: bounded diagnostic feedback

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
