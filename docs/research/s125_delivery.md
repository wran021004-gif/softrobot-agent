# S12.5 — cold-start autonomous research and decision efficiency

Status: completed. Ten isolated paired decisions and one independent cold-start Study ran under the approved 10 + 48 request ceilings. The formal Agent used **46 requests / 4,418,691 tokens**, generated nine candidates, initialized control and completed one NMPC/MuJoCo experiment. It **did not pass the full original task**: holding speed failed. The model issued a truthful native STOP. Independent reconstruction, archive integrity, receipt settlement and frozen-source checks passed. Neither the probes nor this observational Study establish improved total token efficiency.

## A. Cold-start boundary

The target branch was fetched and both local and remote HEAD matched `174cd8c04ede5058cb78ffd91a45fb43f5399cec`. The original target worktree was clean. All changes are confined to `feat/sorosim-matlab-nmpc`.

`configs/research/study_s125_cold.json` uses the existing family-space initializer, original `reach_hold_mirror_v1` task and unchanged `family_space_s7.json`. History, mathematics, control seeds and supplied evidence are empty; `require_task_guidance=false`. Formal ID `s125-cold-live-20261020` has its own Store and new Strands session, created after the admission gates and source commit.

[Cold-start preflight](../../evidence/s125_preflight/cold_start.json) verifies an empty candidate pool, no reference candidate or best result, no imported mathematics/controls, and a separate session with no saved conversation. The compatibility scaffold is explicitly not a scientific candidate. An old S12 artifact fails the new Store's lookup. A disposable engineering candidate can be generated, initialized with the existing baseline control, and admitted for cold mathematics without warm evidence. It is never an input to the formal Study.

`Store.artifact()` queries the current Store database and validates content identity. Formal Agent tools do not expose arbitrary filesystem reads. `experience_retrieve` was already blocked by the formal tool hook and is now omitted from new formal requests; original saved requests retain their schemas. Strands Offload retrieval belongs to the new framework session, which has no previous Study history.

Cold-start means no prior experimental observations or solutions, not absence of human knowledge. Frozen family parameter bounds/defaults, material and section models, assembly prototypes, connector/guide/payload properties, tendon routing rules, force bounds, discretization and controller defaults remain declared design priors. These include defaults established during earlier engineering development. The engineering scaffold does not register a successful historical robot as a new candidate.

The task remains target `[0.29,-0.035,0.19] m`, duration `0.35 s`, control period `0.01 s`, physics step `0.0005 s`, terminal and holding position limits `0.01 m`, holding speed limit `0.02 m/s`, plus every original completeness, force, coverage and evaluator-validity component.

[Frozen protocol](../../evidence/s125_cold/frozen_protocol.json) records the empty actual initial packet, ledger, dependencies and provider before the first request. The scientific implementation is `114578bf44f1d4a7d1134e834a8ed9ffdd0e4aba`; configuration identity is `9209e59bad1a35ae5936a0a65e7bcea43c873a78b0e999018387b4a171820a7a`. A subsequent evidence-only binding commit `44dd78c2ef6f4500df282eaef975a7af0d13d957` did not change the implementation. No code, prompt, scientific parameter or budget changed during execution.

[Cold provenance](../../evidence/s125_cold/cold_provenance.json) connects the first request, first generated candidate at request 13, all nine candidates, the new control initialization and the sole scientific result. Every candidate was generated inside this Study; no evaluated historical candidate, control, mathematics or prior best was registered. The task's canonical identity is `d24aeac7041052ce1d2ae60e825a802e7367107784f6fec192b0a65c4a5e76e7`; the executed candidate's dimension-bound task identity is `53a615f4aa1b6f42fe0a9101912343a895a73c7e475b7c1082f5d99967ef2649`. Candidate-specific channel binding does not change the target, horizon or acceptance thresholds.

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

After the Study stopped, only existing audit scripts and delivery artifacts were extended. `s12_audit.verify_nmpc()` reuses the registered evaluator, saved-state reconstruction, profile summarizer and acceptance assembler; `s125_wire_audit.live_audit()` reuses the original Store and byte partitioner. Both were exercised against the sealed actual result. No new production system or scientific execution was introduced. Provider HTTP acceptance does not mean strict schema enforcement: the live model still omitted a required hypothesis once and proposed an unavailable action during closeout; the unchanged server rejected both.

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

Actual formal S12.5 totals, with identical byte definitions:

| Component or usage | S12, 22 requests | S12.5, 46 requests |
|---|---:|---:|
| Fixed instruction bytes | 139,348 | 290,628 |
| Schema bytes | 692,033 | 1,539,063 |
| Current packet bytes | 704,585 | 850,671 |
| Ordinary assistant text bytes | 0 | 0 |
| Original historical reasoning bytes | 1,733,626 | 7,148,402 |
| Historical tool-result bytes | 1,412,652 | 1,898,348 |
| Other protocol bytes | 359,040 | 2,308,255 |
| Total canonical request bytes | 5,041,284 | 14,035,367 |
| Actual prompt tokens | 1,557,945 | 4,283,714 |
| Actual completion tokens | 52,961 | 134,977 |
| Actual total tokens | 1,610,906 | 4,418,691 |
| Prompt-cache hit tokens | 81,536 | 84,992 |
| Prompt-cache miss tokens | 1,476,409 | 4,198,722 |

The new Study's retained historical reasoning is 50.9% of cumulative canonical request bytes. Fixed instructions remain 6,318 bytes per request; none of the original reasoning was deleted or rewritten. Cache hits account for about 2.0% of actual prompt tokens, versus 5.2% in S12; this does not isolate a cause of cache behavior. Other protocol bytes include assistant tool-call arguments and framing, so the zero ordinary-text bucket is not zero assistant history. Reasoning-specific usage tokens remain `unavailable`.

[All 46 requests](../../evidence/s125_wire_audit/s125_requests.json) retain exact IDs/references, message counts, per-request/cumulative-attributable byte components, original usage/cache fields and actual tool outcomes. Tables appear in section G. Formal total tokens are about 2.74 times S12, under different starting evidence and a larger request allowance. This is an observed cost increase, not proof that the interface change caused it. The paired probes also failed to establish a token saving. The main remaining issue is the amount of conversation accumulated before useful computation, especially retained reasoning and repeated tool interactions. Any future safe session checkpointing needs separate protocol/recovery validation; it was not implemented here.

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

The real DeepSeek/Strands Agent completed one bounded Study. [Decision chain](../../evidence/s125_cold/feedback_decision_chain.json), [summary](../../evidence/s125_cold/summary.json), [accounting](../../evidence/s125_cold/accounting.json) and [original disposition](../../evidence/s125_cold/study/disposition.json) preserve the actual sequence. The chain is a derived index; exact request/feedback/result references resolve in the single immutable archive.

**Design and initialization.** Requests 1–36 concentrated on legal topology/routing construction and evidence reads. Nineteen generation calls reached the design tool: nine generated candidates and ten returned business-level `invalid`. The ten reasons were one wrong family identity, one missing exact section-station definition, one angular-offset domain violation, six tendon-attachment-clearance violations and one unordered/duplicate guide-station violation. These are not physical experiments. The first valid candidate arrived at request 13. Candidates included a two-segment, one-tendon diagnostic layout before the Agent progressed to the executed three-segment, six-tendon design. One `initialize_control` attempt omitted `hypothesis`; its corrected request created a new constant 0.2 N schedule with no parent/source or inherited acceptance.

The executed candidate is `9a0de5df85643d568de7fbacf7b3f07c60471bcda57d683ec31d81cba893142a`. Segment lengths are `[0.15,0.11,0.09] m`, Young's moduli `[4,3,3] MPa`, with 12 cells per segment. Each segment has two local tendons, radius `0.014 m`, guide fraction `0.5`, anchor fraction `0.9`, offsets `[0,pi/2]`; phases are `[-3pi/2,-3pi/2,+3pi/2]`. Tendon diameter is `0.001 m`, force limit `8 N`, pretension `0.2 N`. Other section/material/assembly values retain frozen family defaults. The generated MuJoCo model has 72 bending DOFs; the NMPC model has 24 GVS coordinates and six inputs.

**Actual scientific execution.** Request 37 selected one `execute` experiment using the existing SoRoSim MATLAB NMPC and independent MuJoCo backend. No offline NLP, standalone mathematical analysis, BDF replay, fixed-schedule physical replay, local control search or PPO training/evaluation ran. NMPC used the retained engineering controller recipe: horizon 10, implicit Euler, one substep, MATLAB SQP maximum 120 iterations per update and structural-linear basis. Its numerical initialization is bound to the new candidate/project initial state and bounded pretension; the separately created seed is not falsely described as imported historical warm evidence.

The one physical episode covered all `0.35 s`, with 35 control updates. All 35 SQP updates returned exit flag 1 and delivered accepted non-initialization plans; solver-error count and force-bound violation were zero. These are 35 internal optimizer calls inside **one** high-level scientific decision and **one** physical evaluation, not 35 experiments. Simulation wall time was `2885.859 s`; total reserved execution boundary settled at `2891.409 s`. Mean update time was `82.130 s`; all 35 exceeded the control period, so real-time operation was not demonstrated and is not an acceptance requirement.

| Original acceptance component | Observed | Limit | Outcome |
|---|---:|---:|---|
| Terminal position error | 0.003956106 m | 0.01 m | pass |
| Holding maximum position error | 0.006144922 m | 0.01 m | pass |
| Holding maximum speed | 0.324348056 m/s | 0.02 m/s | **fail** |
| Holding coverage | 6 inclusive samples | 6 | pass |
| Force-bound violation | 0 N | 1e-8 N | pass |
| Solver errors | 0 | 0 | pass |
| Execution and evaluation | complete / valid | complete / valid | pass |
| Full frozen protocol | valid failure | all components pass | **not accepted** |

The endpoint evaluator alone returned success; the full reach-and-hold protocol correctly rejected the speed violation. This is the sole and therefore best valid failed result, normalized research gap `15.217402812`. Scientific result reference: `cba5ff7f2e895491eea1bb6db153dd556ec3956c4ea564cec9c3ecd97e1412e0`; execution `22e31f6d44144231a953caecb6d05f5d`.

**Feedback and stop.** Requests 38–43 read execution, evaluation and controller facts. At request 44 the protection boundary was active. The Agent proposed increasing tendon radius to `0.022 m`, reducing Young's moduli to `[2.5,2,2] MPa` and changing pretension to `0.5 N`. The server rejected `generate` with `PROTECTED_CLOSEOUT_REQUIRES_EVIDENCE_SELECTION_OR_STOP`; this variant was never compiled or executed. Thus there was **one feedback-driven revision proposal and zero executed feedback revisions**. The nine earlier valid candidates preceded any physical or numerical feedback and cannot be credited as such revisions.

The model's proposal attributed the failure to actuation authority and claimed control search alone could not fix it. Those are unsupported causal interpretations, preserved as model text, not findings of this audit. Three tendons reaching 8 N at some samples does not prove structural change is necessary. At request 45, STOP was rejected because exact acceptance had not yet been read. The model then read `/acceptance` and successfully issued STOP on request 46, citing the only fresh result. Final reason: protected closeout with no accepted result, not exhaustion of all physical capacity and not proof of task infeasibility. There was no selected solution, forced engineering stop, retry Study or budget reset.

**Budget and evidence.** The frozen limits remain 48 Provider requests/4 protected, 200 public operations/12 protected, 64 physical starts, four analyses, one offline NLP, two BDF replays, two NMPC executions, one PPO stage/65,536 aggregate actions and one independent RL evaluation. Actual ledger usage is 46 model requests, 70 charged tool operations (67 model-facing tool calls plus three execution stages), one backend start, zero workers and no occupied reservations. Two Provider requests and 63 backend starts remain; unused physical capacity does not override model-request protection. Of the 67 model-facing calls, 42 were evidence reads and six were errors. The ten invalid generation results are counted separately. The probe Store used its separate ten-request ledger; combined authorized usage is 56 requests and 4,636,158 tokens, with no allowance transferred.

[Independent checks](../../evidence/s125_cold/final_artifact_checks.json) reran the registered evaluator on the sealed backend result and reconstructed motion from saved states using `mj_forward`/Jacobians, with no integration or optimization. Recomputed motion, profile, original evaluator result and full acceptance all exactly match. Every receipt is settled, no pending/unconsumed response remains, all raw request/response hashes and tool-call pairs match, and all 664 archive members pass their hashes. The configured API credential was absent from every archive member. Science/core hashes match the freeze; original task/science and sealed S7–S12 evidence are unchanged.

The [design package](../../evidence/s125_cold/study/design_package.json) contains the full best-failure structure. The [recorded design and control](../../evidence/s125_cold/nmpc_design_control_22e31f6d44144231a953caecb6d05f5d.json) includes the exact executed configuration, full applied-command sequence and export references. This sequence records closed-loop execution; it is not a separately validated open-loop replay. Full trajectory, solver observations, original Provider reasoning and all raw evidence occur once in the [immutable archive](../../evidence/s125_cold/study/immutable_artifacts.tar.gz), indexed by its [manifest](../../evidence/s125_cold/study/archive_manifest.json).

## F. Observational stage comparison

| Metric | S10 | S11 | S12 | S12.5 formal |
|---|---:|---:|---:|---|
| Provider requests | 29 | 30 | 22 | 46 |
| Actual tokens | 1,754,349 | 1,837,185 | 1,610,906 | 4,418,691 |
| Executed high-level scientific calculations | 3 | 1 | 3 | 1 |
| Fresh physical evaluations | 20 | 1 | 27 | 1 |
| New standalone mathematical work | 1 analysis | 0 | 1 NLP | 0; 35 internal NMPC solves |
| Tool errors | 6 | 4 | 4 | 6 |
| Evidence reads | 48 | 51 | 22 | 42 |
| Requests through first successful calculation | 6 | 19 | 5 | 37 |
| Requests before first physics, existing convention | 6 | 19 | 18 | 37 |
| Executed changes of method after fresh feedback | 2 | 0 | 2 | 0 |
| Original task passed | no | no | yes | no |

Historical counts use [the existing comparison](../../evidence/s12_mirror/provider_comparison.json). Feedback changes are counted from the archived decision chains: S10 replay→search→equilibrium; S11's later mechanics/search proposals were rejected; S12 mathematics→physical validation→measured control search; S12.5's post-result generation proposal was rejected. Routine reads, STOP/SELECT, seed transport, invalid design attempts and internal optimizer iterations are excluded. The S12 mathematical-to-physical handoff counts as one evidence-driven method transition, not as a structural revision.

The reused S9 root-session accounting returns `time_to_first_physics=null` for a child-owned NMPC execution. The [actual wire supplement](../../evidence/s125_wire_audit/s125_requests.json) includes that owned child's reservation: sequence 545, request 37, `590.595 s` from the first request. Its zero fixed-schedule sequence/probe counts likewise do not mean no NMPC execution. Different initial evidence, budgets, method choices and episode costs prevent causal attribution across stages. No overall efficiency or scientific success advantage is established.

## G. Actual S12.5 request tables

Canonical compact UTF-8 JSON bytes; ordinary assistant text is zero in all rows. Raw message counts are included.

| # / request suffix | Total | Fixed | State | Schema | Reasoning | Tool results | Protocol | Messages |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 / db1fdfd6 | 55503 | 6318 | 14011 | 34815 | 0 | 0 | 359 | 2 |
| 2 / 23d16785 | 67167 | 6318 | 14011 | 34815 | 7252 | 965 | 3806 | 4 |
| 3 / 26f8f848 | 71891 | 6318 | 14011 | 34815 | 7752 | 4248 | 4747 | 7 |
| 4 / 80f0e7fc | 76063 | 6318 | 14011 | 34815 | 9528 | 5842 | 5549 | 10 |
| 5 / 9d45fbcc | 81858 | 6318 | 14011 | 34815 | 11023 | 6801 | 8890 | 12 |
| 6 / 69e29e25 | 88924 | 6318 | 14011 | 34815 | 12532 | 11470 | 9778 | 15 |
| 7 / 849b7e78 | 97918 | 6318 | 14011 | 34815 | 17194 | 12439 | 13141 | 17 |
| 8 / 80961330 | 102312 | 6318 | 14011 | 34815 | 17454 | 13394 | 16320 | 19 |
| 9 / c5cf5f4e | 111084 | 6318 | 14011 | 34815 | 24384 | 14446 | 17110 | 22 |
| 10 / a6c83929 | 119374 | 6318 | 14011 | 34815 | 30974 | 15348 | 17908 | 25 |
| 11 / 99d61685 | 144897 | 6318 | 14011 | 34815 | 52266 | 16314 | 21173 | 27 |
| 12 / 8bb6b87b | 151934 | 6318 | 14011 | 34815 | 55352 | 17269 | 24169 | 29 |
| 13 / dc7478dc | 170963 | 6318 | 14011 | 34815 | 70234 | 18224 | 27361 | 31 |
| 14 / b3a436b5 | 183005 | 6318 | 15655 | 34815 | 76093 | 19716 | 30408 | 33 |
| 15 / 6e05cfd9 | 199248 | 6318 | 15655 | 34815 | 84713 | 26455 | 31292 | 36 |
| 16 / 043de91a | 209064 | 6318 | 15655 | 34815 | 90399 | 27410 | 34467 | 38 |
| 17 / 93037545 | 218077 | 6318 | 15656 | 34815 | 95567 | 28365 | 37356 | 40 |
| 18 / 5adf2d1e | 234235 | 6318 | 17302 | 34815 | 105632 | 29857 | 40311 | 42 |
| 19 / 6ade85df | 249520 | 6318 | 18948 | 34815 | 114320 | 31349 | 43770 | 44 |
| 20 / 742d4741 | 256822 | 6318 | 18948 | 34815 | 114569 | 37843 | 44329 | 46 |
| 21 / 1f122e2a | 280277 | 6318 | 18948 | 34815 | 133548 | 38798 | 47850 | 48 |
| 22 / 04ebed0a | 289153 | 6318 | 18948 | 34815 | 137520 | 40290 | 51262 | 50 |
| 23 / 5883f7b0 | 290530 | 6318 | 18948 | 34815 | 137773 | 40905 | 51771 | 52 |
| 24 / 1fcb34ab | 293777 | 6318 | 18948 | 34815 | 137810 | 43724 | 52162 | 54 |
| 25 / 85898333 | 321516 | 6318 | 18948 | 34815 | 160694 | 45216 | 55525 | 56 |
| 26 / df71a71e | 322558 | 6318 | 18948 | 34815 | 160746 | 45680 | 56051 | 58 |
| 27 / 6d853e04 | 325751 | 6318 | 18948 | 34815 | 160746 | 48502 | 56422 | 60 |
| 28 / 21e8dffa | 342264 | 6318 | 18948 | 34815 | 172395 | 49994 | 59794 | 62 |
| 29 / 0dc6a26e | 348945 | 6318 | 18948 | 34815 | 172754 | 55749 | 60361 | 64 |
| 30 / bc820964 | 402990 | 6318 | 18948 | 34815 | 221626 | 57241 | 64042 | 66 |
| 31 / bd5a44e2 | 405934 | 6318 | 18948 | 34815 | 222562 | 57674 | 65617 | 71 |
| 32 / 55dc9210 | 442145 | 6318 | 18948 | 34815 | 253601 | 59166 | 69297 | 73 |
| 33 / d8dd9185 | 444388 | 6318 | 18948 | 34815 | 253840 | 59599 | 70868 | 78 |
| 34 / 0de48b84 | 465813 | 6318 | 18948 | 34815 | 269878 | 61091 | 74763 | 80 |
| 35 / 5493bd81 | 469257 | 6318 | 18947 | 34815 | 270413 | 61729 | 77035 | 87 |
| 36 / bc7cd8ff | 476939 | 6318 | 18946 | 34815 | 275359 | 62146 | 79355 | 89 |
| 37 / 24827148 | 484652 | 6318 | 22466 | 34815 | 275615 | 63676 | 81762 | 91 |
| 38 / c836bab7 | 494753 | 6318 | 24928 | 34815 | 276782 | 67292 | 84618 | 93 |
| 39 / 4db24c25 | 506915 | 6318 | 24928 | 34815 | 287405 | 67630 | 85819 | 97 |
| 40 / 44e97c88 | 517612 | 6318 | 24927 | 34815 | 294602 | 70156 | 86794 | 100 |
| 41 / b5955694 | 527754 | 6318 | 24927 | 34815 | 303187 | 71053 | 87454 | 102 |
| 42 / 95ca1264 | 529496 | 6318 | 24927 | 34815 | 304452 | 71143 | 87841 | 104 |
| 43 / 77425f37 | 539114 | 6318 | 24927 | 34815 | 304716 | 79779 | 88559 | 107 |
| 44 / 2a95b029 | 524027 | 6318 | 25144 | 14006 | 308817 | 80518 | 89224 | 109 |
| 45 / 57bb2e3c | 544302 | 6318 | 25185 | 14006 | 324725 | 80650 | 93418 | 111 |
| 46 / cad62828 | 554646 | 6318 | 25185 | 14006 | 329598 | 81192 | 98347 | 113 |

Actual original Provider usage; cumulative totals include each sent request once.

| # | Prompt | Completion | Total | Cumulative total | Cache hit | Cache miss |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 16436 | 3126 | 19562 | 19562 | 2560 | 13876 |
| 2 | 19830 | 400 | 20230 | 39792 | 1792 | 18038 |
| 3 | 21178 | 650 | 21828 | 61620 | 1792 | 19386 |
| 4 | 22256 | 1446 | 23702 | 85322 | 1792 | 20464 |
| 5 | 23954 | 570 | 24524 | 109846 | 1792 | 22162 |
| 6 | 26159 | 2543 | 28702 | 138548 | 1792 | 24367 |
| 7 | 28959 | 1161 | 30120 | 168668 | 1792 | 27167 |
| 8 | 30372 | 2057 | 32429 | 201097 | 1792 | 28580 |
| 9 | 32722 | 1963 | 34685 | 235782 | 1792 | 30930 |
| 10 | 34897 | 6798 | 41695 | 277477 | 1792 | 33105 |
| 11 | 41946 | 1926 | 43872 | 321349 | 1792 | 40154 |
| 12 | 44134 | 4976 | 49110 | 370459 | 1792 | 42342 |
| 13 | 49360 | 2637 | 51997 | 422456 | 1792 | 47568 |
| 14 | 52853 | 2579 | 55432 | 477888 | 1792 | 51061 |
| 15 | 57500 | 2661 | 60161 | 538049 | 1792 | 55708 |
| 16 | 60413 | 2365 | 62778 | 600827 | 1792 | 58621 |
| 17 | 63036 | 3933 | 66969 | 667796 | 1792 | 61244 |
| 18 | 67844 | 3883 | 71727 | 739523 | 1792 | 66052 |
| 19 | 72627 | 203 | 72830 | 812353 | 1792 | 70835 |
| 20 | 75089 | 6741 | 81830 | 894183 | 1792 | 73297 |
| 21 | 82092 | 2430 | 84522 | 978705 | 1792 | 80300 |
| 22 | 84902 | 216 | 85118 | 1063823 | 1792 | 83110 |
| 23 | 85303 | 135 | 85438 | 1149261 | 1792 | 83511 |
| 24 | 86480 | 8816 | 95296 | 1244557 | 1792 | 84688 |
| 25 | 95755 | 179 | 95934 | 1340491 | 1792 | 93963 |
| 26 | 96069 | 130 | 96199 | 1436690 | 1792 | 94277 |
| 27 | 97241 | 4999 | 102240 | 1538930 | 1792 | 95449 |
| 28 | 102672 | 241 | 102913 | 1641843 | 1792 | 100880 |
| 29 | 105060 | 20607 | 125667 | 1767510 | 1792 | 103268 |
| 30 | 126097 | 791 | 126888 | 1894398 | 1792 | 124305 |
| 31 | 126995 | 12441 | 139436 | 2033834 | 1792 | 125203 |
| 32 | 139828 | 578 | 140406 | 2174240 | 1792 | 138036 |
| 33 | 140513 | 6311 | 146824 | 2321064 | 1792 | 138721 |
| 34 | 147244 | 948 | 148192 | 2469256 | 1792 | 145452 |
| 35 | 148347 | 1969 | 150316 | 2619572 | 1792 | 146555 |
| 36 | 150431 | 783 | 151214 | 2770786 | 1792 | 148639 |
| 37 | 152692 | 1085 | 153777 | 2924563 | 1792 | 150900 |
| 38 | 155426 | 3109 | 158535 | 3083098 | 1536 | 153890 |
| 39 | 158613 | 2160 | 160773 | 3243871 | 2048 | 156565 |
| 40 | 161505 | 2550 | 164055 | 3407926 | 2048 | 159457 |
| 41 | 164361 | 410 | 164771 | 3572697 | 2048 | 162313 |
| 42 | 164785 | 303 | 165088 | 3737785 | 2048 | 162737 |
| 43 | 167520 | 1232 | 168752 | 3906537 | 2048 | 165472 |
| 44 | 162499 | 5889 | 168388 | 4074925 | 2048 | 160451 |
| 45 | 168429 | 2687 | 171116 | 4246041 | 2048 | 166381 |
| 46 | 171290 | 1360 | 172650 | 4418691 | 2048 | 169242 |
