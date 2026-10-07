# Research Mainline 2: evidence, operations, context and recovery

Engineering implementation on `feat/gvs-dynamics`, 2026-10-07. The normative
[Mainline 1 handoff](research_starting_point_v1.md), including its six-mainline
roadmap and scientific scope boundaries, is unchanged. This work does not reopen
a campaign or provide scientific execution authority.

## Implemented work packages

| Package | Shared behavior and covered public consumers |
| --- | --- |
| A — operations and stopping | `batch_budget.operational_view` uses existing Store accounting, reservations, protected capacity and deadline calculations. Scheduler capabilities, plan validation, current-authority snapshots and report completion expose source-bound operational facts. `stop_interpretation` separates legality, checked assertions, success and unassessed optimality. |
| B — comparison prerequisites | `research_tasks.compare_acceptance` checks declared schedule, receipts, execution and protocol-required source bindings, required component completeness and outcome consistency, task/metric meanings and freshness before ranking. Fixed research and campaign verification use that shared gate. |
| C — roles and authority | Explicit selection roles distinguish incumbent at STOP, frozen challenger and promoted deliverable. Recovery keeps historical state intact and adds a current execution projection. Active supported research requests refresh authority; Host and send checks retain dependency, phase, grant and deadline enforcement. |
| D — bounded context and retrieval | Relationships and the complete canonical archive cover authorized history before selection. Research requests inline deterministic current-decision facts and their execution/source bindings; unrelated facts and historical aliases remain archived. Current hypotheses and counterexamples select required evidence. Existing `evidence.read` resolves offloaded role sources through Host validation and the scoped, hash-checked archive. Complete serialized requests are checked before credential loading and transport. |
| E — lifecycle | Saved results, hypothesis updates, compaction, request construction, durable checkpoint, fresh-process restore and next-request preparation share the working-state implementation. Completed, pending, unknown and sealed work cannot be blindly replayed. |

Historical accounting is checked against the event prefix at its saved sequence
and explicit time cutoff. Current executable capacity is then computed against
the current clock. A legitimate reduction in remaining seconds does not invalidate
recovery. Offline tests use a controlled clock; a historical deadline or menu
cannot restore expired authority. Incompatible historical dependency freezes
remain blocked, including the old narrowly authorized V3 migration.

Fresh repetition is the default for the frozen verification protocol. A declared
protocol can explicitly permit labeled historical reuse for a nonfresh slot.
Even an original producer receipt, when reused, cannot satisfy a fresh slot.
Saved older aggregates remain readable; re-establishing a comparison requires
their original receipts and declared schedule. No acceptance threshold changed.

The saved twenty executions still give joint counts **6/10 versus 7/10**, with
all terminal reach tests passing and neither full joint suite passing. Selection
uses the original primary acceptance rule and retains the physical tradeoffs.
The incumbent at the original STOP remains `batch-ebbeadbdaca10732-0`; later
promotion selects `batch-396bdbbae02626d3-0` for delivery. Exact evaluator terminal
values supersede rounded/profile projections in derived views; originals remain
available as legacy source values.

A 2000-second allocation versus a 2590-second requirement has a 590-second plan
shortfall. Zero actual shortfall says the requirement fits, not that capacity is
zero. Settled costs, outstanding reservations and released capacity are separate;
an unsettled publication snapshot is not final actual cost. Report phase evidence
separates the earlier seven-repair boundary from the later authorized eighth
repair ceiling, without claiming the eighth was used merely because authorized.

## Focused offline validation

Results and exact commands are recorded in
[verification.json](../evidence/research_mainline2_20261007/verification.json) and
[lifecycle.json](../evidence/research_mainline2_20261007/lifecycle.json).
All 51 distinct focused checks pass across the recorded batches and targeted
repairs; the blocked older scheduler fixture is excluded from that count.

The checks cover saved positive comparison and missing/cache/foreign/incomplete
negative cases; explicit protocol reuse; tradeoffs and stopping meanings; the
2000/2590 distinction; reservation, unknown-operation and settlement behavior;
historical cutoff checks, elapsed capacity decay and expiry; immutable grants and
dependency seals; role separation; real Host archive paging/scope/tamper/grant
checks; complete outgoing object overflow with an offline transport recorder;
and actual saved research/reporting builders.

The coherent lifecycle preserves all **256 canonical facts**, role and STOP
bindings, hypothesis history, counterexamples, budget/phase snapshots and **40
explicitly synthetic pending entries** in a fresh subprocess. Both recovered
request purposes fit their declared unchanged limits. No request is sent.
Protected original ledgers, clock, authority index and scientific state hashes
are checked before and after that lifecycle.

That original fixed-fact/pending-entry lifecycle is historical evidence, not a
demonstration of bounded input as distinct experimental facts grow. The closeout
below measures that separate case without replacing the original 51-check record.

Saved diagnostic visibility is also recorded: the executor's evidence query,
the explicit return handed to the design role, and the actual saved principal
input are separately source-bound. Derived displayed handles are labeled as
derived visibility. They do not establish that the principal personally read
all original artifacts, or that any causal explanation is true.

The older `test_research_scheduler` fixture cannot prepare its historical
campaign under current implementation seals (`HISTORICAL_UNREVIEWED_IMPLEMENTATION_CHANGE`
for the candidate implementation). That seal was not bypassed. Public scheduler
decision validation and request construction are instead checked using the
supported isolated decision-recovery fixture. No full repository suite, live
campaign command, diagnostic rollout, backend or solver was run.

## Limits and Mainline 3 handoff

Token measurements are conservative estimates from complete serialized UTF-8
bytes plus framing/reserves, not actual provider token usage. The request's
declared builder protocol determines the cap: a final `research.decide` turn
uses the research cap; report-only builders declare the report cap. Report-only
paths prefetch required facts and explicitly advertise no archive read tool;
if required material cannot fit, preparation fails. Configured provider/model,
endpoint, reasoning, limits, timeout, TLS and proxy settings are unchanged.

There is **no live-model behavior validation**. Valid references and complete
inputs do not certify causal prose, global optimality, real-time feasibility,
or future model accuracy. New provider requests, backend executions, controller
solves and scientific experiments are all **zero**; no credentials were loaded.

Mainline 3 can use the preserved exact result bindings, incomplete/failed cases,
phase-bound capacity, explicit freshness protocol, current role mapping and
saved diagnostic visibility as inputs. Any future executable campaign needs its
own current authorization, deadline and compatible implementation freeze. This
change does not enlarge the old migration permission, alter task thresholds,
expand parameter pools or start new research.

## Bounded three-gap closeout, 2026-10-07

Gap A is closed at the shared assembler. Selection uses existing current roles,
question/case membership, feedback and active comparisons, current named
hypotheses/latest round interpretations, exact supporting/counterexample
selectors, and relevant repeat partners. Role/relationship anchors require core
decision metrics; a cited metric or source retains its additional required facts.
Both sides of an active comparison remain available. Historical fact values,
IDs, source bindings and full-history coverage/repetition calculations are
unchanged. Unrelated execution rows, structure definitions, aliases, membership
lists and chronology are not alternative inline archives.

The complete archive remains in `canonical_fact_reference` and the outgoing
`working_context.fact_archive` reference at `/facts`. Existing `request_facts`
and renderers resolve the full request-scoped archive; recovery retains
`current_facts`. Audits distinguish archived, inline and offloaded counts from
explicit retrievals; Host's read ledger records public retrieval. Retention does
not claim model visibility. Reports with complete prefetch/no read tool continue
to require the entire dataset. Required sets that cannot fit fail with
`CONTEXT_PREPARATION_REQUIRED_MATERIAL_EXCEEDS_BUDGET`; no limit or output reserve
increased.

[Growth evidence](../evidence/research_mainline2_closeout_20261007/growth.json)
uses saved records plus distinct, explicitly synthetic historical executions
and authoritative evaluation/profile bindings. These are engineering fixtures.

| Added synthetic executions | Archived facts | Inline facts | Offloaded facts | Complete request UTF-8 bytes |
| ---: | ---: | ---: | ---: | ---: |
| 0 | 256 | 71 | 185 | 72,540 |
| 16 | 512 | 71 | 441 | 72,540 |
| 64 | 1,280 | 71 | 1,209 | 72,541 |

Full-history relationships and the required counterexample remain intact.
Fresh-process restore preserves all 1,280 facts and the 71-fact selection; the
recovered complete request is 71,789 bytes. Public `evidence.read` retrieves an
offloaded canonical fact with exact execution/source binding and records the
read. The synthetic reader uses an isolated authorization anchor and a scoped
local snapshot, without granting access to the original campaign Store. Both
oversized complete-report prefetch and oversized required research evidence
fail explicitly. Protected saved sources are unchanged during this growth probe.
These byte counts and conservative token estimates are not provider usage or
measured model savings.

Gap B is closed at shared aggregate and individual comparison boundaries. The
reach-and-hold protocol requires its eight core components plus evaluator
`task_bound`; tracking retains sampling and its task-declared tension constraints
without reach holding/profile-link requirements. Accepted/status flags must agree
with complete component outcomes. Invalid execution or absent coverage cannot be
treated as ordinary physical failure. Evaluation/profile references must exist,
match the acceptance sources and authoritative producer evidence, and bind to the
simulation execution; reach profile links are checked under the reach protocol.

Copied-record negative cases return `unavailable` for:

- Symmetric missing `holding_speed`: `PROTOCOL_REQUIRED_COMPONENT_MISSING_OR_UNKNOWN`.
- Valid-failure/status flags with all acceptance conditions passing:
  `ACCEPTANCE_COMPONENT_OUTCOME_INCONSISTENT`.
- Removed required evaluation/profile references and cleared `acceptance.sources`
  on both sides: `PROTOCOL_REQUIRED_SOURCE_MISSING:evaluation`.

Known component results remain present. The intact saved comparison remains
**6/10 versus 7/10, improved**, with neither full suite completed. Tracking's
positive comparison works without reach-specific holding or profile links.

Gap C is closed with explicit optional-mapping handling. A legal voluntary STOP
with no requested allocation observes `plan_shortfall=None`; its assertion is
`not_assessed`, success remains unsupported for the incomplete joint suite, and
optimality remains unassessed. Known-value supported/unsupported behavior is
preserved. This auxiliary case does not reinterpret the saved normal STOP.

[Verification evidence](../evidence/research_mainline2_closeout_20261007/verification.json)
records **20 passing focused checks** and every test ID. Commands actually run
for final evidence:

```powershell
conda run -n softagent python examples/check_mainline2_closeout.py --verify --output evidence/research_mainline2_closeout_20261007
conda run -n softagent python examples/check_mainline2_closeout.py --output evidence/research_mainline2_closeout_20261007
```

The focused batches cover task/track semantics, shared comparison negatives and
saved positive, context/retrieval/request boundaries, null STOP, existing
fresh-process recovery and authoritative report-source regressions. The growth
probe is separate from those 20 unittest checks. Earlier intermediate focused
checks exposed fixture issues that were corrected before this final passing
record. The original 51 checks are not claimed as newly rerun.

No live-model validation, provider requests, scientific experiments, simulations,
controller solves or diagnostic workers occurred. Credentials and provider
settings were untouched. The historical scheduler-fixture implementation seal
remains a coverage limitation; it was not bypassed. Publication requires review
of the entire remote-to-HEAD range, preserving and reporting any unrelated
unpublished commits rather than exporting or rewriting them.
