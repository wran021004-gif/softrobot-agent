# Milestone 5 accuracy and screening-cost campaign, 2026-10-05

Development calculations are complete. **The accepted research go/no-go is
blocked by automatic approval review**, which rejected the DeepSeek transmission
twice before process creation. The second rejection states that the attachment's
embedded authorization is not accepted as direct chat authorization. The exact
[rejections](../evidence/milestone5_predictor_campaign_20261005/platform_rejection.json),
[authorization evidence and payload hash](../evidence/milestone5_predictor_campaign_20261005/authorization_review_evidence.json),
and concrete 55,143-byte native payload are retained. Direct confirmation has been
requested. No provider attempt, prospective forecast, validation grant or backend
attempt has occurred. The pending judgment must not default to completion.

This linked campaign addresses both local prediction accuracy and operational
screening cost. It does not change the production controller, robot, actuator
limits, task, incumbent, historical outcomes, or real-time requirements.

The [acceptance freeze](../evidence/milestone5_predictor_campaign_20261005/freeze.json)
precedes all new development results. The predecessor stages remain immutable.

| Dimension | Frozen acceptance and scope |
| --- | --- |
| Numerical reference | Finite roots, scaled residual <=1e-5, last two successive vector AND speed differences <=1e-4 m/s; backend agreement is separate |
| Physical local accuracy | Position <=1e-6 m, velocity vector and speed <=1e-4 m/s, reported separately on four distinct frozen intervals |
| Direction | Report resolved coverage and correctness; numerical uncertainty can require abstention; direction does not replace quantitative accuracy |
| Candidate discrimination | Lowest sampled maximum holding speed, conditional on position feasibility; margin 1e-4 m/s; universal abstention fails useful screening |
| Physical thresholds | Position 0.01 m and speed 0.02 m/s; retain and report all false-safe/false-unsafe outcomes |
| Operational economics | All incremental pair screening and required decision overhead must cost less than the ONE complete evaluation the decision actually avoids |
| Prospective validation | Only after accepted development admission and sufficient unchanged public reservations; seal both forecasts before either backend; seal local predictions before advancement |
| Real-time control | Outside this offline development correction; incumbent 35/35 deadline misses remain unmet |

The local cases are the shared original .00-.01 s interval, .075's .01-.02 s
early divergence, and .30-.31 s holding entry for both .075 and .15. The shared
first interval counts once. Historical complete forecasts cover .00-.35 s with
.30-.35 s holding. Future registered .20/.30 checkpoint episodes reset the clock
and controller; they are distinct from historical continuations.

Development ceilings: 12 provider attempts, 60 workflow calls, one missing
reference integration, 16 other short integrations, two complete previews,
80 controller attempts, 6000 charged seconds, zero backend steps/attempts,
workers or subagents. Final interpretation/export retains 1265 seconds before
expensive work. Two conditional validation grants are linked but not materialized
before admission; each permits two backend attempts, two previews, 70 preview
and 70 production controller attempts, 6000 seconds, four provider and 16
workflow calls. Failed attempts count. No unused predecessor budget is reset.

The [method freeze](../evidence/milestone5_predictor_campaign_20261005/method_freeze.json)
selects one predictor mechanics correction and one controller-effort strategy
after saved-state localization and before their new comparisons. The mechanics
use the unchanged integrated-v2 linear representation and represented serial
output, with virtual-work pullback of the saved serial mass/force functions.
Only the 24-component reduced state evolves in SciPy's implicit Radau integrator;
MuJoCo supplies non-advancing point evaluations, with its clock held at zero.
No full-order backend rollout or step is used in development.

The controller-response approximation replans at updates 0, 5, 10, 15, 20, 25,
and 30 and uses the intervening commands from its own generated plan. Production
still updates all 35 times. This approximation must reproduce decision-relevant
candidate differences; reduced solve count alone does not establish utility.

## Reference completion and physical localization

The one authorized 2560-substep continuation completed, charging 608.265 seconds.
It used the unchanged zero reduced state, original held direct input and original
.00-.01 s interval, with the repaired 800-second integration guard and 1200-second
outer reservation. Eight earlier endpoints were reused exactly. Finite roots and
scaled residuals passed. Final two vector/speed differences were:

| Common output map | Vector differences (m/s) | Speed differences (m/s) | Result |
| --- | --- | --- | --- |
| Continuous | 6.21189e-5, 3.10755e-5 | 6.14253e-5, 3.07286e-5 | Pass |
| Represented serial | 6.89947e-5, 3.45152e-5 | 6.82941e-5, 3.41647e-5 | Pass |

These references establish local successive-resolution self-consistency of the
original continuum dynamics, not backend accuracy or the changed model. All
serial outputs were re-evaluated on saved endpoint states without reintegration.

The corrected [localization](../evidence/milestone5_predictor_campaign_20261005/localization-r1.json)
finds projection round-trip errors below 1e-13 and position/rate consistency
within finite-difference precision. No projection implementation defect is
established. Continuous versus represented serial reduced mass differs by about
7.9-8.0%; gravity-minus-velocity-bias differs by about 5.4-5.5%. Actuation differs
by 0.6-2.4%, with combined-force discrepancies amplified by cancellation.
Discarded cell-rate norms range from zero initially to 0.064 rad/s early;
holding-entry discarded angle norms are about 0.0213 rad. These are evidence of
representation and dynamics approximations, not fitted physical parameters.
The pulled-back acceleration is not uniformly closer to the projection of full
acceleration: restricting dynamics to represented modes is still an approximation.

The single correction consistently pulls back the complete serial mass and force
functions through the unchanged representation. It retains the serial output and
does not tune stiffness, damping, inertia, gravity, geometry or actuator limits.
Three independently integrated Radau tolerances/maximum steps assess the changed
model on each frozen interval. All twelve integrations completed with finite
solutions, scaled force-balance residuals <=1e-5 and two successive speed/vector
differences <=1e-4. These checks do not transfer to complete histories.

## Local accuracy

| Distinct interval | Position error (m) | Vector error (m/s) | Speed error (m/s) | Direction |
| --- | --- | --- | --- | --- |
| Shared .00-.01 | 3.60446e-5 | 0.00309929 | 0.00300956 | Increasing, correct |
| .075 .01-.02 | 1.68014e-5 | 0.000472262 | 0.000090641 | Increasing, correct |
| .075 .30-.31 | 6.21625e-5 | 0.00487464 | 0.00485669 | Increasing, correct |
| .15 .30-.31 | 6.04562e-5 | 0.00492969 | 0.00468594 | Decreasing, correct |

Direction resolves correctly on 4/4 intervals; position and vector tolerances
pass on 0/4, speed tolerance on 1/4. The .075 holding interval is false-safe.
The physical correction improves all four vector errors relative to the saved
working serial-output predictor, but cannot meet original quantitative criteria.
For the first interval, the old stabilized continuum endpoint under the same
serial output has 0.0416475 m/s vector error; the changed model reduces this to
0.00309929 m/s. Thus the improvement is not solely a coarse-versus-fine comparison.
Holding-start projected positions already differ from backend by about 4.09e-5 m,
above the 1e-6 reporting tolerance before any propagation.

The `local_serial_diagnosis@1.0.0` interface consumes an observed reduced state
and current held input, returning world position/vector/speed, direction,
resolution differences and declared .01 s scope. It accepts no future state or
future input. Numerical differences are not physical-error bounds. The current
evidence supports experimental offline directional diagnosis only, with all
quantitative and threshold failures visible.

## Screening cost and historical discrimination

Saved pair timing attributes 665.726 seconds to controller work, including
195.849 seconds of warm preparation and 469.876 seconds of optimization and
validation. Outside that controller timing, model/graph construction is 7.821
seconds and propagation/output 19.407 seconds; the recorded serialization/loop
remainder is 1.473 seconds. The earlier corrected forecast cost was 694.471 s.

The isolated one-solve response probe reproduces the first two production inputs,
then differs by as much as 2.00003 N in one channel at .02 s. The five-interval
policy is explicitly approximate. No surrogate fit or alternative policy was
tried after seeing this discrepancy.

Both new combined previews completed all 35 intervals with independent candidate
states, commands and plans. Each used seven replans. Exact workflow charges are
110.047 and 110.437 seconds, totaling **220.484 seconds**, a 68.25% reduction.
This includes cold setup, construction, embedded solves, propagation, output and
serialization. Historical trajectories are only scoring data, not free forecasts.

| Holding weight | Predicted max speed (m/s) | Observed max speed (m/s) | Predicted max position error (m) |
| --- | --- | --- | --- |
| .075 | 0.0388530 | 0.0232859 | 0.00295146 |
| .15 | 0.0378865 | 0.0129392 | 0.00297112 |

The predicted gap is 0.000966588 m/s, above the frozen 1e-4 margin. The pair ranks
.15 ahead of .075 correctly: coverage 1/1, accuracy among resolved 1/1, no ordering
error or false rejection under the one-candidate retention rule. This single
historical pair is development evidence, not statistical or prospective reliability.
Both candidates are predicted speed-violating; .15 is actually acceptable, so
eligibility accuracy is only 1/2. The previous full-history .075 false-safe is
removed, while the separate local .075 false-safe remains. No safety or eligibility
authority follows from the correct order.

The recorded arithmetic comparison is against the .075 evaluation the rule would
skip: 303.796 seconds. **Before the still-blocked required research decision**, the
maximum potential net saving is 83.312 seconds. Actual native decision receipts
must be added before final economic admission; treating blocked interaction as
zero operational cost would be incorrect. The retained .15 evaluation still costs
302.141 seconds. Actual evaluations avoided and validation savings are both zero.

## Admission, limitations and next action

The method is not admitted. Original local quantitative accuracy remains failed,
the local false-safe persists, full-history numerical accuracy is unestablished,
and the accepted research judgment and measured required interaction cost are
missing. A ranking-only experiment is a possible research question, not an
automatically approved fallback. Any such role must be frozen before validation
and withhold safety/eligibility authority without erasing the original failures.

The registered `.20` and `.30` reset-clock scenarios and accepted .075/.15 pair
are preserved in the linked protocol. No new reset episode has been forecast or
executed. Recomputed public reservation is 5230 s per batch: 2590 s public base,
2400 s two previews, 180 s local overhead and 60 s export. It fits the 6000 s
ceiling, but budget fit does not establish scientific admission. Batch 2 also
requires the same frozen method and the declared continuation checks; no tuning
between validation batches is authorized under that frozen experiment.

The immediate next action is direct chat confirmation of the concrete DeepSeek
transmission, then resume the saved native packet without recalculation. Obtain
an accepted go/no-go and final interpretation; only an admitted and concretely
frozen validation protocol can materialize grants. The incumbent remains
`batch-ebbeadbdaca10732-0` / `91c3ba1b01d6499fb26df8f95409401b`, .05/.05,
.16/.11 m, .95/compliant, production controller 7.0.0. M2-4 stay closed; M5 stays
open. Real-time control, wider repeatability and family generalization remain unmet.

## Accounting and interventions

| Usage | Predecessors | New development | Validation | Cumulative |
| --- | ---: | ---: | ---: | ---: |
| Provider attempts | 43 | 0 | 0 | 43 |
| Workflow calls | 81 | 7 | 0 | 88 |
| Backend attempts | 6 | 0 | 0 | 6 |
| Charged seconds | 5606.865 | 880.514 | 0 | 6487.379 |
| Additional controller attempts | 79 | 15 | 0 | 94 |
| Standalone integration attempts | 44 | 13 | 0 | 57 |
| Historical backend controller updates | 210 | 0 | 0 | 210 |

The 15 new controller attempts comprise one isolated response probe plus 14
embedded preview solves. The 13 integrations comprise the single continuation
and twelve changed-model local integrations; all completed. Existing histories,
reference endpoints and accepted historical selection were reused without charge.
Protocol/provider semantic corrections remain zero; workers and subagents are zero.

Three engineering interventions are preserved: correcting diagnostic vector-shape
broadcasting (original localization and charged corrected non-advancing evaluation
both retained), and fixing export's distinction between JSON-schema property
objects and concrete artifact references. A campaign-local Git attribute preserves
exact evidence bytes after staging exposed CRLF conversion of a hashed XML artifact.
Export recovered saved artifacts without repeating computations. Both external-call approval rejections occurred before
process creation and consumed no provider quota. Seven focused checks passed;
the final binding check verifies that missing native judgment cannot
silently authorize validation. Production dependency hashes and predecessor
evidence/ledgers remain unchanged.
