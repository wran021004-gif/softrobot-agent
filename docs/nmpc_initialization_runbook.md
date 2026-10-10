# Initialization-dominated NMPC diagnosis

This fresh activity starts at 2026-10-10 22:05:08 Asia/Shanghai, including engineering.
Source `feat/casadi-nmpc-research` was fetched once and remained
`97aced4e75a6c3c6fecd851ae5bb0dc6be112f18`. Delivery uses
`D:\softrobot-agent\.worktrees\nmpc-initialization-diagnosis`, branch
`feat/nmpc-initialization-diagnosis`. Use Git `-c core.longpaths=true` on this
Windows worktree. The original checkout and sealed activities remain preserved.

```powershell
$studyPython = 'D:\softrobot-agent\.mainline5-env\Scripts\python.exe'
& $studyPython -m tools.research_nmpc_initialization prepare
# Commit implementation and frozen specification before bind.
& $studyPython -m tools.research_nmpc_initialization bind
& $studyPython -m tools.research_nmpc_initialization live
& $studyPython -m tools.research_nmpc_initialization stop
& $studyPython -m tools.research_nmpc_initialization export
```

The wrapper selects a new specification; it does not edit or reopen the old one.
Preparation is idempotent and preserves clock/counters. Provider transport,
credentials via `load_credential(Path.home()/'.codex'/'.env')`, Strands Harness,
native tools, sequential execution and `finally` transport close are reused.
Python 3.11.16, CasADi 3.7.2, SciPy 1.17.1, MuJoCo 3.13.0, Strands Agents 1.59.0
and `strands-harness` 0.2.0 match the existing lock; no upgrades are needed.

`prepare` imports original immutable blobs, ownership and export manifests through
`ControlEvidence`, `import_execution` and `BoundReader`. If the local source Store
is unavailable, the committed archive is verified and read instead. No simulation
is launched to reconstruct evidence. The packet includes all 35 updates, absolute
prediction-node times, actual input, horizon, holding activation, feasibility,
termination, selected iteration, matched prediction error and measured motion.
Unrecorded objectives, historical warm plans and optimizer traces remain missing.
The initial velocity is known from the named zero physical initializer; the
post-step trajectory starts at .01 s.

| Native action | Work |
|---|---|
| `inspect_execution` | Bound saved evidence, no new solve |
| `diagnose` | Read-only referenced synthesis |
| `saved_state_comparison` | Two new same-state/common-seed local solves, one factor |
| `control_revision` | One targeted MuJoCo execution against imported baseline |
| `stop` | Evidence-backed disposition, seals further sends |

The pair selects update 1..34, its recorded projected state, preceding applied
tensions, absolute time and effective horizon. Update zero is excluded explicitly.
Before model decisions, preparation supplies one factual same-time projection check
at update20, charged and counted as a representative state. The model selects
subsequent numerical work. Mutable workspaces are separate. States are regenerated from repeated preceding
input; this is a new common seed, not historical warm replay. Same-time reduced
kinematics and velocity are compared with the saved simulator state/Jacobian for
the selected state. At most two distinct states and two pairs/four attempts are
allowed; preparation, failures, verification and instrumentation count toward
each 300 s pair and the 3,600 s scientific ceiling.

Allowed one-factor changes are `feasible_return.budget_s` 15..30, one existing
tip-speed weight .025.. .10, or motivated prediction `substeps` 1..2. Raising
return time never raises IPOPT CPU30s, iteration120, minimum5s, relative
improvement .1, residual tolerance or any other setting. Both policy reason and
raw termination are retained. If an iteration/CPU/improvement/convergence
condition ends a solve first, report it and do not claim the longer return budget
is ineffective. Raw scalar objectives under different weight definitions are not
comparable; compare physical metrics and named residuals instead.

Numerical results are saved before downstream presentation. Bounded snapshots
contain initial/raw-returned/selected and relevant rejected iterates. Feasibility
checks stay intact. A reporting failure pauses expensive work; recover retained
artifacts rather than retrying the numerical solve. Commit a scoped repair, then
use `migrate --reason ...`; the existing clock and counters persist. The native saved-state operation must
receive the existing authorized300s pair allowance, independently of the unchanged
IPOPT CPU30s and feasible-return budget. For the sealed-after-return timeout defect,
`recover` validates and reuses the original two outputs, preserves the failed receipt,
and adds a recovery reference for model feedback. It never reruns either solve.
Commit/migrate first, then recover and resume the same activity. Native rejection
feedback lists exact required new-result references so STOP can cite all of them.

A revision must explain an observed mechanism, keep the original candidate and
change one factor. Select up to two previously diagnosed updates for detailed
snapshots. `RECORD_UPDATE_IDS` is set around the actual receipt-backed execution,
including controller configuration, and reset in `finally`. Other updates retain
ordinary summaries. No physical initial state is replaced by an optimized state.
The simulation allowance is 1,800 s plus evaluation30/profile60; one launch total,
including failed launches. Internal rolling NMPC solves are reported separately.

Actual provider sends are capped at16, with final4 protected for feedback/STOP;
public calls64, total activity6h/final30min delivery. Full-horizon codesign, BDF
campaigns, other models and hardware are excluded. Ceilings are not quotas.
STOP must cite all new results. Accepted local progress never establishes
closed-loop improvement; robot acceptance is unchanged and success is optional.

Export machine results, actual original plans/feedback, immutable archive and
manifest, non-secret configuration and snapshots. Add a factual case record and
recommendation-only diagnostic procedure. Legacy `ArtifactReference`/finalized-run
admission differs from platform `EvidenceRef`/SQLite provenance: document any
specific incompatibility and retain a draft rather than fabricating validation or
human approval. Commit and ordinarily push the delivery branch, then verify SHA.
