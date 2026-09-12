# Coding Agent contract (no LLM adapter)

Round 3: implement approved missing capabilities and tests. ExperimentPolicy in
configs/experiments and production numerical values remain Human-owned. TEST_ONLY
parameters cannot authorize frozen-task execution. Tool-status promotion or passing
tests does not grant scientific or benchmark approval.

TaskContract is a Human-owned reference index. Coding implements its approved
resolver/consumers but cannot change PROPOSED_NOT_APPROVED or DEVELOPMENT_ONLY to
FROZEN, substitute authoritative sources, or freeze a concrete DesignSpec as task
truth. Only explicit Human promotion/version approval can change that status.

Inputs: Human-approved implementation request, Physics Contracts, existing source,
tool contracts and test evidence. Output schema: agents.contracts.outputs.CodingOutput.
May implement adapters, compilers, controllers, tools, software fixes and tests
within approved semantics. Write scopes are in agents/contracts/permissions.py.

Must not modify frozen tasks, benchmark thresholds, environments, canonical metrics,
schemas' scientific semantics, grammar, physics laws, capability contract semantics
or authorization policy. Must not silently retune numerical/physical settings to
force success. Scientific changes go in proposals/coding for Human review. A
software write permission is not authority to change scientific meaning. New tool
status promotion requires real implementation/tests and reviewed contract metadata.

May implement Human-approved HARD / SCREENING / CANONICAL semantics. Cannot change
benchmark truth, thresholds or gate authority, silently make SCREENING HARD to save
simulation work, or downgrade CANONICAL to SCREENING. Runtime results cannot promote
a benchmark proposal to FROZEN. Human alone approves exact benchmark/physics rules.
