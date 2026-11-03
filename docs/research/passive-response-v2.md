# Passive response v2

Implementation milestone, 2026-11-04. Engineering validation is reported
separately; this document is not a PHS/P3 success certificate.

The existing `task.passive_response@1.0.0` explicitly accepts goal and evaluator
payloads at `2.0.0`, with goal `version: passive_response_v2` and
`evaluate.passive_response@2.0.0`. V1 payloads, tasks and solver defaults retain
their original behavior. The backend, Worker, Store, task acceptance, evidence
reader, certificate and SELECT path are shared.

`PassiveResponseGoalV2` in `extensions/reference/contracts.py` is the executable
schema authority. It freezes ordered episode names and `programs`, whose stages
contain start/end seconds, start/end world forces in N, hold/linear/smoothstep
interpolation, ramp endpoint, observation window and scoring window. Adjacent
times and forces must agree; all boundaries lie on both physical and score grids.
Each independent episode resets once. Stages within it never reset. Interval
start versus interval end force sampling is explicit; post-step observations
retain the force actually applied during the preceding physical step.

Each program starts with an explicit zero-load preparation stage. Frozen named
state is the preparation seed. `initial_source: qualified_unloaded` identifies
the dynamically qualified boundary as the loading reference, without resetting
velocity or warm start there. Both preparation seed and loading-boundary state
are recorded. Registered qualification rules freeze speed, joint velocity, tail
drift, static balance, enabled tendon excess, optional initial lateral position
and score-grid/every-step coverage. Static KKT evidence is never substituted.

Optional saved initialization accepts only a current owned completed physical
result and episode name. It restores `mjSTATE_INTEGRATION`, including clock,
velocities and warm start, after checking the complete source binding, engine
version, vector layout and hash. Preparation is still executed and charged.
The Agent never supplies an engine vector. Complete state snapshots bind the
task, design, compiled physical/discretization source and actual engine time;
the enclosing immutable raw record and Store receipt bind execution ownership.

Per-step measurements include signed tendon-limit multipliers and actual
constraint states/residuals; upper-limit row directions are checked against the
tendon Jacobian. Slack requires a negative length gap, low multiplier and absent
constraint rows. Other near-boundary states remain indeterminate. Zero tension
alone does not imply an inactive tendon over a whole stage. Contacts, warnings,
capacity, enabled length excess, force mapping and numerical failures remain
observable. Full-step CSV is optional and stored as immutable `text/csv` bytes in
the same Store, with exact hash, size and completed-step manifest.

`physical_replay.passive_ablation` names exact tendon entities. The shared Worker
runs two fresh native model/data executions under one aggregate reservation,
charging twice the episode count. Each arm has its own raw record and subordinate
native execution receipt, linked to the parent Worker receipt and termination
boundary. These are not two top-level autonomous Study reservations. Only the
selected `tendon_limited` array entries change, after identical unloaded
qualification. All other compiled arrays are checked equal. Ablated evidence is
embedded as a comparator and cannot enter normal candidate selection itself.

The v2 evaluator rechecks source, force/clock grids, complete state boundaries,
qualification measurements, actual constraints and coverage. Registered metrics
reuse spatial reductions and add named stage/reference windows, last/mean/range
and mean-state aggregation, explicit spatial projections, interval stiffness,
precision-limited denominators and a same-tendon slack-to-taut requirement.
Metrics use a stage's declared qualification grid when it covers that scoring
window, otherwise the score grid. This matters for original P3 final full-tail
means and uncertainty: subsampling only the score grid changes these quantities.
Mechanism evidence requires two valid comparable arms and exact native receipts;
its scope is the frozen intervention, program and observed assembly only.

Optional route validation reuses the original P3 convex envelope/hole/anchor
intersection rules. Its checked pose grid is explicit; score-grid exploration
is not an every-step final geometry certificate. This model does not establish
hardware performance, cable friction or continuous geometric nonintersection.

Main uses the existing dynamic tool schema and owned references. No active
control/RL capability is added. Reporter receives bounded stage/qualification
facts and source pointers; state vectors, matrices and full trajectories remain
in L2. The production evaluator contains no PHS/P3 task-name dispatch.

Initial regression: six bounded real-engine tests passed, including v1 behavior,
continuous five-stage execution, state restore, two-arm intervention and evidence
mutations. Store/SDK and original-protocol validation follow this identity freeze.

Integration follow-up: paired partial recovery now reconstructs already observed
arms from the existing durable progress files without relaunch. Interrupted
counts are explicitly lower bounds; incomplete CSV bytes are retained as
unsealed evidence, never a complete trajectory. Native cost entries remain
numeric, so the existing mechanism research kernel can aggregate them. The
existing scientific structure question accepts exact `passive_ablation` names
for finite-time v2 research; its original physical episode reservation doubles.
Missing required mechanism intervention is rejected before execution. The v2
reference boundary replaces the v1-only `unloaded_until_s` lookup in that kernel.

Original-protocol engineering observations (execution identity `e2337e6`):
PHS representative plus/minus 0.1 N at material s=0.5, 12 cells per segment,
completed 128,000 steps with qualified tails and a valid task failure. P3 at
two and four cells each completed four native episodes / 640,000 steps, but
original stage stability failed and acceptance remained INVALID. Original
P3 source trajectories agreed within 5.24e-16 m in these bounded comparisons.
Full-tail metric reanalysis corrected an initially detected score-grid aliasing
error; the earlier audit and consumption remain retained. No successful P3
mechanism claim follows from unsettled arms. PHS original loaded execution
resets velocity and warm start from baseline qpos, whereas v2 retains full
qualified state continuously; original PHS cross-implementation trajectory
tolerance was not found. This initialization/equivalence decision remains a
formal-study readiness prerequisite, even though final point differences were
about 1.2e-10 m in this ordinary assembly. No benchmark-winning parameters or
new autonomous benchmark Study were used.
