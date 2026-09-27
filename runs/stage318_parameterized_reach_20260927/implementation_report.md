# Stage 3.18: parameterized reach and bounded cost investigation

Based on clean `feat/gvs-dynamics` at `58aa9eb`. Implementation commits: `8365356`, `6b0105c`, `dd7ea7e`. The two executions use `6b0105c`; the last correction changes source archiving only. One agent; no paid model requests, full-suite run, target sweep or changes to historical artifacts. The attached Stage 3.18 request is the active assignment; the older Stage 3.12–NMPC IDE selection is completed background.

## Delivered public path

`controller.gvs_nmpc@3.0.0` / `family.gvs_reach_control` accept task-owned targets, small named initial states and timing, plus explicit recipe and sampled settling. The v2 fixed asset and strict identity check remain unchanged. Registry, candidate builder, existing budgeted preparation hook, Host/Route execution and sealed reporting are reused. There is no second execution architecture.

Technical compatibility/model-use assessment, historical performance coverage, preparation state, and authorization/budgets are separate. Both fresh v3 inputs are initially unvalidated configurations. Old numerical values are compatible guesses with original target/provenance, never a newly solved target equilibrium or new success evidence. A cold initial-state/pretension guess is also available; its preparation was checked, but no full cold-start control experiment was added.

The same robot, materials, free-space scene, mount/gravity, 12-cell execution model and GVS basis remain fixed. Named initial perturbations are bounded by 0.05 rad and 0.5 rad/s. Each execution owns mutable workspace/solver state; current target enters its graph, current measurements enter equality constraints and full warm regeneration. Explicit source identity/order/units/bounds checks remain.

Internal seed acceptance defaults to half the task tolerance and 0.02 m/s, recorded in the recipe. Final sampled settling independently uses its frozen window/position/speed settings. Neither changes the authoritative reach evaluator.

## Fixed three-state cost experiment

Measured states and prior actual tensions are from the sealed Stage 3.17 MuJoCo execution at 0, 0.15 and 0.34 s. Original complete MuJoCo optimization plans were not exported. Both benchmark variants therefore use the SAME explicitly identified bundled initial seed and corresponding saved Stage 3.15 GVS plans as later guesses. This is a controlled solver-cost comparison, not a reconstruction of historical per-update timing. `fixed_inputs.json` freezes all inputs and source references. One sample per state/variant; single-threaded environment in `verification.json`.

The candidate eliminated implicit Euler’s linear position equality and solved only for next velocity, retaining the force residual, tolerance, measured feedback and independent plan validation. No gain/solver budget, force/dynamics constraint or task criterion changed.

| State | Baseline preparation / solve / validation / full (s) | Candidate preparation / solve / validation / full (s) | Selected objective before / after | Scaled violation before / after |
|---|---:|---:|---:|---:|
| start | 7.599 / 16.318 / 0.280 / 28.342 | 7.618 / 15.911 / 0.253 / 27.880 | 37.5930619 / 37.5930619 | 2.84e-14 / 2.54e-14 |
| near_target | 12.252 / 11.701 / 0.260 / 24.347 | 12.086 / 11.681 / 0.249 / 24.146 | 0.124092173 / 0.124092173 | 7.43e-06 / 7.43e-06 |
| final_hold | 12.154 / 11.905 / 0.254 / 24.443 | 11.983 / 11.824 / 0.250 / 24.188 | 0.0599680901 / 0.0599680901 | 7.54e-06 / 7.54e-06 |

Graph construction: 1.360 / 1.368 s; first solver construction: 4.016 / 3.969 s (included in full first update). Later solver objects are reused. Initial plan checks are separately recorded in JSON. Historical point/guess loading incurred no new inverse solve; its load time was not separately timed in this microbenchmark. Actual public import/generation time is recorded below.

Total delivery changed by -1.19%; a single sample with this small difference does not establish a benefit. The candidate was REJECTED and removed from production; `rejected_velocity.py` preserves only the reproducible experiment. Production retains the original Newton method. No full-update cost reduction or ten-second target is claimed. The remaining measured costs are warm regeneration and nonlinear solving, not validation. No broader optimization campaign followed.

## Two new backend experiments

Both use a straight initial state, 0.35 s authoritative task, 0.01 s control period, 0.0005 s physics step, original 10 mm reach tolerance and 12 cells/segment. Predictions use 10 intervals with the original recipe and ideal bounded tensions. Final sampled acceptance is the last 0.05 s, <=10 mm error and <=0.02 m/s speed. A and B run sequentially in separate fresh Python processes, without competing numerical benchmarks.

A uses `[0.29, 0.035, 0.19]` m. B changes only target to `[0.29, 0.05, 0.19]` m. The +15 mm world-y offset was frozen before execution; the historical endpoint would miss it by 12.596853 mm. The target was not searched or changed after results.

| Result | A: original target | B: neighboring target |
|---|---:|---:|
| Complete execution | True | True |
| Official reach success | True | False |
| Terminal error (mm) | 8.47343 | 13.2125 |
| Minimum sampled error (m) | 0.00419419 | 0.00622257 |
| Maximum projection residual (rad/m) | 2.47221 | 1.73611 |
| Accepted plans | 35 | 35 |
| Converged updates | 0 | 0 |
| Initialization selections | 7 | 35 |
| Solver errors | 0 | 0 |
| Hold-last responses | 0 | 0 |
| Maximum scaled plan violation | 9.23575e-06 | 1.58157e-10 |
| Mean full update (s) | 24.428 | 26.6706 |
| Mean warm preparation (s) | 9.33392 | 9.39985 |
| Mean numerical solve (s) | 14.5941 | 16.7721 |
| Mean independent validation (s) | 0.256314 | 0.255809 |
| Graph construction (s) | 1.27438 | 1.27666 |
| Total solver construction (s) | 3.93147 | 3.95306 |
| Simulation tool charged wall (s) | 859.406 | 937.875 |
| Deadline misses | 35 | 35 |
| Tension range (N) | [0.5662001386742109, 5.025997143201603] | [0.6315302379791942, 4.755852667139922] |
| Force-bound violation (N) | 0 | 0 |
| Sampled settling passed | False | False |
| Window max error (m) | 0.008694221274361258 | 0.013212549687364744 |
| Window max speed (m/s) | 0.03156205037834025 | 0.2071474222228893 |

Numerical preparation (included in tool wall): A 0.021861 s, B 0.021877 s. Both explicitly reused historical guesses, without a new inverse solve. Full update includes warm preparation, first solver construction, initial feasibility checks, numerical solving, independent validation and command processing; graph creation occurs before updates. Solver construction totals are not additional costs to add again to full-update time.

Historical Stage 3.17 (NOT a new run): terminal error 8.473431 mm; mean full delivery 24.977007 s. New A mean is 24.428019 s. Because no performance candidate was retained and early-stop timing is wall-budget dependent, differences between complete runs are not evidence of a speedup.

B failure diagnosis: the frozen target reaches the built control graph and numerical preparation completes. All 35 updates regenerate prediction states from actual measurements, but all 35 select initialization rather than a later optimization iterate. The applied command sequence differs from the shifted historical seed by at most 0 N. Thus this run demonstrates no effective optimized command adaptation to the new target. It reaches a minimum sampled error of 6.223 mm at 0.28 s, then leaves the tolerance by the authoritative endpoint (terminal speed 0.203473 m/s). This is a control/plan-quality limitation under the declared recipe, not an interface rejection, missing numerical preparation, solver exception or hold-last response. It does not establish a unique causal split between finite-solve quality and model transfer error. The failed result is retained without a third experiment, target change or criterion relaxation.

Each official task outcome comes from the unchanged independent evaluator. Numerical completion, feasible early stopping, objective convergence, sampled settling and real-time delivery remain distinct. The two specific targets have only their recorded execution evidence; no neighborhood-wide success, robustness, continuous settling, changed-material, actuator or contact generalization is established. Small initial perturbations and the cold guess path have interface/preparation checks only, not a third full rollout.

## Verification and provenance

Five existing profile/Route tests passed using saved exports, without extra rollouts. Three focused new tests passed after correcting a duplicate preparation provenance key. The first A launch was rejected during candidate preflight because the old parser recognized only the v2 wrapper; zero backend solves/wall were charged. The v3 dispatch was fixed and the real preflight check added to the focused tests, which passed. The stale prepared session is retained as preflight evidence; the actual A execution uses a new session. There are exactly two new full backend executions.

Implementation files: `gvs_profile.py`, `gvs_nmpc.py`, `gvs_trajectory.py`, `gvs_reporting.py`, `contracts.py`, `candidate.py`, `manifest.py`, `route.py`; public example `examples/gvs_parameterized_reach.py`, focused tests and `docs/gvs_parameterized_reach.md`. No changes to the fixed profile asset or historical result files.

Each experiment folder contains its frozen input/assessment, workflow, public describe/simulate/evaluate/report receipts, summary, report, and `platform.sqlite` with sealed numerical preparation and backend exports. Backend working files are not duplicated in Git. `results.json` is the compact comparison; saved code and JSON make the three-state comparison reproducible.

A final provenance-only correction imports the original historical source artifact alongside the derived guess, so its EvidenceRef is locally readable. The two runs already sealed the complete derived numerical material and checked the packaged source hash; source bytes were subsequently appended to their Stores as explicitly post-execution archive events. `source_archive_completion.json` records this extra archive time, excluded from original simulation timing. No original receipt/result was rewritten and no control rerun was made. Future executions import both through the ordinary budgeted hook. A focused test checks source-reference resolution.

## Reproduce

```powershell
Set-Location 'D:\softrobot-agent'
$py = 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe'
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
# Read-only regeneration of this report:
& $py runs/stage318_parameterized_reach_20260927/report_results.py
# Fresh original-target execution; make-input assigns a new run/project identity:
& $py examples/gvs_parameterized_reach.py make-input --target 0.29 0.035 0.19 --output runs/repro318_A_input.json
& $py examples/gvs_parameterized_reach.py prepare --input runs/repro318_A_input.json --output runs/repro318_A
& $py examples/gvs_parameterized_reach.py run --output runs/repro318_A
# Separate neighboring-target process/project:
& $py examples/gvs_parameterized_reach.py make-input --target 0.29 0.05 0.19 --output runs/repro318_B_input.json
& $py examples/gvs_parameterized_reach.py prepare --input runs/repro318_B_input.json --output runs/repro318_B
& $py examples/gvs_parameterized_reach.py run --output runs/repro318_B
```

The fresh-run commands consume new backend budgets; they are reproduction instructions, not additional experiments performed this round. Cost samples can be reproduced with `cost_comparison.py baseline` and `cost_comparison.py velocity`; choose a copy of the evidence directory to preserve these measurements. No `freeze` or historical replay is needed.
