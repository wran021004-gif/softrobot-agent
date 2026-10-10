# Bounded feedback research, 2026-10-10

This activity starts from CasADi pilot `94fa3b22`, in isolated branch
`feat/casadi-feedback-research`. Historical activities remain sealed STOP.
The user attachment authorizes the fresh ceilings in
`examples/casadi_feedback/specification.json`; rerunning prepare does not reset
them. The activity clock includes implementation and protects the final 30 minutes.

Use the existing Python 3.11.16 environment with CasADi 3.7.2, SciPy 1.17.1,
MuJoCo 3.13.0, Strands Agents 1.59.0 and Harness 0.2.0. No installation is needed.

```powershell
Set-Location D:\softrobot-agent\.worktrees\casadi-feedback-research
$studyPython = 'D:\softrobot-agent\.mainline5-env\Scripts\python.exe'
& $studyPython -m tools.research_casadi_feedback prepare
# Commit implementation and specification before any scientific dispatch.
& $studyPython -m tools.research_casadi_feedback bind
& $studyPython -m tools.research_casadi_feedback diagnose
& $studyPython -m tools.research_casadi_feedback speed
& $studyPython -m tools.research_casadi_feedback live
& $studyPython -m tools.research_casadi_feedback export
& $studyPython -m tools.research_casadi_feedback stop
& $studyPython -m tools.research_casadi_feedback export
```

These commands document a single authorized activity, not permission to repeat
it after STOP. `status` reads current usage. `migrate --reason ...` binds a
committed scoped repair to the same activity, preserving usage and original
implementation identities. Pending numerical/provider outcomes must be inspected
before any new dispatch; unknown work must never be automatically repeated.

The prescribed diagnosis uses corrected A iteration 59, source artifact
`baae52d1f11518a40982491879c4a0ab380c519a617a0588e989a0e496bebbf2`,
selected artifact `6f121f12f89af153953972e5140b4e2fdd4b77ddb089fbc8c340457198af97b9`.
It reads the existing ordinary corrected solve/replay files, and imports only
the selected archive member without extracting the historical archive.
Original and refined implicit trajectories begin at zero and keep all 35
commands, lengths and switches. Root failures and partial horizons are retained.
One BDF precision check tightens tolerances by 100 times. Node comparisons and
dense replay metrics are distinct; no additive attribution to unique causes is assumed.

The sole speed trial removes forced reverse AD from the local step function,
while keeping exact automatic AD at the full-NLP boundary. It compares local
and full derivatives on identical saved inputs, separates construction/cold/warm
evaluation, and estimates setup repayment. Automatic local execution is used
only if values and exact derivatives agree and the observed gain exceeds 5%
with repayment within 30 Jacobian calls. Otherwise the prior local implementation
is retained. No NLP is launched for timing. Focused plan, rollout and actual-graph
slack/initialization checks run inside this same reservation; old mechanics
verification is reused.

Candidate generation adds two shared nonnegative slacks to normalized squared
position/speed inequalities. Dynamics, initial state, lengths and input bounds
remain hard. The weighted task-gap objective may add a secondary effort/variation
coefficient at most 0.001; this is a weighted tradeoff. Original-task acceptance
never subtracts slack. Retained candidates rank by hard validity, original gaps,
then effort, independently of the relaxed constraint violation and changing weights.
Initial guesses are regenerated from zero at the chosen design/grid using
constant 0.2 N, the existing ramp, or an exact referenced schedule. These are
numerical guesses, not changed physical initial conditions.

One real DeepSeek principal uses `build_harness`, `LiveBoundary`,
`live_model_class`, native typed `PythonAgentTool`, sequential execution, Host
and Store. Credentials are loaded with `load_credential(Path.home()/'.codex'/'.env')`
only for live sends. The accepted provider/model/transport settings remain unchanged.
The boundary retains sanitized original wire requests and original response
bytes, including actual usage; it never persists authorization headers.
Continuations stay in the existing asynchronous invocation runtime, and the
transport closes with `await boundary.aclose()`.

`research_plan` records the principal's hypothesis, evidence, falsifier, frozen
conditions, domain/objective/weights, initialization/grid and stopping rule.
An accepted batch dispatches one or two choices sequentially and independently
replays usable schedules before returning compact feedback. The model then
owns revision, a supported diagnostic replay, or STOP. A second batch is capped
at two solves. STOP must cite an actual new result. The before-model packet and
native requests/results are archived separately from prescribed engineering work.
Full artifacts can be inspected through native `evidence_read` by exact reference
and JSON pointer; basic numerical results are supplied directly.

Every scientific worker requires the shared active reservation and uses the
same ledger. Solves reserve 900 s including construction/extraction, with IPOPT
570 s settings under a 600 s solve ceiling. Replays reserve 450 s; diagnosis
900 s and the speed/check investigation 600 s. Actual elapsed process time is
charged once, including known timeouts. Initial investigation is capped at 1800 s
within the 7200 s numerical total. Tool plan/read reservations are cheap and
distinct from scientific worker reservations. Provider sends count auxiliary
requests, and the final four sends are protected for feedback and closeout.

Physical evaluation is optional. The implemented research tool menu is numerical;
no optimized-tension-schedule MuJoCo execution path is claimed. Existing controller
11 would test geometry with different closed-loop inputs. This round can complete
with zero physical launches. Any later supported physical question must preserve
the single launch/1800 s ceiling and record its exact execution semantics.

Export retains compact operation JSON, original plans, cumulative state/calls/events,
the ledger, decision packets and a hashed immutable artifact archive. Interpret
relaxed feasibility, original feasibility, replay accuracy and physical validation
as separate findings. Task success, a speedup and a second batch are optional;
a model-selected execution followed by actual evidence-based revision or STOP
is required. A blocked live cycle must be labeled incomplete.

The actual 2026-10-10 activity is now STOP with candidate/replay and requested
revision incomplete; its 24 provider sends are exhausted. See the completion
report for both implementation failures and the original model STOP text.
The two initial NLPs really ran but failed candidate export. Delivered recovery
now saves the solver-return checkpoint before extraction; this cannot recover
vectors already lost by the old version. Revision requires source-matched replays
only for initial candidates that actually exist. Final four sends expose a typed
STOP-only plan schema and new-result-only evidence reads; an accepted STOP cancels
further sends. These last repairs have focused test coverage and have not been
validated by an additional live cycle. These commands must not reopen this study.
