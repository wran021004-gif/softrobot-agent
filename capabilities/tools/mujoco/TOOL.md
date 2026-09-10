# MuJoCo tools

## Purpose and callables

`compile_mujoco(design, task, output_path)` is a deterministic DesignSpec-to-MJCF
compiler, not a Coding Agent. The same design and compiler produce a consistent
robot structure; the task sets the target marker and the output path selects the
file destination. Compilation success means the XML was written.

`validate_task(xml_path, task)` is the task-level physics gate. It loads the XML,
runs 100 steps, checks finite qpos/qvel, refreshes derived positions using
`mj_forward`, and reads the world position of `tip_site`. It compares that
position with `task.target_m` using Euclidean distance. Success requires
`position_error_m <= task.position_error_max_m`.

## Inputs and field coverage

Compilation accepts DesignSpec, TaskSpec, and a Path. It checks `robot_family`
and uses `segments`, `total_length_m`, and `body_radius_m`. `sections`,
`tendon_count`, and `tendon_routing_radius_m` are ignored. Only `target_m` is
used from TaskSpec. The pipeline, not this compiler, uses task_id for filenames.

Validation accepts an XML path and TaskSpec; it does not read DesignSpec or
enforce a family check. It uses `target_m` and `position_error_max_m`; task_id
and task_type are ignored. It evaluates a positional reach task regardless of
the task_type string. The target_site marker is not the source of the target
used for evaluation.

## Outputs and failures

Both callables return ToolResult on their handled paths. Compilation returns
`artifacts.mjcf_path`; an unsupported family returns
`UNSUPPORTED_ROBOT_FAMILY`. Invalid design arithmetic and file-write exceptions
propagate rather than becoming structured compiler failure codes.

After a completed simulation, validation returns steps, nq, nv, tip_position_m,
target_position_m, position_error_m, position_error_max_m, and task_success.
Positions are Python float lists. These metrics are retained on TASK_FAILED.

- `PHYSICS_ERROR`: an exception in loading, site lookup, simulation, or evaluation.
- `NONFINITE_STATE`: checked qpos/qvel or final tip position contains NaN/Inf.
- `TASK_FAILED`: simulation completed, but the final error exceeds tolerance.

The first two failures have empty metrics. A passing result has no failure code.

## Assumptions and fidelity

Family support is partial. The compiler is a low-fidelity MVP segmented passive
hinge-chain approximation. It accepts only `tendon_driven_continuum`.
Meaningful input requires a positive segment count, length, and radius;
DesignSpec does not enforce physical ranges.

The base is `[0, 0, 0]` in world coordinates. Segments extend along local +x,
with hinge axes along +y. Floor z is `-body_radius_m`. The tip_site lies at the
last segment's local `[segment_length, 0, 0]`. Target_site is a non-colliding
world marker at task.target_m. Density, damping, gravity, and timestep are fixed.

## When to use and limitations

Use these tools to compile the supported approximation and evaluate its final
tip position. This is a planar hinge chain, not a physical continuum model.
There is no tendon actuation or active controller. Self-contact is disabled;
only arm-floor contact is enabled. Reserved tendon fields do not affect physics.

Do not interpret this gate as tracking, orientation, sustained reach, or
robustness validation. MATLAB may pass while this passive model returns
TASK_FAILED. The gate does not add control inputs to make the task succeed.

## Implementation path

`tools/mujoco_tools.py`, module `tools.mujoco_tools`, callables `compile_mujoco`
and `validate_task`. Detailed machine-readable contracts are in manifest.yaml.
