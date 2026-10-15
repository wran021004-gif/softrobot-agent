# Softrobot-Agent research mainline

The active research implementation starts at `python -m tools.research`. See [the PowerShell runbook](docs/research/README.md) and [module and design-space reference](docs/research/modules.md).

This branch contains the active research chain, required shared physical/numerical/execution kernels and focused tests. Retired executable workflows are preserved on `refactor/research-chain` at `5cf08f8ef9323e4309dbc7206366c728ee59b3fd` and in Git history, rather than archive directories or compatibility entrypoints.

The source-relative entry remains `configs/research/study.json`. M3-C1 adds [family-space-first preparation](docs/research/family_space.md): a frozen task and declarative family can start without a scientific candidate, and `research_plan` generates independent two-segment designs with 1–7 tendons from compact routing parameters. The declared 1–9 segment range is executable only at two segments; variable-segment construction belongs to M3-C2. Physical/model compilation does not establish task feasibility.
