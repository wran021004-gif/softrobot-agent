# Task A: unified cross-task research integration

## A-I — C4-R and BF4

Integration workspace: `integration/research-next`, starting at `d7b0f91f9`.
The initial worktree/remote/common-ancestor check found both source branches
based on that same integration head. Other worktrees and the C4 cold-start
Store, authorization, configuration and frozen checkout are untouched.

Selected production changes from C4-R (`c41350922`): `agent`, `contracts`,
`core`, `evidence_policy`, `research_context`, `task_constraints`. This retains
soft scientific claim annotation for experiments while keeping identity,
authorization, applicability, budget and formal conclusion gates hard. Large
controller schemas stay behind the existing L1 evidence query; no second
context or routing system was added. Original refusal and callback cost
feedback remain visible.

Selected BF4 (`404184e4c`) changes: the task adapter/acceptance composition,
native and physical sequence searches, task constraint vectors, feedback,
independent replay registration, and existing family controller/backend
declarations. The frozen Tracking task and its control defaults are retained.
No old experimental Store, success control, Provider trace or C4 configuration
was imported. Existing budget accounting, optimizers, Registry and Store remain
the owners. `extensions/reference/contracts.py` needed no change.

`task_constraints.py` was merged by meaning: C4-R's combined method template,
prerequisite, authorization and cost queries coexist with BF4's timed Tracking
coverage. The obsolete unconditional Tracking authorization veto was removed;
the existing scoped Study grant and request-specific applicability still apply.
Independent replay now publishes its actual Store execution ID and immutable
profile artifact, and that profile is reachable through ordinary evidence reads.

Reach/Hold retains terminal position, holding position and holding speed.
Timed Tracking uses the frozen `r(t)` and its inclusive scored time grid,
without a holding-speed objective. Untimed sequence search and Tracking T1/T2
remain explicitly not applicable. Mathematical diagnostics and Native search
do not establish physical acceptance or global optimality.

### Public entry for a fresh C Tracking Study

Use `python -m tools.research prepare --spec configs/research/study_tracking_public.json`,
then the existing commit/bind/run workflow. The template has zero Provider and
science budgets, empty historical evidence, and no experimental witness. Before
preparing a scientific Study, give the leaf a fresh ID, explicit authorization,
finite Provider/public-operation/math/physical budgets, replay limit and Native
callback/iteration/knot limits. Retain the frozen task/control references and
zero holding/terminal speed weights. Provider/runtime settings use the existing
`runtime.json` and sole `tools.research.config.resolve` resolver.

The same Agent tools are `evidence_read`, `research_plan` and
`research_analysis`. The route is generate → initialize_control → retrieve
`mathematical_capabilities /methods/mujoco_direct_control_v1` → submit that
`research_analysis` template with a bound source and explicit v2 time window
and knots → physical_replay using `control_schedule_reference` → evidence_read
the registered evaluation → SELECT when eligible. `control_search` instead
uses independently charged full replay callbacks; it has its own frozen
capability and shared physical budget. A method label alone executes nothing.

### A-I validation

Focused source regressions cover Reach/Hold, timed Tracking, C4 hard/soft
admission, Native limits, refusal feedback, acceptance protocols and replay
source binding. `test_cross_task_integration` exercises public generation,
method discovery, control initialization, replay registration, read-before-
SELECT and successful formal SELECT with explicitly fabricated motion, using
the real Registry, Store and evaluator. This is an interface fixture only.

`python -m tests.research.integration_tracking_smoke` is the single-use real
engineering route check, after commit. It requests one Native baseline and one
independent 0.6 s replay (1,200 integration steps total), zero Provider, NMPC or
RL requests, and keeps raw artifacts in ignored `runs/integration-tracking-smoke`.
The summary records actual task acceptance and eligibility; a failed baseline
is not selected. No BF4 S1 search is rerun. This does not claim autonomous
Provider behavior or benchmark feasibility.

## A-II / A-III

Multi-condition joint selection and the Task Intake thin adaptation follow as
separate commits. Benchmark execution always consumes the frozen TaskDefinition
directly; Task Intake is not a benchmark prerequisite.
