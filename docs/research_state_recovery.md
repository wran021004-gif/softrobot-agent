# Offline research state and recovery, 2026-10-06

`research_working_state@1.0.0` extends `tools/context_assembly.py` and the existing
`Store` artifact contract. It is a derived working state, not a new scientific
identity catalog. Task adapters supply metric meanings, hypotheses and experiment
permissions; the shared layer retains source bindings, chronology, candidate
roles, claim revisions, experiment status, budget accounting and STOP.

`create_working_state` records the source packet and canonical facts.
`update_working_state` appends evidence/claim revisions, keeps previous support
and counterexamples retrievable, and invalidates artifacts when their declared
candidate dependencies change. Interpretations remain hypotheses; source validity
does not establish causal truth. Completed, failed and incomplete ledger entries
are immutable. Pending entries may receive their recorded outcome. Deliberate
replication requires a new experiment identity and a completed source; cache hits
are rejected as new repetitions. Recovery never automatically executes pending or
uncertain work. `assert_experiment_eligible` rejects already recorded work,
unavailable actions, exhausted budgets and stopped/sealed scopes. The actual host
grants and reservations remain the execution authority.

`persist_working_state` writes an immutable checkpoint through
`Store.put_context_checkpoint`. Its archive-only Store contains existing
`meta`/`artifacts` tables, no execution project, session or grant. It cannot modify
or convert an existing project Store. Historical Stores are passed explicitly for
read access. `restore_working_state` restores the same source allowlist and caller
scope; it neither discovers other Stores nor expands permissions.

`assemble_working_context` and `assemble_working_request` are the future shared
entry points for research decisions and reports. Both use the existing canonical
fact assembler. Report input projects the same ledger with a smaller purpose
view. Full old claim/experiment sources retain original JSON pointers; duplicated
candidate metrics are displayed once through bound execution facts. Original
chronology is retrievable while current role identities remain explicit.
Requests are measured before use and rejected if required information cannot fit.
These functions prepare inputs and do not send model requests.

The [saved M4 sequence](../evidence/research_preparation_20261006/recovery/sequence.json)
uses the actual round 0, 1 and 2 packets, enriched only with source-derived
scientific identities. Canonical fact count grows 192 → 224 → 256. Three saved
holding-response interpretations and their exact original evidence selectors
remain traceable as the weight-interaction question changes. Failed holding-speed
samples remain counterexamples. The actual final scheduler STOP and consumed
budget are recorded after its last decision; backend allocation remains zero.
The previous incumbent and latest attempted/completed execution remain distinct.

The checkpoint was read in a **new subprocess**, then the next decision and
report requests were constructed from the same 256 canonical facts. Their full
wire inputs were 135887 and 87301 UTF-8 bytes, with conservative estimated input
counts 144079 and 95493 including framing. Both fit their existing purpose budgets.
The [restored state observation](../evidence/research_preparation_20261006/recovery/restored.json)
records role identities, final budget, hypotheses, artifact invalidation and the
sealed-campaign rejection. The invalidation artifact is explicitly a contract
probe, not a new mathematical calculation.

Three focused unittest checks passed: scientific source/claim lineage and
candidate invalidation; pending/failed/incomplete/completed/deliberately repeated
ledger behavior; saved multi-round subprocess recovery and equal decision/report
facts. Initial execution hit the existing Windows private-temp ACL issue; tests
now use normal inherited workspace ACLs. Read-only SQLite handles are collected
before verified test-directory cleanup. Early over-budget preparations were
retained, and the affected input duplication was repaired before successful
preparation. No scientific material was silently dropped.

Run:

```powershell
& 'C:/Users/gugugaga/miniconda3/envs/softagent/python.exe' -m unittest tests.test_research_recovery -v
& 'C:/Users/gugugaga/miniconda3/envs/softagent/python.exe' examples/check_research_recovery.py
```

Historical M4/M5 Stores, scheduler state and authorization anchor hashes stayed
unchanged; see the [verification](../evidence/research_preparation_20261006/recovery/protected_hashes.json).
Zero provider calls, backend solves and research operations were charged. Live
input-cost and response-quality validation remains pending; saved model prose is
historical evidence, not a new live model validation. M4/M5 scope closures,
negative findings and protected allocations remain intact.
