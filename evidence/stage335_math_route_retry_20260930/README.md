# Stage 3.35 math-led Route retry

This directory separates the completed offline integration proof, the preserved blocked-launch record, and the one subsequently authorized live DeepSeek run.

## Actual live outcome

The retained session `gvs-stage335-81350ebec934` was verified before launch: every frozen-file digest matched, the explicit `softagent` Python 3.11 runtime matched, the implementation remained commit `28488eda598ad669cb5d610e370ff94bfee13e7e`, and the prepared counters were zero. The existing session was run once without recreation, retry, offline recomputation, budget increase, workers, or manual candidate selection.

The run ended `failed` with `DEEPSEEK_NETWORK_ERROR` after 23 provider requests, 18 charged tool calls, 16 live mathematical evaluations, 0 backend attempts, 0 workers, and 846.329 charged seconds. Together with the retained eight offline evaluations, cumulative Stage 3.35 mathematical evaluations were 24.

The model read the optimizer result and chose `math-compliant-4795c8184616`: near 0.15 m, far 0.11 m, section scale 0.95, compliant material. Both returned proposals tied on the primary local residual (0.002 m, 0.2 of tolerance); compliant had the lower secondary normalized input energy (4.367701514792259e-05 versus 8.463648352583415e-05). Its build used those exact values. The rationale correctly stated the local exact-ZOH applicability, zero world-x mapping row, and limitations.

Automatic report linkage nevertheless failed. The model supplied its build label `mathsel_c1_n0p15_f0p11_s0p95_compliant` as `selected_optimizer_candidate_id` instead of the optimizer's original ID. Route rejected the report with `ROUTE_SELECTED_OPTIMIZER_PROPOSAL_NOT_FOUND`; the next provider request encountered the network error, so the model could not correct the citation. There is no completed analysis report, backend execution, or provider-authored finish, and strict math-influenced-execution acceptance is false.

Robot outcomes are independently unavailable: no valid backend execution, no official reach result, no sampled 0.05 s settling result, and no complete-update real-time result. This is a report-linkage/provider-transport failure, not a robot-performance failure.

`actual_live_selection_review.json` separates the model's evidence-supported choice from the failed automatic linkage. `actual_live_outcomes.json` separates the three requested robot outcomes. `actual_live_manifest.json` identifies all compact review files. The raw SQLite store and full route status remain local-only and are identified by path, size, and SHA-256 in `actual_live_local_only_artifacts.json`.

## Original blocked-launch record

Before the user supplied the later explicit authorization, the live session had been frozen as `gvs-stage335-81350ebec934` against commit `28488eda598ad669cb5d610e370ff94bfee13e7e`. The external execution gate rejected that earlier paid DeepSeek command before the Python process started. No retry or workaround was attempted then. `live_blocker.json` and the original `live_*` snapshot remain unchanged as the historical blocked-launch record.

Usage for that earlier blocked launch was 0 provider requests, 0 tool calls, 0 mathematical evaluations, 0 backend attempts, 0 workers, and 0 charged seconds.

The original record also retains the push restriction that applied at that time. The user subsequently confirmed that the prior two commits were pushed successfully.

## Offline integration proof

The offline provider-format fixture passed the production DeepSeek function decoder and Host boundary. It advertised `route.record_analysis@1.0.0`, invoked metrics and endpoint tools with the returned candidate-linearization envelope, retained the original optimizer result, built an exact returned proposal, attached candidate-bound evidence, and passed the real execution gate without starting a backend. It used 8 cumulative mathematical evaluations, 0 provider requests, 0 backend attempts, 0 NMPC solves, and 0 workers. The scripted proposal choice is not evidence of LLM reasoning.

The first offline report call intentionally remains visible in `provider_fixture_trace.json`: the fixture supplied the outer Route result wrapper where the Route requires the build node result. The same store was resumed with that returned node reference. No optimizer evaluation was repeated and no counter was reset.

Run focused verification with the required interpreter:

```powershell
& 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe' -m unittest tests.test_task_analysis tests.test_math_analysis tests.test_stage335_math_route
```

Do not reproduce the paid live action during ordinary review. `offline_manifest.json` identifies committed files. `local_only_artifacts.json` identifies the raw local SQLite/artifact store by absolute path, size, and SHA-256 and explicitly does not claim remote availability.

The retained five-case MATLAB/SciPy acceptance evidence remains under `evidence/stage334_math_led_design_20260930/`; it was not recomputed for these narrow integration repairs.
