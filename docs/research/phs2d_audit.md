# PHS-2D tool audit (before implementation)

Baseline: `314f75a4971e0a9e4521fe79ddf744ff71de61e2`. Main checkout was
`d629a80d0027209ef6d41d65fdb69b168727bff7`; its untracked files are untouched.
Fetch confirmed the requested baseline. The export worktree is read-only context.

| Question | Baseline status | Actual reusable interface / limitation |
|---|---|---|
| Arbitrary material point position / Jacobian | partially reusable | compiler.resolve attachment uses exact cell and local x, geometry.geometry has body transforms and angular/linear Jacobians; MuJoCo mj_jac accepts arbitrary moving body points. No public global-s point API. |
| Tendon lengths, derivatives, rank | supported | geometry.geometry Jlength; gvs.tendon_kinematics; gvs_casadi symbolic lengths. Rank is operating-point dependent. |
| Gravity + elastic + geometric static balance | partially reusable | GVS equilibrium solves prescribed tensions, not fixed payout; MuJoCo already has gravity and hinge elasticity. |
| Fixed payout / tension only / slack | missing | mjcf emits active tension or length servo; add explicit passive_fixed_payout_v1 using upper tendon limit and no actuator. |
| Arbitrary moving material point world force | missing | backends._apply_mujoco_forces is COM-only; separate mj_applyFT interface needed. |
| Stable loaded passive equilibrium | partially reusable | MuJoCo integration usable; new settling and constraint checks required. |
| Cross-compliance | missing | Add local constrained tangent response on native coordinates, including gravity and tendon geometric stiffness. |
| Structure sensitivity of PHS metrics | not applicable | native fixed_input_structure uses prescribed tensions; optimal_capability / nonlinear_capability reoptimize control; no PHS objective. |
| Legal candidate proposals / scoring | partially reusable | family_space, generated_serial, compiler and mixed_moves usable; search.py task_violation and T1/T2 are not PHS scoring. |
| Study, Store, budget, evidence | partially reusable | core.prepare/bind/generate and Store.reserve/complete reusable; registered TaskAdapter lacks passive experiment. Development-only extension may save candidate-bound raw evidence and independent PHS scoring; never SELECT or evaluate.reach acceptance. |

Read interfaces: family_space, generated_serial, compiler, geometry, mjcf, gvs,
gvs_casadi, mujoco_analysis, backends, scene, model_applicability;
research analysis, native_analysis, optimal_capability, nonlinear_capability,
mixed_moves, search, design, config, core, state, budget; platform_store.

The existing serial cells are 3D with two bending hinges per cell, not a full
Cosserat solid: no axial stretch, shear, material torsion, friction or self-contact.
Geometry admission checks routes/holes/sections; this is not swept cable collision.
World +z remains up. Rotate local +x to world -z at the mount.

MuJoCo 3.13.0 is installed. Official references:
https://mujoco.readthedocs.io/en/3.13.0/XMLreference.html#tendon-spatial
https://mujoco.readthedocs.io/en/3.13.0/APIreference/APIfunctions.html#mj-applyft
Limits are unilateral but numerically soft. Upper-limit Jacobian must equal
negative tendon-length Jacobian and positive constraint multiplier must therefore
produce tension. A zero lower bound must remain inactive. Equality constraints
are not physical rope evidence.

## Minimal integration decision

Use the existing Study solely for frozen FamilySpace construction and candidate
identity. Its inherited Reach task is a construction scaffold, never executed or
scored. Bind a separate immutable PHS protocol in that same Store. PHS requests
use Store reservations, cumulative custom step/count sublimits in the same session,
and immutable outputs/receipts. No new database, optimizer, Provider or Agent.
The separate evaluator consumes recorded equilibrium arrays; development pass is
not registered SELECT. Formal registration needs a passive TaskAdapter, typed
payout/point-force contracts and evaluator capability, not a change to Reach.

## Mathematics

For U = hinge elastic energy + gravitational potential, g = ell(q)-Lset <= 0,
lambda >= 0, lambda*g = 0, equilibrium is
grad U + Jell.T lambda - JF.T F = 0.
For a fixed taut set A, Kt = Hessian(U + lambda.T ell - F.T pF).
Solve [Kt JA.T; JA 0][dq;dlambda] = [JF.T dF;0].
Equivalently dq = Z (Z.T Kt Z)^-1 Z.T JF.T dF for nullspace Z of JA.
Use SVD rank, reduced eigenvalues, residuals and multiplier sign checks.
At zero multipliers the equality prediction is only a bilateral comparison;
unilateral directional response requires an active-set quadratic program.
Finite-force validation must independently measure switching and large deformation.
