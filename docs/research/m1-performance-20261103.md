# M1 sealed closeout: request-local performance repair

Scope: implementation only, on `codex/m1-knowledge-physics-reasoning`, based on
`adfc94cc3aa0e3ec65ea3bedf8f4591691f7a842`. The original Study
`m1-low-tendon-speed004-20261102-campaign3` was accessed read-only. No M1 SELECT,
Provider request, scientific Worker, independent Replay, budget extension,
historical identity migration, or original Store write was performed.

The original actual execution implementation remains
`2542a839c78cf68db20fc6cb23c0c2750562962c`. The later `adfc94c` commit records its
report; it is not substituted for the historical execution identity.

## Original result and authority

The original Store reports `stopped`, successful model selection, three complete
independently accepted frozen conditions, and selected joint artifact
`7fee7f0cde4669da72b2d0a4e0fe61a8507f45c0cf28560d995e03558c42f18b`.
Provider use is 182/191; physical Replay use is 3/18. Pending work, unsealed
calls, workers, and unconsumed SDK response are absent. Original numerical
costs and accepted certificates are unchanged.

Recomputing the read-only three-condition qualification produces the exact
original selected artifact hash. Formal admission in a hypothetical fresh
selection state remains legal, while the original sealed Study continues to
reject selection. The fresh state is an explicitly labelled in-memory fixture,
not a new Study or a second SELECT.

## Sources of repeated work

The original selection path is short-reference binding -> scientific decision
admission -> selection eligibility -> joint result registration. Each calls
`joint_assessment`. Native tool handling and direct Plan dispatch now share the
existing request-local `Store.read_snapshot()` cache. Qualification keys include
Study identity, the complete ordered reference list without deduplication,
the require-read mode, and the complete scientific state identity.

The observer connection checks SQLite `data_version`; a committed Store change
invalidates request facts. The existing state, receipt, evidence-read, budget,
and sealed-selection guards still run. Reservations and state changes therefore
cannot reuse an earlier qualification as permission for a later commit.
Audit-only commits conservatively invalidate it too. The four-call measurement
is an unchanged-snapshot comparison, not a claim that all phases of a writing
native SELECT now run one calculation. No certificate, receipt, or scientific
validation is removed.

Other confirmed metadata-only full reads included Native search summaries,
scientific citation summaries, mathematical/physical relation discovery,
historical action receipt summaries, and Native baseline-failure discovery.
They now select their actual fields from the hash-verified original artifact.
Action traces reuse one request-local result. Session reads also use the
version-invalidated request cache. Read connections used for artifacts and
sessions close deterministically.

Read-credit verification no longer materializes a full artifact for a summary
or a request that was never confirmed delivered. Actual full, field and range
reads still require exact matching contents. A generic JSON-pointer projection
preserves arrays, escaped keys, Unicode, JSON null/absence and Boolean types,
and validates the original artifact hash before projection.
Overlapping dot-path field requests reuse previously verified projected fields,
including absent fields, inside the same request. This is one generic extension
of the existing cache, with no raw JSON copy, persistent cache, or extra Store.

## Observed performance

All measurements use the same sealed original Store and prohibit transactions.
Instrumentation time is included. These are local measurements, not claims of
Provider token savings. Timings are machine/load dependent.

| Entry | Before | After | Interpretation |
|---|---:|---:|---|
| Four identical joint qualifications in one request | 116.0 s | 36.8 s | One authoritative calculation reused three times |
| Complete artifact decodes in that request | 305 | 22 | Existing artifact hashes and all qualification checks retained |
| JSON decoder input in that request | 336.7 MB | 2.0 MB | Most repeated input was session/configuration metadata |
| Python peak for that request | 52.9 MB | 52.7 MB | No meaningful memory improvement on this entry |
| `mathematical_context` | 3.96 s | 3.92 s | Existing 124-artifact projection already avoided full Native decoding; no meaningful additional gain |
| Read-credit coverage | 19.2 s | 16.9 s | Identical output hash; projection and fewer repeated session decodes |
| Default three Reporter summaries | 2.41 s | 2.59 s | Identical output hash; no meaningful latency gain |

All 127 historical action-trace rows retain the exact same serialized hash
`af5376da7195d8e692fc8d1afe64b5e7bc46ba9a3e451cbe5a4f1498597c305c`.
Its uncached first construction became slower in one comparison (11.5 to
23.3 s); request-local reuse and memory avoidance are the reasons for keeping
the projection, not a claimed first-call latency improvement.

Complete compact L0 construction produces 300,082 bytes. An intermediate
instrumented run measured 176.7 s and 312.4 MB Python peak. The final minimal
overlapping-field cache reduced projection reads from 2,109 to 1,717 and
construction without memory tracing from 116.4 to 101.8 s, with the exact
same L0 output hash. The latter run did not measure Python peak. No further
large-scale refactoring was pursued.

The single joint qualification did not become faster in these measurements;
the improvement is eliminating repeats. Early exploratory memory readings used
Mock call-history retention and are excluded from performance claims. A full
original L0 construction was stopped after excessive memory growth, so no
complete before/after L0 speedup or peak-memory ratio is claimed.

The production SDK formatter was separately exercised without sending, using
the same sealed state, tools and system prompt. The historical SDK history was
reconstructed from recorded wire messages and extended with the exact final
response/feedback. Preserving it generated 503,112 bytes (74 SDK messages,
1.32 s, 19.9 MB Python peak); compact handoff generated 254,802 bytes (one
initial message plus exact pending feedback in the current packet, 0.90 s,
9.1 MB Python peak). This is an offline construction comparison, not a new
Provider measurement. Historical last SELECT usage remains the actual recorded
65,171 prompt tokens and is not rewritten.

## Safe continuation and regression evidence

The latest settled tool round crosses a request-feedback handoff intact once.
Old historical feedback can remain compact and queryable. A verified
request-feedback boundary may rotate context after a success gate; the
scientific guard still requires immediate closeout. Completed-invocation
handoffs after a success gate remain blocked. Original SDK snapshots, durable
feedback, evidence-read records and costs are preserved.

Focused tests cover external-commit invalidation, scientific state/read-mode
changes, defensive copies, duplicate input preservation, projected JSON types,
artifact corruption, exact latest feedback beyond the compact allowance,
actual SDK Mock request-boundary rotation, and formal read credit. Existing
saved-reference binding tests pass. Several older broad SDK fixtures fail the
subsequently introduced mathematics-authorization gate before reaching the
tested code; current tests supply explicit synthetic fixture authorization,
without weakening production authorization. Older general-task fixtures also
contain obsolete control-effort/condition inputs; they were not changed to
expand this repair's scope.

Read-only source comparison checked all 118 Native results: scoped scientific
summaries and Native key facts from projected fields equal those from the
complete original artifact. Negative admission checks cover missing/duplicate
conditions, extra historical references, missing formal reads, wrong task,
structure/discretization mismatches, source/Replay errors, foreign ownership,
and the original sealed selection. No synthetic fixture is physical evidence.

Detailed timings, artifact counts, JSON input sizes, output hashes, SDK
construction measurements and integrity checks are delivered as local JSON
reports. The original Store and historical experiment evidence remain the
scientific authority; measurement reports are not a parallel evidence Store.
