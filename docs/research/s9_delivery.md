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

S9.2–S9.3 remain pending. No new feasible solution is claimed.
