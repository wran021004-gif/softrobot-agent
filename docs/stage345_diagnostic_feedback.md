# Stage 3.45: scoped diagnostic feedback

Implementation: `f5e4afa`, following `40eb8af`. Entrypoint:
`examples/stage345_diagnostic_feedback.py` (`prepare`, `run`, `export`).
The new store is `runs/stage345_diagnostic_cycle_20261002`; portable evidence
is `evidence/stage345_diagnostic_cycle_20261002`. Earlier runs remain intact.

`adopt` accepts a named recommendation within scope; `defer` postpones it
pending evidence; `reject` declines it. Defer/reject requires `next_action=stop`.
Bounded verification requires named adoption. Neither action automatically
executes a backend comparison. The coordinator continues the independently
authorized diagnostic check after any valid initial disposition.

Descriptions, normal instructions, validation errors and correction prompts
state these rules. The provider prompt includes a placeholder call example
generated from the actual advertised schema, including its domain fields,
reference shape, enum alternatives and version. Domain fields belong inside
the nested `arguments` object; a correction resubmits the entire provider tool
call, including outer `reason` and `tool_version`. The host never chooses or
rewrites the model's disposition.

The new request carries `saved_state_check`, distinct from evidence reading.
It binds authorized operations, model, horizon, integration, numerical limits
and configuration scope to the identified saved execution. A historical
read-only request grants no numerical execution. Both selection and execution
validate that scope. A temporary local parameter pair additionally requires
adoption of the exact parameter/value and a matching saved plan horizon.
Production controller changes and full backend simulation are excluded.

The frozen project ceilings are 24 provider attempts, 60 tool calls and
3,600 charged seconds, with zero backend solves and workers. Role ceilings
are ten design and fourteen diagnostic attempts, further restricted by the
model-authored diagnostic request. Numerical ceilings remain six local solves
and 24 prediction evaluations, but only one selected check may execute.

| Phase | Provider capacity | Protected downstream capacity |
| --- | --- | --- |
| Design request | 3 | 7 design + 14 diagnostic |
| Initial diagnosis | 4; two successful reading turns | At least 6 diagnostic + 7 design |
| Initial design response | 3: submission plus two corrections | At least 6 diagnostic + 4 design |
| Check selection | Up to 7; 3 under the minimum ten-attempt diagnostic grant after four initial attempts | 3 diagnostic revision + 4 design |
| Revised diagnosis | Shares the ten-attempt check/revision ceiling | 4 design |
| Final design response | 4 | Workflow ends |

Time and tool reservations cover the same downstream phases, including the
executor's one call and up to 300 seconds. The provider transport timeout uses
the same available phase/role/project time as reservation. Role usage and
total correction counters remain cumulative across transitions. Exact
allocations, source identities, implementation hashes, provider configuration
and acceptance criteria are in `freeze.json`.

Nine focused checks passed: eight in 70.254 seconds, then one successful-result
citation check in 2.214 seconds. They cover legal dispositions, actionable
errors, complete-envelope recovery, independent continuation, minimum-grant
downstream capacity, request/executor scope, transport reservation, required
reading views, and previous-report/feedback/revision/final-response linkage.
The initial sandbox invocation failed in temporary SQLite fixture setup before
assertions. The executable checks used normal filesystem access. No paid smoke
test was run. The broader historical combination suite was not rerun and
remains uncertified.

The preserved Stage 3.41 baseline reached tolerance with terminal error
0.007642608585867386 m. Sampled settling failed: terminal speed
0.6351726092425104 m/s and final-window maximum 1.5810152739742807 m/s.
Timing failed: mean update 17.075238151415917 s and 35/35 deadline misses.
These observations do not establish a cause. Physical improvement is not
evaluated in Stage 3.45.

The single live attempt **stopped before a validated first design response**.
The design model used three attempts to read evidence and submit a scoped
request (`20157e7cacb2cf2168802883fa57628c76b9b737f3837f4c58c2fbe09e9c6d3c`).
The diagnostic model read prediction, motion and plan views in one sequential
batch. Its next two submissions were rejected for schema errors; its fourth
attempt delivered the initial report
(`d09aac60283888393a69eca979512cc512aa6592b3a184336911af662f30bf5f`).

All three initial design-response attempts were available and consumed. The
first two printed a JSON tool-call wrapper in ordinary assistant content and
returned no native tool call. The third emitted a native tool call but supplied
the nested domain `arguments` as a JSON string instead of an object. None was
accepted or interpreted as a design decision. The exact stop was
`MODEL_PROTOCOL_CORRECTION_CONSECUTIVE_LIMIT: INVALID_TOOL_CALL_ENVELOPE` at
`choices[0].message.tool_calls[0].function.arguments.arguments`. The host
preserved the existing limit of two consecutive protocol corrections.

| Requested outcome | Live result |
| --- | --- |
| Scoped request and initial report | Validated |
| Initial handoff, including design response | Not completed |
| Check selected and executed | Not completed |
| Feedback consumed by diagnostic model | Not completed |
| Revised report validated | Not completed |
| Design response to revised report | Not completed |
| Numerical outcome | No new evaluations |
| Physical improvement | Not evaluated |

Exact usage: **10/24 provider attempts, 12/60 tools,
425.7620000001043/3600 charged seconds, zero backend simulations, zero local
solves, zero prediction evaluations and zero workers**. Design used six
attempts and diagnosis four; two protocol corrections were consumed. Four
design and ten diagnostic attempts remained, but the frozen initial-response
phase and consecutive correction allowance were exhausted. No guard or budget
was reset and no additional paid attempt ran.

`outcome.json`, `workflow_failure.json`, `model_decisions.json`,
`role_transitions.json`, `receipts.json`, `role_usage.json` and the `artifacts/`
bundle retain the stopping point and raw evidence. `live_source_sha256.json`
identifies the exact frozen implementation. Source manifest and configuration
identities still match the Stage 3.41 original.

Report validation establishes schema, linkage and exact selected values; it
does not certify all prose. A separate read-only review found unsupported
evidence-gap statements: the retained controller-observations file has 35
one-step prediction records and 35 applied-tension records, and resolved
physics supplies all six 8 N force limits. The two selected aligned views do
not establish absence of other retained predictions. The report's speculative
braking/settling-timescale explanation remains untested. These findings are
recorded in `delivery_review.json`; the model-authored report is unchanged.

A subsequent **offline-only prompt clarification** states explicitly that the
model must invoke native `tool_calls`, must not print the example as assistant
content, and must keep nested domain arguments as an object. One focused test
replayed the three observed malformed responses, verified rejection, and
checked a properly structured native call (2.318 seconds). See
`post_live_repairs.json`. This clarification is **not live-validated**; the
frozen live implementation remains `f5e4afa`.

The first launch was blocked by automatic approval review over external
payload authorization. After the user's delegated attachment was inspected
for explicit DeepSeek and Stage 3.41 evidence-sharing instructions, the same
unchanged launch was approved. The rejection created no guard or provider
call; `launch_review.json` records this distinction.

This evidence does **not** justify proposing a future single-factor matched
control comparison yet: the necessary selected check, consumed feedback,
revised report and explicit design response were not obtained. No comparison
or improvement occurred.
