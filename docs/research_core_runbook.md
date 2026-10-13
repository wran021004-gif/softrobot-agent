# Unified reach-and-hold research entry

For the fresh mechanics/control integration, use the explicitly scoped commands
in [mechanics_control_runbook.md](mechanics_control_runbook.md). The study below
is historical and sealed; its default specification must not be executed again.

Actual base: `1311b1228b1f01464b1ff3683482d923cb73ef03` from
`origin/feat/nmpc-settling-followup`, fetched once with no newer commits.
Worktree: `D:\softrobot-agent\.worktrees\unified-research-core`.
Delivery: `feat/unified-research-core`. Reuse the existing interpreter and lock;
do not recreate the environment. Historical stopped studies remain sealed.

```powershell
Set-Location 'D:\softrobot-agent\.worktrees\unified-research-core'
$studyPython = 'D:\softrobot-agent\.mainline5-env\Scripts\python.exe'
& $studyPython -m tools.research_core prepare
& $studyPython -m unittest tests.test_research_core
# Commit implementation and specification before numerical work.
& $studyPython -m tools.research_core bind
# Execute a typed plan JSON, with a new request ID only for an intentional new experiment.
# The original reference plans are indexed in the delivery scientific_summary.json.
$planPath = 'runs/unified-research-20261011/reference_1.json'
& $studyPython -m tools.research_core execute --plan $planPath --request-id engineering-reference-1
& $studyPython -m tools.research_core diagnose
& $studyPython -m tools.research_core live
& $studyPython -m tools.research_core status
& $studyPython -m tools.research_core export
# After accepted STOP, write the completion report and canonical archive without new experiments.
& $studyPython -m tools.research_core_delivery
```

`--spec` chooses a study specification. Its study ID, start clock, task/profile,
budget and independent ledger are persisted at preparation. Study-specific
choices are data, not another historical mode. The production controller remains
the latest recovery-enabled recipe with reference speed weights .10/.10.
Physics, physical zero initialization, 0.2 N numerical guesses, target, timing,
seed 17, solver stopping and inclusive sampled acceptance are frozen.

Native `research_plan` supports `propose`, `execute`, `search`, `diagnose`,
`confirm`, `stop`. `propose` has `parameters` with `d` and the two weights;
`execute` cites the resulting candidate EvidenceRef. `search` provides variable
subset, exact bounds, fixed parameters, maximum evaluations, step and ranking.
All unused coordinates are fixed. Lengths obey near=.16+.0055*d and
far=.11-.0055*d. No parameter-only candidate fabricates an offline trajectory.
The existing mathematical coordinate method supplies internal proposals using
the same candidate constructor and complete-execution evaluator as direct plans.
Reported explored values distinguish declared variables from tested coordinates.
Search keeps the requested initial coordinates separately from the structural
domain's feasible nominal seed, including nonzero fixed d and subdomains that
exclude zero. Every internal evaluation is admitted and executed on the same
ledger, including baseline evaluations, duplicates needing fresh executions,
failures and partial batches.

Every plan includes hypothesis, supporting evidence, expected/weakening
observations, fixed conditions, stopping condition and interpretation. Program
facts and original model interpretations are separate immutable artifacts.
`experience_retrieve` searches/reads the existing case/procedure drafts through
a small index. Metadata filters are exact; missing metadata and draft status are
returned. `experience_disposition` records adoption/rejection by actual retrieval
artifact ID. Supplied historical context is explicitly not autonomous retrieval.
`evidence_read` reads immutable evidence using an optional JSON pointer.

Candidate identity covers all resolved fixed/search parameters, generated
robot/task/physical initialization and versioned evaluation profile. It excludes
execution owner and provenance. Each intentional repetition gets a new execution
owner and backend execution ID. Confirmation cites a passing selected execution,
checks its entire scientific configuration and profile, and reserves a fresh
launch. Both post-selection results and failures remain visible. Two successful
confirmations permit only limited repeat-supported acceptance. Parameter
improvement reporting also requires a current-version comparable reference and
better fixed metric ranking; raw weighted NMPC objective is not the ranking.

Before accepting search/execution, capacity covers every internal launch and its
complete 1900 s allowance (1800 simulation +30 evaluation +60 profile +10
construction), while protecting two launches and 3800 s for confirmations.
Batches shrink to fit. Every internal execution rechecks the shared Store and
numerical ledger; exhaustion returns retained partial results. Failed starts and
timeouts count. NMPC updates/recovery roots belong to the enclosing simulation,
not standalone local solves or a second elapsed charge. Total numerical ceiling
is 10800 s including relevant checks; launch ceiling8; provider ceiling32;
workflow ceiling128; local solve ceiling8/1200 s. Final four requests and final
30 min of the 12 h activity are protected. Ceilings are not quotas.

Complete update records are in `controller_observations.json`; targeted detailed
traces are in `control_snapshots.json` for updates8/29/30. Records include warm
source, initialized vector after bound clipping, variable bounds/order/scaling,
absolute schedule, measured/previous input, raw/selected/recovery/delivered plans,
solver options, identities and diagnostics, actual action and selection reason.
No dual guess is saved because the call does not use one. Serialization occurs
outside the timed numerical solver call; capture timing is retained. Standalone
diagnosis reconstructs the saved initialized optimization problem directly.
Optional `diagnostic` fields: execution EvidenceRef, update_id, repetitions1/2,
mode `production`/`fixed_iteration`, iteration_cap. Fixed iteration is not a change
to the production stopping policy. Each local process has a150 s ceiling and
charges before solving.

After a lost return, use `recover`; completed simulation receipts continue
evaluation/reporting without another launch. Unknown outcomes keep reservations
and block blind repeats. A repair requires commit then `migrate --reason ...`.
Changes to scientific dependency hashes increment the evaluation version,
retain all old results/costs and require constructing a new reference candidate.
Reporting-only changes retain the profile version. Dependencies are checked at
research/provider boundaries. Accepted STOP forbids any additional provider send;
export and Git delivery use saved evidence only.

Optional offline schedule initialization and legacy admission are separate from
the usable core. Draft retrieval does not promote a draft into a validated skill.
The canonical evidence archive includes original model requests/responses and
immutable simulations; compact indexes reference it without expanded duplicate
physics exports. Credentials and authorization headers are excluded.

The delivered study is sealed: do not replay its live command or change its
specification to reset costs. To run an independent study, copy the specification,
choose a fresh study ID and actual start timestamp, and use `--spec` consistently
for prepare/bind/execute/live/export. Replaying an existing operation ID returns
its recorded receipt; it is not an independent confirmation.

This study retained evaluation version 2's two references and local diagnosis,
then established version 3's new comparable reference after conservative
versioning of scientific source changes to failed-input recording, recovery-root
evidence and exact mathematical-search initialization. Source changes were
committed before that reference. No cross-version improvement is attributed.
The optional offline initialization and legacy skill admission remain deferred.


The linked `examples/design_control/campaign.json` declares additional Phase A and B allocations. The sealed
`rl-strands-20261013` remains historical with all original costs. Phase A reconstructs the same d=.5 physical
candidate and XML, PPO 128/64/four epochs, learning rate .0005, gamma .99 and holding-speed reward 2; one
1024-action/90-second live run must yield a complete independent saved-policy evaluation before Phase B.

Capability studies expose mathematical optimization, optional NMPC search, NMPC execution and direct/residual
RL as separately selected operations. Handoff retains objective/relaxation/trajectory provenance without a
controller launch. Search continues to evaluate through NMPC. Residual references use the existing NPZ tension
format only when candidate/task/channel order and the complete 35-interval SI schedule match; no resampling or clipping.

Common result views read measured metrics from original NMPC results or independent RL evaluations. Missing
or incomplete evaluation is unmeasured. Confirmation count comes from the frozen specification. The selection
freezes candidate/task/controller/configuration and exact RL checkpoint generation and file digest. RL confirmations
reload that generation with fresh simulation, without training; NMPC uses its existing execution path. Failures remain
recorded and selection cannot silently change. Passing development evaluation never counts as confirmation.

Before NMPC launch, matching existing configuration timing must fit the 1800-second execution cap and the
remaining route confirmation budget. Missing or mismatched timing makes the route unavailable within this
budget; it does not establish design infeasibility. No new calibration is authorized. RL has separate evaluation
reserves and cumulative training allocations; both routes share phase deadline and delivery reserve. Four NMPC
launches include search and confirmations. Training, resume, repeated status and cached receipts never reset costs.

Prepare and commit scoped implementation/specifications, bind the study, then run `research_core live --spec
examples/design_control/phase_A.json`. Its clock starts once at live entry. Use the same prepare/bind/live sequence
for phase_B.json after Phase A is complete. Runtime stores and checkpoints stay in `runs/`; compact nonsecret
requests, receipts, evidence reads, original decisions and final accounting are archived for delivery.


The campaign order above is an execution instruction, not a public-runtime A/B gate. Removing that gate grants no formal research authorization.
`examples/research_core/rl_evaluation_followup.json` authorizes only status, one pinned sealed-policy evaluation, evidence reads and STOP.
Preparation copies exact source artifacts through read-only Store access; terminal status never reconciles the sealed source.
The new study owns its output, receipts and one episode charge; source training costs stay linked historical facts.
The actual evaluation subprocess timeout is at most 120 seconds and also bounded by the remaining execution deadline.
A valid numerical-failure report verifies reporting, while physical completion, original task pass and two post-selection formal confirmations remain separate requirements.
