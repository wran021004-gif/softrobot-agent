# Route A learning-control pilot

`env.py` implements one Gymnasium environment for the frozen fc1012 robot/task.
`train.py` trains one CPU Stable-Baselines3 PPO MlpPolicy in either route.
`evaluate.py` loads its saved settings and performs deterministic inference with no
parameter updates. These four files are the entire pilot; shared mechanics and
controllers are unchanged. Base commit: `62989e2c1380496fc2953ad9ef4a9a15da99d6ca`.

## Fixed task and reference status

Segment lengths are `[0.15758113296570092, 0.11241886703429908]` m; the world target
is `[0.29, 0.035, 0.19]` m. Reset applies the saved zero joint positions/velocities
by joint name, without settling or perturbations. The original XML preserves
scene, gravity, mounting and physics settings. Each action advances exactly
20 physics steps of 0.0005 s. An episode has 35 actions (0.35 s), with
`terminated=True, truncated=False` after action 35, regardless of reaching the target earlier.

The [offline candidate](../../docs/fixed_task_completion.md) passed numerical
feasibility, independent BDF task acceptance and all-node consistency. Maximum
node velocity-vector disagreement was about 0.00182501 m/s (<0.002 m/s); BDF
holding speed was about 0.0178399 m/s. The [saved-tension MuJoCo replay](../../docs/fc1012_open_loop_replay.md)
failed: holding position error about 14.1865 mm and speed about 0.1513304 m/s.
Commanded/applied tension disagreement was 0 N. Thus the reference is a potentially
useful prior, not a demonstrated successful MuJoCo controller. That cheap replay
does not establish PPO training cost or convergence.

## Dependencies and saved inputs

The isolated worktree is `D:\softrobot-agent.worktrees\rl-control-pilot`; the separate
environment is `D:\softrobot-agent\.rl-pilot-env`. Mainline's environment is unchanged.
Actual installed versions: Python 3.11.16, NumPy 2.4.6, MuJoCo 3.13.0,
Gymnasium 1.4.0, Stable-Baselines3 2.9.0, PyTorch 2.14.1+cpu.
Installation used these commands (plus transitive dependencies only):

```powershell
& D:\softrobot-agent\.mainline5-env\Scripts\python.exe -m venv D:\softrobot-agent\.rl-pilot-env
# Initial ensurepip hit a temporary-directory permission error; this recovered it:
New-Item -ItemType Directory -Force D:\softrobot-agent\runs\rl_pilot\install_tmp | Out-Null
$env:TEMP = 'D:\softrobot-agent\runs\rl_pilot\install_tmp'
$env:TMP = $env:TEMP
& D:\softrobot-agent\.rl-pilot-env\Scripts\python.exe -m ensurepip --upgrade --default-pip
& D:\softrobot-agent\.rl-pilot-env\Scripts\python.exe -m pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
& D:\softrobot-agent\.rl-pilot-env\Scripts\python.exe -m pip install --no-cache-dir 'numpy==2.4.6' 'mujoco==3.13.0' gymnasium stable-baselines3
```

For reproducing these versions later, pin `torch==2.14.1+cpu` in the CPU-index
command and `gymnasium==1.4.0 stable-baselines3==2.9.0` in the final command.
No CUDA, LLM requests, API credentials, research Host or scheduler is involved.

Each environment construction reads the committed
`evidence/fc1012_open_loop_20261013/execution.json` and only
`saved_tensions_n` (35 by 6) from the adjacent `references.npz`.
It never uses previous NMPC commands, GVS states or future reference observations.
`--source-root` defaults to `D:\softrobot-agent\.worktrees\mechanics-control-mainline`.
It locates the original XML for execution `6380ef76518b4c24a6bf459942f72545`:
artifact `60c5e069f76253e05d9b0aa2cd873abda87abecb84b6d0814c30f4e0052a88de`.

The loader queries `runs/fc1012/platform.sqlite` read-only (`artifacts.id/body`);
if absent, it reads the single matching `artifacts/<id>.bin` member from
`runs/fc1012/delivery_archive_reassembled.tar.gz`, then
`evidence/fixed_task_20261012/immutable_artifacts.tar.gz`.
Inputs load once per environment, not per reset. Missing inputs report exact paths;
there is no robot substitution, rebuild, replay entry-point call or hash audit.

## Observations, actions, reward and acceptance

Both modes have the same 109-element float32 observation, in this order:
48 actual XML-order joint positions (rad), 48 actual joint velocities (rad/s),
world target-minus-tip position divided by 0.01 m, world tip velocity divided by
0.02 m/s, previous applied six-tendon tension divided by 8 N, and control index/35.
Joint values are unscaled. There is no learned normalization, observation clipping,
GVS projection or offline reference in the policy observation.
Tip position uses `tip_site`; world translational velocity uses
`mj_jacSite @ qvel` after synchronized post-step kinematics, never finite differences.

Actions are six normalized values in [-1,1], ordered
`near_t0, near_t1, near_t2, far_t0, far_t1, far_t2`:

- Direct: `u = 4 * (a + 1)`.
- Residual: `u = clip(reference[k] + 8 * a, 0, 8)` N, k=0..34.

The explicit residual scale is 8 N. Positive commands go directly into the saved
`*_direct_tension` actuators; their existing gain/gear convention pulls.
Applied positive tension is `-actuator_force`. The environment records each
tension-clipping flag and each 0/8 N saturation flag. SB3 also clips its Gaussian
policy actions to the action box before the environment receives them; those
pre-environment clips are not counted as residual-tension clipping.
The parameterizations differ in slope, offset and saturation, so this compares
complete practical control routes, not a clean single-factor proof of the
reference's contribution.

At each post-action sample, with error norm e, speed v, current applied tension u
and previous applied tension u_prev (zero initially), reward is:

```text
r = -(e / 0.01)^2
    - 1[k in {30,31,32,33,34,35}] * (v / 0.02)^2
    - 0.001 * mean(((u - u_prev) / 8)^2)
```

No speed penalty applies during the movement samples before index 30, and there is
no reference-tracking reward. Independent acceptance requires terminal error
<=0.01 m, maximum holding error <=0.01 m, and maximum holding speed <=0.02 m/s,
with all six integer-index samples 30..35 (0.30..0.35 s) present. Reward never
substitutes for these checks. MuJoCo numerical failures raise an error rather than
silently resetting, inventing task success or changing the saved physics.

## Future training and evaluation commands

Run from the pilot worktree. The commands below are future user-run budgets;
substantive training has **not** been run during delivery.

```powershell
Set-Location D:\softrobot-agent.worktrees\rl-control-pilot
$py = 'D:\softrobot-agent\.rl-pilot-env\Scripts\python.exe'
$env:OPENBLAS_NUM_THREADS = '1'
$env:OMP_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'

& $py -m experiments.rl_pilot.train --mode residual --steps 200000 --seed 17 --max-seconds 1800 --output runs/rl_pilot/residual
& $py -m experiments.rl_pilot.train --mode direct   --steps 200000 --seed 17 --max-seconds 1800 --output runs/rl_pilot/direct

& $py -m experiments.rl_pilot.evaluate --policy runs/rl_pilot/residual/policy.zip
& $py -m experiments.rl_pilot.evaluate --policy runs/rl_pilot/direct/policy.zip
```

Both modes use the same PPO settings at the top of `train.py`: separate actor and
critic MLPs with two 64-unit Tanh layers, rollout 256, batch 64, 10 epochs,
learning rate 3e-4, gamma 0.99, GAE lambda 0.95, clip 0.2, entropy coefficient 0,
value coefficient 0.5 and gradient norm 0.5. One environment, CPU and one Torch
thread are used. SB3 seeds Python/NumPy/Torch and the environment with the supplied
seed; both routes use the same initialization convention.

One training step is one control action, not one physics step; both counts are
saved. A callback stops at the exact action budget even inside a rollout.
The stopped rollout is discarded by SB3, including when stopping on its final
transition; budgets below/equal to 256 actions can therefore save an untrained
policy. Only previous fully completed rollouts have been optimized.
Elapsed time includes setup, sampling and PPO optimization, excludes module imports
and final export. The time limit is cooperative: checked after each action, so an
ongoing optimization and the next action can overrun it. There is no watchdog.
Check actual steps and elapsed time when comparing routes that hit different limits.

Training writes `policy.zip`, `settings.json`, per-action `training.csv` and SB3
`progress.csv` under the output directory. Settings include conventions, input
paths, versions, PPO settings, seed, actual cost and stop reason. Evaluation reads
the checkpoint's paired settings (no mode argument) and writes
`evaluation/trajectory_1.csv` and `evaluation/result.json` beside the policy.
Each trajectory has 36 rows: initial state plus all 35 boundaries. Row k>0 reports
the tension on the just-completed [(k-1)*0.01,k*0.01] interval; row 0 has zero tension
and no action. Final post-step state is saved before any reset.
The JSON includes acceptance metrics, completeness, pass/fail, saved training cost
and evaluation time. Use `--episodes 2 --output <new-directory>` for two fresh
identical-start episodes; this is nominal confirmation, not robustness or
generalization. Existing output directories are refused to preserve earlier runs.
All default runtime outputs are ignored under `runs/rl_pilot/`.

## Checks performed during delivery

Imports, both CLI help interfaces and `pip check` passed. Reset produced the zero
physical state and finite float32 (109,) observations. Mapping endpoints, mixed
actions, reference indices 0/17/34, tendon order, positive-force sign and bounds
were checked without extra physical episodes. Direct mapping was independent of
the reference. Untrained PPO save/load/predict and identical seeded initial
weights were checked. Callback step/time stop decisions were checked synthetically;
`learn()` was never called.

An initial untrained residual-network smoke attempt hit MuJoCo BADQVEL at 0.2055 s
and stopped. No physical configuration was changed or discrepancy investigation
started. To finish interface verification, an untrained PPO fixture with constant
normalized action -1 (zero tension in either mode) completed exactly one 35-action,
700-physics-step episode per mode. Both exported 36 rows, six holding samples and
the final 0.35 s sample, with the required termination flags and full reset.
These are interface checks, not trained-policy results; arbitrary learned/exploratory
actions have not been shown to remain numerically stable.
Local evidence is under `runs/rl_pilot/interface_smoke_zero_tension/`; the initial
aborted attempt is retained under `runs/rl_pilot/interface_smoke/`.

**The pilot is implemented. Substantive training has not been run, PPO learning
behavior/cost/convergence is unverified, and trained-controller task success remains
untested.** No offline optimization, BDF integration, historical replay, NMPC or
repository-wide tests were run.

API references: [Gymnasium Env](https://gymnasium.farama.org/api/env/),
[SB3 PPO](https://stable-baselines3.readthedocs.io/en/master/modules/ppo.html),
[SB3 callbacks](https://stable-baselines3.readthedocs.io/en/master/guide/callbacks.html).
