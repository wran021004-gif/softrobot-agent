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

`statics.gvs_equilibrium@1.0.0` solves
`tau_tendon(q,T) + tau_gravity(q) - tau_elastic(q) = 0` with a damped Newton
iteration and a CasADi automatic Jacobian. Robot geometry, gravity, mount,
tendon order, and force limits come from the frozen session. The caller supplies
only tensions, an initial `q`, and optional numerical tolerances.

`controller.lqr@1.0.0` solves the continuous algebraic Riccati equation with a
lazy LQR-only SciPy import and applies `u=u0-K(x-x0)`. It rejects
non-equilibrium linearizations whose drift exceeds the configured tolerance.
The unconstrained LQR command is finally clamped per tendon to
`[0, force_limit_n]`; its output remains model-space tendon tension, not a
backend tendon-length or motor command. Direct backend selection therefore
continues to fail with `CONTROL_BACKEND_ADAPTER_REQUIRED`.

`controller.gvs_lqr@1.0.0` is the separate backend-executable composition. It
projects the compiled serial-cell `qpos/qvel` state into the unchanged GVS
first-order basis, applies the existing continuous LQR law, and sends its
bounded tendon tensions to the selected backend. Normal
`backend.family_mujoco` execution uses `execute_ideal_tension`: each tension is
clipped to its frozen force limit and applied by a direct tendon-force actuator.
Transmission inversion, actuator travel/rate limits, and the length servo are
not part of this normal path. The old length-servo bridge remains available to
the explicit development comparison, but Route rejects it as a combination.
The projector rotates each principal-axis hinge angle into its segment frame,
divides by the real compiled cell length, then least-squares fits
`[1, 2*s/L-1]` independently for y/z curvature and rate. At least two cells per
flexible segment are required. Runtime traces retain projected state,
projection residual, state error, raw/bounded/measured tension, tendon length,
length change, length rate, and saturation flags.

Executable controller parameters are now a candidate-independent recipe:
semantic LQR weights and the `gvs_inverse_tip_static` operating-point strategy.
For each physical candidate, scene resolution runs the existing inverse-tip
IPOPT assembly against the frozen target, refines it with
`statics.gvs_equilibrium`, then reconstructs the existing
`GVSModel -> DynamicSystem -> CasadiLinearizer -> ContinuousLQRController`
chain. Candidate control evidence records operating-point, linearization, gain,
and final control identities. `q0`, `u0`, and `K` are derived artifacts and are
not Route/LLM inputs. Time-window external forces are omitted only from the
nominal GVS equilibrium/linearization because GVS v1 does not model them, while
the frozen backend task continues to apply them.

The compact public chain is:

```text
dynamics.gvs_build_system@2.0.0 -> DynamicSystem EvidenceRef
linearization.linearize@2.0.0   -> LinearizedModel EvidenceRef
control.lqr_synthesize@1.0.0    -> compact stability summary + gain EvidenceRef
```

The build tool accepts only `x0/u0`; it always uses the frozen task environment.
LQR synthesis accepts semantic curvature, rate, and tendon-tension weights,
derives tendon order and force limits from the frozen robot, and stores the full
gain outside model context. These tools, the GVS equilibrium tool, and the
compact PCC/GVS evaluation tools declare `route_visible`; authorization and
dependency checks still apply. They perform no MATLAB or MuJoCo solve. Existing
GVS omissions remain unchanged: branching, closed
chains, contact, self-collision, torsion, shear, axial extension, tendon
elasticity/friction, motor electrical dynamics, and arbitrary external forces.
