# Stage 3.11: serial-bending discretization convergence

## 1. Scientific question

Does serial-bending refinement approach the fixed Stage 3.10 GVS reference?

Measurement only: 3, 6, 12 and 24 cells per flexible segment. No equilibrium solve, controller execution, dynamics stepping, tuning or production-code changes.

## 2. Frozen reference identities

- parent_commit: `e79f7e03f0009551fdf0e08b813d2da9dccff224`
- robot_identity: `ba16d1977581e01edd9b36839eedc9c8e29b4255fb7f94576264cc4ef353899a`
- design_id: `two_segment_development`
- design_identity: `03f948b02a2f0b9eb368bdc3fb34e6c9575ede4334c118384652b339f7c357b4`
- gvs_dynamic_system_identity: `6c011094f89c77fe06656949c4d01535d9f2d6e2bfa122c58d06a888fa6f0d25`
- basis_identity: `56bba5caad5f7e62bea5ba3f85b75b16664a36c29a2ca99efcc0bef75601db71`
- historical_scene_identity: `5feb87766678e5339f6920ac6016303cc455238ba291f07b929c595424299215`

The reference is the Stage 3.10 audited state inherited from Stages 3.7–3.9. Saved gravity, stiffness, tendon lengths/Jacobian and component masses/COMs are reused. GVS backbone and attachment positions are evaluated once at that same state; the tip is checked against the saved reference to 1e-12 m. Source paths and SHA-256 hashes, all numeric identities, full vectors and matrices are in the JSON.

- q0 (rad/m, coordinate order in JSON): `[1.6129601362410086, -0.10549344917875342, -1.39660100515328, 0.2798787804538121, 0.04082170366393039, -0.13644731696793358, -5.248961441103909, -5.469003090633591, -7.285809868929822, 4.347871889413201, 3.614829121308677, 3.666467499018495]`
- u0 (N): `[1.7512764858409064, 4.755852667139922, 3.1031566686630025, 3.218253612486097, 0.7859357597552847, 0.6315302379791942]`
- Tendon order: `['near_t0', 'near_t1', 'near_t2', 'far_t0', 'far_t1', 'far_t2']`
- Gravity (world, m/s²): `[0.0, 0.0, -9.81]`
- Mount: `{"position_m": [0.0, 0.0, 0.15], "quaternion_wxyz": [1.0, 0.0, 0.0, 0.0]}`
- Basis: structural_linear, knots [0, 0.5, 1] on each segment, 12 coordinates.
- Integration: 24 steps per segment, partitioned at structural knots; unchanged.
- Quadrature: 5 Gauss points per structural-knot interval; unchanged.
- Historical finite-difference step: 1e-6; saved exact CasADi gravity and tendon Jacobian are reused.
- Runtime: Python 3.11.16, MuJoCo 3.13.0, NumPy 2.4.6.

## 3. Mapping semantics

`kappa(s) = B(s) q0` in physical segment y/z axes. For each cell, `qcell = R_x(phi_cell)[yz].T integral_cell B(s) ds q0`. The integral is evaluated exactly for the piecewise-linear basis by splitting at every crossed knot and integrating each linear piece. Segment ordering and compiler principal-section rotations are preserved. Curvature is rad/m; cell angles are rad.

This defines a constant matrix `J_N`, recorded in full: `qcell = J_N q0`, `Qg = J_N.T Qserial`, `K = J_N.T diag(k_hinge) J_N`, `D_length = D_serial J_N`. There is no tip fitting, optimization, or state-dependent force-map correction.

The public discretization helper uses whole-cell midpoint curvature. It is identical to this integral at 6/12/24 cells, checked numerically. At 3 cells the middle cell crosses s=0.5, where the curvature slope changes. Therefore the three-cell *physics* identity matches Stage 3.7 exactly, but its mapped angles and comparison errors differ from the historical midpoint baseline. The maximum angle change is 0.0054466243 rad. The same integral rule is applied at all four resolutions.

## 4. Resolution table

Absolute errors; vector norms are Euclidean and matrix norms are Frobenius. Gravity units are N·m²/rad, stiffness N·m³/rad², tendon Jacobian m²/rad.

| Cells/segment | Backend DOFs | Tip error (m) | Backbone RMS (m) | Far COM (m) | Gravity error | Stiffness error | Tendon Jacobian error |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 3 | 12 | 0.016939066 | 0.0075648721 | 0.0092149618 | 0.0013387391 | 0.00044065375 | 0.00026972839 |
| 6 | 24 | 0.0083498736 | 0.0035613414 | 0.0042361105 | 0.00065650673 | 0.00014144152 | 6.5163095e-05 |
| 12 | 48 | 0.0041397077 | 0.0017255804 | 0.0020245687 | 0.00032551203 | 3.5360866e-05 | 3.8238187e-05 |
| 24 | 96 | 0.0020573033 | 0.00084764453 | 0.00098633416 | 0.00016220938 | 8.8402467e-06 | 2.0491042e-05 |

Each JSON resolution row includes family.discretization data/identity, unchanged Design identity, generated physics identity, generated MJCF SHA-256, all mapped angles and per-cell parameters. XML is generated in memory with the existing compiler.

Successive error ratios (no acceptance tolerance):

| Metric | error6/error3 | error12/error6 | error24/error12 | Trend |
| --- | ---: | ---: | ---: | --- |
| tip_position_error_m | 0.492936 | 0.495781 | 0.496968 | CONVERGING |
| backbone_rms_error_m | 0.470774 | 0.484531 | 0.491223 | CONVERGING |
| backbone_max_error_m | 0.492362 | 0.495479 | 0.496799 | CONVERGING |
| total_mass_absolute_error_kg | 0.25 | 0.25 | 0.25 | CONVERGING |
| whole_robot_com_error_m | 0.462621 | 0.480697 | 0.488617 | CONVERGING |
| gravity_absolute_error | 0.490392 | 0.495824 | 0.498321 | CONVERGING |
| gravity_relative_error | 0.490392 | 0.495824 | 0.498321 | CONVERGING |
| stiffness_frobenius_error | 0.320981 | 0.250003 | 0.250001 | CONVERGING |
| stiffness_relative_error | 0.320981 | 0.250003 | 0.250001 | CONVERGING |
| tendon_length_error_norm_m | 0.293268 | 0.56205 | 0.52796 | CONVERGING |
| tendon_jacobian_absolute_error | 0.241588 | 0.586807 | 0.535879 | CONVERGING |
| tendon_jacobian_relative_error | 0.241588 | 0.586807 | 0.535879 | CONVERGING |
| tendon_jacobian_max_entry_error | 0.174048 | 0.654132 | 0.541588 | CONVERGING |
| mid_guide_com_error_m | 0.268056 | 0.334704 | 0.468936 | CONVERGING |
| connector_com_error_m | 0.268093 | 0.334794 | 0.468985 | CONVERGING |
| payload_com_error_m | 0.492623 | 0.495616 | 0.496872 | CONVERGING |
| far_segment_com_error_m | 0.459699 | 0.477931 | 0.487182 | CONVERGING |
| near_segment_com_error_m | 0.726462 | 0.571478 | 0.53696 | CONVERGING |
| mid_guide_position_error_m | 0.268056 | 0.334704 | 0.468936 | CONVERGING |
| connector_position_error_m | 0.268065 | 0.334726 | 0.468948 | CONVERGING |
| payload_position_error_m | 0.492362 | 0.495479 | 0.496799 | CONVERGING |
| near_t0_length_absolute_error_m | 0.779216 | 0.471972 | 0.487209 | CONVERGING |
| near_t1_length_absolute_error_m | 0.702812 | 0.483546 | 0.493034 | CONVERGING |
| near_t2_length_absolute_error_m | 0.452103 | 0.538467 | 0.517425 | CONVERGING |
| far_t0_length_absolute_error_m | 0.285052 | 0.581664 | 0.533143 | CONVERGING |
| far_t1_length_absolute_error_m | 0.0610182 | 0.987668 | 0.621804 | CONVERGING |
| far_t2_length_absolute_error_m | 1.18792 | 0.42314 | 0.45527 | NON_MONOTONIC |

## 5. Geometry convergence

Both backbones use the same 101 normalized material locations per segment (including endpoints), independent of N. MuJoCo positions are sampled along each straight cell centerline. RMS weights all 202 sampled points equally. All reported geometry errors decrease; the primary geometry errors approach first-order reduction (ratio about 0.5). Raw world positions and pointwise errors are in JSON.

| Metric | 3 cells | 6 cells | 12 cells | 24 cells |
| --- | ---: | ---: | ---: | ---: |
| backbone_max_error_m | 0.016947482 | 0.0083442955 | 0.0041344252 | 0.0020539768 |
| mid_guide_position_error_m | 0.0007110045 | 0.00019058905 | 6.3790863e-05 | 2.9913801e-05 |
| connector_position_error_m | 0.00071100994 | 0.00019059699 | 6.3797827e-05 | 2.9917849e-05 |
| payload_position_error_m | 0.016947482 | 0.0083442955 | 0.0041344252 | 0.0020539768 |

## 6. COM convergence

Flexible reference COMs are the saved GVS distributed-mass quadrature at q0. Serial COMs mass-weight MuJoCo body COMs; rigid COMs include their local offsets. Whole-robot COM includes all physical components, excluding the massless world/mount. All COM errors decrease. Rigid masses are invariant; flexible midpoint mass integration approaches the fixed GVS mass without changing density or sections.

| Metric | 3 cells | 6 cells | 12 cells | 24 cells |
| --- | ---: | ---: | ---: | ---: |
| near_segment_com_error_m | 0.00061799298 | 0.00044894831 | 0.00025656412 | 0.00013776477 |
| far_segment_com_error_m | 0.0092149618 | 0.0042361105 | 0.0020245687 | 0.00098633416 |
| mid_guide_com_error_m | 0.0007110045 | 0.00019058905 | 6.3790863e-05 | 2.9913801e-05 |
| connector_com_error_m | 0.00071102626 | 0.00019062082 | 6.3818721e-05 | 2.9929994e-05 |
| payload_com_error_m | 0.016840078 | 0.0082958179 | 0.0041115363 | 0.0020429086 |
| whole_robot_com_error_m | 0.0040182845 | 0.001858943 | 0.0008935883 | 0.00043662282 |

| Component | GVS mass (kg) | 3 cells | 6 cells | 12 cells | 24 cells |
| --- | ---: | ---: | ---: | ---: | ---: |
| near | 0.0442336245625 | 0.0442336245625 | 0.0442336245625 | 0.0442336245625 | 0.0442336245625 |
| mid_guide | 0.002 | 0.002 | 0.002 | 0.002 | 0.002 |
| connector | 0.003 | 0.003 | 0.003 | 0.003 | 0.003 |
| far | 0.015582 | 0.0155796666667 | 0.0155814166667 | 0.0155818541667 | 0.0155819635417 |
| payload | 0.01 | 0.01 | 0.01 | 0.01 | 0.01 |
| Total | 0.0748156245625 | 0.0748132912292 | 0.0748150412292 | 0.0748154787292 | 0.0748155881042 |

## 7. Gravity convergence

At zero velocity, isolate gravity as `-(bias(g)-bias(0))` with zero controls. Passive springs are not part of qfrc_bias. The zero-gravity bias and the difference between bias with u0 and zero controls are checked. All poses are contact-free. Virtual work maps the resulting backend vector into the same 12 GVS coordinates. Per-coordinate reference, backend and signed error vectors are in JSON. Gravity error approximately halves at each refinement.

| Metric | 3 cells | 6 cells | 12 cells | 24 cells |
| --- | ---: | ---: | ---: | ---: |
| gravity_absolute_error | 0.0013387391 | 0.00065650673 | 0.00032551203 | 0.00016220938 |
| gravity_relative_error | 0.22508357 | 0.11037914 | 0.054728667 | 0.027272428 |

## 8. Stiffness convergence

Use existing MuJoCo joint stiffness EI/ds and the identical mapping J_N. The reference is the saved GVS elastic tangent matrix; this is constitutive stiffness, not a tangent including gravity or tendon preload. The mapping is linear, so there is no extra Hessian term. Relative error falls approximately fourfold per doubling from 6 cells onward. No hinge stiffness is tuned. Full matrices are in JSON.

| Metric | 3 cells | 6 cells | 12 cells | 24 cells |
| --- | ---: | ---: | ---: | ---: |
| stiffness_frobenius_error | 0.00044065375 | 0.00014144152 | 3.5360866e-05 | 8.8402467e-06 |
| stiffness_relative_error | 0.1034852 | 0.033216793 | 0.0083043121 | 0.0020760852 |

## 9. Tendon convergence

Native MuJoCo tendon derivatives are composed with J_N in the frozen tendon order. Their force sign/order is checked by virtual work against actuator force at u0. The Jacobian norm, relative error and maximum entry error all decrease.

Signed length errors (backend minus GVS, m):

| Tendon | 3 cells | 6 cells | 12 cells | 24 cells |
| --- | ---: | ---: | ---: | ---: |
| near_t0 | 8.9721196e-06 | 6.9912199e-06 | 3.2996572e-06 | 1.6076241e-06 |
| near_t1 | 1.5457723e-05 | 1.0863871e-05 | 5.2531843e-06 | 2.589998e-06 |
| near_t2 | -1.5650749e-05 | -7.0757472e-06 | -3.8100564e-06 | -1.9714203e-06 |
| far_t0 | -0.0014351674 | -0.00040909752 | -0.00023795714 | -0.00012686524 |
| far_t1 | -0.00049506492 | -3.0207968e-05 | -2.9835431e-05 | -1.8551782e-05 |
| far_t2 | -0.00014991998 | 0.00017809302 | 7.5358193e-05 | 3.430833e-05 |

| Metric | 3 cells | 6 cells | 12 cells | 24 cells |
| --- | ---: | ---: | ---: | ---: |
| tendon_length_error_norm_m | 0.0015257245 | 0.00044744541 | 0.0002514868 | 0.00013277499 |
| tendon_jacobian_absolute_error | 0.00026972839 | 6.5163095e-05 | 3.8238187e-05 | 2.0491042e-05 |
| tendon_jacobian_relative_error | 0.050656798 | 0.012238066 | 0.0071813875 | 0.0038483549 |
| tendon_jacobian_max_entry_error | 0.00013195548 | 2.2966584e-05 | 1.5023179e-05 | 8.1363754e-06 |

far_t2 length error is NON_MONOTONIC: its signed error crosses zero between 3 and 6 cells and its magnitude initially grows, then falls at 12 and 24. far_t1 also has a nearly flat 6→12 length-error interval, followed by further reduction. Neither establishes a persistent nonzero plateau. A limited source inspection finds that compiler.py:78–80 binds s=0.5 to the middle cell interior at N=3 and a downstream cell origin for even N; lateral tendon offsets use that cell orientation. mjcf.py:40 and :68 attach both root hinges and sites to that body. Tendon site placement and cancellation of signed span errors are plausible causes of the coarse non-monotonicity, not demonstrated causes. No change or extra sweep was made.

## 10. Final classification

**DISCRETIZATION_CONVERGENCE_SUPPORTED — confidence HIGH.**

All six primary errors decrease at every refinement, as do every component COM/position error, the total mass error and aggregate tendon-length error. Geometry, COM and gravity show approximately first-order reduction; stiffness and mass show second-order reduction on the finer meshes. This supports finite serial discretization as a large contributor to the Stage 3.7–3.9 mismatch under the required integrated-curvature mapping. The single coarse tendon-length reversal does not overturn the consistent multi-quantity trend.

Trend labels describe these four measurements: strictly decreasing errors are CONVERGING; exact nonzero constants are PLATEAUING; reversals are NON_MONOTONIC; an exact zero invariant is INCONCLUSIVE for estimating a convergence rate. No pass/fail equivalence tolerances or composite score are introduced. Ratios and observed log2 orders are retained for independent interpretation.

Confidence applies to the observed finite-range trend for this robot and state. Four resolutions do not prove the infinite-resolution limit or equivalence at other states. The fixed 24-step GVS geometry can eventually impose a reference-error floor; it was not refined. At N=24, residual tip error is still about 2.06 mm and gravity relative error about 2.73%. The earlier three-cell mapping convention also contributes to the historical discrepancy.

Validation completed: syntax/import check, this diagnostic, and focused forward calculations for the four requested resolutions. No full test suite, simulations, additional resolutions, parameter changes, controllers or schema changes.

## 11. Recommended next step

Define a minimal cross-model equivalence contract and select practical fidelity levels from measured cost versus error, retaining per-tendon checks; no universal cell count is established here.

Reproduce from the repository root with the softagent environment:

```powershell
& 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe' runs/stage311_discretization_convergence_20260926/discretization_convergence.py
```
