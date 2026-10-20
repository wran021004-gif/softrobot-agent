# S9 delivery — work in progress

Target: `feat/sorosim-matlab-nmpc`, S8 baseline
`fe0274a6d8a7948a3a4ae214b06f1b14972a0941`. Initial worktree clean;
fetch verified identical origin HEAD. Only this worktree is modified.

## S9.0

Extended existing `compact_evidence`, `context`, `read_evidence` and native
tool feedback. Display prefixes are explicitly distinguished from Store
pointers; search field queries contain only existing keys. Negative/outside
list indices, malformed pointers, wrong fields/range target and range start
are rejected. Physical summaries expose the original constraints and shared
`task_gap`. Current tool feedback includes bounded decision facts before the
large preview. Candidate/source action prerequisites use the original binding,
protected state and shared backend capacity; full Plan admission stays mandatory.
The complete STOP index now includes mechanics and matched-state outputs as well
as physical, RL and analysis results. This index does not mark anything as read.

Tests reuse immutable S8 evidence (best gap 0.11786172695770314) and verify
unchanged content identity. Offline checks do not establish real Provider
efficiency. Initial test invocation exposed a pre-existing test import path
requirement; subsequent commands set `PYTHONPATH=.;tests/research`.

S9.0: 70 tests passed with calibrated single-thread environment. Commit
`728a5a754694f238bdf97c405ba1cbf39b3d8e02` pushed and remote SHA verified.

## S9.1

`verified_input_response` in the existing physical replay module is the shared,
side-effect-free source of mathematical seed admission. It checks current
registration, numerical verification, candidate, effective configuration, task,
model, operating point, protocol and channel/coordinate binding. Guided seed
checks now precede baseline persistence. The existing optimizer is unchanged.
Analysis replies include scoped handoff requirements and exact response references;
context uses the same checker to report admission or missing prerequisites.

27 focused tests pass, including archived real S8 sensitivity and negative identity
cases. MATLAB readiness reproduced sandbox `CreateFile` access denial, preserving
the original error and cost. A separate, explicitly identified normal-permission
diagnostic completed dependencies, engine, gateway, sqrt(4), shutdown (`ready`).
See `evidence/s9_readiness/{initial,verified}`. Both consumed zero Provider and
zero scientific starts. No new MATLAB runtime or encoding workaround was added.

Frozen S9.1 source `1da7bec9c7906cd9e7ded7a463cd9a5e2bd2b824` was pushed and
remote verified. Real engineering completed 2 analyses, 1 physics start, 3 public
operations, zero Provider requests. `evidence/s9_engineering/handoff.json` links
target equilibrium, verified sensitivity, candidate-bound 35×4 seed and independent
MuJoCo result; full Store archive and independent recomputation are included.
All original bounds/grid/identity checks passed. Re-reading the completed physics
operation preserved result reference and ledger. Dynamic task failed: terminal
error 0.1705341285 m, holding position 0.1954246923 m, holding speed 0.7460602523 m/s,
gap 36.3030126126. This proves executable handoff, not improved dynamic control or
autonomous Agent choice. The current seed uses the selected fixed-input local
static response; the equilibrium result is separate mathematical evidence.

## S9.2 and formal freeze protocol

The existing response search now checks actual clipped input changes before
calling the public evaluator. It tries the opposite bounded direction/step when
necessary, excludes zero-change directions, identifies projected perturbations,
and records input-direction rank, observed-response rank/singular values and
resolved-subspace conditioning. Zero observed response terminates that start with
an explicit diagnostic. The existing constrained solver, trust radius, ranking,
Store cache and common multistart budget remain the sole implementation.
Cost feedback distinguishes callbacks, new physics, valid cached results,
duplicate sequences, ineffective attempts, unique local response probes, costs
and per-start initial/best results. Context presents newest summaries first.

Final focused regression: **146 tests, 145 pass, 1 skip** (opt-in real RL). Command:
`python -m unittest tests.research.test_{s9_evidence,s9_handoff,s9_probes,
s8_agent_interface,s8_control_seed,s8_sparse_search,s8_tool_readiness,
local_control_search,control_correction,evidence_policy,s7_context,s7_task_intake,
mainline,count_continuation,agent_feedback,sorosim_analysis,sorosim_contract,
rl_integration}` (expand braces into separate module arguments). Environment:
`PYTHONPATH=.;tests/research;C:/Program Files/MATLAB/R2024a/extern/engines/python/build/lib`,
the existing pinned `SOROSIM_ROOT`, and OMP/OPENBLAS/MKL threads each 1.
Logs preserve an initial missing-engine-import-path run and the subsequently fixed
`acceptance=null` regression. Tests launched no real Provider or scientific workers.
Saved S8 invalid-pointer requests were replayed against hash-verified artifacts.

Production delta is **+177/-26, net 151 lines**, six existing modules, zero new
production modules. This is below the suggested range because existing admission,
binding, evidence, task-gap and Store cache functions were reused. No production
changes to contracts, evaluator, scientific kernels or numerical acceptance.
The inventory lists function owners; new files are focused tests, a separate
engineering test driver, one read-only accounting supplement (reusing S8 archive,
search reconstruction and independent audit), study configurations and evidence.

Formal S9 uses `s9-variant-live-20261020` and `study_s9_variant.json`: 24 Provider
requests (4 protected), 150 public operations (12 protected), 64 backend starts,
4 analyses, 1 NLP, 2 BDF replays, 2 NMPC executions, 1 PPO stage/65,536 actions/
1 evaluation. No scientific time limits are added. The original second target
and task identity `596fd628…` match S8 exactly: 0.35 s horizon, 0.01 s controls,
0.0005 s physics, 0.30–0.35 s hold, 0.01 m position, 0.02 m/s speed, original input
bounds and evaluator. Historical S8 best is imported with its historical ownership;
S6 control remains an optional unmeasured seed. Engineering data is not imported.
This is a new Study of a previously studied target, not an unseen task.

The configuration and source are committed before prepare/bind/run. Readiness is
ready, key-file presence is checked without recording its content, and the current
archive/Store restoration path is unchanged. During formal execution no source,
budget, threshold or task modification is permitted. The Agent chooses its own
actions through the existing `python -m tools.research run`; no engineering driver
is used for formal science. Formal results and final Git receipts remain pending.
