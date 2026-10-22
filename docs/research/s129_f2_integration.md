# F2 integration: Agent, Reporter and mathematical evidence

## F3.0 citation repair: offline complete; admission still closed (2026-10-22)

The sealed failure below is unchanged. A read-only inspection of its actual request,
raw response and SDK snapshot confirmed 11 interpretations and 17 unique sources:
16 resolve, and `/trajectory/score_semantics` does not. The request's L2 contains
that derived summary key, whereas the original definition is
`/trajectory/problem_definition`. The complete SDK message identity matches its
original anchor. All 13 files in the original archive, including SQLite, receipts,
configuration, scope and SDK history, have identical before/after SHA-256 hashes.

`reporter._wire()` now builds a request-local `source_catalog` from typed report
locations, explicit capability pointers and requested exact reads. It deduplicates
locations and verifies each with `read_evidence(..., record_read=False)`. Untyped
summary keys are never converted to raw paths. The saved B pair produces 64 linked
sources, including the problem, scores, fixed control, comparison scope, solver
starts and replay. No new evidence registry or report schema is introduced.

Provider output is now `{"interpretations":[{"kind":"new_information",
"text":"...","source_ids":["S1","S2"]}]}`. `_finish()` resolves IDs using the
**persisted request's** catalog, then retains the existing scientific artifact
scope check and raw read validation. Unknown/malformed IDs and direct raw-location
output are rejected, preserving deterministic L2. Persisted ScientificReport still
uses `ReporterInterpretation.sources: list[EvidenceLocation]`. Requests without a
catalog continue through the original `sources` parser; saved responses recover
without resend or another charge. Previously completed reports are not rewritten.
The default instruction asks for 1–3 substantive interpretations; explicit complex
investigations can use more. Provider configuration, thinking, max_tokens and budget
validation are unchanged. Historical Reporter usage was 62,282 prompt / 21,956
completion tokens (17,508 reasoning); no new live token measurement is claimed.

The existing `signed_score_comparisons()` remains the sole projection owner.
`mathematical_decision_view()` already forwards it to L1; Reporter receives the
same deterministic comparisons. `score`, direct `delta`, recorded
`normalized_secants` and positive `control_reoptimization_improvement` have explicit
definitions. Recovery fractions appear only for a positive fixed-control loss
with nonnegative recovery and residual, using that original loss as denominator.

| Saved/derived quantity | Value |
|---|---:|
| Baseline reoptimized score | -0.1999999515720519 |
| Candidate fixed-old-control score | -0.08298844105123285 |
| Candidate reoptimized score | -0.09999951729772974 |
| Fixed-control degradation | +0.11701151052081904 |
| Reoptimization improvement (positive recovery) | +0.017011076246496892 |
| Candidate reoptimized minus candidate fixed score | -0.017011076246496892 |
| Residual reoptimized degradation | +0.10000043427432215 |
| Recovery / original fixed-control loss | 0.14537951156070436 |
| Residual / original fixed-control loss | 0.8546204884392956 |
| Recorded fixed-control normalized secant | 18.72184168333103 |
| Recorded reoptimized normalized secant | 16.00006948389153 |

The structural step is `0.0010000000000000009 m`, normalization scale `0.16 m`;
secants equal the corresponding structural delta divided by the step, times the
scale. These are computed local-model comparisons under the recorded task, input,
sampling and solve-budget conditions. Optimality is uncertified; neither true
optimal structural ranking nor MuJoCo acceptance follows.

**20 distinct focused offline tests passed**: 10 AgentReportingTests, 7
IntegrationTests, the F30 production delivery/reopen test, and 2 native SDK
investigation/Reporter-boundary tests. The latter reuses available, invalid source,
unknown-send and interrupted-response cases. Real Strands SDK plus MockTransport
preserves main → Reporter → main, interpreted L1 before the second main request,
receipts and recovery. No historical 132-test sweep or scientific computation ran.
The 18-test group completed in 13.799 s, and the additional 2 tests in 13.949 s.
`git diff --check` passed. Local unittest stderr formatting by PowerShell does not
represent test failures; both processes exited 0 with `OK`.

```powershell
$env:PYTHONPATH='.;tests/research;C:\Program Files\MATLAB\R2024a\extern\engines\python\dist'
$env:OPENBLAS_NUM_THREADS='1'; $env:OMP_NUM_THREADS='1'; $env:MKL_NUM_THREADS='1'
& D:/softrobot-agent/.mainline5-env/Scripts/python.exe -m unittest test_s129_agent_reporting.AgentReportingTests test_s129_integration.IntegrationTests test_f30_provider_check.F30Tests.test_production_delivery_reopens_with_zero_science -v
& D:/softrobot-agent/.mainline5-env/Scripts/python.exe -m unittest test_s129_agent_reporting.ReportingSessionTests.test_native_investigation_delivers_l1_before_next_model_in_same_invocation test_s129_agent_reporting.ReportingSessionTests.test_native_science_tool_reporter_boundary_and_unknown_send -v
```

Derived audit: [f30_citation_repair.json](../../evidence/s129_integration/f30_citation_repair.json).
Separate **unapproved, unexecuted** revalidation proposal:
[f30_revalidation_scope.json](../../evidence/s129_integration/f30_revalidation_scope.json).
It names a new Study and independent Store, <=2 main + <=1 Reporter requests,
zero science workers and explicit outbound scope. Freeze the exact final pushed
delivery HEAD reported to the user before any newly authorized run. The old fixed-ID
live checker cannot be reused for this proposal. No new Study or authorization was
created. F3 remains closed; offline engineering success is not live admission.

## F3.0 final disposition: FAILED; F3 not started (2026-10-22)

The single authorized live validation is complete. Study `f30-live-20261022`
bound clean, ordinarily pushed implementation `56d8af3663d01bd8390dfcdd44178b4474eebe93`.
The actual production sequence was **main → Reporter → main**, with one native
`research_investigate` call, matched SDK tool result and settled original receipt.
The first main response was consumed before Reporter started. Reporter finished and
archived its original response before the second production `before_model()` built L0.

**Full scientific delivery admission failed.** Reporter invented raw JSON pointer
`/trajectory/score_semantics` on candidate result `9e7a2164…`; the actual raw score
definition is under `/trajectory/problem_definition`. Of its submitted unique
source pairs, one is invalid. The formal validator rejected the entire interpretation
with `KeyError: 'score_semantics'`, preserving the original response and deterministic
report. The second main request received **deterministic L1 plus unavailable status**,
not an accepted Reporter interpretation and not a repeated full L2. This verifies
fallback/recovery, but explicitly does not satisfy the requested live Reporter gate.
No prompt correction, Provider resend, grant reset or replacement Study followed.

The main Agent correctly stated that the changed structure's reoptimized computed
score worsened by `+0.1000004343`, while reoptimizing control on that same structure
improved the computed score by `-0.01701107625`. It distinguished sampled replay,
uncertified optimization and unperformed MuJoCo acceptance, and proposed a read-only
saved-start/bottleneck diagnosis without executing it. These are observations about
its use of deterministic evidence; they cannot establish successful Reporter influence.
The final prose also has limitations: its 17% recovery / 83% remaining decomposition
uses the residual 0.10 gap as denominator. Relative to the original fixed-control loss
0.11701151, recovery is about 14.54% and residual loss about 85.46%. It also conflates
the raw score delta with the separately length-normalized secant. Saved-start diagnosis
can inspect numerical evidence but cannot by itself establish a true structural cause.

| Actual role | Requests | Prompt tokens | Completion tokens | Cache hit | Cache miss |
|---|---:|---:|---:|---:|---:|
| Main Agent | 2 | 34,110 | 3,090 | 512 | 33,598 |
| Reporter | 1 | 62,282 | 21,956 | 384 | 61,898 |

Total: 3/3 Provider requests, 1/12 public operations, **USD unknown**.
Physical launches, mathematics, NMPC, NLP, BDF, PPO stages/actions and independent
RL evaluation are all zero. Remaining 11 public operations are not transferred.
All requests have original response/usage/receipts; no unsettled receipt, unknown send,
unconsumed response or occupied resource remains. Store and actual SDK snapshot were
independently reopened in another process; tool IDs, final message identity and original
B artifact hashes match. The Study is stopped by the existing engineering count-budget
closure, which does not fabricate a model STOP or scientific selection. Handoff remains
unadmitted; no session rotation was attempted or claimed in this F3.0 check.

The independent semantic audit and failed-admission record are preserved in the original
Store. Only derived audit data and scope are published:
[f30_live_validation.json](../../evidence/s129_integration/f30_live_validation.json),
[f30_scope.json](../../evidence/s129_integration/f30_scope.json).
Raw requests/responses, complete SDK history and Store remain local under
`runs/research/f30-live-20261022/`. The decisive unresolved blocker is accepted,
source-valid real Reporter delivery followed by a main decision based on that delivery.
This failed one-shot grant does not authorize another attempt.

**F3 conditional authorization was not activated.** No F3 configuration, Study,
Provider request or scientific experiment was created; no MuJoCo solution, autonomous
multi-round strategy adjustment or F3 research success is claimed. F2 is blocked rather
than declared admitted. No F4 work, sealed Study changes or unrelated branch merges ran.

## F3.0 production-entry preparation (2026-10-22)

Fetched origin and verified `13ddf460f9cb792cfb8e809a4e4f225c0bfd22f0` on both
the clean integration worktree and remote before this work. Historical grants remain sealed.
`tests/research/f30_provider_check.py` invokes production `converse()` directly,
including its actual native registry, hooks, pre-decision Reporter delivery and SDK settlement.
Its only live wrapper rejects excess role counts before `LiveBoundary` reserves/sends.
There is no alternate Agent builder, tool executor or injected scientific answer.

The fixed live ID `f30-live-20261022` can be created only once. Its independent
identity-bound authorization permits <=2 main, <=1 Reporter, <=3 total sends,
12 public operations and zero scientific worker budgets. It imports the original
F1-B artifacts with an explicit source manifest and preserves their content hashes.
Provider configuration is unchanged: `https://api.deepseek.com/chat/completions`,
`deepseek-flash`, thinking enabled, reasoning high, max_tokens 32768. Outbound data
is the frozen project task/model/design context, scoped B evidence, tool feedback,
Reporter interpretations and accounting identities. No unrelated workspace data,
credential-file content or other Studies' raw SDK histories are included. Raw
Provider bodies, SDK snapshots and Store remain under ignored `runs/research/`.

Zero scientific budgets exposed a production admission issue: scientific exhaustion
previously removed investigation and suppressed Reporter delivery. The explicit
`engineering_investigation` mode is validated to allow only investigation capability,
diagnose/stop Plans and zero science counts; only this mode omits the scientific-route
exhaustion trigger. Provider/public protection remains active. Formal research exhaustion
is unchanged. Mathematics is removed from the dynamic schema when disabled/exhausted
even without readiness configuration; engineering investigation also removes SDK retrieval.

Nine focused tests passed: four F3.0 configuration/production/schema/counter tests,
existing Reporter recovery (available/invalid pointer/unknown send/interrupted archive),
malformed/truncated fallback, protected Reporter budget, exact B comparison pointers,
and internal-report SELECT-credit rejection. A test fixture initially reused null request
IDs and was corrected to use distinct durable IDs; an incorrectly named test class was
corrected. Neither issue involved a live send. The existing F2.1 31-test evidence is reused.
The final offline audit independently reopens Store and SDK, verifies native tool IDs,
receipts, L1-before-main order and unchanged scientific artifacts. Its usage is synthetic,
and it is **not** scientific or live admission. See
[f30_offline.json](../../evidence/s129_integration/f30_offline.json).

Run with the installed research interpreter and MATLAB engine import path:
`python -m tests.research.f30_provider_check --live`; never rerun a live failure.
`--audit STUDY_ID` only reopens original records and does not send requests.
F3 remains conditional on a separate semantic audit of the real main/Reporter outputs.

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

## F2.1: science before the next decision (2026-10-22)

Implementation commit: `c8dd71de`; documentation/audit committed separately.
Disposition: **offline_ready; production handoff remains closed**. Fetched origin;
the clean integration worktree and remote both started at `8a1640c67e67329f7d51c0209cdf3743289597b2`.
No new live Provider request, scientific worker, S12.8 continuation or F3 Study ran.
The historical sections above describe F2; their outer-invocation Reporter timing
is superseded by the following F2.1 contract.

### Audited input and implementation

Read-only inspection of the original F2 Store confirms that its engineering driver
put the initial packet in user history and full packets in handoff messages. Its
seven main requests had 1,936-byte system-message arrays, 6,254-byte tool-schema
arrays and 78,049–245,045-byte history arrays. Each request after handoff retained
one full handoff packet. The two Reporter history arrays were 106,249 and 107,604
bytes: Reporter deliberately consumes full L2, not L0. These are component sizes,
not token measurements or a claim that every F2 driver request used the production
`before_model` hook. Production source separately duplicated the current packet
in the system prompt and handoff user message, and expanded reports in both tool
feedback and L0. No raw request body, SDK history or private Store was added to Git.

Changes remain in the existing owners:

- `reporter.py`: `scientific_feedback` and `investigate` save full reports but return
  `scientific_delivery_v2` acknowledgements; `current_reports` resolves revisions;
  `reporter_handoff_summary` supplies deterministic L1 or saved Reporter interpretation.
- `agent.py`: `deliver_science_before_decision` and the existing async `before_model`
  enforce delivery before a new main request. `converse` can recover a received
  intra-invocation Reporter response using the exact saved SDK boundary identity.
- `research_context.py`: `agent_decision_brief` consumes at most two recent L1
  deliveries, removes repeated latest mathematical scope, and preserves budget,
  acceptance, candidate/control binding, action schemas and exact STOP lookup.
  `mathematical_decision_view` replaces full solver starts/sample indices with
  counts, termination facts and exact detail references.
- `research_action_trace(host, limit=5)` derives recent actions and total/error
  counts from original plans, native events and exact receipts. Full trace is
  retrievable through `evidence_read(view='working_set', pointer='/action_trace')`
  with the existing working-set anchor. Ordinary evidence reads do not count.
- `capability.py`: `signed_score_comparisons` projects B's recorded controlled
  comparisons; no solver or new mathematical certificate was introduced.
- `session_handoff.py`: only new initial-message construction changed. The short
  anchor retains the existing preparation/Store/SDK binding. `safe_boundary`,
  `trusted_history`, `validate_snapshot` and historical snapshots are unchanged.

### Actual delivery and recovery boundary

The production chain is:

`worker/Store + execution receipt (L3) -> assemble/_save full ScientificReport (L2)
-> short native toolResult -> SDK tool-result history -> before_model
-> complete_reports -> saved interpretation/skipped/unavailable revision
-> reporter_handoff_summary (L1) -> decision_packet (L0) -> main Provider`.

An acknowledgement contains `delivery_version`, `execution_status`,
`scientific_result_reference`, `report_reference`, `interpretation_status`, and
the existing formal-read obligation. Multiple-result receipts retain the complete
`scientific_result_index`; recovery never selects a globally latest result.
Investigation additionally returns its question and selected-result count.
For example, `evidence_read(reference=ack.report_reference, view='full',
pointer='/report')` retrieves full L2, while a raw result reference plus
`/trajectory/structural_comparison/fixed_control/best_found_violation` retrieves
the original fixed-input score. Neither report delivery nor internal Reporter
reading grants SELECT/STOP reading credit.

Strands **1.59.0** was inspected locally: `live_model_class.stream` consumes the
original Provider response after stream conversion; `_handle_tool_execution`
awaits `_append_messages(tool_result_message)` before recursing into the next
`BeforeModelCallEvent`. F2.1 checks no unsettled Provider/science receipts, no
unmatched tool IDs, and preserved tool-result statuses, then explicitly saves an
SDK snapshot before Reporter. Public SDK offload may shorten large requested
evidence text; immutable original feedback and SDK stash remain intact.
This is not the stricter completed-invocation boundary used by Session handoff.

The actual real-SDK MockTransport test observes, in one invocation:

1. Initial L0 and first main request; original response is consumed.
2. Explicit large `evidence_read` and mocked science executor using saved B data;
   original receipt, full L2 and both original tool feedback records persist.
3. SDK pairs results; `science_delivery_boundary` snapshots the exact history.
4. Independent Reporter request; full revision saved, `reporter_completed`, then
   `r3_response_processing=reporter_archived`.
5. New L0 contains completed L1; only then the second main request is sent.

The observed Provider order is **main, Reporter, main**. A separate production
test checks the same ordering for `research_investigate`. Invalid Reporter pointers
produce `unavailable` plus deterministic L1 before the second main request.
Unknown Reporter sends block both continuation and restart. A crash after HTTP
receipt but before Reporter archival recovers the saved response without another
send/charge; the next main request is the only new request. Tampering with that
SDK snapshot is rejected before recovery. Main `unconsumed_response` still restores
the original system prompt/tool schemas and is replayed before any new L0.

### Numbers, scope and trace

Compact UTF-8 JSON on the same saved B fixture configuration (bytes, not tokens):

| Surface | Before | F2.1 |
|---|---:|---:|
| Full default L0 packet | 69,144 | 45,301 |
| One scientific tool acknowledgement | 54,367 | 648 |
| New Session initial messages | 74,882 | 350 |

The L0 measurements precede model requests; the short anchor was also measured
through actual SDK handoff. No arbitrary compression threshold was used.
Full L2, candidate/control access, mathematical method applicability, task
acceptance and budgets remain available. FamilySpace and frozen analysis protocol
were retained. Existing Session histories are not cleared or migrated.

For saved B, the two explicitly different directions are:

| Comparison | Baseline score | Candidate score | Delta | Computed direction |
|---|---:|---:|---:|---|
| New structure reoptimized vs baseline reoptimized | -0.1999999515720519 | -0.09999951729772974 | +0.10000043427432215 | worse |
| New structure reoptimized vs same structure fixed old control | -0.08298844105123285 | -0.09999951729772974 | -0.017011076246496892 | better |

`smaller_is_better=true`; both sets of three starts reached 100 iterations without
convergence; optimality remains uncertified. The stored `computed_estimate`
comparison owns matched task/model family, physical tensions, channel order,
sampling, horizon and solve-budget scope. Missing or inconclusive comparisons
return `not_comparable`. Tests resolve every displayed score location and reject
invented summary aliases. These are local computed model scores, not MuJoCo
performance or optimal-structure rankings.

The published audit contains an actual saved offline trace: original tool
`native-science`, request `native-native-science-analysis`, method `task_capability`,
and the exact receipt output/result reference. It intentionally has no invented
hypothesis because that direct request had none. The Plan test separately resolves
`/original_plan`, retains H-fixture and its expected/weakening observations, and
checks failure/rejection counts without turning Reporter prose into a conclusion.
Raw B artifacts, original receipts, scientific costs and tool IDs are unchanged.

### Reusable instructions and validation

For a **new** Study, put the following concise rule in its existing
`execution_instructions` source, replacing obsolete `decision_brief_v1` or
immediate-full-report wording. Do not edit frozen S12.8 instructions:

> CURRENT_RESEARCH_PACKET is the current research decision view. Scientific tool
> results acknowledge execution and saved references; use L1 deterministic facts
> and saved Reporter interpretations for scientific judgment. Reporter mechanisms
> are testable hypotheses, not authoritative physical facts. Use evidence_read or
> research_investigate for details. Choose the next structure, control, mathematics,
> diagnosis or stopping action freely; there is no fixed method order. Use structured
> score direction, comparison scope and optimality status as the numerical authority.

The runtime packet now carries these delivery rules, and `_wire` reinforces the
distinction between observations, model computations, hypotheses and open questions.
Provider settings, Reporter max_tokens, frozen Study configuration and budget
sources are unchanged.

Validation: **31 distinct targeted tests passed**. The 26-test reporting,
integration and Session-recovery run includes 14 killed-process scenarios.
The final 11-test run rechecks the native SDK boundary and five integration cases,
and adds five Provider-output/replay tests. No historical 132-test sweep or new
MATLAB/MuJoCo/NMPC/PPO computation was run. `git diff --check` passes.

```powershell
$env:PYTHONPATH='.;tests/research;C:\Program Files\MATLAB\R2024a\extern\engines\python\dist'
$env:OPENBLAS_NUM_THREADS='1'; $env:OMP_NUM_THREADS='1'; $env:MKL_NUM_THREADS='1'
& D:/softrobot-agent/.mainline5-env/Scripts/python.exe -m unittest test_s129_agent_reporting.AgentReportingTests test_s129_agent_reporting.ReportingSessionTests test_s129_integration.IntegrationTests test_s127_session_recovery.SessionRecoveryTests -v
& D:/softrobot-agent/.mainline5-env/Scripts/python.exe -m unittest test_s127_provider_output.ProviderOutputTests -v
```

Derived audit, interface examples, source locations and actual event order:
[f21_delivery.json](../../evidence/s129_integration/f21_delivery.json).

The remaining gate is real Provider scientific interpretation. Recommended separate
authorization: a new frozen engineering Study, **at most two main requests plus one
Reporter request**, one read-only investigation of the existing B pair, zero
science workers/backends, no automatic retries or grant reset. Check that the second
main request receives completed L1 and correctly states both directions, uncertainty
and exact sources. STOP at any unknown send or semantic failure. Only after that
gate passes and explicit admission is recorded should a separately budgeted F3
Study be authorized. The exhausted F2 seven-main grant is not reused.
