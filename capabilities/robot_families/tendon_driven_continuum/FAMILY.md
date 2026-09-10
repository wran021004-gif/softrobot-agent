# Tendon-driven continuum family

This family describes the intended tendon-driven continuum arm design space.
Current support is partial: the executable model is a passive segmented chain.
The existing flat `schemas.design_spec.DesignSpec` is the design contract;
grammar.yaml documents its fields without adding schema validation.

## Current design choices

Use `robot_family: tendon_driven_continuum`. Both the MATLAB adapter and MuJoCo
compiler check this discriminator. Proposals can vary `total_length_m` and
`body_radius_m` as morphology parameters and `segments` as discretization.
Use positive values; current examples are illustrative, not validated physical
operating ranges.

These three numerical fields affect MuJoCo geometry. Only total_length_m enters
MATLAB's numerical check. Tool manifests are the authoritative per-tool field
coverage; robot_family is an acceptance check, not a physical parameter.

`sections`, `tendon_count`, and `tendon_routing_radius_m` remain required schema
fields but are reserved in the implementation. Keep their example values for
current proposals; changing them does not change the analysis or simulation.

## Current tool support and limitations

MATLAB performs only a very-low-fidelity geometric length-bound check. It does
not model PCC, PCS, Cosserat mechanics, stiffness, obstacles, or actuation.

MuJoCo compiles a uniform capsule chain with passive hinges in a plane. It has
no tendon routing, actuation, or controller. Its task gate compares the final
tip world position with the target after 100 simulation steps. A geometric
reachability pass can therefore coexist with TASK_FAILED.

## Future Extensions

Possible future work includes multi-section models, tapered radius, variable
stiffness, physical tendon routing, different tendon counts, and different
end-effectors. These capabilities are unsupported today and require matching
analysis/compiler implementations and updated manifests before being exposed
as supported design choices.
