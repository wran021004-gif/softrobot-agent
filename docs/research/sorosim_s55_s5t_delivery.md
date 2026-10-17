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

**Execution status:** no P1 mathematical integration has been launched. The
configured `SOROSIM_ROOT` environment variable is absent and the pinned
`GVSRobotics/SoRoSim@24d573a3e864ffda87c42ee462a6ed620133cc7b`
checkout has not been located. The MATLAB Engine Python source is present in
the installed R2024a tree and can be imported through its existing `build/lib`
path, but a standalone `matlab -batch` syntax check failed at startup with
`failed to load settings errors_warnings plugin`. This is an environment
obstruction, not a numerical result. The historical one-substep S4.5 discrete
feasible witness remains intact; integration robustness is unresolved.

| Same 35 commands and 36 original sample times | One substep | Two | Four | Eight | Optional 16 |
|---|---:|---:|---:|---:|---:|
| Root-complete integration | Historical yes | Unrun | Unrun | Unrun | Unrun |
| Original sampled mathematical task | Historical feasible witness | Unknown | Unknown | Unknown | Unknown |
| Maximum holding speed (m/s) | 0.000113989 | Unknown | Unknown | Unknown | Unknown |

There is no measured 0.25–0.29 s, 0.29–0.30 s, or 0.30–0.35 s convergence
trend. The historical one-substep braking prediction cannot currently be
classified as persistent, sensitive, or unstable under refinement.

## P2 preparation: archived-state projection only

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
or equality state. A contained replay is required to restore the exact
internal warmstart for dynamic checkpoints before a same-state one-step claim.
No P2 `mj_step` probe or SoRoSim one-step integration has run; `e_projection`,
`e_one_step`, and `e_increment` remain unavailable.

| Hypothesis | Current supporting observation | Distinguishing observation still needed | Current finding |
|---|---|---|---|
| H1: coarse SoRoSim integration causes easy braking | Historical one-substep speed falls from 1.842719 m/s at 0.29 s to 0.000114 m/s at 0.30 s while MuJoCo reaches 0.872629 m/s | Same fixed commands converge or fail to converge under 2/4/8 substeps; compare braking samples | Unresolved; no refined sample either supports or weakens H1 |
| H2: reduced-state projection contributes | Reconstructing the saved 0.15 s MuJoCo state from projected GVS coordinates shifts its kinematic tip position 0.006075 m and velocity 0.119152 m/s | Measure SoRoSim initial output at each projected checkpoint and compare to saved MuJoCo output | Projection loss is measurable inside MuJoCo; cross-model output effect unresolved |
| H3: intrinsic dynamics disagree after alignment | Historical trajectories disagree even though initial tip positions agree closely | Compare same-state, same-tension one-interval increments at stable refinement resolutions | Unresolved; no same-state dynamic probe |
| H4: historical gap accumulates over intervals | Open-loop position and velocity diverge from early intervals and differ strongly by braking | Compare one-step differences at 0, 0.15 and 0.29 s against the accumulated trajectory gap | Plausible, but the accumulated share is unmeasured |

All four mechanisms can coexist. The missing SoRoSim evaluation and the
unreconstructed MuJoCo warmstart prevent a causal decomposition now.

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
recovery. This path has passed Python boundary tests, but no new MATLAB
check-only call or full P3 solve has run because the pinned SoRoSim checkout
is unavailable. The S5-T derivative preflight from the previous study
covered 1,006 variables, 864 equalities and 13 original task inequalities;
its relative objective/constraint directional errors were 2.238e-8 and
1.727e-10. It does not establish Jacobian rank, multiplier reliability,
second-order sufficiency or regularity of the changed transcription.

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
as a new physical candidate. The next discriminating action is the already
prepared Design B fixed-sequence SoRoSim refinement at 2, 4 and 8 substeps,
followed by bounded matched-state one-interval probes if roots complete.
Only after numerical fidelity and the SoRoSim dependency are restored should
a base `task_capability` KKT attempt use the verified full-trajectory warm
start. More PPO training or a new full NMPC campaign is not supported by
these findings.

## Operations, costs and reproduction status

New scientific costs in this worktree: zero SoRoSim integrations, zero
MuJoCo `mj_step` probes, zero full NLP optimizations, zero PPO actions, zero
provider requests. The P2 audit used three `mj_forward` saved-state
kinematic reconstructions; P0 read 260 prior PPO failure captures and
reconstructed their saved starts without stepping. The prepared P1 study
`sorosim-s55-fixed-refinement-20261017` has one candidate materialization,
one imported verified trajectory, and no reserved mathematical worker.
The earlier sealed S4.5 and S5-T numerical costs remain attributed to their
original studies. The configured checkout path must first resolve to the
pinned `GVSRobotics/SoRoSim@24d573a3e864ffda87c42ee462a6ed620133cc7b`.
