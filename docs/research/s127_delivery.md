# S12.7 — Evidence working set, scientific admission and session handoff

2026-10-21. Target: `feat/sorosim-matlab-nmpc`, audited baseline
`af3510cb3e3c304b2314c93c57b1ecd3b1db0a98`. An initial ordinary fetch confirmed
matching local/remote heads and a clean target worktree. Other worktrees were untouched.

## A. Deterministic evidence working set

`context()` now exposes `evidence_working_set_v1`; the existing `decision_brief()`
passes it to the existing Agent. It is recomputed from the sole Store, with no
new database, Agent, scientific executor or persistent model memory.

The projection links current candidates, initialized schedules, mathematical
records, NMPC/policy executions and physical evaluations. Compilation, control
initialization, completed mathematics, valid complete physics and original
acceptance are separate fields. Three candidates are previewed, preserving the
best current candidate as well as recent candidates. Source references and the
complete nine-result S12.6 STOP index survive preview truncation. Control arrays,
solver logs and complete trajectories stay behind exact queries. Same-candidate
comparisons require valid complete executions, matching original component limits,
evaluation version and profile. No cross-structure control attribution is made.

`physical_diagnostic()` now adapts both fixed-tension raw samples and saved NMPC
motion using the original task adapter. It provides original evaluator output,
full acceptance, measured extrema, positions, velocities, actual applied inputs,
channel limits and exact source pointers. NMPC post-step motion is explicitly
paired with the preceding interval's measured pre-step input. Optimizer-predicted
tensions are excluded. Unrecoverable data is `unavailable`; a partial archive may
retain the evaluator reference without having its readable body. Partial execution
does not establish a valid task failure, and an early final saved sample is not
treated as the task deadline. No summary reruns a simulator or invents a cause.

[Scientific audit](../../evidence/s127_working_set/audit.json) and
[diagnostic packages](../../evidence/s127_working_set/physical_diagnostics.json)
cover all eight S12.6 physical attempts: seven valid complete failures and one
incomplete attempt. The existing `s12_audit.verify_nmpc` independently reproduced
the original evaluator, full acceptance, saved-state motion and profile for both
NMPC episodes. Reconstruction uses saved states and the existing kinematics
reader; it advances no simulation and runs no optimizer. Large temporary exports
remain in ignored `runs/s127_saved_nmpc_audit`, outside the delivery.

Read coverage uses successful paired `model_original_tool_feedback` **and actual
tool content in saved Provider request messages**. A tool result later offloaded
from model input is not counted as full delivery. Views, escaped JSON pointers,
field subsets, ranges, Study identity, tool IDs and feedback references are
retained. Full data means the requested scope; `full_artifact` separately identifies
an entire artifact. Exact repetitions and previously covered subnodes are labeled,
without disabling reads or asserting model understanding. Tests also cover
summaries, offloading, failed feedback and field/range overlap.

## B. Mathematical operating-point admission

`AnalysisRequest` now owns the missing equilibrium/target-point check and protocol
window membership. `calculate()` reuses that contract instead of maintaining
duplicate checks. Invalid combinations fail at `dispatch()` entry, before guard,
capacity calculation, reservation or worker startup. Existing paired-design,
sensitivity, saved-state identity/dimension/order/phase and remaining-horizon checks
remain authoritative. Tests verify unchanged scientific ledger and state on rejection.
Normal already-incurred Provider/public-tool accounting is unchanged.

Legal requests still rely on the existing mathematical tool to construct and
verify their operating point. They do not claim numerical success. Neither solvers,
static-equilibrium meaning nor S12.6 failed-attempt charges were rewritten.

## C. Optional control methods and handoffs

NMPC, offline NLP, response search, pattern search, Direct PPO and Residual PPO
remain available under their existing contracts. Method descriptions explain scope,
cost and limitations without choosing an experiment. Candidate-specific PPO rows
show existing stage/action/evaluation budgets and remaining environment/allocation
checks; `prerequisites_only` is explicitly weaker than full scientific admission.
Direct PPO requires no mathematical or NMPC reference.

Existing `compatible_references()` already refreshes after NMPC/mechanics
settlement, reads actual NMPC interval inputs, publishes a bound reference once
and reuses it without another NMPC rollout. A complete failing execution is not
rejected merely for failing the task. The tightened check requires the **ordered
full grid**, rather than membership of every time in a possibly permuted grid.
Candidate/configuration/task/order, finite SI inputs, original bounds, horizon,
file identity and registered ownership remain checked. Reference rows identify
measured NMPC inputs versus mathematical prediction. Regressions reject incomplete,
unordered, repeated-time, nonfinite, out-of-bound and mismatched references; the
existing channel-order regression is also retained. Training, continuation,
checkpointing, independent evaluation and worker lifecycle code are unchanged.

NMPC convergence, prediction, valid MuJoCo execution and original acceptance stay
separate. No reliable model-error bound was introduced, so NMPC is not a hard
structural infeasibility veto or an automatic SELECT gate.

## D. Independent numerical capability audit

[Saved-evidence validation](../../evidence/s127_method_validation/saved_evidence.json)
uses existing observations only, separately from formal Agent research:

| Frozen historical case | Initial normalized violation | Best measured violation | Outcome |
|---|---:|---:|---|
| P1 response search | 1.090705 | 0.054502 | Still failed |
| P1 pattern search | 1.090705 | 1.048252 | Still failed |
| S12 response positive control | 2.419092 | 0 | Original independent acceptance passed |

The S12 audit reconstructs both twelve-column finite-difference Jacobians from
saved callbacks, reproduces their singular values and ranks, and exactly rebuilds
all saved applied schedules and coefficient time supports with the existing
control functions. That historical search recorded 27 callbacks, 26 fresh physics
evaluations, 24 response probes, one reuse and 30.482280 charged numerical seconds.
These are historical costs, not new S12.7 expenditures.

P1's local solver predicted near-zero violation while its best actual result still
failed. This is evidence of local approximation limits, not global structural
infeasibility. Measured input saturation does not establish that all feasible input
directions are blocked. Reproduced time support does not establish that a basis
is sufficient. Different tasks, structures, budgets and bases prevent a general
method ranking. Saved evidence answered these questions; no extra physical or
training Study was launched.

Five existing saved-SoRoSim analysis tests also pass: recorded operating-point
derivatives, mass/residual matrix relations, target equilibrium residuals, loaded
input and paired full-rebuild design sensitivities, distinct feasibility scopes,
and the existing entrypoint with saved models and failed constructions. They use
stored numerical results and local linear algebra, with no MATLAB engine solve.

## E. Safe session handoff: not admitted

[Admission record](../../evidence/s127_checkpoint/admission.json) retains
`not_admitted`. There is no production rotation implementation or enable switch.
The original continuous Strands conversation and DeepSeek reasoning path remain.

The existing S12.6 prototype is reused in five checkpoint test methods. Eleven
additional killed-process subcases use real SDK snapshots and a real Store,
reopened in the parent process: preparation, Store-before-snapshot,
snapshot-before-pointer, committed pointer reuse, unknown first send,
saved-unconsumed response, completed-math feedback marker, completed-physics
feedback marker, RL-running status, pass-before-SELECT and STOP.

Old SDK messages/reasoning restore exactly. The SDK/tool-round regression retains
tool IDs and paired results. Unknown sends block another request; two replay
reads of one saved response make no new send or charge. Unsafe pending states,
RL, unselected success and STOP reject switching. Ledger identity survives reopen.
HTTP replies, usage fields, completion markers and RL status here are explicit
fixtures; there were zero external requests, real science executions or training.

The test **confirms a real protocol gap**: the prototype can commit the Store's
new session pointer while no new SDK snapshot exists. A different interruption
leaves a prepared SDK snapshot while the old pointer remains. There is no validated
production prepare/commit/reconcile protocol covering both stores. Actual
mathematical/MuJoCo worker recovery and feedback consumption through a new
conversation, and an authorized real-provider scientific continuation, remain
unverified. Pending completion markers test rejection, not that recovery capability.
These blockers are why the production checkpoint stays closed.

The original checkpoint test now writes disposable exports under its own ignored
run directory, preventing regression runs from overwriting sealed S12.6 evidence.
An older synthetic RL hook fixture now declares its allocation so existing budget
feedback can read the same field required of real runs.

## F. Verification, costs and next research

[Verification inventory](../../evidence/s127_working_set/verification.json) records
184 distinct passing test IDs: a 147-test regression, a final 41-test targeted
regression with overlap, five saved-mathematics tests, and five checkpoint tests. The cross-process method
contains eleven interruption subcases. Installed MATLAB engine import paths and
the frozen `OPENBLAS_NUM_THREADS=OMP_NUM_THREADS=MKL_NUM_THREADS=1` environment are
required. `git diff --check` passes. There are no unresolved test failures.

Production changes are confined to six existing files: **+217 / -20, net +197
lines**. The full per-file inventory is in the verification record. No scientific
algorithm, original task/evaluator, reward function, budget ledger, frozen archive
or production Provider/reasoning/session implementation changed.

S12.6 has eighteen read attempts, sixteen successful feedbacks, fifteen exact
model deliveries and fourteen full-or-selected-scope data deliveries. One range
result was offloaded. Among delivered queries, exact repeats and covered-subnode
reads are both zero; fifteen are new query scopes. Whether these were unavoidable
scientific queries or understood by the model is not measured. There is no honest
baseline duplicate-reduction claim from this dataset. The final working set is
55,315 serialized UTF-8 bytes; the corresponding decision brief is 107,041 bytes.
These are output sizes, **not measured token savings**.

New external Provider requests, mathematical/physical scientific launches and
training actions are all zero. New actual prompt/completion/cache-token metrics,
legal live proposal rates, first useful live request, and feedback-driven live
method changes are unmeasured. Historical S12.6 usage is unchanged. No new formal
success-rate or interface-efficiency claim is made.

The [six-pair, twelve-request probe proposal](../../evidence/s127_working_set/decision_probe_proposal.json)
and [next cold-study configuration proposal](../../evidence/s127_working_set/next_study_proposal.json)
are reviewable future scopes, not authorizations or runnable frozen experiments.
They require new Provider/output caps, source/readiness freezing and project-data
transfer approval. The old S12.6 authorization cannot be reused. The future cold
Store must remain empty of engineering/probe designs, controls and mathematics;
all original task thresholds and optional methods remain. No 48-request Study ran.

[Upload-scope review](../../evidence/s127_working_set/data_scope.json) covers code,
explicit fixtures, derived numerical measurements and reference metadata only.
No raw Provider request/response, reasoning, original model tool-feedback body,
credential or full Store/SDK archive is added. S7–S12.6 sealed evidence is untouched.
Ordinary commits/pushes target only the authorized feature branch; final delivery
SHA and verified remote/worktree state are reported in the chat.
