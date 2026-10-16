# M3-D offline integration readiness — 2026-10-16

Offline integration is ready for review. The proposed live pilot remains
**unlaunched and unauthorized**. No new task-feasible design, controller update,
Agent research performance, or efficiency advantage has been established.

Branch: `feat/m3d-agent-feedback`; starting SHA:
`eddbcb26a393c8919ac88886c0c1f7d280c374f9`. Work was confined to
`D:\softrobot-agent\.worktrees\m3d-agent-feedback`. No SoRoSim validation files,
sealed studies, historical source identities, search algorithm, task evaluator,
scientific acceptance rules, or first-success gate were changed.

## Actual M3-C3 source and final materialization

Read [M3-C3 delivery](m3c3_delivery.md), its actual search verification, and the
hash-verified original candidate/search/analysis bytes through the existing
`numerics.archived` reader. These are historical observations, not new solves:

| Fact | Exact identity/value |
|---|---|
| Search result | `5d59e00b1d8d5e15e0a9ccd390d0d5de2a5ce4ef86946143d007835e66791c31` |
| Best candidate artifact | `9cfc4af6424adce239b10ef62a07e4de75f414805d00e82980de7b50647dd96f` |
| Best analysis | `2d198c115f0bf5926eacdec6a4ce9189c70e967ebd9033638983400a3bdb472c` |
| Physical design | `e6baadb5c508345a5a0bbd6df4da9794290e976d4f56ec40ac2e4b540f3dd828` |
| Coarse numerical model | `ece9c9d96f8b2885b8bf620e28648e7c9c537972c6c77f5675ce774a80f55b95` |
| Final numerical model | `d09fdef3904fac6d25e16c80b6a626516b4dd351d303b1200e289a0c41ee10df` |
| Frozen final evaluation | `defa9f6c914af60644a246516ecf5efba75218cfd1c46a6c9b0796afb72486a2` |

The best observed static residual was `1.183484041825397e-9 m`. The design has
two segments of 0.20/0.11 m, Young moduli 10.45/5.4 MPa, a root ellipse with
semi-axes 0.01175/0.0076 m and angle 0.35 rad, and distal rectangular sections
0.0133/0.0095 m at their original station angles. Four tendons independently
span the full chain with radius 0.018 m, guide station 0.5, anchor station 1.0,
phases `[pi, 3*pi/2, 0, pi/2]`, and zero individual angular offsets. Force bounds
are 0–8 N per channel; both speed-cost weights are 0.1. Static equilibrium says
nothing about reaching and holding this target within the physical task horizon.

Final materialization copies the **saved candidate parameters**, including its
sections, routing, material and controller choices, and changes only each
segment's `cells` from 4 to the frozen final value 12. It uses the original
`research_plan.generate`, generator, registry and Store. Physical structure
equality and physical identity are preserved; numerical/full candidate identities
change. The new final model has 48 physical DOFs, 12 GVS coordinates, 24 states,
and four ordered inputs `tendon_0` through `tendon_3`. The zero initializer is
rebuilt for those 48 physical DOFs. Coarse mathematical evidence stays bound to
its original candidate.

Real candidate-owned NMPC plan resolution and the registered `prepare_execution`
hook passed, with the unchanged structural basis, pretension preparation,
10-step horizon and 120-iteration solver ceiling. One contained default-loader
XML preflight succeeded: exit 0, 0.530154 s, no stepping. Generation accounted
0.365838 s. These observations do not validate even one NMPC update.

Raw observations and source hashes are in
[prelaunch verification](../../evidence/m3d_agent_feedback/prelaunch_verification.json)
and its [immutable export](../../evidence/m3d_agent_feedback/prelaunch/immutable_artifacts.tar.gz).
The export is an offline test fixture, with the explicit
`offline_fixture_not_scientific_binding` sentinel. Its historical search was
inserted solely to exercise the decision packet; the export's generic search
claim reflects that historical entry, **not a newly performed search**. Source
archive identities and zero new mathematical counts are authoritative. The
temporary fixture was removed; no live pilot Store was prepared. The preflight
records its dirty implementation source hashes; later additive feedback reporting
changes are covered by final tests and do not alter the observed physical model.

## Connected workflow and causal evidence

The existing Agent's `decision_packet` now exposes an exact final-materialization
recipe in `search_feedback`, with source search/candidate references. It is a
recipe, not an automatic generation or evaluation. The Agent chooses its next
action. Native tool schemas already expose the mixed-search union, generation,
candidate-bound analysis, execution, evidence reads and exact-execution selection.
The proposed study explicitly includes `generate` in its advertised actions.

The focused integration fixture traverses the real plan/search/analysis/execution
dispatch and settlement functions. Only numerical worker outputs and native-load
availability are fabricated: search → final generation → final-candidate analysis
→ failed complete task → explicit evidence read → controller revision with cited
failure → fresh complete pass → explicit read → select. Coarse execution is
rejected before launch. Candidate-specific mathematical links do not transfer to
a controller revision. Worker fixtures are interface evidence, not experimental
results or independent physical evaluator observations.

Original plans retain hypotheses, expected/weakening observations, fixed
conditions, stopping conditions, interpretations and `supporting_evidence`.
Generated candidate provenance points to its plan; reused candidates retain a
separate provenance event. Search retains its existing incumbent/evidence lineage,
including optimizer-internal moves, raw analysis references, charges and recovery
attribution. A later research decision must cite what it actually used; temporal
adjacency alone does not establish a causal improvement. No new lineage authority,
Harness, Agent, Store, evaluator or optimizer was introduced.

Execution and decision feedback now exposes the original acceptance status,
validity/coverage/solver/force components, missing evidence and issues, last valid
time, solver termination counts, errors, unusable plans, maximum plan violation,
and worker termination evidence. Position and holding-speed failures include the
original threshold/unit/value, exact motion artifact/sample pointer and time.
Terminal position points to the actual terminal sample rather than a larger
earlier error. Missing evidence remains null. Reporting does not recompute task
acceptance or infer infeasibility from a solver failure.

The first fresh complete final-fidelity pass still persists the existing success
gate before any next action. Queued mathematics, generation, search and execution
are blocked; the Agent can read and select the exact result or stop. Mathematics
and design changes remain optional, including before success. Selection with zero
confirmations seals the study without another execution. Historical, cached,
invalid, incomplete, screening and proxy evidence cannot replace a fresh pass.

## Proposed study and scientific budget

Reviewable composition:
[study_m3d_agent_feedback.json](../../configs/research/study_m3d_agent_feedback.json).
Resolved identity in this worktree:
`e5ce188b5e0ac7d26494fd48e466ebdd6fc5a64db305ce883a69e8b105e16bcc`.
It begins from the unchanged frozen family space, with no reference candidate or
imported M3-C3 result. Historical M3-C3 results inform readiness only; the proposed
Agent must generate its own evidence. This is one exploratory pilot, not a
controlled comparison of Agent efficiency or a repeatability study.

| Resource | Proposed maximum / interpretation |
|---|---|
| Provider requests | 16 total; 3 reserved within that total for closeout |
| Public operations | 64 total; 6 reserved within that total; existing internal stage charges also apply |
| Mathematical attempts | 10 total, shared by search and direct candidate analysis |
| Each mixed search | At most 16 proposals / 8 mathematical attempts, within the shared total |
| Search topology grant | 1/2 segments, 3/4 tendons; existing physical coordinate groups; no control-weight proxy search |
| Physical/NMPC executions | 2 total, potentially fewer due to first success, STOP, failure or budget exhaustion |
| Native XML probes | 2 at most, separate from physical rollout counts; 30 s engineering loading bound per probe |
| RL/training/local diagnostics/offline NLP/replay | 0 |
| Additional confirmations | 0; repeatability unassessed |

The full frozen declarative/executable family is retained. The narrower topology
grant limits mixed search; it does not silently redefine the family's generation
domain. Every generated candidate still needs its own numerical/runtime evidence.
Structure and controller changes share the same frozen joint task: target
`[0.29, 0.035, 0.19] m` in world coordinates, gravity `[0,0,-9.81] m/s²`, seed 17,
0.35 s duration, 0.01 s control/sample period, 0.0005 s physics step, terminal
position ≤0.01 m, and inclusive final 0.30–0.35 s holding position ≤0.01 m and
speed ≤0.02 m/s. Independent evaluator success, complete/valid coverage, no solver
errors and force-bound compliance remain required. Controller weights are chosen
through generation within existing domains; mathematical proxies do not score them.

Two full executions would nominally total 70 control updates and 1,400 physics
steps; early termination reduces completed work. At most 120 principal NLP
iterations per update gives 8,400 principal iterations across that nominal
schedule; internal roots, warm preparation, recovery and validation are additional
work, not bounded by that multiplication. Up to ten mathematical attempts share
the existing analysis counter; their actual GVS construction and internal solver
work retain the inherited settings and raw cost records.

M3-C3's eight real searches took 75.72 charged numerical seconds. That is context,
not a forecast for new operations. M3-C2's different two-segment/three-tendon
single-update case took 112.395 s; multiplying by 70 suggests roughly 2.2 hours
as a planning scale only, not a prediction or validated upper bound. The exact
four-tendon candidate's first update has never been timed. Scientific wall/CPU
timeouts remain explicitly disabled in the inherited count protocol; there is no
promised runtime ceiling. Provider generation is capped at 32,768 tokens/request
(524,288 maximum output tokens across 16 requests); input context and billed
reasoning costs are variable. No monetary quote or provider pricing validation
was performed.

## Remaining launch conditions

Separate explicit user authorization must identify the reviewed configuration,
implementation commit and counts above before any live provider or full NMPC
execution. After authorization, prepare a new pilot session, commit/bind its exact
source through the existing CLI, retain the resolved configuration and run with
the frozen interpreter/thread environment. Do not reset, migrate or reuse a
sealed study. The proposed configuration's authorization text records this pending
status; it is not an authorization credential or a new enforcement mechanism.

Exact candidate XML loading and NMPC preparation are verified; an NMPC update,
nonlinear full-horizon behavior, final task success, robustness and repeatability
remain unverified. Other Agent-selected candidates need exact runtime admission
and candidate-bound analysis/control evidence. Larger segment models retain the
M3-C3 runtime and numerical coverage limits. No alternative stack loader was
enabled. The live provider/Harness transport was not contacted or credential-tested.

## Changes and targeted checks

Production changes are confined to `tools/research/design.py` (pure final-mesh
request copy), `feedback.py` (evidence views and recipe), `core.py` (packet wiring),
and `execution.py` (shared compact numerical feedback). No numerical kernel or
acceptance code changed. Added the proposed configuration,
`tests/research/test_agent_feedback.py`, this report, and the prelaunch export and
verification record under `evidence/m3d_agent_feedback/`.

33 distinct focused tests passed: five M3-D integration/validity cases, 12 mixed
search cases, 12 mainline cases, three count/success cases, and one historical
analysis/acceptance case. Coverage includes exact archived physical regeneration,
registered preparation, full dispatcher feedback adaptation, raw metric pointers,
missing/invalid/incomplete/worker evidence, immutable historical identities,
fidelity gates, recovery attribution, first-pass closure and selection without
extra execution. One development fixture initially omitted receipt `charged`
fields; correcting that fixture made the end-to-end dispatcher test pass. This
was not a production execution failure.

Run from this worktree in PowerShell, using the installed interpreter:

```powershell
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
$env:PYTHONPATH='tests/research'
& D:/softrobot-agent/.mainline5-env/Scripts/python.exe -m unittest `
  test_agent_feedback test_mixed_search test_mainline `
  test_count_continuation.CountContinuationTests.test_fresh_pass_blocks_queued_science_and_search `
  test_count_continuation.CountContinuationTests.test_search_stops_before_second_candidate_on_backend_pass `
  test_count_continuation.CountContinuationTests.test_proxy_historical_incomplete_and_reward_never_trigger_gate `
  test_task_analysis_contract.TaskAnalysisTests.test_old_contracts_and_acceptance_unchanged -v
```

Without `M3D_PREFLIGHT_EVIDENCE`, the M3-D suite performs no native child launch,
physics step, controller solve or provider request. The separately recorded opt-in
real preflight performed exactly one native XML load, zero mathematical solves,
zero controller updates, zero complete task evaluations and zero RL stages.
Archives/member hashes and whitespace are checked before delivery. All scientific
identities remain attached to their original records; fixture outcomes are labeled.
