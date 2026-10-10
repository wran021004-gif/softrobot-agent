# Diagnostic procedure draft: initialization-dominated NMPC

Recommendation only. This procedure has not been validated across executions or
approved as an engineering-registry strategy. Its source is the
[saved timeline](../evidence/nmpc_initialization_20261010/saved_timeline.json)
and original execution `21b607607bf442a6b6d9494dda897ea8`, whose ownership and
artifact hashes are preserved in the
[binding](../evidence/nmpc_initialization_20261010/source_binding.json).

1. Freeze the physical robot, task, acceptance and simulator/controller timing.
   Inspect all applied updates. Separate initialization selection, intentional
   early stopping, convergence, unusable-plan holds and solver exceptions. Count
   selected iterations and inspect actual stopping reasons rather than treating
   aggregate solver status as a causal explanation.
2. Build a timeline using implemented absolute prediction-node times, holding
   flags and effective horizons. Locate first changed action, horizon shortening
   and first holding-cost visibility separately. Distinguish wall computation
   from virtual-time control execution.
3. Import immutable execution evidence with original ownership. Identify missing
   initial, raw-returned, selected, rejected and warm-plan records explicitly.
   Missing historical traces cannot show why an unseen iterate was rejected.
4. Select a bounded representative saved state. Compare full simulator world tip
   position and Jacobian velocity with reduced kinematics evaluated at the saved
   projected state. This is a same-time projection check. Keep curvature residuals
   in rad/m separate from tip position errors in metres.
5. Inspect accepted one-step predictions aligned with the next recorded timestamp
   and actual applied input. Report velocity-vector disagreement and speed-magnitude
   difference separately. This is a next-step prediction check, distinct from
   same-time projection disagreement.
6. State a hypothesis, exact evidence, changed factor/state, expected and weakening
   observations, fixed conditions, budget and stopping rule. Make one same-state
   paired comparison with separate mutable workspaces. Preserve historical warm
   starts only when complete; otherwise declare the new common-seed protocol.
   Handle the previous input explicitly; never obtain update zero's previous
   input through negative indexing.
7. Save numerical results before presentation. Inspect initial, raw-returned,
   selected and retained rejected iterates, objectives, named residuals, first
   commands and physical trajectory metrics. A lower-objective infeasible iterate
   is evidence of progress outside acceptance, not a deliverable command. Different
   objectives require physical comparisons rather than scalar-objective ranking.
8. When extending feasible return from15s to30s, keep CPU/iteration/improvement and
   all other ceilings unchanged. Report the condition that actually ended each
   solve. If another condition triggers first, the longer-budget effect remains
   unresolved; do not declare extended solving ineffective or automatically raise
   that condition's cap.
9. Return actual evidence to the research principal before further work. A single
   targeted closed-loop revision is justified only by an observed mechanism.
   Reuse the original execution as baseline, record selected updates, and compare
   first departure from initialization, error response, holding motion, saturation,
   input variation, aligned prediction errors and complete computation costs.
10. Stop when the evidence answers the bounded question, the principal chooses
    STOP, a ceiling is reached, or an engineering/interface failure requires repair.
    Preserve negative results. A local comparison does not establish closed-loop
    improvement, and an unsuccessful controller does not establish impossibility.

Retain these applicability limits: synchronous simulation latency does not imply
missed virtual-time actions; feasibility does not establish task success; selected
initialization differs from exception fallback; missing traces cannot explain
unseen rejections; local improvement does not establish closed-loop improvement.
The procedure does not establish a unique cause, continuous-time acceptance,
real-time control, hardware transfer, global optimization or LLM superiority.

The older memory/skill contracts require `ArtifactReference(run_id,path,sha256)`
and a finalized `run.json` with `artifact_hashes`, task/design snapshots and
legacy ToolResult metric pointers. This platform uses content-addressed
`EvidenceRef(artifact_id,media_type)`, SQLite sessions and immutable export bundles.
No matching finalized legacy run exists. The procedure stays a reference-backed
draft; no fabricated validation, human approval, database or provenance migration
is introduced to admit it.
