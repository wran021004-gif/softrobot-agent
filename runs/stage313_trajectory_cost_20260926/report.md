# Five-interval GVS trajectory computation repair

A new usable **50 ms** trajectory was produced through `Host.invoke`: `optimization.assemble` followed by `optimization.solve`. This is not a full-task control result. No backend simulation or LLM call was made.

The 10-second development target was **not reached**. Warm numerical optimization took 31.141 s (31.277 s including cached setup and validation). The original implementation exhausted the same 30 s CPU budget after 31.515 s with zero completed iterations and no feasible plan. This truncated baseline is not a completed time-to-solution and does not support a full-solve speedup ratio. The dominant warmed Jacobian evaluation improved approximately **11.5x**.

## Frozen problem and reference

Baseline checkout: `632e4fdb1edcffa44cf8533c2abaa29f1bec7f30`. The original symbolic problem was saved before computational changes in `reference_problem.json.gz`; its canonical identity is `9f80f9a5eec50bc5870c27741208cf633cc0ded65b15bc119724fbd86fc57c41`.

`fixed_problem.json` contains the unchanged robot and task, structural-linear basis, model defaults/quadrature, 5 intervals of 10 ms, one implicit-Euler substep, all objective weights, state scales 10 rad/m and 1000 rad/(m*s), 180 ordered decisions, 120 dynamics constraints, straight initial state, and original six previous tensions. The archived `runs/stage312_to_nmpc_20260926/offline_scaled_candidate.json` supplies the **same numerical initial guess in every comparison and public solve**. The previous-input values come from the frozen Stage 3.11 reference. The trajectory parameters are those saved in `offline_trajectory.json`.

Maximum iterations remain 120; tolerance and acceptable tolerance are 1e-6; usable-plan maximum scaled violation remains 1e-5. Only the experimental CPU cap changes from the historical 120 s to 30 s, identically for the measured before/after runs. The cap reduction is not counted as a speedup. Decision specifications and complete initial-guess dictionaries were compared for equality against the frozen problem. The returned plan differs from the seed.

Environment was recorded once in `environment.json`: Python 3.11.16 at `C:\Users\gugugaga\miniconda3\envs\softagent\python.exe`, NumPy 2.4.6, SciPy 1.17.1, CasADi 3.7.2, Windows 10; OPENBLAS/OMP/MKL threads all 1; stage evaluation threads 1. Final implementation requires no C compiler.

## Implemented changes

1. `gvs_casadi.py` computes the implicit inertial residual by directional point accelerations and adjoint projection of each mass sample's force/torque. It avoids forming the full generalized mass matrix and all pose-Jacobian columns on this path. Sample-level function boundaries contain derivative graphs. Gravity, elasticity, damping, routing, quadrature and temporal discretization are unchanged. The full dynamics provider continues exposing its mass matrix and other existing outputs.
2. `IpoptParameters.constraint_jacobian_mode="reverse"` makes `IpoptSolver` supply an exact reverse-AD constraint Jacobian. It avoids wide forward derivative batches and the unused solution-sensitivity helper. The default remains `automatic`; cache keys include the selected mode. There is no finite-difference approximation, native compilation, reduced basis, changed cost or relaxed constraint in the delivered path.

Solver diagnostics now retain function-call counts/times and post-solve validation time. Existing graph and solver caches are reused; no new caching framework was introduced.

## Timing and new result

Two calls per function at the identical representative decision vector separate first and warmed evaluation. These are small diagnostic samples, not a benchmark campaign. Profile `construction_s` values measure function-wrapper construction only, not AD transformation; actual solver construction is reported separately below.

| Evaluation | Original first / warm, s | Improved first / warm, s |
|---|---:|---:|
| Objective | 0.000218 / 0.000152 | 0.000385 / 0.000175 |
| Constraints | 0.168580 / 0.163208 | 0.067786 / 0.065986 |
| Objective gradient | 0.000584 / 0.000522 | 0.000607 / 0.000531 |
| Constraint Jacobian | 15.166111 / 15.346962 | 1.347672 / 1.329429 |

The improved IPOPT Jacobian helper also returns constraint values, while the original isolated probe returns the Jacobian alone. The measured reduction is therefore conservative. In the original bounded solve, two Jacobian calls consumed 31.306 s of the 31.515 s numerical solve, identifying the dominant cost directly.

| Measurement | Original bounded solve | Improved first solve | Improved cached solve |
|---|---:|---:|---:|
| Solver construction, s | 21.428 | 3.969 | 0.000007 |
| Numerical optimization, s | 31.515 | 30.851 | 31.141 |
| Post-solve validation, s | 0.183 | 0.134 | 0.134 |
| Total solver call, s | 53.132 | 34.956 | 31.277 |
| Iterations | 0 | 19 | 19 |
| Returned scaled violation | 0.239777 | 7.97634e-6 | 7.97634e-6 |
| Status | iteration_limit | iteration_limit | iteration_limit |

A separate assembly-only timing resolves setup cost: graph assembly including serialization took 1.401 s; the complete profiled public assembly call took 6.552 s. The original public assembly call took 3.634 s without that profiler; these public totals are not a graph-build speed comparison.

Final public solve: **33.374 s** total wall time, including 0.128 s solver construction, 30.813 s numerical optimization and 0.134 s validation. It ran in the already warmed process with a new solver instance and the unchanged original seed. Shared symbolic derivative caches explain the smaller construction cost; no previous optimum was used as a new initial guess.

The public result is `iteration_limit` (`Maximum_CpuTime_Exceeded`), **not converged or optimal**. The existing feasible-iterate mechanism selected iteration 8 from that public solve's 19 iterations. The raw final iterate's violation was 0.0142370; it was not accepted. The selected plan was independently reevaluated using the frozen original expressions:

- Maximum scaled dynamics/bound violation: **7.9763411543e-6**, within unchanged 1e-5 acceptance.
- Objective: **0.3615351960**. The archived feasible plan's objective is 0.3622745373; the new plan does not have a worse objective, but its feasibility residual is closer to the acceptance threshold.
- Initial-state equality error and previous-input error: **0**.
- Physical tensions: **0.0000070102 to 7.9999400172 N**, within the original [0,8] N bounds.
- States and tensions are finite. `trajectory.json` saves the 6 physical states and 5 physical tension vectors, ordering and independent checks.
- Original-reference reevaluation took 0.174 s, outside IPOPT.

At the seed and one perturbed decision vector, original-versus-new constraint-value differences were at most 1.39e-14, and objective differences were zero. A directional AD check against central differences of the original expressions passed (maximum error 1.54e-7, rtol 2e-5/atol 2e-6). The actual reverse-AD solver Jacobian passed the same directional check before the public solve.

Public evidence: `exact_reverse_assembly_receipt.json`, `public_solve_receipt.json`, `public_result.json`, `public_solver_diagnostics.json`, and the project Store/session records. `summary.json` provides the compact comparison. No task-success claim is attached to this short-horizon optimization.

## Discarded attempts and remaining cost

Whole-graph SX expansion and monolithic native compilation produced oversized graphs/C functions and were stopped or failed with LCC64 `insufficient memory`. A compiled-values/finite-difference trial took 34.677 s for one iteration and remained infeasible (0.00190658 violation); it is preserved in `rejected_fd_solve.json`, not presented as a useful result. These implementations are absent from production. `attempts.json` records the bounded investigations.

After a feasible public result was obtained, forcing full interval Jacobians was checked once: 1.283 s versus 1.285 s for the prior reverse probe, offering no material gain; that change was reverted. The remaining dominant cost is exact constraint-Jacobian evaluation, about 1.3 s per call and roughly 28 s per bounded solve. Optimizer progress also remains nonmonotonic: the selected feasible iterate precedes an infeasible final iterate. Reaching 10 s requires further derivative-cost/convergence work; shortening the timeout would not demonstrate that improvement.

## Reproduce

Use a fresh output directory. The command performs three bounded solves: first construction, cached solver with the identical seed, and the public solve. It performs no simulation. CPU-limited iteration counts may vary with machine load.

```powershell
Set-Location 'D:\softrobot-agent'
$py = 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe'
$env:OPENBLAS_NUM_THREADS = '1'
$env:OMP_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
& $py runs/stage313_trajectory_cost_20260926/experiment.py candidate --output runs/stage313_reproduction
```

Optional bounded baseline reproduction uses the frozen pre-change problem, not current GVS expressions:

```powershell
& $py runs/stage313_trajectory_cost_20260926/experiment.py baseline --output runs/stage313_baseline_reproduction
```
