# Stage 3.24: time-reference tracking

Implemented and physically demonstrated sampled tracking. The original robot passed on its first deterministic execution; one DeepSeek-selected changed candidate also passed. The live public chain completed after one recorded same-session protocol correction, and structured candidate facts matched. **Provider-authored final prose failed independent review because it contradicts the measured deadline misses. Overall accurate-delivery acceptance is false.** The wrong text is preserved, not rewritten into a pass. No further paid calls or simulations were made after explicit delivery.

The checkout started clean on `feat/gvs-dynamics` at `02c7d00fcc884966a8ba03509236c6f2d4bf7183`. Changes remain uncommitted; nothing was pushed or merged. `environment.json` records the requested Python 3.11 interpreter, installed dependencies and single-thread settings. One agent was used; no dependencies were upgraded and MATLAB was not started.

Baseline reference: existing reports under `runs/stage321_window_braking_llm_20260927`, `runs/stage322_live_design_20260928`, and `runs/stage323_delivery_repair_20260928`. Stage 3.22 demonstrated LLM-selected design changes, two new executions and changed-design reaching, but its original explanation was wrong. Stage 3.23 repaired candidate facts, retention, deduplication and structured validation; a fresh delivery-only request interpreted existing evidence correctly. Historical near/far lengths were 0.159/0.120 m versus 0.160/0.120 m, reaching error 0.0094384 m, sampled settling failed, mean update 25.866 s, ideal tensions. Those experiments and the delivery review were not rerun or copied. They did not establish a repaired fresh end-to-end session, broad design coverage or real-time control.

Public implementation:

- `examples/gvs_tracking.py`: solve-free input creation, frozen-input preparation/execution and bounded live-input creation, reusing the existing public simulation/evaluation/report and DeepSeek Route workflows.
- `task.tracking@1.0.0`, `family.cartesian_reference@1.0.0`, `evaluate.tracking@1.0.0`: constant or quintic world/SI reference, deterministic position/velocity evaluation, clamped endpoint positions and zero velocity outside the interval; independent complete-grid evaluation.
- `controller.gvs_nmpc@5.0.0` and `optimization_assembler.gvs_tracking@1.0.0`: constant and moving references share the same controller/workspace. Absolute prediction times are current execution time plus node offsets. Equal-bound reference input slots prescribe position/velocity and cannot be optimized. The graph and solver are reused as time advances. Position and enabled world tip velocity costs subtract reference values, including terminal costs. Tracking has no absolute-speed holding/braking schedule or seed-settled shortcut. Existing reaching versions retain their semantics.
- Existing measured-state warm regeneration, bounded tensions, input-variation penalties, independent plan validation, feasible-early-stop versus convergence distinction, and complete cost accounting remain in use. Scenes omit fixed target sites for tracking. Reports read the frozen reference and saved backend motion.
- `analysis.gvs_candidate_evaluate@1.0.0`: resolves an explicit completed build owned by the Route session, then evaluates the effective robot with its frozen controller basis and task physical context using existing GVS mathematics. Output binds the immutable configuration, candidate, effective input/robot/task identities, model, resolved basis, coordinate order and robot-base calculation frame. It uses no execution data and invents no physical execution ID. Tracking Route runs require a completed analysis of the exact build; implicit optimization/crosscheck paths are excluded from this first analyzed-build workflow. Other mathematical entry points retain their existing scope and are not exposed in this live policy.

`analysis_proof/proof.json` records two public tools, zero provider/backend calls, and an actual calculation for near length 0.162 m: exact agreement with direct evaluation of that configuration, with straight-arm robot-frame tip x=0.310 m versus baseline 0.308 m. This verifies changed mathematics, not just a metadata label. For the live candidate, the pre-execution analysis configuration matches the executed build and all effective physical/task/control data match. The raw whole-input digest changes only because execution normalization reorders `policy.allowed_tools`; canonicalizing that list makes the full inputs identical. Both immutable references are retained.

Frozen task and criterion, chosen before rollout (`frozen_input.json`):

| Item | Value |
|---|---|
| Original near / far lengths | 0.160 / 0.120 m |
| Reference start | [0.308, 0, 0.150] m, world |
| Reference end | [0.306, 0.024, 0.142] m, world |
| Reference / execution interval | 0 to 0.40 s |
| Interpolation | start + (end-start)(10u^3 - 15u^4 + 6u^5), u=(t-start)/(end-start), clamped to [0,1] |
| Initialization provenance | Baseline MuJoCo `mj_forward` at the existing task initializer, without integration |
| Scoring interval | 0.01 to 0.40 s inclusive, 40 post-step samples |
| Acceptance | Complete valid execution, every scored Euclidean position error <=0.01 m, sampled tendon bounds satisfied |
| RMS | Square root of arithmetic mean of squared errors over those uniform samples |
| Terminal error | Error at execution endpoint |
| Physics / control / sample periods | 0.0005 / 0.01 / 0.01 s |
| Predictor / execution | Existing structural-linear GVS basis, 12 coordinates; existing MuJoCo twelve cells per section |
| Inputs | Six ideal bounded 0-8 N tendon tensions; no motor dynamics |

The path moves 25.377 mm, so a stationary initialized tip cannot pass the whole interval. Reference, scoring window and acceptance never changed or re-anchored for a candidate. Missing/nonfinite samples or incomplete execution cannot succeed. Boundaries must lie on the saved sampling grid; there is no interpolation over missing data and no invented t=0 post-step sample. Velocity error is diagnostic, with no old low-speed holding criterion. Materials, damping, scene, initialization and discretization remain fixed. The recipe uses horizon 10, one implicit substep, relative velocity weights 0.01 (stage and terminal), terminal position weight 5, measured-state regeneration, initial-pretension guesses and returned-tension feasibility recovery; exact remaining settings are frozen in the input.

Measured results and complete cost (validation overlaps recovery validation; do not blindly sum columns):

| Quantity | Deterministic baseline | Live changed candidate |
|---|---:|---:|
| Complete valid execution | True | True |
| Tracking accepted | True | True |
| Maximum error, m | 0.005772548837294318 | 0.00719823810484788 |
| Terminal error, m | 0.003872882630204964 | 0.00719823810484788 |
| Accepted plans | 40 | 40 |
| Converged updates | 0 | 0 |
| Hold-last responses | 0 | 0 |
| Force-bound violation, N | 0.0 | 0.0 |
| Mean complete update, s | 30.390883490006672 | 27.929852807486895 |
| Mean warm preparation, s | 9.468019430001732 | 10.6058610524924 |
| Mean numerical solve, s | 15.85032900502556 | 15.25492737001623 |
| Mean validation, s | 0.4025435450428631 | 0.3035192349925637 |
| Mean recovery total, s | 4.520016139990185 | 1.5523408625100275 |
| Graph construction, s | 1.2834695000201464 | 1.34222050011158 |
| Solver construction total, s | 3.936633199919015 | 4.088749299757183 |
| Charged simulation wall, s | 1220.5469999997877 | 1122.344000000041 |
| Deadline misses / 40 | 40 | 40 |
| RMS error, m | 0.004412616885360754 | 0.006001923582692169 |

Deterministic backend breakdown: `{"backend_call": 1216.3148956999648, "engine_compile": 0.023313899990171194, "prepare_compile": 0.03919460019096732, "solve": 1216.013571599964}`. Live backend breakdown: `{"backend_call": 1117.9175068000332, "engine_compile": 0.024819200159981847, "prepare_compile": 0.03964299988001585, "solve": 1117.6149852999952}`. Charged simulation includes public preparation and host overhead; the detailed preparation provenance and per-update lists remain in each `summary.json`. The deterministic rollout required no correction. The public chain sealed simulation, evaluation and report successfully, then its console printer raised a reaching-only `sampled_settling` KeyError. That display was fixed and checked with the sealed summary and mocked calls, without rerunning or replacing evidence. Route discovery/report wiring and the analysis prerequisite were completed before live execution; no optimizer, dynamics, task or recipe changed afterward.

`one_step_prediction_audit.json` compares saved accepted-plan predictions with the next measured backend state across all 40 deterministic intervals: times align and actual ideal tendon inputs match exactly. Maximum/RMS one-step tip discrepancy is 0.002256738 / 0.001905164 m; generalized coordinates/rates are compared where the next observation exists. No diagnostic re-solves were used. These discrepancies mix model, representation and time-integration effects and do not identify their individual causes. `deterministic_tracking.png` plots all scored errors.

The live provider chose **near 0.165 m (+0.005 m), far 0.120 m (unchanged)** without a prescribed candidate. It completed a correctly bound mathematical analysis at zero q/qdot and 0.2 N per tendon before execution. The first loop stopped after 11 requests, 7 charged tools and no backend on invalid tool arguments. One explicit syntax correction was recorded in the same session; the incomplete host terminal summary was archived, and the existing `Host.resume` path continued. No task, budget, turn, usage or repair counter was reset and no new session was created. The provider then ran the candidate, read its result, repeated analysis once, recovered from another invalid evidence-read request, and explicitly delivered. This is an assisted bounded continuation, not clean unassisted end-to-end success. `live/first_stop_*.json`, `live_first_stop.log`, `protocol_continuation.json` and the Store events preserve this history.

| Live review dimension | Result |
|---|---|
| Public build / analysis / run / evaluation / report / finish chain | Completed after one explicit protocol correction |
| Mathematical analysis used intended candidate before execution | Passed |
| Delivered changed candidate passed frozen interval tracking | Passed |
| Structured candidate facts and evidence identities | Matched |
| Actual provider-authored final prose | Failed independent accuracy review |
| Overall accurate-delivery acceptance | Failed |

The exact final text is `live/model_final.txt`. It says **"zero deadline-nonconforming updates"**, but evidence shows **40/40 deadline misses**, and the same paragraph also correctly states `deadline_misses 40` and no real-time demonstration. This internal contradiction is not silently excused or edited. Other reviewed candidate values, errors, bounds, plan/convergence counts and rounded cost values match. `provider_interpretation_review.json` binds the finding to the exact raw response and explanation. The explicit delivery is preserved as a negative prose example; no delivery-only retry or second session was launched.

| Live usage, including the genuine correction and child operations | Actual / ceiling |
|---|---:|
| Provider requests | 17 / 24 |
| Tool invocation attempts, including five preflight rejections | 20 / 60 |
| Charged tool calls | 15 |
| Fresh backend attempts | 1 / 3 |
| Charged wall time | 1357.080 / 7200 s |
| Provider tokens | 307,216 prompt + 41,360 completion = 348,576 |

Completion includes 34,495 reasoning tokens; prompt cache hits were 81,920 tokens. Monetary charges were not returned. Two backend attempts and seven provider requests remain unused. The initial automatic approval review rejected launch before process creation; explicit attached-authorization/payload checks then obtained approval for the same direct command. `launch_review.json` and `launch_continuation.json` retain both events. Credentials were loaded only by the existing loader and never saved in artifacts.

Evidence identities: deterministic execution `e643574e7a2d486e9ef6f1d7a1060e91`; live execution `842ae454986e4a41b9dbaca5a57fb40a`, candidate configuration `ad97dadde9a7422ea64f447428ad87bb8a48ae5c33e93576c4a7ac1e4a54e1d7`, evaluation `60db46fb085bbeb99f8c3763873bc2062a00fd42281e819284a91abe71c43286`. Public receipts and sealed artifacts reside in the corresponding session directories.

Focused verification: four new tests plus the three existing Stage 3.23 tests passed (7 in 5.240 s). Two affected checks passed after strengthening the force-bound assertion and parent-copy fixture; the three delivery tests passed again after Route wiring (2.748 s). The exact-binding analysis prerequisite was checked against saved public evidence, including rejection of a different candidate. `validation_results.json` records these checks. No full suite, parameter sweep, old reaching rollout or optional benchmark was run.

Remaining scope: sampled acceptance only, no continuous-time guarantee; offline simulation only, no real-time claim; ideal tendon inputs only; one short path and two freshly executed designs, not broad design coverage, general settling, robustness, contact or motor validation. Constant references share the implementation and passed graph/timing checks but were not given an extra rollout. Historical Stage 3.23 delivery repairs remain intact, while this regression demonstrates remaining provider protocol and prose reliability limitations.

Exact PowerShell reproduction commands, from `D:\softrobot-agent` (use fresh output directories):

```powershell
$softPython = 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe'
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
& $softPython -m unittest tests.test_stage324_tracking tests.test_stage323_delivery_repair -v
& $softPython examples/gvs_tracking.py make-input --output runs/tracking_reproduce_input.json
& $softPython examples/gvs_tracking.py prepare --input runs/tracking_reproduce_input.json --output runs/tracking_reproduce
& $softPython examples/gvs_tracking.py run --input runs/tracking_reproduce_input.json --output runs/tracking_reproduce
& $softPython runs/stage324_time_reference_tracking_20260928/verify_candidate.py --output runs/tracking_analysis_reproduce
```

To repeat this exact task, use `runs/stage324_time_reference_tracking_20260928/frozen_input.json` instead of generating another input. After a deterministic pass, prepare the same frozen task for the existing provider workflow:

```powershell
& $softPython examples/gvs_tracking.py live-input --input runs/stage324_time_reference_tracking_20260928/frozen_input.json --output runs/tracking_live_reproduce_input.json
& $softPython examples/gvs_nmpc_route_experiment.py prepare --input runs/tracking_live_reproduce_input.json --output runs/tracking_live_reproduce
$credentialFile = Join-Path $HOME '.codex\.env'
& $softPython examples/gvs_nmpc_route_experiment.py run --input runs/tracking_live_reproduce_input.json --output runs/tracking_live_reproduce --credential-file $credentialFile
```

Provider decisions are nondeterministic. `resume_protocol_once.py` records the specific one-time continuation of this historical session, not an automatic retry loop or a command to reopen the now-finished delivery. New artifacts follow the existing ignored `runs/` convention; implementation and tests remain reviewable uncommitted changes.
