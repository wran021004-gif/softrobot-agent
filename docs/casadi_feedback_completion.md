# CasADi feedback research, 2026-10-10

This study is stopped with the required candidate/replay research cycle **incomplete**.
The real DeepSeek principal chose a batch, consumed execution failures, requested
a revision, and returned an original STOP text. Two actual refined-grid NLPs ran,
but an export bug lost both candidate vectors. A second guard bug then blocked
the requested revision. All 24 provider sends were consumed. No new candidate
replay, original-task acceptance, or physical validation was established.

Branch `feat/casadi-feedback-research` starts at pilot `94fa3b22` in its own
worktree. Implementation/specification were committed as `e5834241` before
dispatch; scoped incumbent/accounting repair `6092b3aa` preserves the original
diagnosis identity and cumulative allowance. Historical activities remain STOP.
The [runbook](casadi_feedback_runbook.md) and
[frozen specification](../examples/casadi_feedback/specification.json) define
reproduction, choices, acceptance and ceilings.

Corrected A iteration 59 was reconstructed from zero with its fixed lengths,
all 35 saved six-channel tension commands and original switching times.
Both tight implicit rollouts and the single BDF precision check completed.

| Comparison at common original nodes | Maximum tip difference, mm | Maximum tip-velocity vector difference, m/s |
|---|---:|---:|
| Saved NLP / tight original grid | 0.00058875 | 0.0000130802 |
| Tight original / two-step refined grid | 3.743508 | 0.0467243 |
| Refined grid / saved BDF | 4.364860 | 0.0529871 |
| Saved BDF / tighter BDF | 0.000000006326 | 0.0000000004708 |

Saved normalized dynamics residuals reached 2.499e-4. Tight original/refined
reconstruction residuals reached 1.948e-10/3.345e-10 with no root failures
(requested root tolerance 1e-11; actual evaluated residuals are retained).
The tightly reconstructed original trajectory closely matches the saved states,
while changing the time grid changes the task prediction substantially. Tightening
BDF tolerances by 100 times changes the result negligibly in this one check.
This supports substantial discretization effects for this schedule, with remaining
refined-grid uncertainty. It establishes neither a unique cause nor convergence
of the 0.005 s grid; no additive percentage attribution is made.

| Fixed-schedule trajectory | Terminal error, mm | Maximum holding position error, mm | Maximum holding speed, m/s |
|---|---:|---:|---:|
| Saved NLP | 9.811832 | 9.817871 | 0.0220791 |
| Tight original grid | 9.811488 | 9.817743 | 0.0220839 |
| Tight refined grid | 6.993894 | 7.788783 | 0.0528863 |
| Precision BDF, dense | 5.483066 | 6.875549 | 0.0979991 |

All four miss the original 0.02 m/s holding-speed limit. Dense BDF metrics are
kept separately from node comparisons and sampled evaluator quantities.
The diagnostic process took 215.608 s, including two reconstructions and one
new BDF check; the saved BDF was reused without rerunning its experiment.

The sole speed trial removed local forced reverse AD while retaining automatic
exact AD at the full-NLP boundary. It compared three saved local points and
one common full-NLP point. Values and derivatives agreed exactly in these checks.
Local warmed derivatives remained approximately 0.08 s per point; full warmed
Jacobian means were 5.211792 s (prior local reverse) and 5.163114 s (trial).
The approximately 0.94% apparent difference does not establish a useful gain.
Trial mechanics/assembly/full-derivative construction cost 1.526/28.381/17.548 s,
and estimated repayment was 974.9 Jacobian calls, beyond the chosen study gate.
The trial was not adopted. Outer NLP AD remains automatic; local step AD keeps
its prior reverse setting. No compiler or extra NLP benchmark was used.

The speed/check worker took 166.245 s. Four focused unit checks passed; one
actual mechanics graph at nonzero design `d=-0.5` verified coherent zero-state
initialization (hard residual 5.019e-11), two shared slack semantics, and separation
between relaxed feasibility and original task failure. Prior mechanics verification
was reused; the 92-comparison check was not repeated.

Candidate generation keeps dynamics, zero initial state, design and force bounds
hard, and adds two shared nonnegative position/speed task slacks. Search minimizes
weighted normalized gaps, optionally with a bounded effort tradeoff. Original
acceptance never subtracts slack. The generic solver retains an additional
caller-ranked incumbent from every finite noninitial callback, using existing
state/constraint outputs without another mechanics evaluation. Selection prioritizes
hard validity, original task gaps, then effort. Raw returned states and retained
assessments remain available even when another incumbent is selected.

The first real principal plan requested two sequential open-length `task_gap`
solves on the refined state grid at equal weights, starting with constant 0.2 N
and the existing 0.2-to-0.4 N ramp. Both use 35 original control intervals and
the prescribed physical zero state. Its hypothesis is that refinement will
produce more faithful predictions and reduce independent replay disagreement.
The original plan and what the model saw are preserved; this is the model's
choice, not a prescribed Codex batch. Numerical software owns execution and
replay; the principal owns its later revision or stopping decision.

The initial plan incorrectly called historical infeasible returned iterates
"optima", asserted a unique discretization cause, and misstated the local AD
setting. A separately labeled Codex engineering correction was recorded for the
next model packet. It preserves the original model request, corrects interpretation
and actual execution settings, and does not prescribe a revision or STOP.

Two automatic approval reviews rejected the first live dispatch before execution,
requesting destination/payload-specific authorization. The user then explicitly
authorized this non-secret research packet to `https://api.deepseek.com/chat/completions`.
The same activity continued with its original counters; no provider send was
charged for either rejected process launch. Credentials and authorization headers
are excluded from saved requests and evidence. This access issue is resolved.

## Actual execution and failed revision

Both initial choices really reached IPOPT's reported optimal-solution termination
under implementation `6092b3aa`. The immutable worker logs establish this, even
though the Host's generic backend counter covers physical launches and its
generic receipt does not identify these extension-owned NLP executions.

| Initial choice, refined grid | Iterations | IPOPT reported time, s | Process time, s | Unscaled constraint violation | Objective |
|---|---:|---:|---:|---:|---:|
| Constant 0.2 N | 18 | 221.178 | 274.566 | 6.854376e-10 | -1.998000006e-8 |
| Existing ramp | 21 | 259.993 | 315.092 | 3.3303056e-9 | -1.950329427e-8 |

The worker then raised a duplicate `candidate` keyword error while constructing
its return dictionary. Both results are recorded as `numerical_error`; neither
has an exported candidate reference. Tiny negative objectives are consistent
with numerical bound relaxation (reported violations approximately 1e-8), and
do not establish negative physical task gaps. Without the vectors, the original
unsoftened metrics, lengths, selected incumbent, and independent replay cannot
be verified. Solver termination alone is insufficient for acceptance.

The scoped packaging repair removes the duplicate and writes a sanitized solver
return checkpoint before candidate extraction. Its mock regression passed without
an NLP; two earlier test attempts encountered Windows temporary-directory access
errors and remain recorded. This repair cannot reconstruct the already lost
vectors. During repair, incompatible source identities rejected public tools;
the native harness nevertheless consumed further provider sends. A temporary
dispatch hold stopped that activity without resetting its clock or counters.
A committed before-model dependency guard now checks compatibility before send.
Migration retained the frozen physical instance, original NLP identity, and all
24 cumulative request charges.

After consuming the failure and committed-repair feedback, the principal requested
two revision choices: constant input at equal weights on the refined grid, and
the ramp with speed weight 2 and position weight 1. These were never executed.
The service incorrectly required an initial candidate replay even though both
initial exports failed and no candidate existed. The principal attempted further
plans and evidence reads, including the already supplied historical BDF result,
while the guard continued to reject revision.

Request 24 returned original plain text with final disposition STOP. It cited
the export failures and unresolved replay prerequisite. The original response
is retained unchanged in `model_original_final_disposition.json`. No typed STOP
plan was accepted. Its statements that no refined NLP had executed and that
"1 unprotected + 4 protected" sends remained are factually wrong: two refined
NLPs ran and zero sends remained. Earlier model claims of historical optimality
and a uniquely identified discretization cause are likewise not endorsed.
The wrapper's attempted subsequent send was rejected before transmission.
All sent requests have settled responses; no unknown provider or worker outcome
remains. The engineering closeout records incomplete status rather than inventing
a model plan, candidate, successful revision, or replay.

The final repair requires replay only for available initial candidates, matching
each replay to its source candidate. Two focused guard/schema tests passed under
the same engineering ledger with zero provider sends and zero NLPs. The final
four-send policy was not fully enforced in the live version: sends 21/22 revisited
supplied historical evidence and send 23 requested a blocked batch. The delivered
wrapper narrows the native plan schema to STOP and evidence reads to new result
references in that window, and cancels any send after accepted STOP. These last
guards were checked with focused tests and source inspection; they were **not
exercised by another live cycle**, because the 24-send allowance is exhausted.

## Decision and evidence trace

`decision_trace.json` links every actual send to its before-model packet, original
wire request/response, usage, native requests, and returned feedback. The hashed
archive preserves the full bodies; the compact trace does not substitute for them.
The scientific sequence is prescribed diagnosis/timing, principal initial batch,
two export failures, separately labeled engineering corrections/repair, requested
but rejected revision, historical evidence reads, and original final STOP text.
Only one batch plan was accepted. No candidate schedule was available for a new
independent BDF replay. The prescribed fixed historical schedule precision check
is a diagnosis, not a replay of a new optimized schedule.

`result_summary.json`, `ledger.json`, `state.json`, `calls.json`, and `events.json`
retain final exact costs and identities. The sealed closeout accounts for elapsed
engineering time as well as scientific workers, checks and provider time. Ordinary
Git delivery follows that recorded closeout snapshot. Budgets are never reset,
and unused solve slots do not authorize further sends or restarting this activity.

| Consumed quantity | Actual |
|---|---:|
| Full NLP executions, initial / revision | 2 / 0 |
| New candidate BDF replays | 0 |
| Prescribed fixed-schedule precision BDF checks | 1 |
| Numerical process time, s | 971.5112324 |
| Initial investigation subset, s | 381.8531265 |
| Actual provider sends | 24 / 24 |
| Public workflow calls | 21 / 96 |
| Provider elapsed time, s | 197.595 |
| Provider prompt / completion / total tokens | 909009 / 43193 / 952202 |
| Prompt cache hit / miss tokens | 96256 / 812753 |
| Physical launches | 0 |

The provider reported no monetary charges; no billing estimate is inferred.
Provider cache fields are reported usage rather than proof of a specific charge.
Each individual solve stayed below 600 seconds, numerical work stayed below
7200 seconds, and initial investigation stayed below 1800 seconds. The full
activity clock is reported in the final ledger; the original final-30-minute
delivery reserve was preserved. The hard 24-send ceiling held; its protected
closeout-use policy failure is explicitly reported above.

The useful scientific findings are the schedule-specific grid sensitivity and
the absence of a justified speedup in the one measured trial. The new formulation
and guard repairs are reviewable, but this round establishes neither a successful
candidate nor physical impossibility, global optimality, joint-design benefit,
or LLM superiority. Implementation failures prevented the requested candidate
generation/replay and revision cycle. Historical activities remain sealed STOP.
