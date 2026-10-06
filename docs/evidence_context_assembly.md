# Shared evidence context assembly, 2026-10-06

`evidence_context_assembly@1.0.0` now assembles the actual native M4 research
decision path (`EvidenceDrivenAdapter.encode` / `payload_for`), the current M4
fact-bound reporting builder (`build_reporting_request4`), and the M5 research
interpretation builder (`build_interpretation_request`). Both purposes use one
`assemble_context` / `assemble_request` interface. Provider endpoint, model,
thinking/reasoning, response/context limits, credential loader and verified TLS
transport remain unchanged. No new model, dual-model study or scientific grant
was introduced.

The immutable archive keeps complete original and assembled inputs, canonical
ledger bindings, source manifests and failed preparation audits. Existing raw
responses, reviews, receipts, configurations, trajectories and historical seals
are unchanged. Scientific facts use the existing `study_history`, unmasked
`reporting_scientific_scope`, `bound_reporting.ledger` and renderer. Research F
aliases remain the existing context-local catalog; they are not replaced by a
new memory or identity system.

The working view removes repeated receipts/hash lists/traces and normalizes
shared execution metadata. Research history retains source-candidate identities;
its exact metrics are displayed once through bound execution/metric references.
Repeated baseline/source comparison metrics are not concatenated again as F
aliases: direct outcome metrics, signed comparison deltas, classifications,
current feedback and aliases needed by rejected drafts/corrections remain.
Comparison bindings explicitly identify both executions. The original full alias
mapping remains in the host and archive. Relevant older failures/counterexamples
are retained; selection starts with the caller's authorized case/comparison
records, never a recency cutoff or a search across unrelated stores.

Incumbent, latest attempted execution, latest completed evaluation and source
baseline are distinct roles. Latest is derived from reservation/completion events,
not list order. Local M5 operation chronology is labeled diagnostic work, never
backend validation. Different structures remain distinct at equal weights.
Explicit source/new repetitions retain scientific identity, aggregate metric
differences and their comparison limitations. Frozen background questions are
labeled historical; a recorded repeat supersedes the absence of repeat evidence
without establishing broad variability, full-trajectory equality or equal timing.
Observed facts, supported local hypotheses, rejected claims and unanswered
questions have separate fields. No scientific threshold, plan, controller
behavior, selection, STOP or protected allocation changes.

`EvidenceArchive.retrieve` reuses the existing `evidence.read` original JSON-pointer
paging implementation. It returns source/binding/units, truncation, next offset
and overview child pointers. `from_manifest` can reopen the durable allowlist with
the same caller scope and explicitly supplied authorized stores. Other roles,
unknown references, changed bytes and missing pointers fail. This creates no
hidden model tool or extra permission: phases with no advertised read tool return
an explicit preparation issue if their required view cannot fit. Unique content
is durably stored and source references verified before offloading. Exact numeric
rendering still rejects a wrong execution/metric, wrong comparison direction or
wrong structure. Citation validity still does not validate surrounding prose.

The complete outgoing wire input, including retained messages and final function
schemas, has a per-purpose conservative estimated input budget of 160000 for
research and 96000 for final reporting. The configured 1000000-token context,
65536-token response allowance and 8192-token interaction reserve are kept
separate. No appropriate tokenizer is installed; measurement is explicitly one
estimated token per serialized UTF-8 byte plus the configured framing allowance.
Characters, bytes and observed provider tokens are separate fields. Overflow or
duplicate history/receipt/full-manifest contamination fails preparation and keeps
its audit; required identities and counterexamples are not silently truncated.

| Complete input over the same enriched saved corpus | Before UTF-8 bytes | After UTF-8 bytes | After estimated input tokens |
| --- | ---: | ---: | ---: |
| M4 research decision | 258006 | 124176 | 132368 |
| M4 final report | 88499 | 74737 | 82929 |
| M5 research interpretation | 32090 | 28057 | 36249 |

The old actually sent M5 input was 25937 bytes. Its new view is larger because it
adds scientific/structure identity, authoritative role/chronology, source and
acceptance bindings; metadata normalization reduces the equally enriched input.
These are offline size observations, not measured new provider tokens or monetary
savings. The archived old successful requests report 40542 M4 and 8260 M5 prompt
tokens; those actual counts do not measure the new assembler.

Ten focused checks passed across the initial and affected repair passes: five
existing fact-binding checks and five saved-corpus assembly checks. They cover
geometry attribution, explicit repeat and limits, reorder-invariant ownership and
latest roles, retained negative evidence, exact signed values/units, original
source retrieval and durable reopening, cross-execution rejection, actual native
and reporting builders, and full-schema overflow. The first new checks were
blocked by sandbox-created temporary directory ACLs. After those checks ran with
filesystem access, one real-path check found over-budget duplicate comparisons;
that preparation failed before sending and its audit remains. A later check found
the credential filter confusing a scientific authorization description with HTTP
Authorization; it was corrected while actual credential fields remain rejected.
Only affected checks were rerun. No full suite or accepted numerical baseline ran.

Live observation is **unperformed**. M4's reviewed report had already succeeded
and its provider ceiling was exhausted; M5's successful interpretation and negative
development scope were sealed. There is no already-planned, unexecuted eligible
call. Old saved responses were rendered offline to check compatibility; they are
not claimed as new model use or evidence of general reasoning improvement.
Attribution/replication recurrence and new actual provider token/cost changes are
unmeasured. This amendment charged zero provider/workflow/scientific operations
under the existing offline engineering convention; it did not reset or create a
grant. M4 remains qualified closed; M5 remains open with its timing/improvement
barriers and six protected backend slots preserved. No scientific work remains
eligible to resume at this checkpoint.

See [saved input observations](../evidence/context_assembly_20261006/observation.json),
[focused checks and repairs](../evidence/context_assembly_20261006/offline_checks.json),
[unchanged historical sources](../evidence/context_assembly_20261006/protected_hash_verification.json)
and the scoped source manifests linked in each assembly audit. Publication status
is recorded separately after the implementation and evidence checkpoints.

Implementation commit: `e9e3c23`; evidence commit: `c4d02ec`. The normal push was
rejected by automatic approval before process launch: the reviewer requires
trusted direct-chat authorization for this code/evidence payload and the existing
GitHub destination. No alternative export was attempted. The verified remote
remains `1c0f886bc0f267778e4af73c324f6fc3d8759148`. See the
[publication rejection](../evidence/context_assembly_publication_20261006/publication.json).
