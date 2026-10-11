# Current-study mechanics and control research

Base: `653530f67097deb064a23290b48054c5b59059c2` on the verified
`feat/unified-research-core`, fetched once with no newer descendant.
Worktree: `D:\softrobot-agent\.worktrees\mechanics-control-mainline`.
Use `D:\softrobot-agent\.mainline5-env\Scripts\python.exe` and the existing
`requirements-strands-mainline5.lock`. Historical studies remain sealed.

Every command uses the fresh specification explicitly:

```powershell
Set-Location 'D:\softrobot-agent\.worktrees\mechanics-control-mainline'
$studyPython = 'D:\softrobot-agent\.mainline5-env\Scripts\python.exe'
$studySpec = 'examples/mechanics_control/specification.json'
& $studyPython -m tools.research_core prepare --spec $studySpec
# Commit scoped implementation and spec before any scientific dispatch.
& $studyPython -m tools.research_core bind --spec $studySpec
& $studyPython -m tools.research_core_demo diagnostic --spec $studySpec
& $studyPython -m tools.research_core_demo integration --spec $studySpec
& $studyPython -m tools.research_core live --spec $studySpec
& $studyPython -m tools.research_core status --spec $studySpec
& $studyPython -m tools.research_core export --spec $studySpec
# Once native STOP is accepted, package and verify saved evidence without new experiments:
& $studyPython -m tools.research_core_mechanics_delivery --spec $studySpec
```

These are the commands for this study, not a recipe for rerunning a sealed
delivery. A later study needs its own ID, actual start clock, authorization and
independent ledger. Use `recover --spec ...` for pending output; commit repairs
then `migrate --spec ... --reason ...` without resetting any counter or clock.

| Operation | Numerical variables | Responsibility |
|---|---|---|
| `mechanics` | Existing `d`, full-horizon states, tensions, two task slacks | Offline mechanics/motion candidate generation |
| Runtime NMPC | Predicted states and future tensions | Control the fixed structure with fixed settings |
| `search` with selected weights | Existing holding/terminal speed weights | Control adaptation at fixed structure |
| Optional `search` with `d` | Existing length coordinate | Evidence-supported local structural correction |

The shared `research_plan` also supports direct `propose`, `execute`, independent
`replay`, diagnosis, confirmation and STOP. The native principal chooses freely;
the engineering demo is labeled separately. There are no imposed weight-direction
rules. Read-only experience retrieval retains original draft status and records
actual retrieval/disposition. Startup evidence is supplied context.

Mechanics reuses the CasADi/GVS workspace, exact AD, retained-point selection,
checkpoint packaging recovery and independent BDF replay. The current adapter
does not import a historical service grant or choose an old environment mode.
The domain stays `d in [-1,1]`, lengths `.16+.0055*d` and `.11-.0055*d` m, total
`.27` m. Offline objective weights are independent of NMPC speed weights.
The `.2 N` guess is numerical initialization, not physical pretension or equilibrium.

A solve returns exact trajectory/checkpoint references, variable ordering,
time grid, raw and retained selections, objective definition, termination, hard
residuals, relaxed feasibility and original task violations. `replay` reports BDF
integration gates separately; BDF is not independent physical validation. A valid
returned structure can enter an explicitly exploratory MuJoCo evaluation even if
its offline task flags fail. The goal-based NMPC receives structure; the trajectory
stays evidence. Optional trajectory initialization and legacy skill admission are
deferred.

`search.mechanics_source` cites an owned mechanics solve result and requires fixed
`d` equal to the handoff. Unused coordinates remain fixed. Both `.025` and `.10`
boundary initializations are covered by focused fixtures; duplicates are skipped
by the existing coordinate method. Feedback reports requested/actual values,
distinct configurations, partial batches and failures. Ranking uses the frozen
task metrics, never weighted objective comparisons across NMPC weights.

Immutable candidates can be shared by identical constructions. Each launch has
a fresh execution ID and child owner under this study, with positive measured
cost. Separate handoff artifacts preserve every mechanics-to-candidate relationship
even when construction returns an existing candidate. Cached operation feedback
states zero additional execution cost and retains earlier costs. Imported history
keeps its original ownership. Confirmation must cite `selected_execution` using
the exact passing result EvidenceRef; packet feedback lists eligibility and concrete
reasons. A hash or candidate reference is insufficient.

The specification caps actual sends32, public operations128, offline NLP2, BDF2,
MuJoCo8, standalone NMPC4/600s, total charged numerical10800s and activity12h.
Each offline worker reserves900s and replay450s. All exploratory admissions protect
two confirmation launches and their3800s allowance, the final4 sends and final30min.
Known killed/waited timeouts count. Unknown outcomes retain reservations; completed
checkpoints recover without a second NLP. Internal recovery is charged once in its
enclosing simulation. Ceilings are not targets.

Complete new update records include the resolved serialized optimization problem,
absolute schedule, warm source, initialized/clipped vector, bounds, scales, solver
settings, nominal workspace, tracing mode and raw/retained/recovered/delivered plans.
Diagnostic reconstruction compares objective/constraint values at recorded points
before solving. Historical inputs lack the full resolved serialized problem, and
a fresh worker does not recreate cache/timing history. Production diagnostics
retain the original tracing setting; fixed iteration is diagnostic only.

Resolved problem definitions are stored once per graph/horizon in exported
`p_<10-character-prefix>.json` files, with full hashes in each reference. Each update keeps a hashed file reference and
its own complete variables/bounds/initial guess. Diagnosis verifies the file hash
then restores that update's values. Progress replacement retries brief Windows
reader conflicts for at most2s, outside the numerical solver; it never repeats a
controller command. A known incomplete launch is charged and its `.tmp` record
is archived. The first engineering launch hit such a replacement failure after20
computed updates (19 in the replaced file); two explicitly new launches are
admitted after repair. Mechanics and BDF are reused, not repeated. A conservative
dependency migration records the changed storage implementation and keeps all
old costs and the task-start clock. No extra physical baseline is prescribed.
The next launch failed on an overly long graph filename after its first computed
update, before that input record was durable. This gap is reported, not reconstructed
as observed data. Short graph filenames now match the known-working progress
basename length; diagnosis verifies both full file and expression hashes. Both
failed launches remain charged. Any continuation has a new explicit operation ID.

```powershell
# Only for this study's known progress-write failure, after committing/migrating:
& $studyPython -m tools.research_core_demo archive-incomplete --spec $studySpec
& $studyPython -m tools.research_core_demo continue-control --spec $studySpec
```

The original target `[.29,.035,.19]` m, physical zero state, mount/gravity,
discretization/mapping, seed17, six ideal tensions0..8N, `.35s` duration, `.01s`
control and `.0005s` physics are frozen. Holding includes `.30` through `.35s`, with
`.01m` position and `.02m/s` speed limits. Passing repetitions support only limited
tested acceptance. Structure comparisons need comparable control adaptation;
unmatched observations cannot establish structural superiority.

Focused checks: `tests.test_research_core`, `tests.test_research_core_mechanics`, and
`tests.test_casadi_feedback.PlanTests.test_solver_return_survives_candidate_packaging`.
They use substituted evaluators and do not add scientific simulations. The bounded
real demonstration is the integration execution. Final evidence includes original
native decisions, exact source versions, counters, costs, complete execution inputs,
confirmation status and a hashed non-secret artifact archive.

The completion command verifies every archive member, exact raw failed-run files,
distinct physical execution identities, settled calls, budget ceilings and no
provider requests after accepted STOP. It reports the one unavailable input from
the graph-path failure explicitly. Current mechanics results remain readable in
protected closeout; read-only mixed diagnosis keeps offline and incomplete
execution facts separate from complete MuJoCo evidence.
