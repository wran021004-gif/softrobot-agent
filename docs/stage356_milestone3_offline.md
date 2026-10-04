# Milestone 3 offline preparation

The original Stage 3.56 pair is frozen in commit `1ded856`. This subsequent work
is **Milestone 3 offline preparation**, not Milestone 3 completion or live
validation of the repairs. No additional provider request, controller solve or
MuJoCo execution was made.

`tools.platform_search` provides `prepare_offline_batch`, `run_offline_batch`
and `offline_batch_result`. Preparation consumes one host-accepted immutable
`platform.search_batch_plan@1.0.0` from `design.submit_search_plan@1.0.0`. It binds
the saved source configuration, fixed identity, acceptance and model-selected
ranges to a batch. Generation uses `search.family_coordinate@1.0.0` and the
existing candidate builder/CandidateInput; only the two supported speed weights
vary. Robot, material, task, controller.gvs_nmpc@7.0.0 and other numerical settings
remain fixed. Builder authorization and weight legality still apply.

The offline callback receives `(stage, candidate, retained_receipts)` for
simulation, evaluation and profile, and supplies synthetic outputs. Its profile
output contains `factual_result` in the existing complete-execution shape, bound
to the requested candidate/configuration. Apply uses the existing builder. Each
output is labelled `offline_injected` and each receipt is sealed in the existing
SQLite ledger. The grant permits zero providers, backends and workers. There is
no default live execution adapter.

Algorithm state, current proposal, configurations and stage receipts persist in
session state. Sealed stages can continue without repetition. Unsealed work keeps
its reservation and becomes unknown; automatic replay is prohibited. Failed
stage receipts remain pending. `WorkingState.search_batch` exposes pending work
and the compact result reference. Existing `diagnostic_facts.handover` transfers
that result into the diagnostic/design fact catalog; the fixture demonstrates
this without a model call.

## Physical feedback

Coordinate search requires a scalar. `physical_feedback` retains the full
`compare_results` comparison and `campaign_metrics` vector, including official
reach, holding position/speed and joint acceptance flags. Guidance minimizes:

`int(not joint_acceptance) + mean(v / (v + frozen_limit))`

Here `v` comprises terminal error, maximum holding error and maximum holding
speed, each with its frozen limit. Joint acceptance occupies [0,1), nonacceptance
[1,2); within a bucket guidance is monotone in each metric. Invalid/incomplete
execution, unavailable holding coverage, force violation or solver errors receive
no score. Changed holding definitions are rejected. Timing is reported separately;
controller-internal weighted costs never enter the score.

A physical trade-off can lower guidance and influence the next proposal. It
remains a **trade-off** under final frozen comparison, never overall improvement
or automatic promotion. A future model must interpret the full vector and
alternatives, not just the scalar.

## Accounting and reservations

`max_candidates` is the coordinate method's **proposal cap**, including the start
and duplicates. Separate counters report proposals, distinct configurations,
reused evaluations, new backend attempts, offline execution attempts and completed
new evaluations. Reusing the start or a duplicate is not a newly tested changed
configuration. Failed/unknown attempts retain charges before a complete result.
Offline backend counts are zero; synthetic receipts are not physical evidence.

The plan floor remains 900 seconds for simulation, 30 for evaluation and 60 for
profile: 990 seconds per planned proposal, plus four tool slots including apply.
Preparation protects an explicit interpretation/delivery reserve (600 seconds by
default). These are reservations, not runtime predictions. Three proposals need
2,970 seconds before this reserve (3,570 with it); the original dual plan's six
need 5,940 before it (6,540 with it). A 1,800-second grant is rejected. Offline
fixtures use their own zero-live grants; original Milestone 2 ledgers stay intact.

## Evidence and remaining work

Focused checks cover guidance/trade-offs, immutable plan/configuration binding,
start/duplicate accounting, continuation, unknown reservation retention,
fact-catalog handover and V6 correction paths. Synthetic examples include Pareto
improvement, worsening, trade-off, joint acceptance and interrupted work. Earlier
filesystem/SQLite fixture failures and affected reruns are retained separately.

Post-live repairs correct V6 alias error paths to submitted fields, describe exact
alias/condition identifiers, and identify usable performed-result aliases in
validator errors. Ceilings, recovery limits, transport settings and archived
model products remain unchanged. Repairs are offline validated only.

Remaining: a separately authorized/funded live adapter connecting existing
simulation/evaluation/profile completion, sealed physical provenance checks and
a model's subsequent batch interpretation. Model-authored stopping conditions
need explicit operational policy where possible; scientific conclusions require
interpretation. No physical batch or Milestone 3 live execution is authorized.
Milestone 2 still needs newly authorized single-context validation of accepted
future-plan and final-decision delivery after the offline repairs.
