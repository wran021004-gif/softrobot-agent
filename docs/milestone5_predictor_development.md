# Milestone 5 predictor development, 2026-10-05

The bounded development stage ends **not ready**. One predictor-only observation
map is implemented and assessed on the frozen cases. Local holding direction is
correct on 2/2 distinct intervals, but quantitative accuracy remains failed.
Full-task ranking abstains on 1/1 pair, the .075 full-history false-safe persists,
and screening costs more than either evaluation it could skip. No prospective
forecast, grant, backend evaluation, or backend step was launched. Milestone 5
remains open; broader repeatability and real-time requirements remain unmet.

The configured research model's [corrected final interpretation](../evidence/milestone5_predictor_development_20261005/interpretation_response.json)
is **accepted: NOT READY**. After the default client's `DEEPSEEK_NETWORK_ERROR`
and the preserved automatic-approval rejection, the user directly confirmed the
payload and supported host-execution path. The same native handoff then succeeded.
One semantic follow-up corrected confusion between backend error and resolution
differences, the undersized guard and mathematical instability, and the next
investigation's interval. Both model responses and their receipts are preserved.
Earlier accepted selection and direction C are reused; no completed numerical
work or old research selection was repeated.

## Frozen scope and acceptance

[Plan and seal](../evidence/milestone5_predictor_development_20261005/freeze.json)
were saved before new numerical results. Cases remain the original shared
.00–.01 s interval, early .01–.02 s divergence, .30–.31 s holding entry, and the
two historical .075/.15 complete .00–.35 s histories with .30–.35 s holding.
Both exact historical executions and all manifests are bound explicitly.

Numerical reference requires finite roots, scaled residual <=1e-5 and the last
**two** successive fine comparisons satisfying both vector and speed <=1e-4 m/s.
Backend agreement is separate. Reporting tolerances remain position 1e-6 m and
speed/vector 1e-4 m/s; physical limits remain .01 m/.02 m/s. Ranking margin stays
1e-4 m/s. Prospective entry also requires an evidence-backed correction, causal
and complete forecasts, useful historical discrimination, handling of known
failures, cost below the expected **one** skipped evaluation, a worthwhile
independent experiment, accepted research interpretation and sufficient budget.
No easier cases or changed thresholds were selected after results.

Development ceilings are 10 provider/50 workflow calls, three additional first
reference attempts, 12 other short integration attempts, two full previews,
80 additional optimization attempts, zero backend/worker/subagent attempts and
4800 charged seconds. Interpretation/export capacity was reserved. The separate
conditional first-batch ceilings remain 4/16/2 provider/workflow/backend attempts,
two previews, 70 preview plus 70 production controller attempts and 6000 seconds.
Previous grants, seals, outcomes and usage are unchanged.

## Reference completion and execution defect

[Reference recovery](../evidence/milestone5_predictor_development_20261005/reference.json)
reuses all six previous results and completes .000015625 s/640 substeps and
.0000078125 s/1280 substeps. Their integration times are 149.301 and 299.294 s.
The two final continuous-map vector/speed differences are
.0001241099/.0001227236 and .0000621189/.0000614253 m/s. Only the last comparison
passes. Completed roots are finite; maximum scaled residual is 5.894e-11.
The finest completed continuous velocity error is .0101438909 m/s. Worsening
backend agreement is not a numerical stability failure condition.

The third declared .00000390625 s/2560-substep attempt failed with
`FIRST_INTERVAL_DEADLINE`. I incorrectly gave every integration a 400-second
guard, although measured scaling predicts about 600 seconds for this last one.
This is an execution configuration defect, **not evidence of instability**.
The failed attempt counts. Its completed endpoint does not exist; no fourth
attempt or partial-state reconstruction was invented. Two completed subresults
were recovered from their original artifacts without replay. The exact runtime
implementation and failed outer receipt are preserved.

Diagnostic tool 1.0.1 corrects a future integration's guard to 800 seconds, within
the unchanged 1200-second outer reservation. This repaired reference path was
not executed. The original shared physical state, zero reduced state, held direct
input, .01-second interval and model remain unchanged. Existing 320-substep
defaults are preserved; only this diagnostic continuation permits 2560.
First-interval stability remains unresolved; holding-entry references cannot
stand in for it or for full-history stability.

## Located source and one correction

[Localization](../evidence/milestone5_predictor_development_20261005/localization.json)
uses saved full coordinates/rates, the registered
`backend_discrete_to_gvs_integrated_v2` projection, exact compiled joint/body
indices and the saved XML's world-frame `tip_site`. It uses forward kinematics
and site Jacobians, never backend stepping. Continuous and represented serial
position maps both have consistent velocity Jacobians: maximum differential
check discrepancies are 1.019e-9 and 2.036e-9 m/s. Projection round-trip norm is
<=1.03e-13. Thus this is not an established projection implementation bug.

At the observed .01 s projected state, continuous output differs from backend by
.000251437 m and .034070582 m/s. Represented serial output differs by
3.263e-8 m and .000016374 m/s. At .31 s the two candidates' instantaneous serial
vector discrepancies are .000067580/.000047062 m/s, while their shape position
residual is about 41 micrometres. Projection still drops cell shape/rate modes.
Units, frames and tip identity agree; the continuum and discrete-chain
kinematic definitions differ.

The single [selected correction](../evidence/milestone5_predictor_development_20261005/correction.json)
is `represented_serial_output@1.0.0`: report the represented serial tip position
and velocity from the **same** world-frame position Jacobian. Reduced continuous
dynamics, physical parameters, production controller 7.0.0, optimizer policy,
early acceptance and controller transcription are unchanged. The working local
method holds the currently available ideal direct command for .01 s, uses
.000125 s propagation with a .00025 s comparison and reports position, velocity,
speed, direction and numerical uncertainty. It explicitly withholds stability
from a two-grid check alone and any quantitative/safety authority.

The complete screening history uses the existing .01 s reduced propagation and
unchanged production NMPC computation on its own predicted state, with its own
warm plan and previous input. This remains a reduced model of the backend plant.
Output mapping does not feed back into command selection or propagation, so
exact previously completed independent state/input/controller histories can be
reused. Their original request, receipt and scientific configuration are checked;
the changed output map accepts only each candidate's own predicted state. No
future measured input/state/outcome enters its forecast. No 70-solve replay or
new complete preview was necessary for an output-only correction.

## Historical assessment

[Assessment](../evidence/milestone5_predictor_development_20261005/assessment.json)
separates working predictions from offline finest results. There are six local
reports: the shared first result is reported twice, plus two early coarse checks
and two holding cases. The primary working assessment has **three distinct
intervals**. Direction resolves on 2/3 and is correct on 2/2 resolved intervals.
First-interval numerical uncertainty forces abstention despite the correct raw
direction. Velocity, speed and position passes are each **0/3**. The early coarse
checks have no fine reference and are not counted as validated working cases.

| Case and step | Old vector error m/s | Corrected vector error m/s | Corrected speed error m/s | Corrected position error m |
|---|---:|---:|---:|---:|
| Shared .00–.01, .000125 | .009731710 | .040597792 | +.038772233 | .000271740 |
| Early .01–.02, saved .01 coarse | .049296899 | .012305722 | -.012060337 | .000155557 |
| .075 holding .30–.31, .000125 | .006823542 | .006012681 | -.002346184 | .000075195 |
| .15 holding .30–.31, .000125 | .007304575 | .006863583 | -.002762828 | .000077912 |

The corrected .075 holding prediction is .020939763 m/s against .023285948
observed, so the local false-safe is removed on this interval: 0/2 holding cases.
Both directions remain correct. Numerical reference comparisons for these two
serial outputs pass their two-successive rule. This narrow result does not
establish quantitative endpoint accuracy or safety.

First-interval total error worsens after a physically consistent observation
map because the old output and evolution discrepancies partially cancelled.
At the finest completed serial result, evolution/output/total vector norms are
.041613536/.000016374/.041613424 m/s. The telescoping identity has zero residual;
it is an ordered decomposition, not causal percentages. Improved instantaneous
observed-state reconstruction does not repair reduced propagation or discarded
state modes.

Both full histories remain complete and independent. Corrected holding maxima
are .008092882 and .008090361 m/s; gap 2.52085e-6 is below the frozen margin.
Resolved ranking is **0/1**, abstention **1/1**, accuracy among resolved is
undefined, ordering errors among resolved **0/0**, and false rejection **0**
because no candidate is rejected. Actual maxima remain .023285948/.012939198.
Both forecasts label predicted-safe, so the visible full-task false-safe is
**1/2 (.075)** and eligibility correctness **1/2**. Those labels are scored
experimental predictions; eligibility/safety claims are withheld.

## Economics and prospective status

New output/setup processing for the two forecasts costs .044229 s. Reused
measured state/controller history work costs 694.426648 s, giving a per-pair
forecast estimate **694.470877 s** for the unchanged computation plus correction.
Exact complete-evaluation receipts sum to .075 **303.796 s**, .15 **302.141 s**,
pair **605.937 s**. At most one evaluation can normally be skipped while one is
retained. Even the larger possible saving is only 303.796 s, so screening would
lose at least **390.675 s** in a hypothetical resolved decision. Actual abstention
skips zero and net forecast overhead is 694.471 s. No new validation ran; actual
validation savings are zero.

Working local two-grid integrations reuse measured costs of about
27.836/28.280/28.235 s for first/.075/.15 intervals, under existing model caches.
Fresh model setup is additional; predecessor cold construction was about 6.9 s.
This is explicitly a cached-cost estimate, not a newly measured cold invocation.
Full forecast setup is already included in the historical costs. Reusing setup
cannot make 694 seconds economical against one 304-second evaluation. One-time
new-stage reference/development cost is separately 922.563 charged seconds,
including all three provider attempts and both accepted handoff calls;
it is not an operational screening saving or an extra charge on reused work.

The [linked protocol](../evidence/milestone5_predictor_development_20261005/protocol.json)
retains `incumbent_checkpoint_20_new_clock`, the exact restored physical state,
zero clock, reset controller and direct-input initialization, and .075/.15 with
terminal .05. These prospective scenario/recipe outcomes remain unobserved.
The first batch is not launch-ready or granted; no second-scenario batch is
authorized. Existing forecast-pair and local-before-step sealing semantics remain
recorded but have no new prospective seals to score.

Current public rules recompute the base reservation as 2590 s and the nominal
complete reservation as **5830 s** against 6000 s: 3000 preview, 180 local
overhead and 60 export seconds beyond the base. Provider/workflow/backend
ceilings are 4/16/2, with 70 preview and 70 production attempts reported
separately. This arithmetic is not changed-method budget admission: new full
preview/checkpoint execution costs and numerical scopes have not passed entry.
No reserves were lowered and no grant was materialized.

## Decision, remaining obstacle and next bounded investigation

The accepted research and engineering go/no-go is **no-go**: unresolved original first reference, universal
ranking abstention, retained full-task false-safe and adverse economics each
prevent prospective entry. The shared finalizer verifies the prior selection and
new corrected interpretation against their completed native receipts in their
respective stores. Final interpretation artifact:
`114049254d15bea569a9603bfdd462f28d077910294559a4617c7a786f288484`;
accepted handoff execution: `cb658588c2d04e4782ff2b1f24fa3a7a`.
Both research-completion flags are true; scientific readiness remains false.
No candidate is promoted. Incumbent remains
`batch-ebbeadbdaca10732-0` / `91c3ba1b01d6499fb26df8f95409401b`, .16/.11 m,
.95/compliant, .05/.05, controller 7.0.0. Its 35/35 deadline misses remain the
separate real-time status.

The model supports the represented serial map as a self-consistent, narrowly
scoped offline diagnostic, with direction evidence limited to the frozen holding
intervals. Quantitative endpoint accuracy and eligibility/safety are unsupported.
Screening remains experimental and deferred; complete evaluation remains necessary.
Another candidate validation batch is not justified by the current evidence.
The model's compressed phrase "position/speed/vector passes are 0/0/0" denotes
zero passes in each metric; the explicit denominator is **three distinct working
intervals**, as reported above. Both holding candidates' errors are reported
separately. Neither wording changes the underlying scored evidence.

The precise numerical follow-up is **one** .00000390625 s/2560-substep original
first-interval integration with the repaired 800 s guard and 1200 s outer
reservation, reusing the existing eight completed results, under a fresh bounded
authorization. Finite roots/residual and the two final vector/speed comparisons
would decide reference stability; physical agreement is not that gate. A timeout
leaves completion unresolved; nonfinite roots, an excessive residual, or a final
comparison above 1e-4 fails this bounded reference-completion criterion.
Even success cannot authorize screening while discrimination and one-skipped
economics remain failed. No further predictor branch, parameter fit, weight
sweep or candidate batch was launched.

## Usage, interventions and verification

[Exact accounting](../evidence/milestone5_predictor_development_20261005/accounting.json)
reconciles all receipts; no occupied reservation remains.

| Ledger | Provider | Workflow | Backend | Charged s |
|---|---:|---:|---:|---:|
| Historical | 40 | 76 | 6 | 4684.302 |
| Development | 3 (1 transport failure, 2 completed) | 5 | 0 | 922.563 |
| Conditional validation | 0 | 0 | 0 | 0 |
| Cumulative | 43 | 81 | 6 | 5606.865 |

Three new reference attempts comprise two completions and one failure; other
short integrations, controller attempts, new full previews, backend updates,
workers and subagents are all zero. Cumulative additional controller attempts
remain 79; standalone integration **attempts** become 44 (43 completed when the
41 predecessor completions are included); historical backend updates remain 210.
Six previous first results, six holding references, fourteen substitutions and
two full independent histories were reused without new charges.

Protocol-recovery corrections are 0 total/0 consecutive; semantic provider
corrections are **1**. Combined correction use is 1/4, with one consecutive
semantic correction, within the ceiling of two. The approval rejection did not
start a provider process and adds no provider attempt. Engineering interventions are
recorded in [interventions](../evidence/milestone5_predictor_development_20261005/interventions.json):
initial bound-reference identity repair before numerical work, explicit session
revisions preserving the same grant and phase counters, the undersized integration
guard, transport/platform failures, an export artifact-reference type check, and
git sandbox fetch recovery. No credentials enter evidence. Seven focused checks
pass: default versus diagnostic substep cap; real-state position/velocity
derivative alignment; immutable predecessor and receipt reconciliation;
resolution differences versus physical errors; independent history reuse and
both accepted research bindings; rejection of missing accepted receipts; and
production-default/public-reservation isolation. Evidence hashes and exported
implementation identities are also verified. No broad suite or extra simulation
was run.

Task-related source, evidence and reports are committed/pushed without force;
publication receipt is recorded separately after the remote contains the commit.
