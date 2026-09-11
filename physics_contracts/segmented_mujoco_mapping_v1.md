# DesignSpec → RobotIR → segmented MuJoCo — V1

Human-owned mapping extracted from main@245a785. High-level DesignSpec is the
flat morphology proposal. The deterministic compiler checks the approved grammar
and resolves one section, segment_length=L/segments, uniform body radius, ordered
routes and the legacy_v1_surrogate profile into RobotIR. A separate backbone radius
and continuum material properties are null/unmodeled, not inferred from capsule
radius. Only the tendon_driven_continuum family is supported.

Every segment, including the first, has proximal local y/z hinge joints and a
capsule from [0,0,0] to [segment_length,0,0]. There is no axial, torsional or free
DOF. A fixed world routing site and each segment's distal offset site form each
spatial tendon. The final distal center carries tip_site. Target markers are
noncolliding visualization, not evaluation truth. Robot contype=1/conaffinity=0
preserves arm-floor contact with the frozen floor masks and disables self-contact.
The floor never follows morphology. Marker sizes/colors and tendon display width
are representation constants preserved in the compiler, not scientific variables.

Physical/surrogate constants are authoritative in legacy_v1_surrogate.yaml:
hinge stiffness 0.1 Nm/rad, damping 0.1 Nm s/rad, capsule density 1000 kg/m^3.
Mass and inertia are inferred by MuJoCo from those capsules and density. These
values were not experimentally fitted. No EI-to-hinge-stiffness conversion is
approved. Changing segmentation retains these constants; parametric execution
support does not assert discretization convergence or identical physical stiffness.

Design variables are counts, lengths and routing/body radii within the existing
grammar. Examples are not validated scientific operating ranges. Physics-model
constants are not optimizer variables. Simulator timestep is in configs/simulator.yaml;
run duration is steps*timestep with steps in configs/run.yaml. Other MuJoCo defaults
retain baseline behavior; engine version and source snapshots are recorded per run.
This is a low-fidelity segmented tendon-driven surrogate, not Cosserat, FEM or a
validated material model. Multi-section laws require Human approval and implementation.
