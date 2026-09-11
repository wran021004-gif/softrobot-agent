# Engineering Skill Library

This is the robot project's engineering strategy library, not a Codex SKILL.md
package. YAML/JSON contracts in `schemas/skill.py` are authoritative; generated
JSON Schemas are in `schema/`. Custom provenance/admission rules additionally run
in `tools.skill_policy.validate_skill`; JSON Schema alone cannot validate files.

The production library starts empty: candidates=0, approved=0, deprecated=0.
`.gitkeep` files are directory markers, not skills. Test data lives exclusively in
`tests/fixtures` and temporary test directories. No run generates a Skill.

A Tool is a deterministic capability. A Skill recommends which tools to select or
combine for an explicit robot/task/model/control scope. A run summary or isolated
TASK_FAILED result is not a Skill and cannot establish a causal scientific rule.

## Admission and revisions

candidate -> validation -> validated -> Human approval -> approved

`SkillRegistry.propose` validates a candidate against existing finalized runs,
manifest SHA-256 evidence, actual metric pointers, registered robot families and
IMPLEMENTED tools. PLANNED tools, undeclared strategy tools, missing evidence,
fabricated metrics, encoded task gate overrides and Human-owned mutations are
rejected. Explicit new physics returns PHYSICS_ASSUMPTION_REQUIRED. Mandatory
negative constraints preserve the existing physics/task/permission boundaries.

Strategies contain only `invoke_tool`, `inspect_evidence`, or
`request_human_review` steps. They contain no executed-result, shell-command,
gate-setting or mutation-path fields. Prose is an explanation, never executable
authority. A small deterministic check rejects explicit English mutation/override
instructions; it is not a semantic proof of arbitrary language. Human must review
scientific/generalization claims. No LLM Judge or automatic causal attribution exists.

`record_validation` requires SkillValidationRecord and hashed
SkillValidationEvidence artifacts binding each outcome to a skill reference,
strategy hash and real run. Validation coverage is checked against saved task,
robot and seed metadata. The infrastructure checks the recorded experiment; it
does not execute or independently reproduce the experiment. Cross-run execution
and statistical assessment remain future work.

Failed/contradicted validation records are preserved. A negative record leaves the
proposal a candidate. A later passed record can validate it; Human reviews the
complete history before approval. A new strategy/scope requires a new version
linked by `supersedes`. Previous versions retain their negative evidence. An
approved version is immutable and can only be deprecated; further experiments or
strategy changes use a new candidate version.

`approve(reference, HumanApproval(...), actor="human")` is an explicit trusted
Human entry point. It requires validated state, a validation record and an approval
hash matching the reviewed content. This local API is not authentication: a future
remote/agent caller must supply authenticated Human identity outside the proposal.
Human ownership and existing filesystem/agent permission checks still apply.
No autonomous executor or approval service is included.

Files use `id@version.rN.yaml`, containing `{revision, skill}`. Status transitions
append an exclusive new file in candidates/, approved/ or deprecated/. Older files
remain audit history; readers use the latest revision, so a deprecated version is
excluded even though its former approved revision still exists. The JSON Schema
for a `skill` value is `schema/skill.schema.json`. Revisions must be contiguous and
transitions valid. No in-place overwrite is permitted. This is a small local
registry; concurrent transactions and tamper-proof signatures are not provided.

## Deterministic retrieval

```python
from capabilities.registry import get_skill_registry

skills = get_skill_registry().retrieve_skills(
    robot_family="tendon_driven_continuum",
    task_type="reach",
    failure_category="TASK_FAILED",
    model_level="M1",
    control_level="C1",
    skill_category="DIAGNOSIS",
)
assert skills == []  # legitimate initial state
```

Filters match explicit scopes exactly. `required_tools` means tools a returned
strategy must require (subset filter), not an execution allowlist. Default results
are approved only. `include_candidates=True` explicitly adds candidate/validated
proposals for research; `status="candidate"` alone does not bypass that default.
Rejected/deprecated versions are never executable retrieval results.
Ranking is stable: approval status, distinct successful validation-run coverage,
descending version, then skill ID. All supplied exact-match filters apply first.
Metric trigger predicates are returned for a future consumer to evaluate against
its current evidence; this metadata interface does not run a diagnosis loop.

No matches returns `[]`; there is no fabricated fallback. The deterministic reach
pipeline never loads/retrieves a Skill. `capabilities/catalog.yaml` links index.yaml
and retains `skills: []` until real Human-approved strategies exist.

Engineer may later retrieve DESIGN/MODEL_SELECTION/CONTROL strategies; Diagnosis
may derive signatures from trace and retrieve DIAGNOSIS strategies; Coding may
retrieve CODING_SIMULATION strategies. All follow recommendation -> decision ->
normal permission check -> execution. Skills cannot elevate any agent's authority.
