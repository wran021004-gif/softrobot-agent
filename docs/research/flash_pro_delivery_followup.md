# Information delivery repair and Flash/Pro follow-up

2026-10-27, Asia/Shanghai. Branch: `integration/research-next`.

## Problems and applied changes

| Observed problem | Minimal change |
| --- | --- |
| A selected evidence object with a large sibling array could lose J, stop_reason and small metrics at handoff. | Selectively integrate C's `e83998a15` into the existing handoff module: retain scalars/small fields within the existing 3,000-byte bound, list omitted keys and preserve the original query. Small feedback stays exact; summaries retain preview semantics and grant no complete-read credit. |
| Pro wrapped the Plan in a `plan` property. | Clarify the existing production tool description: arguments are the Plan itself. No wrapper repair or relaxed validation. |
| The prior probe required a read before seeing the case evidence. | Supply the exact same public scalar evidence inline, alongside its reference. Static reads remain optional. This is a probe projection, not a scientific registration or SELECT read receipt. |
| Read-only decisions carried unused execution payload fields. | Reuse the original `agent_math_decision_probe.decision_schema` projection of production Plan for diagnose/stop. No new contract, dispatcher or framework. |
| Probe refusals lacked the ordinary correction path. | Reuse production `error_feedback`, including bounded reason, existing expected hint and zero-worker/cost facts. Retain rejected inputs locally. |
| Two requests left little room for decision correction and follow-up. | New independent cohort: six requests per case/model, at most 24 total, same 8,192 output-token cap and thinking/high settings. No automatic retries. |

The existing static-view schema restriction, exact T1/T2 method queries,
saved-evidence-only T2 prerequisites and actual sequence-dimension refusal facts
remain in place. The current C Study, its model, configuration, Store and running
implementation are not changed.

## Targeted verification and frozen live protocol

Five offline checks passed: two selected-evidence handoff checks; one original
Harness/ledger case with an invalid wrapper, ordinary refusal, corrected Plan
and final response; one actual SDK request-boundary rotation check; and one
existing large method-read handoff regression. Network Provider requests and
scientific workers in these checks were zero; mock usage is synthetic.

`configs/research/provider_flash_pro.json` now identifies
`provider_decision_public_only_v2`. Its new ignored directory is
`runs/flash-pro-public-v2`; v1 Stores, SDK history, frozen inputs and the published
46,180-token bill are retained unchanged. Both public case JSON values were
checked equal to v1 before live execution. No candidate/control, private research
receipt, trajectory or C Study data is added. Outbound scope is recorded in
`evidence/integration_research_next/provider_payload_review_v2.json`.

Both models get the same frozen instructions, cases and schemas. BF5 order is
Flash/Pro and BF6 Pro/Flash. We record actual requests, first valid decision
request, tool reads/refusals, final-response presence and original token/cache
counters, plus a manual review of evidence understanding. No science worker,
Reporter, solve, physical replay, SELECT or STOP is executed. A parsed decision
does not establish full scientific admission.

This follow-up changes delivery, schema scope and request cap together. It can
compare the models under the repaired interface and describe changes from v1;
it cannot assign a causal percentage to context versus model, rank general
research ability or establish physical progress. Cache state is uncontrolled;
currency remains unknown unless actually returned by the Provider.

Live results will be appended after the bounded cohort finishes.
