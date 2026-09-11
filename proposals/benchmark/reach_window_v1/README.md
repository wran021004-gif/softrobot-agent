# reach_window_v1 — PROPOSED_NOT_APPROVED

`contract.yaml` is the read-only TaskContract entry for these candidate sources.
Resolution preserves all proposal markers and unresolved initial-state decisions;
it does not manufacture executable TaskSpec/EnvironmentSpec or start MATLAB/MuJoCo.
Any future promotion also needs an explicitly Human-approved FROZEN contract
version referencing the approved sources and registered evaluator. Runtime results
cannot perform this step.

Status: BLOCKED_FOR_HUMAN_APPROVAL. The three candidate YAML files contain
suggestions copied from Round 2 development geometry, with a proposed before_window
initial condition. They are not executable task packages and are not registered
in benchmarks/tendon_v1.yaml. No automatic approval, copying or promotion is provided.

The exact initial configuration is unresolved. With the proposed geometry, the
current zero-qpos arm already extends through the wall. Merely adding before_window
does not retract the robot: the evaluator records an initial-condition failure.
Human must approve an initial state and, where necessary, its initialization support
before an insertion benchmark can be frozen. No controller tuning or initializer is
introduced by this round.

The executable WindowAcceptance contract is in schemas/task_spec.py. It supports
before_window/unrestricted, a required final aperture, forbidden window contact,
no additional final whole-body region restriction and no randomization. Allowing
contact, arbitrary window orientation, extra final-region constraints or temporal
path requirements needs approved semantics and implementation before promotion.

## Explicit Human promotion workflow

1. Human reviews/edits and approves the exact task, environment, acceptance and
   initial configuration, using docs/reach_window_human_decision.md. A run PASS,
   Finding, Skill, validator success or Agent output does not constitute approval.
2. Under that explicit approval, create tasks/reach_window/task.yaml containing
   the approved TaskSpec with an explicit `acceptance` mapping. Create its
   environment.yaml with `truth_status: HUMAN_APPROVED`. Resolve the initial-state
   blocker before claiming insertion support. Do not merely rename this proposal.
3. Generate mujoco.xml using tools.spec_tools.environment_xml from that environment;
   do not hand-maintain another geometry source. Include a README recording the
   exact Human decision and limitations.
4. Validate the package with the existing loader:

   `python -c "from tools.spec_tools import load_task_package; load_task_package('tasks/reach_window')"`

   This validates contracts and representation consistency only, never approval
   or physical success. `PROPOSED_NOT_APPROVED` is rejected by runtime schemas;
   formal windows require HUMAN_APPROVED and explicit acceptance.
5. After Human approval and validation of the supported initial/acceptance semantics,
   Human registers `package: tasks/reach_window`, `truth_status: FROZEN`,
   `evaluator: metrics.reach.evaluate_reach`, `metric: task_success` in the existing
   benchmark manifest and removes reach_window from planned_tasks. Until then it
   stays planned. No runtime writes to official task or benchmark directories.

These are local scientific authority rules, not authentication. Existing Human-owned
file boundaries apply; no new service, credentials, permission system or Agent runtime.
