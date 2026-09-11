# MuJoCo tools

compile_mujoco consumes RobotIR, TaskSpec, EnvironmentSpec and SimulatorSpec and
writes deterministic MJCF. Legacy DesignSpec input is compiled through the shared
IR compiler. Defaults load/validate the frozen task environment. The sole geometry
and gravity source is tasks/<environment_id>/environment.yaml, whose mujoco.xml
representation is checked without rewriting. Timestep comes from configs/simulator.yaml.

The existing capsule geometry, y/z joints, routed spatial tendons, unit-gear
pull-only servos and contact masks are unchanged. Mechanics come from the shared
IR's approved legacy_v1_surrogate profile; see physics_contracts/*.md and .yaml.
New or altered IR mechanics are rejected with PHYSICS_ASSUMPTION_REQUIRED rather
than accepted as a material model. IR contract exceptions propagate to the Harness.

run_task accepts a Controller protocol or None and RunSettings. C1 open_loop_length
holds a fixed target. None disables actuation (C0); zero ctrl would request zero
length. Every command is validated against tendon count/transmission/order. The
runner checks qpos/qvel each step, refreshes final site positions and invokes
metrics.reach.evaluate_reach using the TaskSpec target and tolerance, never the XML
marker. Unknown task types are rejected. General evaluate_metrics and validate_physics
remain PLANNED; the implemented reach metric and finite sanity checks are narrower.

validate_task is the backward-compatible wrapper for an optional length list.
Completed runs retain final task/tendon/actuator metrics and final state even for
TASK_FAILED. Harness persistence adds mujoco_result.json, metrics.json and
simulation_state.json. Control/runtime/nonfinite failures retain failure codes;
legacy names are mapped separately by schemas/failure_taxonomy.py.

This is a low-fidelity segmented tendon-driven surrogate. It is not Cosserat,
FEM, a calibrated actuator or a validated material model. No hidden tuning, trajectory
optimization or success override occurs. Finite-state checks do not prove physical
fidelity, convergence, stability or steady state.
