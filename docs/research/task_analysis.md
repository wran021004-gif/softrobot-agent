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
not relaunch. `compact_result` gives both tool responses and `core.packet()` the
same scoped claim, applicability/coverage, worst violation, certificate margin,
cost and exact raw JSON Pointer. `/trajectory`, `/trajectory/replay` and
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
