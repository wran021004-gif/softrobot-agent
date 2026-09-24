# Stage 3.6: GVS-LQR attribution and local regulation

## Reproduction and scope

`controller_failure_attribution.py` reads the frozen Stage 3.5 Case B retry GVS and tip-feedback runs directly. It rebuilds the structural_linear DynamicSystem at the saved q0/u0, checks the saved DynamicSystem and linearization identities, and reuses the saved K, Q/R, projector and force limits. It uses no model requests and no MuJoCo solves. `local_control_experiment.py` uses the same saved robot, physics, control plans, 0.35 s duration, 0.01 s control interval and 0.0005 s MuJoCo step for six new local starts. No task, design, basis, gain or controller weights were changed.

The local starts are `q_initial=(1-f)*q0`, `qdot_initial=0`, with `f=0.01, 0.05, 0.20`; the exact resolved basis maps q to the serial-cell joint angles. The same state is supplied to both controllers for each f. The GVS operating point and tip target are unchanged. The tip-feedback controller has no tension request variable; its force entries below are measured tendon forces.

## Saved Case B chain and first command

The resolved basis has 12 q coordinates and 24 state coordinates. The operating tension has six channels; the saved Q diagonal is 1 for q and 0.1 for qdot, and R is the 6x6 identity. The projected straight initial state is zero, so `delta q=-q0`, `||delta q||=12.6736 rad/m`, and `delta qdot=0`. The full q0, u0, x0, A, B, K, Q/R and initial delta x are in `controller_failure_attribution.json`.

| Tendon | u0 N | Lower margin N | Upper margin N | First request N | First executed N | Case B lower / upper clips |
|---|---:|---:|---:|---:|---:|---:|
| near_t0 | 1.751 | 1.751 | 6.249 | 0.240 | 0.240 | 17 / 17 |
| near_t1 | 4.756 | 4.756 | 3.244 | 10.795 | 8.000 | 17 / 18 |
| near_t2 | 3.103 | 3.103 | 4.897 | -1.176 | 0.000 | 16 / 17 |
| far_t0 | 3.218 | 3.218 | 4.782 | 15.319 | 8.000 | 17 / 18 |
| far_t1 | 0.786 | 0.786 | 7.214 | 2.368 | 2.368 | 17 / 17 |
| far_t2 | 0.632 | 0.632 | 7.368 | -8.633 | 0.000 | 18 / 17 |

Every tendon has a nonzero margin at u0, but the initial correction exceeds four margins. In the saved MuJoCo run, at least one channel clips on **35/35 steps**, with **206/210 channel samples** clipped. The largest positive request is **116.251 N** and the most negative is **-89.311 N**, against `[0,8] N` bounds. The saved initial projection residual is zero; maximum projection residual over the run is `7.1e-15 rad/m` and maximum rate residual is `1.4e-13 rad/(m*s)`.

The reconstructed `A-BK` has maximum real eigenvalue **-3.176 1/s**, so the continuous unconstrained linear loop is asymptotically stable. The fastest eigenvalue is about `-397,229 1/s`, making explicit integration at the 0.5 ms backend step invalid for the model. The open-loop unstable-eigenvalue set is empty, so the public stabilizability test passes. The public unscaled controllability-matrix rank calculation reports 3 because powers of A span a huge numerical range; a column-normalized full-rank prefix reaches **24** with five powers. Neither rank number is a proof of practical control authority under force bounds.

## Four-level counterfactual

All levels start from the same projected straight state. L0 is the exact continuous linear solution. L1 is the continuous linear system with `[0,8] N` clipping. L2 integrates the existing nonlinear GVS dynamics with the same bounded law. L3 is the saved MuJoCo result, with no rerun.

| Level | Final `||x-x0||` | Final tip deviation from GVS equilibrium | Force-request evidence | Interpretation |
|---|---:|---:|---|---|
| L0 linear, unconstrained | 13.773 | 0.0332 m | First request reaches 15.319 N; no bound applied | Stable eigenvalues; q distance falls to 4.112 rad/m, while qdot remains 13.145 rad/(m*s) at 0.35 s. |
| L1 linear, bounded | 13.773 | 0.0332 m | Four sampled channels clipped | Nearly identical to L0 over this horizon. |
| L2 nonlinear GVS, bounded | 13.895 | 0.0321 m | Six channels clipped on the denser early sample grid | Full stiff integration completed; close to L1, with final q distance 4.072 rad/m. |
| L3 saved MuJoCo | 404.787 | 0.1948 m | 206/210 channel samples clipped | Large departure in backend. |

L0–L2 all reduce q distance substantially over 0.35 s, even though the full state norm is still elevated by qdot. L1 is almost identical to L0, so clipping alone in the *linear GVS model* does not reproduce Case B failure. L2 is also close to L1, so nonlinear GVS behavior at the distant start does not reproduce the backend failure either. The large discrepancy first appears in L3. L2 records extra 1 ms samples during the first 10 ms to resolve its transient, so its clipped-sample count is not directly comparable with L1's count. At the straight initial state, the nonlinear GVS bounded command produces a very stiff initial acceleration (about `6.4e6 rad/m/s²`); L2 therefore uses adaptive BDF with the GVS Jacobian, rather than an unstable fixed explicit step.

The initial backend force-balance probe at exactly the discretized GVS q0 and saved u0 measures the intended tensions, yet its tip is **16.743 mm** from the GVS predicted tip and its initial joint acceleration norm is **7,081.6 rad/s²**. Thus q0/u0 is a GVS equilibrium but **not a MuJoCo equilibrium**. This is direct evidence of a reduced-to-backend model discrepancy at the very operating point; it does not by itself identify which physical term differs.

## Saved tip-feedback comparison

The saved tip-feedback tip error falls from about 0.056 m to **0.02599 m**. It has zero actuator travel hits, zero tendon samples at or above 95% of the 8 N force limit, and maximum measured tension **3.116 N**. Its actuator rate limit is active on all 35 steps (channel 4 on 35 and channel 6 on 31). Its better reach result therefore comes with much less *force-limit* activation, while actuator rate limiting remains persistent. Tip feedback did not meet the 0.01 m task tolerance.

## Stage 3.6B: actual local backend behavior

All six runs complete numerically. Distances below are projected q distances from q0 at t=0 and t=0.35 s. Tip deviations use the saved GVS equilibrium tip. `Clip steps` counts a requested force outside `[0,8] N`; tip feedback has no requested force signal.

| Perturbation | Controller | q distance initial → final rad/m | Tip deviation initial → final m | Clip steps | Actual tendon samples at 8 N | Max requested / measured N |
|---|---|---:|---:|---:|---:|---:|
| 1% | GVS-LQR | 0.127 → 27.013 | 0.0160 → 0.2027 | 34/35 | 96/210 | 171.99 requested |
| 1% | Tip feedback | 0.127 → 7.768 | 0.0160 → 0.0319 | n/a | 2/210 | 8.00 measured |
| 5% | GVS-LQR | 0.634 → 25.870 | 0.0132 → 0.2039 | 34/35 | 96/210 | 169.74 requested |
| 5% | Tip feedback | 0.634 → 7.708 | 0.0132 → 0.0311 | n/a | 1/210 | 8.00 measured |
| 20% | GVS-LQR | 2.535 → 28.294 | 0.0040 → 0.2144 | 35/35 | 98/210 | 126.78 requested |
| 20% | Tip feedback | 2.535 → 7.485 | 0.0040 → 0.0291 | n/a | 0/210 | 7.92 measured |

Tip feedback has no actuator travel hits in these runs. Its actuator rate hits are 68, 64 and 65 channel samples for 1%, 5% and 20%. Every tendon in each local GVS-LQR run requests both lower-bound and upper-bound clipping; the per-tendon counts and full error trajectories are in each `summary.json`. GVS-LQR's q distance grows and its tip ends far from the target for every tested magnitude, with no settling trend over 0.35 s. Tip feedback is substantially better in tip position and force activation, but it also fails to regulate q around q0. Its tip trajectory is nonmonotonic; its smaller final error is not proof of settling. The tested **local operating envelope contains no demonstrated successful perturbation level**, including 1%. The initially smaller tip deviation at 20% reflects this particular curvature direction and the GVS/backend kinematic mismatch; it is not evidence that larger perturbations are easier.

## Attribution

| Hypothesis | Verdict | Evidence and limit |
|---|---|---|
| A. Gain / Q-R weights | PARTIALLY_SUPPORTED | The first request exceeds four force margins and the local backend requests reach 126–172 N. The continuous linear loop is stable. No weight sweep isolates an alternative gain. |
| B. Equilibrium / control authority | SUPPORTED | All Case B steps clip, including both lower and upper directions on every tendon; local LQR also clips on 34–35/35 steps. u0 is strictly inside each bound, but available correction is insufficient for these trajectories. |
| C. Distance from linearization point | PARTIALLY_SUPPORTED | The straight Case B start is 12.674 rad/m from q0. Failure also occurs at 1% q perturbation, so acquisition distance alone cannot explain it. |
| D. Projection | NOT_SUPPORTED | The structural_linear projection is exact to numerical precision for this 12-DOF serial-cell backend, including the saved trajectory. |
| E. Reduced versus backend dynamics | SUPPORTED | L0/L1/L2 are close, but L3 differs strongly. At discretized q0/u0, the MuJoCo tip differs by 16.743 mm and acceleration norm is 7,081.6 rad/s², despite matching applied tensions. The precise mismatched term remains unresolved. |
| F. Combined factors | SUPPORTED | Backend operating-point mismatch and persistent force clipping coexist; the saved and local comparisons do not apportion their relative contributions. |

Set-point acquisition from the distant straight start and local disturbance regulation are distinct questions. The local test does **not** validate GVS-LQR as a regulator around this backend state. The next scientific question is why the GVS static equilibrium disagrees with the serial-bending backend under the same nominal tension and whether a backend-consistent equilibrium has enough nearby authority. This stage makes no basis or Route change and does not start Case C.

The public `control.lqr_synthesize` path and the executable `gvs_lqr` build both assemble diagonal Q/R and call `ContinuousLQRController`; they duplicate small synthesis plumbing. This stage leaves that code unchanged because saved-chain analysis and local tests require no source refactor.

Checks: syntax compilation of both new Python scripts; exact saved DynamicSystem and linearization identity assertions; successful L1 and L2 integrations; six finite 700-step MuJoCo local runs; focused JSON assertions on saturation, projection and duration. The full test suite was not run. The complete Stage 3.6 artifact set is this directory, including six `local_runs/<level>/<controller>` folders with summaries, controller observations and compressed trajectories.
