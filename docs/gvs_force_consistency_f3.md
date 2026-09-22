# F3 signed static-force consistency (2026-09-22)

This analysis uses the unchanged `two_segment_development` robot, 24/16 near/far cells, the recomputed F2 `q0,u0`, and zero velocity. It calls `mj_forward` only; no dynamics integration or controller runs. The complete per-tendon Jacobian and virtual-work matrices are in `runs/gvs_static_consistency_f2_20260922/f3_force_report.json`.

## Force extraction

MuJoCo joint forces were projected with the existing exact cell-angle map `M = dq_cell/dq_GVS`; generalized forces use `tau_GVS = M.T tau_cell`. At zero velocity, `qfrc_passive` matches `-k(q-springref)` exactly. Disabling gravity at the same pose makes `qfrc_bias` exactly zero and leaves `qfrc_passive` unchanged, so `-qfrc_bias` is the gravity force here. `qfrc_actuator` matches `-J_tendon.T u` within `3.2e-17` N·m. Contacts and constraint forces are zero. The maximum GVS-versus-MuJoCo tendon-length Jacobian entry difference is `4.47e-5` m²/rad. MuJoCo force extraction and signs were correct.

The signed quantities below are generalized forces in the eight GVS coordinates, in N·m². `Δ` means MuJoCo minus GVS. Elastic is the positive restoring-force magnitude used in `net = tendon + gravity - elastic`.

| Coordinate | Elastic GVS | Elastic MuJoCo | Δ elastic | Gravity GVS | Gravity MuJoCo | Δ gravity |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| near.y0 | +0.01941420 | +0.01941420 | +0.00000000 | +0.00828225 | +0.00846870 | +0.00018645 |
| near.y1 | −0.00349439 | −0.00348833 | +0.00000607 | −0.00206358 | −0.00210162 | −0.00003803 |
| near.z0 | +0.00334135 | +0.00334135 | +0.00000000 | −0.00002136 | +0.00000452 | +0.00002588 |
| near.z1 | −0.00018913 | −0.00018881 | +0.00000033 | +0.00003484 | +0.00004358 | +0.00000873 |
| far.y0 | −0.01137580 | −0.01137363 | +0.00000217 | +0.00073154 | +0.00075446 | +0.00002292 |
| far.y1 | +0.00262638 | +0.00261557 | −0.00001081 | −0.00032497 | −0.00032887 | −0.00000390 |
| far.z0 | −0.00590221 | −0.00590169 | +0.00000052 | −0.00007046 | −0.00010561 | −0.00003515 |
| far.z1 | −0.00011482 | −0.00011474 | +0.00000008 | −0.00002426 | −0.00002451 | −0.00000025 |

| Coordinate | Tendon GVS | Tendon MuJoCo | Δ tendon | Net GVS | Net MuJoCo |
| --- | ---: | ---: | ---: | ---: | ---: |
| near.y0 | +0.01113195 | +0.01083979 | −0.00029217 | ≈0 | −0.00010572 |
| near.y1 | −0.00143081 | −0.00101105 | +0.00041976 | ≈0 | +0.00037565 |
| near.z0 | +0.00336272 | +0.00331089 | −0.00005183 | ≈0 | −0.00002595 |
| near.z1 | −0.00022398 | −0.00012184 | +0.00010214 | ≈0 | +0.00011054 |
| far.y0 | −0.01210735 | −0.01245456 | −0.00034721 | ≈0 | −0.00032646 |
| far.y1 | +0.00295135 | +0.00284855 | −0.00010279 | ≈0 | −0.00009589 |
| far.z0 | −0.00583174 | −0.00592179 | −0.00009004 | ≈0 | −0.00012571 |
| far.z1 | −0.00009056 | −0.00016916 | −0.00007860 | ≈0 | −0.00007892 |

The largest **projected** signed residuals are `near.y1` (+0.00037565) and `far.y0` (−0.00032646) N·m². Component difference norms are tendon `0.00064814`, gravity `0.00019680`, elastic `0.00001260` N·m². Thus the tendon term dominates the eight-coordinate comparison, but its sign and virtual-work implementation are correct.

## Actual source of static drift

The MuJoCo model has **80 independent hinge coordinates**. The GVS equilibrium imposes only eight virtual-work equations, `M.T F = 0`; it does not impose `F = 0` for all hinge coordinates. At the mapped q0, the full MuJoCo net force norm is `0.22898` N·m. Its component orthogonal to the GVS strain subspace is `0.22759` N·m (99.4% of the norm), with `M.T F_orthogonal` below `4.1e-19`. The orthogonal tendon contribution alone has norm `0.23175` N·m, compared with gravity `0.01539` and elastic `0.01630` N·m.

The largest cell residuals occur at `far_cell_8_y`, `near_cell_0_y`, `near_cell_12_y`, and `far_cell_0_y`. These are at or adjacent to the specified tendon start, midpoint guide, segment transition, and far midpoint guide locations. The specified straight-span tendon path applies localized loads there. The first-order GVS basis can balance their **projected** virtual work while independent cells can deform between guides. This explains why sub-1% F1 tendon Jacobian error in the GVS subspace coexists with a large full-cell static residual and drift.

No incorrect force sign, spring reference, stiffness conversion, gravity extraction, or tendon virtual-work mapping was found. Changing one of those terms would be an unsupported adjustment. Making the models share a static equilibrium requires an explicit change to their admissible deformation space: either constrain the backend to the first-order GVS strain manifold or enrich the reduced model to capture the independent-cell modes. The latter is explicitly excluded from this round; the former changes the backend's physical degrees of freedom and is larger than a local force-term correction. The frozen robot's sparse tendon guide locations cannot be changed as a mesh-dependent calibration.

**F2_STATIC_CONSISTENCY = FAIL** remains the valid classification for the unchanged model. The prior single F2 rollout found 5.241 mm initial geometry gap and 120.514 mm tip drift in 0.35 s under exact `u0` tension tracking. No corrected F2 rollout was run because F3 found no justified local physical correction; repeating the same integration would not test a new model. No continuation or LQR work was started.

The next development decision is a **remaining physical-model correction**: define how the backend and GVS model will share admissible deformation modes before using the discrete backend as a static-equilibrium validator. Control remains paused.
