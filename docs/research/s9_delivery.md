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

S9.1–S9.3, runtime results, code inventory and final Git receipts will be added
after execution. No new feasible solution is claimed at this stage.
