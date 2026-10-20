# S10 feedback-driven mirror study

Status: engineering preparation complete; formal Provider study not yet started.
This document will report actual outcomes after formal execution. Passing tests
and historical observations are not S10 scientific success.

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
