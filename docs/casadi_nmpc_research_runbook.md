# Bounded candidate-to-NMPC research

This activity starts at **2026-10-10 19:12:47 Asia/Shanghai**, including engineering.
Fetched source `fix/casadi-feedback-closeout` remained
`056707b4499327ad944df8b7f25460e79dabdee1`. The isolated branch is
`feat/casadi-nmpc-research`. Historical STOP activities stay sealed.

Use `D:\softrobot-agent\.mainline5-env\Scripts\python.exe` from
`D:\softrobot-agent\.worktrees\casadi-nmpc-research`. Python 3.11.16,
CasADi 3.7.2, SciPy 1.17.1, MuJoCo 3.13.0, Strands Agents 1.59.0 and
Harness 0.2.0 were verified once; no environment rebuild or upgrade.

```powershell
$studyPython = 'D:\softrobot-agent\.mainline5-env\Scripts\python.exe'
& $studyPython -m tools.research_casadi_feedback prepare
# Commit implementation, frozen specification and focused-check evidence.
& $studyPython -m tools.research_casadi_feedback bind
& $studyPython -m tools.research_casadi_feedback live
& $studyPython -m tools.research_casadi_feedback stop
& $studyPython -m tools.research_casadi_feedback export
```

`prepare` is idempotent and preserves the original clock and counters. Read
[the frozen specification](../examples/casadi_nmpc/specification.json) before dispatch.
Reuse `load_credential(Path.home()/'.codex'/'.env')`; never print credentials.
The existing authenticated, non-streaming DeepSeek transport keeps
`deepseek-flash`, thinking enabled, high reasoning effort and 32,768 output tokens.
There is one research LLM, native typed tools, sequential execution, the existing
asynchronous runtime, Host/Store and context retrieval; transport closes in `finally`.

| Native plan action | Operation |
|---|---|
| `solve` | One existing objective, weights, initialization and grid choice; save checkpoint/candidate, then independent BDF replay |
| `diagnose` | Read-only synthesis of exact evidence references; original hypothesis stays separate from generated facts |
| `diagnostic_replay` | One explicitly referenced BDF operation; imported candidates are supported |
| `closed_loop` | Resolve one immutable saved candidate and execute target-based NMPC in MuJoCo |
| `control_revision` | Same candidate, preceding execution result reference, changed declared control weights |
| `stop` | Accepted native final disposition, based on imported evidence or all new results |

Any action may be first. No solve, replay, NMPC selection or task success is
mandatory. Each experiment supplies hypothesis, supporting references, parameters,
expected and weakening observations, fixed conditions and a stopping rule.
One expensive experiment is allowed per provider decision, and its evidence must
return before another is selected. Multiple evidence reads remain sequential.

| Resource | Ceiling |
|---|---:|
| New standalone offline NLP attempts | 2 |
| New BDF attempts | 3 |
| MuJoCo launches, including unsuccessful launches | 2 |
| NLP worker / existing IPOPT limits | 900 s / 570 s |
| BDF worker | 450 s |
| Simulation / evaluation / profile | 1,800 / 30 / 60 s |
| Scientific computation, focused numerical checks and recovery | 7,200 s |
| Actual provider sends, including auxiliary requests and retries | 16, last 4 protected |
| Public workflow calls | 64 |
| Overall activity / delivery reserve | 6 h / final 30 min |
| Additional research LLMs / real hardware | 0 / 0 |

The two NMPC speed weights are the only control adjustments: holding default
0.05, terminal default 0.10, both in [0.025, 0.10]. The rest of the NMPC recipe
is inherited unchanged, including solver policy, horizon, initialization,
integration and unusable-plan response. Offline IPOPT time/grid settings do not
become NMPC settings. Its rolling solves are charged through their launch,
reported separately from standalone NLP slots. Parent and child sessions share
one project ledger; outer orchestration does not charge simulation twice.

`tools/casadi_closed_loop.py` imports the two latest candidates with original
solve, checkpoint, replay, plan and correction identities. It reads the exact
candidate design and checkpoint-owned source configuration, validates the frozen
task and structure, and calls `resolved_input` to materialize the full SessionInput.
It checks named reduced coordinates, backend joints, tendon order, transmission,
units and candidate-specific model, workspace, projection and numerical identities.
The builder runs with `changes={}`. The prediction model and simulator share that
resolved robot. Controller 11.0.0, generated builder 3.0.0, MuJoCo backend 1.1.0
and serial bending model 1.0.0 remain bound.

The physical initial positions and velocities are named zeros. `initial_state_pretension`
creates 0.2 N numerical guesses, not an equilibrium or a changed physical initial
state. Saved offline tensions and states never become the NMPC reference or
simulator state. Each controller reads projected current MuJoCo state and computes
new bounded tensions. Existing preparation creates execution-local mutable workspaces.

Exploratory eligibility checks structure, provenance, configuration, mapping and
budget; historical failed open-loop acceptance or replay disagreement does not
block it. Those failures remain unchanged. A successful feedback execution would
validate the tested structure/controller combination only.

Completion uses shared-store child Host sessions, `complete_execution` and
`assemble_acceptance`, with existing completion, force, validity and task checks.
Acceptance uses the inclusive 0.01 s sample grid (six holding samples); historical
BDF metrics use 0.0005 s dense samples. Neither establishes continuous-time or
real-time deployment guarantees. Latencies and deadline misses are reported.
Saved-state reconstruction now retains world-frame tip velocity from MuJoCo's site
Jacobian and saved qvel. First-step comparisons retain timestamp and applied-input
checks and report velocity-vector disagreement separately from speed-magnitude
differences, matched counts and missing reasons. Holding samples are returned for
settling/oscillation inspection, without prescribing a cause.

Unknown reservations block new dispatch. Inspect existing receipts and partial
artifacts before recovery. `recover` continues an existing pending closed-loop
receipt chain without replacing its simulation; unresolved reservations stay
pending. Failed or incomplete results return partial evidence and missing facts,
including saved-state duration, attempted/applied updates and termination when
sealed exports are available. Partial inspection does not invent a completed profile
or launch automatic replacements. Engineering errors pause further sends.
For a scoped committed repair, `migrate --reason ...` preserves the grant, frozen
task, counters and clock. Compatibility is checked before every actual send.
The last four sends expose STOP-only plans and restrict native context retrieval
to feedback produced by this activity, including closed-loop feedback. No send
follows accepted STOP.

Focused checks are in `tests/test_casadi_nmpc_research.py`: saved/nonzero-length
wiring, a small same-state model check, first-action/revision/STOP fixtures and
saved-state velocity alignment. They construct XML for inspection, without
`mj_step` or real NMPC solves. Established mechanics, mesh, BDF precision and
speed studies are imported without repetition. The legacy focused checkpoint and
provider guard fixtures were updated to the supported action schema.

Export writes non-secret immutable artifacts, plans, actual requests/feedback,
receipts, configurations and counters to `evidence/casadi_nmpc_research_20261010`.
Commit the outcome and ordinarily push the feature branch, then verify its remote SHA.
