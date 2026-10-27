# Softrobot-Agent research mainline

The active research implementation starts at `python -m tools.research`. See [the PowerShell runbook](docs/research/README.md) and [module and design-space reference](docs/research/modules.md).

The cross-task integration baseline is `integration/research-next`. See
[the integration report and fresh Tracking/multi-condition configurations](docs/research/integration_research_next.md).
The underlying task-conditioned mainline is documented in
[the original integration results](docs/research/softarm_codesign_mainline.md).

The research path is: reviewed task → structural candidate → mathematical
analysis → Agent decision → control optimization → physical execution →
independent evaluation → next revision. Frozen Study grants own the design
space, methods and budgets; mathematical preparation grants no physical or
formal Study permission. RL reward does not determine task acceptance.

This branch contains the active research chain, required shared physical/numerical/execution kernels and focused tests. Retired executable workflows are preserved on `refactor/research-chain` at `5cf08f8ef9323e4309dbc7206366c728ee59b3fd` and in Git history, rather than archive directories or compatibility entrypoints.

The source-relative entry remains `configs/research/study.json`.
[Family-space-first preparation](docs/research/family_space.md) can start from a
frozen task and declared family. M3-C2's v2 generator constructs named serial
prototypes within declared segment/tendon domains; actual execution still
requires candidate-specific geometry, model and runtime admission. Declared
ranges and successful compilation do not establish task feasibility.
