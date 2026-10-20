# S10 feedback-driven mirror study

Status: prepared and frozen; formal Provider study is awaiting explicit external
payload/destination authorization. No S10 Provider request or fresh scientific
evaluation has run. Passing tests and historical observations are not S10 success.

Only `feat/sorosim-matlab-nmpc` and its designated worktree are modified.
Initial local and fetched origin HEAD are both
`e7750c956e2ec8be9afd28e6d32c81d63a0b2a55`; the worktree was clean.
The independent RL worktree and all sealed S7/S8/S9 evidence remain unchanged.

## Preparation and frozen scope

The authoritative `tasks/reach_hold_mirror_v1.json` resolves to canonical identity
`d24aeac7041052ce1d2ae60e825a802e7367107784f6fec192b0a65c4a5e76e7`.
The target is `[0.29,-0.035,0.19]` m. Original duration 0.35 s, control interval
0.01 s, physics step 0.0005 s, hold 0.30–0.35 s, position 0.01 m and holding
speed 0.02 m/s are unchanged, as are initializer, evaluator and force limits.
Candidate-specific effective task identity includes actual joint names.

`configs/research/study_s10_mirror.json` declares an independent formal Study
`s10-mirror-live-20261020`. Budgets: 32 Provider requests (4 protected), 160 public
operations (12 protected), 64 shared backend starts, 4 registered analyses, 1 NLP,
2 BDF replays, 2 NMPC executions, 1 PPO stage, 65,536 aggregate training actions
and 1 independent evaluation. PPO default rollout is 256, permitting 256 complete
updates at the ceiling; a smaller legal allocation remains the Agent's choice.
Scientific timers stay null; solver/stage counts remain finite. The original
protocol requires zero extra confirmation repetitions. The first fresh complete
pass blocks exploration and requires public reading and exact native selection.
No budget may expand after observing formal outcomes.

S7's best complete mirror failure is imported through the existing identity and
archive checks: normalized gap 3.6020739579215553. S8 produced two static equilibrium
results and zero fresh physics. Both are retained as historical mathematics with
their original candidate/model/workpoint scope; neither is current verified input
sensitivity. S6 provides an optional unmeasured, explicitly adapted control start.
S9's second-target accepted result is not imported as mirror acceptance.

## Actual engineering availability

- New separate `s10-readiness-20261020` ledger: MATLAB dependencies, startup,
  gateway, sqrt(4) and shutdown passed using the existing pinned SoRoSim commit
  `24d573a3e864ffda87c42ee462a6ed620133cc7b`. Zero Provider/scientific starts.
- `s10-admission-20261020` materializes history and candidates without scientific
  launches. Existing binding checks confirm current task/channel/grid identity.
  Direct PPO configuration and actual environment construction passed in the
  configured `.rl-pilot-env` interpreter: 4 ideal-tension channels, 48 DOFs,
  107 observation components, 35 control intervals and original force limits.
  Initial probing in the research interpreter lacked gymnasium; the check was
  corrected to use the existing RL interpreter, without installing packages.
- Residual PPO has no current published compatible reference. Its existing
  candidate/task/order/grid/reference admission remains required; a future exact
  complete mathematical or NMPC trajectory may supply it. This is a missing
  prerequisite, not a reason to change actuator semantics or disable Direct PPO.
- Mathematics and NMPC passed dependency/gateway readiness and retain existing
  candidate-specific admission. No new scientific solve, NMPC rollout, training
  or independent policy evaluation was performed during preparation.
- Full `family_space_s7` domains remain available through candidate capability
  reads; no manually selected reduced structural space or fixed method order.

Preflight data and exact domains: `evidence/s10_mirror/preflight.json`;
history/model details: `historical_inventory.json`; actual MATLAB report:
`evidence/s10_readiness/verified/report.json`. Engineering ledgers remain separate
from formal costs. The evidence includes limitations distinguishing registration,
environment construction, actual scientific execution and Agent selection.

## Changes and validation

Production code: **+0/-0 lines**. Existing Agent, decision contracts, Store,
budget, evidence policy, physical playback, optimizer and evaluator are reused.
No additional production module, optimizer, Agent or formal runner is introduced.
The three new configuration files own formal study, independent startup readiness
and independent admission preflight. The new three-test configuration module
checks original task identity, bounded methods/counts and historical scope.

Existing focused regression: 75 tests, 74 passed and 1 opt-in real RL skipped.
`test_s10_configuration`: 3 passed. Logs are under `evidence/s10_mirror`.
Commands use `.mainline5-env`, `PYTHONPATH=.;tests/research;` plus the existing
MATLAB Engine path, pinned `SOROSIM_ROOT`, and OMP/OPENBLAS/MKL threads each 1.
No test sent a Provider request or executed training/scientific rollout.

Provider destination for formal research is
`https://api.deepseek.com/chat/completions`. Scope is this project's task, family,
robot/control parameters, scoped mathematical/physical evidence, budgets, tool
schemas and Agent/tool conversation. Authentication is loaded from the existing
credential reference; key contents, headers and unrelated worktrees are excluded
from saved/exported research payload. Any external-send approval requirement
must be resolved against this S10 scope, without relying on S9 authorization.

## Formal launch and current research conclusions

Preparation commit `8c2eb88ee5e076c873edc5fe9e4fb22966b93d64` and formal protocol
commit `7bac54ad311fab798d806ccd29504740a5cf07c4` were ordinarily pushed; each
remote SHA was verified. Formal Store is
`runs/research/s10-mirror-live-20261020`, bound to `7bac54ad…`. The initial binding
at preparation commit was migrated using the existing CLI before any Provider
request, with an explicit metadata-only reason. Frozen configuration, source
hashes, historical ownership and zero scientific counters were preserved.

The requested `python -m tools.research run --run-id s10-mirror-live-20261020`
was rejected by automatic approval review **before command execution**. Its stated
reason: potentially sensitive project/numerical/control/conversation data would
be transmitted to DeepSeek, and existing trusted authorization did not clearly
authorize the exact payload/destination combination. There was no retry or
indirect send. A new S10-specific authorization question names the exact scope,
review file and `https://api.deepseek.com/chat/completions` destination.

The formal study remains ready and recoverable, rather than scientifically
stopped or falsely marked failed. All formal counts remain unused, pending and
unconsumed response are empty. The exported archive preserves configuration,
identities, materialized history, initial controls, binding and ledger. Historical
best failure is retained through its original references; there is no fresh S10
best candidate to deliver. The archive does not claim new dynamic acceptance.

Current answers to the requested research questions:

1. **Autonomous calculations:** none yet; no real Provider request executed.
   Engineering readiness and admission checks are not Agent research decisions.
2. **Failure-driven strategy revision:** not observed; no new scientific batch
   or subsequent Agent decision exists. No synthetic failure or decision was made.
3. **Mathematical value:** formal value remains untested. The gateway check and
   scoped historical equilibria establish preparation only; neither establishes
   improved control or physical feasibility.
4. **Structure/control exploration:** none in formal S10. Historical structure
   materialization and legal seed adaptation are preparation, not a model-selected
   structural experiment. The full legal space remains available.
5. **Feasible S10 solution:** not established. There is no new independent MuJoCo
   evaluation, accepted result or native SELECT/STOP. The external approval block
   is not evidence of mathematical or physical infeasibility.

After explicit authorization, resume through the same `run` command and frozen
Study; do not prepare a duplicate Study, reset counts or substitute a local
scientific plan. The existing recovery mechanism handles any later uncertain
Provider/worker outcome. No new research direction has been selected by Codex.
