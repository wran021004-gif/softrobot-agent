# F2 integration: Agent, Reporter and mathematical evidence

2026-10-21; branch `integration/s129-research`; isolated worktree `s129-integration`.
This is engineering integration, not F3 autonomous research or a reopened S12.8 Study.

## History and scope

F0: `6e5c0e4c7f3af62cc345d44461369d795af4da4b`.
Fetched origin before creating the branch; both F1 remote heads matched the request.
Ordinary merges preserve F1-B `fc6ea98cf81e349022b66d9f337181e115cc5626`
and F1-A `f3367e6a6b5c65ab17852d3d8fd72424527c2ee2`.
B merge: `03e6ea34`; A merge: `c9b8a447`; neither required conflict resolution.
The root checkout predates AGENTS.md; the identical F1 branch rules apply here.
No commit, merge or execution targets `feat/sorosim-matlab-nmpc`.

## Five layers and authoritative ownership

| Layer | Modules / unique authority | Output to next layer |
|---|---|---|
| M0 task | `research_tasks.py`, `task_constraints.py`, `platform_analysis.py`; frozen registered TaskDefinition/evaluator | `TaskAnalysisRequirement`, signal signatures, references, indices, thresholds and provenance, input bounds, expressible and unsupported conditions |
| M1 model | Existing GVS/CasADi and SoRoSim/MATLAB model builders and declarations | State/input ordering, operating point, local affine or static model and declared outputs; no new physics |
| M2 method | `math_analysis/trajectory.py`, `task_capability.py`, `kernels.py`, existing SoRoSim optimization/sensitivity | Sampled witnesses, signed best-found scores, bounded diagnostics, fixed/reoptimized comparisons and numerical termination facts |
| M3 evidence | `analysis.py`, `capability.py`, `evidence_views.py`, F0 reporting types, Store and evidence policy | Scoped claim, quantity status/value/source, raw artifacts, measured costs; independent physical acceptance remains separate |
| M4 decision | `research_context.py`, `agent.py`, `reporter.py` | Bounded scientific views, method candidates, original research intent, exact retrieval and resource limits; Agent chooses actions |

Reporter does not define task limits, recompute signed G or compute structural secants.
The local affine `task_capability` is a sampled minimax approximation. Existing SoRoSim
nonlinear optimization retains its own model/objective and recorded solver facts;
similar names do not imply identical mathematics or a common optimality certificate.
No additional TaskSpec, registry, optimizer, scheduler, database or event framework was introduced.

## Interfaces and changed functions

- `analysis_capabilities(configuration, requirements, protocol, *, model=None,
  exact_point=None, remaining_evaluations=None)` in `task_constraints.py`.
- `mathematical_decision_view(card)` and `agent_decision_brief(host)` in `research_context.py`.
- `scientific_feedback(host, value, before=None, *, receipt=None)` and
  `interpretation_priority(report, previous)` in `reporter.py`.
- `recover_feedback(host, agent)` passes the exact saved receipt to report recovery.
- `core.dispatch` records the operation's `scientific_results` in its original receipt output.
- `analysis.decision_result` removes duplicate scope/configuration projection, preserving inference strength.
- `capability_summary` projects original fixed-control scores, verification, active-record indices and exact raw pointers.
- `reporter._comparison` reuses B's explicitly bound mathematical comparison; physical pairing rules remain for physical comparisons.
- `reporter.provider_usage` includes actual cache usage and explicit unknown USD cost.
- `tests/research/s129_provider_check.py` is a bounded engineering entrypoint using existing SDK/Store methods.

The task entry remains `ResearchTaskAdapter.analysis_requirements()` via
`describe_analysis_requirements(configuration, binding)`. Reach compilation, acceptance,
sampling, thresholds and evaluation budgets are unchanged. Tracking name recognition does
not imply an executable registered tracking evaluator. Unsupported predicates retain their identity.
The synthetic moving-reference test is explicitly an engineering fixture, not tracking deployment.

## Capability catalogue

The catalogue enumerates the existing `AnalysisRequest.operation` Literal, then uses
`model_assessment()` and `check_analysis_applicability()` for actual compatibility.
It reports required outputs, constraint kinds, time scope, control treatment, coverage,
evaluation count, prerequisites, remaining count budget and reasons for rejection.
Unknown wall time is `unknown`; final dispatch still owns full admission.

| Existing operation | Scope / prerequisites |
|---|---|
| `equilibrium` | Static target construction; no dynamic acceptance |
| `input_sensitivity`, `design_sensitivity` | SoRoSim static IFT; fixed-input equilibrium; paired candidates for design sensitivity |
| `linearization`, `controllability` | Declared local scoring window; diagnostics |
| `endpoint`, `braking` | Bounded local endpoint constraints; other sampled requirements remain unchecked |
| `instantaneous_braking_v1` | Exact saved state; instantaneous diagnostic |
| `trajectory_feasibility` | Shared local affine input sequence; aligned norm/interval samples |
| `task_capability` | Signed sampled minimax estimate; optional same-input structural replay |

For a supported GVS reach candidate and sufficient count budget, `task_capability` is
applicable; static IFT is not available through that provider. An unavailable signal,
unknown contact predicate or unsupported physics is reported explicitly. Explicit Agent
operations are never replaced by weaker operations. Partial coverage keeps unchecked indices.

## B evidence in new Agent sessions

Result cards supply model declaration, actual time/constraint coverage, quantity status,
signed score definition, discrete replay scope, solver starts, bottleneck/time, input
margin, locality limits, structural deltas, exact sources and unresolved explanations.
Repeated per-quantity problem conditions are projected once, not recalculated.
Full matrices, state arrays and optimization histories remain in original Store artifacts.
Two recent reports are shown; recent mathematical evidence absent from them remains accessible
through an additional bounded mathematical projection and the existing working set.

The saved B engineering example is tested without changing its raw artifact hashes:

| Model case | Original best-found signed G |
|---|---:|
| 0.160 m, reoptimized | -0.1999999515720519 |
| 0.161 m, fixed baseline input | -0.08298844105123286 |
| 0.161 m, reoptimized | -0.09999951729772974 |

Recorded fixed/reoptimized deltas: +0.11701151052081904 / +0.10000043427432215.
Negative values mean modeled sampled constraints are inside their bounds. Both candidates'
three starts reached 100 iterations without reporting convergence. Replay is checked;
optimal task violation and rigorous floating-point upper bounds remain uncertified.
Neither result proves MuJoCo task acceptance, nonlinear/hardware performance or optimal structure.

## Exact recovery and Reporter priority

Saved original tool feedback wins. Otherwise original tool ID, request hash, execution receipt
and receipt output determine the result. Analysis uses the receipt output artifact itself;
new Plan receipts contain the exact newly produced result list. Multiple results produce
multiple F0 one-result reports; feedback carries the primary report and complete report index.
F0's one-result-summary contract is unchanged.
An already saved report for the same exact results is reused. No global latest-result fallback
exists during recovery. Missing binding preserves the original operation facts and marks
interpretation unavailable. Science workers and resource reservations are never replayed.

Every result gets a deterministic report. Explicit investigation, first mathematical method,
structural comparison, new task bottleneck, first complete pass and best complete result
improvement can receive an explanation. Routine repetitions get a persisted skipped revision.
This is an observable rule, not a calibrated information score or an action planner.
Existing protected budget and unknown-send checks still apply; a skipped explanation cannot
remove a scientific result. Reporter runs only after the main response is consumed.

## Validation and byte audit

Initial import/F0/F1 test run: 35/35 passed, including the existing real small GVS pair.
The old M2 assertion was reproduced: 11,501 bytes versus its 8,192-byte limit.
The duplicated EvidenceSummary operating point/assumptions/coverage contained repeated full
configuration. Removing only that redundant projection reduces the entry to 2,672 bytes;
the old compact entry remains 40,960 bytes. The original assertion is unchanged and passes.
All 13 replay records remain readable over seven exact pages; original artifact SHA is unchanged.

Old tests need two historical SQLite stores absent from a fresh worktree. Read-only SQLite
backup copies from the A worktree were used locally; sealed source stores were not changed.
The original 19 layered-context/working-set/session-recovery tests pass, including 14 process
interruption scenarios. Test-generated scope.json changes are restored after runs.
Final regression and real Provider measurements are recorded in the accompanying evidence audit.

Reproduction (PowerShell, worktree root):

```powershell
$env:PYTHONPATH='.;tests/research;C:\Program Files\MATLAB\R2024a\extern\engines\python\dist'
$env:OPENBLAS_NUM_THREADS='1'; $env:OMP_NUM_THREADS='1'; $env:MKL_NUM_THREADS='1'
& D:/softrobot-agent/.mainline5-env/Scripts/python.exe -m unittest test_s129_integration.IntegrationTests test_s129_integration.CrossTaskTests -v
& D:/softrobot-agent/.mainline5-env/Scripts/python.exe -m tests.research.s129_provider_check
# --live requires the existing credential and an explicit bounded engineering grant.
git diff --check
```

## Production admission and F3

The engineering check freezes a new isolated Study with at most 10 Provider sends,
main <=7 / Reporter <=3, zero backend/NMPC/PPO launches. One unused mathematics slot
keeps the original count-based closeout semantics; no scientific worker tool is exposed.
It reuses saved B engineering artifacts, their original ownership and exact source hashes.
The candidate handoff flag applies only to this engineering Study. No global default changes.
Raw Provider responses, SDK history and Store stay under ignored `runs/`; only non-secret
derived counts, hashes and verdicts are published.

F3 must create and authorize a new frozen Study; bind its clean committed implementation;
verify applicable model/provider/schema scope and its finite grant; record the exact F2
validation evidence and approval in the original Store; explicitly set that new Study's
`pilot.session_handoff_live_admitted=true`, then use `converse(..., session_handoff=True)`.
This is permitted only after offline, process recovery and actual Provider gates all pass,
with no unsettled receipts, unknown sends, unmatched tool IDs or unconsumed responses.
An engineering check is not blanket approval for all future Study configurations.

No tracking evaluator, contact/obstacle/hybrid solver, rigorous minimax optimality certificate,
regional structural guarantee or F3 scientific experiment is added by this change.

## Final engineering disposition

Across the initial 35-test F0/F1 suite and the affected 117-test suite, 132 distinct tests
have passing final results. The affected suite initially passed 116/117; the remaining
test assumed a full and compact EvidenceSummary must be identical. It now checks every
retained field exactly while scope stays accessible through the original pointer.
The 41-test focused rerun passed, followed by seven focused projection/recovery tests.
The old 1:5 size assertion was not relaxed. `git diff --check` passes.

The final offline check runs five mock main requests plus one mock Reporter request,
three actual SDK Sessions and two handoffs. Native investigation and diagnostic tool IDs,
H-F2 intent, original scientific hashes, independently reopened Store/SDK and accounting
remain consistent. These token counts are explicitly mocked, not real usage.
An earlier driver preflight correctly rejected B evidence under the unrelated mirror task;
the driver now freezes the original B task before preparation, without changing acceptance.

After the initial automatic-review rejection, the user explicitly approved the recorded
[egress scope](../../evidence/s129_integration/provider_scope.json). Real requests then ran in
one isolated Study, `s129-f2-live-3d6206f07b`, with no budget reset. The first stage used
implementation `40a1a340`; the same-Study corrective stage bound `ea637c1f` through the
existing migration path. All original results, failures and costs remain immutable.

| Actual usage | Requests | Prompt | Completion | Cache hit | Cache miss |
|---|---:|---:|---:|---:|---:|
| Main Agent | 7 | 244,542 | 11,987 | 123,776 | 120,766 |
| Reporter | 2 | 63,750 | 25,638 | 256 | 63,494 |

Total 9/10 requests; USD **unknown**. Three real SDK Sessions and two real handoffs
passed independent reopening, native schema/tool/receipt pairing and ledger checks.
One invalid evidence reference was rejected before reservation; the main Agent corrected
it autonomously. Reporter ran only after main responses were consumed. No unknown sends,
unsettled receipts, unconsumed responses or new science workers remain.

The first Reporter interpretation was explicitly unavailable: it invented a raw pointer
from a summary alias. Its deterministic report survived unchanged. Exact pointer guidance
and B comparison scope were fixed; 20 focused tests and the offline three-Session check
passed. A distinct follow-up investigation used the same remaining grant, produced a legal
Reporter interpretation, and changed only the interpretation slot. Original failures were
not retried or overwritten. All interpretation sources resolve to original evidence.

**Production admission remains closed.** The final main response corrected margin meaning,
score versus secant, comparison scope and replay versus optimum, and retained H-F2. It
nevertheless called the candidate's larger (worse) minimax score a "better score" and used
`/score_semantics`, a summary alias, like a raw source path. This fails the required
scientific-interpretation gate even though all authoritative numbers and hashes are intact.
The main 7-request ceiling is exhausted; the remaining total slot cannot authorize another
main request. No automatic resend or fresh Study/grant was used to bypass that limit.

The deterministic projection now explicitly says smaller is better; its focused regression
passes. That final wording change has **not** been validated by another real main request.
The engineering Study's candidate handoff flag is disabled again, with the blocked admission
record saved in its original Store. A separately authorized bounded validation must resolve
this gate before F3. No F3 Study or sealed S12.8 execution was started.

Commits `9fe8383c` and `40a1a340` were ordinarily pushed before live validation;
`ea637c1f` contains the live source/scope correction. Final audit and directional wording
are committed separately. The isolated integration branch is the only push target.
Detailed checks: [validation.json](../../evidence/s129_integration/validation.json),
[live_validation.json](../../evidence/s129_integration/live_validation.json).
Actual B-to-Agent sample: [mathematical_decision_sample.json](../../evidence/s129_integration/mathematical_decision_sample.json).
