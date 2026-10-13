# Standalone RL interface

`run.py` exposes `start`, `status`, `stop`, `resume`, `diagnose`, and `evaluate` as ordinary Python functions and one CLI. `env.py` owns the saved robot/task, observations, tension mapping, physics and failure capture. `train.py` owns SB3 PPO, accounting and checkpoint generations. `checks.py` owns frozen-task acceptance and bounded replay. Imports never start a run.

## PowerShell commands

Use the existing interpreter; no installation or credentials are needed. The worktree was moved into the shared workspace during this migration.

```powershell
Set-Location D:\softrobot-agent\.worktrees\rl-control-pilot
$py = 'D:\softrobot-agent\.rl-pilot-env\Scripts\python.exe'

# Allocate one immutable run. Default config: seed 17, 2048 actions, 120 active seconds.
& $py -m tools.rl.run start --run-id my-direct --config tools/rl/config.json
& $py -m tools.rl.run status --run-id my-direct
& $py -m tools.rl.run stop --run-id my-direct
# Wait for the previous worker to exit before resuming the SAME run.
& $py -m tools.rl.run resume --run-id my-direct

# One frozen policy episode, in a new output directory.
& $py -m tools.rl.run evaluate --policy evidence/rl_pilot_20261013/round2_direct/policy.zip --output runs/rl/my-direct/evaluation
# Default diagnosis reads evidence and performs zero physical steps.
& $py -m tools.rl.run diagnose --capture evidence/rl_pilot_20261013/direct_capture.npz
# Explicit replay executes exactly one recorded pre-failure physical step.
& $py -m tools.rl.run diagnose --capture evidence/rl_pilot_20261013/direct_capture.npz --replay --output runs/rl/my-direct/replay

# Cheap focused boundary checks; no training campaigns.
& $py -m unittest discover -s tests -p test_rl_runtime.py -v
```

Worker processes use this selected Python, CPU, one Torch thread, and `OPENBLAS_NUM_THREADS=OMP_NUM_THREADS=MKL_NUM_THREADS=1`. Only necessary OS environment paths are read. No API configuration, external model requests, Strands tools or agent runtime are used. Python callers can pass a configuration dictionary to `start(config, run_id)` and receive structured summaries and artifact paths. Rejections raise explicit exceptions; status never restarts workers.

Replay loads numerical settings from the capture's own run config or the archived diagnosis. A relocated capture without recorded settings requires an explicit `--config`; unknown numerical settings are rejected rather than silently replaced.

## Configuration and supported physical contract

`config.json` separates task/acceptance, reward, observation, action, physics, PPO and budget. A resolved copy is saved in `runs/rl/<run_id>/config.json`; its digest binds each checkpoint. The frozen initializer is included by joint name, retaining execution/XML provenance. Runtime task initialization does not read historical execution JSON. The loader reads only the specified saved XML artifact, using the existing read-only SQLite/archive fallback.

The compatibility contract is target `[0.29,0.035,0.19]` m, saved segment lengths/initializer, 48 qpos + 48 qvel and the existing 109-dimensional observation order. Six tendons are ordered `near_t0, near_t1, near_t2, far_t0, far_t1, far_t2`. Direct maps `4*(action+1)` N; residual maps `clip(reference[k]+8*action,0,8)` N. Positive commands go to direct-tension actuators; positive measured pull is `-actuator_force`. Physics remains implicitfast at 0.0005 s, with 20 substeps per 0.01 s action and 35 actions per episode. Observation scaling and reward never supply acceptance thresholds. Frozen acceptance uses position <=0.01 m and holding speed <=0.02 m/s at indices 30..35 inclusive.

Direct does not read a reference. Residual requires `reference` with `path`, `source_physical_execution`, `tendon_order`, `control_period_s`, and a descriptive validation status. Resolve freezes its SHA-256; the worker checks digest, metadata, finite values, [0,8] N bounds and shape (35,6). The existing source is `evidence/fc1012_open_loop_20261013/references.npz`, execution `6380ef76518b4c24a6bf459942f72545`, six-tendon order above, period 0.01 s. That reference **failed MuJoCo task acceptance** and is not a successful demonstration.

PPO schedules can be constants or `{ "kind": "linear", "initial": ..., "final": ... }` for learning rate, clip range and optional value-function clip range. Default PPO remains rollout 256, minibatch 64, 10 epochs, actor/critic [64,64], initial log_std -3, with no policy selection.

Only no-reference direct control and a complete compatible residual tension reference are supported. Stage goals, state/path tracking, behavioral cloning, demonstration initialization and online NMPC residual control are unsupported. Unsupported controller modes/orderings are rejected; no extension framework is provided.

## Recovery, schedules and accounting

Statuses distinguish starting/running, stopped, completed, interrupted and failed. `stop` creates a token-bound request and returns `stopping`; a worker exits cooperatively. A run cannot start twice. Resume requires the previous worker to have exited; PID plus Windows process creation time and launch token prevent confusing a reused PID with the expected worker. Lifecycle operations use an exclusive file lock. A retained lifecycle lock blocks the operation with an explicit reason and requires inspection; it is never ignored to permit a second worker.

The original action horizon is immutable across all workers. Installed SB3 2.9.0 adds `num_timesteps` to `total_timesteps` when `reset_num_timesteps=False`, so the runtime calls `learn(original_horizon - loaded_num_timesteps, reset_num_timesteps=False)`. It never resets counters or schedule progress, and never passes the entire remaining allowance as a second absolute horizon. Restore checks compare policy parameters, Adam state, learned counters, original schedule horizon, progress and evaluated learning-rate/clipping values, again after SB3 setup and before sampling. Resume starts a fresh physical episode; physical rollouts and random streams are not promised to continue bitwise.

Costs are separate from checkpoint-inherited learning and current-worker work. All attempted actions, including numerical failures, consume the shared action allowance. Physical substeps count actual attempts rather than successful actions times 20. A pre-action guard prevents an extra action. A full aligned final rollout is optimized; a partial rollout is charged but never described as learned experience. Completed rollout optimizations, PPO epochs and Adam steps are recorded separately.

Each rollout reserves at most its remaining action allowance **before** sampling. The worker also reserves its remaining active-time allowance. After an unexpected exit, status charges any outstanding reservation conservatively, retains the durable known lower bound and `consumption_uncertain`, and reports interrupted. The conservative time charge can exhaust the cap and explicitly block resume even when a valid checkpoint exists. Unknown work never becomes free budget. Repair/retry work must stay in this same run; an exhausted run cannot be resumed. Expected successful counts cannot override limits; a short verification is reported incomplete.

Active time runs from worker entry before heavy Torch/SB3/MuJoCo imports through setup, sampling, optimization, boundary waits, checkpoint writes and cleanup, ending at the timestamp immediately before final state publication. Launcher/interpreter prelude, final ledger write/interpreter teardown, paused intervals, evaluation and replay are excluded. Guards check before actions and before optimization. In-flight optimization/checkpoint work can produce a cooperative overrun, which is recorded honestly rather than refunded.

Policy ZIP, inherited-state metadata and consumed counters are written to a new checkpoint generation only after successful PPO optimization. `checkpoint.json` atomically publishes current/previous valid generations. Metadata includes file/config digests and schedule state. If current is damaged, recovery validates the previous generation; failed publication leaves the prior pointer usable. Runtime files also retain worker identities, final worker summaries, stop reason, failures, restore checks and evaluation/replay paths. Status reports the latest recoverable generation and remaining allowance, without policy selection or automatic restart.

`stop_at_boundary` is an optional interior rollout boundary. A first worker waits there for the real public `stop` request; wait time is active time. It provides deterministic stop testing and is skipped when resuming a checkpoint.

## Evidence and limits

The sole [verification campaign](../../evidence/rl_runtime_20261013/verification.json) used one run with two workers: 1024 actions/4 optimizations/40 epochs, then 2048 cumulative actions/8 optimizations/80 epochs. Its total active time was 8.444 s. Actual attempted physical steps were 40441, with 51 explicit numerical failures; these actions were charged and used only as marked surrogate training terminals. Policy parameters changed in both workers. At restore, the horizon stayed 2048 and progress stayed 0.5; final progress was 0.0. A further resume was rejected without sampling. The allocation manifest prevents another campaign from being used to repair this demonstration.

The [existing-policy episode](../../evidence/rl_runtime_20261013/existing-policy/result.json) passed with 35 actions, 700 physical steps, 36 rows and six holding samples: terminal error 2.847921 mm, holding max speed 0.004975700 m/s. The [one-step replay](../../evidence/rl_runtime_20261013/existing-failure/result.json) reproduced BADQACC and engine reset from 0.3060 s to 0.0005 s. Historical direct nominal success and residual holding-speed failure (~0.031746 m/s) remain unchanged. The interrupted first residual formal run lost network state; its later policy inherited an earlier short checkpoint, not the lost formal training.

Numerical-failure capture precedes the failing substep and preserves the attempted action and full integration state. Training's explicit terminal surrogate and penalty are not physical transitions. Evaluation exports only the valid prefix and never fabricates a complete successful episode after reset. Numerical root cause remains unresolved. Short training is not required to solve the task, and nominal success establishes neither robustness nor generalization.

Three lessons are stored in the existing [curated diagnostic index](../../memory/diagnostic_index.json), with source links and tested scope:

- [Capture pre-failure state](../../memory/diagnostics/rl-pre-failure-state_v1.json) before attributing instability to PPO or rewards.
- [Exclude surrogate terminals](../../memory/diagnostics/rl-surrogate-boundary_v1.json) from physical evaluation and demonstrations.
- [Separate spent compute from inherited learning](../../memory/diagnostics/rl-spent-vs-inherited_v1.json).

The RL interface does not retrieve lessons automatically. Reproducible commands, persistent artifacts, executable checks and evidence-backed experience borrow the milestone's HARBOR ideas; these are project-specific interfaces, not HARBOR APIs. No multi-agent hierarchy, parallel tuning, Strands integration or live model invocation was added.
