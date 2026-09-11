# Coding Agent contract (no LLM adapter)

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
