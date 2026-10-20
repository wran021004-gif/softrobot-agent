# S11 delivery ? real study completed, efficiency improvement not demonstrated

**S11 completed a real authorized DeepSeek/Strands Study and ended with native model STOP, without a complete original-task pass.** The frozen Agent created one explicit control seed from historical static-equilibrium evidence and executed one new independent MuJoCo replay. That replay failed and was worse than the historical best. Subsequent offline-NLP proposals were rejected; the proposed wider-radius search reached protected closeout and never executed.

The interface reduced offline decision-packet bytes, but **live decision efficiency did not improve in this run**: 30 Provider requests, 51 evidence reads and 1,837,185 actual tokens, versus S10's 29/48/1,754,349. Tool errors decreased to four of 57 tools (7.02%). These are observations from different historical starting evidence, not a controlled A/B result or causal interface conclusion.

Only the designated worktree/branch was changed. Production implementation was frozen before science and remained unchanged throughout and after the run. Study `s11-mirror-live-20261020` is bound to pushed commit `6f6f3a52a287de431b80f4969a01750b7ecad791`; resolved configuration identity `d554a10fbb3236071609f548cd9d4352bd0ce831ea90fe2e017970cc417ffc77`. Canonical mirror task identity remains `d24aeac7041052ce1d2ae60e825a802e7367107784f6fec192b0a65c4a5e76e7`, with original effective task identity `bd9df2d930423f2b2a12152f076e2ae88b4d1a0af84d6126aa13b0b1fac9ec77` and target `[0.29,-0.035,0.19]` m. No task threshold, timing, actuator, evaluator or scientific solver changed.

## Q1. What did the decision interface reduce?

The existing `decision_packet()` now projects `decision_brief_v1`, retaining the task, best bound observation and actual failed thresholds, scoped mathematics, method ceilings and usage, legal actions, exact registered references and the complete STOP index. It removes repeated observation/Pareto/recent-decision lists and duplicate control-start listings from the model packet. Best valid control is advertised first, even if it was not among the last three evaluations. All original data remain in Store.

Tool feedback stores its complete original output and returns new scientific facts once. It labels `wrapper_reference` retrieval-only and separates `scientific_reference`. Default physical/search feedback omits full trajectories and search callbacks while retaining task gap, all acceptance components, search diagnostics and best source/evaluation. Explicit evidence reads keep original views and JSON-pointer semantics. The next system packet owns dynamic state; tool history no longer appends `decision_feedback` and `all_fresh_results` to every new calculation response. Saved Provider messages, model reasoning, tool IDs, immutable results, original feedback and Strands recovery are not deleted or rewritten. The existing Provider boundary and public Offload mechanism are unchanged.

Production diff against `1cda36ec`: +106/-23, net **83 lines** across `agent.py`, `budget.py`, `evidence_policy.py`, `research_context.py`; no new production module, optimizer, controller, Store or research entry point. Admission's original reference inventory was extracted and reused rather than duplicated.

Pure projection of the same 29 saved S10 packets: **1,017,937 → 690,630 canonical UTF-8 JSON bytes (32.15% reduction)**. This retains task identity, best result/gap, actual violated constraints, actions, method counts, original budget and every STOP reference. It does not replay Agent choices or forecast full-session token usage. The actual prepared S11 first packet is **24,602 bytes**, including new budget/reference/prerequisite fields and its different historical starting evidence.

The final S11 wire's current packet component was 28,673 canonical serialized bytes versus S10's 47,347, but its model-message history was 245,226 versus 160,917 bytes. Tool history was 62,593 versus 93,089 bytes. First/last whole S11 wire requests were 67,652 / 356,497 bytes versus S10's 70,866 / 322,507. These partitions serialize the embedded packet string and are distinct from the 24,602-byte standalone first-packet measurement. No reasoning/history was removed to make numbers smaller.

A residual projection defect is explicitly recorded in [remaining interface gaps](../../evidence/s11_mirror/remaining_interface_gaps.json): seed/STOP fallback feedback shows the nested result's keys but keeps an empty pointer against its wrapper, where the full result is actually at `/result`. This wrapper is labeled retrieval-only and remains inadmissible as scientific evidence. No model read this fallback wrapper; the scientific-result branch and bound source handoff were usable. It is a remaining code-level defect, not an observed query error or established cause of the efficiency outcome. It was not silently patched after formal results.

## Q2. Why did S10 use 48 evidence reads?

The [raw S10 audit](../../evidence/s11_mirror/s10_offline_audit.json) reads hash-verified original requests/feedback from the sealed archive, not just its delivery summary. All 48 queries and all six errors retain original request/reference IDs. Reads comprise 19 summaries, 13 full views, 12 ranges, three field queries and one capabilities view. There were **no identical repeated queries**. Repeated access instead used different views/pointers: four `/trajectory/tensions_n` queries, two `/trajectory` queries, six `/samples` queries, four `/raw_reference`, four `/provenance`, and two `/acceptance` queries, alongside identity/parameter and mathematical-scope navigation.

Four errors were incorrect field names or `/samples` on evaluation artifacts instead of their raw references. One proposal used unregistered wrapper/search citations; the corrected proposal hit protected closeout. Mathematical display fields also induced extra navigation: display `static_input_observation` and `control_handoff` are tool summaries, not authoritative mathematical artifact layout. The expanded-radius search remained unexecuted.

Byte partitions reuse `s8_audit.payload`: fixed instructions, tool schemas, current packet, model history, tool history and other protocol fields. The first original request was 70,866 bytes; its last was 322,507 bytes, including 160,917 model-history bytes and 93,089 tool-history bytes. These are serialized bytes, **not** Provider prompt-token counts. Original Provider usage remains 1,754,349 tokens. The last wire request contains three `decision_feedback` markers in historical tool messages. Strands truncation prefixes make some messages non-JSON, so the audit separately counts markers and containing-message bytes; it does not claim exact subtree byte sizes or count those overlapping diagnostics as new partition components. No estimated-token reduction is claimed.

S11 directly exposes bound candidate/source pairs, domain/grid/channel information, registered supporting references, task violations and search diagnostics. This reduces the need to reconstruct a legal request by reading entire arrays or every callback. It does not prohibit necessary diagnostic queries or force a scientific tool in every turn.

## Q3. Can physical and mathematical evidence legally hand off?

Admission and handoff share the extracted original registered-reference inventory. The actual S10 rejected `H_LARGER_RADIUS_62DD` proposal still raises `UNREGISTERED_RESEARCH_EVIDENCE`; replacing its wrapper references/candidate/source with the current registered handoff passes `admit_decision()`. Wrong selected candidate, unsupported mathematics, wrong raw pointers and incomplete STOP coverage remain rejected. `preflight_eligible` covers only advertised prerequisites; typed Plan, requested budget, scientific preflight and execution remain authoritative.

The **real S11 Agent** cited registered S10 equilibrium `3573c3b24e533bda8ee635e7f652d265390814b56790820ae335905e2a4f01bd` and historical source `62ddc2387077c5b49440d16208cd83d07d9108187e3e94df00043e4bfdb9557d` to initialize explicit baseline source `4a7879ebfde39a634f9446facb1f000c27ef3a2ac47fb10569db2b8699fcf153`. It then replayed that exact source on executable candidate `15d2a97a0f7e788864f66360bc733200c393e583b300d01db27c887481667df1`, producing fresh S11 evaluation `289592aeb8f31ee4dd620b3aa8ad9cbe21612752d1d1cef2e6810e77eff61d5d`. This demonstrates lawful evidence?explicit Agent-chosen input?new measured outcome. It does not demonstrate mathematical-response certification or improved dynamics. No unregistered supporting-evidence error occurred in S11.

S11 reused `analysis.compact_result()` and `verified_input_response()` without modifying analysis or numerics. Historical equilibrium is not current verified input sensitivity. The Agent used explicit baseline inputs as a falsifiable hypothesis, not the automatic `mathematical_response` method. No new input-sensitivity calculation or mathematical seed certification occurred. Existing S9 handoff regressions cover current sensitivity and identity/verification rejections.

The complete fresh-result index contains one result and native STOP explicitly cites it plus historical/source/raw evidence. That proves citation coverage, not model comprehension: STOP's cost narrative incorrectly describes the fresh replay as an earlier-run reuse. The [independent checks](../../evidence/s11_mirror/final_artifact_checks.json) establish S11 ownership and exactly one charged fresh backend start. Model interpretations remain preserved and are corrected by the audit, never rewritten.

## Q4. Did Provider budget efficiency improve?

| Metric, same original accounting convention | S10 | S11 |
|---|---:|---:|
| Provider requests | 29 | 30 |
| Actual Provider prompt tokens | 1,706,805 | 1,767,033 |
| Actual Provider completion tokens | 47,544 | 70,152 |
| Actual total tokens | 1,754,349 | 1,837,185 |
| Model tools | 54 | 57 |
| Evidence reads | 48 | 51 |
| Read share of model tools | 88.89% | 89.47% |
| Tool errors | 6 (11.11%) | 4 (7.02%) |
| Requests before first physics, existing audit convention | 6 | 19 |
| Executed high-level scientific calculation decisions | 3 | 1 |
| Fresh independent physical evaluations | 20 | 1 |
| New mathematical analyses | 1 | 0 |
| Best fresh normalized task gap | 2.4190924923 | 33.1919339363 |
| Remaining Provider / physical slots | 3 / 44 | 2 / 63 |
| Full original task accepted | No | No |

Tokens increased **82,836 (4.72%)**. The lower error rate meets the aspirational <10% marker, but readings, latency to science and executed science did not improve. No full-session efficiency benefit or causal claim is supported. Currency cost is unknown; actual response usage, including preserved reasoning, is authoritative. Serialized byte changes and original Provider usage are distinct; no token estimate is represented as measured savings.

S11 reads were 28 full, 16 summary, three fields, three range and one capabilities query. No identical repeated query occurred, but source/candidate/math navigation continued, including 11 separate `/samples/<index>/tip_m` reads and three sample ranges after failure. Full candidate configuration/scientific configuration was requested despite the current brief. All successful empty field selections remain counted as reads. Four errors were an invalid historical mathematical pointer, a forbidden extra Plan field (`interpenetration_note`), `VERIFIED_MATHEMATICAL_WARM_SOURCE_REQUIRED`, and protected-closeout rejection of a control search. No errors are discarded to improve the denominator.

The derived budget view uses the existing ledger and never changes gates. It was available throughout: initialization packet total 15/next-request exploration 10, replay packet 14/9, two NLP proposals 7/2 then 6/1. The search packet explicitly showed total 5, reserve 4, next-request exploration 0 and `next_request_will_protect=true`. The Agent nevertheless requested a 56-evaluation search; after the request charge, the original gate correctly blocked it. Presentation did not ensure the model acted on the warning. See [action-level budget audit](../../evidence/s11_mirror/decision_budget_audit.json).

Frozen budgets exactly equal S10: 32 Provider/4 protected, 160 operations/12 protected, 64 shared backend starts, four analyses, one offline NLP, two BDF, two NMPC, one PPO stage/65,536 aggregate actions and one independent RL evaluation. Actual use: 30/57/1, zero new analyses/NLP/BDF/NMPC/PPO. At STOP 2 Provider, 103 public and 63 physical slots remain; no increase, reset or transfer occurred. Protection ended science before physical capacity was exhausted.

Historical S10 best failure and mathematics were added to the S7/S8 evidence and optional unmeasured S6 control seed. **S10 and S11 are not equal-start controlled A/B experiments.** This single result neither proves a general harmful interface effect nor supports a benefit.

## Q5. What did the real Agent do?

[Original requests and feedback](../../evidence/s11_mirror/decisions.json) and the [feedback/decision chain](../../evidence/s11_mirror/feedback_decision_chain.json) preserve exact hypotheses, choices, references and outcomes.

| Decision | Actual choice | Outcome |
|---|---|---|
| 1, `TARGET_EQUILIBRIUM_HOLD` | Keep imported structure; choose explicit 35?4 cosine-ramp/hold inputs from 0.2 N to rounded historical equilibrium `[4.130153,1.813905,2.101490,3.240433]` N over 0.10 s, hold to 0.35 s; zero physical budget for initialization | New unmeasured source `4a7879eb?` |
| 2, same hypothesis | Allocate one complete independent fixed-input MuJoCo replay | Fresh valid failure `289592ae?`, gap 33.1919339363 |
| 3, `SWING_AND_STOP_OPTIMAL_CONTROL` | After failure/trace reads, propose one bounded offline NLP, max 120 iterations, warm-started with the historical fixed-tension schedule | Rejected before science: extra `interpenetration_note` field |
| 4, same revised request | Remove the extra field and resubmit | Rejected before solver: verified mathematical warm source required |
| 5, `CONTROL_SEARCH_WIDER_RADIUS` | Propose response search from historical best: three knots 0.10?0.32 s, coefficient limit 2.5 N, three iterations, 56-evaluation cap | Protected closeout; no search or physics executed |
| 6, `CLOSEOUT_NO_FRESH_COMPLETE_PASS` | Cite fresh result, raw trajectory, sources and historical equilibrium; native model STOP | Study stopped, no SELECT or accepted design |

There is **one executed high-level scientific calculation** (the replay), plus a separate seed-construction decision. Rejected NLP proposals, unexecuted search, query turns and STOP are not additional successful experiments. No new mathematical analysis, NMPC, PPO, numerical structural search or model-generated structural modification occurred; none is credited with a benefit.

Engineering preflight remains separate: [report](../../evidence/s11_mirror/preflight.json), [MATLAB readiness](../../evidence/s11_mirror/readiness/report.json), and retained [sandbox failure](../../evidence/s11_mirror/readiness/sandbox_failure.json). A separate permitted-access ledger passed dependency/engine/gateway/sqrt(4)/shutdown after the sandbox UTF-8 startup failure. No source/runtime workaround was added. Direct PPO environment construction passed: 48 DOFs, four 0?8 N actions, 107 observations, 35 intervals. NMPC count/horizon and mathematics admission were available, but full candidate execution remained necessary. Residual PPO still requires a published exact compatible reference. All original methods/family domains remained open without a forced order or design change.

94 focused regressions passed before implementation commit, followed by all nine S11 tests including the new configuration check: **95 distinct tests** in the reported set. They cover the actual S10 request/archive, exact refs, strict field/pointer/object-range handling, verified mathematics, STOP coverage, tool/reasoning IDs, protection and existing continuation/unknown-outcome recovery. No test result is presented as formal research evidence. No production or test code was changed after the formal run.

## Q6. Did feedback cause a new scientific strategy revision?

It caused **new research proposals**, but **no second scientific calculation executed after failure**. The failed replay weakened this particular ramp-to-static-equilibrium strategy. The Agent proposed swing-and-stop offline optimization, corrected its schema, then proposed wider-radius physical response optimization when the warm-source prerequisite failed. Both changed hypothesis/method/budget in response to actual feedback, but neither generated a result. An unexecuted revised strategy must not be counted as a successful adaptive experiment.

The Agent inferred a slow swing/settling explanation from the trace and sometimes used stronger wording such as ?proves ... only through a timed swing.? That causal/exclusivity claim is unsupported by one rollout and is **not adopted by this report**. Static target equilibrium does not establish dynamic reachability or identify the physical failure cause. Model mismatch, timing, parameterization and other controls/designs remain unresolved.

Likewise STOP's statement that this replay was an earlier-run reuse/no new launch is contradicted by the original receipt, `owning_study` and ledger. Exactly one fresh S11 start occurred; no duplicate send, physics charge or cost reset occurred. Original model text is retained for inspection.

The run exposes unfinished interface needs: mechanics warm-source prerequisites were not parameterized in `action_feedback`; compact facts did not prevent extensive field navigation; the next-request budget warning did not prevent a protected proposal; seed/STOP wrapper fallback pointers need correction in a future version. [Residual-gap audit](../../evidence/s11_mirror/remaining_interface_gaps.json) distinguishes observed errors from the code-level fallback issue. In accordance with the frozen protocol, none was repaired after seeing formal results and no replacement study/budget was used to improve the score.

## Q7. Was a feasible scheme found?

**No.** [Complete fresh design/control/task package](../../evidence/s11_mirror/study/design_package.json) is `best_valid_candidate`, `accepted=false`. It contains the unchanged two-segment/four-tendon structure, full 35?4 input, frozen task/evaluator and exact raw/result provenance. [Fresh control and acceptance](../../evidence/s11_mirror/best_control.json) and [independent audit](../../evidence/s11_mirror/independent_audit.json) retain all measurements.

| Original check | Fresh S11 value | Original bound | Result |
|---|---:|---:|---|
| Terminal position error | 0.074021789045062 m | ?0.01 m | Fail |
| Holding maximum position error | 0.104661091671770 m | ?0.01 m | Fail |
| Holding maximum speed | 0.683838678726421 m/s | ?0.02 m/s | Fail |
| Maximum normalized gap | 33.191933936321 | 0 | Fail |
| Solver errors | 0 | 0 | Pass |
| Force-bound violation | 0 N | ?1e-8 N | Pass |
| Complete execution / validity / six holding samples | Complete / valid / covered | Required | Pass |
| Independent original task evaluator | false | true | Fail |

The audit re-ran the **original registered evaluator on the saved raw samples** and recomposed full acceptance with the original protocol; both exactly matched the stored result. It also independently reconstructed task gap and checked actual applied tension arrays. This audit launched no new physics. Fresh physical time was 1.1041938 s; cumulative numerical time 2.7122741 s includes preparation. No pass/confirmation/SELECT occurred and no exploration was appended after STOP.

The **best overall available observation remains historical S10**, not new S11 science: evaluation `49c76e42767e0ab9870e7a18322bebc916215f721c955a7bbbba472ac72ab0ed`, source `62ddc2387077c5b49440d16208cd83d07d9108187e3e94df00043e4bfdb9557d`, gap 2.419092492282298, holding position 0.034190924922823 m and speed 0.068014941313063 m/s. Its full original [S10 package](../../evidence/s10_mirror/study/design_package.json) remains sealed. The fresh S11 package and historical best are kept distinct; no historical result is relabeled new or accepted.

Failure of this one schedule and protected exhaustion of decision opportunities do not establish task/structural infeasibility. Optimality, robustness, extra margin, hardware performance and repeatability were not studied.

## Freeze, authorization and artifact integrity

Implementation commit `72b933d5af87fb0317d5cce3b08f4c6723f00a1e`, freeze commit `6f6f3a52a287de431b80f4969a01750b7ecad791`, and preparation report commit `1f759fdbfa18d7a0d9201f9ecfc1afafa0bdad2a` were ordinarily pushed and remote SHA-verified. The scientific binding stayed at `6f6f3a52`; later documentation/exports did not change source/task/model/budget. No force push, history rewrite, unrelated worktree edit, credential commit or sealed S7?S10 modification occurred.

Automatic review initially rejected the S11 launch before process creation for missing specific payload/destination authorization. The user then explicitly authorized **???????study?** after the concrete review. [Authorization record](../../evidence/s11_mirror/provider_authorization.json) retains both events. The new run used `https://api.deepseek.com/chat/completions`, frozen `deepseek-flash` thinking/reasoning settings and the [reviewed project-only scope](../../evidence/s11_mirror/provider_payload_review.json): task, robot/family/control, optional S6 seed, scoped S7/S8/S10 history, numerical evidence, budgets, tool contracts and study conversation/reasoning/tool feedback. Keys/authentication headers and unrelated worktrees/files were excluded; S10 approval was not reused and no approval workaround was attempted.

[Final checks](../../evidence/s11_mirror/final_artifact_checks.json) verify **474 archive members**, original request hashes and response byte hashes, all 57 exact model tool request/feedback pairs, complete fresh STOP citations, unchanged scientific/task/history sources, settled receipts, no pending/occupied resources and no unconsumed response. Thirty sends have thirty unique responses; each has raw-received and decoded-usage metadata events (60 metadata snapshots, not 60 sends). The existing accounting deduplicates usage by request ID. Provider response replays were zero. The pre-run `prepared_checks.json` is retained as a historical preparation snapshot, not current research status.

Reused commands and entry points:

```powershell
python -m tools.research prepare --spec configs/research/study_s11_mirror.json
python -m tools.research bind --run-id s11-mirror-live-20261020
python -m tools.research run --run-id s11-mirror-live-20261020
python -m tests.research.s9_audit s11-mirror-live-20261020 evidence/s11_mirror --export
```

The existing `s8_audit` owns numeric/package verification, `s9_audit` accounting and `s10_audit.decision_chain` provenance; no new formal execution entry or duplicated milestone audit module was introduced. The Study is sealed; further scientific work requires a separately authorized, newly frozen Study, not a reset or extension of S11.
