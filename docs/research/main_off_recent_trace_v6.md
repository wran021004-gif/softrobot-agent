# Final Main-Off v6: smaller wires, safe continuation, inconclusive decisions

The final independently authorized probe used **7 Main requests, 0 Reporter requests, 0 mathematical/physical workers and no retries**. It verified materially smaller real requests, selective tool exposure, seven safe handoffs and offline SDK restore. Scientific-decision acceptance remains **inconclusive**: no diagnosis settled, no mathematical variables were submitted, and no SELECT or formal STOP was accepted. Do not start the formal cold-start Study on this evidence.

## Authorization and immutable scope

The user explicitly approved sending the necessary non-public C3 frozen task, candidate/control information, saved measurements/reports and Trace/recall content to `https://api.deepseek.com/chat/completions`, with an independent cap of eight Main requests including routes, zero Reporter/workers and no retries. The first automatic-review rejection occurred before process creation and sent nothing; it was resolved by this explicit payload/destination approval, not a workaround.

Repository commit was `2189a5ce31da2abdd784f463a732da542a79c50d`, branch `codex/english-native-decision-brief`, with a clean worktree. It contains tested implementation `b0a866a6869f84f9314e2ee38fd5af4120baba69` plus documentation. Store/grant ID is `main-off-recent-trace-v6-20261028` / `-provider-only`, independent of v1–v5. Frozen policies are `recent_round_trace_v1` (8 trace rows), `on_demand_tools_v1`, `bound_scientific_variables_v2` and `research_roles_v2`. Main uses `deepseek-flash`, thinking disabled, reasoning effort none, with no `max_tokens` generation cap.

The copied C3 scientific state intentionally retains original frozen implementation `7283d07d652d2a382e16e2ba33e9b99533572414`; this is distinct from the repository implementation tested above. Original evidence, candidate/profile identities, historical dependencies and guard mismatches are not migrated or repaired. No full scientific execution admission was run or passed.

## Actual actions and feedback

1. Main first selected `research_plan` / `diagnose`. Its next request saw only the focused diagnose Schema plus `research_route`.
2. It proposed an unresolved incomplete-braking versus oscillation question grounded in the recorded speed **0.04301 m/s versus 0.020 m/s**, using saved trajectory shape as a proposed discriminator. It chose registered method `endpoint` but omitted `decision.selected_candidate`. Original v2 Schema requirements rejected the Plan before settlement/execution. No candidate was inferred. The hypothesis was not a computed result or causal finding; method coverage was not validated by an actual analysis.
3. The next actual request received that error. Main switched to `evidence_read`, successfully queried a working-set inventory and candidate-bound mathematical method descriptions, then submitted two invalid reads: `view=fields` without required `fields`, and raw `view=full, pointer=/methods` on a candidate whose methods belong to the derived mathematical-capabilities view. Both errors produced truthful feedback and no scientific work.
4. Main switched back to diagnose, then selected the Recall tool instead of correcting/submitting a Plan. Request seven therefore selected Recall, but **no `research_recall(step=...)` executed**: the next send was blocked. Live step Recall behavior and subsequent correction remain untested. The stable recorded trace is `#76 diagnose: endpoint; rejected`, with no scientific execution/result.
5. No formal STOP was used to end the probe. The harness's eighth-request feedback reserve found no analysis feedback and stopped **before reservation or HTTP send**, retaining one unused request. It records `probe_inconclusive`, not scientific STOP or scientific budget exhaustion. The SDK wrapped this local cap in `APIConnectionError`; this was not an external connection failure or an eighth charged request. No retry or continuation was attempted.

The initial hypothesis is more specific than asserting static equilibrium proves holding speed, but seven requests did not establish a supported scientific diagnosis. Source queries, candidate omission, routing overhead and the very short cap prevented a complete decision/analysis/feedback path. The trial does not isolate which mechanism caused this outcome.

## Actual Provider accounting

| Main request | Complete bytes | Prompt | Completion | Exposed tools |
|---|---:|---:|---:|---|
| 1 | 22,434 | 5,678 | 90 | research_route |
| 2 | 31,344 | 8,028 | 687 | research_plan, research_route |
| 3 | 33,251 | 8,542 | 62 | research_plan, research_route |
| 4 | 26,662 | 6,811 | 294 | evidence_read, research_route |
| 5 | 30,419 | 7,795 | 285 | evidence_read, research_route |
| 6 | 29,468 | 7,658 | 85 | evidence_read, research_route |
| 7 | 31,605 | 8,086 | 76 | research_plan, research_route |

All seven responses were HTTP 200 with `finish_reason=tool_calls`. Totals are **52,598 prompt + 1,579 completion = 54,177 tokens**; prompt cache hit/miss are **8,960 / 43,638**. Provider elapsed sum is **11.859 s**. The independent ledger used seven model calls and nine public operations, zero backend solves and zero workers. The last selected-route feedback remains durably pending delivery because no eighth request was sent.

Actual currency cost was not reported. At the [official Flash rates](https://api-docs.deepseek.com/quick_start/pricing/) checked on 2026-10-28, the measured cache/output counts imply approximately **$0.007520 off-peak / $0.015040 peak**; these are rate scenarios, not an invoice.

First-request input fell from v5's 11,558 Provider prompt tokens to **5,678**, and complete wire bytes fell from 41,240 to **22,434**. Maximum input in this run was **8,542**, compared with v5's 24,707. Default SDK history was 162 bytes initially and 531 bytes after rotation, while the actual whole wires were 22,434–33,251 bytes. These observations establish shorter requests; seven different decisions totaling 52,598 tokens must not be presented as a controlled whole-task efficiency improvement over v5's eight requests/141,593 prompt tokens. The paired offline whole-workflow measurement, including three added routing turns, is reported separately in [the architecture/measurement report](recent_round_trace_and_tools.md).

## Safety, recovery and limitations

Ordinary request one advertised only `research_route` (853 Schema bytes). Every subsequent real request advertised that route plus one selected actual tool; no unrelated investigate/experience Schema or full mathematical union was sent. Focused diagnose Schema was 7,656 bytes including the router; selected evidence reads were 2,757 bytes including the router. No program-selected method or action was submitted on Main's behalf.

Seven handoffs committed through the existing verified snapshots. After stopping, `converse(restore_only=True)` ran with an HTTP-forbidden MockTransport: original registry/snapshot/Store identities verified, unmatched tool IDs were empty, no pending execution or unknown/unconsumed Provider response existed, the selected-route feedback remained preserved, and the ledger did not change. This restore created no new Provider request. Formal whole-result read delivery and SELECT/STOP credit were verified in the offline regressions; this live run did not exercise an accepted full-result SELECT/STOP or actual Recall call.

Two small post-run corrections were verified by three focused offline tests: JSON Schema errors now identify the missing field and reuse the original candidate-repair hint without exposing Schema internals; the harness recognizes only its exact pre-send cap through client wrappers, while real transport errors still propagate. Their effect on live decisions remains unknown. Original live requests, errors, raw log and Store are unchanged; no further Provider request was sent.

Complete real wires/response references, actual Provider usage, Main choices, feedback, trace, pending delivery and restore proof are in [live_validation.json](../../evidence/recent_round_trace/live_validation.json). Run `python -m tests.research.recent_round_live_audit` to read those original wires and append a restore-verification audit event; it forbids HTTP and never changes original requests, responses or receipts. There is no additional live allowance, successful mathematical computation, independent physical acceptance or readiness claim for a formal autonomous Study.

## Modified files and ownership

| Files | Responsibility |
|---|---|
| `tools/research/agent.py`, `__main__.py` | Automatic policy opt-in, native route/selected Schema loading, focused Plan validation, exact SDK continuation and compact repair feedback |
| `tools/research/config.py`, `contracts.py` | Versioned frozen policies and the small route/Recall contracts |
| `tools/research/research_context.py`, `session_handoff.py` | Stable bounded Trace, existing Store Recall, recent response/feedback units, full-read delivery and receipt recovery |
| `tools/research/task_constraints.py` | Registered scientific scope and static/dynamic interpretation limits |
| `tests/research/main_off_live_probe.py` | Independent policy opt-in, fixed role/worker caps and harness-owned probe lifecycle |
| `tests/research/test_recent_round_tools.py`, `test_bound_analysis.py`, `test_incomplete_session_recovery.py` | Targeted wire, source/credit, binding and crash-recovery checks |
| `tests/research/recent_round_wire_audit.py`, `recent_round_live_audit.py` | Offline paired request measurement and actual live-wire/restore audit |
| `docs/research/`, `evidence/recent_round_trace/` | Architecture, measured evidence, authorization/launch history and final outcome |

All work is on the designated `codex/english-native-decision-brief` worktree. Other worktrees, historical source Stores, frozen Studies and robot dynamics were not modified. No dependencies were installed. Implementation was committed/pushed before the live test; post-run corrections and evidence are a separate follow-up commit. The pre-live suite passed 38 cases, and the final post-run focused check passed three cases in 5.318 s; no Provider rerun followed those corrections.

Post-run code corrections were pushed as `a56588274338afddbd1fb3464a67442f1fb6e1da`. The user separately approved publishing this real report and `live_validation.json`, including Main choices/parameters/hypotheses, feedback, Trace, source identities and actual usage, to `wran021004-gif/softrobot-agent` on `codex/english-native-decision-brief`. This publication creates no Provider request and changes no scientific outcome or budget.
