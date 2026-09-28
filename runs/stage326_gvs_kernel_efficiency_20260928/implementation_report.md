# Stage 3.26: GVS kernel efficiency

**Retained:** common-subexpression elimination (CSE) in the existing MX force-balance function and generated derivatives. Three paired saved cases passed the predeclared cost/quality rule; the one authorized deterministic confirmation passed the frozen 10 mm task. This is an offline computational improvement, not real-time control or optimizer convergence.

Stage 3.25 was closed first in local commit `1b4c00f`: protocol/factual-delivery repairs, focused tests, ten-test historical verification, five original rejection/replay records, three-state negative numerical evidence, withdrawn SX patch, and an additive LF/CRLF archive clarification. No maintenance tests were rerun because review found no subsequent relevant repair edits. The historical Stage 3.22 failed delivery, Stage 3.23 successful delivery-only review, Stage 3.24 tracking success with failed prose, and Stage 3.25 withdrawn method remain distinct and unchanged.

## Frozen comparison and selected computation

`frozen_comparison.json` records the pre-result acceptance rule and an immutable reference to Stage 3.25 selected_states.json, committed in `1b4c00f`. No second copy of that input or the historical databases is needed. Measured state, serial-state projection, previous tensions, reconstructed warm input, absolute reference time, robot, physical parameters, basis/order, integration, horizon, weights, force limits, tolerances and solver stopping options match pairwise. The warm plan is reconstructed from repeated measured states and constant previous tensions; unavailable original optimizer warm plans were not reproduced. Raw serial states come from the committed trajectory at each interval start (the initial scene supplies t=0); projection reproduces saved q/qdot exactly in all six cases.

The interpreter and packages match Stage 3.25; all three numerical thread variables are 1. No dependency upgrades, provider credentials, MATLAB, GPU work, compiler installation, or subagents were used. The compiler availability check found none in PATH or checked standard locations; no compilation was attempted.

Prior profiling identified implicit root integration (about 12 s warm preparation) and constraint Jacobians (about 13-16 s inside IPOPT). Residual probes were about 13 ms versus 283-297 ms for all Jacobians. Root statistics did not expose usable internal per-function timing, so no invented residual/Jacobian/Newton/linear-solve split is reported. Existing per-tail integration times and NLP function statistics sufficiently identify the recurring cost. No broad profiler catalogue was collected.

One targeted graph probe showed that sample wrench functions actually inline into the surviving force-balance function: CSE reduced it from 127,449 to 31,889 MX nodes, taking 0.326 s for that diagnostic transformation. The initial idea of applying CSE at sample boundaries was refined before the numerical edit to this surviving boundary. The final five-line change enables `cse=True` and derivative `cse=True` in `gvs_force_balance`. It shares repeated kinematics and derivative expressions while retaining all equations and AD semantics. It does not expand MX to SX, repeat the withdrawn Stage 3.25 method, add new graph/solver caching, or introduce the already existing reverse constraint-Jacobian mode. There was one implementation direction and zero numerical corrections.

At the three baseline plan points, residual outputs match exactly; maximum absolute Jacobian difference is 2.132e-14 (limits declared beforehand: residual rtol/atol 1e-10, Jacobian rtol/atol 1e-9). Revised residual probes are about 4-5 ms and Jacobians about 74 ms. These probes are outside the operational timers. `baseline_kernel.json` originally searched for sample boundaries and therefore has an empty node list; `cse_graph_probe.json` records the surviving original boundary, and `modified_kernel.json` records the retained node count.

## Complete local updates

Acceptance was fixed before revised results: total revised time <=85% of baseline total; no case >105% of its baseline; no objective increase beyond max(1e-8, 1% of baseline objective); every independently checked plan <=1e-5 scaled violation. The feasible-return minimum 5 s, budget 15 s and relative improvement 0.1 are unchanged. Objectives are compared only within each case.

Each variant ran once in a fresh process with one persistent workspace/solver across the three cases. Setup primes one implicit integration and constructs the real IPOPT/value cache without an NLP solve. The outer timer starts before serial-state projection and ends after command return, covering preparation, solve, recovery, validation, ideal command conversion, prediction diagnostics and observation construction. Loading archived inputs, copying the test fixture, and graph/cache construction are outside. Saved tip geometry is supplied as measured input. The old Stage 3.24 controller timer ended before prediction/observation work; Stage 3.25 included that work but excluded projection. These fresh pairs use the same outer scope.

| State, s | Baseline update, s | CSE update, s | Speedup | Initial objective B / CSE | Delivered objective B / CSE | Original-graph violation B / CSE |
|---:|---:|---:|---:|---:|---:|---:|
| 0.00 | 40.783 | 22.103 | 1.85x | 173.118435 / 173.118435 | 62.0773177 / 1.16242733 | 8.02e-11 / 3.69e-12 |
| 0.20 | 28.376 | 10.512 | 2.70x | 0.313958319 / 0.313958319 | 0.0400903054 / 0.0240970168 | 7.09e-06 / 2.12e-11 |
| 0.35 | 28.439 | 10.403 | 2.73x | 0.695650487 / 0.695650487 | 0.0454402485 / 0.0328686454 | 9.38e-07 / 7.49e-12 |

| Variant / state | Projection | Warm preparation | IPOPT solve | Recovery | Validation* | Iterations | Plan source |
|---|---:|---:|---:|---:|---:|---:|---|
| Baseline / 0.00 | 0.0014 | 12.505 | 17.087 | 10.762 | 0.396 | 4 | reintegrated_returned_iterate |
| Baseline / 0.20 | 0.0015 | 12.906 | 15.081 | 0.000 | 0.254 | 3 | ipopt_selected |
| Baseline / 0.35 | 0.0015 | 12.735 | 15.295 | 0.000 | 0.263 | 3 | ipopt_selected |
| CSE / 0.00 | 0.0013 | 3.274 | 15.989 | 2.706 | 0.131 | 17 | reintegrated_returned_iterate |
| CSE / 0.20 | 0.0025 | 3.346 | 5.245 | 1.740 | 0.175 | 4 | reintegrated_returned_iterate |
| CSE / 0.35 | 0.0014 | 3.404 | 5.065 | 1.756 | 0.176 | 4 | reintegrated_returned_iterate |

*Validation includes recovery validation and overlaps recovery; columns must not be blindly summed. Every local plan was accepted as `feasible_early_stop`, with raw `User_Requested_Stop`, success/convergence false. Revised cases all selected reintegrated returned iterates; the baseline only used recovery at t=0. More iterations at t=0 and earlier improvement-policy stops later explain changed delivered objectives under the identical wall-time policy.

Total update time fell by 55.92% (97.599 to 43.018 s). All three cost/quality comparisons passed. Fresh baseline timings were 2.5-4.1% above the historical Stage 3.25 baseline, a contextual indication of timing variation rather than a formal variance estimate; the improvement is much larger. No repeat pair was warranted.

Comparable setup/cache warming was 11.100 s baseline and 12.102 s revised. The approximately 1.002 s added setup was amortized within the first update (18.681 s saved). No native compilation cost exists. The separate kernel-check construction probes are diagnostic and not added to recurring update cost.

All six selected plans were independently reevaluated with the original production graph, temporarily reversing only numerical_change.patch and restoring it afterward. All feasibility checks passed and objective discrepancies were zero. No recovery, root solve or NLP solve was run by this independent value-only check.

## One public tracking confirmation

The clear local benefit authorized exactly one confirmation through examples/gvs_tracking.py -> simulation.run -> evaluation.run -> control.profile_report. A fresh session changes only run_id; the frozen task, robot and complete policy are exactly equal as JSON values. The deterministic public entry has no Route owned-build analysis prerequisite; none was bypassed and no unrelated historical analysis was substituted. Current numerical preparation, candidate/configuration, frozen reference, execution, evaluation and report bindings are checked in confirmation_audit.json and resolve in the new Store. The existing public candidate label remains `parameterized-reach` although its task is tracking.

Execution `67f8d7f01c514dc2bab4085eb008630b` completed all 40 expected samples over [0.01,0.40] s. Maximum / RMS / terminal position error: 7.705287 / 2.729176 / 1.382349 mm. **Frozen 10 mm acceptance passed.** All 40 plans were independently feasible; max scaled residual 5.76926e-06. Tendon range 1.428715-5.105889 N, with zero sampled bound violation. Accepted plans 40, converged 0, holds 0, solver errors/failure flags 0, deadline misses 40/40. All stops were feasible early stops / User_Requested_Stop; three plans used recovery.

Mean complete update 8.992280 s; minimum 7.681843, maximum 31.504374, sum 359.691208 s. Charged simulation wall 363.781000 s; backend call 360.316727 s. Mean warm preparation 2.725793, solve 5.855387, recovery 0.156610, overlapping validation 0.097776 s. The backend outer timer now also includes current measurement/geometry and projection (mean 0.001602 s); disk evidence serialization remains in total backend cost. Graph construction is charged outside the recurring update and initial solver construction remains in the first cold update. No claim of meeting the 0.01 s period is made.

All 40 one-step predictions align with the measured endpoint and applied interval tension (command discrepancy 0). Maximum / RMS position prediction discrepancy 1.117982 / 0.806153 mm. This is prediction/execution disagreement, not an identified physical cause. Historical deterministic maximum was 2.26 mm; new maximum is 1.12 mm. Historical full-run maximum tracking error was 5.77 mm versus new 7.71 mm, while RMS and terminal errors improved: the accepted task is preserved, but peak tracking error did not improve. The full-run trajectory and warm inputs evolve differently, so historical/full-run means are not a second paired saved-state benchmark.

Production independent plan checks cover all 40 updates. The public backend does not export full-horizon plans, so there is no claim of a separate original-graph replay of all 40; the original-graph cross-check covers the six retained benchmark plans.

## Verification, usage and next round

Focused verification consists of three residual/AD equivalence cases, six original-graph plan value checks, exact serial projection and solver-option equality checks, and the one full public confirmation with an independent archive audit. Existing maintenance test outcomes remain in the Stage 3.25 commit. No new whole-suite run or LLM regression was needed. Source diff whitespace checks passed (the preserved historical patch has intentional patch-context whitespace).

Actual usage this round: **0 provider requests; 1 full backend rollout; 6 local saved-state IPOPT optimization solves, plus 40 controller optimization updates within that rollout.** There were also two untimed root priming integrations and solve-free kernel/graph/plan checks. Stage 3.25 original six local solves and ten tests are archived historical observations, not work repeated this round. No push was performed.

Next round: extend the accepted deterministic task to a predeclared multi-segment reference. Current evidence supports lower computational cost and sampled tracking acceptance; the 1.12 mm prediction discrepancy does not establish a prediction-consistency limitation requiring a new physical model. Do not infer robustness, continuous-time accuracy, real-time performance, or arbitrary provider-prose correctness.

## Exact PowerShell commands

From D:\softrobot-agent, the executed fresh measurements were:

```powershell
$softPython = 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe'
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
$out = 'runs/stage326_gvs_kernel_efficiency_20260928'
$selection = 'runs/stage325_tracking_efficiency_20260928/selected_states.json'
& $softPython examples/gvs_update_comparison.py baseline --output $out --selection $selection --project-saved-state
& $softPython "$out/kernel_check.py" baseline
# Apply the retained CSE change (numerical_change.patch), then:
& $softPython "$out/kernel_check.py" modified
& $softPython examples/gvs_update_comparison.py modified --output $out --selection $selection --project-saved-state
git apply -R "$out/numerical_change.patch"
try {
    & $softPython examples/gvs_update_comparison.py verify --output $out --selection $selection
} finally { git apply "$out/numerical_change.patch" }
# confirmation_input.json changes only run_id from the original frozen input:
& $softPython examples/gvs_tracking.py run --input "$out/confirmation_input.json" --output "$out/confirmation"
& $softPython "$out/audit_confirmation.py"
```

These output locations are now finished evidence and must not be resumed or overwritten. For another local reproduction, reproduction.ps1 creates a fresh directory and safely selects/restores the original/CSE graph; it performs six local NLP solves and no rollout. Any future full reproduction needs a fresh run_id, grant and directory and is outside this completed one-rollout round. Raw script operations used to freeze the new input were `value=json.loads(original.read_text()); value["run_id"]="gvs-stage326-confirmation-20260928"; output.write_text(json.dumps(value,indent=2)+"\n")`; no task or policy fields changed.
