# Stage 3.25 handoff

Historical evidence is now committed. Offline protocol and factual delivery repairs remain uncommitted. The single numerical candidate and its one revision did not improve update cost; the numerical change was withdrawn. No full tracking confirmation was launched. **Actual provider requests: 0. Actual backend rollouts: 0.** Six local NMPC updates were measured (three baseline, three revised), plus construction/cache preparation and solve-free saved-plan checks. No credentials were read, provider connectivity attempted, dependency upgraded, MATLAB started, or subagent used.

## Historical evidence

Evidence-only commit: `4569782` (full identity in `archive_verification.json`). Branch `feat/gvs-dynamics` started clean at reviewed `5589248b7d95687644e8db360397b90350c4533c`. Nothing was pushed or merged.

The additive [Stage 3.24 index](../stage324_time_reference_tracking_20260928/evidence_index.md) records original paths, sizes and SHA-256 hashes. There are 72 newly recovered historical files plus the new index in the commit; the already tracked implementation report is also indexed. Total original indexed data is about 19.7 MB. The 73 indexed original files remained byte-identical at final verification. The original three SQLite snapshots hold 11, 34 and 141 immutable artifacts; every artifact hash passed and every embedded artifact reference resolved within its Store. This includes raw provider requests/responses, build and analysis artifacts, sealed execution/evaluation/report associations, structured finish, rejection events and continuation records. Session locks were excluded. Authorization anchors were not copied; the evidence can be read without making it executable elsewhere.

All named minimum Stage 3.24 artifacts were found. Full warm-start plans at later control intervals were not retained; that limits performance replay, not historical result verification. Original `model_final.txt`, the false ?zero deadline-nonconforming updates? claim, failed `provider_interpretation_review.json`, first stop, and same-session intervention remain unchanged. The historical live run was assisted and its prose delivery failed. Its 17 provider requests and one live backend attempt are historical counts, not this round's usage.

## Offline repairs and verification

The five actual rejections were `model-1-tool`, `model-8-tool`, `model-9-tool`, `model-10-tool`, and `model-14-tool`. Four placed an extra `reason` inside evidence-read or candidate-analysis arguments; one supplied `combination` for a run of a saved build. These were domain/preflight failures, not malformed outer transport, incorrect evidence-reference shape, or missing candidate identities. The actual raw responses and historical errors were replayed.

Shared argument validation now identifies paths, required/allowed fields, and the outer-reason correction before reservation or execution. Discovery and tool instructions explain the distinction and the run/build combination rule. Existing per-turn repair accounting is retained. At the repair limit, one durable additional argument correction is allowed under unchanged provider/tool/wall/turn limits; it cannot invent arguments or replenish budgets. Failure of that opportunity becomes `needs_input`, not a fabricated final delivery; repeated resume cannot reopen it. Finished deliveries and exhausted authorization cannot resume. A successful correction follows the existing consecutive-repair reset, with the consumed correction flag and all charged usage preserved.

An isolated copied Store replay preserves historical inputs/counters while explicitly migrating only the fixture's dependency snapshot and session state. Its local authority check is bypassed only inside the test; real provider transport and backend simulation are assertion-blocked. All five originals reject without reservation or charge. Corrected argument forms validate; a corrected evidence read runs through the production pending-decision loop and preserves session, candidate, task and budgets. The original Store remains unchanged. This verifies bounded offline behavior, not a new unassisted provider success.

`delivery_facts.py` projects candidate/configuration, execution, evaluation and report bindings; sampled acceptance; maximum/RMS tracking error and limit; update/feasible/converged counts; deadline misses and period; simulated duration and charged measured computation; and real-time status. Report/evaluation execution identities and metrics are checked. Model context, typed `result_statement`, public deterministic rendering and route delivery use this representation. An inconsistent supplied typed claim is rejected; an absent claim is not treated as a pass. Provider reasoning remains separate and its status remains `prose_review_required` for new delivery. Numeric consistency does not validate arbitrary prose.

`deterministic_factual_delivery.{json,md}` and `live_factual_delivery.{json,md}` are new program-generated projections of the archived evidence. They are not replacement historical reports or corrected provider responses. Both show 40 deadline misses and `real_time_demonstrated: false`; the saved negative prose review remains false.

Ten unique focused tests passed: three new offline tests, four Stage 3.24 tracking tests, and three Stage 3.23 delivery tests. The initial combined nine-test run passed in 18.754 s; the two changed shared-path checks subsequently passed in 13.004 s, and the added public deterministic-render check passed in 0.151 s. `verification_results.json` records scope. The first log contains PowerShell's stderr wrapper, but the unittest result is `OK`. No full suite or broad failure matrix was run. The new tests depend only on the committed Stage 3.24 archive; the existing Stage 3.23 tests still require their pre-existing local Stage 3.22 evidence.

## Three saved states and numerical decision

`selected_states.json` freezes existing interval-start samples at 0.00, 0.20 and 0.35 s, their measured coordinate order/state, prior applied tensions, physical environment, robot, frozen task, recipe and absolute time. Both versions receive identical reconstructed seeds: repeated measured-state guesses with constant prior applied tensions. Both regenerate states from measurements. This is not an exact replay of the historical selected warm plans.

The real controller command boundary is timed externally, including prediction diagnostics and observation creation. Production timing now also includes that diagnostic work. One-time construction/cache warming is separate: 10.809 s baseline, 15.667 s revision. Both versions prime the root solver and construct the real IPOPT solver/value cache before measurements; priming does not run numerical optimization. Solver and graph caches persist across the three samples. Relevant physics, 12-coordinate basis, 10-step horizon, discretization, objective/scales, bounds and feasibility tolerances are identical. The feasible-return policy stays at minimum 5 s, budget 15 s, relative improvement 0.1. No policy adjustment was made.

All costs below are seconds. Validation includes recovery validation, so it overlaps recovery and must not be summed blindly with it.

| Version | State time | Complete update | Preparation | Numerical solve | Recovery | Validation | Objective | Scaled violation | Selected source |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Baseline | 0.00 | 39.184 | 11.933 | 16.579 | 10.282 | 0.393 | 62.0773177 | 8.02e-11 | reintegrated_returned_iterate |
| Baseline | 0.20 | 27.682 | 12.318 | 14.941 | 0.000 | 0.293 | 0.0400903054 | 7.09e-06 | ipopt_selected |
| Baseline | 0.35 | 27.537 | 12.297 | 14.854 | 0.000 | 0.254 | 0.0454402485 | 9.38e-07 | ipopt_selected |
| Withdrawn revision | 0.00 | 57.589 | 22.668 | 16.952 | 17.594 | 0.376 | 80.339964 | 3.69e-12 | reintegrated_returned_iterate |
| Withdrawn revision | 0.20 | 57.555 | 23.273 | 17.814 | 16.093 | 0.370 | 0.104596734 | 1.59e-10 | reintegrated_returned_iterate |
| Withdrawn revision | 0.35 | 59.049 | 23.542 | 18.046 | 17.076 | 0.382 | 0.396556626 | 1.83e-10 | reintegrated_returned_iterate |

Baseline preparation is almost entirely implicit root integration: 11.933, 12.317 and 12.296 s. IPOPT constraint-Jacobian evaluations account for 15.847, 13.338 and 13.239 s inside solve. Representative single-step residual evaluations take 0.0125?0.0130 s; all step Jacobians take 0.277?0.299 s. These diagnostic probes run outside the operational update and are not attributed as an exact internal root-solver breakdown; the existing root statistics do not retain usable per-function time counters. The retained per-tail integration times, NLP function timings, initial checks, recovery integration/validation, and full boundary account for the material costs. Residual checks, initial feasibility and controller bookkeeping explain the remaining overhead. Construction is not the main recurring bottleneck.

The first implementation expanded the entire implicit-step MX expression to SX. Construction reached 10,841,075,712 bytes of working set without completing an update and was stopped. The one allowed revision expanded only each mass-sample wrench expression, preserving the existing AD boundaries. It roughly doubled root preparation and individual Jacobian cost (0.542?0.558 s), reduced optimizer progress to one iteration, and required recovery at all three states. Baseline optimizer iteration counts were 4, 3 and 3. All six outcomes are feasible early stops, **not optimizer convergence**.

The revision was slower and its objectives worse at every state. This is sufficient to reject it without repeat measurements, policy tuning or an optional rollout. `withdrawn_sample_sx.patch` preserves the exact measured revision; production dynamics and numerical integration remain unchanged. `numerical_decision.json` retains the aborted first attempt and withdrawal. `baseline.json` and `modified.json` retain detailed results, function timings and selected plans.

`plan_verification.json` independently evaluates all six saved selected plans against the original graph without solving. Every plan satisfies the unchanged `1e-5` feasibility threshold; objective differences are zero. No full tracking result is inferred from these three states. Historical baseline max/RMS tracking errors remain 0.005772548837294318 / 0.004412616885360754 m; there is no new rollout metric, speedup claim, convergence claim or real-time demonstration.

## PowerShell reproduction

From `D:\softrobot-agent`, use the installed interpreter and single-thread settings. These commands are offline; none sends a provider request or runs a backend rollout.

```powershell
$softPython = 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe'
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
& $softPython -m unittest tests.test_stage325_efficiency tests.test_stage324_tracking -v
# Existing local Stage 3.22 evidence is needed for this legacy test module:
& $softPython -m unittest tests.test_stage323_delivery_repair -v
& $softPython examples/gvs_update_comparison.py verify --output runs/stage325_tracking_efficiency_20260928
& $softPython runs/stage325_tracking_efficiency_20260928/render_saved_facts.py --output runs/stage325_facts_reproduce
```

To reproduce the measured comparison, choose a fresh output directory. The withdrawn patch is experimental and is reversed afterward. This repeats only six local updates; it does not authorize a full rollout.

```powershell
$comparisonOutput = 'runs/stage325_comparison_reproduce'
& $softPython examples/gvs_update_comparison.py freeze --output $comparisonOutput
& $softPython examples/gvs_update_comparison.py baseline --output $comparisonOutput
git apply --check runs/stage325_tracking_efficiency_20260928/withdrawn_sample_sx.patch
git apply runs/stage325_tracking_efficiency_20260928/withdrawn_sample_sx.patch
try {
    & $softPython examples/gvs_update_comparison.py modified --output $comparisonOutput
} finally {
    git apply -R runs/stage325_tracking_efficiency_20260928/withdrawn_sample_sx.patch
}
& $softPython examples/gvs_update_comparison.py verify --output $comparisonOutput
```

The current uncommitted files contain the offline repairs, rendering integration, complete-timing correction, comparison helper and focused tests. Stage 3.25 working outputs remain under the repository's ignored-runs policy. No new full rollout was justified; no live LLM regression, paid review, old reaching rerun, design search or additional numerical exploration was performed.
