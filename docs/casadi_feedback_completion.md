# CasADi feedback research, 2026-10-10

The numerical engineering phase is complete. The real DeepSeek research cycle
is executing in the same fresh activity; this report will be finalized after
its returned evidence and disposition. No task acceptance or physical validation
has been established at this checkpoint.

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

Current scientific costs before optimization: 381.853 numerical process seconds;
two public scientific tool calls. Model-selected solve/replay results, final
provider costs, decision trace, final disposition and push identity are pending.
Physical validation is optional and no MuJoCo launch has been requested.
