# GVS CasADi, linearization, and LQR

`model.gvs@1.0.0` now exports a continuous `DynamicSystem`.  The numerical
reference remains `extensions/tendon_family/gvs.py`; the differentiable MX
graph is implemented in `extensions/tendon_family/gvs_casadi.py`.  The public
system stores a `family.gvs_continuous_dynamics@1.0.0` reconstruction payload,
not a Python callable or CasADi runtime object.

For each flexible segment, the coordinate order is
`kappa_y_0, kappa_y_1, kappa_z_0, kappa_z_1`.  The flattened state is all
segment coordinates followed by their rates in the same order.  Inputs are
actual tendon tensions in `family.design.tendons` order.  The model evaluates

```text
xdot = [qdot, M(q)^-1 (tau_tendon + tau_gravity
                       - c - tau_elastic - tau_damping)]
```

CasADi automatic differentiation supplies the tendon-length Jacobian, mass
matrix derivatives used by the Christoffel velocity bias, and the `A=df/dx`,
`B=df/du` linearization at the explicit `DynamicSystem.x0/u0`.  The
linearization always retains `drift=f(x0,u0)`.

`controller.lqr@1.0.0` solves the continuous algebraic Riccati equation with
SciPy and applies `u=u0-K(x-x0)`.  It rejects non-equilibrium linearizations
whose drift exceeds the configured tolerance.  The unconstrained LQR command
is finally clamped per tendon to `[0, force_limit_n]`; its output is model-space
tendon tension, not a backend tendon-length or motor command.

Public discovery entries are `dynamics.gvs_build_system`,
`linearization.linearize`, and `control.lqr_describe`.  They perform no MATLAB
or MuJoCo solve.  Existing GVS omissions remain unchanged: branching, closed
chains, contact, self-collision, torsion, shear, axial extension, tendon
elasticity/friction, motor electrical dynamics, and arbitrary external forces.
