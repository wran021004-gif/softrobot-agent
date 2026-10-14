# Softrobot-Agent research mainline

The active research implementation starts at `python -m tools.research`. See [the PowerShell runbook](docs/research/README.md) and [module and design-space reference](docs/research/modules.md).

This branch contains the active research chain, required shared physical/numerical/execution kernels and focused tests. Retired executable workflows are preserved on `refactor/research-chain` at `5cf08f8ef9323e4309dbc7206366c728ee59b3fd` and in Git history, rather than archive directories or compatibility entrypoints.

The daily entry is `configs/research/study.json`. Two flexible segments and six independent ideal tensions are the validated first-stage scope. Next: variable tendon count with explicit start/guide/anchor routes; then variable segment count and conditional continuous optimization.
