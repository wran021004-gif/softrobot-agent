# Bounded pre-study revision, version 1.1.0

The current [study freeze](../configs/research/reach_hold_v1_1.json) supersedes the
allocation policy in [version 1.0](research_first_study.md). The original freeze,
observed smoke result and milestone evidence remain unchanged. No research group,
model request or backend execution was launched for this revision.

The exact retained incumbent, eight-variable catalog and granted domains, five
initial-state cases, mapping, seeds 17/18, physics, task and acceptance protocol
remain unchanged. Terminal and holding position limits are 0.01 m; holding speed
is 0.02 m/s over the final inclusive 0.05 s. Stable v7 controller stopping rules
and all numerical settings remain source-bound. This is still an offline study;
historical real-time failures retain their original labels.

The per-group ceiling remains 28 backend attempts, 100 workflow calls, eight model
requests, zero workers and 30000 charged seconds. The allocation is now explicit:

| Phase | Maximum backend attempts | Rule |
| --- | ---: | --- |
| Search and control adaptation | 8 | Four structures, two nominal seed-17 control pairs each |
| Unchanged incumbent validation | 10 | Five frozen cases, two fresh repetitions each, empty candidate changes |
| One selected candidate validation | 10 | Same cases, seeds, mapping and repetitions; selected candidate frozen first |

The final two rows are matched validation. Each case/repetition runs incumbent
then candidate. No search execution counts as a validation repetition. Twenty
full validation reservations remain protected during search: each reserves one
backend attempt, three receipt operations and 990 seconds. A search attempt is
started only when those reserves plus its own execution fit. Thus the full
fixed workflow needs at most 84 workflow calls and 27720 reserved seconds. The
validation schedule is saved before its first execution; pairs must fit before
starting. Failed, invalid, incomplete and unrecorded slots remain visible in the
ten-slot denominator; no retry seeks a passing result.

The old catalog-order proposal list exhausted four structure slots before
section/material changes. Version 1.1 uses an explicit incumbent-anchored family
allocation, frozen before any new outcome:

| Structure slot | Physical proposal | Second control pair |
| --- | --- | --- |
| 0 | Unchanged incumbent | Terminal tip-speed weight 0.06875 |
| 1 | Near length 0.165 m | Holding tip-speed weight 0.06875 |
| 2 | Far section scale 0.975 | Terminal tip-speed weight 0.06875 |
| 3 | Near material scenario `stiff` | Holding tip-speed weight 0.06875 |

Every first control pair uses incumbent weights 0.05/0.05; the other weight in
each second pair stays 0.05. Numeric edits use the retained normalized 0.25 step;
the material proposal is a legal categorical choice. Near length/material sample
the proximal segment and far section samples the distal segment. This gives one
representative edit per physical family and both control objectives within the
existing budget. It is a finite family allocation, with embedded v7 numerical
adaptation, rather than a claim of exhaustive coordinate optimization.

Planned coverage is five variables: near length, far section, near material and
both speed weights. Far length, near section and far material remain unvisited by
this baseline policy. They remain available in the same shared eight-variable
pool to future planning groups. The saved plan lists intended coverage; delivery
records actual changed values, attempt counts and complete results per variable,
and actual structure/control slots. This revision has zero scientific search
coverage because no study execution occurred. Offline synthetic scheduling
fixtures establish behavior only. Neither availability nor planned coverage
means all eight variables were optimized. Exhaustive coverage and automatic
budget increases are unnecessary.

A new candidate is eligible only if it changes the effective design/control
configuration and has a fresh charged, complete, correctly bound authoritative
nominal joint pass. Unchanged, cached, unavailable, incomplete and valid physical
failure results are ineligible. Choose exactly one nondominated eligible candidate
in frozen proposal order; equivalence or tradeoffs keep the earlier candidate.
Freeze its exact configuration and changes before validation. Nominal selection
does not establish superiority.

If there is no eligible new candidate, retain the incumbent and perform only its
ten validation slots. Report `no_eligible_new_candidate`; the ten candidate slots
are unscheduled and unused. Do not force a failed candidate, expand the search,
transfer validation slots to search, or fill unused budget. A complete incumbent
validation can support its observed robustness, never an improvement claim.

Only complete, fresh, correctly bound matched results permit final comparison:
joint acceptance count first, then componentwise physical dominance. Promote the
candidate only for an improvement under that rule. Retain the incumbent on
equivalence, tradeoff, worse or unavailable comparison, with all component
outcomes and costs visible. Incomplete validation suppresses superiority claims.
Stops report policy legality, factual support and unassessed optimality separately.
No additional candidates are substituted after validation begins.

The earlier real development smoke, execution
`ef0a8703dff7494f8053e34067b33f7a`, used near scale 0.96, `near_z_plus`, seed 17 and
incumbent weights. Its terminal error 0.0028974459148354828 m passed but holding
speed 0.06773111912652348 m/s failed. It cost one backend / three tools /
336.359 seconds and zero model requests. That case is exposed development data,
not unseen data or a formal validation repetition. The sealed [smoke delivery](../evidence/research_preparation_20261006/smoke/delivery.json)
predates the planner/catalog bridge. The later [bridge checks](../evidence/research_preparation_20261006/shared_parameter_checks.json)
were offline and produced no robot outcome. The nominal source is also observed;
future repetitions are prospective fresh executions, not a claim that every case
is unseen.

Implementation is `fixed_coordinate_reach_hold@1.1.0` and
`shared.parameter_search@1.1.0`. Source projection is now shared between archived
planning and the fixed runner. Plan validation, batch preparation and the runner
share catalog-bound finite ask/tell preparation, followed by actual candidate
construction and the same simulation/evaluation/profile receipt executor. Native
planner role/alias-ledger and whole batch orchestration remain separately offline
checked; this integration proposal does not claim their live execution.

The precise next execution proposed for independent approval is one fresh
development smoke through that final shared preparation path: near section
scale 0.96, other physical parameters and weights unchanged, `near_z_plus` total
bend +0.01 rad and rate +0.02 rad/s, seed 17, duration 0.35 s. It uses a new Store,
unique session/request identities and `cache=new`; no replay or automatic retry.
Its independent cap is one backend, three tools, zero model/worker calls and
990 seconds (900 simulation, 30 evaluation, 60 profile). It consumes no formal
study allocation and does not transfer the unused earlier smoke slot.

Prepared command, **not executed; requires the separate approval requested by
the user**:

```powershell
& 'C:/Users/gugugaga/miniconda3/envs/softagent/python.exe' examples/fixed_research_baseline.py --mode smoke --spec configs/research/reach_hold_v1_1.json --output runs/research_shared_path_v11_approval_20261006 --export evidence/research_shared_path_v11_approval_20261006
```

Safe plan-only command is `--mode plan --spec configs/research/reach_hold_v1_1.json`.
The full `--mode study` workflow remains prepared and unlaunched. Version 1.0
reproduction uses its historical commit and original freeze; the revised runner
rejects that superseded allocation policy rather than silently changing it.
See [revision evidence](../evidence/research_pre_study_revision_20261006/revision.json).
