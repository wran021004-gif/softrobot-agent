# Milestone 5 accuracy and screening-cost campaign, 2026-10-05

Development and the accepted native research judgment are complete. The first
interpretation was NO_GO but misstated numerical gates and the requirement for
actual savings before validation. One factual follow-up preserved that response,
the original phase budget and all receipts. The corrected judgment is
**GO_EXPERIMENT_RANKING_ONLY**, conditional on the final receipt cost. Reconciliation
passes: 220.484 s for fresh forecasts plus 63.875 s for both required research
interactions totals 284.359 s, giving 19.437 s counterfactual margin against one
303.796 s evaluation. No actual saving has been realized.

The user's direct chat authorization resolved the earlier automatic-review
rejections. The exact rejections and original reviewed payload remain in the audit
trail; two native provider responses and their accepted tool receipts now exist.
The [corrected development judgment](../evidence/milestone5_predictor_campaign_20261005/interpretation_response.json)
permits only a frozen ranking experiment, with safety and eligibility authority
withheld. The [prospective protocol](../evidence/milestone5_predictor_campaign_20261005/prospective_protocol.json)
was frozen before both new candidate forecasts. **Batch 1 completed; Batch 2
stopped** because the sealed decision abstained and counterfactual net saving was
negative. The accepted final native judgment is STOP. The ranking substage is
complete with a negative result; no ranking capability is accepted and M5 stays open.

The existing origin / feat/gvs-dynamics non-force push is directly authorized.
Final commit and remote verification follow this completed scientific closeout;
[publication status](../evidence/milestone5_predictor_campaign_20261005/publication.json)
preserves the earlier blocked checkpoint and subsequent recovery.

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

The comparison is against the .075 evaluation the sealed historical rule would
skip: 303.796 seconds. The two required native research interactions cost 63.875 s,
so full incremental screening cost is **284.359 s** and counterfactual net saving
is **19.437 s**. The margin is small and is not evidence of general economic
reliability. The retained .15 evaluation still costs 302.141 s. Actual evaluations
avoided and validation savings are zero. Development/reference work remains a
separate one-time charge; no completed history is treated as a free future forecast.

## Admission, limitations and next action

Full quantitative prediction is not admitted. Position/vector accuracy still
fails on all four local intervals, the local .075 false-safe persists and complete
history numerical accuracy is not established. These failures remain visible.
The corrected native judgment admits a ranking-only test: whether the same
seven-replan predictor resolves the order of sampled maximum holding speed on the
registered unobserved reset-clock episodes at the unchanged 1e-4 m/s margin.
Prediction remains experimental and cannot certify safety or eligibility.

The registered `.20` and `.30` reset-clock scenarios and accepted .075/.15 pair
are unchanged. Both complete candidate forecasts must be sealed before either
backend execution. Local predictions at new-clock .20 and .30 are sealed before
advancement, using only current observed state and available held command. They
use the same three frozen resolution grids; their original accuracy errors are
scored independently of ranking. Both candidates receive complete evaluation.

Recomputed public reservation is 5230 s per batch: 2590 s public base, 2400 s for
two previews, 180 s local overhead and 60 s export. The 6000 s ceiling, four model
attempts, 16 workflow calls and two backend attempts remain unchanged. Embedded
preview solves count against 70; production's 70 updates are recorded separately.
The four local checkpoints permit twelve integrations, charged inside the backend
workflow. Their measured validation instrumentation is subtracted from the
counterfactual cost of a skipped operational evaluation, avoiding inflated savings.

Batch 2 requires complete valid Batch 1, no local holding or full-history
false-safe, resolved correct rank, all local numerical checks passing, positive
counterfactual net saving including required decision receipts, and accepted native
continuation. Any failure stops the campaign; no method tuning or replacement
simulation is allowed. The incumbent remains `batch-ebbeadbdaca10732-0` /
`91c3ba1b01d6499fb26df8f95409401b`, .05/.05, .16/.11 m, .95/compliant,
production controller 7.0.0. M2-4 stay closed; M5 stays open. Real-time control,
wider repeatability and family generalization remain unmet.

## Prospective Batch 1 and capability acceptance

The `.20` reset-clock batch completed two candidate-specific forecasts, both real
backend executions and full evaluations. The pair seal is event **97**, before
backend reservations **99** and **135**. Local prediction seals are events
**111, 119, 147, 155**, each emitted synchronously before the corresponding backend
step. Current state, actual applied input, time, configuration and execution
bindings were verified. All 35 intervals and 35 production updates per candidate
are present. No incomplete numerical or backend case was replaced or hidden.

| Holding weight | Predicted holding speed (m/s) | Observed holding speed (m/s) | Predicted holding/terminal position error (m) | Observed holding / terminal error (m) |
| --- | ---: | ---: | ---: | ---: |
| .075 | 0.161095836 | 1.149100815 | 0.039132747 | 0.026289243 / 0.016158442 |
| .15 | 0.161095836 | 0.907361857 | 0.039132747 | 0.025127241 / 0.009301106 |

The two predicted histories have identical states and commands despite distinct
configuration identities. Both predicted positions exceed 0.01 m, triggering the
frozen abstention rule; the raw predicted speed gap is also zero. Ranking coverage
is **0/1**, with one abstention, no asserted ordering error and no false rejection;
accuracy among resolved decisions is undefined. Observed raw speed order favors
.15 by 0.241738958 m/s, but both candidates violate holding position and speed
limits, so there is no position-feasible winner under the conditional objective.
Both full-history eligibility predictions abstain (0/2 resolved); this is neither
a successful constraint classification nor a categorical false-safe/false-unsafe.

| Local interval, each candidate | Predicted / observed speed change | Position error (m) | Vector error (m/s) | Signed speed error (m/s) | Direction |
| --- | --- | ---: | ---: | ---: | --- |
| .20-.21 | +0.006666671 / +0.011395251 | 0.000153927 | 0.008491293 | -0.004733323 | Correct increasing |
| .30-.31 | -0.005178438 / +0.001556277 | 0.000184246 | 0.009501082 | -0.006631540 | Incorrect decreasing |

These are **four candidate checkpoint observations but only two unique
state/input/time cases**. Direction resolves 4/4 and is correct 2/4; there are no
neutral or indeterminate results. All four local numerical checks pass, while
position, speed and vector accuracy each pass 0/4 at the original reporting
tolerances. Local speed false-safe and false-unsafe are both 0/4; holding
false-safe is 0/2. These cases do not remove the historical local .075 false-safe
or establish reliable threshold classification. Local numerical convergence does
not establish complete-history convergence or physical accuracy.

Fresh forecast receipts are 156.063 + 172.531 = **328.594 s**. Required research,
including the initial response, native recovery, two factual corrections and
accepted tool submissions, costs **48.705 s**. The all-in screening cost is
**377.299 s**. The sealed rule omits no candidate, so avoided cost is **0 s** and
counterfactual net saving is **-377.299 s**. Actual evaluations saved and actual
savings are zero. The historical admission margin of +19.437 s did not transfer.

Both complete evaluations cost 692.032 and 710.015 s with instrumentation.
Measured local validation-only instrumentation is 1.532639 and 1.499520 s, leaving
operational comparators of 690.499361 and 708.515480 s. Neither is counted as
avoided because the decision abstained. Two candidate preparation receipts cost
0.063 s separately in the validation ledger. All validation charges total
1779.409 s; no cost category was moved to obtain a favorable margin.

The frozen continuation condition includes **both local holding false-safe and
full-history false-safe**. Complete evaluation, local numerics and no false-safe
pass on this batch; resolved correct ranking and positive net saving fail. The
accepted final research judgment is **STOP**. Batch 2 has no grant, preview or
backend attempt. A narrower ranking role did not remove any stop condition.

| Original requirement | Acceptance conclusion |
| --- | --- |
| Numerical reference | Supported on the explicitly tested local scopes; complete-history convergence unestablished |
| Local directional diagnosis | Experimental only: 2/4 prospective observations correct, two unique cases |
| Local quantitative prediction | Failed: 0/4 position, vector and speed passes |
| Constraint/threshold reliability | Unsupported; historical false-safe retained, full-history eligibility abstains |
| Prospective ranking usefulness | Failed useful-screening gate: 0/1 resolved, no omission |
| Operational economics | Failed: -377.299 s counterfactual net benefit |
| Causal sealing, identity and recovery | Verified; existing native store, receipts and phase counters retained |
| Repeatability and real-time | Unestablished repeatability; 70/70 new and 35/35 incumbent deadline misses |

The [acceptance audit](../evidence/milestone5_predictor_campaign_20261005/acceptance_audit.json)
uses the original documented milestone requirements. The ranking experiment is
closed as a negative result; Milestone 5 remains open, M2-4 remain closed and the
incumbent is retained. Complete candidate evaluation remains necessary.

One precise next objective is to investigate the lost weight-dependent controller
response at the saved first production input divergence, **.32 s**, which is an
omitted replan in the five-interval predictor. A separately bounded investigation
would compare exactly two unchanged production-controller solves at one common
observed reduced state, available previous input and common initialization. Command
separation above 1e-9 N supports this specific diagnostic hypothesis; otherwise
reject it. Preserve early acceptance. This investigation is not executed here and
would not itself repair local dynamics accuracy or establish screening utility.
Any resulting predictor version needs untouched prospective reset-clock pairs,
the original accuracy/constraint/ranking metrics and positive all-in economics;
this completed batch would be development evidence for that revision.

See [Batch 1 assessment](../evidence/milestone5_predictor_campaign_validation1_20261005/assessment.json),
[final native judgment](../evidence/milestone5_predictor_campaign_validation1_20261005/interpretation.json)
and [saved controller comparison](../evidence/milestone5_predictor_campaign_validation1_20261005/saved_controller_comparison.json).

## Accounting and interventions

| Usage | Predecessors | New development | Validation | Cumulative |
| --- | ---: | ---: | ---: | ---: |
| Provider attempts | 43 | 2 | 3 | 48 |
| Workflow calls | 81 | 9 | 14 | 104 |
| Backend attempts | 6 | 0 | 2 | 8 |
| Charged seconds | 5606.865 | 944.389 | 1779.409 | 8330.663 |
| Additional controller attempts | 79 | 15 | 14 | 108 |
| Standalone integration attempts | 44 | 13 | 12 | 69 |
| Backend controller updates | 210 | 0 | 70 | 280 |

The 15 new controller attempts comprise one isolated response probe plus 14
embedded preview solves. The 13 integrations comprise the single continuation
and twelve changed-model local integrations; all completed. Existing histories,
reference endpoints and accepted historical selection were reused without charge.
One semantic provider correction and zero protocol recovery corrections were used
in development; workers and subagents are zero. The original phase budget and
started-usage counters were preserved. The first response remains available rather
than being rewritten. Its estimated correction runtime is superseded by the actual
31.829 s receipt in the economic assessment.

Four engineering interventions are preserved: correcting diagnostic vector-shape
broadcasting (both original and corrected charged observations retained), fixing
export's distinction between JSON-schema property objects and concrete artifact
references, adding campaign-local Git attributes to preserve hashed raw bytes,
and converting a correction-packet reference to plain JSON before serialization.
That last failed transaction rolled back before authentication or provider dispatch.
No completed integration, optimization, preview or API result was replayed.
Earlier approval rejections occurred before process creation and consumed no quota.

The seven development checks previously passed. After the accepted correction,
five focused checks passed: two new sealing-point tests and three receipt/budget,
causality/cost and accepted-binding checks. Static validation confirms exact frozen
implementation identities and unchanged public reservations before any prospective
computation. Production dependency hashes and predecessor evidence remain unchanged.
The final prospective binding/recovery test also passed, including real seal
sequences, all current-input bindings, accepted native research references, zero
duplicate previews/backends, original phase counters and no unresolved writers.
No broad suite or numerical/API replay was run.

Validation needed one engineering recovery: the research handoff inherited a
900 s simulation allowance, exceeding its 600 s phase, and its packet lacked the
required selected-weight field. The rejected tool attempt counts. A research-only
session revision supplied the established 10 s timeout / 5 s reservation and
frozen weights in the same grant, preserving phase usage. It submitted the exact
saved native response without another provider call. A copied result-ownership
cache was then removed from that research-only session after a read-only lookup
failure; original execution ownership and results were retained.

Two subsequent native factual corrections fixed time/candidate indexing, the
next-investigation definition and stale economics. Original responses remain
preserved. The final model explicitly leaves its own call cost for receipt
reconciliation: its 370.970 s subtotal plus the final 6.329 s charge gives the
377.299 s reported above. Validation used 3/4 provider, 14/16 workflow, 2/2 backend,
14/70 preview controller and 70/70 production updates within 1779.409/6000 s.
The original research phase used 3/4 provider and 4/4 workflow slots, including
the rejected submission; no capacity was reset. Two semantic corrections and one
engineering repair stay within the three-repair bound. No workers or subagents.
