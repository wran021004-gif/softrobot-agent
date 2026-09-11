# ROUND 1.5 RESULT

Round 1.5 implements fine-grained execution traces, evidence-level findings,
machine-readable Skill contracts, deterministic admission/versioning/retrieval,
and future Memory/Curator contracts while preserving the Round 1 numerical baseline.

Branch: `feat/round1.5-trace-skill-infrastructure`, based on
`feat/round1-physics-diagnostics` at f7baa01. No commit or push performed.

Primary evidence: [run manifest](../runs/20260911T071524_339902Z_141b473c/run.json),
[fine-grained trace](../runs/20260911T071524_339902Z_141b473c/trace.jsonl),
[diagnostic summary](../runs/20260911T071524_339902Z_141b473c/diagnostic_summary.json).
Runs stay local under the existing ignored runs/ directory. This report is a
summary; the referenced artifacts and their manifest hashes are the evidence.

## STAGE RESULTS

| Stage | Result | Implementation | Verification |
| --- | --- | --- | --- |
| 1. Audit | PASS | Audited flat trace, ToolResult persistence, source snapshots, manifest hashing, Harness returns, diagnostics and permissions; confirmed branch ancestry | Pre-change suite: 44 passed, 3 opt-in skips |
| 2. Trace schema/storage | PASS | Finite taxonomy, actors, bounded fields, DecisionRecord, JSONL append/seal/read | Schema, serialization, graph, timestamp, size and invalid-input tests |
| 3. Instrumentation | PASS | Actual M0/M1/MuJoCo/diagnostic calls, controller selection/application, capability/spec gates and stage spans | Canonical trace assertions using fixture MATLAB and real MATLAB |
| 4. Validation/provenance | PASS | Unique run-prefixed IDs, active parents, paired completion, resolvable refs, final trace hashes; legacy trace retained | Hash, missing/pointer/escaping reference, failure/early-exit and seal tests |
| 5. CandidateFinding | PASS | Strict observation-only schema and explicit exact-metric extractor/validator | Real canonical proposal and synthetic mismatch/unavailable evidence tests |
| 6. Skill contracts/registry | PASS | Machine-readable schemas, empty directories, catalog link, file-backed revision registry | Candidate, schema, family, registry-layout and empty production tests |
| 7. Admission/versioning | PASS | Real hashed evidence, implemented tools, metric checks, immutable versions, bound validation and explicit Human approval | Unknown/planned tool, mutation/override, missing evidence, borrowed validation, false outcome, negative history and version tests |
| 8. Retrieval | PASS | Exact structured filters, approved default, explicit candidate opt-in, stable status/coverage/version ordering | Exact/no-match, candidate exclusion, category/failure/model/control/tool filters and ranking |
| 9. Future contracts | PASS | Small MemoryRecord; Skill Curator ROLE.md; DecisionRecord and agent integration docs | Contract roundtrips and no fabricated runtime actors |
| 10. Canonical regression | PASS | Real reach_free run, full timeline, evidence-only finding | 8 baseline files byte-identical, four diagnostic metric dictionaries unchanged |
| 11. Full tests/docs | PASS | Architecture, library, agent, Memory and result documentation; exported JSON Schema | 74/74 tests including real MATLAB; git diff --check |

## TRACE ARCHITECTURE

- Artifact: factual numerical results, XML, inputs, final state and diagnostic outputs.
- Trace: execution order, actual actors, parent/child spans and structured gate evidence.
- Memory: future cross-run summary/search index with evidence links; no database.
- Skill: validated reusable strategy for selecting/composing deterministic tools.

Artifact != Trace != Memory != Skill. CandidateFinding bridges observations and
future proposals but is not a reusable strategy. See
[architecture](trace_skill_architecture.md) and [Skill Library](../skills/README.md).

`trace.json` retains the flat Round 1 compatibility contract. `trace.jsonl` adds
64 logical events (41,312 bytes) in this canonical run, with no per-timestep data.
Stage/tool finishes reference their starts; inputs/outputs reference real artifacts.
Both trace files are included among the 29 verified artifact hashes in run.json.

```text
run
  model stage
    MATLAB session
    analyze_workspace
    plan_pcc_reach
  controller selection
  mujoco stage
    compile_mujoco
    run_task
    controller application
  physics/task gates
  diagnostics stage
    compare_model_sim
    check_actuator_limits
    check_tendon_tracking
    inspect_numerics
  MATLAB cleanup
run finished
```

## CANONICAL RUN TRACE

Run: `20260911T071524_339902Z_141b473c`.

| Sequence | Actual event |
| --- | --- |
| 0 | RUN_STARTED |
| 3–5 | Task loaded, environment validated, design loaded |
| 8, 10–11, 15 | Spec gate PASS, capability resolved, grammar gate PASS, RobotIR built |
| 17–19 | Model stage and MATLAB session start/complete |
| 20–22 | M0 analyze_workspace start/complete |
| 23–25 | M1 plan_pcc_reach start/complete; model_task_success=false |
| 26, 29 | Model stage complete; C1 controller selected |
| 31–34 | MuJoCo stage; compile_mujoco start/complete |
| 36–40 | run_task completes with TASK_FAILED; actual control recorded; simulation stage completes |
| 44 | physics_sanity_gate PASS |
| 45 | task_metric_gate FAIL: position_error_m=0.17116166894090315 > frozen threshold 0.01 m |
| 46–49 | Diagnostics stage; compare_model_sim |
| 50–52 | check_actuator_limits |
| 53–55 | check_tendon_tracking |
| 56–58 | inspect_numerics |
| 59–60 | diagnostic_summary.json created; diagnostics stage complete |
| 61–63 | MATLAB cleanup; RUN_FINISHED, TASK_FAILED |

TOOL_FAILED for run_task preserves its formal failed ToolResult. The surrounding
simulation stage completed successfully; task failure is distinguished from an
interrupted or unavailable execution. Gate authority is the frozen TaskSpec and
canonical evaluator. Diagnostics and future agents cannot overwrite the gate.

## CANDIDATE FINDING RESULT

Explicitly extracted and saved
[round1_5_candidate_finding.json](../proposals/diagnosis/round1_5_candidate_finding.json).
The production Harness does not automatically persist findings or propose skills.
Each observation includes a real run ID, artifact path, exact JSON pointer and SHA-256.

Observed:

- M1 predicts task tolerance failure: true.
- Endpoint discrepancy: 0.1841045610291436 m; no approved mismatch criterion.
- Sampled maximum-pull force saturation observed: false.
- Maximum final tendon tracking error: 0.006847228877633504 m.
- Recorded numerical anomaly indicators: empty.

`ruled_out` retains only the recorded lack of sampled maximum-pull saturation and
absence of the inspected numerical indicators. It does not establish correct
actuation, scientific model validity or stability.

Unresolved: causal attribution UNKNOWN, no validated repair, and no Human-approved
mismatch/tracking thresholds. This is **not a Skill**; it recommends no solution.

## SKILL LIBRARY STATUS

| Collection | Current skill count |
| --- | --- |
| candidate | 0 |
| approved | 0 |
| deprecated | 0 |

Fixture skills are confined to tests/fixtures and temporary test libraries.
Empty approved retrieval is valid and has no effect on the deterministic pipeline.

## SKILL ADMISSION RULES

candidate -> validation -> validated -> Human approval -> approved.

Admission rejects absent/non-finalized runs, missing/tampered evidence, unknown
families/tools, PLANNED tools, nonexistent metrics, undeclared strategy tools,
encoded Human-owned mutation and gate override, and explicit unapproved physics.
Strategies contain no arbitrary execution/result/mutation fields. New physics
requires PHYSICS_ASSUMPTION_REQUIRED/Human review.

Validation records bind skill version and strategy hash to hashed experiment
outcomes. Run/task/robot/seed coverage is checked against real run metadata.
Failed and contradicted experiments remain in append-only revision history.
Approval requires a passed validation and an explicit Human record matching the
reviewed content hash. Strategy/scope changes require a new version; approved
versions can be deprecated without erasing their prior evidence.

The local Human entry point assumes a trusted caller, not an authenticated service.
Arbitrary natural-language scientific claims still require Human review. Skills
grant no permissions, and no autonomous executor or automatic approval exists.

## RETRIEVAL RESULT

The `fixture_tracking_inspection@1` test fixture demonstrates:

| Query/state | Result |
| --- | --- |
| Candidate, default query | [] |
| Candidate with include_candidates=True | Candidate fixture |
| Explicit fixture Human admission + exact family/reach/TASK_FAILED/M1/C1/DIAGNOSIS filters | Approved fixture |
| Different family/task/failure/model/control/category/tool filter | [] |
| Production registry | [] |

Ranking is deterministic: status, distinct successful validation-run coverage,
version recency, skill ID. No embedding, vector DB or fabricated fallback.

## MEMORY STATUS

Memory DB: **not implemented**.

Memory contract/interface: **implemented and documented** as schemas.memory.MemoryRecord:
bounded run summary, searchable metadata, evidence references. No full trace,
artifact or skill copies are stored in Memory.

## AGENT INTEGRATION STATUS

| Future role | Contractual use |
| --- | --- |
| Engineer | Retrieve DESIGN/MODEL_SELECTION/CONTROL strategies for explicit scope |
| Diagnosis | Inspect Trace and evidence, derive a signature, retrieve DIAGNOSIS strategies |
| Coding | Retrieve CODING_SIMULATION strategies within existing file permissions |
| Skill Curator | Collect findings, propose patterns, request validation, suggest narrowing/deprecation; never approve |

Recommendation -> Agent decision -> normal permission check -> execution.
Only contracts/interfaces are implemented. **No LLM integrated.**

## BASELINE REGRESSION

Compared directly with Round 1 run `20260911T053307_539565Z_13e07e9c`:

| Metric | Round 1 | Round 1.5 |
| --- | --- | --- |
| PCC error (m) | 0.08714456960728613 | 0.08714456960728613 |
| MuJoCo error (m) | 0.17116166894090315 | 0.17116166894090315 |
| Task status | TASK_FAILED | TASK_FAILED |
| Endpoint discrepancy (m) | 0.1841045610291436 | 0.1841045610291436 |
| Maximum tendon tracking error (m) | 0.006847228877633504 | 0.006847228877633504 |
| Observed maximum-pull saturation | false | false |
| Numerical anomaly indicators | [] | [] |

task.yaml, environment.yaml, design_input.yaml, robot_ir.yaml, robot.xml,
tendon_command.json, controller.json and simulation_state.json are byte-identical.
All four diagnostic metric dictionaries are equal after excluding the expected
new comparison_context.run_id. No physical equation, parameter, canonical metric,
frozen input, optimizer authorization or agent permission implementation changed.

## TEST RESULT

Interpreter: `C:\Users\gugugaga\miniconda3\envs\softagent\python.exe`.

| Actual command | Result |
| --- | --- |
| `python -m unittest discover -s tests -q` before changes | 47 total: 44 pass, 3 opt-in skips |
| `python -m unittest tests.test_trace tests.test_skills -q` intermediate | 23/23 pass |
| `python -m tools.export_contract_schemas` | Exported seven JSON Schemas; drift checked by test |
| `$env:SOFTROBOT_TEST_MATLAB='1'` then `python -m unittest discover -s tests -q` | **74/74 pass, 47.775 s**, including all three real MATLAB tests |
| `python examples/run_reach_pipeline.py` | Real canonical run saved; exit 1 for expected TASK_FAILED |
| Direct artifact/diagnostic comparison script | 29 hashes verified; 8 files byte-identical; all diagnostic metrics unchanged |
| `git diff --check` | PASS |

The first sandboxed pre-change test attempt hit Windows access denial in newly
created temporary directories. Normal process/filesystem permissions passed the
same suite. During development a persistent trace handle exposed an abandoned-run
Windows file lock; the writer now closes each logical append. The 20 temporary
directories left by these failed attempts were removed after exact-path checks.
No baseline or expected scientific result was weakened to pass tests.

## OPEN QUESTIONS

None blocks this infrastructure scope. Existing Human scientific decisions remain:
approved model-mismatch/tracking/anomaly criteria, calibrated material/actuator
laws and optimization bounds. The new library intentionally contains no approved
strategy until actual validation and Human approval exist.

## FILES CHANGED

- Trace: schemas/trace.py, schemas/evidence.py, tools/trace_tools.py, tools/evidence.py.
- Skill: schemas/skill.py, tools/skill_policy.py, skills/registry.py, skills/index.yaml,
  empty status directories, capabilities catalog/registry integration.
- Schemas: schemas/finding.py, schemas/memory.py, schemas/json/*,
  skills/schema/*, tools/export_contract_schemas.py.
- Harness: tools/artifact_tools.py, tools/harness.py, diagnostic persistence wrapper
  in tools/diagnostic_tools.py, examples/run_reach_pipeline.py.
- Findings: tools/finding_tools.py, proposals/diagnosis/round1_5_candidate_finding.json.
- Tests: tests/test_trace.py, tests/test_skills.py, tests/fixtures/skill_candidate.yaml,
  additional real MATLAB trace assertions in tests/test_matlab_integration.py.
- Docs: README.md, capabilities/README.md, agents/contracts/README.md,
  agents/skill_curator/ROLE.md, memory/README.md, skills/README.md,
  docs/trace_skill_architecture.md and this report.

No commit. No push.
