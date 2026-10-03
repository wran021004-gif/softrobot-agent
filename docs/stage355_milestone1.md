# Stage 3.55 working state and Milestone 2 boundary

Milestone 1 passed its offline gate: eight new checks and 23 directly affected
Milestone 0 checks passed, with affected reruns after fixes. The six saved
single/dual provider payloads range from 190,363 to 268,991 bytes under the
unchanged 400,000-byte cap. This stage made zero new provider requests, backend
simulations, numerical optimization runs, workers or subagents. Milestone 2
remains interface preparation only. Source pointer checks cover both
`CandidateInput.effective` and `SessionSnapshot.input` wrappers.

`platform.working_state@1.0.0` is a typed read-only projection in
`schemas/working_state.py`, produced by `tools/working_state.py`. It joins the
existing SQLite session, immutable artifacts, public accepted role transitions,
completion stages, context-local evidence catalog and budget ledger in one
read-only transaction. It creates no sessions, events, artifacts, aliases,
receipts, reads, grants or charges. A public accepted product is distinct from
private reading history and an unaccepted draft. Public workflow products belong
to the existing one-workflow-per-project organization; catalogs stay local to
the requested context.

The consumers are `Host.context` -> `platform_models.input_for/payload_for` ->
the single/dual native adapters, and `examples/stage355_inspect.py`. The flat
adapter retains the view; the scoped adapter preserves its canonical IDs through
native function-name substitution. Existing native tool names, exact alias
spellings and legacy long handles still work. Alias persistence now occurs in
successful evidence acquisition/handoff, rather than provider payload encoding.
Legacy stores expose whether their actual alias table exists. Payload encoding
may prepare the legacy adapter's deterministic presentation in memory, without
changing those stores or their compatibility metadata.

```powershell
& 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe' examples/stage355_inspect.py runs/stage354_milestone0_20261003/dual_context
& 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe' examples/stage355_inspect.py runs/stage354_milestone0_20261003/dual_context --run-id gvs-stage354-68b86eee4963-design
```

The view includes task/evaluator identity; role, phase and session status;
baseline; proposed and prepared candidates; latest tested configuration;
prepared/executed scope agreement; explicit selection (including recorded null);
accepted initial/revised reports, feedback and final decision references;
completion stages, pending/unsealed operations; private permitted evidence
references and catalog compatibility; project/session/role-grant/phase capacity;
recovery counters; installed versus permitted actions with reasons; the two
demonstrated parameter impacts; and an actual experiment/search plan or null.
No low-level controller trajectory plan is promoted into an experiment plan.
An installed `policy.search` method binding is also distinct from an authored
plan. Only an explicitly retained `experiment_plan` artifact reference qualifies;
these saved workflows have none.

Completion is a computation fact. Delivery requires an accepted final decision.
Validity and terminal reach acceptance are separate from joint reach/holding.
The latest tested candidate is never substituted for the selected candidate.
Null selection never selects the baseline. Stage 3.53 therefore remains complete
in computation and incomplete in delivery. The fresh Stage 3.54 single workflow
retains baseline, while the dual workflow records `defer_selection` and null.

`Store.spendable` factors the existing reservation gates and is consumed both by
`Store.reserve` and this view. `remaining` provides nominal ledger remainder;
`phase_remaining` retains the original downstream protections and started-usage
ceilings. Unsealed operations already carry reservation charges in that ledger;
the view does not subtract them again. Permission uses frozen bindings, registry
inspection, request grants, `phase_tools` (including reading allowances), session
and pending state, final delivery, and ledger capacity. Action permission is a
phase-level observation; exact arguments, dependency compatibility, resources,
preflight costs and resume/continuation still pass through the existing Host.
An installed capability confers no grant. The Stage 3.54 saved-response repair is
not exposed as a general recovery action.

## Acceptance sources

`tools/acceptance_definitions.py::resolve_acceptance` interprets frozen effective
configuration and sealed profile/comparison references, with versioned source
pointers and explicit missing definitions. It is used by the projection,
`execution_completion.structured_feedback`, and
`diagnostic_revision.comparison_view`. `campaign_metrics` uses the official
frozen reach outcome and recorded settling limits; the ranking policy has a
single definition, still re-exported as `settling_campaign.RANKING`.

| Definition | Authoritative contract/source | Interpretation |
|---|---|---|
| Terminal reach | Task evaluator `evaluate.reach`, `parameters.data.tolerance_m` | Final world position error; saved tolerance 0.01 m |
| Holding interval | Effective controller `parameters.data.settling.window_s`; task timing | Inclusive final `[duration-window, duration]`; saved window 0.05 s |
| Holding position/speed | Controller settling `position_limit_m`, `speed_limit_m_s` | Saved limits 0.01 m and 0.02 m/s |
| Sample coverage | Task `sample_period_s`, profile `sampled_settling.available`, feedback timestamps | Expected aligned endpoints and every sampled time; six samples in saved final window |
| Speed | Sealed profile motion artifact; `gvs_reporting.reconstruct_motion` | World tip translational Jacobian times recorded qvel; norm, m/s, no finite differencing |
| Timing | Task duration, control/sample periods; sealed computation metrics | Simulated updates and wall time remain separate; synchronous overruns do not inject actuator delay |
| Comparison | Sealed `campaign_comparison.ranking_rule`, settling ranking v1 | Joint acceptance first, then componentwise physical comparison; computation separate; no ranking raw costs under different weights |

Historical controller v1/v2 without explicit settling uses the explicit original
`gvs_profile.settling_for` / `SampledSettling` contract, identified in the view.
Missing definitions for other versions remain missing. Newly derived definition
views have interpretation version 1.0.0; archived results are not recomputed,
regraded or rewritten. Sampled holding does not establish continuous-time
performance. The resolver is limited to these existing reach campaign semantics.

## Demonstrated impact mapping

`tools/parameter_impacts.py` maps only these two builder paths. Current grants
are read from frozen `policy.editable` and builder `control_parameters`, rather
than inferred from installed controller support.

| Builder path | Effective CandidateInput path | Cost semantics |
|---|---|---|
| `control/recipe/terminal_tip_speed_weight` | `/effective/policy/controller/parameters/data/recipe/terminal_tip_speed_weight` | Dimensionless terminal squared world tip speed normalized by configured speed scale |
| `control/recipe/holding_tip_speed_weight` | `/effective/policy/controller/parameters/data/recipe/holding_tip_speed_weight` | Per-second normalized squared world tip speed on holding-cost nodes |

`GVSTrajectoryParameters` accepts finite nonnegative values; the demonstrated
reach builder permits zero or `[0.0001, 1]`, intersected with the current grant.
Controllers `gvs_nmpc` 3/4/6/7 support these reach settings; the saved campaign uses
7.0.0. The actual speed scale is read from the candidate recipe; it does not alter
acceptance limits. Candidate identity/content, actual_diff, controller plan,
candidate-specific `TrajectoryWorkspace` graph/solver, regenerated warm states,
execution records and bound evaluation/profile/comparison must be reconstructed.
The profile-backed `GVSNMPCController.configure` constructs a workspace per
candidate rather than reusing the global non-profile workspace cache. Fixed task
and robot definitions are reusable. Compatible tensions remain numerical guesses
only, subject to the existing preparation validation.

Old trajectories, mathematical analyses, optimized plans, evaluation and profile
results remain valid for their original identities. They cannot be rebound to a
changed candidate. Fresh execution requires the existing simulation, evaluation
and profile steps, then bound comparison and revision. The mapping cites
`candidate.apply`, `diagnostic_improvement.prepare_improvement`,
`gvs_profile.prepare_execution`, `GVSNMPCController.configure` and
`gvs_trajectory.TrajectoryWorkspace`. All other dependencies are explicitly
unmapped. This is neither a universal dependency graph nor a grant for new work.

## Milestone 2 handoff and next executable target

`platform.diagnostic_handoff@1.0.0` uses the existing `EvidenceSelector` contract,
with observations, hypotheses, unresolved questions, supporting/contradicting
selectors, previous assessment, new-result references, and a discriminating
check. The check names expected and weakening observations, capability,
authorization, budget and proceed/revise/stop conditions. The offline consumer
`tools/diagnostic_handoff.py::consume_handoff` binds the current context,
candidate and exact catalog membership/values. It proves citation agreement,
not causality, and invokes nothing. `engineering_fixture` supplies a saved
Stage 3.54 example, explicitly engineer-authored. Its proposed experiment is
unavailable under this zero-execution stage; the handoff contains no invented
historical search plan.

The next executable development target is to materialize this consumer contract
from an accepted existing diagnostic report/revision and host-bound working
state, validate competing assessments and changed evidence, then author and
validate a bounded **search-batch** plan before any execution. That plan must
contain: (1) hypothesis/evidence/weakening observations, (2) variables,
(3) fixed conditions, (4) objectives/constraints, (5) method/budget,
(6) verification/stopping conditions. `DiagnosticHandoff.search_plan` is the
extension point for its immutable reference. One plan governs a batch, not each
numerical candidate. Future authorization must explicitly bind the plan and
capability requirements to existing phase grants and reservations.

Milestone 2 remains unimplemented: no model-authored diagnostic handoff, causal
identification, bounded search-plan execution, search executor, automatic memory,
skill discovery, coding agent or optimization campaign was added. Preparing this
consumer boundary does not complete Milestone 2.

Verification commands, results, initial failures and affected reruns are in
`evidence/stage355_milestone1_20261003/`. The delivery summary records the final
gate, payload sizes and limitations. No paid live validation occurred. The
Stage 3.54 review amendment is documented in its delivery document and in
`examples/stage355_review.py`; only review metadata and its checksum changed.
