# Milestone 0 interfaces and Milestone 1 inventory

Stage 3.54 keeps the existing store, public execution contracts, scientific task,
and bounded provider loop. The v5 model adapter presents exact scoped aliases,
accepts a small revision, and materializes the existing diagnostic report. The
final response v3 separates recommendation acceptance from controller selection.
Historical adapters and long-handle readers remain available.

| Interface | Contract/module | Producer → consumer | Milestone 1 gap or connection |
|---|---|---|---|
| Fixed task and acceptance | `SessionInput.task`, `evaluate.reach`, `campaign_metrics`, `RANKING` | Human-owned task and evaluator → execution, comparison, model feedback | Connect one task reference to a compact working-state view; keep official terminal reach distinct from sampled holding and computation. No new acceptance criteria. |
| Candidate and effective identity | `CandidateInput`, `prepare_improvement`, `actual_diff`, `execution_scope` | Registered candidate builder → execution host, profile, final selection | Expose effective scientific scope and required rebuild impact together. Candidate preparation and executed configuration may have different artifact identities; preserve their explicit link. |
| Execution and evaluation | `ToolReceipt`, `BackendResult`, `complete_execution`, `ControlEvidence` (see `tools/execution_completion.py`) | Backend/evaluator/profile → sealed completion stages and diagnostic feedback | Present completion state, pending/failed stage and next permitted continuation together. Existing stages already prevent duplicate simulation and charges. |
| Scoped evidence | `diagnostic_facts`, `diagnostic_revision.ensure_aliases`, adapter v5 | Successful read or explicit handoff → context-local alias table → exact selector validator | Add a compact reference to the current evidence scope in a working-state view; do not merge private role catalogs. Aliases are append-only within host-bound scope; original source, pointer, value, units and long handle remain in the catalog. |
| Diagnostic revision | `CompactRevision` → `InventoryDiagnosisSubmission` v2 | Model delta + accepted initial report + current feedback → existing submit validator | Expose accepted revision and its initial-report/feedback references together. The small input is archived as a draft; materialized facts retain exact provenance. Numerical validity does not certify interpretation. |
| Final design decision | `FinalDesignResponse` v3 | Design model → `respond_workflow` and accepted handoff | Feed explicit disposition and selected candidate into the next authorized work item. Acceptance records intent only; no automatic baseline replacement or execution. |
| Working state and budgets | `Store.session.state`, `phase_budget`, `Store.remaining`, `recovery_status`, `diagnostic_work`, completion stages | Trusted host and operation receipts → provider context and coordinator | Provide a small read-only projection of existing phase, accepted products, pending operation and remaining budgets. Do not create another state store. |
| Parameter and controller capabilities | Candidate builder payload, `policy.editable`, `control_grant`, `REACH_WEIGHT_PATHS`, registered extension capabilities, `GVSTrajectoryParameters` | Registered schemas and human grant → decision schema and builder | Existing metadata covers legal values and implementation identity; it lacks a complete per-field invalidation/rebuild map. Add only demonstrated mappings for supported changes. Unavailable capability and unauthorized work remain separate from missing/unread data. |

## Rebuild boundaries

The current two-weight grant changes only controller recipe values. The existing
complete execution constructs a candidate-specific controller/solver; it reuses
the fixed task and robot definition. A frozen local analysis result must not be
silently rebound to another effective configuration. Geometry, materials,
discretization, basis, dynamics model, actuator settings and numerical methods
are outside this grant. Their registered schemas and compilation paths exist,
but this milestone does not validate their rebuild dependencies or authorize
changes to them. Runtime/hardware and continuous-time performance are not
established by these sampled MuJoCo experiments.

The next concrete Milestone 1 target is a read-only working-state adapter joining
the existing task, effective candidate, accepted decision, completion stage,
evidence scope and remaining budget references. It should include an explicit
rebuild requirement for the two supported controller weights and report other
dependencies as unmapped. This inventory does not complete Milestone 1.

## Correction and scope rules

`F1` resolves only against the current host-bound alias table. Existing v1 scopes
keep their original `F001` spelling; new scopes avoid insignificant leading zeros.
Reordering a
catalog never reassigns an alias. Foreign, unknown, ambiguous and mistyped
references are rejected without prefix repair. Cross-role transfers explicitly
carry accepted facts or current feedback, never another role's reading history.

A rejected draft stays unaccepted. The same native function accepts a bounded
list of exact JSON-pointer replacements/removals, or a full resubmission. The
assembled result goes through schema, reference, inventory and report checks.
Corrections consume ordinary attempts, tools and time under the unchanged
four-total/two-consecutive recovery policy. Submit-only revision instructions
supply references directly. Native invocation names are generated from the same
mapping as the advertised functions.

Saved suffix grants are supplementary validations, not completed Stage 3.53
conversations. Their historical source bytes and failed outcomes are immutable.
Fresh runs are gated on both suffixes, with one candidate execution per fresh
organization and no baseline replay.

The dual suffix exposed a decoder defect in the documented draft-root pointer
form `/arguments/...`. The repair supports that explicit root as well as paths
relative to business arguments, reports missing profile citations before tool
execution, and distinguishes report fact IDs from evidence aliases. The recovery
entry point is restricted to the exact failed saved response. It records changed
implementation fingerprints and immutable prior outcomes, then uses the normal
pending-tool path without a new revision provider call. Phase ceilings, started
usage, total corrections and all original receipts remain unchanged. Only a
successful business call resets consecutive corrections, under the existing rule.
