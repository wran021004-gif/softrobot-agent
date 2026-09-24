# Stage 3.7: GVS to backend equilibrium consistency

## Frozen baseline and method

The diagnostic uses the Stage 3.6 saved `q0`, `u0`, robot, `structural_linear` resolved basis, scene, compiled physics, and original Stage 3.5 `robot.xml`. It rebuilds the same DynamicSystem and linearization and asserts their exact saved identity hashes (`6c011094...f0d25`, `ebad2be5...470d`), the saved basis record, robot tendon point bindings, tendon order, pretension, limits, and physics identity (`0be5f7b2...a6b8d`). The robot digest is `ba16d197...3899a`. No physical equations, gains, or source model are modified.

The coordinate order is `near` then `far`, each with `kappa_y_node_0/1/2` followed by `kappa_z_node_0/1/2` (12 coefficients). The tendon order is `near_t0/t1/t2`, `far_t0/t1/t2`, with `[0, 8] N` limits. The saved operating tensions in that order are `[1.751276, 4.755853, 3.103157, 3.218254, 0.785936, 0.631530]` N. The full `q0`, identities, force vectors, shapes, and tendon Jacobians are in the JSON artifact. The GVS tip is `[0.289999972, 0.035000005, 0.189999985]` m and its recomputed static residual norm is `1.60e-17` N·m², consistent with the saved refined residual `1.04e-17`.

The script maps `q0` through the saved cell-angle matrix, sets zero velocity and the six direct tension controls, and calls `mj_forward` before any step. It then advances the unchanged MuJoCo model at fixed `u0` until five consecutive 0.1 s checks have `||qvel|| < 1e-4` rad/s and `||qacc|| < 1e-2` rad/s². It stopped at 4.3 s. This is a numerical stationary-state criterion, not an independent root solve.

## Measurements

| Quantity | GVS at `q0/u0` | Backend at mapped `q0/u0` | Backend after fixed tension settling |
| --- | ---: | ---: | ---: |
| Tip, m | `[0.290000, 0.035000, 0.190000]` | `[0.282824, 0.043662, 0.202401]` | `[0.269316, 0.049709, 0.205812]` |
| Tip distance from GVS tip, mm | 0 | 16.743 | 29.903 |
| GVS coordinate distance from `q0`, rad/m | 0 | `8.49e-15` | 4.4881 |
| Tendon lengths, m | `[.159817, .160078, .160023, .278653, .296773, .304670]` | `[.159824, .160063, .160037, .277321, .296276, .304496]` | full vector in JSON |
| Maximum absolute tendon length difference from GVS, mm | 0 | 1.332 | 6.408 |
| Applied tendon tension, N | `u0` | exactly `u0` | exactly `u0` |
| Joint acceleration norm, rad/s² | 0 at equilibrium | 7081.57 | `7.02e-4` |
| Projected static force residual norm, N·m² | `1.60e-17` | `1.242e-3` | `8.34e-8` |

At the mapped state, `MuJoCo_tip - GVS_tip = [-0.007176, +0.008662, +0.012401]` m. The backend coordinates project back to `q0` to `8.49e-15` rad/m; its cell-angle mapping is square and exact for this 3-cell-per-segment model. Its physical backbone still differs: cell endpoint gaps are 0.82–1.24 mm on `near` and 6.18–16.81 mm on `far`. The far tendon length `far_t0` is 1.332 mm shorter. Thus the same coefficients do **not** describe the same shape, even though the angle transfer is exact.

Tendon routing point bindings, order, pretension (`0.2` N each), and limits match the design. The direct tension actuators deliver exactly `u0`; their virtual-work relation `qfrc_actuator = -J_length.T u0` has maximum error `1.39e-17` N·m. The hinge passive force matches its compiled spring law exactly. There are no contacts or constraint forces. Therefore this is not an actuator sign, pretension, or route-topology error. The geometry difference changes tendon lengths and Jacobians (maximum projected Jacobian entry difference `2.33e-4` m²/rad).

## Signed force localization at mapped `q0`

The table uses `M.T` to project backend joint forces into the saved GVS coordinates. Elastic is the positive term in `net = tendon + gravity - elastic`. All entries are vector L2 norms in N·m².

| Term | `||backend - GVS||` | Finding |
| --- | ---: | --- |
| Gravity | `1.771e-3` | Largest term difference and aligned with the observed net residual. |
| Tendon generalized force | `1.390e-3` | Same tensions, different length Jacobian and force distribution. |
| Elastic restoring force | `0.442e-3` | Smaller difference despite exact backend spring-law evaluation. |
| Net force | `1.242e-3` | Terms partly cancel. |

The gravity difference contributes about 107% of the residual **along its measured direction**; tendon and elastic differences oppose it by about 4% and 3%, respectively. These directional fractions describe this one pose, not a global model sensitivity. The largest backend residual coordinates are `near.kappa_y_node_1` (`+9.41e-4`) and `far.kappa_z_node_1` (`+4.86e-4`) N·m². The full signed vectors and Jacobians are in the JSON.

The backend settles to a different shape under the identical constant forces: its projected coordinate gap is 4.4881 rad/m and tip gap is 29.903 mm. At the final check, `||qvel|| = 2.72e-5` rad/s and `||qacc|| = 7.02e-4` rad/s². This rules out a transient-only initialization explanation. The final state meets the stated numerical stationarity criterion; no uniqueness or global stability claim follows.

## Attribution

| Hypothesis | Verdict | Evidence and limit |
| --- | --- | --- |
| State transfer mismatch | **SUPPORTED** | Exact coefficient transfer produces a 16.743 mm physical tip gap and large backbone gap. The numeric q transfer itself is exact. |
| Tendon force mismatch | **SUPPORTED** | Same applied force, but tendon length/Jacobian differences give a `1.390e-3` N·m² generalized-force difference. Routing topology and force sign agree. |
| Stiffness model mismatch | **PARTIALLY_SUPPORTED** | Elastic generalized force differs by `0.442e-3` N·m². The backend spring law is correct; this experiment does not isolate material stiffness from geometric discretization. |
| Gravity model mismatch | **SUPPORTED** | Gravity generalized force differs by `1.771e-3` N·m² and is the principal contributor to the initial signed residual. Shape, mass distribution, and quadrature contributions are not separately identified. |
| Coordinate mapping mismatch | **NOT_SUPPORTED** | Cell-angle discretization and projection recover `q0` to numerical precision. The physical shape discrepancy remains under that exact mapping. |
| Initialization-only mismatch | **NOT_SUPPORTED** | Fixed `u0` yields a distinct stationary backend configuration. |

**Scientific conclusion:** The equilibrium disagreement is a physical reduced-to-serial discretization mismatch at the mapped operating pose. With only three cells per segment, exact transfer of the structural-linear coefficients gives different backbone geometry, tendon geometry, and gravity loading. The signed initial force residual is dominated by the gravity term, while tendon force also differs materially. The remaining uncertainty is how much of the gravity and smaller elastic differences comes from geometric integration versus discrete mass and spring representation. No correction term or controller change is justified by this experiment.

Run only: syntax compilation and `gvs_backend_consistency.py` in the `softagent` Python environment. The script performs one `mj_forward` operating-point probe and one fixed-tension MuJoCo settling trajectory; no parameter sweep or full test suite was run.
