# Fixed structure milestone fc1012

Run from the mechanics-control-mainline worktree with
`D:\softrobot-agent\.mainline5-env\Scripts\python.exe` as `python`.
The single ledger is `runs/fc1012`; nr1012 stays sealed. No provider request,
dependency reinstall, length design, or open-loop success claim is authorized.
The specification starts from the selected immutable nr1012 candidate and its
complete recipe, rather than the initial historical specification.

Set the same numerical runtime environment before launching the interpreter:

```powershell
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
```

Standalone/integration workers already fix these values. Full execution now
requires them at startup and records them in its profile/results. An early full
start that inherited unset values was confirmed stopped, retained as incomplete,
and charged; its partial plans cannot establish task acceptance. Do not recreate
it to demonstrate its failure. Calibration and complete execution must share the
runtime as well as iteration/horizon/mesh settings.

The unset-variable start establishes a calibration/runtime mismatch, not its
performance cause. A metadata-only process under the frozen startup variables
reads NumPy, SciPy and CasADi OpenBLAS thread counters (all1 in this study). Live
process DLL paths and OS thread count are separately recorded. This probe does
not benchmark, solve, integrate or inject code into the live numerical process.

Budgets: 2 offline optimizations, 6 standalone solves / 2400 seconds, 8 independent
integration configurations, 4 complete execution starts, 28800 charged numerical
seconds, and 12 activity hours including delivery. Failed starts and interruptions
count. Internal NMPC updates belong to their full execution. Protect 1800 activity
seconds for delivery. Preliminary 8500-second simulation reservations conservatively
scale prior measured work for the possible 3-to-6 iteration change; full dispatch
requires a fresh same-configuration calibration and a newly recorded estimate.

```powershell
python -m tools.fixed_task_milestone prepare
# Commit scoped implementation before the initial binding.
python -m tools.research_core bind --spec examples/fixed_task_milestone/specification.json
python -m tools.fixed_task_milestone import
python -m tools.fixed_task_milestone local --update 29 --iterations 3 --key hold29-work3
python -m tools.fixed_task_milestone local --update 29 --iterations 6 --key hold29-work6
```

These arms restore the exact measured state, previous input, initialized vector,
serialized objective and constraints from selected execution
`1335ee31ad4f46e8b258de6523d07e68`. They retain plan selection and returned-tension
recovery. Compare raw, selected, recovered and delivered plans, numerical residuals,
absolute holding times, position and speed violations, first action and cost.
Iteration-limited feasibility does not demonstrate convergence or task success.

The commands below document completed offline development. The accepted new
candidate is now frozen with its three-gate evidence. Do not launch another
offline optimization, fixed-schedule rollout or mesh comparison in fc1012.

Offline internal resolution is declared separately in `offline_recipe`. Preserve
the physical zero state and the 35 zero-order-held commands. Diagnose the saved
exact-node BDF disagreement across the entire trajectory, then test one supported
refinement with the same tensions before reoptimization. NMPC stays at its separately
validated resolution unless its own evidence supports a change.

```powershell
python -m tools.fixed_task_milestone rollout --substeps 32 --key saved-midpoint32
python -m tools.fixed_task_milestone verify --rollout-source FIXED32_ROLLOUT_ARTIFACT --key saved-midpoint32-bdf
# The fixed schedule32 comparison still failed at .2903125s. Selected local grid:
# intervals29-30 use64 internal substeps, all other physical intervals use16.
python -m tools.fixed_task_milestone rollout --offline-grid --key saved-local64-corrected
python -m tools.fixed_task_milestone verify --rollout-source LOCAL64_ROLLOUT_ARTIFACT --key saved-local64-bdf
python -m tools.fixed_task_milestone solve --key fixed-local64
# SOURCE is the returned result artifact ID, not the execution ID.
python -m tools.fixed_task_milestone verify --source SOURCE --key bdf-fixed-local64
```

After an evidence-supported controller selection, record it with `select_recipe`,
commit and `research_core migrate --spec ... --reason ...`, retaining all counters
and the original activity clock. A local current-path check regenerates states from
the saved measured state and control-schedule guess. Any changed work limit, horizon
or mesh invalidates the execution estimate. Estimate with that check's comparison
artifact. The estimate uses its measured work and all 35 historical update costs,
includes construction/reporting and a 35% margin, and binds recipe and implementation.

The later horizon-stratified estimator replaces whole-run scaling for any next
start. It uses existing matched checks and saved full-execution update timings:
26 updates at maximum horizon10 and nine deadline-shortened updates at horizons9
through1. Each stratum takes its measured upper cost ratio without crediting a
speedup; cold first-update cost is a separate floor. The setup/evidence allowance
and35% watchdog margin are retained. The mistakenly extended horizon10 check at
.29s is diagnostic only and excluded. No additional performance sweep is needed.

```powershell
python -m tools.fixed_task_runtime metadata
# While pending: save a prospective estimate; leave active reservation unchanged.
python -m tools.fixed_task_runtime estimate
# After the original process exits and its ledger settles, before any next start:
python -m tools.fixed_task_runtime estimate --apply
python -m tools.fixed_task_milestone status
```

`--apply` rejects pending executions because their reserved allowance must settle
using the value present at dispatch. The active watchdog also remains the one
declared at dispatch. Check the original tool handle, exact process identity and
saved files before recovery or another launch. A paused goal does not prove a
stopped numerical process. An incomplete prefix cannot become an independent
confirmation; that requires a fresh process and original physical zero state.
The .0307537565m/s local delivered prediction is retained as a diagnostic, not an
additional prohibition on complete validation. Final acceptance uses actual
inclusive .30–.35s measurements.

```powershell
python -m tools.fixed_task_milestone local --update 29 --iterations SELECTED --current --key selected-calibration
python -m tools.fixed_task_milestone estimate --source CALIBRATION_ARTIFACT
python -m tools.fixed_task_milestone status
python -m tools.fixed_task_milestone execute --key development
# Only a passing original-task source can use this fresh confirmation command.
python -m tools.fixed_task_milestone repeat --source PASSING_ARTIFACT --key confirmation
```

Before development, admission must fit that execution, one fresh same-configuration
confirmation, outstanding independent integration and delivery in both numerical
and activity budgets. Re-estimate again after a configuration change. Do not repeat
a failed complete run. A second development revision needs a concrete correctable
failure and enough remaining resources for its own confirmation.

The migration entry applies explicit specification changes while forbidding changes
to study/source identities, original clocks, authorized ceilings or delivery cutoff.
An interrupted accidental old-grid diagnostic remains charged as an unsuccessful
attempt. Its key is not local-refinement evidence. The corrected local-grid request
declares all35 internal interval counts and preserves every physical boundary.

Inspect `status` and `last_operation.json` before dispatch. Recover pending outcomes
with `recover`; never rerun an expensive command to redisplay its result. External
watchdog interruption is incomplete. Original sampled acceptance, all-node vector
consistency, dense diagnostics and MuJoCo feedback acceptance remain separate.
Curated experience reads identify exact entries, revisions and content hashes;
dispositions require actual read receipts. Engineering retrieval checks use zero
provider calls and do not establish LLM reuse or cost savings.

Seal with an engineering STOP citing every new experiment, export with the existing
archive mechanism, verify member and archive hashes, and split if oversized. Commit
only scoped code, documentation and non-secret evidence. Push ordinary HTTPS and
verify the published branch SHA over HTTPS before claiming delivery complete.
