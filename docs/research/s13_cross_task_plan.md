# S13: minimal second-task preparation after the accepted S12 archive

This audit was performed **after** S12 stopped with native SELECT, was archived, and passed independent verification. S12 remains bound to `a65dc0381573dacea693aebf16d15d8cf1d4c6e7`. No production source was changed after its freeze, and no cross-task scientific run was launched. Registry results are recorded in [cross_task_inventory.json](../../evidence/s12_mirror/cross_task_inventory.json); the existing unsupported-search/no-fallback regression passed in [cross_task_readonly_tests.txt](../../evidence/s12_mirror/cross_task_readonly_tests.txt).

## 1. Finding: tracking is not currently an executable second task

The actual active registry, assembled by `tools/platform_registry.py:registry` from `extensions/tendon_family/manifest.py`, contains only `task.reach@1.0.0` and `evaluate.reach@1.0.0` for task/evaluator kinds. Looking up `task.tracking@1.0.0` raises `IMPLEMENTATION_REQUIRED`. There is no registered tracking goal/evaluator contract or executable tracking task file in the present tree.

Remaining branches mentioning tracking do **not** establish support:

- `ResearchTaskAdapter.reference_at` unconditionally reads `goal.data.target_m` and returns zero reference velocity; `describe` calls this path through `operating_point`.
- `analysis_requirements` explicitly retains a non-reach task as an unsupported requirement; this honest rejection should remain until a validated translation exists.
- `violation_samples` returns unsupported for non-reach tasks. `holding_start_s` and `ranking_limits` require reach settling parameters.
- `tools/research_tasks.py:_protocol_requirements` recognizes only `offline_reach_hold_v1`. The partial `assemble_acceptance` tracking branch and tracking aggregation metric names do not supply the missing validated protocol.
- `extensions/tendon_family/gvs_reporting.py:summarize` and `reconstruct_motion` hard-code `tracking=False`, a constant position target and zero reference velocity despite outer tracking branches. `scene.py` retaining a `time_reference` branch is insufficient.
- Fixed-tension recovery in `tools/research/physical_replay.py:recover` directly invokes `evaluate_reach`, reconstructs only the tip-position signal, and builds a reach holding profile.
- `tools/rl/env.py:TensionEnv` explicitly accepts reach-and-hold only. No tracking PPO capability should be advertised from this audit.

Therefore **tracking remains the preferred candidate to investigate**, but cannot be described as an existing validated executable task. First recover an authoritative, versioned tracking definition/evaluator and its tests from legitimate project history, or obtain an explicit new task specification. Do not invent interpolation, tolerances, scored windows, channel limits or success semantics merely to make preflight pass.

## 2. Reuse and task dependencies

| Area | Reusable now | Dependency to keep in the task adapter or owner |
|---|---|---|
| Provider/Strands, Store, transactional counts, immutable artifacts, receipts, recovery | Transport and accounting mechanisms | `agent` research packets are not entirely task independent; their context/actions still invoke task-specific code |
| ResearchDecision/Plan, candidate/source identities, evidence ownership and scoped citations | Existing contracts and admission framework | Task compatibility and mathematical applicability remain authoritative prerequisites |
| Input parameterization | `corrected_tensions`, `correction_basis`, bounded channels/time grids, `trust_radius` | A task must not alter actual force bounds, tendon order, sampling phase or horizon |
| Physical acceptance and recorded facts | Full backend execution, receipt binding, fresh-result selection, independent evaluator boundary | Current fixed-input result adapter directly uses the reach evaluator/holding profile |
| Feedback | Evidence links, validity vs acceptance distinction, ownership, provenance | `feedback.task_gap` explicitly requires three reach components and holding coverage; its RL branch is also reach-specific |
| Search | Callback execution, caching, finite shared allowance, multiple starts, success stop | Outer dispatch rejects non-reach; `make_start` builds target/holding limits. The search loop's response path calls reach `constraint_vectors` |
| Mathematics | Declared model assumptions, output identities, horizon/grid checks, explicit partial/unsupported results | Supported constraint kinds, operating references and solver assemblers; no automatic transfer from reach endpoint tools to tracking |

`control_correction.task_measure`, `fitting_residual`, `constraint_vectors` and `output_error_budget` encode constant 3-D tip target, terminal error, holding-window position, and absolute velocity relative to zero. Their mathematical claims must remain scoped. `constrained_response_step` supports blocks of 3-D norm constraints, not arbitrary task predicates.

## 3. Minimal common interface

Extend the **existing** `ResearchTaskAdapter`; retain the current `TaskDefinition` as the sole specification. No new TaskSpec hierarchy, registry, evaluator framework or Planner is needed. Four distinct capabilities are sufficient:

1. **Acceptance requirements and independent evaluation binding.** Declare the registered evaluator, required validity/coverage components, exact sampling/frame/unit/channel meanings, and protocol version. The original evaluator alone determines success. Task identities, historical ownership, physical freshness and complete execution remain independent gates.
2. **Violation facts.** Map authoritative failed constraints to measured extrema and exact evidence pointers. Missing observations return unsupported/unavailable. Do not manufacture causes or prescribe the scientific next step.
3. **Optional search representation.** A task may expose compatible normalized norm blocks or an optional residual and its scope. Pattern search needs validity, original pass/fail and an explicitly declared comparison rule; it does not require differentiability. If no graded objective exists, retain feasibility-only comparison rather than inventing a weighted loss. The response method needs aligned perturbation outputs and compatible constraint blocks. Discrete predicates can remain outside this method.
4. **Mathematical applicability.** Translate only constraints supported by the requested tool. Keep exact reference/time scope and explicit unsupported/partial results. Static target authority is not tracking feasibility; a mathematical result is never physical acceptance.

An eventual timed-reference accessor must reuse the authoritative task's interpolation/sampling owner and return position/velocity only when those quantities are actually defined. Tracking must not inherit a zero absolute-speed holding constraint. Max error, RMS error and terminal error, if part of the authoritative task, keep their distinct original meanings; averaging must not erase a hard maximum violation.

## 4. Smallest implementable S13 sequence and code estimate

**Prerequisite gate (required before implementation):** locate or explicitly specify and validate tracking goal/evaluator semantics. Current read-only inventory fails this gate. This work is a task-owner contract/evaluator restoration, not an interface-only refactor; its size cannot be promised from the absent implementation. No estimated integration size below includes manufacturing a new physics evaluator.

Once that gate passes, begin with complete fixed-input MuJoCo evaluation plus optional pattern search. Keep NMPC/NLP/response search/PPO unavailable for tracking until their actual requirements are met. Do not require every method or every task to share one smooth objective.

| Existing file | Minimal integration | Indicative production change |
|---|---|---:|
| `tools/research_tasks.py` | Task-owned reference/coverage/violation and optional search-block methods; explicit protocol requirements | 45–70 lines |
| `tools/research/feedback.py` | Consume adapter validity and available comparison components without requiring three reach fields | 15–25 lines |
| `tools/research/physical_replay.py` | Delegate registered evaluation/profile translation to the adapter; retain launch/accounting/receipts | 20–35 lines |
| `tools/research/research_context.py` | Use advertised task capabilities and exact supported diagnostics | 10–20 lines |
| `tools/research/local_control_search.py`, `control_correction.py` | Pass task-owned comparison and optional norm blocks; keep current reach numerics/interpretation intact | 30–45 lines |
| `tools/research/task_constraints.py` | Capability translation only where the restored task really supplies supported constraints | 10–20 lines |

Indicative **130–215 production lines** for integration after the missing task semantics/evaluator exist, plus focused tests; no new production subsystem. Reporting/NMPC/PPO work is separate and should remain out of this first slice if it is not needed for fixed-input evaluation. The estimate is conditional, not evidence of current executability.

Required tests: original reach fixtures unchanged; authoritative tracking evaluator fixtures pass; inclusive scored position grid and pre-step tension grid preserve original rules; absent/invalid samples and wrong channels fail; timed reference does not become a constant target; task acceptance remains separate from optional search scores; unsupported response/mathematical methods stop before scientific execution; candidate/source/task identities and budgets remain bound. Only after these checks should a new separately authorized, frozen finite Study be considered.

No production refactor was needed for this planning deliverable. Nothing in this document is claimed to have participated in S12 science.
