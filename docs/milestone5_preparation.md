# Milestone 5 two-capability preparation and development, 2026-10-05

The authorized local work is **completed and stopped**, with the required
new-stage research-model handoff blocked. Both prediction interfaces, independent
candidate histories and the two sealing points are implemented. Two exact saved
states and a concrete provisional recipe pair are registered. The protocol is
**not ready for prospective execution**, and no future forecasts, backend steps,
replays or simulations ran. The configured research model has not selected the
pair for this new protocol or interpreted these results: automatic approval
review rejected that external handoff. Engineering assessments are labeled as
such and do not replace a model response.

The incumbent remains `batch-ebbeadbdaca10732-0`, execution
`91c3ba1b01d6499fb26df8f95409401b`: near/far .16/.11 m, section scale .95,
compliant material, holding/terminal .05/.05 and `controller.gvs_nmpc@7.0.0`.
Milestones 2–4 remain closed; Milestone 5 remains open. The starting branch was
clean `feat/gvs-dynamics` at `0989982`; no reset, push, dependency upgrade,
MATLAB validation, controller-family expansion, worker or subagent occurred.

See [delivery](../evidence/milestone5_preparation_20261005/delivery.json),
[registered protocol](../evidence/milestone5_preparation_20261005/protocol.json),
[reference results](../evidence/milestone5_preparation_20261005/reference.json),
[preview summary](../evidence/milestone5_preparation_20261005/preview_summary.json),
[readiness](../evidence/milestone5_preparation_20261005/readiness.json), and
[exact receipts/accounting](../evidence/milestone5_preparation_20261005/accounting.json).
All predecessor evidence, usage and saved session states were checked unchanged.

## Capability definitions and acceptance

Local diagnostic prediction starts at an observed checkpoint, uses only the
current state and causally available input, and predicts the declared subsequent
.01 s interval. It reports world velocity vectors, speed norms, changes,
neutral/indeterminate directions, position/vector/speed errors, resolution
uncertainty and threshold crossings. Supported use remains directional diagnosis
under test; quantitative endpoint accuracy and constraint reliability are unmet.

Pre-execution screening starts before either backend evaluation and independently
generates each candidate's state, input and selected-plan history over .0–.35 s,
including approach and the full .30–.35 s holding window. It reports ranking or
abstention, eligibility, resolved coverage, conditional accuracy, ordering errors,
false rejection, false-safe predictions and cost. Universal abstention does not
establish usefulness. Different histories alone do not establish predictive value.

The existing requirements are preserved: terminal and holding position .01 m,
holding speed .02 m/s, numerical speed and velocity-vector reporting tolerance
`1e-4 m/s`, complete sampled holding coverage, physical feasibility, useful
prospective discrimination/order, broader repeatability and the existing .01 s
real-time deadline. The .005 m settled-seed check is a controller shortcut,
separate from the .01 m physical task threshold. No gate is lowered or closed.

The new protocol adds explicit causal inputs, two complete forecasts sealed
together, full own-history coverage, neutral/uncertainty rules, rejection and
false-safe scoring, and separate implementation/numerical/screening/physical
readiness. These interfaces and budgets can be used by single-model or dual-model
orchestration. Their comparison was not launched.

## Registered states and provisional future recipes

Both scenarios use the incumbent's exact manifest
`785e2d9c957be8df82700d6b5f64eb99900fd020f82d4aa19344716acba7566d`, XML
`f8eacffa3163e99f9a689e42a95a39237f35145f2357906c0d68d58656cd2cc7`, and
trajectory `b9647aec551f9819094e13e0c68ff8cc2e7854285bca6d10fc077a76c58f5446`.
The complete robot/task/configurations, named states, projection, previous-input
provenance, artifact references and full new-episode integration-state vectors
are in [registration](../evidence/milestone5_preparation_20261005/registration.json).

| Scenario | Historical source | New task/controller/backend origin | Full reset-state identity |
|---|---|---|---|
| `incumbent_checkpoint_20_new_clock` | trajectory `/19`, .20 s | 0 s | `fff0981cbaf0f7a5ccff40ac729c2578f4dfb37ce445f665b3d6a086070f5516` |
| `incumbent_checkpoint_30_new_clock` | trajectory `/29`, .30 s | 0 s | `6fe6f789745a57704375606c694edb5872a7137a10b466b5b4fdd71b47e612eb` |

`initialize.family` restores all 48 named positions and velocities into a fresh
MuJoCo episode. Activation and mocap dimensions are zero. Time, control, applied
forces and integrator caches reset through fresh `MjData`; the new task references
and holding window use the new zero origin. Each 373-value
`mjSTATE_INTEGRATION` vector was captured and round-tripped with `mj_setState`
and kinematics only, with zero advancement. These are reproducible new episodes
initialized from historical coordinates, **not exact historical integrator
continuations**. Original integrator caches and historical warm plans were not
retained; none was invented.

The source episode's last applied tension is preserved as historical evidence.
The new controller instead uses its production `reach_numerical` bundled-guess
initial input and historical initial tension guesses, with placeholder states
regenerated using the candidate model. It resets observations, last-plan history
and unusable-update count. The new previous input is
`[1.7512764858409064,4.755852667139922,3.1031566686630025,3.218253612486097,0.7859357597552847,0.6315302379791942] N`.

The provisional recipes are holding **.075 and .15**, terminal .05, with identical
structure, material, limits, task thresholds and other solver settings. These are
historical numerical weights, inherited from the predecessor model selection;
the new saved-checkpoint/reset-task combinations have not been evaluated. They
permit a matched test of whether distinct generated histories predict the prior
acceptance contrast in new scenarios. The compact accepted candidate inventory
was read once. A new-stage model selection/justification is still required: the
provisional registration is not represented as a new accepted model choice.
Both candidates share the same initial condition within each batch.

## Bounded local numerical reference

The predecessor's six .01/.002/.001 s comparisons were reused, not repeated.
Six new standalone implicit-Euler integrations used .0005/.00025/.000125 s
steps for the two known .30–.31 s intervals. Initial reduced state, held recorded
input, model, endpoints and world-frame definitions were fixed. Saved
`actual_tension_n` is the direct applied tension after interval-start `mj_forward`
and before `mj_step`; it is not a subsequently measured interval average.
Requested and applied tensions match in the saved ideal-tension executions.

| Quantity | Historical .075 | Historical .15 |
|---|---:|---:|
| .0005 s endpoint speed, m/s | .018718163791 | .006987403844 |
| .00025 s endpoint speed, m/s | .018773504590 | .007021723724 |
| .000125 s endpoint speed, m/s | .018801500957 | .007039088535 |
| Last speed-resolution difference, m/s | .000027996367 | .000017364812 |
| Last vector-resolution difference norm, m/s | .000033443864 | .000023907661 |
| Last position-resolution difference norm, m | .000001539521 | .000000877496 |
| Finest speed error vs backend, m/s | -.004484446553 | -.003984043586 |
| Finest vector error norm vs backend, m/s | .006823541689 | .007304574737 |
| Largest scaled root residual | 1.19035e-12 | 1.80596e-12 |

Both successive refinement pairs are below `1e-4 m/s` for scalar and vector
differences, supporting a local numerical reference at that reporting resolution.
The final differences are measured resolution uncertainty, not a proven bound.
The endpoints, full vectors, positions, step counts, residuals and individual
costs are exported. The reference receipt charged 74.016 s including construction
and export overhead.

Backend agreement remains poor. The .075 endpoint remains false-safe. The .15
speed norm improves, while vector agreement worsens further. No material fit,
scalar correction or unique omitted-physics attribution was introduced. The one
focused local improvement is `local_fixed_command@2.0.0`, isolated from production:
.000125 s integration with a causal .00025 s resolution comparison at each future
checkpoint. This improves numerical reporting, not demonstrated physical accuracy.

## Complete generated-history development previews

`candidate_history@1.0.0` uses `TrajectoryWorkspace` with production feasibility,
force limits, warm-plan shifting, deadline horizon truncation, settled-seed
acceptance and unusable-update stopping. Each candidate owns its reduced state,
previous command and selected plan. It propagates the same implicit model with
bounded direct tension, then updates its own history. It never reads future
backend observations, realized future inputs or another candidate's plan.
Reduced dynamics approximate full-order backend dynamics; the ideal force mapping
does not establish equivalence to a real actuator. Production defaults are unchanged.

Development used the original historical initial condition and the historical
.075/.15 recipes, **not either new scenario**. Saved timing and the actual 35-update
grid admitted 70 solves, with 1200 s per preview and 660 s protected finalization.
All 35 updates completed in each preview; each embedded solve was charged even
when iteration zero was selected. Internal warm integration and independent
propagation telemetry are exported within the outer receipt, without duplicate
wall-time charges.

| Metric | .075 preview | .15 preview |
|---|---:|---:|
| Holding max speed, m/s | .008689043741 | .008686385372 |
| Holding max error, m | .000531789330 | .000530767053 |
| Terminal error, m | .000531789330 | .000530767053 |
| Controller attempts | 35 | 35 |
| Iteration-zero selections | 21 | 21 |
| Settled-seed stops | 16 | 16 |

First commands match; first weight-dependent command divergence occurs at update
20 (.20 s). The full histories differ, but their holding-speed gap is only
`2.658369128e-6 m/s`, so the unchanged `1e-4` rule abstains. Actual historical
holding speeds are .023285947510/.012939198456 m/s; their order resolves in favor
of .15, while predicted ordering is unresolved. Both previews predict safe
eligibility; .075 is false-safe. Coverage for resolved ranking is 0/1 and
conditional accuracy is undefined; no rejection means zero hypothetical savings.
Eligibility resolves for 2/2 candidates but is correct for only 1/2; the .075
false-safe classification prevents a useful constraint-screening claim.
These are retrospective development scores, not new prospective validation.

Preview calculation cost totals 694.427 s, exceeding the saved pair's complete
evaluation cost of 605.937 s. This implementation shows candidate independence
and coverage, but neither useful discrimination nor a cost advantage here.

## Seals, future batches and budgets

The pre-execution seal binds both complete forecasts, scenario/configuration,
predictor/controller versions, interval and frozen ranking rules in one immutable
Store artifact/event before either `complete-simulation` reservation. Revision
after either backend starts is rejected. The primary objective is minimum sampled
holding max speed, conditional on predicted terminal/holding position feasibility;
tie margin is `1e-4 m/s`. Missing, nonfinite, infeasible, partial or position-invalid
histories abstain. No empirical safety allowance is imposed or claimed.

The existing `PRE_STEP_OBSERVER` captures .20 and .30 s states and the currently
available bounded command. It seals .20–.21 and .30–.31 predictions before the
next advance. Current direct force is checked against the command; no subsequent
input measurement is used. The independent numerical calculation cannot alter
the production decision. It has separate telemetry inside the backend receipt;
its overhead does not demonstrate real-time operation. Nonholding threshold
diagnosis is distinguished from physical holding acceptance at .30 s.

Both candidates receive complete evaluation, including a hypothetically rejected
candidate. Both capabilities are scored separately in those same evaluations.
Batch 2 uses the unchanged method and recipes after Batch 1. Invalidity,
implementation defects, incomplete execution, resource shortfall, numerical
instability or a false-safe holding/eligibility result stops continuation after
both Batch 1 evaluations. Tuning after Batch 1 reclassifies it as development for
the changed method. Two pairs establish neither statistical reliability nor
family-wide generalization. Actual validation savings are zero.

Current `tools/batch_budget.py` and `EXECUTION_ALLOWANCES` are unchanged.

| Reservation | Completed development ceiling | Future Batch 1 | Future Batch 2 |
|---|---:|---:|---:|
| Provider attempts | 8 | 4 | 4 |
| Workflow calls | 40 | 16 | 16 |
| Backend attempts | 0 | 2 | 2 |
| Controller-attempt ceiling | 80 | 140 | 140 |
| Preview attempts | 2 | 2 | 2 |
| Standalone reference integrations | 8 | 0 | 0 |
| Charged wall ceiling, s | 3600 | 6000 | 6000 |
| Minimum complete reservation, s | See admission/receipts | 5830 | 5830 |

Each future floor is `2*(900+30+60+5)+600=2590 s`, plus 3000 s for two
previews, 180 s protected local-checkpoint overhead and 60 s export: **5830 s**.
Actual nested local work is charged only inside simulation, not again. Its
reservation protects incremental overhead; the public 900 s simulation timeout
remains fixed. Two batches reserve interpretation separately: the four-evaluation
public floor is **5180 s**, not the single-interpretation illustrative 4580 s.

The future nominal call sequence has **zero planning requests** (plan frozen in
development), **one interpretation request**, and **three protected correction or
length-recovery slots**: a ceiling of **four**, not four plus an implicit fifth.
Public interpretation reserves four workflow calls too. Eight execution/preparation
calls plus those four, two previews and two assessment/export allowances give 16.
Future protocol corrections are at most three total and two consecutive. Required
export is protected even when a request fails; receipt recovery reuses completed
calculations and evaluations and does not replay unresolved attempts.

## Readiness, unexecuted commands and accounting

Six focused checks passed, including actual Store schema compatibility. They
cover history independence, state/input/time alignment, causal inputs, atomic pair
sealing, local sealing before advance, abstention/false-safe scoring and completed
receipt reuse. Static readiness checks passed concrete registration, controller,
grid, numerical-reference and public-budget checks; required new-stage model pair
selection failed. No check generated prospective numerical forecasts.

Implementation and concrete registration are complete. Local numerical stability
is established within the stated development scope. Physical endpoint accuracy,
useful screening discrimination and screening cost advantage are unmet. Future
reservation arithmetic fits the proposed 6000 s grant per batch, but neither
future grant exists or is authorized. The protocol is **not ready**, primarily
because the required research handoff was blocked; scientific usefulness also
remains unestablished. The runner rejects execution before forecasts/backend work
while that prerequisite is unresolved.

```powershell
$env:SOFTAGENT_CONFIGURATION_PATH = Join-Path $HOME '.codex\.env'
& 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe' examples/milestone5_future_validation.py --check
# Prepared only; do not run without a model-reviewed protocol and separate grant:
& 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe' examples/milestone5_future_validation.py --batch 1 --execute --grant evidence/milestone5_preparation_20261005/future_batch1_grant.json
& 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe' examples/milestone5_future_validation.py --batch 2 --execute --grant evidence/milestone5_preparation_20261005/future_batch2_grant.json
```

Grant files must bind the final protocol identity, exact batch, explicit future
backend authorization and interpretation-transmission authorization, grant ID,
authorization source and budget. Their absence is deliberate. Current preparation
authorizes none of those backend executions. Completion stops each future batch;
Batch 2 is a separate authorized command governed by the frozen continuation rule.

| Resource | Historical cumulative | New stage | Cumulative |
|---|---:|---:|---:|
| Provider attempts | 35 | 1 failed transport | 36 |
| Workflow calls | 64 | 3 | 67 |
| Backend attempts | 6 | 0 | 6 |
| Charged seconds | 3398.084 | 772.984 | 4171.068 |
| Additional controller attempts | 9 | 70 | 79 |
| Standalone reduced integrations | 15 | 6 | 21 |
| Backend controller updates | 210 | 0 | 210 |

Receipt sums reconcile; no resources are occupied. Preview solves are the same
70 controller attempts and are not added again. Offline engineering, tests and
export follow the predecessor convention and remain separate from charged work.
New model protocol/semantic corrections are zero; historical totals remain 7/8.

The first provider attempt failed through the sandbox's `127.0.0.1:9` proxy and
charged 2.031 s. The escalation was rejected before process start, with zero
additional provider charge. Its stated reason was lack of trusted authorization
for the specific external project payload and destination. No proxy workaround
or indirect transmission was attempted. A direct approval question remains pending.
Credentials were loaded only for authentication and were not printed or exported;
the endpoint, `deepseek-flash`, high reasoning, context/token limits, TLS and
transport were preserved.

Other engineering interventions are recorded: use trajectory `tension_n` instead
of a nonexistent `actual_tension_n` field; populate the existing native adapter's
required context fields; retain unused zero-cost sessions and create compatible
sessions after registering tools; correct the seal SQL to the existing calls-table
request identity; extract inventory weights from exact configuration references
instead of result facts and compact the captured inventory without rediscovery.
The original failed provider payload remains preserved. The sandbox blocked a
temporary SQLite test fixture; the same
focused checks passed with normal filesystem access and no network/backend work.
All completed calculations were reused during final export. The final operational
action is **finish/stop**, with no future backend launch or automatic promotion.
