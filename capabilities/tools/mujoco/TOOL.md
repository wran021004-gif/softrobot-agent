# MuJoCo tools

## Compiler

`compile_mujoco(design, task, output_path)` deterministically composes a fixed
environment, a single-section tendon-actuated segmented approximation, and a
task marker. It accepts only `robot_family=tendon_driven_continuum`, `sections=1`.
The numerical design fields are segments, total_length_m, body_radius_m,
tendon_count, and tendon_routing_radius_m. Counts/dimensions must be positive
and finite. sections is a support restriction, not multi-section geometry.

`task.environment_id` selects `mujoco/environments/<environment_id>.xml`.
IDs contain only letters, digits, underscores, and hyphens. The environment
must have a mujoco root and worldbody. `reach_free.xml` fixes gravity, timestep,
floor (z=-0.02 m), and light independently of morphology and target.
These environments are manually defined and version controlled; a future LLM
proposing DesignSpec has no authority to edit them. Future reach_window.xml or
insertion.xml must likewise be authored separately. Generated XML is only a
runtime artifact combining environment + robot + task marker.

Robot base is `[0,0,0]`, straight centerline is +x, cross-section is y-z.
Each equal-length capsule has y and z bending hinges at its proximal end,
including the base connection. No axial extension, torsional DOF, or free joint
is introduced. body_radius_m sets capsule geometry and thus mass/inertia and
contact; it does not move the floor. Arm self-contact is disabled.

For each tendon i, `alpha_i=2*pi*i/N` and routing offsets are
`[y,z]=r_t*[cos(alpha_i),sin(alpha_i)]`. A fixed world base site and each
segment's distal site form a real spatial tendon. Tendon count determines both
spatial tendon and actuator count; routing radius determines the path geometry.
Each tendon has a position actuator with tendon transmission and unit gear,
so ctrl is target length in meters, ordered tendon_0 through tendon_N-1.
The force range is [-20,0] N: cables pull and do not push.
MJCF syntax follows the [MuJoCo XML reference](https://mujoco.readthedocs.io/en/stable/XMLreference.html#actuator-position)
and has been loaded with the installed MuJoCo 3.13.0.

The last segment carries tip_site; target_site is a non-colliding world marker
from task.target_m. Task tolerance does not enter the XML. The pipeline uses
task_id to choose `mujoco/generated/<task_id>.xml`; output_path remains explicit.
Compilation returns `artifacts.mjcf_path`. A pass means XML was written;
model loading and task success are separate checks.

Compiler failures: UNSUPPORTED_ROBOT_FAMILY, UNSUPPORTED_DESIGN_CONFIGURATION,
INVALID_DESIGN, INVALID_ENVIRONMENT. File-write errors propagate.

## Fixed simulator/compiler parameters

`tools/mujoco_tools.py` module constants define:

- JOINT_STIFFNESS_NM_PER_RAD = 0.1
- JOINT_DAMPING_NM_S_PER_RAD = 0.1
- BODY_DENSITY_KG_M3 = 1000
- TENDON_SERVO_KP = 1000 N/m
- TENDON_FORCE_LIMIT_N = 20, applied as [-20,0] N
- MUJOCO_TASK_STEPS = 1000

`mujoco/environments/reach_free.xml` sets timestep=0.002 s and gravity=[0,0,-9.81].
The task run lasts 2 simulated seconds. These are fixed simulator/compiler
parameters, not designable morphology fields. Joint stiffness is a segmented
surrogate stiffness, not a validated continuum material model; future work
may replace it using EI/material parameters.

## Task gate

`validate_task(xml_path, task, tendon_target_lengths_m=None)` loads the model.
When commands are supplied, it checks positive finite lengths, a count equal
to both model.nu and model.ntendon, and ordered tendon transmissions. It writes
length targets to data.ctrl once and holds them for 1000 steps. Without a
command, actuation is explicitly disabled to preserve unactuated validation:
zero ctrl on a position actuator would instead command zero tendon length.

The gate checks finite qpos/qvel each step, calls mj_forward after integration,
and reads actual tip_site world position. Its only task inputs are target_m
and position_error_max_m. It does not use target_site as evaluation truth or
dispatch on task_type. Success is final Euclidean error <= allowed error.

Completed runs return steps, nq, nv, tip_position_m, target_position_m,
position_error_m, position_error_max_m, task_success. Controlled runs additionally
return tendon_target_lengths_m, final_tendon_lengths_m, actuator_controls,
actuator_force, all ordinary Python float lists. TASK_FAILED retains all these
metrics. Other handled failures have empty metrics:

- INVALID_TENDON_COMMAND: invalid count/values or model transmission/order.
- PHYSICS_ERROR: model loading, lookup, simulation, or evaluation exception.
- NONFINITE_STATE: nonfinite checked state or final tip.
- TASK_FAILED: completed simulation exceeds the task tolerance.

## Scope and limitations

This is single-section tendon-driven continuum V1 at low fidelity: spatial
routing and tendon actuation are implemented, but Cosserat continuum, FEM, and
validated material physics are unsupported. PCC assumes smooth constant
curvature; this model has discrete hinges, straight tendon spans, gravity,
contact, surrogate stiffness, and force limits. Prediction and simulation may
therefore disagree. Neither a compiler pass nor PCC model_task_success proves
physical task success. The gate adds no hidden controller or parameter search.
It checks final position only, not tracking, orientation, sustained reach, or
robustness. A fixed run duration does not certify steady state.

Implementation: `tools/mujoco_tools.py`; machine-readable details: manifest.yaml.
