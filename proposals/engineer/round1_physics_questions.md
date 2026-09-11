# Round 1 scientific decisions — PHYSICS_ASSUMPTION_REQUIRED

Proposal only; none of these candidates is connected to the canonical pipeline.
DesignSpec, RobotIR and Physics Contracts contain no approved material/EI-to-hinge
mapping. PhysicsSpec is legacy_v1_surrogate, validated=false. Existing resolver/IR
guards reject unapproved profiles and altered mechanics with
PHYSICS_ASSUMPTION_REQUIRED.

An energy-equivalent beam candidate would equate each cell's continuum bending
energy to discrete hinge energy. Human must first decide material law, backbone
cross-section, beam assumptions, strain regime and cell length for every hinge,
including the proximal hinge and end cells. EI has units N m^2, cell length m,
angle rad, energy N m and hinge stiffness N m/rad. Inverse-cell-length scaling is
only a candidate under those assumptions; capsule radius is not an approved
backbone radius. Convergence expectations also require approval before a mapping
becomes executable. Current stiffness remains 0.1 N m/rad per hinge.

Separate Human decisions concern damping law/source (N m s/rad), cable elasticity,
slack/friction and calibrated actuator dynamics. Current zero-force clipping
cannot stand in for these physical laws. Damping, density, gain and force limits
remain legacy assumptions, neither identified nor experimentally validated.

Human must define legitimate optimizer variables, finite bounds, units,
constraints, provenance and objective authority in the existing grammar. Examples
and positive type constraints are not approved ranges. Sensitivity needs its own
approved diagnostic purpose, variable set and bounds; task failure grants none.

Human must approve a scientific comparison criterion and validation context before
discrepancy becomes MODEL_MISMATCH. Tracking acceptance and large-state anomaly
thresholds likewise need justified sources. Until then, tools report measurements
without selecting new laws, ranges, thresholds, controllers or retuned designs.
