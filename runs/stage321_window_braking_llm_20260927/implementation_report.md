# Stage 3.21: window braking and conditional LLM acceptance

Stage complete: False. B passed reach and all sampled settling checks; A failed both. The conditional live session was not launched.

Implementation `17b817ccbe39720140509594f36824542b184693`; original baseline `dbe49b3`. Historical evidence and fixed v2 profile preserved.

The new reusable `holding_brake_lead_s` recipe field starts holding-speed cost earlier relative to the task window. Zero preserves the old schedule; the tested 0.05 s value is an empirical temporal margin, not a bound on model error. The authoritative 0.35 s task, 0.30–0.35 s sampled window, 10 mm / 0.02 m/s limits, physical model, ideal tensions, 10 ms control period and 0.5 ms physics step are unchanged.

## Diagnosis

- The existing 100 ms horizon anticipates the 300 ms holding start from 200 ms; it is not blind until holding starts.
- Stage 3.20 retains 51.70 mm/s measured speed at 280 ms. At 290 ms the actual applied command predicts 3.14 mm/s at 300 ms, versus 25.27 mm/s measured; vector error is 23.56 mm/s. Projection alone differs by 1.38 mm/s in velocity vector before this interval.
- The three sampled original plans were selected IPOPT iterates 3, 2, 2, had objective improvements and original-feasible returned iterates. Initialization lock is not the observed local cause; limited optimization progress elsewhere is not excluded.
- One-period discrepancies have different signs/directions. They include reduced representation, dynamics and time integration differences; this sample cannot uniquely separate them or certify an error bound.
- Use a 50 ms empirical temporal margin: move full holding-speed cost to 250 ms while retaining 300--350 ms acceptance. This allows residual motion to decay before the actual window; no fixed velocity-vector correction, new budget, or gain sweep.
- Reconstructed full plans are diagnostic re-solves from current states with regenerated constant-tension seeds, not the missing historical selected plans. The 290 ms lead and baseline schedules are identical; that repeated local solve is not additional candidate evidence.
- The 240 ms lead reconstruction brakes earlier but predicts a later speed rebound above threshold; local results support a physical test, not a predicted pass.

| State s | Projected velocity vector error mm/s | Next predicted speed mm/s | Next measured speed mm/s | Next vector error mm/s |
|---:|---:|---:|---:|---:|
| 0.24 | 2.159 | 67.230 | 57.879 | 12.643 |
| 0.28 | 2.947 | 45.931 | 33.054 | 16.119 |
| 0.29 | 1.384 | 3.141 | 25.266 | 23.558 |

## Actual physical acceptance

| Execution | Reach | Sampled settling | Endpoint mm | Window max mm | Window max mm/s | Speed margin mm/s | Mean update s | Misses |
|---|---|---|---:|---:|---:|---:|---:|---:|
| B | True (valid) | True | 8.4112 | 8.4112 | 19.5517 | 0.4483 | 27.403 | 35/35 |
| B_correction | Not executed | Not executed | — | — | — | — | — | — |
| A | False (valid) | False | 10.9298 | 10.9298 | 54.6129 | -34.6129 | 29.670 | 35/35 |
| live | Not executed | Not executed | — | — | — | — | — | — |

B: execution `c181d39d0c044bec836ae04a64126e9b`, evaluation `bc3b200015cee7b6b18757a19db9fefccd0204860b9b7f308ad84f1ab76211bb`. Accepted plans 35/35; converged 0; initialization selections 4; recovered 10; maximum residual 9.94e-06. Solver errors 0; holds 0; force violation 0.0 N; tension range [0.16767469486054454, 4.804202885710652] N.

| Sample time s | Error mm | Speed mm/s |
|---:|---:|---:|
| 0.30 | 7.5956 | 17.7646 |
| 0.31 | 7.7455 | 15.2063 |
| 0.32 | 7.8972 | 16.5372 |
| 0.33 | 8.0537 | 16.4261 |
| 0.34 | 8.2300 | 19.5517 |
| 0.35 | 8.4112 | 18.5281 |

A: execution `d8d5256ce61e4409a2447bf7b1f1423b`, evaluation `0b7b89381a6738c9291615a42a96789c6f8b2fe06b47da32d10a2a534c7f7ffe`. Accepted plans 35/35; converged 0; initialization selections 0; recovered 16; maximum residual 9.63e-06. Solver errors 0; holds 0; force violation 0.0 N; tension range [0.1281334053102584, 5.480277357319036] N.

| Sample time s | Error mm | Speed mm/s |
|---:|---:|---:|
| 0.30 | 8.7112 | 46.0492 |
| 0.31 | 9.0822 | 35.1823 |
| 0.32 | 9.5300 | 52.5738 |
| 0.33 | 9.9928 | 45.2167 |
| 0.34 | 10.4933 | 54.6129 |
| 0.35 | 10.9298 | 39.8376 |

## Remaining physical blocker

A drifts away during the holding window: all six speeds fail and the last two positions fail. It has zero initialization selections, 16 recovered plans, 35 feasible accepted plans, no holds and no solver errors. This is physical task failure, not a computation-budget rejection or a stopped execution.

Two saved-state one-interval checks use exactly the actual applied tension. They do not compare a rolling endpoint with the current measurement:

| Interval s | Predicted speed mm/s | Actual speed mm/s | Velocity-vector error mm/s |
|---|---:|---:|---:|
| 0.29–0.30 | 3.154 | 46.049 | 43.906 |
| 0.33–0.34 | 7.295 | 54.613 | 47.667 |

A also has 4.66–4.81 mm position reconstruction differences at those interval starts. The lead-only recipe therefore does not close the measured discrepancy across both tasks. The separate roles of representation, dynamics, integration and unfinished optimization remain unresolved. A new control correction would require fresh validation on both targets; B’s passing result cannot validate a changed recipe.

The specified extra B execution is conditional on a failed B run; B passed on its first run. No second A run was specified, and the live session requires both tasks to pass. The unused conditional allowances were not spent. No claim that all numerical or model-request budgets were exhausted is made.

## Computation

Complete delivery includes warm preparation, solver construction/solve, recovery and validation. Recovery validation is also counted in validation: do not sum overlapping columns. Graph construction and public preparation are once per execution. Process time includes reporting; live additionally includes provider decisions. 0.01 s deadlines differ from the 10 s development target.

| Execution | Graph s | Solver construction s | Warm mean s | Solve mean s | Recovery mean s | Validation mean s | Process s |
|---|---:|---:|---:|---:|---:|---:|---:|
| B | 1.279 | 3.928 | 9.525 | 14.895 | 2.483 | 0.299 | 968.194 |
| A | 1.288 | 3.951 | 10.672 | 15.200 | 3.303 | 0.312 | 1047.471 |

## Public path and live acceptance

The existing v3 preparation freezes the full task, recipe, initialization provenance and evidence scope. `examples/gvs_nmpc_route_experiment.py --input` now accepts a public parameterized SessionInput, rejects changed inputs on resume, and advertises the frozen combination for model selection. No target-specific controller/Route branches or private cache injection. The real-provider project/session ceilings are 24 model calls, 60 tools, one backend and 3600 s. Child-owned reports remain available in current model context.

Live session not executed: A failed the physical prerequisite. Real-provider requests / live tool calls / live backend executions: **0 / 0 / 0**. Current-evidence reading and explanation checks are unexecuted, not passed; no model final answer exists. The two deterministic public runs used 8 tools and two backend executions, with zero model calls.

## Focused verification and limitations

Eight focused tests: seven passed initially; the timing fixture attempted to mutate a frozen Pydantic object and was corrected to model_copy. Its focused rerun passed. No full suite. Local numerical solves used three frozen current states; no historical full rollout was repeated.

Evidence covers this fixed robot, tested explicit targets, free space and ideal tensions. Sampled settling is not continuous-time settling. Feasible unfinished optimization does not establish convergence. These executions do not establish robustness, arbitrary-target transfer, hardware performance or real-time control.

## Reproduction

Use a fresh output folder for a new execution; archived execute.py deliberately refuses to overwrite executed folders. Read-only report consolidation does not consume a backend or model call.

```powershell
Set-Location 'D:\softrobot-agent'
$py = 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe'
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
& $py runs/stage321_window_braking_llm_20260927/report_results.py
# Optional short same-input diagnosis of the saved failed A trajectory (no backend rollout):
& $py runs/stage321_window_braking_llm_20260927/review_A.py
& $py examples/gvs_parameterized_reach.py run --input runs/stage321_window_braking_llm_20260927/B_input.json --output runs/repro321_B
# Only after B passes reach and all sampled settling checks:
& $py examples/gvs_parameterized_reach.py run --input runs/stage321_window_braking_llm_20260927/A_input.json --output runs/repro321_A
# DO NOT launch for this candidate: A failed. After a newly validated candidate passes both gates:
# & $py examples/gvs_nmpc_route_experiment.py run --input runs/validated_candidate_B.json --output runs/repro321_live --wall-s 3600
```
