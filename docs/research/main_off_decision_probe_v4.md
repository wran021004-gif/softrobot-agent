# Main-Off v4: deterministic analysis binding, offline validation

## Outcome: C — real decision capability remains uncertain

On 2026-10-28, the engineering interface passed focused offline validation, including actual Strands tool registration and a scripted correction through Mock HTTP. **No live DeepSeek request was authorized or sent. No mathematical or physical worker, NMPC, PPO, or formal Study ran.** The task explicitly requires a new independent Provider grant; exhausted v1-v3 grants were not reused.

The baseline and remote branch both resolved to `b5d82ad2d50ed352271afc8aef07ef1f264403c6`. Validated implementation commit: `f5c1a1a0bed296adcfcc5dd3547b4152ef43cbd0`, on `codex/english-native-decision-brief`, in `.worktrees/english-native-decision-brief`. That worktree was clean after the implementation commit; this report is a separate documentation follow-up. The final documentation commit and push status are identified in the delivery message. The unrelated `feat/gvs-dynamics` worktree and its untracked work were preserved. Historical Stores were opened read-only; new offline fixtures used independent run IDs.

## Interface and ownership

New frozen configurations explicitly opt in with `research_decisions.analysis_interface = "bound_scientific_variables_v1"`, alongside `architecture = "english_decision_v1"`. Existing configurations, including the pending fresh Study, retain their original interface. The resolver rejects unknown interface versions. No Store was silently migrated.

Changes remain within existing owners:

- `agent.py`: existing selected-method Schema gains a scientific-variable projection; one binder constructs the full request, persists provenance, validates it, and calls the unchanged dispatcher.
- `task_constraints.py`: original method views gain selected-method operating-point guidance and verified source navigation.
- `contracts.py`: point restrictions are shared between discovery and full Pydantic validation, preserving legal scientific meanings. A direct comparison confirmed the **entire full `AnalysisRequest` JSON Schema equals the baseline Schema**.
- `config.py`: freezes the opt-in version; `research_context.py`: exposes guidance through the existing selected-method detail query without expanding every L0 method row.
- `main_off_live_probe.py`: independent v4 ID, eight Main/zero Reporter cap, feedback reserve, explicit live-authorization argument, original dependency guard inspection and no-worker interception.
- `test_bound_analysis.py`: six focused regressions using a genuine saved-C3 ownership copy and scripted HTTP responses.

The binder obtains the explicit candidate from the last completed diagnose decision, checks candidate ownership, and requires its identity to match the existing method template. It injects the frozen Study's complete protocol and selected registration's operation. Native registrations uniquely bind `model_source=mujoco`; conic registrations bind their existing method discriminator. Reduced controller/GVS/SoRoSim model selection stays with Main. There is no newest-candidate inference.

Main must choose `operating_point`, applicable state/execution/update references, local windows, and method-specific scientific variables. Even a singleton point remains explicit. The schema rejects unrelated parameters and bound-field overrides. Native dynamics exposes only meaningful tension options; short-response methods retain their original response options. No invalid point or missing state is repaired automatically.

`analysis_request_binding` preserves raw input, the full bound object, Provider Schema and each top-level field's source. Candidate provenance points to the settled Plan; protocol provenance names the Study, freeze and original spec field; registration-derived fields point to the candidate's method view. Existing original requests, errors and feedback remain intact. Full Pydantic and original JSON Schema checks precede unchanged `analysis.dispatch()`, whose identity, source, authorization, applicability and budget checks remain authoritative.

## Legal points and scope example

For the settled `native_dynamics_v1` fixture, the actual Provider description exposes:

| Point | Source readiness | Scientific scope |
|---|---|---|
| `standardized_initial_pretension` | Frozen initialization available; no saved source required | Time-zero mechanics; does not diagnose the recorded terminal state |
| `saved_state` | Source selection required; exact checkpoint or owned execution plus interval ID | Selected instant/prefix and actual remaining horizon |

`fixed_input_equilibrium` is absent and remains invalid under the original Pydantic rule. `short_input_response_v1` has the same point restrictions, with its declared short-response horizon and input parameters. Neither is automatically redirected to initialization.

The guide finds the actual owned result `629f68ead132e519aeede8727566481e4fc077eef63cf1c9bcccab87f48b208f` for candidate `e85fc8e3eb57e05bfef71db74885db619ce316f90cb9e9b88dc3e971e01f7543`, canonical task `062de8ca2fd2acaebdbf856ba8fc3420d88c8d3943cfa789c5c9e6f06e486c6b`. Its native trace is `dc2757c649ea6d00786720a1b41c0713a1a17241f4cb7471e9eefa81169c4495`. `native_point()` verifies the interval-zero source binding without replay or integration, and the original trace remains navigable for Main to choose another recorded interval. The program does not select a terminal interval. A measured prefix still needs charged reconstruction if execution is later authorized.

The guide separately preserves method applicability, execution status, raw constraint coverage and limitations. All three Reach/Hold constraints are marked diagnostic with no verified samples for native mechanics. Parameter legality proves no task feasibility, full holding-window compliance, global structural infeasibility or physical acceptance. Saved checkpoints not enumerated in navigation still require original source admission; no checkpoint is invented. Reduced saved-source admission is explicitly reported as not run by the probe when it has not been performed.

## Offline results and retained evidence

[Offline validation evidence](../../evidence/main_off_binding_v4/offline_validation.json) preserves actual mocked Provider Schema, original scripted responses, request/response references, raw and bound requests, validation feedback and interception outcome. The backing isolated Store is `runs/research/bound-analysis-offline-0badf1e7f4`. All responses and usage there are **test fixtures, not live Main observations or billed Provider usage**.

The Mock HTTP sequence used a real settled read-only diagnosis with `native_dynamics_v1` selected by the fixture:

1. Scripted Main submitted `{"operating_point":"fixed_input_equilibrium"}`. The binder preserved it, injected identities and protocol, and the original Pydantic check returned `NATIVE_ANALYSIS_REQUIRES_EXACT_STATE_OR_FROZEN_INITIALIZATION`.
2. The next actual SDK request contained that error. Its scripted response submitted `{"operating_point":"standardized_initial_pretension"}`. The program did not edit the first request or choose this correction.
3. The corrected request passed selected Schema, original full JSON Schema, Pydantic, candidate/protocol/model binding and deterministic native applicability checks. The next SDK request contained `probe_only_not_executed`; the scripted final response acknowledged that nothing had been calculated.

The rejected binding audit is `2735a2e9afae638495ab725b639926f979693f0263b66fa95fcf98b05cd269eb`; the corrected audit is `c679ae7a877314674aa1e72645e380b7826630e49339810a1f05456421bc0462`. The exported full requests include the original candidate object and complete frozen protocol; Main supplied neither. Raw requests, both wire checks and Pydantic results are retained rather than represented as a corrected model success.

The original scientific guard returned `DEPENDENCIES_CHANGED_COMMIT_AND_MIGRATE_WITHOUT_RESETTING_COSTS`. The historical eight-dependency mismatch was retained. Full historical scientific admission was **not run or passed**. The probe ledger had zero backend and worker limits and zero usage; process launch was also trapped in the HTTP regression. No numerical result was produced.

Six new binding tests plus ten existing targeted tests passed: **16 distinct passing tests**, not a full suite. They cover rejection of frozen overrides, absent decisions/ownership, incompatible method fields, real SDK Schema projection and feedback, original math admission/invalid states/windows, legacy request serialization, saved-snapshot Schema restoration, SELECT full-read admission and STOP citation coverage. The pre-send cap regression additionally confirms a reserved feedback turn is rejected before any production ledger charge; Reporter and ninth-request sends are blocked. Restore-only recovery sent nothing.

Commands used the installed `.f3-prestudy-env/Scripts/python.exe -m unittest` with these targets:

```text
tests.research.test_bound_analysis
tests.research.test_s127_math_admission
tests.research.test_mujoco_analysis.NativeAnalysisTests.test_native_source_and_legacy_request_identity
tests.research.test_request_boundary_handoff.RequestBoundaryHandoffTests.test_new_requests_refresh_query_schema_after_old_snapshot_verification
tests.research.test_request_boundary_handoff.RequestBoundaryHandoffTests.test_selected_method_changes_actual_provider_schema
tests.research.test_s125_contract.S125ContractTests.test_settled_diagnosis_exposes_actual_candidate_method_schema
tests.research.test_s129_agent_reporting.AgentReportingTests.test_selected_method_requires_settled_diagnosis_and_matching_candidate
tests.research.test_s129_agent_reporting.AgentReportingTests.test_english_selection_requires_full_read_not_summary
tests.research.test_s11_decision_context.DecisionContextTests.test_stop_coverage_and_display_paths_remain_strict
```

One additional existing C1 test failed at `test_c1_method_context.py:142`: it expects an external-force case to be unsupported, whereas the baseline native assessment now supports it and returns `requires_parameters`. Running that same test with **unmodified baseline `task_constraints.py` loaded in memory reproduced the identical failure**. This is an existing stale expectation, not a v4 binding regression; neither scientific support nor the test was changed to manufacture a pass. Initial test-harness restore errors were fixed by applying the same probe guard to restore-only verification; the final relevant tests pass. `git diff --check` passed. Invoking the live CLI without an authorization argument stopped before credential loading or sending.

## Provider cost and request reserve

Live requests: **0 Main, 0 Reporter**. Live tokens, cache usage and incurred Provider cost: zero for this task. No real Main hypothesis, scientific-variable request, correction or feedback interpretation was observed in v4.

For the same selected native method, independently serialized Schema bytes changed from **3,791 to 4,507** (+716) because legal-source/coverage guidance and conditional source rules exceed the removed constants. This measures Schema bytes only. The three mocked wires were 45,355, 46,956 and 51,369 bytes; their hard-coded 30 prompt/15 completion tokens are fixtures and must not be used as a cost estimate. Finish reasons were `tool_calls`, `tool_calls`, `stop`. Exact request IDs and raw references are in the evidence export. No live round-count or total-flow cost improvement is established.

The separate v4 live scope, if explicitly granted later, is at most eight Main requests, zero new Reporter calls, zero automatic retries and zero workers. The script checks caps before ledger reservation and again at transport. If seven Main calls have occurred without analysis feedback, it stops with `PROBE_FEEDBACK_TURN_RESERVED_NO_SEND`, records insufficient evidence and leaves the final allowance unused. If the first analysis occurs on call seven, call eight can process its actual feedback. Earlier feedback similarly reaches subsequent decisions. This does not force Main to choose mathematics or a particular method. Native source reconstruction, numerical solves and independent physics remain forbidden even for a fully typed request.

## Decision assessment and readiness

| Layer | v4 conclusion |
|---|---|
| Understand the saved task failure | Not newly observed in a real Main request; prior reports remain historical evidence |
| Evidence-supported falsifiable hypothesis | Not newly observed; no scientific reasoning is inferred from scripted fixtures |
| Autonomous mathematical method choice | Not tested live; the offline fixture selected the method |
| Scientifically meaningful legal point | Legal initial point tested offline; it does not answer terminal braking capability |
| Main scientific variables | Scripted invalid and valid inputs preserved; genuine Main performance unknown |
| Frozen-field binding | Verified offline against the settled candidate, registration and frozen Study |
| Complete original request contract | JSON Schema and Pydantic passed for the corrected fixture |
| Original scientific admission | Historical dependency guard rejects; full scientific admission not established |
| Correction from feedback | Wire plumbing verified with scripted correction; real Main adaptation unknown |
| Mathematical computation | **No** |

No new live scientific statements exist to audit for causal overclaiming. The prior structure/control confound and the inability of a local diagnostic to establish global structure infeasibility remain unresolved. The mocked initial-state request cannot count as a scientifically sufficient terminal-state experiment. The final mocked acknowledgement tests feedback delivery, not real scientific understanding.

**Do not enter the formal two-condition cold-start Study yet.** First obtain a new independent Provider-only grant and observe autonomous method/point selection plus at least one real feedback decision using this interface. Preserve a C outcome if Main chooses another reasonable direction or the finite budget cannot complete the chain. Separately resolve/migrate historical scientific dependency identities through the existing mechanisms before claiming execution readiness; this provider-only probe cannot grant it. The pending fresh Study and all formal research allowances remain untouched.
