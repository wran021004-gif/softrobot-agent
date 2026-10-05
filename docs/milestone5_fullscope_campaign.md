# Milestone 5 full-scope development campaign — 2026-10-05

This separately authorized campaign starts at delivered commit
`a1f8f5d71f199ab32c86e9464ec5fe11ee94f057`. It preserves the predecessor STOP,
canceled second validation batch, incumbent and all earlier evidence. The original
reference is reused. Milestones 2–4 remain closed; Milestone 5 remains open.

The [frozen acceptance plan](../evidence/milestone5_fullscope_20261005/plan.json)
requires numerical support, quantitative accuracy on six distinct development
cases, correct resolved directions, useful position-feasible discrimination,
positive all-in economics and a genuine research admission before any new backend
validation. Ranking-only admission is unavailable. Conditional validation requires
two untouched pairs and an independent repeat, with no failed-case substitution.
The aggregate ceiling is 30,000 charged seconds, 20 provider attempts, 160 workflow
calls and six complete backend attempts; development is capped at 12,000 seconds
and two coherent revisions. No workers or subagents were used.

The tolerances stay at residual `1e-5`, position `1e-6 m`, speed/vector `1e-4 m/s`,
ranking separation `1e-4 m/s`, task position `.01 m`, holding speed `.02 m/s`, and
complete production-update wall time `.01 s`. Numerical resolution differences
are never physical uncertainty bounds.

## Matched-state diagnosis and two revisions

Two unchanged production-controller solves used the same saved `.32 s` reduced
state, previous input, three-step horizon and cold constant-input initialization.
Only holding weight changed, `.075` versus `.15`. Both accepted plans passed
independent feasibility checks; first-command separation was **2.113062916 N**.
Both stopped by relative seed improvement, selecting iterations 34 and 27.
This supports the narrow matched-state hypothesis; it does not reconstruct the
historical warm plans or prove useful complete-task screening.

Revision 1, `full_serial_continuous@1.0.0`, retains all 48 serial angles and rates
instead of projecting away deformation modes. SciPy Radau integrates complete
point mechanics with unchanged physical parameters. It performs no backend steps.
Initial full-state output loss is removed. Six cases at three registered
resolutions distinguish representation error from propagation error.

Revision 2, `full_serial_discrete@2.0.0`, tests the remaining backend discretization
effect. For this hinge-only, ideal-tension model with joint damping, it independently
evaluates `(M+h*C)*a=f`, then `v_next=v+h*a`, `q_next=q+h*v_next`.
The implicit-damping construction follows the [MuJoCo integration definition](https://mujoco.readthedocs.io/en/3.9.0/computation/index.html#numerical-integration);
its applicability here is supported by the saved model and endpoint comparisons.
This is explicitly **full-order backend-equivalent physics emulation**, with all
work charged, not a cheap reduced model or independent backend validation.

The primary step `.0005 s` was fixed to the backend step before revision-2 results.
Steps `.00025` and `.000125 s` retain the original two-successive-comparison test.
Primary backend reproduction and numerical refinement are reported separately.

| Development result, six unique cases | Continuous R1 | Discrete R2 |
|---|---:|---:|
| Numerical resolution passes | 6/6 | 3/6 |
| Position accuracy | 0/6 | 6/6 |
| Speed accuracy | 3/6 | 6/6 |
| Velocity-vector accuracy | 2/6 | 6/6 |
| Correct resolved direction with numerical support | 6/6 | 3/6 |
| Raw direction agreement, before numerical qualification | 6/6 | 6/6 |
| Speed false-safe / false-unsafe observations | 0 / 0 | 0 / 0 |

R1 position errors range from `2.184e-6` to `3.602e-5 m`; vector errors range
from `4.673e-5` to `3.039e-3 m/s`. R2 primary position/vector errors are at floating
point roundoff, but the first, early-original and original-.075 holding cases fail
step refinement. Neither revision meets the combined admission requirement.
The previous reset checkpoints contribute two unique cases, not four independent
observations. Passing six development reproductions grants no safety authority.

## Complete histories, cost and performance

The experimental controller-response schedule replans every fifth update before
holding and every update during the configured holding window: 11 solves per
forecast. It uses configured phase and each candidate's own predicted state and
previous plans; it contains no special `.32 s` trigger and reads no future outcome.
The production controller, early acceptance and incumbent remain unchanged.

One point model is constructed and reused per forecast, and the controller graph
is reused while its horizon is unchanged. Setup, graph reconstruction, controller
preparation/optimization, propagation and required research are all charged.
Full-state physics cost is separated from the expensive controller-response work.

The matched solves cost 21.012 and 18.308 seconds including cold construction;
updates alone took 19.530 and 17.890 seconds. Warm preparation took 6.610 and
6.633 seconds; optimization/validation took 12.920 and 11.256 seconds. Even removing
all construction cannot bring these original solves under 10 milliseconds.
Offline prediction speed does not satisfy this production deadline. No deadline
definition, compilation convention, solver acceptance or incumbent was changed.

| Historical pair | Holding speed forecasts, .075 / .15, m/s | Holding position forecasts, m | Decision | Useful position-feasible pair |
|---|---|---|---|---|
| Original | 1.485542 / 1.228151 | .049488 / .049488 | Abstain | No |
| Reset .20 | .097316 / .033489 | .002770 / .002670 | Raw order .15 before .075 | No |

The original pair first diverges from saved production commands at `.02 s`, with
position accuracy failing by `.03 s`. Both real original outcomes are position
feasible; the .15 outcome meets joint holding acceptance. The approximation thus
creates two raw position false-unsafe classifications and one raw speed
false-unsafe classification. Eligibility nevertheless abstains for this pair.

The reset pair first diverges at `.01 s`. Its raw speed order agrees with the
observed `1.149101 / .907362 m/s`, but both observed holding positions violate the
limit (`.026289 / .025127 m`). Both forecasts therefore have raw position
false-safe errors. Correct speed order does not produce a position-feasible winner.
Across two pairs, raw ranking resolves 1/2 and is correct 1/1 when resolved;
useful feasibility-qualified comparisons are **0/2**, with one abstention and no
wrong exclusion by the frozen raw-order/acceptable-candidate scorer. Local
threshold errors remain zero and must not erase these full-history errors.

| Cost, seconds | Original pair | Reset .20 pair |
|---|---:|---:|
| Both forecast receipts | 496.079 | 337.641 |
| Required native research including factual corrections | 60.720 | 60.720 |
| All-in screening | **556.799** | **398.361** |
| One evaluation hypothetically omitted | 0 | 690.499 |
| Counterfactual net | **−556.799** | **+292.138** |
| Actual savings | 0 | 0 |

Each standalone operational pair is conservatively charged the entire required
research overhead; the campaign ledger charges those actual calls once. The reset
comparison excludes the previously measured validation-only instrumentation from
its avoided evaluation cost, using the unchanged convention. Positive reset
arithmetic is reported separately from its failed position-feasible usefulness.
No new evaluation was actually omitted or launched in this development campaign.

## Acceptance and remaining work

The final accepted native judgment is **NO_GO**. The first response and two factual
corrections remain available. Corrections fixed local/task error conflation,
refinement pass counts, continuous/discrete labels and forecast/all-in cost labels;
they changed no scientific result, threshold or phase allowance. Final accounting
adds the last pending receipt after the model's response. User authorization is
valid; validation is withheld because scientific admission failed.

**Milestone 5 remains open.** Both allowed revisions were completed; the resource
budget was not exhausted. No new prospective pair or independent repeat was
admitted, and repeatability is untested. The unchanged incumbent remains candidate
`batch-ebbeadbdaca10732-0`, execution `91c3ba1b01d6499fb26df8f95409401b`, lengths
`.16/.11 m`, `.95/compliant`, weights `.05/.05`, production
`controller.gvs_nmpc@7.0.0`. It is not replaced by a historical candidate.

The remaining technical sequence is:

1. Establish a predictor/reference combination that meets the original local
   accuracy and numerical-support criteria together. Full-state retention removes
   mapping loss; fixed-step backend reproduction still differs from converged
   continuous physics. Neither observed result may be relabeled as the other.
2. Preserve the feedback response during the transient as well as holding, recover
   position-feasible complete predictions and remove full-history threshold errors.
   Measure positive screening economics and address the seconds-long controller
   optimization/preparation obstruction; construction caching alone is insufficient.
3. Pass the unchanged development gates and freeze a method, then evaluate two
   untouched pairs and a designated independent repeat, with causal pair/local seals
   and both candidates evaluated under the original stop rules.
4. Map those results, repeatability and complete-update deadline evidence to every
   original requirement before closing Milestone 5.

This campaign consumed **3 provider / 10 workflow / 0 real backend attempts,
937.862 charged seconds**, with 46 controller solves, 36 standalone local
integrations and four complete full-order forecasts (2,800 emulated physics
steps). All emulation costs are included; those forecasts are not independent
backend evaluations. Workers/subagents: zero. Cumulative usage is
**51 / 114 / 8, 9,268.525 seconds**, 154 additional controller solves,
105 standalone integrations and 280 historical backend controller updates.

Delivery checks: seven focused checks passed without numerical/API replay.
The final commit and exact `origin/feat/gvs-dynamics` verification are reported in
the delivery response. The archived SHA-256 manifest fixes evidence bytes; source,
ledger and handoff references remain reproducible from the linked repository.

## Evidence and reproducibility

The [assessment](../evidence/milestone5_fullscope_20261005/assessment.json),
[acceptance audit](../evidence/milestone5_fullscope_20261005/acceptance_audit.json),
[native research judgment](../evidence/milestone5_fullscope_20261005/interpretation.json),
[accounting](../evidence/milestone5_fullscope_20261005/accounting.json) and
[byte manifest](../evidence/milestone5_fullscope_20261005/sha256_manifest.json)
bind the plans, actual receipts, states/inputs, complete histories, model handoff
and implementation. Earlier evidence roots are required linked dependencies,
verified unchanged against the pre-work snapshot. Credentials are not exported.

The focused checks exercise the independent discrete equation and causal holding
schedule, then verify saved numerical gates, histories, accounting and evidence
bytes. They do not replay controller solves, integrations or provider calls.
