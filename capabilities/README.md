# Capability Library

This library describes, indexes, and queries current capabilities. Start at
`catalog.yaml`; paths in that catalog are relative to this directory. Execution
remains in the repository's `tools/` directory.

| Concept | Meaning |
| --- | --- |
| Robot Family / Design Grammar | Robot designs an LLM may propose using the current DesignSpec. |
| Tool | Executable deterministic computation or validation. Its manifest describes its actual contract. |
| Skill | A future strategy for combining tools; no skill executor is implemented here. |
| Artifact | A factual file produced by a run, such as a design, XML, or saved metrics. Current compilation writes XML; tools return metrics without automatically saving them. |

LLMs must obtain numerical results by calling tools. They must not infer physical
results from TOOL.md. MATLAB's geometric reachability pass does not imply a
MuJoCo task pass.

## Query metadata

`capabilities.registry` provides `load_catalog()`, `list_tool_bundles()`,
`get_tool_manifest(bundle_name)`, `list_robot_families()`, and
`get_robot_family_grammar(family_name)`. These return ordinary dicts or lists
using PyYAML. They do not import numerical tools or start MATLAB/MuJoCo.
Unknown catalog names raise `KeyError`; file and YAML errors propagate.

```python
from capabilities.registry import get_tool_manifest, list_robot_families

families = list_robot_families()
manifest = get_tool_manifest("mujoco")
```

## Read support honestly

Manifests are the source of per-tool field coverage, fidelity, limitations, and
failure codes. `design_fields_used` includes the family discriminator;
`numerical_design_fields_used` identifies fields used in calculations/model
generation. Ignored fields have no effect on that tool. `validate_task` takes
XML instead of DesignSpec and therefore consumes no DesignSpec fields directly.

The grammar records field meanings and `active`/`reserved` status. `active`
means a field is used by at least one current tool, not every tool. `reserved`
fields have no implemented numerical effect. Bundle/family support is `partial`:
the current approximations are executable with spatial tendon routing and tendon
actuation, but Cosserat, FEM, and validated material physics are unsupported.
The reserved sections field is explicitly restricted to 1 by M1 and compilation.
This metadata does not enforce new schema constraints.

## Current reach execution chain

TaskSpec + DesignSpec -> M0 geometric screening -> M1 single-section PCC planning
-> tendon length targets -> deterministic MuJoCo compilation -> command execution
-> final tip-position task gate. M1 uses total_length_m, tendon_count, and
tendon_routing_radius_m. Both tendon fields are active in MuJoCo as well.
M1 returns best-effort commands even when its predicted error exceeds tolerance;
only the final physics gate decides task success. TASK_FAILED is a valid result.

`mujoco/environments/reach_free.xml` is a fixed task environment selected by
TaskSpec.environment_id. Its floor, gravity, and timestep do not depend on
DesignSpec. Environments such as future reach_window.xml and insertion.xml must
be manually authored and version controlled. A future LLM designing a robot
has no authority to modify the task environment. Target and tolerance remain
TaskSpec facts, and morphology remains a DesignSpec fact. Generated XML in
`mujoco/generated/` is only environment + robot + task marker runtime output.

Only `tendon_driven_continuum` is registered. To add a family later, supply its
grammar and FAMILY.md, implement the corresponding MATLAB analysis and MuJoCo
compiler support, update the tool manifests and family acceptance checks, and
add the catalog entry. Documentation alone does not create executable support.
The metadata loader needs no per-family dispatch logic. `skills` remains empty.
