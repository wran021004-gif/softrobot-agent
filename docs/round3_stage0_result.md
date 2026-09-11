# ROUND 3 STAGE 0 RESULT

**PASS — Task Contract Consolidation complete.** No optimizer, feedback controller,
Agent runtime, physics change, new permission system or artifact subsystem was added.
No commit or push was performed.

Audited baseline: branch `feat/round2.5-gate-benchmark-contracts`, HEAD
`ce2dd2d` (`feat: formalize gate semantics and benchmark contracts`). The workspace
was clean before this stage. Existing numerical authority and directory layout remain
in place. See [TaskContract documentation](task_contract.md).

## STAGE RESULTS

| Stage | Result | Evidence |
| --- | --- | --- |
| 1. Audit | PASS | Existing sources identified in the map below; no truth migration |
| 2. Schema | PASS | schemas/task_contract.py and exported schemas/json/task_contract.schema.json |
| 3. Eight concepts | PASS | Goal through Gate policy are located through explicit references |
| 4. reach_free | PASS | tasks/reach_free/contract.yaml, FROZEN, existing tendon_v1 registration |
| 5. reach_window proposal | PASS | proposals/benchmark/reach_window_v1/contract.yaml, approval and exact initializer still unresolved |
| 6. Development fixture | PASS | tests/fixtures/reach_window_dev/contract.yaml, DEVELOPMENT_ONLY |
| 7. Resolver | PASS | load_task_contract / resolve_task_contract; source, identity, evaluator and status consistency checks |
| 8. Harness | PASS | Contract sources/settings/evaluator consumed; existing CLI and candidate input retained |
| 9. Artifacts | PASS | Exact manifest, compact resolved index, run/provenance identity and source archive hashes |
| 10. Trace | PASS | Existing event types; task_contract_resolved precedes task/environment validation |
| 11. Agent contracts | PASS | Engineer, Diagnosis and Coding role documentation updated; Human retains promotion authority |
| Focused tests and regression | PASS | 6 new focused tests; full suite 92/92 with real MATLAB enabled |
| Documentation | PASS | README, task/proposal/tool documentation, docs/task_contract.md and this report |

## TASK CONTRACT MODEL

TaskContract is an immutable, reference-only Pydantic manifest. It binds contract
identity/type/status to task, environment, initial condition, grammar, evaluator,
acceptance, run/simulator settings, execution protocol, Gate policy/mapping, physics
sources and optional benchmark registration. The existing environment XML is linked
as a representation checked against EnvironmentSpec.

It contains no target, tolerance, window geometry, gravity, optimization bounds,
physics constants or concrete DesignSpec. The deterministic baseline candidate at
configs/design_tendon_arm.yaml is an independent run input, not frozen task truth.

References starting with `./` are package-relative; other paths are repository-relative.
Executable resolutions hold typed TaskSpec, EnvironmentSpec and settings plus grammar
and callable references in memory. The serialized view contains only metadata, paths,
hashes and unresolved markers. It does not duplicate those loaded objects.

The proposal resolves its candidate source references and evaluator applicability for
inspection, retaining approval markers. It deliberately has no executable typed
task/environment/evaluator view. Harness rejects its execution before numerical tools.
The existing V1 initialization, physics, protocol and Gate implementations are explicitly
supported; substituting an unimplemented source is rejected rather than ignored.

TaskContract defines the problem. DesignSpec proposes a solution. RobotIR defines the
instantiated robot. Physics Contract defines model semantics. Artifacts record what happened.

## SOURCE-OF-TRUTH MAP

`<package>` denotes the selected task package; proposal sources retain their candidate names.
Ownership below describes authority over definitions, not who may silently edit a frozen run.

| Concept | Authoritative source | Referenced by TaskContract? | Duplicated? | Owner |
| --- | --- | --- | --- | --- |
| Goal | <package>/task.yaml; proposal candidate_task.yaml | Yes: task_source | No | Human |
| Environment | <package>/environment.yaml; proposal candidate_environment.yaml | Yes: environment_source; XML is representation only | No | Human |
| Initial condition | tools/mujoco_tools.py existing MjData initialization of the compiled robot; proposal candidate_acceptance.yaml pending initial-state decision | Yes: initial_condition_source | No | Human; deterministic tool implements the approved model |
| Design envelope | capabilities/robot_families/tendon_driven_continuum/grammar.yaml | Yes: design_grammar_source | No | Human |
| Metrics | metrics/reach.py evaluate_reach | Yes: evaluator and resolved implementation hash | No | Human-owned evaluator definition |
| Acceptance | task.yaml tolerance/explicit acceptance; schemas/task_spec.py existing development defaults; proposal candidate_acceptance.yaml | Yes: task_source / acceptance_source | No | Human |
| Evaluation protocol | configs/run.yaml seed/steps; configs/simulator.yaml timestep; tools/harness.py single attempt/no retry; tools/mujoco_tools.py deterministic steps without random sampling | Yes: settings, protocol and initialization sources | No | Human; Harness/tools execute |
| Gate policy | schemas/gate.py actions and tools/harness.py existing HARD / SCREENING / CANONICAL mapping; thresholds remain in their original sources | Yes: gate_policy_source / gate_mapping_source | No | Human; deterministic Gate implementation |
| Physics | Existing five physics_contracts/*.md references plus legacy_v1_surrogate.yaml | Yes: physics_contract_sources | No | Human |
| Concrete DesignSpec | Independent design_path input, default configs/design_tendon_arm.yaml | No | No | Human baseline candidate; future Engineer may propose within approved grammar |

The formal benchmark association uses the unchanged benchmarks/tendon_v1.yaml.
FROZEN does not prohibit an explicit Human-approved future version such as reach_free_v2;
it prohibits silent mutation by run participants. No version service was introduced.

## CONTRACT STATUS

| Task | Contract ID | Status | Formal benchmark? |
| --- | --- | --- | --- |
| reach_free | reach_free_v1 | FROZEN | Yes, existing tendon_v1 |
| reach_window proposal | reach_window_v1_proposal | PROPOSED_NOT_APPROVED | No; exact values, acceptance and initial configuration remain unapproved |
| reach_window_dev | reach_window_dev_v1 | DEVELOPMENT_ONLY | No; software capability fixture only |

No proposal was promoted and no benchmark registration was changed. A development
environment cannot be resolved as FROZEN. A benchmark-bound contract must match its
registered frozen task/environment sources and evaluator. These checks enforce source
consistency; Human approval remains the existing repository authority, not a new authentication system.

## HARNESS INTEGRATION

The existing `python examples/run_reach_pipeline.py` and `--task-package` entry remain.
When contract.yaml exists, Harness resolves it first, snapshots the manifest and all
referenced files, checks archived bytes against resolved hashes, and uses the referenced
task/environment, grammar, evaluator and run/simulator settings. Policy/protocol identity
is checked against the existing implementation. DesignSpec stays a separate argument.

Each contract run records task_contract.yaml, task_contract_resolved.json, and
task_contract_id/status/hash in run.json and provenance.json. gate_summary.json carries
contract scope. source_snapshot.zip retains referenced source bytes at their repository
paths, alongside the existing task/environment and numerical artifacts.

Trace uses existing ARTIFACT_CREATED and SPEC_VALIDATED types, including
`task_contract_resolved`, linked to both contract artifacts. Verified order:
RUN_STARTED -> task_contract_resolved -> task_loaded / environment_validated ->
design/capability/RobotIR and existing downstream execution.

Packages without a contract keep the explicit `task_contract_compatibility` path,
marked DEVELOPMENT_ONLY with no fabricated contract ID. A test that copies and modifies
the frozen package now removes its copied contract to avoid claiming frozen membership.

## AGENT BOUNDARY

- Engineer reads TaskContract, Design Grammar, Capability Registry and future retrieved
  Memory/Skills. It can propose DesignSpec within approved bounds; it cannot edit frozen truth.
- Diagnosis reads the saved contract, artifacts, trace and diagnostics. It cannot override
  canonical success, reinterpret the benchmark or turn screening predictions into acceptance.
- Coding implements approved consumers and may not promote PROPOSED_NOT_APPROVED to FROZEN.
- Human owns definitions, approval, promotion and explicit contract version changes.

No LLM or Agent runtime was connected. No CandidateFinding or Skill was generated.

## REGRESSION RESULT

Existing gate/trace baseline: **15/15 passed** (3.609 s). New focused tests plus existing
gate/trace tests: **21/21 passed** (4.945 s). Full suite with
`SOFTROBOT_TEST_MATLAB=1`: **92 tests passed, no skips**, 54.921 s.
The six focused tests cover resolution, proposal status, development/frozen separation,
identity/evaluator mismatch, Harness artifacts/regression, and actual dispatch of referenced
settings/evaluator. Existing schema export drift checks also passed.

Two additional real MATLAB + MuJoCo runs retained final evidence:

| Run | ID | PCC predicted error (m) | MuJoCo actual error (m) | Final status |
| --- | --- | --- | --- | --- |
| reach_free | 20260911T101003_808679Z_d282bc15 | 0.08714456960728613 | 0.17116166894090315 | TASK_FAILED |
| reach_window_dev | 20260911T101011_362815Z_5c41864c | 0.08714456960728613 | 0.17116166894090315 | TASK_FAILED |

**Numerical change: none.** Compared with Round 2.5 retained runs
20260911T094026_035046Z_832778ce and 20260911T094033_672395Z_5c868455 respectively,
all prior metric fields were exactly equal, excluding the descriptive comparison_context.
For each pair, task.yaml, environment.yaml, robot.xml, robot_ir.yaml, physics.yaml,
controller.json, tendon_command.json and simulation_state.json were byte-identical.
Window development clearance/contact/crossing metrics and acceptance outcomes were unchanged.

| Evidence check | reach_free | reach_window_dev |
| --- | --- | --- |
| Referenced source entries checked against archive hashes | 19 | 18 |
| Registered artifact hashes verified | 32 | 35 |
| Trace events | 73 | 86 |
| Contract SHA-256 | 93633233ade80cfae7d6b4a535ab94fc7d655021c7826a2266c4375ace31497c | 99d05514238c3aa22b2bbb2a941e3643613bec232247e597504870ac209f39a8 |

Source checks count reference entries; repeated source paths are deduplicated in the archive.
Task/environment numeric files, grammar, physics contracts, controller/configuration files,
benchmark registrations and numerical expected values were not changed.

## READY FOR ROUND 3 OPTIMIZATION?

**NO**

- Human has not approved optimization variables and their bounds/constraints. The existing
  grammar keeps optimizable=false, bounds unset and scientific_status=human_approval_required.
  Approval must define the permitted design search domain before optimization can run.
