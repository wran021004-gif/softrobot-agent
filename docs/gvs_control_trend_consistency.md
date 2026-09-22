# Small tendon control-trend comparison (2026-09-22)

This read-only model experiment compares **incremental initial acceleration** at a fixed pose, with zero initial velocity. GVS uses its tendon-length Jacobian, mass matrix, and tip Jacobian. MuJoCo uses its direct-tension actuator, `mj_forward` acceleration, and tip-site Jacobian. The baseline acceleration is subtracted before comparing a +0.1 N perturbation on one tendon. No time integration, equilibrium solve, controller, or optimization was run.

The physical `two_segment_development` robot and 24/16 near/far cell discretization are unchanged. States are straight `q=0`; moderate `q=[2,-1,1,0.5,-4,2,-2,1]` rad/m; and the saved high-curvature `q0`. The straight/moderate baseline is the design's 0.2 N pretension on all six tendons; the high-curvature baseline is the saved equilibrium `u0`. All perturbations remain below the 8 N tendon limits.

Unit tip vectors are `(world x, y, z)`. `Tip angle` compares GVS and MuJoCo incremental tip acceleration. `q angle` compares GVS incremental curvature acceleration with the existing projector applied to MuJoCo incremental joint acceleration. In the dominant-q column, `far.y1` abbreviates `far.kappa_y_1`, and likewise for `far.z1`. The complete eight-component normalized q vectors, acceleration magnitudes, and cosines are in `runs/gvs_static_consistency_f2_20260922/control_trend_report.json`. At straight near-tendon cases, the MuJoCo tip response norm is below `8e-13` m/s², so its direction and angle are undefined; the displayed GVS direction remains meaningful.

| State | Tendon | GVS tip unit vector | MuJoCo tip unit vector | Tip angle | Dominant q direction, GVS / MuJoCo | q angle |
| --- | --- | --- | --- | ---: | --- | ---: |
| Straight | near_t0 | (0,+0.96,+0.27) | undefined | undefined | far.z1+ / far.z1+ | 21.7° |
| Straight | near_t1 | (0,−0.56,+0.83) | undefined | undefined | far.y1− / far.y1− | 21.6° |
| Straight | near_t2 | (0,−0.36,−0.93) | undefined | undefined | far.y1+ / far.y1+ | 22.1° |
| Straight | far_t0 | (0,+0.75,+0.66) | (0,+0.73,+0.68) | 1.7° | far.z1+ / far.z1+ | 5.6° |
| Straight | far_t1 | (0,−0.95,+0.31) | (0,−0.96,+0.27) | 2.5° | far.z1− / far.z1− | 5.4° |
| Straight | far_t2 | (0,+0.05,−1.00) | (0,−0.03,−1.00) | 4.1° | far.y1+ / far.y1+ | 6.1° |
| Moderate | near_t0 | (−0.35,+0.91,+0.20) | (−0.97,+0.25,+0.02) | 54.8° | far.z1+ / far.z1+ | 21.9° |
| Moderate | near_t1 | (+0.75,−0.36,+0.55) | (+1.00,+0.06,+0.01) | 42.5° | far.y1− / far.y1− | 23.7° |
| Moderate | near_t2 | (−0.60,−0.23,−0.76) | (−0.98,−0.20,−0.03) | 48.7° | far.y1+ / far.y1+ | 23.3° |
| Moderate | far_t0 | (−0.11,+0.74,+0.66) | (−0.11,+0.71,+0.70) | 2.9° | far.z1+ / far.z1+ | 7.4° |
| Moderate | far_t1 | (−0.24,−0.92,+0.30) | (−0.21,−0.94,+0.26) | 2.9° | far.z1− / far.z1− | 7.7° |
| Moderate | far_t2 | (+0.24,+0.04,−0.97) | (+0.16,−0.04,−0.99) | 6.3° | far.y1+ / far.y1+ | 5.2° |
| High-curvature q0 | near_t0 | (0,+0.85,+0.52) | (+0.05,+0.91,+0.41) | 7.5° | far.z1+ / far.z1+ | 21.6° |
| High-curvature q0 | near_t1 | (−0.75,−0.63,+0.19) | (+0.35,−0.43,+0.83) | 80.0° | far.z1− / far.y1− | 28.1° |
| High-curvature q0 | near_t2 | (+0.70,−0.23,−0.68) | (−0.34,0,−0.94) | 66.4° | far.y1+ / far.y1+ | 25.5° |
| High-curvature q0 | far_t0 | (−0.71,+0.66,+0.26) | (−0.66,+0.69,+0.30) | 4.2° | far.y1− / far.z1+ | 17.5° |
| High-curvature q0 | far_t1 | (−0.57,−0.77,−0.29) | (−0.56,−0.71,−0.42) | 8.3° | far.z1− / far.z1− | 9.1° |
| High-curvature q0 | far_t2 | (+0.97,−0.21,−0.09) | (+0.95,−0.21,−0.24) | 8.7° | far.y1+ / far.y1+ | 10.1° |

Using clear tip alignment as at most 15°, 10 cases align: all nine far-tendon cases and high-curvature `near_t0`. Three moderate near-tendon cases are partly aligned (42–55°). Two high-curvature near-tendon cases are strongly inconsistent (66–80°), including opposite world-x signs. Three straight near-tendon cases have no measurable MuJoCo tip-acceleration direction. All 18 projected reduced-state comparisons have cosine at least 0.882 (angle at most 28.1°), but 98–100% of the full MuJoCo incremental joint acceleration lies outside the current GVS cell-angle subspace. Thus projected state agreement does not guarantee tip-direction agreement.

**CONTROL_TREND_CONSISTENCY = PARTIAL.** GVS captures the far-tendon tip trend and the projected curvature trend. It is not a reliable all-tendon tip-direction guide for MuJoCo at straight or high-curvature states. The strongest defined disagreement is high-curvature `near_t1` (80°; GVS world-x negative, MuJoCo positive), followed by `near_t2` (66°; world-x sign also opposite). The next modeling target is the near-tendon response of the independent-cell backend and the unresolved modes identified in F4. This result does not establish static-equilibrium accuracy or justify starting control.

Validation: three states × six tendon perturbations, one +0.1 N increment, three MuJoCo model loads while correcting the report's treatment of negligible tip responses, zero MuJoCo integration steps, zero MATLAB launches, and zero external LLM calls. No full test suite ran.
