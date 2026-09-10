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
the current approximations are executable, but full continuum/tendon physics
is `unsupported`. This metadata does not enforce new schema constraints.

Only `tendon_driven_continuum` is registered. To add a family later, supply its
grammar and FAMILY.md, implement the corresponding MATLAB analysis and MuJoCo
compiler support, update the tool manifests and family acceptance checks, and
add the catalog entry. Documentation alone does not create executable support.
The metadata loader needs no per-family dispatch logic. `skills` remains empty.
