# Tendon length mapping — V1

Human-owned geometry contract. For the ordered RobotIR routing angles alpha_i,
l_i = L - r_t*theta*cos(alpha_i-phi), and delta_i = l_i-L. All commands are
meters in tendon_0 through tendon_(N-1) order. Positive theta toward +z shortens
the tendon at alpha=pi/2. No reordering by the MATLAB or MuJoCo adapter is allowed.
Single-tendon MATLAB scalar results are normalized to Python lists.

PCC models continuous arc routing; MuJoCo uses straight spans through segment
distal sites. Their lengths can disagree. A commanded length need not be achieved
under gravity, contact, restoring joints or force saturation. Cable elasticity,
slack mechanics and friction have no validated law in V1; do not infer them from
this geometric mapping. New laws require PHYSICS_ASSUMPTION_REQUIRED.
