# Independent closeout mechanics v1

Authority: `configs/experiments/round3_closeout_authorization.yaml`, scoped to this
simulation campaign and independent development analysis. No main physics writeback.
Scientific status: SURROGATE_ASSUMPTION; independent solver, not independent physical validation.

One-mode Rayleigh–Ritz reduction of the n-segment rigid-link rod: q is total
bend towards world +z (rad), each hinge bends q/n about body -y. Base is fixed,
segment i orientation is i*q/n. Axial extension, shear, torsion, friction and
contact are omitted; no catch/collision capability. This planar one-mode constraint
does not represent the full 2n MuJoCo coordinates or arbitrary three-dimensional loads.
Out-of-plane force has zero virtual work. Do not interpret that as resisting it.

Centers of mass and centerline follow these finite rotations, not a linear beam.
Mass and inertia are exported from loaded XML, with inertial principal axes rotated
into the body frame; COM is checked against the capsule midpoint. Stiffness and
damping are exported from compiled y hinges. Radius does not determine material EI.
No continuous EI to hinge conversion is introduced. n remains fixed in comparisons.

U(q,t) = sum(k_i)*(q/n)^2/2 - sum(m_i*g dot c_i(q)) - F(t) dot tip(q)
+ sum(T_j(t)*ell_j(q)). T is nonnegative tensile force in N, ell the actual
piecewise route through rotating distal tendon sites and fixed base sites, in m.
Given length commands are **not** accepted as tensions. Static C1 comparisons
therefore require observed force input and are conditional on that distinct semantics.
No static C1 length-servo equivalence is claimed by this tool.

M(q) = sum(m_i*|dc_i/dq|^2 + I_yi*(i/n)^2), kg m^2;
D = sum(d_i)/n^2, N m s/rad. Dynamics:
M*qdd + 0.5*M'(q)*qd^2 + D*qd + dU/dq = 0.
Central differences use 1e-5 rad. Static fminbnd is bounded to [-2.8,2.8],
120 iterations / 160 evaluations. Equilibrium requires interior solution and
|dU/dq| <= 1e-6 N m. Dynamic ode15s uses RelTol=1e-7, AbsTol=1e-9,
MaxStep=0.01 s and a 30 s wall limit; horizon <=4 s. Failed solves are failures,
not predictions. For constant conservative loads E=0.5*M*qd^2+U decays via D;
with time-varying loads input work changes E, so monotonicity is not required.

Identification: stiffness multiplier in [0.5,2], training loss is mean squared
static equilibrium torque residual (N m)^2. Training forces [-0.06,-0.03,0.03,0.06]
N and validation forces [-0.045,0.045] N are frozen before synthetic generation.
Truth multiplier 1.4 is a synthetic fixture; zero gravity and zero tendon force.
The validation set is never used for fit selection. Fit MaxIter=80, MaxFunEvals=100;
each residual evaluates formulas, not a nested mechanics solve. New analysis version
only, SYNTHETIC_VALIDATION; no real calibration or uniqueness claim.
