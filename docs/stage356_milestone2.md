# Stage 3.56: evidence-driven diagnosis and future batch planning

This stage extends the existing diagnostic workflow, host, SQLite store, evidence
catalog and phase budgets. It adds no search-batch runner. Both organizations use
the Stage 3.54 single-context candidate `087adee8e8a24fe88e5c85fe89e638c8`,
baseline `cf997605885642759ee33920e2c9e2ef`, accepted source revision and sealed
feedback. Historical reach success and holding failure remain unchanged.

## Producer and consumer path

`stage356_milestone2.scientific_bundle` verifies the historical host acceptance
events, report/feedback lineage, configuration, official evaluation, profile,
derived facts and comparison. `import_common` imports exact artifact bytes and a
host verification record, without sessions, private memories or historical ledger
charges. Fresh assessments use the existing `diagnosis.submit@2.0.0` path.

`diagnosis.propose_check@1.0.0` binds the accepted assessment and read-only
`WorkingState` to `platform.diagnostic_handoff@1.0.0`. Scope includes the task,
acceptance definitions, baseline/subject/configuration/execution, model/controller,
evidence context, source report, previous assessment, historical feedback and
current grant/budget snapshot. `consume_handoff` checks those associations against
host records. A submitted provenance string is insufficient.

The proposal precedes the selected evidence query or existing saved-state check.
Its immutable result envelope binds proposal, previous assessment, tool receipt,
result, execution and coverage. `diagnosis.revise_assessment@1.0.0` expands a
compact delta through the existing report materializer and acceptance validator.
It requires new detail from the received result and a link to an assessment. An
immutable interpretation companion preserves declared outcomes, changes,
uncertainty and resolving evidence. The accepted revision produces another
validated handoff with result/receipt lineage.

`design.submit_search_plan@1.0.0` consumes the revised report and performed check.
The host validates exact two-weight paths, builder domains, reachable coordinate
steps, starting configuration, installed `search.family_coordinate@1.0.0`, fixed
controller `controller.gvs_nmpc@7.0.0`, physical criteria, candidate/work counts,
cost floor and required fresh evaluation/profile/comparison. One immutable plan
governs a future batch. Its structural validity, model-authored scientific promise,
and execution authorization are separate fields. Execution remains unauthorized;
no candidate is promoted or baseline replaced by plan submission.

V6 of the existing scoped adapter advertises compact proposal/revision/plan
schemas while preserving exact aliases, targeted corrections, transport settings,
65,536 output tokens and existing 131,072 length recovery. Native adapter version
recognition is extended without changing old adapter behavior. Both organizations
share project limits of 24 provider attempts, 60 tools and 1,800 charged seconds;
dual roles share rather than duplicate this ledger. Check selection and execution
protect six attempts, six tools and 600 seconds for interpretation and delivery.

## Numerical eligibility and scientific limits

Eligibility is read from saved metadata. At a 0.01-second requested horizon only
update 34 qualifies for `local_comparison`; its effective horizon is one control
interval. The other horizons are not silently shortened. Exact design adoption is
also required. `prediction_braking` uses eligible saved projected states and the
existing model/integration validation. At most one numerical request is permitted,
with at most two local solves or two prediction evaluations and 180 seconds.
Evidence queries remain available independently of numerical eligibility.

Archived first-step predictions, local optimization results and sampled backend
motion have different meanings. Neither citation validation nor an accepted
revision proves causality. Wall-clock deadline misses do not imply skipped
simulated updates; solver termination does not imply numerical convergence.
Terminal reach and sampled holding are independent criteria. No continuous-time
guarantee or organizational superiority follows from this single pair.

## Historical engineering corrections

Stage 3.55 documentation now identifies the saved controller as version 7.0.0.
The engineer-authored example now treats terminal reach success as compatible
with holding-speed failure, supplies relationship relevance to each containing
assessment, and uses empty contradiction lists where appropriate. The original
fixture bytes and amendment hashes are retained under Stage 3.56 evidence; only
the engineering export and its Stage 3.55 checksum entry are amended. Historical
model responses, accepted products and measurements are preserved.

## Verification and live evidence

Run focused verification using:

```powershell
& 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe' examples/stage356_milestone2.py verify
```

Original failures and affected reruns are retained in
`evidence/stage356_milestone2_20261004/`. Offline fixtures prohibit real provider,
backend and optimizer execution. Windows sandbox temporary-directory permissions
required approved filesystem access; subsequent failures and repairs are retained,
including SQLite fixture cleanup. Only affected checks were rerun.

The implementation is committed before the authorized live pair. Each fresh
organization has a single guarded run directory; no failed run can be replaced or
have its counters reset. `common_input_freeze.json` records the matched source
bundle and implementation. Full public attempts, tool arguments, receipts,
accepted products, interpretation companions, accounting and checksums are
exported per organization. Monetary cost is unknown without billing information.

Milestone 3 must execute validated bounded batches through the existing candidate,
numerical, simulation, evaluation and profile machinery under a new grant,
followed by frozen physical comparison and evidence-dependent revision. The
coordinate method's candidate ask/tell capability alone supplies no holding
ranking or execution authority. This stage does not implement that batch runner.

## Delivery status

Milestone 2 is **incomplete**. Implementation commit `cddba26` passes 22 unique
focused checks (latest result per check, including preserved affected reruns).
The engineering fixture completes the actual check/revision/plan/final tool path,
and the dual fixture validates fresh payloads, shared ceilings and role isolation.
These are engineering results, not model-authored live diagnostic products.

Automatic approval review rejected the attempted single-context launch before
process creation because it did not recognize authorization in the attachment
for repository-derived evidence transmission to `https://api.deepseek.com` using
credentials. A direct confirmation is pending. Neither organization has started;
both live gates remain unmet. No transport request, model failure or campaign
attempt was consumed, and no run or grant has been replaced/reset. The complete
live pair remains to be performed after that transfer is approved.

Per organization, new provider attempts, tools, local solves, prediction
evaluations, charged time, workflow elapsed time, reported tokens and protocol
corrections are all zero. Backend simulations and workers/subagents are zero.
Reported token usage is absent because there is no provider response. Monetary
cost remains unknown; historical costs are retained separately in the verified
source bundle. Offline verification durations and engineering failures are in the
check logs and are not charged workflow time. No organizational comparison or
new scientific diagnostic conclusion is claimed. Nothing was pushed.
