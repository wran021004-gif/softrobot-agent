# Milestone 4 development campaign, 2026-10-04

Milestone 4 is now **closed**, after the explicitly authorized linked continuation. The first Milestone 5 pilot also completed, with an **inconclusive** direction/ranking result; Milestone 5 as a whole remains open. The current delivery is [delivery.json](../evidence/milestone45_continuation_20261004/delivery.json). The original stopped campaign and its evidence below remain historical records.

The continuation reused the shared immutable planner, candidate builder, verified-evidence importer and receipt executor. Before a new provider request, focused checks verified the actual execution-child projection, serialized current planning schema, final-feedback bindings and structure-to-adaptation transition. Its fresh ledger was limited to the reconciled remainder of the original grant, with an explicit predecessor-state/usage binding. No historical charges or stop states were reset.

The research model selected the earlier terminal-only result `50618bf23b31464ba4f84c55cd26d1ca` as the structural source, while the successful `a8382f8a4c6e4ebe921fb72f821b2188` remained available. The accepted plan changed only near length from 0.15 to 0.16 m, with holding/terminal weights fixed at 0/0.05. It gained joint sampled acceptance. A subsequent immutable adaptation batch fixed that structure and tested holding weights 0.05 and 0.10, retaining terminal weight 0.05. Both full simulations, evaluations and profiles completed. The 0.05 point preserved joint acceptance; the 0.10 point lost it through speed failure.

| Configuration | Near, m | Holding / terminal weight | Terminal error, m | Holding max error, m | Holding max speed, m/s | Joint acceptance | Mean update, s |
|---|---:|---|---:|---:|---:|---|---:|
| Retained baseline `cf997605...` | 0.15 | 0 / 0 | 0.007642609 | 0.058138104 | 1.581015274 | Failed | 17.263319 |
| Declared structural source `50618bf2...` | 0.15 | 0 / 0.05 | 0.008186891 | 0.008275123 | 0.035567308 | Failed | 16.876453 |
| Earlier successful control `a8382f8a...` | 0.15 | 0.05 / 0.05 | 0.008117263 | 0.008211990 | 0.018334515 | Passed | 17.258959 |
| New structure `bebcfd47...` | 0.16 | 0 / 0.05 | 0.002705005 | 0.002736842 | 0.012735678 | Passed | 8.342850 |
| **Selected adaptation `91c3ba1b...`** | **0.16** | **0.05 / 0.05** | **0.002697829** | **0.002730054** | **0.012750256** | **Passed** | **8.518061** |
| Other adaptation `110dc2c9...` | 0.16 | 0.10 / 0.05 | 0.002633323 | 0.002810910 | 0.022128675 | Failed | 8.642199 |

All configurations retain far length 0.11 m, section scale 0.95 and the compliant numerical material scenario. Controller implementation remains `controller.gvs_nmpc@7.0.0`. Terminal/holding position limits remain 0.01 m, speed limit 0.02 m/s, and the final sampled window 0.05 s. The selected configuration is `285236abf99bf36894fa08410ac82fefa177a80179c4ceba15d95f8d1bc8d978`, candidate `batch-ebbeadbdaca10732-0`, execution `91c3ba1b01d6499fb26df8f95409401b`. The latest execution is separately `batch-ebbeadbdaca10732-1`, not the selected deliverable.

The model selected the 0.05 adaptation for slightly lower terminal/holding errors, explicitly acknowledging slightly worse speed and timing versus the pre-adaptation configuration. This is a tradeoff, not dominance. It improves all three physical metrics against the earlier successful control result and gains joint acceptance against the declared source and retained baseline. All new runs recorded 35/35 deadline misses; real-time feasibility remains undemonstrated. They had zero force-bound violation and zero solver errors.

The [prospective pilot](milestone5.md) was frozen before either adaptation backend. Three independent local controller attempts and three short rollouts selected the same settled seed; the research model abstained on full-task direction, ordering and absolute acceptance. Actual evaluations exposed different outcomes, including acceptance loss at 0.10. The final model decision retained full evaluation as necessary.

| Resource | Historical | Continuation | Combined / ceiling |
|---|---:|---:|---:|
| Provider attempts | 11 | 8 | 19 / 24 |
| Workflow tools | 14 | 23 | 37 / 60 |
| Full backend attempts | 1 | 3 | 4 / 4 |
| Charged seconds | 932.172 | 1298.035 | 2230.207 / 9000 |
| Workers | 0 | 0 | 0 / 0 |

Protocol corrections: historical 4, continuation 0, lifetime 4; the continuation allowance was four additional corrections, at most two consecutive. Three separate scientific/status correction requests consumed ordinary provider/tool/time capacity. The continuation performed 105 embedded controller updates, separately from three additional local attempts and three short predictions. Unused capacity was not spent after delivery.

Concrete engineering interventions preserved their failures and charges: extend the existing compatibility review to the accepted control execution; populate the reused summary's authorization lineage; fix duplicate-key export construction; compact repeated structural/pilot data under the existing payload guard; bind latest execution to receipt chronology instead of artifact hash ordering. Sealed structural/adaptation results were interpreted without backend replay. Original model prose was preserved and corrected by the model for a false structural-confounding caveat, omitted sequence/pilot interpretation, and stale pending-candidate language. No model conclusion was edited into a replacement scientific result by an engineer.

Implementation checkpoints were `b41fd3b`, `0ef5cf4`, `6bdf312`, `4cb9006`, `4bf10ea`, `97f1064` and `58d25e5`. Final evidence is committed locally; no push, new paired comparison, new controller, extra campaign, parameter sweep, dependency upgrade or MATLAB validation was performed. Milestones 2 and 3 remain closed.

## Historical stopped development segment

At the end of the original development segment, Milestone 4 was **incomplete and open**. The shared planning changes, one live control continuation, and structural interfaces passed their checks. The changed-structure execution, adaptation on that structure, and final model decision for the entire sequence did not run. The campaign stopped at its four-protocol-correction ceiling after a host policy projection defect advertised no planning tools. The repaired projection passed a focused offline check; no additional provider request, budget reset, or replacement campaign followed within that historical segment.

The authoritative delivery is [delivery.json](../evidence/milestone4_20261004/delivery.json). This is a development result under the user’s cumulative grant, not a successful completion of Milestone 4.

## Scope and gates

| Gate | Evidence | Status |
|---|---|---|
| Accurate shared research state and executable model plan | Six verified historical configurations, dynamic branch summaries, explicit source and predecessor, actual differences, computed budgets, accepted control plan | Passed |
| One complete control continuation and accurate interpretation | Sealed simulation, evaluation, profile, source/baseline comparisons, corrected model decision | Passed |
| Four structural decisions in shared batch workflow | Length, absolute common scale, numerical material scenarios, discrete enumeration, reconstruction/ownership and stale-reuse checks | Offline passed |
| One fully evaluated changed structure | Far length 0.12 m appeared in rejected model prose; no accepted executable plan or new execution | Incomplete |
| Control adaptation on new structure | No newly evaluated structure available | Incomplete |
| Final model decision for complete sequence | Last accepted decision closes the control substage only | Incomplete |

Milestones 2 and 3 remain closed. Their failed proposals, unknown operations, charges and accepted interpretations were preserved. The historical 900-second unknown reservation is reported as historical information, not transferred or replayed in this project.

## Shared implementation

`tools/study_history.py` projects verified candidate/configuration/execution identities, physical and control decisions, metrics, references, and execution status. Completed, incomplete and proposed records have distinct statuses; tested branches are computed from completed evidence. Retained baseline, selected study source, latest tested and selected deliverable are independent.

`tools/batch_budget.py` provides the shared reservations: simulation 900 s, evaluation 30 s, profile 60 s, protected interpretation 600 s/four model/four tool calls, and planning one model/one tool. Semantic structural batches additionally reserve 5 s per candidate for charged preparation. A one-result structural batch therefore requires 1,595 s, five provider attempts, nine workflow calls and one backend attempt. Actual candidate reconstruction time is included in the existing apply-stage accounting.

`schemas/parameter_domains.py`, `schemas/platform_handoff.py`, and the existing explicit search adapter support continuous ranges and discrete choices. Archived numeric ranges remain accepted. Discrete material labels use finite enumeration and are rejected by continuous coordinate search. The receipt-backed executor remains the existing implementation.

`tools/candidate_parameters.py` resolves source values and actual changes, masks declared changes for fixed-field validation, and separates common-task comparability from exact execution reuse. Full configuration/execution bindings remain required for reuse. The four structure decisions and two demonstrated speed weights are the only added study dimensions; acceptance, timing, task/environment, force limits, routing, topology, implementation and undeclared settings remain fixed.

`tools/structural_study.py` freezes the new controller-7 capability profile. It preserves the historical multiphysics controller-6 profile. Section scaling and Young-modulus scenarios remain absolute relative to original semantic source identity `03f948b02a2f0b9eb368bdc3fb34e6c9575ede4334c118384652b339f7c357b4`; repeated continuation does not compound them. Material options are numerical scenarios, not identified commercial materials. Compatible historical tensions remain guesses, with candidate-specific state regeneration; no equilibrium or separate mathematical solve was added.

The research planning projection now preserves the source’s scientific scope while restoring the authorized planning model/budget/tool bindings. A payload guard verifies that its native handoff is advertised before any provider attempt. The exhausted campaign guard prevents replacement requests after the recorded protocol stop.

## What actually ran

The model’s accepted control plan selected predecessor execution `50618bf23b31464ba4f84c55cd26d1ca`, despite Stage 3.59 being the latest historical result. It varied holding speed weight from 0 to 0.05 and kept terminal speed weight at 0.05. One exact finite candidate was executed:

- Candidate `batch-9293a74b063bb9a0-0`.
- Execution `a8382f8a4c6e4ebe921fb72f821b2188`.
- Configuration `10ab5d77921b1a45beed67cc0ec9769d96282923ef1078409c22f36ec1d72a4f`.
- Structure unchanged: near 0.15 m, far 0.11 m, common scale 0.95, compliant numerical material scenario.
- Retained baseline remains `cf997605885642759ee33920e2c9e2ef`.

| Configuration (holding / terminal) | Terminal error, m | Holding max error, m | Holding max speed, m/s | Joint sampled acceptance |
|---|---:|---:|---:|---|
| Retained baseline 0 / 0 | 0.007642609 | 0.058138104 | 1.581015274 | Failed |
| Declared source 0 / 0.05 | 0.008186891 | 0.008275123 | 0.035567308 | Failed |
| New candidate 0.05 / 0.05 | 0.008117263 | 0.008211990 | 0.018334515 | Passed |

Frozen limits are terminal and holding position 0.01 m, holding speed 0.02 m/s, and the final sampled 0.05 s window. All three physical metrics improved against the declared source. Against retained baseline, holding metrics improved but terminal error increased by `0.0004746544442497391 m`, remaining within tolerance. The corrected model adopted the new control candidate without replacing the retained baseline identity.

Mean complete update was `17.258959311459744 s`, with 35/35 misses against a 0.01 s deadline. It was 0.382506692 s slower than the source and 0.004359737 s faster than retained baseline. Real-time feasibility was not demonstrated. The run had zero force-bound violation and zero solver errors. Sampled acceptance, physical tradeoffs and measured timing are reported separately.

The structural responses proposed far length 0.11 → 0.12 m using this control candidate as source. They contained no native tool call and did not match the executable SearchBatchPlan schema. They remain rejected, unexecuted proposals; no performance metrics or structural success are assigned to them. There was no adaptation batch, baseline rerun, diagnostic sweep, benchmark, or worker.

## Costs, corrections and interventions

Project `gvs-milestone4-e117fbe28995` used **11/24 provider attempts, 14/60 workflow tools, 1/4 backend attempts, 932.1719999995548/9,000 charged seconds, and 0 workers**. All receipt counts and wall charges reconcile with the cumulative ledger; no reservations remain occupied. Unspent capacity remains recorded, but cannot justify exceeding the recovery ceiling. Provider configuration remains the existing DeepSeek Flash endpoint, high reasoning, verified TLS and preserved token/context settings. No separate provider preflight was bought.

There were four scheduled protocol corrections in total, with final consecutive count one and no total-counter reset. Three arose from missing final host feedback context; the fourth arose from the zero-tool structural planning context. Three initial business validation failures also remain recorded. Comparison and future-budget semantic corrections consumed ordinary provider attempts and remain in the same ledger.

Engineering interventions were explicit:

1. Correct downstream capacity validation to use project/session capacity rather than the planning phase’s local allowance; revalidate the unchanged saved control plan.
2. Restore final feedback bindings; seal the saved interpretation, then obtain corrected comparison and next-budget statements without replaying the simulation.
3. Repair typed structural projection, absolute semantics and temporary-store fixture cleanup. An accidentally created empty fixture session in the campaign store is retained, marked excluded/stopped, and has no provider/backend charges.
4. Repair the research host’s inheritance of the execution child’s zero-model budget, then identify and repair its execution-only tool bindings. Two structural provider responses were paid before the latter was caught; both remain preserved. The final repair was checked offline only because recovery was exhausted.

The host binding defects were implementation errors, not evidence that the proposed structure or control method is physically impossible. Their charges were not erased or reclassified as free work.

## Verification, provenance and commits

[offline_verification.json](../evidence/milestone4_20261004/offline_verification.json) records the focused checks. Single-context received the new live validation. Single- and dual-context consumers share the tested public interfaces; there was no new paired comparison or dual-model advantage claim. Section scale and material choice have offline support only. No structural parameter category received new live validation.

The evidence directory includes immutable plans, prelaunch review, exact inputs/outputs, sealed configuration and backend/evaluation/profile artifacts, comparisons and SHA-256 manifest. `single_context/campaign_receipts.json`, `campaign_raw_calls.json`, `campaign_resolved_calls.json` and `campaign_contexts.json` cover every project context, including engineering continuations and failed attempts; these supplement the inherited exporter’s current-host-only views. Missing historical external references are listed explicitly.

Local checkpoints: `31be1fe` shared planning; `9910b35` downstream capacity; `1fb8d5d` final feedback; `5fecb0d` preserved semantic corrections; `e96a05c` shared future-budget guard; `86140b0` typed structural workflow; `9e9a878` planning allowance; `b8cbac5` offline planning-tool repair and strict correction stop. The final evidence commit is identified in the delivery response. No push was performed.

Milestone 4 cannot be marked passed on these records. Any further live structural/adaptation work requires renewed authorization that explicitly addresses the exhausted correction allowance; the current campaign is not automatically resumed.
