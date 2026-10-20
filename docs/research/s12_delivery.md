# S12 delivery ? original mirror task accepted by the real autonomous Agent

**S12 completed a real DeepSeek/Strands Study, found a new complete MuJoCo pass, and ended with native SELECT.** The original frozen task and evaluator were unchanged. Independent recomputation matched the original evaluator and full acceptance for all 27 physical executions. The first complete pass was the last physical execution; only evidence reads and SELECT followed it.

| Original requirement | Selected measured value | Original limit |
|---|---:|---:|
| Terminal position error | 0.008340186060374276 m | 0.01 m |
| Maximum final-window position error | 0.008429987595659346 m | 0.01 m |
| Maximum final-window tip speed | 0.019585799995396225 m/s | 0.02 m/s |

All other original acceptance components passed, including complete execution, sampled coverage, evaluator validity, zero solver errors and force bounds. This is one nominal sampled-task pass; optimality, robustness, repeatability and hardware performance were not assessed or required.

The exact [accepted solution index](../../evidence/s12_mirror/accepted_solution.json) points to the complete [structure?control package](../../evidence/s12_mirror/study/design_package.json), including candidate parameters, effective configuration, the complete 35?4 tension schedule and original acceptance. The immutable Store artifacts and original model reasoning are retained in the [archive manifest](../../evidence/s12_mirror/study/archive_manifest.json).

- Study: `s12-mirror-live-20261020`.
- Frozen scientific implementation: `a65dc0381573dacea693aebf16d15d8cf1d4c6e7`; separately pushed binding/authorization record: `6591d21802869175e245e9ad7529de15488365be`.
- Frozen resolved configuration: `b47ea80aa1a04c7ad6ac4894a334cb6d489ca29f560441cd7b5ede4d9a174e53`.
- Canonical task: `d24aeac7041052ce1d2ae60e825a802e7367107784f6fec192b0a65c4a5e76e7`, target `[0.29,-0.035,0.19]` m.
- Exact accepted evaluation: `72a0334662dddb2ce4a75460c6d0381795ae868014196f66f14da22c8c65ff1e`.
- Candidate: `5f6f99b6c44900c0868942d35ce39eab45df2f2e6f168e92184036993b1e241b`.
- Applied control source: `b06959b4a5affbfe566b3256575893ef34b465ddab1454a0b1376dddfe29adea`.

## A. Real decision-capability validation

Three authentic S11 cutoff packets were used: sequence 34 (historical near-success starting evidence), 319 (fresh failed replay available), and 450 (five Provider requests remain, four protected). The [frozen cases](../../evidence/s12_decision_probe/frozen_cases.json) and [wire manifest](../../evidence/s12_decision_probe/wire_manifest.json) preserve exact identities. Hash-verified in-memory snapshots contain only artifacts transitively reachable from inputs/outputs published up to the cutoff. Final-state lists are filtered to that subset; a regression proves the future fresh replay is inaccessible at the first cutoff. Original sealed Studies are unchanged.

Each state had one actual response under the original S11 interface and one under the S12 interface, with the same model/settings, task, evidence scope, underlying capabilities and budget. Conversation history was omitted identically in both arms. These are six new single-turn decisions, not recycled historical model outputs or a full-session randomized trial.

| State | Real S11-interface proposal | Real S12-interface proposal |
|---|---|---|
| Historical start | Response control search, 36 evaluations; checked contracts/references pass | Response control search, 20 evaluations; rejected for extra top-level `hypothesis_id` |
| Fresh physical failure | Exact physical replay, 1 evaluation; checked contracts/references pass | Cold offline NLP, 1 solve; checked contracts/references and warm-source checks pass |
| Last pre-protection request | NMPC execution; rejected by post-charge budget protection | STOP, zero scientific budget; checked contracts/references pass |

The checked scientific-proposal pass counts were 2/3 for S11 and 1/2 for S12; the S12 STOP is separate from scientific actions. **Full scientific execution admission remains `not_tested` in these probes.** Type/reference checks are not represented as completed solver preflight. All actions were intercepted; no scientific dispatch, callback, fabricated success or sealed-state write occurred. No evidence-read request was selected in these six turns. No unregistered scientific citation was detected in the checked typed proposals; reference validation of the malformed proposal was not reached.

Actual costs: S11 arm **82,374 tokens**, S12 arm **81,290**, total **163,664**, exactly six Provider requests. The separate existing Store ledger had zero tool/backend/worker allowance and zero scientific use. Original request/response bytes, metadata, receipts and usage are retained in [provider_receipts.json](../../evidence/s12_decision_probe/provider_receipts.json); [summary.json](../../evidence/s12_decision_probe/summary.json) separates partial admission, costs and limitations. First research proposal occurred on request one in every arm; first fully admitted scientific execution is not tested.

The protection-boundary sample supports correctness of that displayed boundary; the malformed S12 proposal prevents any blanket claim that all decisions improved. Scientific method quality was not judged by matching a predetermined choice.

After the six frozen requests, final formal source also retained diagnostics on historical `best_valid`, and formal instructions clarified the existing location of `decision.hypothesis_id`. No probe wire was changed or resampled, and no unexecuted proposal was imported as scientific history.

## B. Minimal repairs and validation

Production diff against baseline `25e1c889`: **+74/?19, net +55 lines**, across three existing modules. There is no new production module, Planner, Store, ledger, evaluator, solver or controller. ResearchDecision and Plan remain the formal decision contracts.

| File | Functions | Actual change |
|---|---|---|
| `tools/research/agent.py` (+1/?1) | `converse.before_model` | Reuse `next_request_will_protect` to apply existing closeout schemas before the charged request; retain exact saved-request restoration before this projection |
| `tools/research/mechanics.py` (+17/?15) | `warm_start`, `dispatch` | Extract and reuse original warm-source eligibility without changing its admission rules |
| `tools/research/research_context.py` (+56/?3) | `physical_diagnostic`, `context`, `action_feedback`, `decision_brief`, `tool_feedback` | Existing task-adapter violation extrema and terminal samples, original acceptance and sampled input bounds, exact raw pointers and owning Study; cold/warm prerequisites; post-charge actions; correct `/result` wrapper fallback |

Diagnostics distinguish measured facts from an unproven cause. They neither change thresholds nor prescribe a scientific method. The original raw trajectory remains readable. Mathematics guidance exposes both cold modes and candidate-bound warm sources for stated defaults; missing warm evidence does not disable cold optimization. Full Plan/scientific preflight remains authoritative. Wrapper references remain retrieval-only and cannot become scientific supporting evidence.

[Final source regression](../../evidence/s12_decision_probe/formal_source_regression.txt): **104 tests, zero failures/errors, one existing opt-in integration skip**. Actual BeforeModel hook tests cover ample counts, the five/four boundary, existing protection, success awaiting SELECT, existing RL work, saved-schema restoration, and zero-Provider engineering mode. Existing confirmed-response replay plus the new unknown-send fixture verify no duplicate send and retained uncertainty charge. Other checks retain exact pointers, scientific-citation strictness, STOP coverage, numerical contracts and readiness semantics.

The [baseline regressions](../../evidence/s12_decision_probe/baseline_regression.txt) reproduce the original missing diagnostic, permissive boundary actions and wrapper pointer. A repeated test run exposed a fixed fixture grant identifier; the budget system correctly rejected it. The fixture now uses its unique directory identity. No ledger/registry entry was erased or reset; intermediate local commits retain the earlier failure.

Engineering [MATLAB readiness](../../evidence/s12_mirror/readiness/report.json) passed dependency, startup, gateway, `sqrt(4)` and shutdown. Its original [sandbox access failure](../../evidence/s12_mirror/readiness/sandbox_failure.json) was retained, and a separate permitted-access engineering session was used. [Preflight](../../evidence/s12_mirror/preflight.json) constructed the direct PPO environment (48 DOFs, four 0?8 N actions, 107 observations, 35 intervals) and checked mathematics/NMPC admission without training, rollout or optimization. Readiness is not counted as scientific success.

## C. Real autonomous Study and evidence chain

[Original requests/feedback](../../evidence/s12_mirror/decisions.json) and [decision chain](../../evidence/s12_mirror/feedback_decision_chain.json) preserve exact hypotheses, selected variables, budgets and errors.

| Decision | Actual action and allocation | Observed result |
|---|---|---|
| Static-target hypothesis | Submitted `mechanics`: cold `ramp_0_2_to_0_4`, `task_gap`, 120-iteration cap, 1 NLP | Dynamic trajectory optimizer converged in 33 iterations; mathematical conclusion remains inconclusive and physical acceptance unmeasured |
| Transfer mathematical schedule | `initialize_control` baseline, explicit 35?4 inputs, zero physical allocation | Registered unmeasured source `b55bd800?` |
| Attempt independent validation | Three rejected `physical_replay` proposals | Missing payload, extra action payload, then unsupported inference declaration; no physical start for these rejected requests |
| Corrected validation | One actual fixed-input MuJoCo replay | Complete valid failure, normalized gap 44.834538263 |
| Revise method after failure | Response control search from historical source `62ddc238?`; 40-evaluation cap, three knots `[0,0.175,0.35]` s, full window, 12 tension-offset coefficients, limit 2.5 N, difference step 0.02 N, initial radius 0.3 N, three iterations | 27 callbacks: one historical cache baseline, 24 new finite-difference probes and two new response proposals; 26 fresh physical runs. The second response proposal was the first complete original-task pass |
| Close success | Read exact acceptance, then native SELECT, zero new science | Selected `72a03346?`; no additional exploration |

The Agent's first `selected_method` text says static equilibrium, but its submitted action/payload executed **dynamic offline NLP**, not a new static-equilibrium analysis. This mismatch is retained and corrected by the audit. The corrected replay's decision requested budget zero even though its actual backend start was correctly charged once by the original ledger. Decision prose and requested labels do not override actual receipts.

The Agent demonstrably revised from mathematical trajectory transfer to **measured response search after physical failure**. It used the historical near-success control as the search baseline rather than treating the failed mathematical schedule as physical evidence. This is an observed strategy revision, not a universal scientific-policy result. There were three executed high-level scientific calculations (NLP, replay, search), one separate seed-construction decision, three rejected replay proposals and one SELECT. Queries, optimizer probes and SELECT are not extra high-level scientific decisions.

The selected design retains the imported two-segment, four-tendon geometry: segment lengths 0.195 m and 0.11 m with the exact section/material/routing parameters in the package. No structural modification, NMPC, PPO training, BDF or new equilibrium/sensitivity analysis occurred. The actual solution is a newly evaluated bounded 35?4 open-loop control on that geometry; sampled applied inputs ranged from approximately 0.09911 N to 8 N. No extra safety margin is claimed.

The [search reconstruction](../../evidence/s12_mirror/search_reconstruction.json) reconstructs every callback's applied input array, selected dimensions and window behavior without physics. [Independent checks](../../evidence/s12_mirror/final_artifact_checks.json) verify every original fixed-input evaluator/profile/acceptance result, request and response hashes, native tool pairing, all settled receipts, zero pending/unconsumed outcomes, all 545 archive members, credential absence and unchanged scientific source/task/history. [Success-gate audit](../../evidence/s12_mirror/success_gate_audit.json) proves the selected run was the first pass and last physical run, followed only by evidence reads and native SELECT. Audit computation launched no new scientific experiment.

## D. Actual Provider efficiency and resource use

| Same historical accounting convention | S10 formal | S11 formal | S12 formal |
|---|---:|---:|---:|
| Provider requests | 29 | 30 | 22 |
| Prompt tokens | 1,706,805 | 1,767,033 | 1,557,945 |
| Completion tokens | 47,544 | 70,152 | 52,961 |
| Actual total tokens | 1,754,349 | 1,837,185 | 1,610,906 |
| Model tool requests | 54 | 57 | 32 |
| Evidence reads | 48 | 51 | 22 |
| Tool errors | 6 (11.11%) | 4 (7.02%) | 4 (12.50%) |
| Provider requests through first successful scientific calculation decision | 6 | 19 | 5 |
| Provider requests before first physics, existing convention | 6 | 19 | 18 |
| Executed high-level scientific calculations | 3 | 1 | 3 |
| Fresh physical evaluations | 20 | 1 | 27 |
| New mathematics | 1 analysis | 0 | 1 offline NLP |
| Original task accepted | No | No | Yes |

S12 formal tokens were 226,279 (12.32%) below S11. Evidence reads fell, but the error rate was higher and first physics remained late (358.522 s from the first request under the existing audit convention), including real NLP computation. Different historical starting evidence and one run per configuration prevent a causal claim about interface quality or general method superiority. The first scientific calculation metric includes successful tool execution, not physical acceptance.

The separate six-request decision probe cost **163,664** tokens. S12 probe plus formal usage totals **28 requests / 1,774,570 actual tokens**; do not omit the probe cost or confuse it with the formal 32-request allowance. Offline tests/readiness/audits used no real Provider requests. Currency cost is unknown.

| Frozen formal allowance | Actual used | Remaining |
|---|---:|---:|
| Provider 32, including 4 protected | 22 | 10 |
| Public operations 160, including 12 protected | 58 | 102 |
| Shared physical starts 64 | 27 | 37 |
| Mathematical analyses 4 | 0 | 4 |
| Offline NLP 1 | 1 | 0 |
| BDF 2 | 0 | 2 |
| NMPC 2 | 0 | 2 |
| PPO stages 1 / actions 65,536 / independent evaluations 1 | 0 / 0 / 0 | 1 / 65,536 / 1 |

Public operations include internal physical calls; the 32 original model tool requests have a different denominator. No budget extension, reset, transfer or protected-exploration bypass occurred. The run ended on success rather than resource exhaustion. [Provider comparison](../../evidence/s12_mirror/provider_comparison.json) retains the original count conventions and exact first-calculation event indices.

## E. Cross-task preparation after sealing

The post-Study read-only audit found **no active registered `task.tracking` or tracking evaluator**, despite residual branches mentioning them. Current reference/reporting/validity/search/RL paths also contain reach-specific assumptions. The absence is recorded rather than hidden with a fabricated evaluator.

The [S13 minimal plan](s13_cross_task_plan.md) identifies reusable transport/Store/budget/evidence/input-parameterization mechanisms, concrete reach dependencies, and four separate adapter capabilities: independent hard acceptance, measured violation feedback, optional search representation, and mathematical applicability. It retains TaskDefinition and the existing adapter; it does not impose a common smooth objective or weighted loss.

Tracking remains a candidate second task only after an authoritative task/evaluator definition and validation are restored or explicitly specified. Conditional adapter integration is estimated at 130?215 production lines across existing files, excluding that missing task-owner implementation; start with complete fixed-input evaluation and optional pattern search, retaining honest unsupported gates for methods lacking their prerequisites. No cross-task experiment or post-freeze production refactor occurred.

## Authorization, versioning and reproduction

Automatic approval initially rejected DeepSeek transfer and ordinary push. Those exact refusals were retained. The user subsequently explicitly authorized the stated research-data scope to `https://api.deepseek.com` (6 probe + 32 formal ceiling) and ordinary pushes to `github.com/wran021004-gif/softrobot-agent`, branch `feat/sorosim-matlab-nmpc`. Execution proceeded only after that authorization. No workaround, force push or history rewrite was used.

All work is confined to the designated checkout. S7?S11 sealed results, scientific solvers, physical scene, task/evaluator thresholds and original design domains are unchanged. The implementation remained frozen during formal research and afterward. API credentials were loaded through the existing loader and excluded from request/response artifacts and commits; configured-key scanning found zero matches.

The existing environment is `.mainline5-env`, with the already installed MATLAB Engine and pinned SoRoSim paths and the original single-thread settings. The original CLI was used:

```text
python -m tools.research prepare --spec configs/research/study_s12_mirror.json
python -m tools.research bind --run-id s12-mirror-live-20261020
python -m tools.research run --run-id s12-mirror-live-20261020
python -m tests.research.s9_audit s12-mirror-live-20261020 evidence/s12_mirror --export
python -m tests.research.s12_audit --final
```

The original CLI exited zero. The completed run is sealed: restore/read its evidence rather than repeat science or reset its counts. Independent audits recompute recorded-array acceptance and hashes only.
