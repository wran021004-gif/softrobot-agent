# S7 frozen research protocol

Starting repository: `6629b37f976ad7fc63521171082f6a8f1cb7e4e5`, branch
`feat/sorosim-matlab-nmpc`. Historical S6 artifacts are immutable inputs.

Two targets were fixed before any S7 physical execution:

| Study | Task target (world m) | Task input |
|---|---|---|
| `s7-mirror-live-20261019` | `[0.29, -0.035, 0.19]` | `tasks/reach_hold_mirror_v1.json` |
| `s7-variant-live-20261019` | `[0.28, 0.02, 0.20]` | `tasks/s7_reach_variant.json` |

Both studies retain the original registered reach evaluator, endpoint tolerance,
holding window, position and speed thresholds, timestep and ideal tension model.
The same research instructions, family definition, tools, Store, ledger and
acceptance protocol serve both tasks. Source controls from S6 are engineering
initializations only; historical task success is never imported as a new result.

Each formal study permits at most 24 provider requests (4 protected for closeout),
150 public operations (12 protected), 64 shared backend launches, 4 mathematical
analyses, 1 full NLP, 2 independent mathematical reintegrations, 2 full NMPC
executions, 1 PPO training stage with at most 65,536 actions, and 1 independent PPO
evaluation. These are ceilings, not quotas. All routes share the backend ledger.
No mid-study budget enlargement or threshold edits are permitted. The first fresh
complete original-task pass blocks further exploration and requires exact public
evidence read and selection. A failed bounded search is not an infeasibility proof.

The separate context connection study permits two provider requests and zero
physical or mathematical executions. The separate numerical engineering study
permits two physical evaluations and zero provider requests. Its prescribed
density/topology checks are labelled engineering work, not Agent decisions.

Before each launch, prepare and bind its committed configuration through
`python -m tools.research`. Persist original requests, provider responses, tool
requests, raw results, failures and costs. Export each study separately. A valid
failure receives a best-candidate delivery package without a success label.

S7 claims cover nominal sampled reach-and-hold instances. They do not establish
general robot-task solvability, optimality, robustness, hardware execution or
repeatability. Mathematical tools keep their registered task-specific limitations.
