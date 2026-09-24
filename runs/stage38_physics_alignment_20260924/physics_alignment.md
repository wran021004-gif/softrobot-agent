# Stage 3.8: GVS–MuJoCo physics term alignment

## Scientific question and frozen reference

Why does the saved GVS equilibrium fail to balance the serial-bending/MuJoCo backend under the same tendon tensions? This diagnostic measures forces and geometry at **one** configuration; it does not tune or change either model.

The reference is the Stage 3.7 `q0/u0` and `structural_linear` basis. Robot identity is `ba16d197...3899a`, resolved basis identity is `56bba5ca...1db71`, backend discretization identity is `152d5e04...7b6e`, and the frozen physics identity is `0be5f7b2...a6b8d`. The backend has three two-axis cells per flexible segment, 12 hinge coordinates, and gravity `[0, 0, -9.81]` m/s². The full robot, basis, geometry, sections, compiled hinge stiffness, and identities are in `physics_alignment.json`.

| Item | Frozen value |
| --- | --- |
| `q0`, rad/m | `[1.612960, -0.105493, -1.396601, 0.279879, 0.040822, -0.136447, -5.248961, -5.469003, -7.285810, 4.347872, 3.614829, 3.666467]` |
| Tendon order | `near_t0`, `near_t1`, `near_t2`, `far_t0`, `far_t1`, `far_t2` |
| `u0`, N | `[1.751276, 4.755853, 3.103157, 3.218254, 0.785936, 0.631530]` |
| Material | Near: `E=8 MPa`, `ρ=1100 kg/m³`; far: `E=6 MPa`, `ρ=1050 kg/m³`; natural curvature zero |

GVS terms are the exact CasADi force outputs evaluated at this operating point in Stage 3.7, where the DynamicSystem and linearization identities were verified. This script rechecks robot, basis, physics, q mapping, tendon bindings, and the saved backend force vectors. MuJoCo terms are **directly read** from `qfrc_bias`, `qfrc_passive`, and `qfrc_actuator` after `mj_forward`; multiplication by the saved `M.T` reconstructs forces in GVS coordinates. The decomposition is valid here at zero velocity, without contacts or constraint force. The continuum model has no directly comparable per-body gravity breakdown in these saved outputs, so geometry and mass effects within gravity are **not** separately inferred.

## Controlled force decomposition at `q0`

The three MuJoCo queries retain the same `q0`, zero velocity, XML, and cell mapping. Gravity-only sets direct tension controls to zero and reads `-M.T qfrc_bias`. Tendon-only sets model gravity to zero, retains `u0`, and reads `M.T qfrc_actuator`. Elastic-only sets both gravity and direct tensions to zero and reads `-M.T qfrc_passive`. Other passive effects remain in the model during each query but are excluded from the named measured force. The isolated terms reproduce the original full-state terms to numerical precision. GVS terms are read from the saved Stage 3.7 evaluation; their tendon term is linear in `u0` and their elastic term is independent of gravity and tendon force.

Generalized forces use N·m² because the GVS coordinates are curvature in rad/m. Elastic is the positive restoring term in `residual = tendon + gravity - elastic`.

| Term | `||GVS||` | `||MuJoCo||` | `||MuJoCo − GVS||` | Relative gap |
| --- | ---: | ---: | ---: | ---: |
| Gravity | `5.948e-3` | `7.526e-3` | **`1.771e-3`** | 29.8% |
| Tendon | `7.053e-3` | `8.137e-3` | **`1.390e-3`** | 19.7% |
| Elastic | `4.117e-3` | `4.133e-3` | **`0.442e-3`** | 10.7% |
| Total residual | `1.60e-17` | `1.242e-3` | `1.242e-3` | undefined at zero GVS residual |

The JSON records all signed 12-coordinate vectors. The gravity difference is the largest individual gap and contributes 107% of the measured residual along that residual's direction; tendon and elastic differences each partly oppose it. A counterfactual with **only** the gravity term changed from GVS to backend has residual norm `1.771e-3` N·m², so gravity mismatch alone is sufficient to break the GVS equilibrium. Conversely, keeping GVS gravity but using the backend tendon and elastic terms leaves `1.174e-3` N·m², about 94.5% of the observed residual norm. Gravity is therefore **not** the only consequential discrepancy. These are one-pose additive force substitutions, not independent physical rollouts.

### Tendon force and geometry

The tendon order, physical attachment and guide bindings, pretension, and force limits match exactly. MuJoCo direct actuators produce the requested six tensions; the Stage 3.7 virtual-work check found a `1.39e-17` N·m maximum actuator sign/Jacobian error. The mismatch is in the length Jacobians at the transferred pose, not in applied tension or tendon topology.

| Tendon | Backend − GVS length, mm | Difference in its generalized force norm, N·m² |
| --- | ---: | ---: |
| `near_t0` | +0.007 | `0.348e-3` |
| `near_t1` | −0.015 | `0.961e-3` |
| `near_t2` | +0.015 | `0.607e-3` |
| `far_t0` | −1.332 | `1.281e-3` |
| `far_t1` | −0.497 | `0.257e-3` |
| `far_t2` | −0.174 | `0.178e-3` |

The `far_t0` contribution is the largest individual tendon gap. Per-tendon vector differences partly cancel, leaving the total tendon gap of `1.390e-3` N·m². Even near tendons with almost equal lengths have different derivatives, so matching length alone would not establish matching force. The largest tendon Jacobian entry difference is `2.33e-4` m²/rad.

### Elasticity and mass

The elastic force directions remain close: cosine similarity is 0.9989 on `near` and 0.9951 on `far`. The near and far elastic force difference norms are `0.220e-3` and `0.384e-3` N·m². The effective GVS and mapped hinge stiffness matrices differ by 18.3% in Frobenius norm; each reproduces its own elastic force at `q0`. This supports a discrete stiffness representation difference, without evidence of an incorrect material value or spring sign.

Total mass matches to rounding for `near`, guide, connector, and payload. The far segment differs by only `2.33e-6` kg out of about `0.01558` kg (0.015%). Thus missing total mass does not explain the gravity-force gap. Different mass placement, Jacobians, and integration remain possible causes; this experiment does not separate them.

### Shape and pose

MuJoCo's static serial geometry reproduces its engine tip and tendon lengths to about `1e-16` m, so the comparison is not an artifact of the geometry reader. At the same mapped coordinates, maximum cell-endpoint gaps from GVS are 1.237 mm (`near`) and 16.812 mm (`far`). Segment-end orientation gaps are 0.00202 and 0.05261 rad, respectively. The tip position gap is 16.743 mm and the tip orientation gap is 0.05261 rad. This directly establishes `GEOMETRIC_INTEGRATION_MISMATCH` at the common coefficient state. The saved projection recovers `q0` to numerical precision, so the algebraic coordinate transfer is sound.

## Attribution and next step

| Physical term | Difference magnitude | Attribution |
| --- | ---: | --- |
| Gravity | `1.771e-3` N·m² | Largest individual force gap; sufficient to break equilibrium alone. `GRAVITY_MODEL_MISMATCH`. |
| Tendon | `1.390e-3` N·m² | Large Jacobian-driven gap; remaining mismatch is substantial without gravity gap. `TENDON_FORCE_MISMATCH`. |
| Elasticity | `0.442e-3` N·m² | Smaller force gap, with an 18.3% effective stiffness-matrix gap. `STIFFNESS_MODEL_MISMATCH`. |
| Geometry | 16.743 mm tip, 0.05261 rad tip orientation | Direct shape and pose discrepancy at identical coefficients. `GEOMETRIC_INTEGRATION_MISMATCH`. |

**PRIMARY_CAUSE: multiple. CONFIDENCE: medium.** Gravity is the largest immediate force mismatch, but tendon and stiffness differences together would still leave a large unbalanced force. The upstream physical explanation is a reduced continuous shape versus three-cell serial shape, plus different effective gravity and stiffness representations. Exact portions attributable to geometry integration versus mass placement are unresolved; the measured total masses alone cannot resolve them.

Recommended next step: perform a single controlled geometry/mass diagnostic at this same `q0`, comparing each body's center-of-mass position and gravity Jacobian with GVS quadrature mass samples. Keep tendon routing and material parameters frozen. This would distinguish geometric Jacobian error from mass placement without fitting a correction.

Checks: syntax/import compilation and one execution of `physics_alignment.py`; four `mj_forward` force queries at the same configuration; no dynamics rollout, parameter sweep, full test suite, or production source change.
