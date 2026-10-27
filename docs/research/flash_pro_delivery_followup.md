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

The first v2 launch was rejected by automatic review before process creation,
with zero requests. In response to review's request for low-risk evidence,
unauthenticated HTTP checks confirmed the GitHub repository is public and all
three exact task/evidence source files return HTTP 200 with JSON equal to the
local committed inputs. These checks and source URLs are retained in the v2
payload review. No alternate Provider route or private payload is used.

## Completed v2 cohort

After the public-source checks, automatic review approved the same launch.
All four cases completed, using nine actual requests and nine confirmed HTTP
200 responses, below the 24-request cap. No science worker, physics step,
Reporter or C Study operation occurred. Results and original ledger counters:
`evidence/integration_research_next/flash_pro_decisions_v2.json`.

| Case | Model | Requests including final answer | Evidence reads | First valid Plan request | Total tokens |
| --- | --- | ---: | ---: | ---: | ---: |
| BF5 failed baseline | Flash | 3 | 1 | 2 | 23,255 |
| BF5 failed baseline | Pro | 2 | 0 | 1 | 19,528 |
| BF6 incomplete | Pro | 2 | 0 | 1 | 12,374 |
| BF6 incomplete | Flash | 2 | 0 | 1 | 10,802 |

Flash totals: five requests, one read, 34,057 tokens. Pro totals: four requests,
zero reads, 31,902 tokens. Combined actual usage is 49,647 prompt + 16,312
completion = 65,959 tokens; 10,239 reasoning tokens are already included in
completion. Prompt cache hits/misses were 30,720/18,927. Currency was not returned.
Observed Provider receipt wall time was 48.266 s for Flash and 100.360 s for Pro;
these uncontrolled sequential measurements do not establish a general speed or
price ratio. Pro's 6.3% lower total-token count here is not a currency claim.

There were no tool refusals. All four Plans passed the partial production
schema/reference/intent checks and all four received final prose. Read attempts,
including rejected attempts, fell from nine in v1 to one in v2. Tool-schema JSON
size fell from 10,617 to 7,502 characters using the same measurement. Pro made
both decisions directly from inline evidence. Flash still requested the BF5
summary, then submitted its Plan; BF6 needed no extra read. This is evidence
that clearer delivery can reduce reads under the tested interface. The bundled
changes and tiny cohort do not isolate a model-versus-context causal percentage.

V1 had only one valid partial Plan and no final answers before its cap; v2 has
four valid partial Plans with final answers. Its higher total token usage cannot
be interpreted as a regression against unfinished v1 outputs. Both cohorts are
retained: 17 actual requests and 112,139 total tokens cumulatively. The rejected
launches sent zero requests and incurred no recorded Provider usage.

## Evidence-understanding review and model decision

Format compliance improved; scientific interpretation still needs care:

- Flash BF5 recognizes the failed baseline and missing objective errors, but
  sometimes treats the tiny search budget as an established failure cause and
  treats STOP as if it implied infeasibility. Its final response is verbose.
- Pro BF5 uses inline facts immediately, but conflates unmeasured Native
  acceptance with missing complete independent acceptance even though the
  independent `valid_failure` status was supplied. It overstates DIAGNOSE as the
  only legal proposal; descriptive STOP was available.
- Pro BF6 correctly preserves incomplete/null status and names mass/COM, but
  calls the load valid without an independent binding check. It reports Native
  cost without clearly distinguishing the aggregate 452-step lower bound and
  453 attempted calls, and labels read-only diagnosis `empirical_search`.
- Flash BF6 correctly separates format validation from scientific admission,
  but explicitly mixes one stage's 226 steps with the aggregate 453 calls,
  despite the supplied 452 completed-step lower bound. It also treats out-of-scope
  C data as missing and mixes A registration with physical/structural failure.

All four final answers undercount Provider requests by one: they count tool
rounds and omit the request producing the final answer. The published counts
come solely from settled LiveBoundary receipts. Model prose is not a cost owner.
No valid Plan is relabeled as a fully correct scientific conclusion.

Pro reduced round trips in these two cases but did not remove interpretation
errors, and its observed Provider wall time was longer. There is still no basis
for changing the frozen C Study's model or claiming improved physical research
performance. The immediate gain is a clearer existing interface; further model
selection should use completed decisions, factual accuracy and actual cost
together, rather than format validity or self-reported budgets alone.

## Read budget

No independent hard read budget or current Study policy was introduced during
the comparison. The user's follow-up question was addressed by recording reads
and identifying the one extra query of already inline facts. An exact repeated
reference/pointer/view is a useful diagnostic, but `summary` followed by `full`
can legitimately add information. A future cap must preserve mandatory public
acceptance reads before SELECT and share the existing admission/accounting
boundary; simply blocking all reads after a low count can prevent legal closure.
Here, reads dropped to one without a new hard limit. The production handoff
change was verified offline; this live cohort did not exercise actual handoff.

## Subsequent C formal Study closeout evidence

C delivered its independent closeout in `da096fc0b`. A reviewed the committed
sanitized audits only; no private Store, design/control package, runtime or
configuration was imported. A compact provenance-bound review is in
`evidence/integration_research_next/c4_closeout_review.json`. This is additional
observational evidence, not another Flash/Pro comparison or a new experiment.

The formal Flash Study legally stopped without a solution, with no final
engineering blocker and without exhausting its budget. It still had 22
mathematical units, seven shared physical launches, four fixed replays and 17
Provider requests (including protected allowance). The best independent result
had terminal error 9.7163 mm (passes 10 mm), holding error 10.3096 mm (fails
10 mm) and holding speed 20.6248 mm/s (fails 20 mm/s). No SELECT or task pass.

The last saved discovery checkpoint still supplied `structure_actions.search`.
Controlled structural sensitivity was registered/authorized, with the missing
validated stencil an unprepared prerequisite rather than a prohibition. The
Agent submitted no structural search or sensitivity, kept numerical work on one
two-segment/six-tendon structure, then stopped on local control stagnation.
The initial `heuristic_generate` rule applied to the first legal structure;
mathematical structure comparison was available afterwards. Thus final legal
STOP does not validate the Agent's substantive claim that useful routes were
exhausted, nor prove a global physical tradeoff or structural infeasibility.

The read audit records 135 attempts and 57 complete-read records, classified as
45 new queries, ten exact repeats, one covered subnode and one changed-content
read. It also reports 30 repeated query signatures. These totals do not mean
135 wasted reads: previews and dynamic method/working-set views need different
interpretation. Of 102 main requests, 67 were read-only; 30 included illegal
tool feedback, some caused by documented engineering presentation/intervention.
Neither aggregate is entirely attributable to model error.

C's separate cost is 111 confirmed Provider requests (102 main + nine Reporter),
7,547,550 tokens (6,713,318 input + 834,232 output; 743,742 reasoning included),
with currency unknown. Scientific work used 14 mathematical units, 11 Native
searches/891 internal rollouts/891,000 steps, one NMPC run and eight fixed
independent replays. These costs are not combined with A's two Provider-only
cohorts, and no raw reasoning is imported.

This closeout strengthens the evidence that research-route selection and
stopping judgment are additional Agent limitations. Delivery defects were real
and required repair, but cannot account for all observed inefficiency. Read
limits can contain cost; they cannot make an Agent test an unexamined mechanism
or justify stopping. There is no paired formal Pro run, so the closeout still
cannot establish that switching models would produce a physical solution.
The closed Study and all original receipts remain unchanged; no new Study starts.
