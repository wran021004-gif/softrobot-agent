# Completed bounded NMPC feasibility-recovery investigation

Regeneration restored numerical feasibility under unchanged tensions and
preserved useful predicted motion. The one recovery-enabled closed-loop run
substantially improved sampled position and speed, but **failed the unchanged
holding-speed acceptance limit**. This supports a bounded inspection/test
procedure; it does not support always enabling recovery or LLM superiority.

| Recorded local plan at update20 / .20s | Feasible selected initialization | Rejected15s return | Regenerated15s return |
|---|---:|---:|---:|
| Objective, original definition |1697.085748|22.306039|22.260486|
| Maximum scaled residual |2.93e-14|.0426871|8.78e-13|
| Dynamics rows above unchanged1e-5 |0|120|0|
| Predicted error at .30s |180.449mm|5.045mm|4.819mm|
| Predicted speed at .30s |.367882m/s|.101116m/s|.102305m/s|

Every tension and switching time was preserved. Ten existing implicit root
solves regenerated states from the recorded measured state, using saved states
only as guesses. All original constraints and objective components were evaluated
without launching IPOPT. Maximum state changes versus the rejected plan were
.0083593rad/m in curvature and .459820rad/(m*s) in rate. Objective and position
improvements survived; speed slightly worsened versus the rejected plan, while
improving versus the feasible initialization. The feedback's
`horizon_end_speed_improved` uses the feasible selected plan as comparator.
The .30s horizon endpoint is outside the .35s terminal acceptance question.

| Actual sampled closed loop | Imported recovery-disabled baseline | New recovery-enabled run |
|---|---:|---:|
| Terminal error at .35s |95.525mm|3.016mm|
| Maximum holding error, inclusive .30-.35s |193.152mm|3.464mm|
| Maximum holding speed |3.249830m/s|.024643m/s|
| Initialization selections |30|3|
| Recovered deliveries |0|6|
| Other feasible deliveries |35|29|
| Noninitialization feasible deliveries |5|32|
| Solver exceptions / unusable plans |0 /0|0 /0|
| Mean complete control update |19.292s|15.432s|
| Task acceptance |fail|fail|

All35 commands were delivered. Recovery was attempted six times, selected six
times, failed zero times, and used60 root solves. Recovered update IDs were
`[0,1,2,3,13,23]`; other feasible deliveries comprise26 noninitialization IPOPT
plans and3 selected warm initializations at updates32-34. These latter seeds
carried the changed schedules from earlier successful deliveries. The flag
was active throughout all35 updates. Recording a detailed snapshot at update20
did not limit recovery to update20; that update actually delivered the
IPOPT-selected iteration6 plan. Snapshots explicitly retain `selected` and
`delivered`, and retain `regenerated` when attempted and recorded.

Holding-speed samples at .30s (.020494m/s) and .31s (.024643m/s) exceed .02m/s.
All six inclusive holding-position samples and terminal-position acceptance
pass. Terminal speed is .008934m/s. The evaluator's position-only task success
does not override the full reach-and-hold acceptance (`valid_failure`). No
weights, threshold, holding window or timing were relaxed.

There are35 aligned first-step comparisons in each execution. Maximum tip
prediction disagreement fell9.445mm to3.576mm, mean3.683mm to2.832mm; maximum
velocity-vector disagreement fell.222288 to.088021m/s. Disagreement remains.
The prior same-time projection differences4.3975mm/.021396m/s were reused
without repeating the study. All35 wall-clock delivery deadlines were missed;
simulation advances synchronously without skipped virtual-time actions. No
real-time, continuous-time, hardware or uniquely dominant causal conclusion
follows. One new run does not establish robustness across states or repetitions.

The [residual audit](../evidence/nmpc_feasibility_20261011/residual_audit.json)
reconstructs both paired source problems, including measured state, previous
input, absolute timing/holding flags, effective horizon, variable/constraint
order and scaling. Identical initial/selected and returned/retained vectors
are explicitly aliased. Rows0-11 per interval are kinematic residuals
`(q_next-q_previous-h*qdot_next)/10`; rows12-23 are implicit generalized force
balance divided by.001N*m^2/rad. The30s returned `dynamics_5_13` is
`near.kappa_y_node_1` at .25-.26s, magnitude9.537607e-7N*m^2/rad. Its retained
least-infeasible `dynamics_4_13` is the same coordinate at .24-.25s,
7.145890e-7N*m^2/rad. The audit includes signed/absolute values, denominators,
units, group counts, ranked rows and exact inertial/velocity/elastic/damping/
gravity/tendon decomposition, closing to floating-point precision. These are
generalized force residuals, not Cartesian or tendon-force errors; a small
physical residual does not bound trajectory error.

DeepSeek made three native decisions: regenerate the15s rejected returned plan
(deduplicating identical checkpoint1), run the single permitted flag revision
after consuming feedback, then STOP after actual simulation feedback. It did
not request the optional second schedule or warm/cold NLP comparison. The task
supplied the recovery method and experiment menu; Codex supplied engineering,
factual arithmetic and startup case/procedure context. This was supplied prior
context, not autonomous memory retrieval. Complete original requests, tool
feedback and decisions remain in the immutable archive/events.

The [original STOP](../evidence/nmpc_feasibility_20261011/plan_02_stop.json) is
preserved unchanged. Its unsupported duplicate-operation claim, confusion of
used and remaining budgets, update20-only interpretation and speed-comparator
interpretation are addressed in a separate
[factual correction](../evidence/nmpc_feasibility_20261011/post_stop_factual_correction.json).
One fresh regeneration and one fresh simulation occurred, each once. Repeated
appearance of their references in current packets and evidence retrieval is
not a numerical repeat. No provider request followed accepted STOP; transport
closed in `finally`.

| New activity work | Actual | Ceiling |
|---|---:|---:|
| Distinct saved regenerations / root solves |1 /10|2 schedules,180s each|
| Standalone local NLP attempts / warm comparisons |0 /0|2 attempts,300s combined|
| MuJoCo launches / internal NMPC solve attempts |1 /35|1 launch,1800s|
| Internal recovery attempts / roots |6 /60|one attempt per update, within simulation|
| Actual provider sends / public calls |3 /8|16 /64|
| Scientific function wall charged |618.417s|3600s|
| Conservative science plus saved native boundary |621.043s|3600s|
| Activity start through sealed closeout |1714.491s|21600s,1800s delivery reserve|
| Codesign / BDF / hardware / other models |0 /0 /0 /0|0 /0 /0 /0|

Preparation/audit27.492s; focused checks20.336s including the corrected test
fixture failure; configuration inspection2.324s. Saved regeneration numerical
preparation9.351s, integration4.520s, verification.116s, complete numerical
result14.219s; scientific function charge15.312s and full native receipt17.938s
have distinct scopes. Simulation548.171s, evaluation2.125s, profile2.281s,
construction.376s, complete closed-loop charge552.953s. Native provenance and
reporting overhead is charged in the global ledger; the conservative total
adds the saved native boundary overhead explicitly. No numerical retry,
reporting recovery, counter reset or additional launch occurred.

Nine of eleven relevant existing checks passed, with two tests skipped because
local-only historical Stores are absent; committed archives were used instead.
Six final focused checks passed, covering rejected-vector selection and row
mapping, evaluation through serialization without hidden NLP, root-return
equation checks, preservation of the feasible incumbent/status/iteration count,
flag propagation and distinct delivered-plan evidence. One existing synthetic
contract test ran a toy IPOPT solve; it is distinct from scientific local NLP
attempts. No full suite or broad campaign was run. Ordinary controller
observations do not retain all per-update iteration counts; update20's snapshot
retains its returned count and trace. Missing aggregate counts are reported as
unknown, not inferred from elapsed time.

Implementation and frozen specification were committed before binding at
`3535db738326f9adb117fcb10527736060007757`. The fetched source branch remained
reviewed commit `b83b5b4fe03f97ccca3ad173187c0d80bb65ceba`. The isolated delivery
branch is `feat/nmpc-feasibility-recovery`; original checkouts were preserved.
The existing environment/lock were reused without upgrades. Exact execution
commands and paths are in the [runbook](nmpc_feasibility_runbook.md).

The [scientific summary](../evidence/nmpc_feasibility_20261011/scientific_summary.json),
full regenerated vectors, closed-loop observations/snapshot/configuration,
receipts, source ownership/hashes and archive manifest preserve the evidence.
The [case draft](../memory/nmpc_feasibility_case_draft.json) extends the prior
case; the [procedure](nmpc_feasibility_procedure.md) remains recommendation-only.
The known legacy admission mismatch was not repeated; no database, provenance
migration, validation, automatic reuse or human approval is fabricated.
