# Stage 3.9: Do GVS and MuJoCo preserve one RobotIR interpretation?

## Executive conclusion

Both generators use the same frozen `family.design` robot and preserve scalar mass, rigid-body local inertials, tendon attachment definitions, material moduli, and actuator force sign. They **do not produce equivalent deformed spatial physics at the saved `q0`**. The three-cell serial model places downstream mass differently from GVS, gives a different gravity Jacobian, and predicts different tendon moment arms and effective bending stiffness. This is a geometry and discretization issue with multiple force consequences; it is not evidence for changing RobotIR material values.

The main suspected cause is **multiple causes**, with **medium confidence**. Geometry integration is the strongest upstream explanation for the observed COM and gravity differences. The same pose also has a separately measured stiffness-matrix gap. One pose cannot apportion all gravity difference between COM placement and gravity Jacobian shape effects.

## One immutable reference

The script uses the saved Stage 3.7 `q0/u0` and Stage 3.8 force comparison, with no new equilibrium solve. Robot identity `ba16d197...3899a`, GVS DynamicSystem identity `6c011094...f0d25`, resolved basis identity `56bba5ca...1db71`, backend discretization identity `152d5e04...7b6e`, and physics identity `0be5f7b2...a6b8d` are checked. The basis is `structural_linear`, the backend has three two-axis cells per segment, and gravity is `[0, 0, -9.81]` m/s². The full 12-value `q0`, six tendon tensions, and identities are in `physics_consistency.json`.

## Generation paths inspected

| Quantity | RobotIR source | GVS path | MuJoCo path |
| --- | --- | --- | --- |
| Geometry and sections | `family.design` component lengths, section stations and interpolation | `gvs.py`: continuous strain pose integrated over the structural-linear basis; `sections.py` gives local area and moments | `compiler.py`: equal-length cells, section sampled at each cell center; `mjcf.py`: rigid body and hinge tree |
| Mass and COM | Flexible: density and section imply mass/COM; rigid: explicit mass, local COM and inertia | `_mass_descriptors`: section mass and centroid at GVS quadrature points, plus rigid descriptors; `_observe_mass` places them on the continuous shape | `compiler.resolve`: `m=ρ A_mid ds`, local COM at `ds/2` plus section centroid; `mjcf.compile_xml` writes body inertials |
| Inertia | Flexible: derived from density, area moments and length; rigid: explicit tensor | Quadrature-point cross-section inertia and rigid tensors enter the generalized mass matrix | Cell cross-section inertia plus `m ds²/12` transverse terms; XML `fullinertia` |
| Gravity | Assembly gravity vector | `GVSModel → DynamicSystem`; CasADi computes `Σ m J_com.T g` using continuous poses | `robot.xml → MuJoCo`; `-qfrc_bias` at zero speed; body COM Jacobians reconstruct the same force |
| Stiffness | Material `E`, section bending area tensor and natural curvature | `∫ B(s).T E I(s) [B(s)q−κ₀] ds` by section/basis quadrature | Cell-center principal `E I / ds` as two hinge spring constants; XML joint `stiffness` and `springref` |
| Tendons | Ordered start/guide/anchor bindings and holes | Continuous attachment poses, straight spans, `-J_length.T u` | Compiler maps the same bindings into sites; XML spatial tendon and negative-gain direct tension actuator |

The actual source chain is `route.json:robot.structure.data → GVSModel → DynamicSystem` or `route.json:robot.structure.data → compiler.resolve → mjcf.compile_xml → saved robot.xml → MuJoCo`. The relevant source files are `extensions/tendon_family/gvs.py`, `gvs_casadi.py`, `sections.py`, `compiler.py`, and `mjcf.py`. No generation path was changed.

## Mass, COM, inertia, and gravity at `q0`

Flexible RobotIR does **not** store a single segment mass, COM or inertia tensor. These are derived from its density, length and interpolated cross sections. The near segment is a constant rotated ellipse (`E=8 MPa`, `ρ=1100 kg/m³`, length 0.16 m); the far segment is an interpolated rotated rectangle (`E=6 MPa`, `ρ=1050 kg/m³`, length 0.12 m). GVS uses ten mass quadrature samples per segment and 24 pose-integration steps per segment. The serial backend uses three midpoint-sampled bodies per segment. Rigid RobotIR mass, local COM and local inertia pass exactly into compiler parts and the XML model; maximum compiler-to-XML errors are zero for mass and local COM, and `3.68e-15` kg·m² for inertia.

The table gives **deformed world-frame** component COM and inertia comparisons at the same `q0`. Inertia difference is the Frobenius gap divided by the GVS component inertia norm. The JSON includes complete COM vectors and tensors.

| Component | GVS mass, kg | MuJoCo mass, kg | COM gap, mm | Inertia gap | Gravity-force gap, N·m² |
| --- | ---: | ---: | ---: | ---: | ---: |
| Near segment | 0.044233625 | 0.044233625 | 0.551 | 1.01% | `0.745e-3` |
| Mid guide | 0.002000000 | 0.002000000 | 0.906 | 0.11% | `0.063e-3` |
| Connector | 0.003000000 | 0.003000000 | 0.921 | 0.05% | `0.096e-3` |
| Far segment | 0.015582000 | 0.015579667 | 9.321 | 13.34% | `0.546e-3` |
| Payload | 0.010000000 | 0.010000000 | 16.673 | 1.24% | `0.378e-3` |

Total mass is 0.074815625 kg in GVS and 0.074813291 kg in MuJoCo, a `2.33e-6` kg difference (0.0031%). The far segment accounts for it: midpoint section sampling approximates its interpolated cross section. That small scalar difference cannot explain a 29.8% gravity generalized-force gap by itself. The far and payload world COM gaps track the previously measured 16.743 mm tip/shape discrepancy. Rigid local COM fields match, yet rigid *world* COMs differ because their parent flexible shape differs. Thus `MASS_MAPPING_MISMATCH` means **spatial mass placement at this deformed pose**; it does not mean RobotIR mass was lost or arbitrarily changed.

The script reconstructs GVS gravity by differentiating each saved quadrature COM pose and grouping by component. Its sum differs from the saved exact CasADi force by `2.85e-10` N·m². Summing MuJoCo body COM Jacobian forces differs from the projected `-qfrc_bias` by `1.96e-18` N·m². These checks establish that the following gravity gap reflects the actual model kinematics rather than force extraction.

| GVS coordinate | MuJoCo − GVS gravity force, N·m² |
| --- | ---: |
| `near.kappa_y_node_0` | `+2.206e-4` |
| `near.kappa_y_node_1` | **`+1.729e-3`** |
| `near.kappa_y_node_2` | `+1.822e-4` |
| `near.kappa_z_node_0/1/2` | `−4.97e-6`, `−3.12e-6`, `+5.18e-6` |
| `far.kappa_y_node_0/1/2` | `+4.23e-5`, `+2.359e-4`, `+3.81e-5` |
| `far.kappa_z_node_0/1/2` | `+2.49e-5`, `+5.92e-5`, `+1.74e-5` |

The dominant coordinate is `near.kappa_y_node_1`. Its `+1.729e-3` difference receives `+0.697e-3` from near mass, `+0.529e-3` from far mass, `+0.350e-3` from payload mass, and the remaining `+0.153e-3` from guide and connector. Bending at this near coordinate moves downstream bodies, so a large difference there does not imply a single incorrect near-segment mass. The total gravity vector gap is `1.771e-3` N·m².

**Gravity attribution:** wrong mass magnitude is not supported. Different deformed COM placement and geometry-dependent COM Jacobians are supported; the measured shape difference makes geometry integration the leading upstream explanation. Their separate contributions cannot be identified from this one state, so a standalone local-COM mapping defect is unresolved.

## Stiffness, tendon, and geometry consistency

The GVS material law and backend cell law both draw `E` and section bending moments from RobotIR. The compiler computes each cell's principal hinge constants as `E I_mid / ds`, and the XML joint stiffness exactly equals those values. GVS integrates its continuous `E I(s)` against the resolved basis. These are different discretizations of the same input: the mapped 12×12 stiffness matrices differ by **18.3%** in Frobenius norm, and elastic force at `q0` differs by `0.442e-3` N·m². Thus `STIFFNESS_MAPPING_MISMATCH` is supported at the model level, without evidence of a wrong XML spring value or wrong material modulus.

All six tendon start/guide/anchor bindings and ordering match RobotIR exactly. Direct actuators apply `u0` with correct sign. GVS and MuJoCo both use `-J_length.T u`, but their deformed tendon Jacobians differ; the maximum entry gap is `2.33e-4` m²/rad and the generalized-force gap is `1.390e-3` N·m². `far_t0` has the largest individual force gap (`1.281e-3` N·m²) and a 1.332 mm shorter backend length. Thus `TENDON_MAPPING_MISMATCH` refers to geometry and moment arms at `q0`, not route topology or actuator semantics.

The continuous backbone and serial cell geometry differ even though projection recovers `q0` to numerical precision. Maximum endpoint gaps are 1.237 mm near and 16.812 mm far; tip gap is 16.743 mm and tip orientation gap is 0.05261 rad. The MuJoCo engine and the serial geometry reader agree at numerical precision. The common section definitions and guide bindings therefore do **not** imply the same deformed pose under this three-cell discretization. `GEOMETRY_INTEGRATION_MISMATCH` is directly measured.

## Consistency verdict and next investigation

| Area | Result | Confidence |
| --- | --- | --- |
| Mass | `MASS_MAPPING_MISMATCH`: total mass nearly conserved, deformed COM/inertia differ | High for measurement; medium for origin |
| Gravity | `GRAVITY_MODEL_MISMATCH`: `1.771e-3` N·m², concentrated at `near.kappa_y_node_1` | High |
| Stiffness | `STIFFNESS_MAPPING_MISMATCH`: 18.3% mapped matrix gap | High |
| Tendon | `TENDON_MAPPING_MISMATCH`: same bindings/force sign, different Jacobian | High |
| Geometry | `GEOMETRY_INTEGRATION_MISMATCH`: 16.743 mm tip gap | High |

**Main suspected cause: multiple causes.** Geometry integration and associated spatial mass placement account for the shape/COM discrepancy and are strongly implicated in gravity and tendon Jacobian differences. Continuous versus hinge stiffness integration is an additional measured mismatch. The exact causal split among COM placement, COM Jacobians, and section quadrature remains unresolved.

Recommended next investigation: at this same `q0`, compare gravity **per GVS mass sample** with a geometry-matched discrete quadrature representation, while keeping the RobotIR material values and tendon bindings frozen. This would separate COM placement from kinematic Jacobian effects. It is a proposed experiment, not a model change.

Checks: syntax/import check and one `physics_consistency.py` run; one MuJoCo `mj_forward` at `q0`; comparisons with saved Stage 3.7/3.8 artifacts. No simulation sweep, full test suite, controller change, or physical-equation change.
