# Round 1.5 trace and experience contracts

Artifact != Trace != Memory != Skill.

Round 2.5 adds `gate.gate_type` (HARD / SCREENING / CANONICAL) and one bounded
`gate_summary.json` per Harness run, with gate actions, stopping reason, screening
failures, task truth status and final evaluation. HARD FAIL stops the candidate;
SCREENING FAIL continues; CANONICAL FAIL remains TASK_FAILED. Historical traces
with missing gate_type remain readable as untyped evidence, not retroactively
approved gates. See schemas/gate.py and agents/contracts/README.md for authority.

| Concept | Responsibility | Current storage/interface |
| --- | --- | --- |
| Artifact | Raw factual result of a run, including numerical state | Existing run files and SHA-256 manifest |
| Trace | Logical order, stage/tool parentage, decisions and gate evidence inside one run | trace.jsonl and schemas.trace.TraceEvent |
| Memory | Historical run summary/search metadata/evidence index | MemoryRecord only; no database |
| CandidateFinding | Evidence-level observations with unknown causal attribution | CandidateFinding and explicit extractor/validator |
| Skill | Reusable, validated tool selection/orchestration strategy | Versioned YAML registry, admission policy, metadata retrieval |

Run artifacts -> fine-grained trace -> Candidate Finding -> Candidate Skill ->
validation -> Human approval -> Approved Skill. Trace can also feed a future
Memory index. No automatic Skill generation, curator or agent loop is implemented.

## Audit and compatibility

Round 1's trace.json was a flat list of `{sequence, gate, status, ...evidence}`
rewritten after each call to RunArtifacts.event. save_tool_result wrote a ToolResult
and appended its flat summary. finalize_run hashed each artifact except run.json;
run.json is the manifest, avoiding a self-hash cycle. Tests rely on these filenames,
gate names, ToolResult contents and exact-byte hashing. These contracts remain.

trace.jsonl adds one bounded JSON event per logical action. It is not MuJoCo
timestep data and never contains full XML, ToolResults or simulation arrays.
ToolResult remains the formal deterministic tool output; trace references it and
copies only a bounded scalar summary. Trace uses at most 16 KiB per event, 32
items per payload collection, 1 KiB strings and bounded nesting. It has no private
chain-of-thought fields; DecisionRecord stores only a short public rationale.

```text
RUN_STARTED
  input snapshots / spec validation / capability and grammar gates / RobotIR
  model STAGE_STARTED
    matlab_session TOOL_STARTED -> TOOL_FINISHED
    analyze_workspace TOOL_STARTED -> TOOL_FINISHED
    plan_pcc_reach TOOL_STARTED -> TOOL_FINISHED
  model STAGE_FINISHED
  CONTROL_SELECTED (C1)
  mujoco STAGE_STARTED
    compile_mujoco TOOL_STARTED -> TOOL_FINISHED
    run_task TOOL_STARTED -> TOOL_FAILED (TASK_FAILED is its formal ToolResult)
    CONTROL_APPLIED (actual control evidence)
  mujoco STAGE_FINISHED (execution completed)
  physics_sanity_gate PASS
  task_metric_gate FAIL (position_error_m > frozen tolerance)
  diagnostics STAGE_STARTED
    compare_model_sim DIAGNOSTIC_STARTED -> DIAGNOSTIC_FINISHED
    check_actuator_limits DIAGNOSTIC_STARTED -> DIAGNOSTIC_FINISHED
    check_tendon_tracking DIAGNOSTIC_STARTED -> DIAGNOSTIC_FINISHED
    inspect_numerics DIAGNOSTIC_STARTED -> DIAGNOSTIC_FINISHED
    ARTIFACT_CREATED diagnostic_summary.json
  diagnostics STAGE_FINISHED
  matlab_cleanup TOOL_STARTED -> TOOL_FINISHED
RUN_FINISHED (TASK_FAILED)
```

Finish events are children of their start events. Tool starts are children of
stage starts; stage starts are children of the run root. Sequence starts at zero;
event IDs include the run ID and are unique across runs.
Parents must already exist and remain open. Validation rejects cycles, mixed runs,
duplicate IDs, invalid pairing, duplicate finish, unfinished children, invalid
timestamps, unknown taxonomy, oversized payloads and missing/escaping references.
Only actual harness/tool/gate actors generate current events. Other actor types,
DecisionRecord and repair/skill event types are schema support for future callers.

`run_reach(previous_run_id=..., relationship="rerun" | "repair")` records an explicit
relationship to a real finalized run without pretending that an agent repaired it.
The default pipeline never generates a repair or Skill event.

The writer appends at logical calls, never at a timestep. Each append closes its
file handle, so abandoning a run does not leak a Windows file lock. It does not
force fsync. The trace remains an incomplete prefix if the process crashes;
completed trace readers reject such a prefix, while `read_trace(validate=False)`
allows schema-only inspection. Exceptions and normal early returns use span
cleanup and the Harness finally block to close and validate the run.

At finalization: emit RUN_FINISHED, seal the writer, validate in-memory and saved
JSONL, hash exact files, update run.json. trace.json and trace.jsonl both enter the
manifest. Absolute duration/timestamps/run IDs are observational and naturally
differ across runs; frozen inputs, numerical outputs, equations and gates do not.
Source snapshots include the new contracts/library implementation for provenance.

Artifact references are portable run-relative paths. They resolve against the
final artifact bytes; repeated writes such as provenance.json are not historical
content snapshots. Source/ToolResult snapshots provide the factual inputs/outputs.
References may include JSON pointers and SHA-256; trace references obtain their
final integrity from run.json. Skill/Finding admission requires explicit hashes
matching finalized manifests and actual artifact bytes. Hashes detect changes,
not malicious replacement of the entire run and manifest.

## Finding extraction

`extract_diagnostic_finding(run_id, run_root)` is an explicit post-run interface.
It copies five exact diagnostic fields only when all corresponding evidence is
available and valid. No production pipeline automatically stores a finding.
`validate_finding` requires real finalized source runs, exact hashes/pointers and
observation values matching those artifacts. `ruled_out` is narrowly scoped to
the recorded sampled maximum-pull saturation and numerical indicators. It does
not prove correct actuation, stability, model mismatch or a repair. Attribution
is UNKNOWN. A missing diagnostic returns None; unavailable is not interpreted as
zero or false. A caller can persist a finding in a separate evidence-bearing run
or a proposal without editing a sealed source run.

## Future integrations

Engineer, Diagnosis and Coding can later produce DecisionRecord with requested
tools, evidence refs and selected versioned Skill refs. Their current roles and
permissions remain unchanged. Curator is a ROLE.md contract only. Human approves
skills; no agent may promote itself or modify task/physics truth through a Skill.

MemoryRecord is a small future index contract, with no SQLite/vector/embedding
implementation. Skill retrieval filters metadata and does not execute tools.
See [library admission and usage](../skills/README.md). No LLM integrated.

Regenerate exported schemas with `python -m tools.export_contract_schemas`.
