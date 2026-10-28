# Repository development rules

## Research boundaries

- Keep robot design, task specification, mathematical analysis, Agent decisions,
  and independent task evaluation distinct.
- Mathematical results do not establish successful physical execution.
- Failed optimizer attempts do not establish infeasibility.
- Local controllability, Gramians, and sensitivity estimates are diagnostics
  unless stronger mathematical conditions are independently verified.
- Declare the model, physical input bounds, operating point, time horizon,
  assumptions, and limitations of each mathematical conclusion.
- Return explicit unsupported or not-applicable results for unsupported tasks
  or physics; never silently substitute a weaker problem.
- The Agent selects and interprets evidence; deterministic tools own certificate
  validity and frozen task acceptance.
- The currently listed tasks are not the complete future task set.
- Generalize research interfaces, not every task-specific mathematical solver.

## Reuse existing architecture

- Reuse `python -m tools.research`, the registry, Store, candidate identities,
  budget accounting, and execution interfaces.
- Prefer extending existing contracts and functions to parallel frameworks.
- Do not duplicate configuration loaders, registries, evaluators, optimizers,
  or evidence stores.
- Give a new Python module one clear responsibility that cannot be placed
  cleanly in an existing module.
- Separate robot-family physics from task-specific analysis and evaluation.
- Keep numerical analysis independent of provider communication, persistence,
  and workflow orchestration.
- Existing studies own their frozen configuration; do not reload mutable
  configuration sources to reinterpret their tasks or candidates.
- Preserve purpose-specific model profiles and the shared accounted provider
  ledger when working with a Study that freezes `research_roles_v1`.
- Author new research text directly in English. Preserve historical text and
  evidence exactly; do not introduce translation or language-based rejection.
- Keep selected-method schemas, Main-Agent full-read credit, and token handoff
  tied to the existing Store, admission, receipts, and verified SDK boundaries.

## Maintainability

- Prefer short explicit functions and direct data flow.
- Avoid giant scripts, unnecessary abstraction layers, excessive classes,
  and pass-through wrappers.
- Do not add speculative compatibility code for unsupported future features.
- Avoid defensive checks that duplicate validated boundaries or Pydantic.
- Give each scientific fact and configuration field one authoritative owner.
- Localize changes; remove superseded code only after migrating its real callers.
- Treat line-count targets as guidance, not correctness constraints.
- Keep concise module documentation describing actual responsibilities.
- Preserve unrelated work and inspect the active branch and worktree first.
- Use the existing Windows/PowerShell environment and installed dependencies;
  install only when a concrete missing dependency blocks authorized work.

## Scientific evidence and versioning

- Preserve immutable historical experiments, receipts, configurations, costs,
  and source identities, including failures.
- Never silently reset research budgets or rewrite historical failures.
- Version new scientific semantics explicitly when needed; retain old meanings.
- Distinguish computation status, mathematical strength, and task acceptance.
- Track units, coordinate frames, state dimensions, tendon channel order,
  sampling phase, time grid, and actual task horizon.
- Local calculations do not establish global nonlinear feasibility, hardware
  performance, robustness, or repeatability.
- Only the independently registered task evaluator establishes task acceptance;
  retain the frozen protocol's additional acceptance components.
- Preserve raw numerical results and exact provenance alongside interpretations.

## Testing and execution

- Target changed contracts, numerical boundaries, functions, and regressions.
- Avoid exhaustive suites and repeated checks without a concrete reason.
- Do not initiate model-provider requests, long NMPC rollouts, RL training,
  or expensive scientific experiments without specific task authorization.
- Label fabricated numerical examples as test fixtures, never scientific evidence.
- Record actual changes, tests, limitations, and remaining work accurately.
- Commit and ordinarily push authorized code and non-secret documentation
  and evidence to the designated branch.
- Never commit credentials, secrets, or private environment files.
- Do not force-push, merge into a protected/base branch, delete unrelated files,
  or modify sealed scientific evidence without explicit authorization.
- Keep milestone implementation plans in task documentation, not these rules.
