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

A-I was committed and pushed as `fd4104ba9`. Its 57 focused tests passed.
The real check completed 600 Native steps plus 600 independent steps, with
`valid_failure` against the original task, truthful SELECT rejection and a
verified `research.physical_replay` Store receipt/profile binding. Cumulative
measured numerical cost was 3.0557587 s; Provider/NMPC/RL counts were zero.
Only a sanitized count/cost summary is published; private artifacts stay local.

## A-II: same-structure conditions

`study_multicondition_public.json` uses the same resolver/defaults and imports
only BF2's frozen zero/positive task definitions (negative is available for a
third condition). No BF2 experiment branch, historical result or witness is
merged. The leaf's `task_conditions=[{condition_id,task}, ...]` replaces its
single root `task`; there are two or three unique conditions and one shared
Study ledger. All condition TaskDefinitions, seeds and settling limits are
frozen during preparation; resume reads saved state, never mutable sources.

Generate once. For each condition, call `initialize_control` with the generated
structure candidate and `control_seed.condition_id`; use its returned
`candidate` and `source` for normal Native analysis/control_search and independent
physical_replay. Condition candidates share the exact robot structure and mesh;
only their frozen task/seed/settling binding differs. Initial states, external
forces, versioned task, applied control and real execution IDs remain independent.
Control initialization time, all internal Native attempts and independent
replays retain the existing cumulative costs.

`SELECT selected_execution=[result_ref, ...]` checks the ordinary eligibility
of every child, public reads, owned complete physical_replay receipts, control
binding, original acceptance, immutable profile sources, the exact condition
set, and identical robot/mesh. Results are ordered canonically before saving
one joint result in the existing Store and freezing the selected solution.
Missing/duplicate/failed/incomplete conditions, changed structures, wrong
controls or invented execution IDs cannot qualify. The success gate waits for
all conditions, preserving partial/out-of-order completion and legal recovery.
The exported design package includes the joint result and every condition ref.

The only new production module, `conditions.py`, owns condition binding and
aggregation. Existing `aggregate_acceptance` now recognizes real completed
`research.physical_replay` receipts as well as `simulation.run`; no synthetic
simulation receipt is manufactured. No optimizer, backend or Store was added.
The existing per-request analysis protocol remains the method's time scope;
BF2's frozen conditions share that grid. Joint selection currently requires
independent fixed-tension replays, matching the B2/BF2 protocol, and zero extra
confirmation repetitions; mixed protocol families and joint RL/NMPC selection
are not implemented.

A-II validation: the small two-condition fixture exercises different controls,
partial-Store reopening, reverse result order, original evaluators and formal
joint SELECT/export. Three-condition checks cover binding/reuse, missing and
failed conditions, wrong source, forged execution ID and mixed structure.
40 directly relevant tests passed. The additional family-space checks passed
except two existing assertions for a fixed old digest and an outdated compact
summary size. Direct comparison with the starting resolver confirmed the
legacy Reach/Hold effective configuration is exactly unchanged; those historical
assertions were not rewritten. Use the existing `.f3-prestudy-env` for tests
requiring MATLAB Engine or CVXPY; neither dependency was newly installed.

`python -m tests.research.integration_tracking_smoke conditions` is the one
minimal real two-condition check after commit: one Native baseline and full
independent replay per frozen condition; zero Provider/NMPC/RL and no structure
search. The separate private Store records all actual outcomes and costs.

A-II was committed as `0bfa26d44`. The real two-condition check completed
700 Native + 700 replay steps per condition (2,800 total), two complete independent
receipts and 5.2990101 s cumulative measured numerical cost. Both original task
outcomes were `valid_failure`; joint SELECT correctly rejected them. Provider,
NMPC and RL counts were zero. The sanitized summary is published beside A-I.

## A-III: independent Task Intake preview

The original `schemas/task_intake.py` contract, source tracing, N1 parser,
questions and deterministic review flow remain. `compile_draft` now accepts an
explicit complete snapshot for a registered timed Tracking task and its real
controller/backend compatibility. It copies that exact path, times and limits;
it cannot compile new paths, circles, arbitrary evaluators or changed thresholds.
There is no resolver/Store/Study/Provider/science call inside compilation.

Example supported clauses, separated by semicolons:

- `末端跟踪参考配置的时间轨迹`
- `采用参考配置的轨迹顶点与时间点`
- `世界坐标系`
- `跟踪误差不超过 0.012 m` (must match the supplied BF4 reference)
- `采用参考配置的其余验收与执行设置`

The ordinary CLI accepts offline N1 response JSON and `--compile-reference`
pointing to the explicitly supplied full SessionInput snapshot. Compilation
returns `status=draft`, `authorization=not_authorized`, preserved numeric sources,
frozen `r(t)` constraints and pending original protocol evidence. Tracking has
no invented holding speed. A draft can compose missing-evidence diagnostics;
supplying physical observations still requires the original development-valid
Tracking admission. Questions, event relations, unknown clauses, absent path
adoption, changed limits and unsupported tasks remain unresolved for review.

38 Intake tests passed (12 parser/source tests and 26 compilation checks), with
zero Provider or physics. The directly related stale endpoint-coverage assertion
was corrected to `partial`: its terminal sample covers only part of the holding
window, while full-task support remains false. Reach previews preserve their
original effective configuration. Benchmark studies always read B's frozen
TaskDefinition directly and never depend on Task Intake.

## Remaining scope

No autonomous Provider Study was launched by this integration. Positive SELECT
paths use explicitly labeled fabricated motion with real Store/evaluator gates;
the small real baselines failed honestly. C owns future finite-budget autonomous
Tracking studies. Multi-condition extra repetitions, heterogeneous protocol
aggregation and joint RL/NMPC selection remain explicit unsupported combinations.
The two unrelated old family-space digest/size assertions remain documented
above; no old success result, private Store, raw Provider reasoning or key is
published.
