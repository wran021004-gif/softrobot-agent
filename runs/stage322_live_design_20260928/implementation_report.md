# Stage 3.22: real design experiment completed; provider interpretation failed

The genuine DeepSeek experiment ran through the public Route and two fresh MuJoCo executions. The second provider-selected changed design passed the unchanged original reach evaluator. The provider explicitly delivered that execution and stopped early, but described its near length incorrectly. **Physical reach passed; provider interpretation and overall final-delivery acceptance failed.** The actual provider conclusion is preserved without correction in `model_final.txt` and `provider_delivery_raw.json`.

## Authorization and preserved history

The user's direct chat withdrew the older paid-LLM prohibition and authorized credential loading plus scoped task/design/schema/evidence transmission. Automatic review approved this direct launch. `launch_review.json` retains the earlier rejection; `launch_continuation.json` records the approved continuation and final usage. The old blocked report and experience are preserved as `implementation_report_prelaunch.md` and `engineering_experience_prelaunch.json`.

The prepared session `gvs-live-e593ca2b7c60` was reused after confirming created status, matching input identity, compatible dependencies, no reservations and zero prior stage usage. The old `gvs-live-ce84ecb1bfcd` session also had zero usage. Checkout was clean at `9ff9fa8a1faaa4bf1ff927e9da661310b7a971be`. No implementation changes, numerical checks, deterministic rollouts, tuning, extra paid connectivity checks or dependency upgrades were performed in this continuation. One agent was used. No commit, push or merge was performed.

## Frozen task and control

Target `[0.29, 0.035, 0.19]` m; duration **0.35 s**; original reach tolerance **0.01 m**. Physics/control/sample periods are 0.0005/0.01/0.01 s. There are twelve serial bending cells per section. Initialization, scene, materials, damping and tendon arrangement remain frozen.

Controller `controller.gvs_nmpc@4.0.0` uses the bundled Stage 3.15/3.16/3.17 recipe: candidate GVS prediction, structural-linear basis, ten horizon intervals and one implicit substep per interval. Candidate physics determines preparation, coordinate order and tendon bounds. Historical tensions are numerical guesses only; historical states are not reused and states are regenerated from measurements using candidate dynamics. Execution uses six direct ideal tendon tensions, each 0 to 8 N, with no motor dynamics. Full recipe and preparation provenance are in `engineering_experience.json` and `trial_results.json`.

## Provider choices and measured results

Baseline lengths: near **0.160 m**, far **0.120 m**. Authorized ranges: near 0.15-0.17 m, far 0.11-0.13 m. The recorded instructions explicitly require an absolute change of at least 1 mm in either length.

| Tested candidate | Near / far (m) | Terminal error | Original reach | Sampled settling | Backend call / charged simulation |
|---|---|---:|---|---|---:|
| `build_extend_v1` | 0.170 / 0.130 | 26.278254 mm | Fail | Fail | 934.384 / 938.547 s |
| `near_shorten_v2` (delivered) | 0.159 / 0.120 | 9.438402 mm | Pass | Fail | 905.522 / 909.797 s |

The provider first extended both lengths by 10 mm, hypothesizing improved reach and reduced curvature demand. After the measured failure and repeated evidence reads, it selected a 1 mm proximal shortening from baseline, hypothesizing less gravity sag and a smaller departure from the historical tension guess. These rationales are preserved as provider hypotheses, not identified causal conclusions. The initial reachability argument compared target distance against flexible length alone even though rigid portions also contribute to the robot geometry; it does not establish baseline unreachability. No fresh baseline was rerun and no improvement over historical baseline performance is claimed.

Both executions completed all 35 control updates and passed every design/build/export/preparation/evaluation/report identity check. Neither had sampled contact, solver errors, hold-last responses or tendon-bound violations.

| Metric | Extended candidate | Delivered shortened candidate |
|---|---:|---:|
| Accepted plans / converged updates | 35 / 0 | 35 / 0 |
| Initialization-selected / noninitialization plans | 35 / 0 | 13 / 22 |
| Maximum independent scaled plan violation | 2.346e-10 | 9.919e-6 |
| Tension range (N) | 0.631530-4.755853 | 0.631530-5.005157 |
| Mean complete control update (s) | 26.6823 | 25.8660 |
| Update range (s) | 24.9570-38.1302 | 21.5477-37.6623 |
| Mean numerical solve / preparation / validation (s) | 16.4340 / 9.7532 / 0.2535 | 15.6722 / 9.6926 / 0.2577 |
| Graph / solver construction (s) | 1.2912 / 3.9394 | 1.2921 / 3.9782 |
| Missed 10 ms deadlines | 35/35 | 35/35 |
| Terminal tip speed (m/s) | 0.234191 | 0.035531 |
| Final 0.05 s maximum tip error (mm) | 34.6411 | 9.72284 |
| Final 0.05 s maximum speed (m/s) | 0.234191 | 0.0640404 |

All accepted plans were `feasible_early_stop`, with raw `User_Requested_Stop`; these are not optimizer convergence. The delivered candidate's sampled position stayed within 10 mm over the final 0.05 s, but speed exceeded 0.02 m/s. Settling therefore failed. These sampled checks provide no continuous-time guarantee. Mean updates take thousands of times the 10 ms control period, so real-time control was not demonstrated. Maximum GVS projection residual was 2.3672 rad/m for the delivered run; backend states are not assumed to remain exactly in the reduced subspace.

## Actual provider delivery and acceptance

Final request `model-23` explicitly finished with the session incumbent and cited its current run result, evaluation and report. The corrected audit binds:

- Owning run: `gvs-live-e593ca2b7c60-e552cdda64495450`.
- Execution: `5fc1457877a7456282f2f6f7d089a783`.
- Configuration: `e27be7be491f1984cc30da2e6af232056d17122fdb5a6c7653e63e5d8516e14c`.
- Evaluation: `51b6caf274252ff1aaa341826f906307e985d3137e5ec4d01cd6c88b1c9d33f2`.
- Report: `0aafd631b896f6361d7f58b9e5ac21fb2174385f26c55663449d9754233f3489`.
- Raw provider response: `f6e475a9918483a4a9fc72c12a91b705d2b4cd41e42dce18d52eba081ac4f292`.

The actual conclusion says near length **0.15 m**, a **10 mm** change. The provider's own build, effective candidate and backend export show **0.159 m**, a **1 mm** change. This is a material design-reporting error, not an ambiguous candidate label. The provider correctly reports reach versus failed settling, current evaluation references and lack of real-time feasibility. Its final explanation omits an explicit zero-optimizer-convergence qualification. `provider_interpretation_review.json` records the assistant's review bound to the exact execution, evidence, raw response and conclusion digest; no human sign-off or synthesized provider correction was added.

| Acceptance | Outcome |
|---|---|
| Genuine provider call chain through explicit delivery | Pass |
| Provider-selected authorized changed-design execution | Pass |
| Delivered original reach | Pass |
| Delivered changed-design reach on that same execution | Pass |
| Current report received in final provider context | Pass |
| Explicit provider delivery | Pass |
| Correct provider interpretation | **Fail** |
| Overall final-delivery acceptance | **Fail** |
| Additional sampled settling | Fail |
| Real-time feasibility | Not demonstrated |

## Usage and costs

The session stopped after successful changed-design reach and explicit provider finish, leaving the third backend attempt unused. Across both stage directories, usage is **24/24 real model requests, 30/60 tool calls, 2/3 backend attempts and 2372.451/7200 charged seconds**. All calls completed. There were 19 provider `evidence.read` actions and five Route actions (two builds, two runs, finish); six child simulation/evaluation/report calls account for the remaining tools.

Charged wall time by caller: model transport 499.781 s, model tools 20.169 s, child execution/evaluation/report 1852.501 s. First provider submission to last raw response spans 2415.124 s (40.252 min), a different measurement from charged time. Each physical simulation covers only 0.35 s.

Provider-reported usage totals: **477,204 prompt tokens** (96,256 cache-hit; 380,948 cache-miss), **89,555 completion tokens** including 81,782 reasoning tokens, **566,759 total tokens**. The provider returned no invoice or currency charge; monetary cost is unknown and has not been fabricated from an assumed price. No additional paid request was made to correct the final explanation.

## Saved experience and next step

`engineering_experience.json` is a structured, evidence-linked record of both tested points, the frozen task/recipe, preparation provenance, identities, actual provider rationale, results, costs and limitations. It is not a globally validated skill. `trial_results.json` includes per-update timings; `report.md` is the existing backend report; `provider_delivery_raw.json`, `model_final.txt` and `provider_delivery_context.json` preserve the actual finish and its context. The original immutable artifacts remain in `platform.sqlite`.

The compact final context contained the correct current evaluation/report but no exact `0.159` length value. The provider also spent 19 requests on evidence reads, several repeated. These are observed interface/behavior weaknesses, not proof of a single cause. **The smallest next development step is to include resolved near/far lengths and baseline deltas in the compact current-candidate delivery context, tied to the configuration reference, and check the provider's restatement against them.** That work was not performed in this execution-only continuation. The current model budget is exhausted.

Only two configurations were tested. The allowed length rectangle, physical motor behavior, contact, robustness and global stability remain unvalidated. The passing reach does not cure failed settling, slow computation or incorrect provider interpretation.

## Reproduce the saved inspection (no paid calls or rollout)

```powershell
Set-Location 'D:\softrobot-agent'
$py = 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe'
$out = 'runs/stage322_live_design_20260928'
$env:OPENBLAS_NUM_THREADS = '1'
$env:OMP_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
& $py examples/gvs_nmpc_route_experiment.py inspect --output $out
& $py runs/stage322_live_design_20260927/audit_design.py --output $out
```

The exact authorized launch used was:

```powershell
& $py examples/gvs_nmpc_route_experiment.py run --output $out --input "$out/experiment_input.json" --credential-file "$HOME\.codex\.env"
```

This session is now stopped and has exhausted its model allowance; the launch command documents provenance, not authorization to restart or expand the stage budget.
