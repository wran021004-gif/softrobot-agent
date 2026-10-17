# S5.5 model fidelity and S5-T mathematical sensitivity

Starting branch `feat/sorosim-matlab-nmpc`, commit
`7000e900568a5b5778265968dd8f8861d32cb130`.

## P0: prospective scientific identity and saved PPO failures

The new preflight compares the resolved robot, compiled physical scene identity,
task and seed, controller/model, runtime identity, and either the complete ordered
fixed-tension grid or RL mode, binding, residual reference and checkpoint policy
hash. Store artifact IDs, study names and paths are excluded from the scientific
signature. For NMPC the numerical environment is included. Missing effective
fields produce an unresolved comparison and a possible repeat is withheld from
execution. The preflight runs before the public plan or backend reservation;
an explicit confirmation remains admitted under the existing confirmation grant.
The saved preflight returns the proposed identity, exact equal categories and
differing paths, prior identities and outcomes, and repeat admission status.

The [read-only equivalence audit](../../evidence/sorosim_s55/p0_equivalence.json)
finds the S5-Agent NMPC launch equivalent to S5-B and its fixed-tension replay
equivalent to S5-A. It also recognizes the original direct and residual PPO
evaluations independently. All four comparisons retain the prior `valid_failure`
or task-failure outcome. Changing a physical tension, robot, seed, RL mode or
checkpoint hash changes the appropriate signature. This is a configuration
comparison, not a claim that physical executions are deterministic.

The [PPO classification](../../evidence/sorosim_s55/p0_ppo_diagnosis.json) reads
all 260 original direct failure JSON, JSONL and NPZ captures. Saved interval
start states were reconstructed with `mj_setState` and `mj_forward`, with zero
physics steps; reconstructed tip-speed norms match the snapshots exactly. No
checkpoint or training record was modified.

| Recorded training fact | Direct | Residual |
|---|---:|---:|
| Attempted actions | 32,768 | 32,768 |
| Complete episodes | 782 | 936 |
| Numerical-failure episodes | 260 | 0 |
| Engine time reset captures | 260 | 0 |
| `mjWARN_BADQVEL` | 207 | 0 |
| `mjWARN_BADQACC` | 52 | 0 |
| `mjWARN_BADQPOS` | 1 | 0 |
| Explicit nonfinite-state/observation captures | 0 | 0 |

The 260 direct failures occurred at episode actions 18–27; 249 occurred at
actions 18–22. They occurred across all four consecutive 8,192-action training
quarters: 104, 88, 29 and 39. The failing physics substeps span 1–20. No
capture records action clipping or tension saturation. At failure interval
starts the per-channel tension extrema were approximately 3.23–4.90 N and the
median tip speed was 1.155 m/s. One saved state has an extreme finite speed of
about 3.42e10 m/s; it is reported as an instability outlier, not treated as a
normal task sample. The saved last-valid-action reward median is about -429;
reward magnitude is a training signal, not an independent acceptance metric.

`TensionEnv.fail()` increments `failed_episodes` for an invalid MuJoCo
transition, restores the interval's last valid boundary, and returns a terminal
surrogate observation with the frozen failure penalty of -10,000 and
`valid_physical_transition=false`. A normal complete episode that misses reach
or holding thresholds increments `complete_episodes`, not `failed_episodes`.
The independent `checks.run_episode()` excludes the terminal surrogate from
physical trajectory evidence. Direct and residual remain separate available
controller routes. The saved correlation with the middle episode phase does
not establish whether state, action, physical stiffness, or their interaction
caused the warnings. A next RL investigation should first inspect pre-failure
joint states and force/acceleration growth against stable direct episodes;
further training is not supported by this audit alone.

P0 incurred zero new model requests, mathematical integrations, physical
rollouts, and PPO actions. The only numerical work was read-only identity
construction and saved-state kinematic reconstruction.

## P1: fixed-sequence integration refinement

The candidate-bound `refine` action now reserves one mathematical replay slot
per resolution in the original research ledger. Its typed request accepts the
archived verified Design B trajectory and a declared substep count. The worker
checks model, design, task, coordinate, channel, initial-state, force-bound and
35-command/36-time identities before constructing SoRoSim. `sr_diagnose` uses
the existing implicit-Euler residual and root Jacobian for each substep, records
every root outcome, and samples outputs only on the original task clock. A root
failure preserves the last completed sample, failing state and residual, and
cannot be reported as task success. A complete result includes every sampled
state and world tip output, original-constraint violations, root count, force
residual, wall time, and exact trajectory/control hashes. The sparse study grant
allocates at most four refinements and zero physical, PPO, full-NLP or provider
work.

The pinned upstream commit was fetched into an ignored local checkout and
verified exactly. MATLAB R2024a starts outside the filesystem sandbox; its
static code check accepted the changed solver and diagnostic files. The
[P1 result](../../evidence/sorosim_s55/p1_refinement.json) preserves all
three newly charged integrations and the historical one-substep outputs.

| Same 35 commands and 36 original sample times | One substep | Two | Four | Eight | Optional 16 |
|---|---:|---:|---:|---:|---:|
| Root-complete integration | Historical yes | No: stopped at interval 7, substep 2 | Yes: 140 roots | Yes: 280 roots | Unrun |
| Original sampled mathematical task | Feasible witness | Unavailable beyond 0.06 s | Failed | Failed | Unknown |
| Maximum holding speed (m/s) | 0.000113989 | Unavailable | 0.593457 | 0.723387 | Unknown |
| Maximum holding position error (m) | 0.000056429 | Unavailable | 0.019057 | 0.022767 | Unknown |

The first two-substep attempt stopped because `fsolve` returned exit flag
-3 at interval 7, substep 2 despite a finite state and full residual
1.7694e-13. That is a diagnostic gate error, not evidence of a failed
implicit equation. The corrected gate accepts finite roots with full
residual below 1e-9 and retains every solver flag. The first partial attempt
remains charged and was not rerun. The four- and eight-substep attempts used
the committed correction and completed with maximum full root residuals
1.003e-12 and 1.464e-12; both have zero nonpositive exit flags.

At 0.29–0.30 s the one-to-four-substep maximum tip velocity vector
difference is 0.593381 m/s. Four-to-eight still differs by 0.132965 m/s
in that window and 0.004036 m in tip position over 0.25–0.29 s. The
original striking one-substep brake does **not** persist at either complete
refinement. Both finer models violate the original holding speed and
position bounds with unchanged controls. The four-to-eight gap remains
material, so the sequence is classified as **strongly sensitive, not yet
converged**; it does not prove any continuous-time task infeasibility. The
public study operation grant was exhausted by candidate version rebinding,
so the optional 16-substep follow-up was not launched. The frozen S4.5
one-substep feasibility claim remains valid for that discrete model.

## P2: archived-state projection and matched intervals

The [read-only S5-A state audit](../../evidence/sorosim_s55/p2_projection_audit.json)
uses its exact saved XML and 48 joint positions/rates at 0, 0.15 and 0.29 s.
`mj_forward` reproduces each archived tip position and velocity from those
saved joint values. The existing GVS projector and inverse discretization
give these **MuJoCo kinematic representation** differences:

| Saved time | Reconstructed joint curvature residual (rad/m) | Tip position difference (m) | Tip velocity difference (m/s) |
|---|---:|---:|---:|
| 0.00 s | 0 | 0 | 0 |
| 0.15 s | 24.650479 | 0.006075352 | 0.119151954 |
| 0.29 s | 15.299266 | 0.002142288 | 0.042359836 |

These are projection/reconstruction effects inside MuJoCo kinematics; they
are not yet SoRoSim-versus-MuJoCo matched-state errors. The archived samples
record time, joint positions and rates, but omit the 48-value MuJoCo
`qacc_warmstart`. The next interval's four control values and zero applied
external forces are known. The model has no activation, plugin, mocap, history,
or equality state. The contained P2 prefix playback reconstructed that
warmstart and matched every archived saved joint state and tip output through
0.30 s. It used 540 MuJoCo steps to reach the three checkpoints and 60
steps for the three measured following intervals. The 0.29 s state uses
command index 29 over `[0.29, 0.30]` s. Every actual applied tension matched
the recorded command. No new complete 35-interval task rollout occurred.

The [P2 matched-state evidence](../../evidence/sorosim_s55/p2_matched_state.json)
links the [sealed P2 study](../../evidence/sorosim_s55/matched_state_study/archive_manifest.json)
and reports full signed world-frame position and velocity vectors for
`e_projection`, `e_one_step` and `e_increment`. Each checkpoint was projected
through the existing GVS map and integrated for one 0.01 s interval with the
same physical tension at four and eight SoRoSim substeps. All six mathematical
intervals completed with maximum full implicit root residual below 1.5e-12.

| Saved start time | 8-substep initial projection, position / velocity | 8-substep one-step, position / velocity | 8-substep increment, position / velocity | 4-to-8 predicted end difference, position / velocity |
|---|---:|---:|---:|---:|
| 0.00 s | 0 m / 0 m/s | 0.000302 m / 0.008835 m/s | 0.000302 m / 0.008835 m/s | 0.000312 m / 0.022599 m/s |
| 0.15 s | 0.014843 m / 0.232082 m/s | 0.016844 m / 0.434798 m/s | 0.003908 m / 0.244622 m/s | 0.000341 m / 0.018762 m/s |
| 0.29 s | 0.003864 m / 0.125358 m/s | 0.002954 m / 0.066699 m/s | 0.001203 m / 0.183600 m/s | 0.000834 m / 0.045487 m/s |

The initial projection and the change-over-interval are separate vector
quantities; their norms do not add. The 0.15 s SoRoSim initial position gap
is larger than the 0.006075 m MuJoCo-only projection reconstruction gap, so
the cross-model initial difference includes kinematic model differences.
The nonzero incremental differences at 0.15 and 0.29 s support distinct
responses to the same physical tension after projection. The remaining
four-to-eight differences prevent a converged numerical bound on intrinsic
dynamics disagreement.

| Hypothesis | Current supporting observation | Distinguishing observation still needed | Current finding |
|---|---|---|---|
| H1: coarse SoRoSim integration causes easy braking | One-substep speed nearly vanishes at 0.30 s, while complete four/eight-substep integrations violate holding speed with the same commands | A later resolution would test numerical convergence of the refined models | Strong support for material discretization error; exact continuous-time contribution unresolved |
| H2: reduced-state projection contributes | MuJoCo-only reconstruction shifts the 0.15 s tip by 0.006075 m and 0.119152 m/s; projected SoRoSim starts 0.014843 m and 0.232082 m/s from the exact saved MuJoCo output | A higher-fidelity mapping or matched reduced-coordinate perturbation would isolate representational loss from cross-model kinematics | Supported contribution, not a unique quantitative share |
| H3: intrinsic dynamics disagree after alignment | Eight-substep same-command velocity increments differ by 0.244622 m/s at 0.15 s and 0.183600 m/s at 0.29 s | Converged mathematical integration and projection-sensitivity bounds would isolate dynamics | Supported response disagreement, with numerical/projection confounders |
| H4: historical gap accumulates over intervals | At 0.30 s the historical open-loop velocity gap is 0.872552 m/s, while the 0.29 s matched one-step gap is 0.066699 m/s | Further controlled state resets would measure history effects across intervals | Strong evidence of a history contribution, no unique additive share |

All four mechanisms can coexist. Their independent quantitative shares
remain unresolved because the reduced projection is not isometric and the
four/eight-substep SoRoSim outputs have not converged.

## P3 preparation: raw S4.5 SQP point and full warm start

The [saved-point audit](../../evidence/sorosim_s55/p3_p4_saved_audit.json)
extracts the raw optimizer checkpoint from the sealed S4.5 archive. The raw
SQP iterate has 1,006 variables, exit flag 0, 120 iterations, 501 function
evaluations, reported first-order optimality 0.025136655, reported constraint
violation 3.5438909e-5, step size 0.0282428 and line-search length 0.49.
Its scaled transcription violation was 3.5438909e-5. The output explicitly
stopped at the iteration limit. No iteration-by-iteration trace, search
direction, or full historical multipliers were saved. The reported
`bestfeasible` field points to the initial objective 0.000100000052 and
first-order value 1; it is not evidence of convergence of the final point.

Root recovery selected a **different** trajectory with objective
-0.9999675163278883 and scaled violation 6.4358241e-13. Its independent
post-hoc check satisfies all original sampled mathematical predicates. This
supports a mathematical feasible witness, not KKT stationarity, global
optimality, robust integration fidelity, or physical acceptance. The raw
iterate's nonzero optimality measure and constraint violation establish that
the historical solver did not verify a KKT point; the exact cause of the slow
SQP progress is unresolved. Near `rho = -1`, the task excess is nearly flat.
That is a plausible conditioning issue, not a demonstrated cause. The
terminal-position and final holding-position predicates are equal at the
same 0.35 s sample. New `task_capability` transcription keeps both in the
task report but uses one optimization inequality with an explicit mapping
back to both original IDs. This removes an exact duplicate row from the
active-set system without changing the frozen task.

The `saved_candidate_trajectory` solve route now checks exact model,
design, task, coordinate, tendon, substep, time-grid, initial-state and force
identities. It passes all 36 physical state nodes, 35 ordered tensions and
the signed source epigraph to `sr_codesign`. The MATLAB transcription checks
the complete initial-state/dynamics residual, physical bounds, epigraph
inequalities and original sampled task before using that point as the SQP
initial vector. A failure stops before optimization. It keeps the raw
optimizer checkpoint and computes KKT residuals on that point, before any
recovery. This path has passed Python boundary tests and MATLAB static code
checks. A [new check-only MATLAB preflight](../../evidence/sorosim_s55/p3_warm_derivative_preflight.json)
used the exact recovered witness as its full 1,006-variable initial vector.
Its scaled equality, inequality and bound violation was 6.436e-13. The
transcription retains all 13 original predicates for reporting, with 12
optimization inequalities after deduplicating the equal terminal/final
holding position row; there are 864 dynamics/initial-state equalities.
Directional objective and complete-constraint derivative relative errors
were 3.144e-10 and 1.127e-9. This check used 25.278 s and launched no
optimizer. A full P3 solve has not yet run. The previous S5-T derivative
preflight used 13 optimization inequalities and had relative errors
2.238e-8 and 1.727e-10. Neither check establishes Jacobian rank,
multiplier reliability, second-order sufficiency or local regularity.

## P4: conditional descent and unavailable certificate

For a fixed supported task and a differentiable **local** value branch
`W_tau`, let a design step `Delta d` stay in a declared region. Assume a
valid bound `||s_hat - grad W_tau(d)|| <= delta_s` and a regional gradient
Lipschitz bound `||grad W_tau(d1)-grad W_tau(d2)|| <= L||d1-d2||` for every
pair on the step segment. The fundamental theorem of calculus gives

`W_tau(d+Delta d)-W_tau(d) = integral_0^1 grad W_tau(d+t Delta d)^T Delta d dt`.

Add and subtract `grad W_tau(d)` inside the integral. Cauchy-Schwarz bounds
the gradient-estimate error by `delta_s ||Delta d||`; Lipschitz continuity
bounds the integrated variation by
`integral_0^1 Lt||Delta d||^2 dt = (L/2)||Delta d||^2`. Therefore

`W_tau(d+Delta d)-W_tau(d) <= s_hat^T Delta d + delta_s||Delta d|| + (L/2)||Delta d||^2`.

If this right-hand side is strictly negative, the stated local mathematical
branch strictly decreases. This theorem says nothing about the global
nonconvex optimum or MuJoCo performance. Here `s_hat` is unavailable:
there is no verified base KKT point, complete full-Lagrangian structural
derivative, or plus/minus reoptimization. Neither a justified `delta_s` nor
a regional `L` has been established, so the descent predicate is
**unavailable**. The earlier A/B common-tension secant is fixed-control
evidence only. Its B-minus-A terminal-error, holding-error and holding-speed
changes are +0.004849203 m, +0.004683372 m and +0.131846081 m/s over a
-0.005 m proximal-length change. It is not the reoptimized value derivative.
No P4 perturbation solve is admitted without validated base KKT conditions.

## Agent feedback and current decision

The research packet now exposes refinement completeness, resolution, task
metrics, root count, source/control hashes, and compact raw KKT residual
fields when present, alongside the P0 scientific equivalence preflight and
direct/residual PPO failure summaries. Unavailable numerical results remain
null; an Agent must not describe the archived repeated S5-Agent configuration
as a new physical candidate. The next mathematical action is a bounded
`task_capability` KKT attempt using the verified full-trajectory warm
start. More PPO training or a new full NMPC campaign is not supported by
these findings.

## Operations, costs and reproduction status

New scientific costs through the P3 preflight: three P1 SoRoSim fixed-sequence attempts,
two complete and one saved partial, totaling 119.706879 s charged worker
time; three P2 MuJoCo interval probes after a contained 540-step checkpoint
reconstruction; and six P2 SoRoSim one-interval integrations. P2 charged
20.696515 s and 600 total MuJoCo steps, of which 60 belong to measured
intervals. There have been zero full NLP optimizations, PPO actions and
provider requests. The P3 check-only derivative/feasibility evaluation
used another 25.278 s of MATLAB time without an NLP solve. The earlier
P2 preparation used three `mj_forward`
saved-state kinematic reconstructions; P0 read 260 prior PPO failure
captures and reconstructed their saved starts without stepping.
The P1 study spent three of four mathematical refinement slots and all six
public operations (three candidate materializations and three refinements).
The extra materializations bound the exact same Design B science to
committed numerical implementation versions; they did not launch physical
or mathematical repeats. The earlier sealed S4.5 and S5-T numerical costs
remain attributed to their original studies. The pinned upstream checkout
is verified at commit `24d573a3e864ffda87c42ee462a6ed620133cc7b`.
