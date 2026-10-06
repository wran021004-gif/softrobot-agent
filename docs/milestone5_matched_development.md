# M5 full feedback trajectory development checkpoint — 2026-10-06

**Milestone 5 remains open.** Two complete forecasts and two new independent
development backend executions used the same scoped native experimental
controller. Accuracy and holding-speed classification failed; correct pair
ordering did not establish useful or economical screening. No revision or
same-policy rerun was justified. The incumbent and all six protected formal
validation slots remain unchanged.

## Frozen comparison and execution

The existing development cases `original075` and `original15` retain their
exact saved robot, task, full initializer, controller weights and numerical
settings. Their historical source executions are respectively
`2413ff2a56de422dac47b7fd78717563` and `9865f1636266479c93817cad42a65353`.
Those historical outcomes are not acceptance results for this new controller.
The [protocol](../evidence/milestone5_matched_20261006/protocol.json) identifies
the physical and numerical settings, full state, mappings, .5 ms physical
step, .01 s replanning period, output times and unchanged quantitative rules.

The hash-checked local `gvs_native_chunked_kernel@2.0.0` DLL was reused.
No compiler experiment, package change, solver migration, skipped replan or
stopping-policy change occurred. The provider ContextVar was active only
within these experimental executions. Default production functions were
unchanged. Both forecasts evolve their own full state, previous command and
plan; each command is retained before emulated propagation.

Both 35-update forecasts, component classifications and feasibility-qualified
ordering were [sealed together](../evidence/milestone5_matched_20261006/pair_seal.json)
before either new backend reservation. The actual matching executions are
`95a801287a2646bbab73416a19c38dcc` and `5e34c91605904d5fae877c465b963cf7`.
Each completed its existing official evaluation and profile. Emulation was
not substituted for either backend.

## Prediction and classification

| Candidate | Terminal error, predicted / actual (mm) | Holding max error, predicted / actual (mm) | Holding max speed, predicted / actual (m/s) | Joint pass, predicted / actual |
| --- | ---: | ---: | ---: | --- |
| original075 | 3.188024 / 3.179143 | 3.226667 / 3.373475 | 0.012173523 / 0.022343916 | True / False |
| original15 | 3.196551 / 3.253346 | 3.291358 / 3.290348 | 0.010424726 / 0.014704772 | True / True |

Both candidates pass actual and predicted terminal/holding-position task
classification. `original075` falsely predicts holding-speed and joint
feasibility; `original15` classifies all task components correctly. There are
no false-infeasible classifications. This does not establish quantitative
accuracy: both candidates fail every aggregate accuracy gate under the
original 1 micrometre position and .0001 m/s speed/vector tolerances.
Only 2/35 and 6/35 samples respectively pass each trajectory output gate.
The .15 holding-position aggregate discrepancy is 1.009776 micrometres,
slightly above the unchanged 1 micrometre threshold.

Predicted and observed position-qualified speed ordering both resolve to
`original15`, then `original075`; there is no abstention or wrong exclusion.
One correct development order, failed accuracy and a false-feasible speed
classification do not establish reliable screening, superiority or safety.

## Discrepancy localization and numerical support

For .075, the first meaningful command and output discrepancy occurs at
update 2, time .02 s. Current full/projected state differences are only
1.33e-15 / 8.53e-14 and previous input differs by 1.11e-15 N, yet selected
iterations are 5 versus 10 and commands differ by .047479 N. Current states
separate at update 3. For .15, small command/projection differences appear
at update 4; accuracy first fails at update 6, with selected iterations 4
versus 10. This is consistent with timed iteration selection sensitivity.
Temporal order does not isolate a unique cause; floating-point state
differences, evolving warm plans and later feedback remain relevant.

Four post-outcome fixed-input diagnostics at .075 updates 0/1/30 and .15
update 30 used eight LU/independent-Cholesky component evaluations. All pass
`fixed_backend_transition_validation@2.0.0`, including comparison against
the new matched backend endpoints. They support those fixed .5 ms maps,
not the accuracy of sealed closed-loop histories or continuous/hardware
dynamics. The six existing local checks are reused; historical continuous
solution and step-refinement failures remain preserved. Diagnostic outcomes
were never supplied to either sealed forecast.

## Cost, latency and decision

Forecast receipts total **393.312 s**. The metered forecast
plus pair-seal boundary and both required model interpretations cost **434.031 s**.
The corresponding complete .075 backend boundary costs **194.951 s**;
counterfactual net saving is **-239.080 s**. Both backends ran, so
actual avoided evaluations and actual screening savings are **zero**.
This method is more expensive than the work its sealed order could omit.

The reuse boundary includes configuration/model/native loading, controller
setup, observation/projection, graph/warm preparation, optimization,
validation, command packaging, emulated propagation, seal/export overhead
and required model interpretation/correction. Store event spans settle
wrapper gaps once, without replay or double charging. Static protocol
registration and first harness registration before the initial reservation
follow the existing offline engineering convention. These are software
cost boundaries, not end-to-end hardware measurements.

Cold compilation for this exact structure would add the historical measured
599.757 s; it was not charged again or assumed free for other structures.
Fresh structures need their own loading/compilation assessment. Development
diagnostics and matched backends are separate from operational screening cost.

| Candidate | Forecast software interval mean / median / max (s) | Backend software update mean / median / max (s) | Deadline misses, forecast + backend |
| --- | ---: | ---: | ---: |
| original075 | 5.556725 / 6.515356 / 14.277510 | 5.370491 / 6.488790 / 14.367679 | 35 + 35 |
| original15 | 5.567795 / 6.527531 / 14.401885 | 4.922291 / 6.499324 / 14.156791 | 35 + 35 |

Forecast input-to-command intervals are directly measured from supplied
full state through projection/output preparation and packaged command.
Backend intervals include current observation/projection and controller
computation. Applying the command to simulated actuators and physical
propagation are outside that command boundary and included in full backend
cost. Forecast propagation is separately measured. Sensor/network/hardware
delivery latency is not measured. Individual component distributions and
one-time setup are retained; no small-sample worst-case guarantee is claimed.

Optimization is the measured dominant component: **299.176 s**
across the forecast pair, versus **83.647 s** warm preparation
and **3.142 s** validation. All 140 command updates miss
the original **10 ms** requirement. No coherent equation-preserving revision
was justified by these accuracy, cost and latency results, so the chosen
action is to stop this route at the development checkpoint.

A genuine DeepSeek interpretation and one neutral factual correction assess
these measurements. The original response, numerical decisions and failed
factual review are preserved. Model readiness language cannot override a
failed numerical, classification, cost or realtime gate.
The [corrected model report](../evidence/milestone5_matched_20261006/interpretation1.json)
passes the [final factual review](../evidence/milestone5_matched_20261006/final_factual_review.json);
the [original report](../evidence/milestone5_matched_20261006/interpretation0.json)
and [its failed review](../evidence/milestone5_matched_20261006/interpretation_review0.json)
remain available. Closure of this bounded development checkpoint does not close M5.

The next technical objective requires a separately explicit substantive
controller/termination design that meets the full software 10 ms deadline,
followed by new matched accuracy/classification studies. Formal admission
still requires original local/trajectory accuracy, useful position-qualified
ordering, positive complete economics, realtime and accepted factual research
interpretation before the two untouched pairs and registered independent
repeat. None of those protected cases ran here.

New M5 charges: **2 provider / 19 workflow / 2 backend / 808.364 s**.
There are 70 standalone forecast controller updates, 70 separately recorded
embedded backend updates, 2 complete forecasts, 1,400 forecast-emulated steps
and 160 additional diagnostic-emulated steps. Eight component evaluations
form four diagnostic intervals; these are not another set of controller
solves. Unused new M5 allocations and linked lifetime receipts are in
[accounting](../evidence/milestone5_matched_20261006/accounting.json). Zero
workers or subagents ran; all six protected backend slots remain available.

Evidence: [final operational assessment](../evidence/milestone5_matched_20261006/operational_assessment.json),
[initial assessment](../evidence/milestone5_matched_20261006/assessment.json),
[fixed-input diagnostics](../evidence/milestone5_matched_20261006/fixed_diagnostics.json),
[focused checks](../evidence/milestone5_matched_20261006/focused_checks.json),
[pair cost boundary](../evidence/milestone5_matched_20261006/pair_boundary_settlement.json).

The initial protocol, prelaunch wrapper amendment and later reporting-only
transport correction have separate recorded identities. Controller, native
kernel, equations, numerical tolerances and stopping semantics stayed fixed
through both forecasts and both backend executions.
