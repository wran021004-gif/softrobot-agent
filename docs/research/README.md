# Research mainline

## SoRoSim S4.5–S5 studies

The [stage delivery report](sorosim_s45_s5_delivery.md) links the separate
S4.5, open-loop MuJoCo, full feedback NMPC, direct/residual PPO, and S5-T
immutable Store exports. All observed physical evaluations failed the original
task; mathematical feasibility and optimizer convergence are reported
separately. The local [Agent preflight](../../evidence/sorosim_s5_agent/preflight.json)
imports those stages into one research packet without a provider send. The
[egress review](../../evidence/sorosim_s5_agent/egress_review.json) records why
the bounded live provider pilot has not run.

The historical root study described below still has ten training-stage
allowances and no aggregate action ceiling. New sparse stage configurations
may declare smaller explicit stage and cumulative action counts; the S5-RL
study enforced two 32,768-action stages and two independent evaluations.

The public entry is `python -m tools.research`. Edit `configs/research/study.json`; its references own robot physics (`robot.json`), task/acceptance (`tasks/reach_hold.json`), control/training defaults (`control.json`) and interpreters/provider/threads/credential reference (`runtime.json`). `tools/research/config.py` is the sole resolver. It recursively merges sparse objects, replaces lists, validates complete effective settings and freezes provenance plus identity in the owned Store and `resolved_configuration.json`.

Omitted training/reward settings inherit configured values. `policy_kwargs.log_std_init` preserves the declared architecture. Explicit null disables scientific/aggregate time limits and is supported for absent references/boundaries and optional PPO `clip_range_vf`/`target_kl`; null cannot clear required numeric settings, mode or step allocation. Reward and observation scaling never change frozen task acceptance. Existing-study commands and workers use saved configurations, without resolving editable files. Status/export do not import Torch, SB3 or construct an environment, and do not require an RL interpreter. Source JSON can be edited or absent without changing a prepared study.

The resolver materializes typed controller/backend parameters before freezing. Preparation consumes that complete configuration without recomposing policy defaults. The algorithm helper validates configured solver iterations/tolerance without overriding them. Limits permit null elapsed time; receipt/event costs require finite numeric elapsed time. Unknown unflushed training consumption is reported as lower/upper bounds with actual actions unknown until verified.

```powershell
Set-Location D:/softrobot-agent/.worktrees/research-mainline
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
$researchPython='D:/softrobot-agent/.mainline5-env/Scripts/python.exe'
# Edit the root identity before a NEW study. IDs are single use.
& $researchPython -m tools.research prepare --spec configs/research/study.json
# Commit implementation before binding or dispatch.
& $researchPython -m tools.research bind --run-id research-count-20261015
& $researchPython -m tools.research run --run-id research-count-20261015
& $researchPython -m tools.research status --run-id research-count-20261015
& $researchPython -m tools.research recover --run-id research-count-20261015
& $researchPython -m tools.research export --run-id research-count-20261015
# After a committed implementation repair, preserving configuration and counters:
& $researchPython -m tools.research migrate --run-id research-count-20261015 --reason 'Concrete repair and evidence impact'
```

`runtime.json` references the existing DeepSeek provider and `~/.codex/.env`; the loader uses the actual home directory. Credentials are never exported, logged or passed into RL children. The existing `.mainline5-env` research and `.rl-pilot-env` RL environments are reused; no dependency upgrades are required.

The scientific allowance is ten durably admitted training stages, shared by initialization and checkpoint continuation. A rejected request consumes no stage; an admitted failed stage remains an engineering attempt. Exact recovery and receipt reuse retain the stage. Worker launches are recorded separately. Each stage has positive finite actions, aligned upward to complete rollouts **before** admission with requested/effective amounts recorded. At least two complete updates are required. There is no aggregate requested-action or training-time ceiling. Terminal verified unused actions are released; uncertain unflushed reservations remain conservatively recorded and cannot be duplicated. Reconciliation is idempotent.

NMPC executions, independent RL evaluation episodes, candidate mathematics (including search internals), local solves, provider sends and public operations each have finite frozen counts. Provider/public-operation closeout reserves are subsets of the totals. Zero offline-NLP/BDF/diagnostic-replay allowances disable those expensive routes. The current root records the exact counts; ten stages are a ceiling, not a target. No allowance expands after failures.

All scientific elapsed-time limits are explicit `null`, through the model loop, admission, Host/Store, contained numerical workers and backend. Actual elapsed time remains numeric evidence. Finite solver iterations, stage steps and physical simulation timestep/control period/duration/holding window remain enforced. Network transport timeouts and short synchronization polls remain operational settings. This mode cannot guarantee finite wall-clock completion if a native computation hangs, and offline task success does not establish real-time performance.

The model chooses supported structure/material/control changes, NMPC, direct RL, compatible residual RL, mathematics, saved-state diagnosis, continuation or justified STOP. RL does not depend on prior NMPC success. A complete failed NMPC reference remains usable only for its exact candidate/task/channel/grid identity. No reference transfer to changed robots is allowed.

The first fresh, complete, numerically valid backend pass against every frozen condition persists a common success gate. It blocks subsequent science, including remaining search candidates and queued model calls. The model must publicly read and select the exact evidence. Zero extra confirmations seal immediately, with repeatability unassessed. Observed pass, model selection and engineering completion are distinct. Exhausted counts without model STOP produce explicit engineering count-budget closure.

## RL lifecycle and manual cancellation

`rl --run-id <study> --plan <request.json> --request-id <unique-key>` dispatches a typed research RL request. `execute` similarly accepts a research plan. `start` initializes a stage. `resume` accepts an owned run ID and recovers its exact original configuration, checkpoint schedule and remaining admitted steps. `continue` accepts the exact parent `run_id`, published `checkpoint`, additional finite `allocation.actions`, rationale and sparse training/reward changes; it creates a separate immutable stage.

Continuation supports learning rate (constant or `{kind: linear, initial, final}`), rollout length, minibatch size, epochs, entropy coefficient and the declared reward weights. It preserves policy weights, Adam moments/step counters and lifetime history; it resets stage-local progress and applies the declared new schedule to the actual optimizer and rollout buffer. Architecture, observation/action semantics, normalization, tendon order, candidate and residual reference must match. Initialization-only changes are rejected. The exited parent and complete published checkpoint are verified against the original source configuration. Parent artifacts are never edited.

For a new direct-policy initialization, `initial_tension_n` optionally sets a declared physical mean tension by initializing the actor's last-layer weights/bias. Null preserves ordinary SB3 initialization. This changes initial policy weights, never action mapping, bounds or task acceptance. Resume/continue reject this setting and preserve the parent weights. The default remains null; the engineering addendum explicitly chose a low-tension initial mean after the original high-tension short policy produced an incomplete numerical evaluation.

A `stop` request cooperatively stops the owned RL run. Add `"force": true` to stop the verified owned process tree if native work does not respond. For an owned synchronous numerical worker, interrupt the foreground research process; containment terminates its worker tree. Inspect/recover retained evidence afterward; no automatic relaunch is permitted. Unknown termination retains reservations. The Windows worker uses a kill-on-close job and process identity, never process-name matching.

## Limited verification

```powershell
# Fixtures only; normal discovery never launches training or provider calls.
& $researchPython -m unittest discover -s tests/research -v
# Single-use real chain, declared through the SAME root/resolver:
$env:SOFTROBOT_REAL_RL_TEST='1'
& $researchPython -m unittest discover -s tests/research -p test_rl_integration.py -v
Remove-Item Env:SOFTROBOT_REAL_RL_TEST
```

The `rl_chain` profile uses its separate engineering study, two 4096-action stages, one independent full-task evaluation, zero provider requests and disabled scientific timers. A short policy may fail acceptance while its complete engineering chain passes. Do not rerun this profile to overwrite its single-use ledger. The [results](results.md) separate fixture, saved-data, real-process and scientific outcomes. Historical `research-mainline-20261015` remains sealed with original receipts, implementation binding and conservative charge intact.

The first real chain completed both training stages and continuation checks but its evaluation failed numerically. The user explicitly authorized an addendum in the same engineering study: two additional stages and one additional evaluation (totals 4/2, with six physical-dispatch slots). Its original frozen configuration, failed evidence, grant identity and consumption remain preserved. This addendum does not apply to scientific studies and is unavailable to model tools. Continuing this explicitly authorized chain selects its frozen run with `SOFTROBOT_VALIDATION_RUN_ID=engineering-count-20261015`; it requires a committed explicit migration and cannot silently repeat the addendum.

The completed scientific study `research-count-20261015` remains bound to `b3ba9cc019302cbd74de73c991977a31f44e0551`. The model selected its first fresh passing NMPC result after reading it: one execution, seven provider requests, no RL stages and no extra confirmation. See [results](results.md) for exact evidence and limitations. The final configuration-validation repair was made after closure; normalized effective defaults are identical to those actually studied, and the sealed study was neither rebound nor rerun.
