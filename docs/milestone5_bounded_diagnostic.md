# Bounded Milestone 5 saved-evidence diagnosis, 2026-10-05

This **new linked diagnostic stage is complete and stopped**. The research model
selected **D: retain local diagnostic use and defer run-ahead screening**. No
candidate was promoted. The deliverable remains `batch-ebbeadbdaca10732-0`,
execution `91c3ba1b01d6499fb26df8f95409401b`, holding/terminal weights .05/.05,
controller `controller.gvs_nmpc@7.0.0`, near/far .16/.11 m, scale .95, compliant
material. Milestones 2–4 remain closed; Milestone 5 remains open.

See [delivery](../evidence/milestone5_diagnostic_20261005/delivery.json),
[explicit research handoff](../evidence/milestone5_diagnostic_20261005/research_handoff.json),
[interval evidence](../evidence/milestone5_diagnostic_20261005/single_context/intervals.json),
[preview evidence](../evidence/milestone5_diagnostic_20261005/single_context/preview.json),
and [accepted model response](../evidence/milestone5_diagnostic_20261005/single_context/final_response.json).
The completed predecessor's entire evidence directory, session states and usage
were checked unchanged. Its four correct local prospective directions, zero
endpoint passes, four unresolved full-task forecasts and abstained ordering stay
immutable. The two latest executions are development data here. Current
calculations are retrospective; they provide no new prospective accuracy.

## Speed error and numerical resolution

Each .30–.31 s calculation uses its own recorded projected initial state, actual
applied tension and exact duration, located through the exact execution manifest.
World backend velocity is reconstructed from saved serial q/qdot and sealed XML
using `J_site(q) @ qdot`. Backend kinematics are evaluated without stepping or
replaying a simulation. Requested and applied inputs agree. Full vectors, their
norms and their sources are retained in the interval evidence.

Predicted-minus-observed endpoint error equals initial projection error plus
predicted-change-minus-observed-change error. This holds for vectors; a separate
identity holds for speed norms. The second term blends projection, omitted modes,
integration and solved transcription; it is not a uniquely isolated dynamics error.

| Quantity | Holding .075 | Holding .15 |
|---|---:|---:|
| Initial position discrepancy, m | .002689177882 | .002688984482 |
| Initial speed offset, m/s | +.000016801317 | −.000058143445 |
| Initial velocity vector error norm, m/s | .000379223713 | .000364315408 |
| Predicted speed change, m/s | +.004824189031 | −.007050978817 |
| Observed speed change, m/s | +.011173371397 | −.001916066335 |
| Change discrepancy, m/s | −.006349182366 | −.005134912482 |
| Saved endpoint speed discrepancy, m/s | −.006332381049 | −.005193055927 |
| Saved endpoint velocity vector error norm, m/s | .007492333503 | .006934123088 |

Thus the small initial scalar offsets do not explain endpoint underestimation,
and do not establish initial vector agreement. All vector/position identities
close to floating-point precision. The .075 prediction is below .02 m/s while the
observed endpoint is above it; .15 is below the limit in both prediction and
observation. This is one false-safe out of two development intervals, not a new
prospective validation statistic.

Exactly **six** reduced-model rollouts ran: two intervals at .01, .002 and .001 s,
with the same dynamics, implicit Euler family, initial state and held tension.
There were **zero additional controller optimizations**. Construction, root
verification and calculation time are included in hosted receipts.

| Step, s | .075 endpoint speed, m/s | .15 endpoint speed, m/s |
|---|---:|---:|
| .01 | .016953566891 | .005829992416 |
| .002 | .018402548747 | .006790903668 |
| .001 | .018609956973 | .006920253274 |
| Saved backend endpoint | .023285947510 | .011023132122 |

The coarse root reproduces saved production speed to +4.30e-10 / −8.38e-8 m/s;
velocity-vector differences are 2.62e-9 / 9.20e-8 m/s and positions differ by
2.62e-11 / 9.19e-10 m. Saved first-step scaled defects are 5.10e-8 / 1.91e-6;
their small tolerance-related root differences cannot explain the large mismatch.
No root/transcription non-reproduction was mislabeled as integration error.

Coarse-to-.001 speed increases are .001656390082 / .001090260858 m/s, reducing
scalar endpoint errors by **26.16% / 20.99%**. Numerical resolution is a material
contributor. Remaining errors are −.004675990537 / −.004102878848 m/s, still over
40 times the unchanged 1e-4 tolerance. The .075 finer result remains false-safe.

The .002-to-.001 speed differences are .000207408226 / .000129349605 m/s, both
above that tolerance; velocity differences are .000247156818 / .000173479353 m/s,
and position differences 1.21e-5 / 6.94e-6 m. These results do **not** demonstrate
convergence at reporting tolerance. Root residual maxima are at most 4.49e-11,
which verifies solved equations, not physical accuracy or integration convergence.
For .075 the vector error improves from .007492334429 to .006859011574 m/s; for
.15 it worsens from .006934196218 to .007222011083 m/s. Scalar speed improvement
alone cannot justify an accuracy or screening claim. The remaining cause is not
uniquely identified; no material/structural fitting or scalar correction was made.

## Why the cold preview lost discrimination

At .30 s the common repeated previous-input cold seed is regenerated through the
candidate dynamics. Its maximum position error **.001360190821 m** is below the
settled-seed position threshold **.005 m** (half the .01 m task tolerance), and
maximum speed **.019915546834 m/s** is below **.02 m/s**. Independent feasibility
passes with scaled violation **5.279447940e-12**. These checks are independent of
holding weights .05/.075/.15; terminal weight is .05 throughout.

The feasible-iterate callback accepts iteration zero through
`verified_settled_seed`. Objectives are evaluated and can depend on weight, but
there is no weight-dependent optimization update before seed acceptance. All
first commands equal the common previous input:
`[3.7361075486,5.3572081605,1.6263988170,2.8012972481,1.6272059076,1.7895461086] N`.
The frozen full-task mapping used these identical .30 s plans, hence abstention.
At .20 s, the seed was not settled and all three previews selected iteration 5
through `relative_seed_improvement`; those small plan differences were not the
frozen full-task mapping.

Production at .30 s selected iterations 7 / 11 / 7 for incumbent/.075/.15,
through `relative_seed_improvement`. The incumbent checkpoint state and previous
input equal the common preview's; the two development candidates have different
states and previous inputs. Their state-vector differences from the common
preview have norms .11927/.46077 (mixed generalized-coordinate units), and maximum
input differences .0011278/.0043518 N. These values are not endpoint errors.
Actual commands, initial states, previous inputs, selection and stops are retained
in the preview evidence. Production keeps its own evolving selected-plan history.
Exact historical warm plans/optimizer snapshots were not retained. Their
availability was checked once through manifests; none was invented or recovered
by replay. Initialization/history, differing state/input and optimizer paths
remain distinct explanations. No warm-start-only attribution follows.

The saved seed and callback evidence sufficiently explain cold preview equality;
no paired solves or diagnostic bypass were needed. Production defaults were not
changed. Historical missing warm plans do not prove a future generated-history
method impossible; such a method remains unvalidated. Online diagnosis may use
executed actual history, while run-ahead screening must generate history without
access to an unseen candidate's future backend state or warm plan.

## One decision and the unexecuted next protocol

Retain **D**, local diagnosis only. Numerical integration is a supported
contributor, but adopting the finer calculation does not establish endpoint
accuracy, consistent vector improvement, convergence or screening value. No
specific projection/model defect was identified and no controller history method
was validated. No production controller/predictor patch was adopted.

The [frozen future protocol](../evidence/milestone5_diagnostic_20261005/next_validation_protocol.json)
retains the unchanged .01 s production predictor and incumbent controller. A
separate future grant would freeze two genuinely independent held-out initial
histories before backend execution, sealing actual-input predictions at .20/.30 s
and comparing .21/.31 endpoints. The exact new histories must be registered in
that future grant; deterministic identical replays are not independent evidence.
Known .075/.15 outcomes remain development data.

It reports scalar/vector projection, change and endpoint errors; direction with
±1e-4 m/s rules; scalar and vector accuracy at 1e-4 m/s; threshold margins and
false-safe/false-unsafe counts; resolved coverage and conditional accuracy
(undefined with zero resolved); invalidity/abstention; useful local information
relative to capture/reconstruction/interpretation cost. Full-task screening and
ordering always abstain under D. Physical holding .01 m/.02 m/s and real-time
acceptance stay unchanged. The previous preview's 73.313 s versus the two full
evaluations' 605.937 s demonstrates lower cost, not decision value.

Proposed **future** ceilings: 4 provider attempts, 20 workflow calls, 2 backend
attempts, 0 extra solves/rollouts, 2500 charged seconds, 0 workers, 2 corrections
with at most 2 consecutive. Stop on invalidity, a false-safe crossing, completion
of both executions/four interval scores, or any ceiling. Numerical misses retain
diagnosis-only use; this does not close M5 or authorize screening. The protocol is
sealed **unexecuted**. This diagnostic stage's operational decision is finish/stop
with zero further budget and zero backend authorization.

## Accounting and review

| Resource | Historical cumulative | New stage | Cumulative |
|---|---:|---:|---:|
| Provider attempts | 28 | 7 / 8 | 35 |
| Workflow calls | 55 | 9 / 30 | 64 |
| Full backend attempts | 6 | 0 / 0 | 6 |
| Charged seconds | 3201.913 | 196.171 / 1800 | 3398.084 |
| Additional controller solves | 9 | 0 / 6 | 9 |
| Reduced rollouts | 9 | 6 / 8 | 15 |
| Embedded controller updates | 210 | 0 | 210 |

Exact [receipts/accounting](../evidence/milestone5_diagnostic_20261005/accounting.json)
govern rounding; sums reconcile and no resource is occupied. Workers/subagents
are zero. Offline engineering and export time is separate from receipt-charged
work, following existing conventions.

One model protocol correction and three semantic reviews were used (historical
protocol 6 → cumulative 7; historical semantic 5 → cumulative 8). The first
provider response supplied a correction without an existing draft. Three final
handoff workflow calls failed because the initial @4 tool requires an unexecuted
future batch plan. The existing feedback-bound @3 tool was used in a new linked
context, preserving failed receipts and counters. No future plan was fabricated.
Serializer fact-catalog setup and an old nested-selector reference helper were
repaired offline; partial preparation reused its receipt. An export assertion
expected a different punctuation spelling of the accepted D response and was
repaired without paid/numerical work. No completed calculation was rerun.

Original responses, protocol feedback and semantic reviews are retained. The
[final semantic review](../evidence/milestone5_diagnostic_20261005/final_semantic_review.json)
accepts D/incumbent/stop with scope qualifications: A need not solve every error
to be investigable; missing historical warm plans do not prove generated-history
preview impossible; the varied factor was holding, not terminal, weight. Stronger
model prose is not adopted as a causal finding. The host-frozen future protocol
preserves the earlier exact proposal when the final response shortened it.

Three focused unit tests passed. Saved-data verification checked time/input/state
alignment, vector versus norm identities, coarse reproduction, root residuals,
seed selection, exact incumbent binding, predecessor immutability and receipt
reconciliation. Earlier checks were reused; no broad suite, dependency upgrade,
weight sweep, provider preflight, backend replay, worker or push occurred.
Implementation and delivery are committed locally; exact commits are in Git.
