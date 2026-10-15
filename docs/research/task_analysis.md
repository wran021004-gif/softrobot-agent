# Task-aware mathematical evidence (M1 and M2)

M1 adds deterministic descriptions and evidence scope to `research_analysis`.
The M1 baseline documented below does not implement a trajectory feasibility solver.
M2 adds the explicitly selected sampled solver described in the final section.
The independent evaluator and reach/hold acceptance assembly are unchanged.

## Data flow and ownership

`dispatch` verifies the owned candidate against study state, then reads its frozen
effective configuration. It does not resolve mutable research JSON sources.
`ResearchTaskAdapter.analysis_requirements(binding)` owns reach translation;
`describe_analysis_requirements` exposes it to analysis callers. The common
`TaskAnalysisRequirement` also accepts explicitly declared, validated fixtures.
`model_assessment` reuses the existing registry and `assess_model_uses` for the
actual GVS binding used by candidate mathematics. `check_analysis_applicability`
checks the operation, outputs, input bounds, sampling and available horizon.
`calculate` retains the original numerical algorithms and raw result, attaching
`task_analysis`, `analysis_applicability`, and a versioned `scoped_claim`.
The existing Store saves these fields in the same candidate analysis artifact.
The tool response exposes applicability and claim; `evidence_read` exposes full
requirements, model and raw verification data. No prompt or Agent change is needed.

## Contract and sampling

`task-analysis-v1` uses SignalSpec identity, dimension, units, frame and phase.
Each constraint has ordered unique nonnegative sample indices, one reference
vector per index, and frozen-configuration JSON-pointer provenance.
`norm_bound` means `||signal[index] - reference[index]||_2 <= radius`.
`component_interval` means `lower <= signal[index] - reference[index] <= upper`.
The inclusive absolute task grid must match duration and sample period within
1e-12 seconds; invalid indices and nonfinite values are rejected.
Physical inputs retain nonnegative total tendon tensions, limits, channel order,
newtons, tendon-path frame, pre-step phase and the task control period.
The current task yields terminal index 35 and holding indices 30 through 35,
with separate terminal-position, holding-position and holding-speed requirements.
Values come from the frozen evaluator tolerance and controller settling contract.
Task/candidate/configuration/source/evaluation-profile identities are retained.
Time-varying references use the same schema; their tests are synthetic fixtures.
They do not register or establish an executable tracking task.

## Applicability and evidence

Schema expressibility, mathematical applicability and executable compatibility
are separate. Execution support is explicitly `not_assessed` here; existing
task/controller/backend compatibility checks retain ownership of that question.
Endpoint analysis checks terminal position only. Braking also checks the final
speed sample; the rest of the holding window remains unanalyzed. Coverage lists
exact analyzed indices. `full_task_supported` is false for current operations.
Linearization/controllability and equilibrium provide diagnostics, not sampled
constraint certificates. Actual model outputs and input semantics are rechecked
after construction. Nominal operating points retain a nominal horizon; saved
states retain their actual origin and remaining task time.
External applied forces, declared omitted physics and unknown required physics
prevent applicability before numerical model construction. Nonconvex/contact
requirements retain their original payload with `kind=unsupported`; unknown
signals or mismatched units/frames/phases are not silently replaced. Intervals
are expressible but have no constraint solver in this interface yet.

- `feasible_witness`: existing bounded_endpoint independent finite/bounds/output
  checks passed; only the reported local affine endpoint problem is covered.
- `model_infeasibility_certificate`: the existing separating-direction lower
  bound has a positive margin including its numerical allowance, within that
  exact model and input box. Solver failure alone is never a certificate.
- `diagnostic`: computed Gramian authority or available static construction.
- `inconclusive`: failed, unavailable, or insufficiently verified computation.
- `not_applicable`: no compatible operation/model scope; reasons are explicit.

Claims retain model/protocol hashes, assumptions, operating point, horizon,
physical inputs, coverage, computation/verification status and a JSON Pointer
into the same result's numerical evidence. No claim establishes backend task
acceptance, whole-window holding, global nonlinear behavior or hardware results.
`reach-local-v1`, `task-local-v2` and historical AnalysisResult payloads remain
valid. Old receipts are reused unchanged. New failed workers use scope frozen in
their request; attempts and elapsed costs retain existing accounting semantics,
including admitted requests found not applicable. Recovery never relaunches work.

## Verification and M2 extension point

Run `python -m unittest discover -s tests/research -p test_task_analysis_contract.py -v`
and the directly affected `test_mainline.py`. Create the untracked `runs/`
directory first when running the older regression module in a fresh worktree.
Tests cover frozen translation, moving references, invalid grids/signals,
unsupported physics, real kernel witnesses/certificates on labeled fixtures,
one light GVS initial linearization, acceptance, old contracts and Store recovery.
No provider request, full NMPC rollout or RL training is involved.
Verified on 2026-10-15 using the existing `.mainline5-env`: M1 11/11 passed;
mainline 12/12 passed; `git diff --check` passed. The first mainline attempt
failed during fixture setup because `runs/` was absent; creating it resolved this.
M2 can reuse normalized references, physical bounds, exact grids, provenance and
claim semantics, adding explicit multi-sample coverage and a verified solver.
It must retain independent task acceptance and introduce its own versioned scope.

## M2: sampled affine trajectory feasibility

Select `operation="trajectory_feasibility"` through the existing `AnalysisRequest`
and `research_analysis` tool. Use `controller_start_input`,
`standardized_initial_pretension`, or an exactly bound `saved_state`/execution
update. The request still uses the frozen `task-local-v2` protocol for its periods,
iteration limit and numerical tolerance. The numerical algorithm has the new
explicit scope `sampled-affine-trajectory-v1`; the M1 requirement and scoped-claim
contracts, `reach-local-v1`, old result payloads and endpoint/braking algorithms
retain their meanings. No task evaluator or controller acceptance changed.

`extensions/math_analysis/trajectory.py` owns the pure numerical calculation.
It reuses `kernels.zoh` for exact affine ZOH discretization, and builds all sampled
state/output maps by recurrence against one stacked incremental input sequence.
Physical inputs are `u0 + delta_u`, bounded by the candidate's actual total tendon
limits. Dimensions derive from the matrices; no task name or fixed channel count
appears in the kernel. `norm_bound` and `component_interval` residuals use each
sample's own reference. SLSQP selects a small normalized-effort solution subject
to all supported samples jointly, with explicit constraint scaling and the frozen
100-iteration maximum. Numerical failure remains inconclusive.

A separate forward discrete-state recurrence checks the proposed sequence,
outputs, physical bounds, residuals, margins and prediction agreement. Only this
replay can establish a witness, within the declared physical-unit absolute check
tolerance (`endpoint_check_atol`, currently 1e-8). Records retain every checked
constraint ID, absolute sample index/time, units/frame, value, reference, residual,
margin and normalized violation. The result includes discrete matrices, initial
perturbation, physical input sequence, worst violation and minimum tension margin.
Nonfinite or dimensionally incompatible sequences are rejected.

If replay fails, the existing `_minimum_residual_certificate` proposes a norm
separating direction. M2 renormalizes and recomputes its support lower bound over
the complete physical input box, with a roundoff allowance plus check tolerance;
it does not trust the least-squares success flag or proposed bound. Component
intervals can be excluded by their exact affine residual range over the same box.
Only a strictly positive verified margin establishes a necessary-condition
exclusion. A joint conflict without an individually excluded necessary constraint
remains inconclusive. This compact certificate mechanism is deliberately incomplete.

Initial perturbation is zero at the exact linearization state; the pure kernel
also accepts an explicit mapped initial perturbation. Initial configuration
points use the existing initializer projection and get task time zero only for
this new operation. Hypothetical equilibrium/halfway points have no known task
origin and are not applicable to this trajectory operation. Saved points retain
their actual time, previous physical input and remaining task time. Absolute
samples must align with control boundaries within 1e-12 s; a coarser aligned
sample grid is supported. No time is silently rounded. At 0.30 s of the frozen
0.35 s task, there are five future control intervals. Past samples are unchecked;
any later start is explicitly partial frozen-task temporal coverage. A terminal
zero-horizon request can check its known sample without optimization.

Post-step outputs with nonzero D use the preceding held input. The initial
sample requires a known previous input; missing ownership leaves that sample
unsupported, even when later samples can be covered. Current GVS tip outputs
have D=0. Unsupported signals, units, frames, phases, nonlinear constraints and
omitted physical effects retain explicit reasons and coverage gaps.

`full_task_supported` describes complete expressibility and temporal coverage,
independently of feasibility. `analyzed_indices`, `unchecked_indices`,
`checked_indices` and `satisfied_indices` distinguish availability, actual replay
and satisfaction. A partial witness is never complete frozen-task feasibility.
A necessary-condition certificate can exclude the joint local-model task even
with other requirements uncovered; it identifies the precise constraint/index
and complete input-box assumption. Complete sampled witnesses establish only
the declared discrete samples in this frozen local affine model. They establish
neither continuous-time holding, nonlinear/global feasibility, backend task
acceptance, robustness nor hardware performance.

The existing dispatch, worker, recovery, immutable Store and cumulative ledger
remain the only execution path. One admitted attempt is charged once, including
failed or unsupported computations under existing rules. Reusing its operation
key reads the original artifact and returns zero additional work; recovery does
not relaunch. `compact_result` preserves the public tool response. `core.packet()`
uses the smaller deterministic `decision_result`, retaining identity, conclusion,
coverage, decisive sampled margin, certificate status, cost and exact pointers.
`/trajectory`, `/trajectory/replay` and
`/trajectory/certificate` are readable through the existing `evidence_read`.
Raw trajectories/matrices stay in the artifact. The saved-state interface now
checks input length against candidate `tendon_order`, alongside exact ownership,
coordinate/tendon order, newton units and previous-input interval-start phase.
Both the extension source list and `SCIENCE_FILES` fingerprint the new kernel.

### M2 verification on 2026-10-15

Using the existing Windows `.mainline5-env` (NumPy 2.4.6, SciPy 1.17.1):

- New M2 module: **15/15 passed**, 16.476 s in the final run.
- Existing M1 module: **11/11 passed**, 7.776 s.
- Directly affected mainline module: **12/12 passed**, 5.311 s.
- `git diff --check`: passed.

The numerical fixtures cover moving references, shared-input prediction/replay,
nonzero nominal tension, one/five/seven channels, intervals, norm separation,
forged certificate bounds, joint conflicts, early solver stop/nonfinite output,
absolute/zero-time samples, aligned/coarser and incompatible grids, initial and
preceding-hold feedthrough, full/partial/unsupported requirements, saved input
ownership/order/phase, historical semantics and source fingerprints. Five
conclusion/coverage cases pass through Store, compact packet, exact evidence-read
and free cached retrieval without a provider call. The first integration test
attempt exposed a test assertion that incorrectly expected a trajectory artifact
for an unsupported request; the assertion now follows the declared applicability
pointer. This did not require changing the scientific verifier.

The real candidate-bound GVS integration used the frozen reach configuration,
24 state coordinates, six ordered tendon channels, world-frame position/velocity,
35 mathematical input intervals at 0.01 s, and all 13 declared constraint/sample
pairs. The final SLSQP attempt reached 100 iterations and remained **inconclusive**.
Its worst proposed-sequence violation was `holding_max_speed_m_s` at absolute
sample 34 (0.34 s): 0.02000951183424395 m/s against 0.02 m/s, a violation of
9.51183424394847e-6 m/s. No necessary-condition exclusion was verified. Maximum
prediction/replay difference was 6.106226635438361e-16. The task was fully
expressible and replayed, but not certified satisfied; tolerance was not relaxed.
This final Store attempt charged one mathematical evaluation and 10.066039699944668
numerical seconds. Three focused GVS trajectory attempts were made during test
development, each with the same inconclusive conclusion (10.1511, 10.1314,
10.0660 charged seconds); M1 regression additionally ran its one local GVS
linearization. No NMPC rollout, provider request, RL training or scientific search
was started. The 35 intervals here are affine prediction, not 35 NMPC solves.

The non-secret export `evidence/task_feasibility_20261015/real_gvs.json` retains
the original numerical Store result, exact response/packet projection and source
fingerprints. `original_result` hashes under the Store's canonical encoding to
artifact ID `69ed5164545847b17eabc484818decc69b1421b6787c20746283344dea6fda27`;
its numerical pointer remains `/trajectory` (inside that original result).
This is a labeled integration fixture, not a live Agent study or physical result.
Normal tests clean up their temporary fixture Stores. Set `M2_EVIDENCE_DIR` to an
explicit workspace directory when an export is wanted.

M2-A was independently tested and committed as
`0071b52dccf71c89d023bb4019afe21d0c5e5cd4` before M2-B integration. Runtime changes
are approximately 330 net lines, within the requested guidance; the larger test
module exercises the three independent verification layers and both required
interface repairs. M3 remains responsible for variable tendon/topology generation.
Five/seven-channel M2 fixtures only validate the numerical and saved-state
interfaces. They add no variable-count robot generator or new physical model.

### M2 numerical closeout: controlled analytic constraint Jacobian

`analytic_jacobian_ab.json` in the same evidence directory records one new pair,
with a shared freshly constructed GVS model (arrays exactly equal to the saved
M2 model), frozen requirements, zero initial delta sequence, bounds, 100 iterations,
1e-12 SLSQP ftol and 1e-8 physical replay tolerance. Both use the existing
single-thread environment. The optional `controlled_real_gvs_ab()` helper in
the M2 test module refuses to overwrite this record and is not a discovered test.
The analytic Jacobian differentiates the original normalized norm/interval
margins, in the same row order. At zero norm it uses the zero supergradient of
the concave margin. Central difference checks away from zero pass.

| Measurement | Numerical differences | Analytic |
|---|---:|---:|
| Optimization seconds | 1.5607669999590144 | 0.32040670001879334 |
| SLSQP iterations | 100 | 100 |
| Objective evaluations | 101 | 101 |
| Constraint evaluations | 21413 | 102 |
| Constraint Jacobian evaluations (including numerical construction) | 101 | 101 |
| Maximum physical violation (m/s) | 9.19619888416906e-6 | 9.547179930784189e-6 |

Both worst rows are `holding_max_speed_m_s`, sample 34, 0.34 s. Both independent
replays fail and neither yields an exclusion certificate: **inconclusive**.
The slightly larger analytic residual is retained honestly; feasibility did not
improve. The analytic implementation is retained for its measured 4.87x reduction
in optimization time and constraint calls, with unchanged verification semantics.
There is one production solver path; the numerical comparison uses test-only
instrumentation of SciPy's original differentiation. No further tuning was run.
The evidence contains measured construction/linearization and kernel times,
environment, identities, both proposed sequences and all replay records. It
references the immutable old GVS artifact rather than duplicating its model.

### Agent decision context and interpretable feedback

The complete Store artifact and compatible public tool response remain unchanged.
Only the repeated `CURRENT_RESEARCH_PACKET` mathematical entry changes. It uses
the same evidence reference, candidate, task, operation and conclusion; scope is
retrieved at `/scoped_claim` (including model/protocol identities). Coverage is
`full`, `partial` or `unchecked`; reasons and every omitted constraint remain
available at `/analysis_applicability`. One decisive row is selected from existing
`trajectory.replay.records`, preferring the kernel's worst normalized violation,
otherwise a tight physical margin. Values are copied, not recalculated. The row
identifies signal, time, residual norm or component residual, bound, margin,
violation, units and its exact original pointer. Norm values refer to the declared
reference, not an absolute position norm. Full output/reference vectors remain in
that record. No valid sequence means no invented margin.

An attempted-sequence violation is never a lower bound on achievable error.
Satisfied samples describe remaining sampled margin only. Certificate status is
reported separately from attempted margins. Deterministic `decision_relevance`
distinguishes local witnesses, verified model/input-box exclusions, inconclusive
attempts, unsupported operations and diagnostics. It states supported facts,
unresolved questions, possible distinguishing checks and unsupported global or
physical/structural inferences. Partial witnesses refer only to checked samples;
the Agent chooses any next action within its frozen grant.

Offline verification loaded the unchanged M2 artifact
`69ed5164545847b17eabc484818decc69b1421b6787c20746283344dea6fda27`, exercised
`agent.decision_packet` without a provider, and measured canonical UTF-8 JSON:
**29,318 → 1,304 bytes per entry (95.55% reduction)**. With all other packet fields
identical, the actual decision boundary measured **77,435 → 49,421 bytes**.
`decision_packet.json` records sizes and identity checks. Seven existing bounded
pages retrieved all 13 original replay records exactly; original artifact identity
was unchanged. Existing M2 integration exercises full/partial witnesses,
exclusion, inconclusive and not-applicable results through Store and packet with
receipt reuse. Strands offload, retrieval and provider integration were not changed.

## M3-A: explicitly authorized tendon topology

`configs/research/topology.json` is a small, single-level extension of the existing
study. It references its original raw study hash/ID and the same robot, task,
control and runtime sources. Preparation freezes these values once. The original
`study.json` is unchanged and gains no topology permission. The example grants
five through seven independent ideal tensions, explicit attachment-position boxes,
editable guide ownership, and tendon diameter/force/pretension/servo bounds.
Its provider, NMPC and backend-launch allowances are zero. The inherited
`topology_scope` still describes the six-tendon physical source; the separate,
versioned `topology_authorization` alone permits candidate modifications.

The additive builder is `candidate.family@4.0.0`, with
`family.topology_space@1.0.0`. It reuses the old continuous segment generation and
the existing physical `Tendon`, `RoutePoint`, `Actuator` and compiler contracts.
The old `candidate.family@3.0.0` / `family.generator_space@1.0.0` payload and old
proposal serialization are unchanged. A topology proposal uses the existing
`research_plan` action `propose`, with its usual hypothesis/evidence/stop fields:

```python
parameters = {
    **frozen_reference_parameters,  # existing continuous physical/control fields
    "version": "research_topology_parameters_v1",
    "topology": {
        "version": "tendon_topology_patch_v1",
        "remove_tendons": ["far_t2"],
        "upsert_tendons": [],      # complete existing Tendon definitions
        "guide_holes": {},         # guide ID -> named hole -> explicit local xyz
    },
}
```

Without the new parameter version, the old continuous proposal contract applies.
Without the frozen topology grant, a versioned topology proposal is rejected.
Complete upserts replace an existing tendon at its source index or append a new
tendon in patch order; removals also remove their independent actuator. The
explicit grant rule `copy_source_independent_displacement_v1` copies the first
source actuator's physical parameters for a new tendon, names it
`<tendon_id>_motor` and sets its sole transmission to that tendon at ratio one.
Existing actuators remain unchanged, in the resolved tendon order. There is no
implicit actuator tuning, route-coordinate scaling or unknown-field patching.
Continuous coordinate search can retain a fixed typed topology in `Search.fixed`;
it is not a mixed-integer search or a cross-topology ranking mechanism.

Guide holes must fit the unchanged guide envelope, remain separated by more than
two hole radii, and accept the actual tendon diameter. M3-A uses one tendon per
named guide hole and requires named-hole references on guides. Supported segment
attachments remain explicit normalized stations and fixed local offsets inside
the grant's position boxes; these are ideal model attachments, not newly modeled
physical guide hardware. The compiler checks role order, attachment ownership,
zero spans, unique entities and transmission ownership. Missing checks added here
reject pretension above the physical force limit and explicit rigid attachment
points outside the rigid envelope. No geometry/transmission check was weakened.

Effective candidate configurations retain the frozen six-tendon source design,
mesh, explicit grant/patch, resolved physical tendon/actuator order, force bounds,
control recipe, GVS basis, named zero initializer and exact evaluation profile.
The owning Store study retains the original study ID/hash. Same-count route
changes produce different scientific candidate IDs; labels and evidence references
do not replace the physical configuration in the identity. Historical source
fingerprints and sealed results remain untouched. New implementations require a
new binding or explicit migration under the existing guards, without budget reset.

### Verified physical/model boundary

The single `test_variable_tendons.py` module exercises real candidate construction
through typed native proposal dispatch and Store receipts, without a provider.
`evidence/topology_20261015/physical_diagnostics.json` retains exact candidate,
configuration, source, profile, physical and GVS model identities, patches,
ordered bounds, Jacobians, force sign checks and actual measured costs. Candidate
artifact references identify temporary offline fixture Stores; the export retains
the explicit patches and frozen source identities needed to reconstruct them.

| Case | Physical change | GVS length Jacobian | MuJoCo inputs |
|---|---|---|---:|
| T0 | Unchanged six-tendon reference | 6 x 12 | 6 |
| T1 | Remove `far_t2` and its motor | 5 x 12 | 5 |
| T2 | Explicitly move `near_t0`'s midpoint offset to `[0, .021, .006]` m | 6 x 12 | 6 |
| T3 | Add `near_t3`, with start/midpoint `[0, 0, .018]` m and a fitting new `near_h3` hole | 7 x 12 | 7 |

Every candidate keeps the same two flexible segments, 12 structural-linear GVS
coordinates and source mesh. T0's complete compiled physics equals the original
compiler at `8b69568f`; its effective old configuration hash remains
`31af3e097ad29fef1ffd74c5178a6267fc5ffe35889c63e98f531dd42c0df69e`.
Its GVS expression identity also exactly matches the saved M2 expression
`42f50c6ff37ab86f514368d7fb155536f2721252d333ad50fe2347a788b64e37`.

At the common declared zero-curvature pose, T2 changes only `near_t0`'s Jacobian
row (norm of the row difference `2.0359160852663087e-4` m/(rad/m)). The actual
model returns `tau_tendon = -J_length.T @ total_tension`; directional central
differences using the independent numerical GVS kinematics agree within
`3.498248132144388e-12` absolute error across all four candidates. T3's one local
linearization has A shape 24 x 24 and B shape 24 x 7. Model/input order, physical
bounds and candidate-owned initializer/warm-guess dimensions agree. Real five/seven
candidate saved-state boundary tests reject six-channel states before any worker;
the deliberate valid-boundary worker-failure fixtures remain `incomplete`.

All four XML files compile in MuJoCo 3.13.0. Tendon/actuator indices, negative
actuator force for positive tension, generalized-force sign and physical length
agree with compiled geometry. Each model executes exactly three physical steps
(0.0015 s), with finite states and no bad-state warnings: 12 steps total. No
controller command, optimization rollout or task acceptance was evaluated.

The recorded geometry validation took 11.279801800032146 s: four GVS graph builds
took 1.3859340999042615, 1.4161933000432327, 1.3793710001045838 and
1.3759216000325978 s; the seven-input linearization took 5.119289500056766 s.
The four three-step physics loops took approximately 0.00465–0.00537 s each.
The final lightweight regression ran **43 tests, all passed**, in
12.921046599978581 s, excluding the already completed expensive GVS integrations.
Together with the separate physical diagnostic test, all five topology tests
passed. `validation.json` records the exact tests, exclusions and fixture fixes.
No live study counters were reset; test grants are independent offline fixtures.

M3-A establishes model consistency under the declared ideal physical assumptions.
It establishes no manufacturability, global controllability, task improvement,
full-task feasibility or design superiority. Individual limits are 8 N; total
box capacities are 40/48/56 N, so cross-topology comparisons need explicit common
physical conditions. M3-B still needs a declared comparison protocol, appropriate
nonlinear/controller checks and independently evaluated execution. No six-tendon
RL policy or incompatible warm state was transferred, and no NMPC campaign,
provider call, RL training or large candidate search was performed.

### M3-B1 actual control boundary

The independent `topology_control_b1.json` grant permits one through seven tendons
on the unchanged two-segment source. S1 retains `near_t0` and explicitly removes
the other five tendons and their independent actuators. Its GVS length Jacobian
is 1 x 10, force-to-state input matrix is 20 x 1, warm input guess is 10 x 1,
and MuJoCo has exactly one correctly indexed ideal-tension channel, bounded 0–8 N.
The registered controller prepared and actually solved all T0/T1/T2/T3/S1 models.
Each applied one command for 20 physics steps (0.01 s). This is an incomplete
engineering diagnostic; neither underactuation nor optimizer convergence establishes
full-task feasibility. Exact states, solver records and raw model exports are in
the [B1 evidence](../../evidence/topology_control_20261015/b1/control_diagnostics.json)
and its immutable archive. No historical M3-A grant or task threshold changed.
S1 has 10 structural-linear coordinates / 20 states: removing far-tendon routes
also removes a tendon-defined structural knot. The original two flexible segments
and physical mesh remain; no state from a 24-state candidate was transferred.

### Frozen new task instance

`tasks/reach_hold_mirror_v1.json` composes `reach_hold.json` with a distinct
`family-multisegment-mirror-dev@1.0.0` identity and target `[0.29,-0.035,0.19]` m.
Evaluator semantics, 10 mm tolerance, 0.35 s duration, 0.05 s inclusive holding
window, 0.020 m/s speed limit, zero initializer and all sampling phases/grids
are inherited unchanged. Its task identity is
`7d4e6bf6bb30eab21cdafbe90f1dc30e201b167d90031b05fe7e44a0eea25c1b`.
Eight prior immutable archives and ordinary evidence records expose only the
positive-y target; novelty is limited to the evidence available on this branch.
Geometric plausibility does not establish unilateral-tension or holding feasibility.

`configs/research/first_feasible_mirror.json` freezes a single new study with
12 provider requests (3 protected), 60 public operations (10 protected), three
complete backend launches and ten mathematical evaluations. RL, local replays,
offline NLP/BDF and extra confirmations are disabled. The Agent may choose
authorized tendon count/routing, continuous structure and existing control weights,
mathematics, execution, diagnosis or STOP. No fixed scientific decision sequence
or mandatory mathematical action is supplied. B1/B2 and older successes are
explicitly historical context, never fresh acceptance or shared study consumption.
