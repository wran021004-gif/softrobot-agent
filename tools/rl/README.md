# Candidate-aware RL in the existing Strands research workflow

`research_core.converse` registers `research_plan`, `research_rl`, `experience_retrieve`, and `evidence_read` with the existing Strands harness and sequential executor. The RL study mode exposes candidate proposals and bounded closeout; other study modes retain their existing numerical workflow. `tools/research_core_rl.py` verifies owned candidates, compiles XML through `physics_for → scene.assemble → compile_xml` without `MujocoBackend.solve`, freezes task/control/configuration and dispatches the existing CLI across the research/RL interpreter boundary. It implements no PPO or physics stepping.

Use `examples/rl_strands/specification.json` with `python -m tools.research_core prepare|bind|live|status|export --spec ...`. Commit the scoped implementation before `bind`. `live` uses the existing credential loader at `$HOME/.codex/.env` and configured DeepSeek provider. No credential enters a worker environment or evidence artifact. The live clock starts once before the first request; subsequent conversation recovery retains it and every cost. The checked-in study ID is single-use: inspecting it does not launch new experiments.

The fixed ceilings are 24 provider sends (including failed sends and auxiliary requests), 60 public operations, one new training run, 2048 attempted training actions, 120 cumulative active training seconds, one evaluation episode, at most one diagnostic replay of one physical step, and 900 live elapsed seconds. Last four provider requests are protected for evidence/STOP. Failed operations consume their applicable limits. Recommendations for more work close this bounded study without executing a second trial. A short training failure does not prove design infeasibility.

## Public operation contract

`research_rl` accepts `operation: start|status|stop|resume|evaluate|diagnose` and a rationale. Start requires an owned candidate EvidenceRef, explicit direct/residual mode, allocation `{actions, active_seconds}`, `training_overrides`, and `reward_overrides`; task may be omitted only to bind unambiguously to the study's immutable task. Residual requires a complete reference matching candidate/task identity, tendon order, timing, dimensions, limits and digest. There is no compatible residual reference for the acceptance study; the model chooses its mode and settings.

Supported PPO settings are learning rate, rollout/minibatch/epoch sizes, gamma, GAE lambda, policy/value clipping, advantage normalization, entropy/value coefficients, gradient norm, target KL and bounded policy network settings. Learning rate/clipping accept existing linear schedules `{kind: linear, initial, final}`. CPU, one environment and one Torch thread are fixed. Rollout allocation must contain at least two complete batches and align to `n_steps`. Reward weights are `position`, `holding_speed`, `smoothness`, and nonpositive `failure_penalty`. Unknown fields and arbitrary reward code are rejected. Requested overrides and the effective merged configuration are saved; the worker records the values actually passed to PPO and its environment.

Subsequent operations require `run_id` and retain configuration. Evaluation accepts a published `checkpoint` (defaults to current). Diagnosis accepts an owned run-relative `failure` NPZ; default `replay=false` inspects evidence only. An explicit replay reloads the capture's recorded configuration and checks its digest, then calls exactly one `mj_step`. An unknown/incompatible capture cannot be replayed. No automatic replay, reference substitution or worker restart occurs.

## Candidate and frozen task

The runtime input is explicit XML plus snapshotted assets, selected ordered joint/tendon/actuator names, tip site, ideal-tension semantics, frozen reach-and-hold task and RL configuration. The current generator emits inline meshes; external asset files are rejected until explicit snapshot support is added. The environment resolves selected hinge qpos/dof addresses independently, excluding unrelated scene coordinates and actuators. Dimensions, per-channel limits and control substeps derive from the loaded model. Length servo, unsupported joints, incorrect gain/sign/force limits and incompatible timing raise specific errors. Positive commanded tension corresponds to negative MuJoCo actuator force. Physics options are never silently rewritten.

Direct maps normalized actions into each channel's actual permitted tension interval. Residual adds recorded per-channel residual scales to a compatible saved tension reference and clips to those intervals. Observations concatenate selected qpos/qvel, target error, world tip velocity, previous applied tensions and task phase. Only reach-and-hold is supported. Goal, named initializer, duration, inclusive holding samples, position and speed thresholds remain frozen independently of reward weights.

New starts have no historical XML/database/archive fallback. Historical compatibility is isolated in `checks.historical_input`/`legacy_config`, backed by the explicitly archived historical configuration; it is never used by the candidate bridge. The historical policies and numerical-failure evidence are retained without retraining.

## Accounting, recovery and evidence

The existing project Store reserves a launch and its allocation before dispatch. Operation receipts prevent duplicate delivery from launching another worker. Run facts store cumulative consumption by run ID; status replaces those facts rather than repeatedly adding the entire cumulative total. Active reservations persist while a worker exists. Worker accounting records actual attempted/completed actions, physical substeps, failed episodes, active time, conservative uncertain consumption and checkpoint-inherited optimizations/epochs. Rollout physical reservations now use actual runtime substeps.

Checkpoint generation remains atomic, with policy/configuration digests, Adam state, counters and original schedule continuity. Resume retains the same horizon, configuration and budget. Pre-action and pre-optimization guards enforce limits; existing cooperative in-flight optimization/write overruns are recorded rather than hidden. Pauses do not reset costs. Provider, training, evaluation and diagnostic costs remain distinguishable; the live elapsed clock is not a sum of overlapping intervals.

Independent evaluation reloads a saved policy and starts a fresh simulation. Evidence binds study → candidate → task → run/configuration → checkpoint → evaluation, with actual errors/speeds, holding coverage, trajectory completeness, pass/fail and concrete failure reason. Numerical failures retain full pre-failure integration state; training surrogate terminals are excluded from physical evaluation trajectories. The model must explicitly read immutable evaluation evidence and cite it in its next-step decision. Protected closeout removes mutating RL tools and permits owned RL evidence; it does not require historical-style confirmation runs.

## Focused verification

Use the two existing interpreters, without installing dependencies:

```powershell
& D:/softrobot-agent/.rl-pilot-env/Scripts/python.exe -m unittest discover -s tests -p test_rl_runtime.py -v
& D:/softrobot-agent/.mainline5-env/Scripts/python.exe -m unittest tests.test_research_core.RLIntegrationTests -v
```

Tests cover a two-hinge/two-tendon robot alongside an unrelated free scene joint/actuator, coordinate ordering, channel limits/sign, exact timing, rejected servo inputs, override propagation, immutable task acceptance, real candidate XML compilation, duplicate receipts and idempotent cumulative accounting. Existing checkpoint/recovery checks are retained. These checks do not launch training or execute a diagnostic physical replay. The single live study provides separate interface and task-performance evidence in `evidence/rl_strands_20261013`.


The sole live study did not meet full interface acceptance: its worker failed during Torch import before sampling because the bridge's first environment filter dropped `SystemRoot` when Windows enumerated it as `SYSTEMROOT`. The repair uses the existing case-insensitive keyed environment lookup and is verified by a real Torch/asyncio import in a credential-free subprocess. The failed run retains its conservative 90-second startup charge and is not retrained. An unavailable-evaluation artifact records zero episodes, no checkpoint, no metrics, and unmeasured task performance. The real model publicly read that failure artifact and selected `adjust_training` for future work; no second trial was executed.

`strands_pilot.py` is unchanged. The one narrow `strands_pilot_r3.py` edit lets an opt-in bounded study reserve at most the remaining request deadline/wall allowance instead of an unconditional 600 seconds. A fixed 600-second reservation would otherwise make a 900-second study reject later requests after only 300 seconds. Provider logging, response recovery, retry behavior and default studies retain their prior behavior. Research feedback facts also received a scoped RL branch so tool errors expose RL ownership/evidence rather than numerical confirmation assumptions.
