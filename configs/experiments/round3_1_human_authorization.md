# Human authorization: Round 3.1

Owner: Human. Source: the user's supplied "ROUND 3.1 — Debug Visualization +
First Human-Authorized Design Experiment" request, received 2026-09-12.
This record transcribes that explicit authorization; it is not Agent approval.

Applies only to configs/experiments/round3_1_reach_free.yaml, frozen reach_free_v1,
and a simulator study using current legacy_v1_surrogate physics. No real-robot
physical validation is claimed. Task/environment/tolerance/evaluator values are
resolved through the existing TaskContract and are not duplicated here.

Only total_length_m may change: finite, positive, [0.35, 0.45] m.
All other baseline DesignSpec fields remain fixed: sections=1, segments=8,
body_radius_m=0.02, tendon_count=4, tendon_routing_radius_m=0.015,
and the baseline robot_family. The baseline source is configs/design_tendon_arm.yaml.

M1 PCC screening minimizes model.predicted_position_error_m. Canonical comparison
minimizes mujoco.position_error_m; the frozen evaluator alone decides task success.
Only legacy C1 open loop is authorized; no C2 or controller/physics tuning.
Seed=17, total evaluation budget=12, MuJoCo sub-budget=5. Baseline and endpoint
screening share this budget. Lower/baseline/upper sensitivity is derived from
these same evaluations, with UNKNOWN causal attribution.

Repair is disabled: repair_iteration_budget=0, repair_actions=[], no escalation.
Boundary optima must be reported as BOUNDARY_OPTIMUM_OBSERVED, with no automatic
extension of bounds or approval of another variable. Human decides the next range.
No commit, push, LLM connection, or Skill admission is authorized by this experiment.
