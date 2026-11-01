# M1 scientific intent interface repair

The stopped M1 run did not adequately explore the scientific task. This repair
addresses verified interface projections and preparation handoffs, while retaining
the observed model failures and the original scientific execution contracts.
Interface validation is distinct from autonomous research success.

## Baseline and evidence

Read-only remote inspection found the preparation branch at
`d89adbcc20347d1bebc66d341260de6cddca9e2f`, U1/U2 at
`bc4ea4c06214a3e77796c9f96c09c695f30bfdcd`, and main at
`2a854280db69425dc50af9012b8da52194a679ee`. The independent worktree and branch
`codex/scientific-intent-interface-repair` start at the actual preparation head.
Neither historical STOP Store is migrated or resumed.

The original SQLite databases were opened mode=ro/query_only. Their full actual
request wires, response bodies, tool definitions and paired handoffs were read,
not reconstructed from the previous report. The 42-row audit includes the one
Reporter request at #26, which is not a Main scientific decision. See
[the request audit](m1_intent_wire_audit.md) and its
[structured evidence](../../evidence/m1_intent_interface_repair/request_audit.json).

Confirmed attribution:

- Requests 2/3/4 passed their delivered generation Schema but violated the frozen
  base-only routing rule. The actual Span Schema allowed first_segment > 0. This
  is a domain-projection defect, despite the repeated model error after feedback.
- Requests 8/23 violated the delivered Plan Schema. Requests
  28/29/31/32/33/34/35/36/38 violated the delivered nested V4 Schema. Correct
  definitions were actually in every relevant wire. Each of the nine V4 rejection
  bodies was exactly present in the next Main wire's pending_feedback by tool_id.
  Feedback was not lost by handoff or compression.
- No relevant delivered wire contained scientific_question_v2 or an old-v2
  example. Unexpected root names are fields of the current nested structure
  payload or Plan decision. Their causal origin in model generation is unknown;
  merely recognizing those names does not prove an obsolete-contract leak.
- Requests 11/13 genuinely lacked a complete legal control source. Their feedback
  supplied the existing initialize_control action. Main's repeated reads and
  retry did not satisfy that prerequisite.
- Requests 37/39 conformed to the delivered Schema but combined a mechanism
  observable with reoptimized-task semantics. The compiler correctly rejected
  them; the model-visible Schema failed to express that scientific restriction.
- Request 25 entered the original Native T1 worker and completed 32 callbacks,
  16 iterations and 19,200 physics steps. Its failing model prediction is a
  scientific result, unlike rejected requests, and is not independent acceptance.
- The delivered V4 parameter catalog used labels such as lengths/materials/sections,
  while the mechanism compiler accepted authoritative registry categories and the
  existing segment_lengths selector. This is a confirmed catalog/compiler mismatch;
  the historical requests failed earlier, so it does not explain away their root
  field errors. The real engineering inspect probe exposed an additional unregistered
  `/parameters` navigation pointer admitted by the free-string parameter Schema.
  V4 now uses the original structural registry's group names and enumerated IDs.
  V1/V2/V3 selectors retain their existing meanings.

The architecture planning document was read for responsibility boundaries only.
Its historical candidate examples are not supplied to the next Main Study.

## One scientific contract and deterministic compilation

ScientificQuestionV4 remains the complete internal scientific contract.
`selected_question_schema()` supplies the same candidate/action-specific
projection to the Provider registry, compiler and binding audit. Full original
AnalysisRequest, authorization, source checks, method admission and worker
accounting still own execution. There is no V5, new agent, planner, optimizer,
workflow or parallel Store.

The existing research_analysis entry accepts omitted execution fields only when
their values are uniquely implied by Main's selected semantics or frozen physics.
It never relocates illegal root fields, normalizes a nonunit scientific direction,
changes a target, chooses an ambiguous source, or starts an unchosen computation.
Raw Main input, expanded V4 question, field sources, selected Plan, selected Schema
and final AnalysisRequest are saved in scientific_intent_compilation events.

Before, a control request repeated question_type and effect_semantics although its
selected domain already fixed both. The current projected request can be:

```json
{
  "domain": "control",
  "control": {
    "control_scope": {"mode": "full_task"},
    "control_search_effort": {
      "method": "pattern", "knot_count": 4,
      "iterations": 2, "evaluation_requests": 4
    }
  }
}
```

Those example effort values are offline fixtures, not prescribed research effort.
The program resolves an exactly unique legal schedule and the candidate's frozen
task/protocol. Multiple different schedules require Main selection. Reach/Hold
keeps T1; heterogeneous task families use a registered applicable Direct identity,
without presenting it as T1. Main still chooses scope, effort and any scientifically
different method.

For a mechanism parameter study, Main continues to choose the operation, explicit
target and goal, parameters, and a working point with distinct physical meaning:

```json
{
  "domain": "structure",
  "structure": {
    "operation": "differentiate",
    "effect_semantics": "mechanism_effect",
    "parameter_paths": ["segments.0.length_m"],
    "target": {"quantity": "tip_acceleration_input_map", "reduction": "norm", "goal": "decrease"},
    "operating_point": "frozen_task_initial_state",
    "requested_budget": 5
  }
}
```

This is an explicitly synthetic contract example, not a proposed M1 design or
scientific next step. Fixed absolute tensions follow from this effect semantics;
they are no longer a repeated required field. Reoptimized-task effects instead
require a registered frozen task constraint/value target and the complete frozen
initial task. A mechanism direction is never silently converted into that task
objective. Passive mode and its uniquely implied point/control treatment are
compiled from the existing physical semantics; load choices remain explicit.

## Preparation and concise context

`legal_control_sources()` extracts the previous compiler's exact complete-source
validation into the existing physical_replay module. Both discovery and compilation
now use it. This is read-only source discovery, not a change to Replay evaluation.
The catalog distinguishes blocked/unsupported/unauthorized/budget conditions,
missing initialization, distinct-source choice and readiness to submit scientific
scope/effort. Preparation includes the exact existing control_seed entry.

An explicitly selected V4 diagnose survives a completed initialize_control only
when the actual returned candidate/condition is identical. A new candidate,
condition, different scientific Plan or unsettled preparation does not inherit
that choice. The loaded tool returns to the previously chosen scientific entry;
no scientific action executes automatically. This removes the otherwise required
repeat diagnose and route round trip, not merely an error message.

The generation Schema now projects count bounds and the original conditional
base-only rule. Broader existing routing grants retain first_segment choices.
The generator, FamilySpace authorization and historical defaults are unchanged.

L0 retains the latest real result, task gaps, Main hypothesis, available actions,
source readiness and remaining budget. The V4 handoff exposes grouped parameter
counts and an exact L1 query instead of a full parameter catalog. It explains the
single outer payload shape without copying Pydantic definitions or matrices.
Original exact rejection feedback remains available; no error-specific retries or
compatibility white lists were introduced.

## Files and functions

| File | Change and purpose |
|---|---|
| scientific_intent.py | Shared selected Schema, expand_v4, original V4 compilation audit, source readiness, same-object preparation carry. |
| agent.py | Frozen generation-domain projection, reused scientific Schema, tool loading after explicitly chosen preparation. |
| physical_replay.py | Read-only legal_control_sources extraction; existing execution/evaluation functions unchanged. |
| task_constraints.py | Same legal sources in method discovery and accurate preparation request. |
| research_context.py | Read earlier Plan intent without state mutation; preserve prepared hypothesis and concise grouped L0 handoff. |
| structure_research.py | Share the original scalar-direction admission set with Schema; unchanged computation and acceptance semantics. |
| test_intent_compilation_handoff.py | Seven focused Mock SDK/worker contract, registry, source, routing, invalid-input and sealed-state checks. |
| study_m1_knowledge_assisted_v4_intent_repair.json | New independent finite proposal, preserving original science and curated Knowledge. |

No file or historical contract was deleted. Native T1/T2 algorithms, MuJoCo
integration, task evaluators, FamilySpace science, certificates and SELECT/STOP
implementation were not edited.

## Validation and bounded real-model follow-up

Offline validation uses original SDK request assembly and explicitly fabricated
workers. The seven new cases cover M1 T1 admission, mechanism inspect and explicit
decrease, shared source uniqueness/ambiguity, generation grants, rejected inputs,
STOP sends, and candidate-change barriers. Existing targeted V1/V2/V3, passive
V4 and heterogeneous Direct checks cover compatibility. A first passive check was
blocked by the original commit-before-bind rule; it must be rerun after committing
the implementation. A test-class spelling error is retained in local logs and is
not counted as a passing test. No real scientific worker or Replay is authorized.

The user subsequently explicitly approved real model calls without another
permission request. A bounded engineering model-interface probe may use at most
8 actual Provider requests through the original accounted transport. It validates
generated requests against actual projected schemas and the original compiler;
it executes no numerical/physical workers and establishes no autonomous M1 result.
Its exact calls and costs must be reported separately from Mock tests and from
the future formal Study. There is no automatic full research run. The first
engineering window made four actual requests: the control case corrected a root
field error and compiled to original T1 on request two; an inspect case submitted
an unregistered parameter pointer, and request four returned confirmed HTTP 502
`empty_response`. Its four charges and engineering STOP are preserved. After the
registry projection repair, at most four remaining requests may be used under a
new committed implementation, keeping the cumulative engineering ceiling at eight.

The second window used three requests: inspect compiled immediately; a legal
Schema request for differentiation selected an unreduced matrix, correctly
rejected by the original scalar-direction rule; its next response was again
confirmed HTTP 502 empty_response. Both failed windows retain their own source
identities, receipts and engineering STOP. The scalar requirement is now projected
using the exact original admission set, with no automatic choice of norm/min/max.
Only one original engineering request remains for a final check.

## New formal M1 proposal

The new proposal retains all three original conditions, scientific thresholds,
FamilySpace, four whitelisted Knowledge revisions, runtime model/reasoning,
16 mathematics entries, 18 independent launches, Native limits 800/100/4 and the
7,700,400-step conservative per-Study bound. Historical winning structures,
controls, results and background are not imported.

Proposed finite Provider total is 80, including 12 protected closeout requests;
public operations 240, including 16 closeout. This provides 68 exploratory
requests versus the prior 39, while keeping a meaningful reserve and an early
maximum-8-request settled-feedback checkpoint. The old 42 successful responses
used 513,879 tokens, about 12,235 tokens/request; applying that observed mean to
80 requests gives about 979,000 tokens as a planning estimate, not a token cap or
monetary quote. Actual context, replies and Reporter use can differ.

New allocations never refund or reset the prior 43 actual requests, 1 mathematics
entry or 19,200 steps. Subsequent repeated mathematics retains original accounting.
The source/configuration/tests must be committed before new prepare/bind. The
formal scientific authorization remains identity-bound and unrecorded during
this engineering task. The proposal is delivered without starting a formal M1
Worker, replaying an old STOP, merging main or executing nine-task benchmarks.
