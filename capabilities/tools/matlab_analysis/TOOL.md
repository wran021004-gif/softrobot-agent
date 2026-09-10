# MATLAB analysis

## Purpose

Very cheap early geometric screening: `norm(target_m) <= total_length_m`.
Family support is partial. `reachable=True` does not imply MuJoCo task success.

## Available callable

`MatlabTools.analyze_workspace(design, task)`. Constructing `MatlabTools()` starts
MATLAB and adds the repository's `matlab/` directory. Call `close()` in a
`finally` block to quit the engine.

## Inputs

`DesignSpec` and `TaskSpec`; only `tendon_driven_continuum` is accepted.

## Outputs

`ToolResult` with pass/fail, failure code, and metrics `target_reachable`,
`target_distance_m`, `max_reach_m`, and `reach_margin_m`. No artifacts are written.
Unsupported families return empty metrics. Engine exceptions propagate.

## Design fields actually used

`robot_family` is checked as a discriminator; only `total_length_m` enters the
numerical calculation. All other DesignSpec fields are ignored; see manifest.

## Task fields actually used

`target_m`. The task ID, task type, and position tolerance are ignored.

## When to use

Reject targets beyond the total centerline length before more expensive checks.

## When NOT to use

Do not use a pass as proof of physical reachability, actuation feasibility,
collision avoidance, or task completion.

## Assumptions

The target is in meters relative to the robot base at the world origin.
Total length is a meaningful positive geometric bound. Engine startup has
separate overhead despite the low compute cost of the calculation.

## Limitations

No PCC, PCS, or Cosserat; no tendon count/routing, stiffness, obstacles,
dynamics, or actuation feasibility. This is not a workspace sampling model.

## Failure codes

- `DESIGN_INFEASIBLE`: target distance exceeds total length.
- `UNSUPPORTED_ROBOT_FAMILY`: the family is not supported.

## Fidelity

`very_low`, `geometric_reachability`.

## Implementation path

Python: `tools/matlab_tools.py`, module `tools.matlab_tools`, callable
`MatlabTools.analyze_workspace`. Numerical backend: `matlab/analyze_workspace.m`.
