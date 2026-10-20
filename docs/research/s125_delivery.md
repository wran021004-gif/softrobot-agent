# S12.5 — cold-start autonomous research and decision efficiency

Status: engineering validation and all ten authorized paired decisions completed. The formal Study is admitted and awaiting its source/Store binding. Its outcome remains unmeasured.

## A. Cold-start boundary

The target branch was fetched and both local and remote HEAD matched `174cd8c04ede5058cb78ffd91a45fb43f5399cec`. The original target worktree was clean. All changes are confined to `feat/sorosim-matlab-nmpc`.

`configs/research/study_s125_cold.json` uses the existing family-space initializer, original `reach_hold_mirror_v1` task and unchanged `family_space_s7.json`. History, mathematics, control seeds and supplied evidence are empty; `require_task_guidance=false`. The proposed formal ID is `s125-cold-live-20261020`; its Store and Strands session will be created only after the admission gates and source commit.

[Cold-start preflight](../../evidence/s125_preflight/cold_start.json) verifies an empty candidate pool, no reference candidate or best result, no imported mathematics/controls, and a separate session with no saved conversation. The compatibility scaffold is explicitly not a scientific candidate. An old S12 artifact fails the new Store's lookup. A disposable engineering candidate can be generated, initialized with the existing baseline control, and admitted for cold mathematics without warm evidence. It is never an input to the formal Study.

`Store.artifact()` queries the current Store database and validates content identity. Formal Agent tools do not expose arbitrary filesystem reads. `experience_retrieve` was already blocked by the formal tool hook and is now omitted from new formal requests; original saved requests retain their schemas. Strands Offload retrieval belongs to the new framework session, which has no previous Study history.

Cold-start means no prior experimental observations or solutions, not absence of human knowledge. Frozen family parameter bounds/defaults, material and section models, assembly prototypes, connector/guide/payload properties, tendon routing rules, force bounds, discretization and controller defaults remain declared design priors. These include defaults established during earlier engineering development. The engineering scaffold does not register a successful historical robot as a new candidate.

The task remains target `[0.29,-0.035,0.19] m`, duration `0.35 s`, control period `0.01 s`, physics step `0.0005 s`, terminal and holding position limits `0.01 m`, holding speed limit `0.02 m/s`, plus every original completeness, force, coverage and evaluator-validity component.

## B. Minimal interface changes

Production diff against `174cd8c0`: **+48 / −21, net +27 lines**, in three existing modules. No new production module, Planner, Store, ledger, evaluator, solver or scheduling system.

| Existing file | Functions and changes | Added / removed |
|---|---|---:|
| `tools/research/contracts.py` | `Plan.required()` shares payload ownership with its schema projection; `ResearchDecision.claimed_inference` explains experiment requests versus supported inferences | +12 / −7 |
| `tools/research/agent.py` | `plan_schema()` exposes only applicable payloads, enforces required non-null payloads and formal `decision`, retains optional diagnose/propose exceptions; `converse.before_model` projects current actions and removes unavailable experience retrieval after the saved-request recovery branch | +30 / −12 |
| `tools/research/research_context.py` | `compact_evidence()` supplies bounded exact child queries and deeper pointers; `decision_brief()` displays search-domain details once on control search, not again on physical replay | +6 / −2 |

Server-side strict Plan validation, scientific evidence identity/inference checks and budget admission remain authoritative. An invalid request is rejected, never rewritten. Legacy optional `diagnostic`, propose-with-`mechanics_source`, null unused payload serialization, SELECT/STOP and RL closeout remain supported.

The four exact S12 errors were reproduced from hash-verified archive records: sequence 75 nonexistent candidate fields; 252 missing `weakening_observation` (also missing replay payload); 264 missing `physical_replay`; 277 unsupported inference `physical_validation_of_exact_schedule`. Contrary to a loose description in the S12 report, sequence 264 contains a missing payload, not an extra candidate payload. The original requests and rejection references are in the [wire audit](../../evidence/s125_wire_audit/s12_requests.json).

[Regression result](../../evidence/s125_preflight/regression.txt): **62 tests, zero failures/errors/skips**. Coverage includes all Plan actions, required fields and illegal payloads, original archived errors, nested/escaped evidence paths, empty initialization, actual Strands HTTP serialization, budget/success/RL boundaries, exact saved-schema restoration, reasoning/tool IDs, confirmed-response replay and unknown-send blocking. Strands adds field descriptions during serialization; the test verifies all non-documentation schema constraints at the actual HTTP transport boundary.

The initial environment lacked MATLAB Engine on `PYTHONPATH`; using the installed engine path resolved that dependency check. A separate readiness attempt then failed because the sandbox denied MATLAB startup; [that original failure](../../evidence/s125_preflight/readiness.json) is preserved. The authorized access check [passed](../../evidence/s125_preflight/readiness_verified.json) dependency verification, engine startup, gateway, `sqrt(4)` and shutdown. Direct PPO environment construction passed with 48 DOFs, four actions, 107 observations and 35 control intervals. No rollout, training, optimization or scientific acceptance is claimed by readiness.

## C. Provider wire cost

All 22 S12 formal requests and their original usage were inspected read-only. Actual usage is **1,557,945 prompt + 52,961 completion = 1,610,906 tokens**.

| Disjoint canonical JSON component | Cumulative bytes |
|---|---:|
| Original historical reasoning | 1,733,626 |
| Historical tool results | 1,412,652 |
| Current research packet | 704,585 |
| Tools/schema | 692,033 |
| Other protocol fields/framing | 359,040 |
| Fixed instructions | 139,348 |
| Ordinary assistant text | 0 |
| **Total** | **5,041,284** |

These parts sum exactly for every canonical compact UTF-8 JSON request. They are not HTTP byte captures or token estimates. Assistant tool calls and JSON framing remain in the protocol bucket. Raw usage/cache fields are preserved; absent reasoning-token detail is `unavailable`.

Exact repeated parsed subtrees, counted without recursively recounting a repeated occurrence, are led by search `domain` (23,845 bytes), `unsupported_inferences` (12,616), `supporting_evidence` (7,854), `violated_constraints` (7,581), and `physical_diagnostic` (2,541). These are diagnostic repetitions, not additional disjoint request components or an estimate of safe total removal. No identical full message-content strings were found within these requests. Fixed instructions/schema necessarily recur across requests; their measured cumulative sizes are above.

Applying only the new schema/tool projection to the original 22 messages reduces cumulative schema bytes from **692,033 to 671,220** (20,813 bytes, about 3.0%). This is an offline projection, not measured token savings. The actual saved reasoning and conversation are unchanged. Dynamic system-state updates and historical reasoning remain substantial costs; this iteration does not implement session checkpoints or rewrite history.

Per-request byte partitions, original IDs/references, actual prompt/completion/total tokens, cache hit/miss fields, message counts and subsequent tool outcomes are in [s12_requests.json](../../evidence/s125_wire_audit/s12_requests.json). 

Per-request canonical bytes (ordinary assistant text is zero in every row):

| # / request suffix | Total | Fixed | State | Schema | Reasoning | Tool results | Protocol |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 / ead96eb0 | 72170 | 6334 | 30370 | 35107 | 0 | 0 | 359 |
| 2 / b853a379 | 86052 | 6334 | 30370 | 35107 | 3950 | 8564 | 1727 |
| 3 / 245f5df3 | 102169 | 6334 | 30370 | 35107 | 16215 | 11210 | 2933 |
| 4 / 7b1675bd | 105475 | 6334 | 30370 | 35107 | 16512 | 13607 | 3545 |
| 5 / dc93c0e2 | 118133 | 6334 | 30370 | 35107 | 17193 | 25206 | 3923 |
| 6 / db3deca7 | 177438 | 6334 | 30660 | 33384 | 71301 | 27580 | 8179 |
| 7 / 478fbb39 | 181190 | 6334 | 30660 | 33384 | 72097 | 29904 | 8811 |
| 8 / 00b353ac | 186742 | 6334 | 30660 | 33384 | 72545 | 34318 | 9501 |
| 9 / ed6b4cfe | 196082 | 6334 | 30660 | 33384 | 72930 | 42575 | 10199 |
| 10 / 450b817c | 240519 | 6334 | 30660 | 33384 | 75542 | 83579 | 11020 |
| 11 / cc187032 | 247238 | 6334 | 30660 | 33384 | 80076 | 84647 | 12137 |
| 12 / af45fe6b | 251600 | 6334 | 30660 | 33384 | 83448 | 84936 | 12838 |
| 13 / 4e1aebc2 | 254477 | 6334 | 30660 | 33384 | 83591 | 87319 | 13189 |
| 14 / 3b7cbdf2 | 268406 | 6334 | 30660 | 33384 | 94119 | 90063 | 13846 |
| 15 / 91657629 | 285255 | 6334 | 30414 | 33384 | 103976 | 91189 | 19958 |
| 16 / f912aa65 | 290180 | 6334 | 30414 | 33384 | 105372 | 91617 | 23059 |
| 17 / 8736b9f7 | 294011 | 6334 | 30414 | 33384 | 105421 | 92158 | 26300 |
| 18 / 298a1e11 | 301300 | 6334 | 30414 | 33384 | 109103 | 92669 | 29396 |
| 19 / 5126340e | 315439 | 6334 | 34947 | 33384 | 109891 | 98412 | 32471 |
| 20 / 902f6c39 | 343782 | 6334 | 40064 | 16374 | 139552 | 103865 | 37593 |
| 21 / d058f93a | 357719 | 6334 | 40064 | 16374 | 147100 | 109269 | 38578 |
| 22 / e20a2e0b | 365907 | 6334 | 40064 | 16374 | 153692 | 109965 | 39478 |

Actual Provider usage; cumulative totals count each request once:

| # | Prompt | Completion | Total | Cumulative total | Cache hit | Cache miss |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 21625 | 1356 | 22981 | 22981 | 0 | 21625 |
| 2 | 25430 | 3235 | 28665 | 51646 | 4224 | 21206 |
| 3 | 29477 | 257 | 29734 | 81380 | 4224 | 25253 |
| 4 | 30682 | 276 | 30958 | 112338 | 4224 | 26458 |
| 5 | 35395 | 14398 | 49793 | 162131 | 4224 | 31171 |
| 6 | 49962 | 363 | 50325 | 212456 | 3200 | 46762 |
| 7 | 51253 | 333 | 51586 | 264042 | 4096 | 47157 |
| 8 | 53362 | 318 | 53680 | 317722 | 4096 | 49266 |
| 9 | 56211 | 857 | 57068 | 374790 | 4096 | 52115 |
| 10 | 77605 | 1471 | 79076 | 453866 | 4096 | 73509 |
| 11 | 79341 | 969 | 80310 | 534176 | 4096 | 75245 |
| 12 | 80378 | 133 | 80511 | 614687 | 4096 | 76282 |
| 13 | 81433 | 2636 | 84069 | 698756 | 4096 | 77337 |
| 14 | 85265 | 5205 | 90470 | 789226 | 4096 | 81169 |
| 15 | 90677 | 1153 | 91830 | 881056 | 4096 | 86581 |
| 16 | 91942 | 860 | 92802 | 973858 | 4096 | 87846 |
| 17 | 92949 | 1693 | 94642 | 1068500 | 4096 | 88853 |
| 18 | 94788 | 1038 | 95826 | 1164326 | 4096 | 90692 |
| 19 | 98907 | 9193 | 108100 | 1272426 | 4096 | 94811 |
| 20 | 107164 | 2140 | 109304 | 1381730 | 1536 | 105628 |
| 21 | 110914 | 2036 | 112950 | 1494680 | 3328 | 107586 |
| 22 | 113185 | 3041 | 116226 | 1610906 | 3328 | 109857 |

## D. Paired decision probes

[Authorization](../../evidence/s125_preflight/external_authorization.json) explicitly allows ten isolated decisions plus at most 48 separate formal requests to `https://api.deepseek.com`; S12 authorization is not reused.

Five states are paired under S12 and S12.5 interfaces: empty cold start; a generated candidate with no control; real S12 failure at cutoff 299; real S12 mathematics before physical acceptance at cutoff 121; and five remaining requests with four protected. Each pair has the identical packet, accessible-artifact set, provider settings and budget. Cold-state candidates are engineering fixtures; historical states retain ownership and never enter the formal cold Store.

[Final frozen manifest](../../evidence/s125_decision_probe/wire_manifest.json) indexes raw wires and states in an isolated existing Store. A superseded, unsent manifest retains the initial offline projection before the last schema simplification; it consumed zero Provider requests. The live run uses only the final ten-wire manifest.

All scientific dispatch is intercepted. Results distinguish contract/reference checks from full scientific admission, which is `not_tested`; no fabricated scientific result is returned. One response per interface/state cannot establish statistical superiority or full-study success rates.

[Actual probe summary](../../evidence/s125_decision_probe/summary.json): ten HTTP 200 responses; **217,467 actual tokens**, zero backend/tool/worker charges, all receipts settled. S12 consumed 107,732 tokens; S12.5 consumed 109,735. New prompt tokens fell by 374, while completion tokens increased by 2,377; total cost therefore rose by 2,003 tokens (about 1.86%). No net token-efficiency improvement is established.

| Frozen state | S12 proposal | S12.5 proposal |
|---|---|---|
| Empty | generate; checked pass | generate; checked pass |
| Generated, no control | generate; checked pass | cold mechanics; checked pass |
| Fresh physical failure | execute NMPC; checked pass | four exact evidence reads; checked pass |
| Mathematics, no fresh physics | four evidence reads; checked pass | three evidence reads; checked pass |
| Next request protected | STOP; checked pass | STOP with unsupported `no_inference_stop`; rejected |

S12 had 8/8 checked proposals pass, including 3/3 scientific proposals. S12.5 had 9/10 pass, including 2/2 scientific proposals; seven of its proposals were evidence reads. Neither arm had a detected type/field/path error or attempted exploration across the protection boundary. The S12.5 error is an inference-admission failure, not a budget misjudgment. No rejected request was rewritten or resampled. Scientific proposals occurred on the first response where present; other single-response cases have no observed scientific proposal. Full scientific admission remains `not_tested` for every proposal.

The predefined formal gate concerns contract/server consistency, cold isolation, recovery, readiness, accepted Provider schema and explicit authorization; it does not require empirical superiority in this small sample. All gates passed, so the formal Study proceeds without increasing either budget.

## E. Formal Study

Not started at this report revision. The finite configuration is 48 Provider requests including four protected, 200 public operations including 12 protected, 64 shared physical starts, four analyses, one offline NLP, two BDF replays, two NMPC executions, one PPO stage/65,536 aggregate actions and one independent RL evaluation. No budget reset, increase, retry study or fixed scientific action sequence is permitted.

After the decision probes, the code/configuration/readiness gates will be recorded, committed and ordinarily pushed. The new empty Store will then be bound to the frozen source SHA before the first actual Provider request. The Agent chooses its own structures, controls, hypotheses, methods and finite allocations. First original-task success must stop exploration, be read exactly and selected; otherwise the original failure and stopping reason remain the result.

## F. Observational stage comparison

| Metric | S10 | S11 | S12 | S12.5 formal |
|---|---:|---:|---:|---|
| Provider requests | 29 | 30 | 22 | not started |
| Actual tokens | 1,754,349 | 1,837,185 | 1,610,906 | not started |
| Executed high-level scientific calculations | 3 | 1 | 3 | not started |
| Fresh physical evaluations | 20 | 1 | 27 | not started |
| New mathematical work | 1 analysis | 0 | 1 NLP | not started |
| Tool errors | 6 | 4 | 4 | not started |
| Evidence reads | 48 | 51 | 22 | not started |
| Requests through first successful calculation | 6 | 19 | 5 | not started |
| Requests before first physics, existing convention | 6 | 19 | 18 | not started |
| Original task passed | no | no | yes | unmeasured |

Historical counts use [the existing comparison](../../evidence/s12_mirror/provider_comparison.json). Different initial evidence and budgets prevent causal attribution. Genuine feedback-driven method revisions must be read from the decision chain, not counted from arbitrary changes in method text. Probe costs are reported separately from formal Study costs.
