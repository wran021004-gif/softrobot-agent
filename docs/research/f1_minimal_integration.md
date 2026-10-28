# F1 minimal research integration

## Baseline and selected changes

The independently verified remote heads were:

| Branch | HEAD |
|---|---|
| `integration/research-next` | `455ec55347ce6ab05cfbf71ad439044e9db77aca` |
| `codex/english-native-decision-brief` | `7a327eb4023c08a28e8106e2029465ed8ab88b2a` |
| `research/base-only-benchmark-feasibility` | `314f75a4971e0a9e4521fe79ddf744ff71de61e2` |

Both side branches descend from the remote integration head. The existing local
integration worktree additionally contains `618bb16b2`; its scientific archive
was not imported. Work uses a new `codex/f1-minimal-integration` worktree based on
the remote integration head. No branch merge was performed.

Selected code patches:

- `618bb16b2`: only generation error feedback and exact V2 section guidance.
- `5bf126408`, `08da01910`: retain incomplete computation/diagnosis facts.
- `661ee842c`, `fda58968e`, `705b5049a`: Windows session paths and verified
  incomplete-response inspection/recovery prerequisites.
- Runtime changes between `08da01910` and `7a327eb40`: compact English decisions,
  purpose-specific frozen roles, selected analysis binding, on-demand tool
  schemas, bounded recent Trace, Store Recall, automatic verified Handoff,
  feedback delivery and formal Main full-read credit. Also import the matching
  `ModelConfig` fields and `jsonschema` dependency declaration.
- `983197a0e`: explicitly versioned Base-only rule, route validation and legal
  mixed-search generation; three already-public Base-only FamilySpace files.

Conflicts in `agent.py`, `contracts.py`, and `research_context.py` were resolved
at the function/hunk level against V1/V2 interfaces. V3 physical routing, V3
search algorithms, paired decision experiments, owner campaign drivers,
historical Study configurations and scientific evidence were not imported.
The retained generator/search code remains the integration implementation with
the Base-only rule, section guidance and incomplete-result fixes applied.

## Runtime ownership and compatibility

| Files | Responsibility |
|---|---|
| `agent.py`, `__main__.py` | Existing Main conversation, selected schema and execution boundary |
| `config.py`, `contracts.py`, `schemas/platform.py` | Explicit frozen opt-ins and existing typed requests |
| `research_context.py`, `provider_context.py`, `session_handoff.py` | Compact decisions, Trace/Recall and verified delivery/recovery |
| `reporter.py`, `experience.py`, `evidence_policy.py`, `feedback.py`, `task_constraints.py` | Existing report, evidence, experience and method boundaries |
| `analysis.py`, `diagnostic.py` | Incomplete-result projection without changing original scientific records |
| `family_space.py`, `generated_serial.py`, `mixed_moves.py`, `search.py` | Base-only validation/generation and compatible mixed search |
| `core.py` | Existing evidence read admission plus derived-method navigation hint |

Existing tasks, evaluators, physics, budgets, grant checks, Store, EvidenceRef,
candidate identities and control-source authority are unchanged. No additional
Store, registry, optimizer, Agent, or identity-hash mechanism was added.
The complete resolved legacy BF5 and native Reach/Hold configurations were
compared with the original resolver and remained equal.

New Studies must explicitly choose their frozen policies. For example, inside
the existing `research_decisions` object:

```json
{
  "architecture": "english_decision_v1",
  "role_policy": {
    "version": "research_roles_v2",
    "main": {"thinking": "disabled", "reasoning_effort": "none"},
    "reporter": {"thinking": "enabled", "reasoning_effort": "low"}
  },
  "analysis_interface": "bound_scientific_variables_v2",
  "conversation_policy": {"version": "recent_round_trace_v1", "trace_limit": 8},
  "tool_schema_policy": {"version": "on_demand_tools_v1"}
}
```

This fragment extends the existing version/history/mathematics/control_seeds
fields; it is neither a complete Study nor execution authorization. Choosing
Base-only also requires an explicit FamilySpace file. Old frozen configurations
are not migrated. Histories, evidence inventories and full tool schemas remain
outside ordinary Main requests; formal SELECT reads still deliver the exact
whole result and preserve original admission and receipt checks.

## Main-Off error regressions

| Observed error shape | Resolution |
|---|---|
| diagnose omits `decision.selected_candidate` | Reuse the v2 focused original Plan schema, `admit_decision` and concise repair hint. No candidate is inferred. |
| `view=fields` omits `fields` | Existing EvidenceQuery validator, conditional schema and compact error are sufficient. |
| raw/full `/methods` against a candidate | Add a navigation hint to the existing `mathematical_capabilities` derived view after verifying that query is legal. The failed request remains failed; Main must resubmit. |
| diagnose mistaken for executed analysis | Reuse the explicit tool description and selected-method schema. diagnose records intent; only a separately admitted `research_analysis` executes science. |

The consolidated offline regression reproduces the saved v6 error shapes with
synthetic candidate/evidence identities. A corrected diagnose still produces no
analysis result. No real Provider rerun was performed; whether Main actually
uses the feedback efficiently remains unverified.

## Mathematics to Native control

The existing path is already connected:

`research_analysis(task_capability, capability_method=sampled-affine-conic-minimax-v1)`
→ `initialize_control(method=capability_sequence, response_evidence=...)`
→ `mujoco_direct_control_v1(control_optimization.source=...)`
→ independently admitted `physical_replay(candidate, source)`.

`capability_seed` consumes a registered current-Study computed SOCP result for
the same candidate and frozen implementation/protocol. It checks the original
candidate, effective task, model, source, tendon order, N input units/bounds,
zero initial deviation, complete original time grid and independent affine
witness replay. It creates the existing explicit schedule with separate
execution-model provenance, `task_acceptance=unmeasured`, and no inherited
acceptance. Native admission rechecks the executable source and physical
binding. It does not automatically transfer another candidate's schedule.
No code was changed in this path and no mathematical/physics worker ran.

| Benchmark conditions | SOCP trajectory initialization | Native sequence search |
|---|---|---|
| M1 multi-target Reach/Hold | Supported per candidate/task condition for the declared sampled affine problem; each condition needs its own bound source | Supported; joint independent acceptance remains required |
| M2 full COM external-force conditions | Not supported by the current reduced/GVS full-physics model; a force-free substitute is not equivalent | Supported under the existing frozen world-COM force contract |
| M3 Reach/Hold draft | Supported for the declared sampled affine problem; formal protocol approval remains separate | Supported; draft status unchanged |
| M4 timed position tracking | Supported for aligned sampled position constraints; local affine validity remains conditional | Supported; full physical timed tracking still required |
| M5 position plus directed tool axis | Not supported for the complete task by current affine/SOCP methods | Supported with both real position and axis signals |
| M6 loaded oriented tracking plus no contact | Not supported for the complete task by current affine/SOCP methods | Supported as a sampled search proxy; rigid-tool and per-step contact acceptance require independent replay |

No row asserts that a useful SOCP trajectory exists for every generated
candidate. Saved-state partial windows, mismatched grids/channels/bounds and
other-candidate results cannot silently become full-task seeds. A bounded
mathematical task-failing sequence can remain a diagnostic seed under the
existing rules; it is not a physical pass. Main chooses whether any method is
worth its budget. Reach-only nonlinear T1/T2 coverage must not be extended to
M4/M5/M6 merely because direct Native sequence control supports them.

## Experience and experimental separation

Six short owner-local cards were extracted against the original Store events,
with the existing review manifests as indices. They distinguish incomplete
execution, valid task failure, finite search stagnation and strict near-threshold
failure. The cards and source extracts remain ignored under the new worktree's
`runs/f1-private/`; they are not committed or registered with runtime retrieval.

The existing public procedural index and `experience_retrieve` already provide
a non-sensitive search/read example, with exact read receipts and
`experience_disposition` bindings. Its focused regression passed. No new
experience database or runtime policy was added and no six-card startup
injection occurs. Task-specific cards are excluded from independent M1–M6
blind studies. Experience-assisted experiments require an explicitly separate
configuration/context and actual read/adoption accounting. A clean checkout,
new Store and enforced readable-file/tool scope must exclude owner runs, cards,
winner reports and this chat; `.gitignore` alone is not isolation.

## Focused offline validation and readiness

- 19 reused Base-only tests through `tests.research.stage0_no_integration`:
  legality, legacy serialization, mixed/native search with mocked results,
  multi-condition resume and SELECT, BF5/BF6 replay-read-SELECT. All passed;
  forbidden execution attempts were empty.
- 13 initial directed tests: nine reused recent-round tests, two request-boundary
  handoff/full-read tests, one existing experience exact-read/disposition test,
  and the consolidated F1 error regression. All passed in 40.127 s.
- Two follow-up tests: the adjusted exact v6 `/methods` error shape and one
  reused read-only confirmed-truncation admission test. Both passed in 3.500 s.
- One opt-in configuration test passed after discovering and importing the
  matching ModelConfig fields. It resolves the combined Base-only/Main-Off M5
  configuration, preserves task and budgets, and creates no Store. Two complete
  legacy resolver comparisons also passed. `git diff --check` passed.

There are 34 distinct passing test cases and 35 successful case executions
(the error test was rerun only after its request shape was corrected).
No full-repository suite, stress test or live scientific execution was run.
Mock SDK replies and synthetic acceptance fixtures are engineering evidence,
not autonomous scientific decisions or new physical passes.

Actual resources: Provider 0, Reporter 0, mathematical workers 0, physical
workers 0, MuJoCo integration 0, NMPC/PPO 0, formal Studies 0.

M5 has the engineering interfaces needed for a new autonomous Study. However,
the existing public BF5 leaf deliberately retains zero Provider requests and
`PENDING_EXPLICIT_APPROVAL`; this integration does not turn it into an executable
grant. A new uniquely identified Store, explicitly frozen finite Main/scientific
allowances and authorization, matching runtime/interpreter, and blind versus
assisted read scope are required before launch. M1/M2 joint design can use the
same integrated interfaces, preserving separate controls for each condition and
the original common-structure joint SELECT rules. No additional demonstrated
code blocker remains in the checked paths; full real execution admission and
scientific outcome are untested here. M3 also needs formal protocol approval.

Main's hypothesis quality, correct method choice, response to failed evidence,
efficient tool correction, actual scientific completion and SELECT/STOP behavior
must be assessed inside a separately authorized real Study. Passing offline
tests does not establish those capabilities. Stop after this delivery; do not
automatically launch or continue a Study.
