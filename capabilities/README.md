# Capability library

catalog.yaml indexes spec, model, optimization, control, mujoco, diagnostics,
artifacts and learning bundles. matlab_analysis is a deprecated alias of model.
The registry reads metadata without starting MATLAB or importing numerical engines.

Each tool manifest declares IMPLEMENTED or PLANNED, inputs/outputs, family support,
fidelity, assumptions, applicability, limitations, failure codes, cost, consumed
fields, artifacts and physics dependencies. PLANNED entries have no implementation
callable and make no numerical claim; empty consumed fields/artifacts mean these
contracts are not yet finalized. Promotion requires real implementation, numerical
or structural tests as appropriate, and Human-reviewed contract metadata.

Use tools.capability_resolver.resolve_capability for deterministic route support.
SUPPORTED and PARAMETRICALLY_SUPPORTED never imply scientific feasibility or task
success. Current sections=2 is OUT_OF_GRAMMAR; if a future approved grammar admits
it, V1 returns IMPLEMENTATION_REQUIRED. Unknown physics profiles produce
PHYSICS_ASSUMPTION_REQUIRED. Missing tools or unimplemented model/control levels
produce IMPLEMENTATION_REQUIRED. Grammar bounds are not expanded by this migration.

Shared source semantics, migration commands, authority and run recovery are in
../README.md. tasks/reach_free/environment.yaml owns environment semantics;
validated XML is a representation. Runs provide artifacts and fine-grained traces.
Memory has a future index contract only. Skill schema, admission and deterministic
metadata retrieval are implemented with an initially empty library. The catalog's
skill_registry points to ../skills/index.yaml; get_skill_registry() resolves it.
No LLM runtime exists. See ../skills/README.md and ../docs/trace_skill_architecture.md.
