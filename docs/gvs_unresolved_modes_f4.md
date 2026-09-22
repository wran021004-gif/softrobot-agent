# F4 unresolved deformation modes (2026-09-22)

This analysis reuses the saved 24/16-cell F2/F3 equilibrium state: the same physical robot, `q0`, zero velocity, and `u0`. It projects the saved full MuJoCo force vector into the existing eight-coordinate GVS cell-angle subspace and its orthogonal complement. No MuJoCo integration or new equilibrium solve was performed. Full cell data are in `runs/gvs_static_consistency_f2_20260922/f4_unresolved_modes.json`.

## Spatial structure

The full joint-force residual norm is **0.22898 N·m**. Its component in the current GVS deformation subspace is **0.02511 N·m**; the unresolved component is **0.22759 N·m**, or **99.4%** of the full norm. These are orthogonal components in the common 80-joint torque coordinates.

The table lists the strongest unresolved cells. Arc position is measured from each segment's start. Signs refer to the cell's principal bending axes. The specified tendon routes have a midpoint guide at normalized arc position 0.5 on both segments; the far segment begins at the near/far transition.

| Segment | Cell | Arc center (m) | Principal y (N·m) | Principal z (N·m) | Nearby feature |
| --- | ---: | ---: | ---: | ---: | --- |
| far | 8 | 0.06375 | −0.09343 | −0.03333 | Midpoint tendon guides |
| near | 0 | 0.00333 | +0.07461 | −0.00947 | Base/tendon starts |
| near | 12 | 0.08333 | +0.06557 | −0.00823 | Midpoint tendon guides |
| far | 0 | 0.00375 | −0.05572 | −0.01664 | Segment transition |
| far | 4 | 0.03375 | +0.04981 | +0.01293 | Between guides |
| far | 3 | 0.02625 | +0.04813 | +0.01583 | Between guides |
| near | 6 | 0.04333 | −0.04731 | +0.00627 | Between guides |
| near | 5 | 0.03667 | −0.04465 | +0.00603 | Between guides |
| near | 7 | 0.05000 | −0.04344 | +0.00568 | Between guides |
| far | 7 | 0.05625 | −0.03732 | −0.01891 | Before midpoint guides |
| near | 13 | 0.09000 | +0.04023 | −0.00551 | After midpoint guides |
| far | 9 | 0.07125 | −0.03984 | −0.00460 | After midpoint guides |

The top four cells account for **44.9% of unresolved squared magnitude**. Cells at guide, segment start, or segment end locations account for **46.1%**. Principal y bending accounts for **93.3%** of unresolved squared magnitude. Neighboring cells form broad same-sign lobes and change sign across guide regions; the pattern is neither a simple global quadratic bend nor alternating cell-scale noise. The specified point guides and straight tendon spans concentrate load at physical route locations, while the independent cells can deform between them.

## Small basis tests

The existing constant-plus-linear GVS bending basis was compared with two one-term additions per bending direction and segment, using the same cell-angle virtual-work map. These are projection diagnostics only; no dynamics model was changed.

| Basis | GVS coordinates | Unresolved norm (N·m) | Reduction from current |
| --- | ---: | ---: | ---: |
| Constant + linear | 8 | 0.22759 | — |
| Add global quadratic `P₂(2s/L−1)` | 12 | 0.22516 | 1.1% |
| Add guide-aligned kink `max(0,2s/L−1)` | 12 | 0.22290 | 2.1% |

Neither minimal enrichment materially absorbs the missing force. A localized basis concentrated at the guides would need a physical support width or a richer set of modes; choosing either from this single force state would be an empirical fit. Constraining MuJoCo's independent cells to the eight GVS modes would remove real degrees of freedom without evidence that the intended robot is physically constrained that way. Redistributing the specified guide forces would likewise change the physical tendon route. No justified small correction follows from F4.

## Branch result

The unresolved residual has not been reduced enough to justify a corrected static rollout. The existing result remains **F2_STATIC_CONSISTENCY = FAIL**: at `q0,u0`, initial GVS/MuJoCo tip gap was 5.241 mm, final and maximum tip drift were 120.514 mm, maximum joint drift was 0.7121 rad, final projected GVS drift was 19.6235 rad/m, and maximum projection residual was 33.8806 rad/m. Constant direct tendon tensions tracked exactly. The full-order initial static residual was 0.22898 N·m, including 0.22759 N·m unresolved by GVS.

No continuation, LQR, or frozen `reach_free` evaluation was run. The next step is a **further physically justified deformation-space correction**: specify how tendon-guide forces are distributed and which local bending modes the physical arm admits, then encode the same assumptions in both models. One more arbitrary polynomial enrichment is not supported by these data.
