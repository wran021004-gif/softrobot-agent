# Recent research rounds, Store recall and on-demand tools

New Studies can opt into automatic verified Session Handoff and on-demand native tool Schemas. This reuses Strands' registry, the existing Store, original receipts, `handoff()`, `pending_feedback_delivery()` and the accounted transport. Historical Stores, saved requests, studies and budgets are not upgraded or reset.

## Frozen configuration

Add these fields to a **new** English Study's existing `research_decisions`, retaining its role policy and scientific settings:

```json
{
  "conversation_policy": {"version": "recent_round_trace_v1", "trace_limit": 8},
  "tool_schema_policy": {"version": "on_demand_tools_v1"}
}
```

The trace limit accepts 6–10; on-demand tools require this conversation policy. Absence retains the prior behavior. `research_decisions.history` keeps its original import meaning. `converse()` automatically enables handoff for the new policy, still requiring the existing live-handoff admission and `request_feedback` boundary admission. The CLI supports `--session-handoff` / `--no-session-handoff`. Policy configuration does not authorize Provider communication or scientific execution.

The existing isolated probe accepts `--conversation-policy recent_round_trace_v1 --tool-schema-policy on_demand_tools_v1 --analysis-interface bound_scientific_variables_v2` with a new `--probe-id` and independent `--live --authorization`. Its eight-request cap includes routes; Reporter and worker allowances remain zero. Existing directories cannot be reset, and continuation must match the frozen policies. No formal Study is started by configuration or preparation.

## Context and safety

Current `research_decision_brief_v3` retains the task, verified numbers/units/sources, candidate/control links, latest sourced Reporter interpretation, execution status, budgets and closeout rules. The most recent round groups an actual Main request with its settled tool feedback. It retains choices, actual outcomes, errors and exact sources; oversized ordinary payloads are labeled partial projections with original navigation. It is not an arbitrary last-two-message slice. Reporter internal reasoning and raw model reasoning are excluded.

Earlier SDK conversations remain in original snapshots and Store artifacts. A clean session contains the existing identity-bound initial message and a regenerated packet. Default history contains eight recent scientific actions plus at most two older unresolved failures, total count and pagination. Complete trace/receipts remain in Store, not another enlarged L0 field.

Every paired-feedback or completed-invocation boundary is considered for automatic rotation. Existing checks verify the original Provider response, tool IDs/statuses, durable snapshot, settled receipts, delivered reports and Store identities. Active workers, pending execution and unsettled outcomes defer rotation. Unknown Provider outcomes block new sends. Integrity/pairing failures remain errors. The original token threshold and hard context guard remain in force. Rotation adds Store/snapshot I/O and **zero model requests**.

Explicit original root `evidence_read(view="full")` bypasses compact feedback limits: exact original feedback reaches Main through the verified handoff packet, even when large. The hard context guard still checks the entire request. Formal coverage is earned only after the complete value appears on a confirmed Main wire. Recall and summaries do not earn it.

Saved-response recovery restores original system text, tool definitions and packet verbatim. Public `invoke_async(None)` resumes a durable unsent prompt or paired feedback, avoiding an extra prompt that would change the request hash. The transport still verifies the entire saved wire before replay without charging another send. Route/Recall receipt recovery reconstructs settled feedback without reexecuting the operation.

## Trace and Recall

Step numbers use the durable Store event sequence of the original native request, or the original Plan event for engineering actions. They can have gaps and differ between independent Stores; they remain stable across handoff/restart within one Store. Existing events/plans/receipts deterministically supply the mapping, without another history database.

Recorded offline fixture examples (no scientific worker ran):

```text
#139 diagnose: equilibrium; read_only_diagnosis_completed
#160 research_analysis; probe_only_not_executed
#203 stop: equilibrium; rejected
```

```python
research_recall()                         # First bounded page
research_recall(offset=8, limit=8)
research_recall(step=139, view="summary")  # Use an actual returned step
research_recall(step=139, view="details")
```

Details use the first original scientific result when present, otherwise the original Plan/tool feedback envelope. Returned `detail_source` identifies the base for relative `pointer` and `fields` queries. Feedback envelope text remains original text. Summary/detail responses distinguish unexecuted requests, rejected input, recorded scientific results and execution requiring receipt inspection. Existing evidence reads run with `record_read=False` and bounded navigation. Source/receipt/result identities are resolved by the program; Main does not construct SHAs. Protected closeout's original source restrictions still apply, and its directory excludes ordinary Recall. SELECT/STOP retain their original evidence and inference admission.

## On-demand Schemas

Ordinary requests expose **only `research_route`**. The compact L0 directory lists tool names, short purposes, request-validation availability, Plan actions/RL operations and resource implications, without parameter definitions. Routing records Main's choice in Store, performs no science and grants no execution/evidence authority.

After `research_route(tool="research_plan", action="diagnose")`, the next request exposes the small route plus only the focused diagnose Schema, removing unrelated generation/search/control payloads. STOP likewise retains mandatory hypothesis, decision and evidence fields. Inputs pass the advertised JSON Schema and original Pydantic/dispatcher/admission boundaries. The program never fills a missing scientific field.

Consecutive operations may reuse a loaded tool. Switching tools/actions costs another route request. A settled Main diagnosis selecting an owned candidate and method directly loads the existing method-specific `research_analysis` Schema, avoiding a redundant route. The existing binder still converts Main's scientific variables into the full frozen request. The program selects neither a method nor a scientific direction. The transient SDK `retrieve_context` Schema is absent from this opt-in wire; permanent Store navigation and exact full-result delivery remain available.

Protected closeout filters the directory and checks both loaded Schema and actual operation against original permitted actions. An unavailable route fails without science dispatch or additional allowance. Old Studies retain their original tool exposure and saved-Schema recovery.

## v5 cost diagnosis and paired offline wires

The eight original v5 requests are read-only. Its 145,847 total tokens comprise **141,593 Provider prompt tokens + 4,254 completion tokens**. For requests 1–6 the L0 message remained 13,508 bytes, while SDK history grew from 164 bytes initially to 48,611 by request eight. Initial tool Schema was 26,745 bytes, rose to 30,619 with selected analysis, and fell to 13,688 in closeout. History growth and substantial fixed Schema cost both matter.

The audit preserves real request identities and Provider usage separately from local estimates. Mutually exclusive encoded byte spans cover system, tools, current L0, older SDK messages, recent feedback, Trace, directory and framing/other; they sum to the complete request. Fragment token counts have BPE boundary effects and are not additive API accounting. The fixed local tokenizer SHA is `89085f12ef79460ac5f66d1119325ddfc694b4ab209d80bbd81d35f081dc9614`; it is not a Provider invoice or assurance of the current model's tokenizer identity. Store retains parsed original requests: normalized httpx key order may differ, but all eight reconstructed byte counts match saved transport measurements.

The paired **actual SDK/Mock HTTP** workflow starts from the same frozen pre-decision C3 state and replays v5 replies 1, 2, 6, 7 and 8: consecutive reads, diagnosis, mathematical variables, and the saved feedback-based response with its invalid STOP. It is a complete bounded interface path, not all eight original live decisions. The routed variant inserts three explicitly scripted route choices. It does not establish new model behavior or a successful STOP. Production Strands/httpx serializes every request into MockTransport. New fixture usage is explicitly zero; no API send or worker occurs. The original database SHA is unchanged, authoritative verified facts match across variants, and Recall gives no formal credit.

| Offline path | Requests | Complete bytes | Local input tokens | Input USD, all-miss off-peak | Input + fixed-output USD, all-miss off-peak |
|---|---:|---:|---:|---:|---:|
| Original context / full tools | 5 | 290,270 | 78,179 | 0.011727 | 0.013674 |
| Recent round + Trace / full tools | 5 | 270,216 | 71,579 | 0.010737 | 0.012684 |
| Recent round + Trace / on-demand tools | 8 | 235,832 | 65,821 | 0.009873 | 0.011939 |

| Routed request | Stage | Actually exposed native tools | Bytes | Local input tokens |
|---|---|---|---:|---:|
| 1 | ordinary_decision | research_route | 22,427 | 6,353 |
| 2 | tool_execution | evidence_read, research_route | 26,336 | 7,391 |
| 3 | tool_execution | evidence_read, research_route | 32,149 | 9,480 |
| 4 | tool_selection | evidence_read, research_route | 28,515 | 8,052 |
| 5 | tool_execution | research_plan, research_route | 31,279 | 8,487 |
| 6 | tool_execution | research_route, research_analysis | 32,161 | 8,800 |
| 7 | tool_selection | research_route, research_analysis | 32,303 | 8,807 |
| 8 | tool_execution | research_plan, research_route | 30,662 | 8,451 |

The first routed request sends 853 Schema bytes. Its complete wire is 45.9% smaller than the paired original first wire. Whole-workflow estimated input falls 15.8%, while request count increases by three. L0 adds current control and recent feedback, so some history is replaced by bounded state; the complete-wire measurement includes this replacement.

Cost scenarios use the [official Flash price page](https://api-docs.deepseek.com/quick_start/pricing/) checked on 2026-10-28: per million input cache-miss tokens $0.15/$0.30, cache-hit $0.003/$0.006 and output $0.60/$1.20, off-peak/peak respectively. Output scenarios reuse saved completion counts plus locally estimated scripted routes. Future output, cache behavior, latency and charges remain unknown. Routing increases this bounded path from five to eight requests and can exhaust a short probe before analysis is reached; smaller Schemas alone do not prove lower autonomous-study cost.

Per-request/component estimates, cost scenarios, stages, exact source identities and a Recall sample are in [offline_wire_audit.json](../../evidence/recent_round_trace/offline_wire_audit.json). Trace, Recall and handoff introduce no extra LLM. Only explicit route turns add requests.

## Scientific and lifecycle boundaries

Existing registered method views now supply `scientific_scope`: computation meaning, model sources/operating points, source requirements, task quantity coverage, mathematical execution, missing evidence and independent physical acceptance. These come from original registrations/applicability, not Reporter judgment or another registry. Equilibrium remains selectable for static diagnosis; its description explicitly excludes holding-window maximum speed, structure/control causal attribution and interpreting solver failure as infeasibility. Scope is loaded with selected-method guidance.

The harness records `probe_completed`, `probe_inconclusive` or `probe_budget_exhausted`, independently of formal STOP. Tool dependencies and test allowances are not scientific falsification. Mandatory `Plan.hypothesis`, SELECT/STOP ordering, exact citations and inference checks are retained. Historical scientific dependency mismatch is not repaired or treated as passed. Robot dynamics and formal scientific execution readiness are unchanged.

## Validation and final live boundary

38 targeted tests passed in the final combined run (94.035 s): recent-round/routing/recovery checks, request-boundary handoff and mathematical-binding regressions, incomplete-session recovery cases, and original formal-read/selection regressions. The latest recent-round continuation adjustment also passed its direct SDK directory/reuse check. `compileall` and `git diff --check` passed. Scripted interruptions intentionally log exceptions; these are asserted recovery paths, not failed tests. The actual SDK/Mock HTTP audit passed all byte partitions, verified-fact equality, read-credit, no-worker and source-integrity assertions.

The old incomplete-recovery fixtures also failed at unmodified HEAD before any Mock send because host readiness was not mocked. Their setup now explicitly mocks that irrelevant environment boundary, leaving production preflight unchanged and allowing the intended SDK recovery checks to run.

The user subsequently authorized one final independent Main-Off test, conditional on smaller wires and successful offline correctness checks: eight Main requests including routes, zero Reporter, zero scientific/physical workers, no retries, a new Store/grant, no formal Study. The tested implementation was committed and pushed as `b0a866a6869f84f9314e2ee38fd5af4120baba69`.

The launch was rejected by automatic approval review **before process creation**. The review requires explicit permission for the particular non-public C3 evidence payload and the DeepSeek destination (`https://api.deepseek.com/chat/completions`), beyond the bounded probe approval. No new probe directory, grant, HTTP attempt, cost or Provider result was created. The exact payload/destination/budget permission has been requested separately; no workaround or indirect send is used. Prior Stores and grants remain unchanged. Formal autonomous Study readiness remains unproven: scientific dependency mismatch persists, and no new mathematical or independent physical execution has been admitted or performed.
