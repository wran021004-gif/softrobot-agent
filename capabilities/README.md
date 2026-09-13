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
../README.md. Each selected package's environment.yaml owns environment semantics;
validated XML is a representation. Runs provide artifacts and fine-grained traces.
Memory has a future index contract only. Skill schema, admission and deterministic
metadata retrieval are implemented with an initially empty library. The catalog's
skill_registry points to ../skills/index.yaml; get_skill_registry() resolves it.
The optional single-model DeepSeek runtime uses the bounded workbench; it cannot
run code or call historical campaign entry points. See ../docs/round6_deepseek.md.
Skill admission remains separate; see ../skills/README.md and ../docs/trace_skill_architecture.md.

Round 2 promotes analyze_clearance (MATLAB, full PCC swept radius, low/geometric)
and check_collision (deterministic recorded evidence) in the existing model and
diagnostics bundles. The explicit reach_window route uses a NON_CANONICAL fixture
until Human approves benchmark geometry. Policy-scoped optimization and bounded
repair are implemented; learning/RL remains PLANNED. Historical experiment
authorization does not grant execution through the new workbench.

Round 5: `python examples/workbench.py catalog` is the executable directory.
It includes strict JSON input schemas, preconditions, permissions, costs and a
uniform WorkbenchResult output. Legacy manifests remain descriptive library
metadata and cannot dynamically register executable tools. See
[the Chinese workbench guide](../docs/round5_workbench.md).

Round 6 adds create_candidate, check_candidate, evaluate_candidate,
compare_candidates and observe_candidate in the same allowlist. These require
a design session created with `--deepseek`, validate the existing Human-owned
exploration envelope, and bind checks and evaluation caches to each candidate.
The decision model may change only length, routing radius and tendon count.
