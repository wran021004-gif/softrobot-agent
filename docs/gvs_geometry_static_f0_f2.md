# GVS/serial-cell consistency, F0–F2 (2026-09-22)

Follow-up [F3 signed-force analysis](gvs_force_consistency_f3.md) shows that the
dominant full-cell residual lies outside the first-order GVS strain subspace.

The physical `two_segment_development` robot, mount, tip, target, and tendon routes were held fixed. Only the near/far cell counts changed. The three GVS states were zero; moderate `[2,-1,1,0.5,-4,2,-2,1]` rad/m; and the previous failed E1 equilibrium `q0`. All positions below use the same world mount. The segment orientation comparison removes the cell's principal-section frame rotation before comparing it with the GVS segment frame.

## A. F0 kinematic convergence

Errors are in mm for positions and radians for orientations. The two segment columns list near/far errors.

| GVS state | Cells near/far | Tip | Segment ends | Segment orientations |
| --- | ---: | ---: | ---: | ---: |
| Zero | 3/2 | 0 | 0 / 0 | 0 / 0 |
| Moderate | 3/2 | 5.590 | 9.184 / 5.597 | 0.0008 / 0.0343 |
| High curvature | 3/2 | 40.781 | 15.041 / 40.511 | 0.0082 / 0.2184 |
| Zero | 6/4 | 0 | 0 / 0 | 0 / 0 |
| Moderate | 6/4 | 3.042 | 4.669 / 3.039 | 0.0006 / 0.0177 |
| High curvature | 6/4 | 20.723 | 7.753 / 20.465 | 0.0040 / 0.1187 |
| Zero | 12/8 | 0 | 0 / 0 | 0 / 0 |
| Moderate | 12/8 | 1.588 | 2.356 / 1.584 | 0.0004 / 0.0089 |
| High curvature | 12/8 | 10.439 | 3.940 / 10.284 | 0.0020 / 0.0618 |
| Zero | 24/16 | 0 | 0 / 0 | 0 / 0 |
| Moderate | 24/16 | 0.813 | 1.185 / 0.810 | 0.0002 / 0.0045 |
| High curvature | 24/16 | 5.241 | 1.991 / 5.158 | 0.0010 / 0.0316 |

**F0_KINEMATIC_CONVERGENCE = PASS.** The high-curvature tip error roughly halves on each refinement. No kinematic semantic correction was needed. The 24/16 level is the first measured mesh with its worst tip error below 6 mm, leaving about 4.76 mm of the 10 mm reach tolerance for other errors. It has 80 hinge coordinates, versus 10 at 3/2, so the cost is substantially higher. The existing GVS-to-cell mapping/projector still round-trips with a maximum coordinate error below `1.1e-14` rad/m. MuJoCo tip positions match the serial geometry calculation to `1.1e-16` m at the selected mesh.

## B. F1 tendon geometry

Tendon order is `near_t0, near_t1, near_t2, far_t0, far_t1, far_t2`. The GVS reference uses the existing symbolic tendon path and CasADi automatic differentiation; the MuJoCo comparison uses its actual spatial tendon sites and `ten_J` chained through the existing cell-angle map. At 24/16, MuJoCo tendon lengths and Jacobians match the shared serial geometry calculation to numerical precision.

| State | Maximum length error | Maximum relative length error | Maximum absolute `dl/dq` error | Relative Jacobian norm error | Largest tendon / coordinate |
| --- | ---: | ---: | ---: | ---: | --- |
| Zero | < `1e-15` m | < `1e-14` | `2.14e-5` m²/rad | 0.43% | far_t2 / far.kappa_y_0 |
| Moderate | `0.0765` mm | 0.026% | `2.07e-5` m²/rad | 0.48% | far_t1 / far.kappa_z_0 |
| High curvature | `0.2353` mm | 0.086% | `4.47e-5` m²/rad | 0.85% | far_t2 / far.kappa_y_0 |

At high curvature, signed backend-minus-GVS length differences in tendon order are `[+0.03273,+0.02701,+0.03228,-0.22431,-0.23529,-0.11669]` mm. The complete GVS and backend lengths for all states are in `runs/gvs_geometry_consistency_20260922/report.json`.

**F1_TENDON_GEOMETRY = PASS.** The remaining length and Jacobian errors are small finite-cell errors; no tendon route correction was required.

## C. F2 static equilibrium

The trusted inverse-tip IPOPT and equilibrium refinement were rerun for the unchanged physical robot. They returned `q0 = [3.687431,-1.963256,0.880317,-0.311389,-16.000113,6.798085,-4.243816,-3.309072]` rad/m and `u0 = [6.856826,4.296876,6.044077,4.620509,5.914320,4.522017]` N. The GVS static residual norm was `2.43e-17`.

The 0.35 s MuJoCo rollout started at the mapped 24/16 state with zero velocity, constant direct tendon tension `u0`, no disturbance, and no controller feedback. The GVS tip was `[0.250000,0,0.150000]` m; MuJoCo started at `[0.247161,-0.003330,0.152884]` m, a 5.241 mm gap. It ended at `[0.127468,-0.011580,0.141521]` m, a 120.514 mm displacement from its initial tip; the maximum drift was the same. Desired and actual tendon tensions agreed at all recorded times. The maximum backend joint L2 drift was 0.7121 rad. Final projected GVS-coordinate drift was 19.6235 rad/m, and the maximum projection residual was 33.8806 rad/m. Tendon lengths changed by `[-0.014,-2.219,+2.392,-53.336,-37.981,-2.568]` mm. All states were finite. Replaying the saved states through `mj_forward` found zero contacts and zero constraint force at every saved state.

**F2_STATIC_CONSISTENCY = FAIL.** The initial spatial gap passes the 10 mm budget, but the equilibrium drift does not. No control work followed.

One initial-state force attribution gives GVS-coordinate mismatch norms: tendon `0.000648`, gravity `0.000197`, elastic `0.0000126`. The tendon term is still dominant, although it is about eleven times smaller than in the prior 3/2-cell E2 result. The projected MuJoCo net force is nonzero while the GVS net force is approximately zero. This identifies the remaining static force mismatch; it does not establish that tendon geometry alone explains the full nonlinear drift.

The model/backend consistency prerequisite remains unsatisfied. Control design should stay paused.

## Validation cost and reproduction

F0 used 12 kinematic cases (three states at four meshes); F1 used three tendon comparisons and one MuJoCo model at the selected mesh. F2 used one rollout, 35 control samples, and 700 MuJoCo integration steps. There were two MJCF XML compilations and four MuJoCo model loads including initial force attribution and contact replay. MATLAB launches: 0. External LLM calls: 0. No full test suite ran.

```powershell
conda run -n softagent python examples/gvs_geometry_consistency.py
conda run -n softagent python examples/gvs_static_consistency.py e1 runs/new_f2 --near-cells 24 --far-cells 16
conda run -n softagent python examples/gvs_static_consistency.py e2 runs/new_f2
```
