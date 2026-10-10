# Bounded NMPC feasibility recovery

Activity `nmpc-feasibility-20261011` starts 2026-10-11 00:45:14 Asia/Shanghai,
including engineering. Origin was fetched once; the initialization source branch
still matched reviewed commit `b83b5b4fe03f97ccca3ad173187c0d80bb65ceba`.
Delivery worktree: `D:\softrobot-agent\.worktrees\nmpc-feasibility-recovery`.
The existing environment and lock are reused without upgrades: Python3.11.16,
CasADi3.7.2, SciPy1.17.1, MuJoCo3.13.0, Strands1.59.0, Harness0.2.0.

```powershell
$studyPython = 'D:\softrobot-agent\.mainline5-env\Scripts\python.exe'
& $studyPython -m tools.research_nmpc_feasibility prepare
# Commit implementation and frozen specification, then bind the committed tree.
& $studyPython -m tools.research_nmpc_feasibility bind
& $studyPython -m tools.research_nmpc_feasibility live
& $studyPython -m tools.research_nmpc_feasibility stop
& $studyPython -m tools.research_nmpc_feasibility export
```

Preparation imports verified immutable source archives and both paired numerical
results, ownership, snapshots, case/procedure context and factual corrections.
It computes the exact residual audit without optimization and does not repeat
the historical projection study, paired experiment or simulation. The model
chooses a rejected saved plan via its immutable snapshot reference and nested
plan label. Duplicate vectors and schedules are identified before integration.

Native actions inspect residuals, regenerate unchanged saved tensions, compare
a regenerated explicit warm seed with its corresponding cold seed, revise only
the recovery flag, read evidence, or STOP. The existing implicit root finder is
shared with live recovery. Each root return must satisfy its original equations;
failure preserves verified partial states rather than old inconsistent states.
Verification deserializes the original CasADi expression without constructing
or running IPOPT. Full vectors are sealed before concise feedback is packaged.

At most two distinct schedules180s each, two local NLP attempts300s combined,
one MuJoCo launch1800s/evaluation30s/profile60s, scientific3600s, provider16
with final4 protected, public64, total6h/final30min delivery. After the first
regeneration, at most one further scientific step is allowed. Preparation,
verification, failures and focused checks count. Live NMPC solves and recoveries
belong to the simulation allowance and are reported separately. Production
defaults remain unchanged. Recovery does not alter original IPOPT status or
iteration counts. Snapshots distinguish IPOPT-selected, regenerated and delivered
plans; simulator commands originate from measured simulator states each update.

For a scoped repair, commit then `migrate --reason ...`; preserve clock/counters
and inspect sealed numerical artifacts before resuming. Lifecycle `recover`
concerns existing reporting/receipts, not saved-tension regeneration. Never rerun
completed numerical work to repair reports. Accepted STOP forbids more sends.

This is a discretized-model consistency test, not independent validation.
Horizon end .30s differs from task acceptance at .35s. Physical generalized
force residuals do not bound trajectory error. The known same-state projection
disagreement remains. Case/procedure records stay reference-backed drafts; do
not repeat legacy admission or invent approval, validation or automatic reuse.
