# Settled-shape fit and load check (2026-09-22)

The focused diagnostic is `examples/gvs_settled_shape_fit.py`; its local data
artifact is `runs/gvs_settled_shape_fit_20260922.json`. It replays only the
saved 24/16-cell `q0,u0` zero-disturbance setup, until every flexible joint
rate stays below 0.001 rad/s for 0.1 s. The run reaches that condition at
1.6045 s. The recorded maximum joint rate is 0.000485 rad/s, and the
joint-velocity L2 norm is 0.001004 rad/s. The zero-velocity full-cell force
residual at that pose is 0.000119 N m. The
settled tip is 120.999 mm from the original GVS target; the original mapped
MuJoCo tip was 5.241 mm from it. No design or tendon command changed.

The target samples are the cell-boundary centerline points in the same world
frame as the GVS mount, at 25 near and 17 far stations. The current eight
coordinates were fitted with the exact GVS pose integration. A guide-aligned
12-coordinate diagnostic adds one `max(0,2s/L-1)` curvature mode for each bend
axis and section. Both 8D and 12D were also fitted through the same 24/16-cell
geometry to make their comparison independent of discretization error.

| Representation | Centerline RMS | Centerline maximum | Tip error | Far curvature RMS mismatch |
| --- | ---: | ---: | ---: | ---: |
| Original GVS `q0` | 42.27 mm | 109.58 mm | 121.00 mm | — |
| Best exact 8D GVS fit | 2.29 mm | 7.02 mm | 13.61 mm | — |
| Best 8D fit in common cell geometry | 2.00 mm | 5.63 mm | 11.16 mm | 13.39 rad/m |
| Best 12D guide-kink fit in common cell geometry | 1.28 mm | 3.23 mm | 2.39 mm | 11.86 rad/m |

The 8D best-fit coordinates and their difference from `q0` are in the artifact.
The original shape error is concentrated in the far section (66.39 mm RMS,
versus 1.97 mm near). After fitting, the far tip and guide neighborhood remain
the weak points. A position fit can be close while curvature remains wrong:
the 12D maximum far-cell curvature discrepancy is 31.00 rad/m, at cell 8
beside the midpoint guide.

At the exact 8D fitted state under the unchanged `u0`, GVS net static force is
0.003482 N m². MuJoCo, constrained only for this diagnostic to the same 8D
cell-angle state, gives 0.003297 N m². Their net difference is 0.000928 N m²;
its tendon, gravity, and elastic component differences are respectively
0.000959, 0.0000995, and 0.0000314 N m². Thus both models say the 8D shape
that best represents the settled centerline is not an equilibrium. The small
model-to-model difference is consistent with the previously measured finite
cell tendon Jacobian error; it does not identify missing guide-load physics.

The 12D fit has projected MuJoCo net force 0.004840 N m². Solving its
12-dimensional constrained MuJoCo equilibrium reduces that force below
`4e-9` N m² but leaves 16.24 mm centerline RMS and 49.69 mm tip mismatch
against the freely settled 80-coordinate shape. The extra four guide modes
therefore improve *representation* but do not establish a common equilibrium.
The prior full-force projection showed 99.4% of the initial 0.22898 N m
residual outside the 8D subspace (0.22759 N m outside versus 0.02511 N m
inside), and one guide-kink term absorbed only 2.1%
of its unresolved norm. The settled curvature data confirm that the remaining
far-section local modes matter physically.

GVS computes each tendon length as a sum of straight, frictionless spans
through the RobotIR start, guides, and anchor, then applies `-J_length.T u`.
MuJoCo uses spatial tendon sites at the same route points and direct tension;
the tendon Jacobian applies the direction-change guide reactions through
virtual work. The saved F3 force check verified its `qfrc_actuator` against
`-J_length.T u` to numerical precision. There is no identified missing load
term to repair. A correction vector or a changed guide force would change
the specified physical routing without evidence.

**Root cause: `STATE_SPACE_LIMITATION`. Endpoint:
`PHYSICS_MODEL_REFINEMENT_REQUIRED`.** No physical model code was changed.
The small guide-aligned enrichment does not make `q0,u0` a common operating
point, so a larger, explicitly justified local deformation basis is needed
before shared control experiments. This round did not rerun LQR or launch the
next design-system validation.
