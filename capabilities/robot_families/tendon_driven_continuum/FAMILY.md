# Tendon-driven continuum family

Current support is single-section tendon-driven continuum V1: a low-fidelity
tendon-actuated segmented approximation. The flat DesignSpec remains the design
contract. grammar.yaml documents fields; tools enforce their execution limits.

## Current design choices

Use robot_family=tendon_driven_continuum and sections=1. Family identity is an
acceptance check, not a physical parameter. sections remains reserved for future
multi-section support; M1 and compilation explicitly reject sections != 1 with
UNSUPPORTED_DESIGN_CONFIGURATION. The shared RobotIR compiler now enforces this boundary before numerical calls.

Active numerical fields:

- total_length_m: M0 reach bound, M1 PCC arc length, MuJoCo centerline length.
- segments: MuJoCo discretization, paired y/z hinges, and distal routing stations.
- body_radius_m: capsule geometry and resulting mass/inertia/contact.
- tendon_count: number and angular spacing of PCC commands and MuJoCo tendons/actuators.
- tendon_routing_radius_m: PCC length changes and MuJoCo circumferential routing offsets.

The two tendon fields have moved from reserved to active. Positive finite
lengths/radii and positive counts are required by consuming tools. Examples are
illustrative, not validated scientific operating ranges. The environment floor
is fixed and does not follow body_radius_m. Tool manifests provide exact coverage.

## Current tools and coordinates

M0 is a geometric length-bound screen. M1 uses base MATLAB fminbnd to find a
best-fit single-section PCC bend on theta in [0,pi] and produces length commands.
PCC ignores dynamics, gravity, stiffness/load, and contact. It can pass as a tool
while model_task_success=false, allowing the pipeline to continue.

Both M1 and MuJoCo place the base at [0,0,0], straight centerline along +x, and
cross-section in y-z. Routing i uses alpha_i=2*pi*i/N, y=r_t*cos(alpha_i),
z=r_t*sin(alpha_i); phi is measured from +y toward +z.

MuJoCo compiles actual spatial tendons through the base and distal routing
sites, with tendon-transmission length servos. Every segment has y/z bending
hinges and fixed surrogate restoring stiffness/damping. There is no axial or
torsional DOF. Force-limited tendons pull only. This is not Cosserat continuum,
FEM, or a validated material model. Self-contact is disabled.

The task environment source is tasks/reach_free/environment.yaml, selected using TaskSpec.environment_id;
a future LLM supplying DesignSpec cannot modify it. The task gate holds the PCC
commands for 1000 steps and compares actual final tip position to the TaskSpec
target/tolerance. No command disables actuation. PCC error and physical error are
reported separately; TASK_FAILED must not trigger hidden retuning.

## Unsupported extensions

Multi-section physics, tapered radius, variable/material-derived stiffness,
Cosserat/FEM models, and interchangeable end-effectors remain unsupported.
They require implementation and matching metadata before being exposed as
supported choices. Agent role/output/permission contracts are present; no LLM runtime, RL or design optimizer is implemented.

DesignSpec is compiled once into shared RobotIR; both MATLAB and MuJoCo consume
its physical structure. See ../../../physics_contracts/ for approved mappings
and ../../../README.md for artifact recovery and authority boundaries.
