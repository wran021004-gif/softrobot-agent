# Stage 3.15: full-task optimization feedback

Historical evidence is unchanged. All new evidence is in this directory. The original task is 0.35 s, target [0.29, 0.035, 0.19] m, 10 mm endpoint tolerance, straight start, 10 ms direct ideal-tension holds and 12 serial cells per segment.

## Warm starts and optional return policy

See [declared policy](POLICY.md). Every state is regenerated using the cached implicit shooting residual. Entire-guess defects include current initial/previous-input equalities and tendon bounds. Candidate times are relative to the solver call; delivery includes preparation, solver construction, checks and independent validation.

| Case | Preparation | Initial defect | First callback feasible | Policy stop | Validation | Delivery | Objective | Selected defect |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Historical 0.01 s | see source | 0.526 | 8.34 s | CPU cap | source | 41.16 s | 0.166844 | 6.8e-07 |
| Historical 0.02 s | see source | 0.371 | 14.15 s | CPU cap | source | 32.72 s | 0.0582859 | 3.84e-06 |
| Case 1, regenerated only | 10.77 s | 3.28e-13 | 9.73 s | disabled | 0.191 s | 46.17 s | 0.168859 | 2.01e-06 |
| Case 2, regenerated only | 6.02 s | 3.86e-11 | 2.85 s | disabled | 0.193 s | 36.91 s | 0.0577452 | 6.53e-06 |
| Case 1, policy | 6.32 s | 3.28e-13 | 9.79 s | 9.79 s | 0.066 s | 16.37 s | 0.261641 | 3.27e-06 |
| Case 2, policy | 6.03 s | 3.86e-11 | 2.73 s | 13.00 s | 0.127 s | 19.22 s | 0.0585599 | 2.8e-06 |

The policy deliberately trades some objective improvement for bounded delivery. Case 1 stops at objective 0.26164 versus 0.16886 with the longer regenerated solve; case 2 stops at 0.058560 versus 0.057745. Both satisfy the unchanged 1e-5 threshold. Raw termination is User_Requested_Stop, not convergence. Generic default behavior is unchanged.

## Nonlinear GVS execution

**Full duration and settling pass.** Endpoint 3.661 mm; tip speed 0.01661 m/s. Final 50 ms maxima: 4.009 mm and 0.01923 m/s. Maximum plan defect 7.73e-06; tension range [0.5529417509026899, 4.980115024271848] N.

Measured computation 1125.18 s including both constructions and the reused prefix; preparation 346.00 s, numerical solves 519.20 s, BDF integration 220.61 s. 7 of 35 updates selected initialization; the remaining updates improved their plans.

The first 12 actually integrated intervals are reused from the approach check; later states continue from its actual BDF endpoint. No prediction nodes substitute for observations. Settling is a separate sampled 50 ms window criterion; it does not redefine official task success.

## Recorded-command numerical diagnosis

| Physics step | Complete | First reset | Last pre-warning/terminal error | Wall time |
|---|---|---|---:|---:|
| 0.50 ms | False | 0.23600000000000018 | 368.46 mm | 0.037 s |
| 0.25 ms | True | none | 292.73 mm | 0.103 s |

No optimizer runs in these replays. Commands switch at identical physical times. The 0.25 ms case is a numerical diagnostic; public execution retains the authoritative 0.5 ms setting.

## Public MuJoCo execution

**Original evaluator: valid, task_success=true.** Full 0.35 s at 0.5 ms physics step; endpoint 8.473 mm. 35 feasible intentional stops, zero solver errors, zero hold-last responses, zero numerical resets. Maximum independently checked defect 9.24e-06; tensions 0.566–5.026 N within each tendon’s authoritative 0–8 N bounds; violation 0.0 N.

Execution wall time 881.23 s. Mean delivered update 25.073 s: preparation 9.584 s, numerical solve 14.986 s, validation 0.258 s. Workspace graph 1.318 s, solver construction 3.969 s. All 35 deadlines missed; not real time.

Backend endpoint speed 0.02095 m/s, final-window maximum 0.03156 m/s. The separate GVS settling criterion is **not** met by MuJoCo; the authoritative reach criterion is met. Maximum position/rate projection residuals 2.472 rad/m and 12.563 rad/(m*s); no exact-subspace claim. 7 of 35 updates selected initialization; sampled contact count is zero.

The original `evaluation.run` receipt was rejected by wall-time reservation: the host reserved the full 1800 s call timeout although only about 1220 s remained in the session. It was not a backend-solve-limit rejection. The immutable simulation receipt and rejection remain intact. A new read-only `evaluation.saved` session checked the sealed producer receipt, identical task/instance/backend and **all** unchanged producer dependencies, then called the original `evaluate.reach`. `saved_evaluation_receipt.json` records public acceptance and `task_success=true`, with zero backend solves. `source_compatibility.json` records no dependency changes. The reproduction reserves enough wall budget for the original evaluation tool.

Backend motion is reconstructed with read-only `mj_forward`/site Jacobians at saved actual states; no dynamics or optimization is rerun. Sampled contact counts do not constitute a continuous contact trace. Root-solver graph setup is included in first warm preparation; the separately reported graph time is workspace assembly.

For context, the archived same-start sampled-LQR endpoint was 33.942 mm (`../stage312_to_nmpc_20260926/lqr_task.json`, same task/timing/resolution); it is reused evidence, not a new baseline run.

## Implementation and focused checks

- `354c9e0`: full warm-state regeneration, optional feasible return, raw status preservation, soft terminal rate cost, sustained-unusable stop and controller timing metadata.
- The two saved-state comparisons verify full regenerated guesses, physical scaling and independently feasible selected plans through the production workspace.
- Two focused optimizer tests pass: intentional stop/current bounds and unchanged iteration-limited feasible-candidate retention. One new saved-evaluation test checks public acceptance, unchanged producer snapshot, task mismatch and changed-source rejection. No full suite or historical investigation was rerun.
- `42a1fe3` / `7801923`: comparison evidence, approach checkpoint, reproducible bounded protocol.
- `a745a68`: focused read-only saved-result evaluator and future reproduction budget fix. Original evaluator, host, storage contracts and old extension definitions are unchanged.

## Reproduction

Run in a fresh output directory for a new immutable public session. The full GVS command reuses the actual approach checkpoint from the same output directory.

```powershell
Set-Location 'D:\softrobot-agent'
$py = 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe'
$env:OPENBLAS_NUM_THREADS='1'; $env:OMP_NUM_THREADS='1'; $env:MKL_NUM_THREADS='1'
$out = 'runs/stage315_reproduction'
$script = 'runs/stage315_complete_control_20260927/experiment.py'
& $py $script compare --output $out
& $py $script gvs-check --output $out
& $py $script gvs-full --output $out
& $py $script replay --output $out
& $py $script public --output $out
```

Mathematical feasibility, nonlinear task performance and real-time feasibility remain separate. Every measured solve is slower than the 10 ms controller deadline. No real-time claim is made.

## Concrete limits

This is one fixed free-reach task and straight start, not a robustness or global-stability result. Plans are independently feasible and quality-qualified but intentionally stopped before mathematical convergence. Preparation and solving remain far above the 10 ms deadline and the 10 s development-delivery objective. Projection residuals remain nonzero. MuJoCo passes reach but not the additional 50 ms low-motion criterion. The refined historical replay is not a successful task and includes unintended floor contact: both step sizes first contact at 0.2355 s; the 0.5 ms reset follows at 0.236 s. This supports timestep sensitivity of that excursion, not validated contact prediction.
