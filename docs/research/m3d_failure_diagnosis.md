# M3-D1 failure diagnosis — 2026-10-16

C10 reached the sampled position region but did not settle: every inclusive holding sample failed speed. Its maximum was 0.1339154652 m/s (6.696 times the limit), with 0.1006187225 m/s remaining at termination. C9 entered position tolerance earlier, left it, and finished outside. The joint revision improved the outcome, but these two executions do not identify a unique physical or numerical cause.

## Scope and provenance

Read-only postmortem in `D:/softrobot-agent/.worktrees/m3d-agent-feedback`, branch `feat/m3d-agent-feedback`, repository `https://github.com/wran021004-gif/softrobot-agent.git`. Local and remote starting HEAD were both `9c2f2721e7bbc8441281154fdfd9ac8085a0b402`; initial worktree clean. Scientific binding remains `92064a72854d2ac21969846989ba6f93d0a482dc`. The delivery commit and verified remote SHA are reported in the handoff rather than embedded self-referentially here.

Authoritative frozen identities in [binding.json](../../evidence/m3d_agent_feedback/pilot/binding.json): configuration `6259446ce6dea8523f0f4762007ff9dde9249896192be171e40ad8f1413ad057`, evaluation profile `77cc3728cf6ba5510b66f6b7069a8cf9963ca51c8f62e6cfea96db0911d79c38`, final evaluation `defa9f6c914af60644a246516ecf5efba75218cfd1c46a6c9b0796afb72486a2`. Family identity is `120f23ddcf625a2fe4c0c0bfad3ad8d7a0fa25d42654e22261f2757ba539c987`.

Independently rehashed both archives and every member against their committed manifests, checking names and byte lengths: 343 Store members and 146 worker members. All 55 unique bound science/core file hashes match current source. Resolved configuration matches the prelaunch copy as decoded JSON (serialization differs). No archive was extracted onto the filesystem or rewritten.

| Archive / manifest in [pilot/](../../evidence/m3d_agent_feedback/pilot/) | Verified SHA256 |
|---|---|
| `immutable_artifacts.tar.gz` / `archive_manifest.json` | `98d79e5c8d9a8c4eb6790e652ca9af2621b7ffe1f74c697f80737d5924552036` |
| `original_worker_files.tar.gz` / `original_worker_manifest.json` | `13c3a1687f44ef35824dbe24fe73cf9135b4ebde32a54adbf4306e5377507e06` |

Source notation below: **S** = immutable archive member `artifacts/<full-ID>.json`; **W9/W10** = worker archive prefixes in the next table. JSON pointers and update IDs are zero-based. A time printed as 0.35 denotes the original stored `0.35000000000000003`, without resampling.

| Identity | C9 | C10 |
|---|---|---|
| Candidate S | `28e9fb3d03ac881485efe551bca01d23b1bcdc486a7361766e21d10c9ea93f8b` | `7fe8ed32039523cf9bda99e103c91bcc7bbdeed864b9aeb685b9775bc2ef5711` |
| Original full result S | `6323276c1fb77f42b1637ce88edd8ca9c873ab2d6123c0fbb25d111f6394c279` | `7579620e93ab25080d538042f3ad2f40dfd858532c176865b812fce4dc6361bf` |
| Motion S | `9422af882a29014c5ae998e8dc58db26b13c61c2cca6f3d419d82540815f2984` | `b7363ad04cf73602a7e7b7d7eac6141a6db0e09532ee90b6074aed79955e6edf` |
| Aligned predictions S | `92331bba9136334b2b071ce4d80ac2734fea492c0d19551c045d223eeb7d93f7` | `6eb5cd4e3476f03bf87620ce9edd26e23f91cc4e5592f14560cf17846a4adfea` |
| Physical design identity | `c6f5581f478bdb30b07044b505600975ffd2e9c38f644748007982b39d275a48` | `f1d4991d3d31b47688932da3854f79e6fd17cf2ce05e4f0bb850ef5ece9c494a` |
| Numerical model identity | `aca3656e2945a74b6b06a27adf04b14767aa731557d3769a1c06c0ac2d446ed6` | `b84a05725752e3f9c63fa4ceb353a50bb592bdd7f22eec949b9e3165e2f80a9b` |
| Worker backend prefix | `sessions/m3d-agent-feedback-pilot-exec-5968e7501462447a/executions/55c7135bea6a4f89ad01e21f419e52d1/backend/` | `sessions/m3d-agent-feedback-pilot-exec-4643dfee4ada4cba/executions/7791635f940a4d64afcd794cc03bb4df/backend/` |

Raw observations: W `trajectory.json.gz`, `actual_commands.json`, `controller_observations.json`, `nmpc_updates.json`, `control_snapshots.json`, `robot.xml`. Original reporting artifacts: S motion and aligned predictions, generated during the original execution; motion velocities were recorded from backend tip Jacobian times qvel, not finite differences. Original decisions/provider bytes are in S; all 21 timeline native inputs were checked against original `tool_use.input` bytes decoded as JSON. Existing [physical](../../evidence/m3d_agent_feedback/pilot/physical_evidence.json), [mathematical](../../evidence/m3d_agent_feedback/pilot/mathematical_evidence.json), [inventory](../../evidence/m3d_agent_feedback/pilot/candidate_inventory.json), [timeline](../../evidence/m3d_agent_feedback/pilot/decision_timeline.json), [cost](../../evidence/m3d_agent_feedback/pilot/cost_audit.json), [ledger](../../evidence/m3d_agent_feedback/pilot/ledger.json), [disposition](../../evidence/m3d_agent_feedback/pilot/disposition.json) and [delivery](../../evidence/m3d_agent_feedback/pilot/delivery_verification.json) files are derived original delivery views, not newly performed experiments.

New [derived_metrics.json](../../evidence/m3d_agent_feedback/offline_diagnosis/derived_metrics.json) contains deterministic arithmetic, exact member names/hashes and all 35 samples/updates/pairs per execution. Each update preserves command, previous input, solver counts/selection, recovery, warm initialization, prediction components and innovations. Assertions matched original execution/candidate ownership, sample positions, timestamps, actual commands and prediction input; independently recomputed norms match recorded values within 1e-12. Explanations below are explicitly separated from these calculations.

## Scientific configuration and outcomes

Frozen target `[0.29,0.035,0.19] m`, world frame; duration 0.35 s; 0.01 s control/sample grid; 0.0005 s physics step. Terminal and all six inclusive 0.30–0.35 s holding position errors must be ≤0.010 m; all six speeds ≤0.020 m/s. Coverage, force compliance, valid execution and solver policy also apply; no limit is reinterpreted.

Both candidates have two 0.20/0.11 m segments, circular radius 0.008 m, the same section station angles and four whole-chain tendons at radius 0.018 m, guide 0.5, anchor 1.0. Ordered channels are `[tendon_0,tendon_1,tendon_2,tendon_3]`, routing phases `[pi,3*pi/2,0,pi/2]`; each tension is unilateral, 0–8 N. Both use zero physical initialization, 12 cells/segment (48 physical DOFs), structural-linear GVS basis (12 curvature coordinates, 24 states), `controller.gvs_nmpc@11.0.0` and `backend.family_mujoco@1.1.0`.

| Configuration / outcome | C9 | C10 |
|---|---:|---:|
| Segment Young moduli, MPa | 7.2 / 5.4 | 5.0 / 3.8 |
| Holding / terminal tip-speed weights | 0.1 / 0.1 | 0.5 / 0.5 |
| Terminal error, m | 0.0159701054 fail | 0.0090662254 pass |
| Holding maximum error, m | 0.0159701054 fail | 0.0095616563 pass |
| Holding maximum speed, m/s | 0.2693533002 fail | 0.1339154652 fail |
| Terminal speed, m/s | 0.2693533002 | 0.1006187225 |
| Complete updates / physics steps | 35 / 700 | 35 / 700 |

Both use implicit Euler GVS prediction, one 0.01 s integration substep, nominal horizon 10, shortening to the task endpoint late in execution (6 intervals at t=0.29). IPOPT ceiling 120, tolerance/acceptable tolerance 1e-6, limited-memory Hessian, reverse constraint Jacobian. Warm states are regenerated; returned tensions can be reintegrated. Holding speed cost uses `time_integral_v1`, speed scale 0.02 m/s and zero brake lead; holding-node activation begins at 0.30 s. Terminal speed cost remains active and predictive control can act earlier: zero lead does not prove that no anticipatory braking occurred. MuJoCo uses `implicitfast`, 20 steps/interval, ideal direct tensions and gravity `[0,0,-9.81] m/s²`. Exact recipes remain in candidate S and the derived JSON.

## Actual sampled motion

Signed position error is actual minus target. Terminal positions: C9 `[0.275452131,0.038461641,0.195605426] m`, signed error `[-0.014547869,+0.003461641,+0.005605426] m`; C10 `[0.282598370,0.036821205,0.194908720] m`, signed error `[-0.007401630,+0.001821205,+0.004908720] m`. Both are short in x and high in z at termination; those offsets are not evidence of a steady equilibrium.

C9 first enters position tolerance at 0.09 s (minimum 0.005003254 m), remains inside at 0.10, and exits at 0.11; no later saved sample reenters. C10 first enters at 0.29 s and stays inside through termination. These are sampled entry times, not interpolated continuous crossing times. C9 is not simply a late first arrival. C10 arrives late with appreciable velocity, then reverses x direction before the first holding sample.

| Time, s | C9 speed, m/s | C10 speed, m/s | C10 vx, m/s |
|---|---:|---:|---:|
| 0.25 | 0.041585 | 0.057947 | +0.017277 |
| 0.26 | 0.051305 | 0.140543 | +0.117323 |
| 0.27 | 0.130753 | 0.234322 | +0.222386 |
| 0.28 | 0.214058 | 0.330719 | +0.318299 |
| 0.29 | 0.174955 | 0.322625 | +0.302177 |

Every holding sample follows; `P/F` means position passes, speed fails, not aggregate success. Velocity components are world-frame m/s. Source: motion S `/29`–`/34`; full signed errors for every sample are in the derived JSON.

| Candidate/time, s | Error, m | Velocity [vx,vy,vz], m/s | Speed, m/s | Position/speed |
|---|---:|---|---:|---|
| C9/0.30 | 0.012788507 | [-0.112673,-0.016749,+0.057766] | 0.127721099 | F/F |
| C9/0.31 | 0.013384719 | [-0.045030,-0.016779,+0.043913] | 0.065096267 | F/F |
| C9/0.32 | 0.013673570 | [-0.023928,-0.000557,+0.022251] | 0.032680004 | F/F |
| C9/0.33 | 0.013525030 | [+0.019352,+0.018229,-0.030362] | 0.040356372 | F/F |
| C9/0.34 | 0.014385812 | [-0.150653,-0.004515,+0.018817] | 0.151890837 | F/F |
| C9/0.35 | 0.015970105 | [-0.266402,-0.039458,-0.004899] | 0.269353300 | F/F |
| C10/0.30 | 0.007627811 | [-0.131769,-0.020846,+0.011647] | 0.133915465 | P/F |
| C10/0.31 | 0.008638060 | [-0.126513,+0.006757,+0.018460] | 0.128031189 | P/F |
| C10/0.32 | 0.009410622 | [-0.047039,-0.001168,+0.008335] | 0.047786253 | P/F |
| C10/0.33 | 0.009561656 | [-0.020345,-0.010568,-0.004954] | 0.023455105 | P/F |
| C10/0.34 | 0.009171782 | [+0.082917,-0.067763,-0.015669] | 0.108224634 | P/F |
| C10/0.35 | 0.009066225 | [-0.097285,-0.024918,+0.006236] | 0.100618723 | P/F |

C9 slows until 0.32, briefly reverses x at 0.33, then accelerates away; its speed maximum is the terminal sample. C10 slows to 0.023455 m/s at 0.33 (still above limit), then rises to 0.108225 at 0.34 and finishes at 0.100619; its holding maximum is already at 0.30. Its position error worsens through 0.33, improves thereafter, while x velocity changes negative → positive → negative across 0.33–0.35. Both show reversals/rebound and residual transient motion. Six samples do not establish a sustained periodic oscillation or a damping ratio. Neither shows monotonic approach to rest over the full holding interval. Braking begun at 0.30 cannot repair that already failed sample; a future holding analysis should start at a saved 0.20–0.25 state.

## Applied effort, bounds and numerical quality

All 70 actual command vectors were matched to W commands, observations and post-step trajectory tension records in channel order. Original force-bound violation is zero. For comparability use the original reporting definitions: near upper ≥7.92 N (99% of 8), near zero ≤1e-6 N. Counts below are out of 35 per channel; exact times are retained in JSON. These proximity counts differ from `force_limit_saturated`, which records actual clipping: C9 clips at 0.02 (channels 2/3), 0.03 (0/1/3), 0.33 (3), 0.34 (2); C10 clips channel 1 at 0.31. Its additional near-zero command at 0.34 reaches zero without a clipping flag.

| Candidate/channel | Actual min–max, N | Near upper | Near zero | Minimum upper headroom, N |
|---|---|---:|---:|---:|
| C9/0 | 0.00000075–8.000000 | 1 | 1 | 0 |
| C9/1 | 0–7.940758 | 1 | 2 | 0.059242 |
| C9/2 | 5.108775–8.000000 | 6 | 0 | 0 |
| C9/3 | 0.00000137–8.000000 | 7 | 0 | 0 |
| C10/0 | 0.368294–6.652924 | 0 | 0 | 1.347076 |
| C10/1 | 0–3.612472 | 0 | 2 | 4.387528 |
| C10/2 | 1.184551–7.919449 | 0 | 0 | 0.080551 |
| C10/3 | 4.025186–7.856912 | 0 | 0 | 0.143088 |

C9 has 15/140 channel commands near upper, spanning 10/35 updates at t=0–0.06, 0.31, 0.33, 0.34. Late upper proximity is channel 3 at 0.31/0.33 and channel 2 at 0.34; no upper proximity occurs at 0.20–0.30. C10 has 0/140 near-upper commands, narrowly including its early maximum 7.919449 N; the threshold is descriptive, not a discontinuity in authority. From command times 0.20–0.34 its channel maxima are `[6.652924,2.467618,7.158345,7.407001] N`, leaving at least `[1.347076,5.532382,0.841655,0.592999] N` upper headroom. Channel 1 reaches its lower bound at 0.31/0.34. Available upward force does not guarantee the required world-direction braking authority under unilateral bounds.

Late applied controls below act over `[t,t+0.01]`; the sample at 0.30 is caused by the command at 0.29. Full 35-vector histories are in JSON `/executions/C9/updates` and `/executions/C10/updates`.

| Command t, s | C9 [0,1,2,3], N | C10 [0,1,2,3], N |
|---|---|---|
| 0.25 | [5.6186,1.6639,6.1974,6.4637] | [2.3395,0.7868,2.9849,4.9568] |
| 0.26 | [4.8846,0.8540,5.5150,5.8718] | [2.1386,0.0024,2.5529,4.4671] |
| 0.27 | [5.6557,2.1865,6.2351,6.2628] | [2.0949,0.2145,2.3988,4.5256] |
| 0.28 | [5.8960,2.7449,6.7189,6.6580] | [3.1687,1.6917,3.4346,5.1837] |
| 0.29 | [6.0778,0.4287,6.3321,6.7378] | [3.9982,2.4676,4.5270,7.4070] |
| 0.30 | [5.9178,1.8289,6.2182,6.6465] | [2.7617,0.9585,3.3894,5.4682] |
| 0.31 | [4.6927,3.8614,5.1088,7.9993] | [2.1594,-0.0000,2.5740,4.8672] |
| 0.32 | [6.0185,3.4856,6.4442,6.7283] | [3.0160,1.1867,3.3176,5.4460] |
| 0.33 | [5.2204,3.3196,5.6784,8.0000] | [1.3374,0.6132,1.1846,5.4606] |
| 0.34 | [7.8051,4.1632,8.0000,7.5592] | [6.6529,0.0000,7.1583,4.0252] |

Largest consecutive command changes by channel: C9 `[6.823892,7.940733,2.321586,5.750391] N`; C10 `[5.315514,1.509069,5.973794,2.223310] N`. The C10 final transition 0.33→0.34 changes channels 0/2 by +5.315514/+5.973794 N and accompanies a velocity reversal. Tension-increment sign reversals across all 34 transitions, excluding ≤1e-6 N increments, are C9 `[16,17,17,19]`, C10 `[14,14,12,13]`. These establish variable input, not periodic physical oscillation or causation by any single jump.

| Numerical observation (all updates) | C9 | C10 |
|---|---:|---:|
| Accepted plans / unusable / solver errors | 35 / 0 / 0 | 35 / 0 / 0 |
| Raw maximum-iteration / successful exits | 33 / 2 | 34 / 1 |
| Recorded IPOPT iteration sum | 4013 | 4102 |
| Delivered selected-iteration sum / missing | 2900 / 7 | 2036 / 6 |
| Maximum accepted scaled constraint violation | 8.946196e-6 | 8.300594e-6 |
| IPOPT-selected / reintegrated delivered plans | 28 / 7 | 29 / 6 |
| Recovery attempts / selected / root solves | 7 / 7 / 69 | 6 / 6 / 48 |
| Update wall min / mean / max, s | 2.261 / 80.572 / 105.463 | 2.637 / 87.941 / 111.929 |

Evidence: W `controller_observations.json` `/0`–`/34`, nested `complete_update_record/diagnostics`, `/selection`, `/warm`, `/initialization`, `/recovery`. Complete embedded update records exist for all 35 updates in each execution. Separate decoded snapshots/iteration traces cover only IDs 0,29,30; do not infer full iteration trajectories elsewhere. Iteration sums use recorded `diagnostics.iterations`, not the ceiling times 35. Missing delivered selected iterations belong to reintegrated returns and remain null; original IPOPT-selected iterations are separately retained. Root totals above concern returned-plan recovery, not every warm-preparation or internal root evaluation.

Both runs record 10 `explicit` warm sources and 25 `previous_selected`, zero dual initialization and zero initialization-only selected plans. The 10 explicit sources reflect execution-local preparation/horizon work; they do not establish ten independent cold science attempts. Embedded nominal workspace remains the preparation point, while the NLP receives the actual projected measured state at every update. Wall overruns occur at all 70 updates, but the synchronous backend still performs every simulated interval; this is not evidence of injected actuator delay or skipped controls.

**Three different statements:** (A) every delivered plan passes the existing scaled-defect acceptance policy (`TrajectoryWorkspace.solve`, [gvs_trajectory.py](../../extensions/tendon_family/gvs_trajectory.py), allowed usable status and violation ≤1e-5); (B) only 2/1 raw IPOPT solves meet successful termination; (C) neither physical task passes. An accepted iteration-limited return is feasible under policy, not fully optimized and not a reported solver error.

C9's two successful solves are updates 33/34 (35/18 iterations); C10's sole success is update 34 (22 iterations). Nevertheless C9's last velocity innovation is 0.263458 m/s, and C10's last forecast speed is 0.000927 versus actual 0.100619 m/s. Thus better termination is not sufficient to guarantee one-step physical agreement. The historical record cannot show whether converging the other updates would have altered the state reached at holding. Iteration limits are a substantial numerical-quality limitation, with unproven material contribution to this failure.

## GVS prediction versus MuJoCo execution

Used the **original 35 aligned records per execution**, without changing alignment. Each start timestamp matches observation/update index; forecast end matches the next recorded motion time; applied inputs match exactly (recorded applied-input difference 0 N). Predictions are accepted-plan first steps in projected 24-state GVS dynamics. Measurements are 48-DOF backend execution, and reported tip positions/velocities are world frame. Position innovation is measured minus predicted in m; velocity innovation is measured minus predicted in m/s. Speed-magnitude difference is not the velocity-vector norm difference.

| One-step metric | C9 | C10 |
|---|---:|---:|
| Maximum position discrepancy, m | 0.0121043422 | 0.0093696819 |
| Mean position discrepancy, m | 0.0095051520 | 0.0077233727 |
| Maximum velocity-vector discrepancy, m/s | 0.2634583307 | 0.1750482938 |
| Mean position discrepancy, end ≤0.25 / holding, m | 0.008802 / 0.011329 | 0.007379 / 0.008444 |
| Mean velocity discrepancy, end ≤0.25 / holding, m/s | 0.174272 / 0.198276 | 0.097621 / 0.087952 |

Position discrepancy is persistently large late, rather than growing monotonically at holding. C10 velocity discrepancy is smaller at preholding ends 0.26–0.29 (mean 0.034039 m/s), then rises to holding mean 0.087952. Its global velocity maximum occurs early at update 1, not at holding. Full component vectors and innovations for all pairs are in JSON `updates[i].one_step`, directly linked to prediction S `/i`.

Ranked informative records (position maxima first within each purpose; `I` iteration limit, `S` success):

| Rank/purpose | Candidate/update | Interval, s | Position innovation norm, m | Velocity innovation norm, m/s | Forecast/actual speed, m/s | Max tension, N / stop |
|---|---|---|---:|---:|---|---|
| 1: holding onset | C10/29 | 0.29-0.30 | 0.007323492 | 0.141660705 | 0.008234/0.133915 | 7.407001 / I |
| 2: largest C10 position | C10/25 | 0.25-0.26 | 0.009369682 | 0.051283943 | 0.185597/0.140543 | 4.956839 / I |
| 3: largest C10 velocity | C10/1 | 0.01-0.02 | 0.000321372 | 0.175048294 | 1.438794/1.608618 | 7.919449 / I |
| 4: converged terminal | C10/34 | 0.34-0.35 | 0.007814521 | 0.101172966 | 0.000927/0.100619 | 7.158345 / S |
| 5: largest C9 position | C9/16 | 0.16-0.17 | 0.012104342 | 0.219848358 | 0.152387/0.077952 | 6.504865 / I |
| 6: largest C9 velocity | C9/34 | 0.34-0.35 | 0.011938370 | 0.263458331 | 0.031729/0.269353 | 8.000000 / S |

At C10 update 29 the forecast gives velocity `[+0.007115,+0.002988,-0.002872]`, while measurement is `[-0.131769,-0.020846,+0.011647] m/s`: innovation `[-0.138884,-0.023835,+0.014518]`. Forecast position `[0.289249055,0.034788242,0.189835631]` versus measured `[0.284723301,0.037774394,0.194758433] m` gives innovation `[-0.004525755,+0.002986152,+0.004922802] m`. The model predicts a passing first holding speed (0.008234), whereas execution fails (0.133915). This recovered plan's scaled defect is near machine precision; that verifies its internal dynamics, not the backend model.

Projection is `backend_discrete_to_gvs_integrated_v2`: least squares fits principal joint angle/cell length and rate to the integrated structural basis. Maximum recorded curvature residual is 7.450387/4.790975 rad/m for C9/C10; original maximum rate residual is 94.635975/82.865009 rad/(m·s). At C10 update 29, curvature/rate reconstruction residuals are 4.239409 rad/m and 16.378792 rad/(m·s). These are representation residuals, not tip errors. Initial curvature projection residual is zero in both runs, yet first-interval velocity innovations are nonzero, weakening a projection-only explanation. No per-update initial GVS world-tip reconstruction is explicitly reported to cleanly subtract initial output bias from propagated discrepancy.

Actual direct-tension semantics are visible in W `robot.xml`: gain −1, ctrl 0–8, actuator force −8–0; backend reports tension as negative actuator force. Recorded tracking errors are zero; gross command/order or actuator-lag explanations lack support in these ideal-tension runs. This does not independently validate the generalized force map or virtual-work routing agreement between models.

Descriptive Pearson correlations across 35 pairs: position discrepancy versus measured speed C9 −0.959/C10 −0.878, versus maximum tension −0.731/−0.813; velocity discrepancy versus speed −0.282/+0.604, versus maximum tension +0.132/+0.830. C10 has no near-upper commands, and C9's position maximum occurs without upper proximity. Successful late solves still have large innovations. These time-confounded correlations do not isolate saturation, convergence, projection, continuous dynamics or integration as the cause.

## Actual Agent feedback and causal limits

Original decisions, with times Asia/Shanghai UTC+08, are [timeline](../../evidence/m3d_agent_feedback/pilot/decision_timeline.json) indices below; original tool inputs were independently matched to S references.

| Timeline index / time | Observed decision or read |
|---|---|
| 0–1 / 12:54:27–34 | Agent chooses mathematical search; first request including `control` is rejected, corrected request succeeds. Eight coordinate proposals are optimizer-internal, not eight Agent proposals. |
| 2–3 / 12:56:11–25 | Agent materializes C9 at final fidelity and requests its first fresh execution. |
| 4–12 / 13:44:32–38 | Explicitly reads C9 result `/acceptance/components` and motion `/34,/0,/5,/10,/15,/20,/25,/30`. |
| 13 / 13:46:07 | Reads screening analysis `03dcfa8a167e93fa1626159996bcf6e830ff1b26c93954083ac30a8edad2d718` `/raw`. |
| 14 / 13:47:18 | Revision plan S `689730e5884f961d79353298d48f75f6ea14813c97d59fcf954a589835bf65c1` cites all three already-read artifacts; changes Young moduli and both speed weights together. |
| 15–16 / 13:47:26–13:48:22 | Selects new C10-bound target-equilibrium analysis, then requests its new full execution. |
| 17–18 / 14:40:06–07 | Reads C10 acceptance components and terminal motion `/34`. |
| 19–20 / 14:40:22–44 | First STOP rejected for omitted mathematical references; corrected STOP includes all nine analyses and both executions; seals with no selection. |

The cited screening static solution really has channel 2 at 7.999999994 N, tensions `[7.806909,3.346686,8.000000,7.626135] N`. It belongs to coarse candidate `a967296529c8bc526726fafb477f4c7583d00f4530623997c9989ca503601c68`, not C9's final numerical identity. Physical structure is shared, but no independent C9 candidate-bound static solve was performed. C10 analysis S `5c2ed63cd28cb9d2c0a108b11de6573294aec5bbfffedf35b549dca49faffbdb` finds residual 5.872029386e-9 m, 13 SLSQP iterations, tensions `[2.215264,2.875877,2.520612,7.235172] N`, minimum upper margin 0.764828 N. Static constructions do not score speed weights or prove dynamic settling.

The Agent's observed x/z offset, terminal speed spike and 33 iteration-limited solves were facts. Calling the offset “steady” was unverified. Claiming ~30% lower required tensions was a hypothesis: the independently optimized tension vectors change by different fractions and use different local equilibria, not a stiffness-only proportional law. Actual C10 upper-bound margin and better positions/speed support the direction of the revision, but its claim that 8 N prevented settling is not established. Increased weights did not achieve their intended holding-speed outcome. The phrase “reproducible design path” in the preserved STOP is a workflow description at most; there were no repeated executions establishing repeatability.

## Confirmed observations

- Both exact fresh full executions are valid failures: C9 fails terminal/holding position and speed; C10 fails only holding speed. Complete coverage and force/solver-policy components pass. No result is selected and no first-success gate is set (result S `/acceptance`, [disposition](../../evidence/m3d_agent_feedback/pilot/disposition.json)).
- Every holding speed fails, including C10 t=0.30; late direction reversals and large aligned innovations are measured. A scalar position pass does not establish rest (motion/prediction S above).
- All 70 plans are numerically usable; 67 raw solves terminate at the iteration ceiling. C10 has upper headroom and persistent failure; successful final solves retain prediction error (W records above).
- Joint material/control revision and actual prior evidence reads are established; unique parameter attribution is not. Search had eight internal evaluations plus one later direct analysis, 9/10 total. Physical launches are exhausted 2/2, not every budget: provider 13/16, public operations 27/64, native probes 2/2 ([cost](../../evidence/m3d_agent_feedback/pilot/cost_audit.json), [delivery](../../evidence/m3d_agent_feedback/pilot/delivery_verification.json)).
- Both tool-interface rejections happen before new science; the guards function correctly. Closure retains no pending execution, reservation or occupied resource.

## Supported but unproven hypotheses

| Hypothesis / confidence | Supporting evidence | Counterevidence / missing proof | Discriminating calculation needed |
|---|---|---|---|
| Late braking contributes — moderate | C10 first entry 0.29 with 0.322625 m/s; 0.30 already fails; speed cost has zero lead | Predictive/terminal costs already allow earlier braking; no optimal constrained authority result | Existing sampled-trajectory extension from exact 0.20–0.25 state, every holding sample, fixed physical bounds |
| Weak damping or persistent transient — moderate for transient, limited for damping cause | Speed falls then rises; x reversals in holding | Changing controls can drive reversals; no free-response or validated local pole evidence for these states | Candidate-bound transient drift/poles and bounded velocity response; cannot infer damping from six samples |
| Composite prediction/execution mismatch contributes — strong for discrepancy, moderate for contribution | 35 matched pairs each; update 29 falsely forecasts passing speed; successful final solve still disagrees | Initial projection output bias and integration/model effects not isolated; errors do not alone prove controller counterfactual | The single no-NMPC interval comparison specified below |
| Iteration-limited optimization contributes — limited | 33/34 ceiling exits; feasible earlier iterates/recovery selected | All plans usable; sole C10 successful final step also fails physical speed | Fixed-state/action comparison first separates forecast effects; optimizer benefit ultimately needs a separately authorized fixed-state convergence comparison |
| Saturation/directional authority contributes — limited | C9 early/late upper proximity, C10 lower-active channel 1 | C10 no ≥7.92 N commands; C9 preholding often unsaturated; no bounded directional feasibility certificate | Physical-box local velocity response and shared-sequence holding margin, not a Gramian alone |
| Structure/control interaction caused improvement — moderate for joint effect, limited for individual mechanism | Same geometry/routing, lower stiffness plus larger speed weights, improved original metrics | Both changed together; different state histories; no repeats | Matched single-factor comparison would be required for attribution; not performed or the primary next recommendation |

## Unresolved questions

The evidence cannot determine whether the authorized family contains an accepted design; which revision parameter caused improvement; which of projection, generalized force mapping, continuous dynamics or integration dominates discrepancy; whether improved IPOPT convergence would fix holding speed; whether another backend would improve actual acceptance; whether the Agent is more efficient than a traditional optimizer; or whether any result repeats. No local or global infeasibility, optimality, stable equilibrium or closed-loop stability certificate exists for these two trajectories. Failure to isolate a cause is the scientific conclusion.

## ONE next discriminating calculation — proposed only

Recommend one **fixed-state, fixed-action, 0.29→0.30 s C10 open-loop comparison**, without NMPC, optimization or parameter search. Update 29 has the most informative late velocity discrepancy and both decoded snapshot and complete records: forecast passes speed, measurement fails, action matches, recovery internally reintegrated the plan.

Inputs: C10 exact candidate/XML/model identities above; W10 `trajectory.json.gz` `/28/qpos_rad` and `/28/qvel_rad_s` (state at 0.29), controller observations `/29/measured_initial_state` (24 projected components), `/29/complete_update_record`, snapshot ID `65f3ddae85584eddb303e52b1703b21f2e9caeb4e82f078273f58279972610f5`; previous command `[3.168703947,1.691714352,3.434623103,5.183691846] N`, current `[3.998169955,2.467618453,4.526973495,7.407001452] N`. Use full saved precision and original channel/coordinate order, not these rounded display vectors.

At interval start, record both model tip outputs and velocity, physical state/projected state, projection residual, command sign/order, tensions and generalized tendon forces. Hold current action through exactly 0.01 s: one GVS implicit-Euler step with original 1e-10 root tolerance versus 20 MuJoCo `implicitfast` steps of 0.0005 s. Record end states, world positions/velocities, innovations, original S prediction `/29` differences and physical endpoint replay error. Compare incremental motion separately from the initial output offset. This removes optimization/action choice from the interval, exposes initial projection/kinematics bias, and checks force semantics before interpreting remaining composite dynamics/integration error. One pair cannot separate continuous-model error from discretization error without further work.

**Saved-state limitation:** qpos/qvel, projected state, XML, time and actions exist, but a complete serialized MuJoCo integration state including `qacc_warmstart` is not retained. Exact bitwise historical replay cannot be promised. The nearest viable single calculation is the same pair with a declared deterministic backend restart (reset auxiliary state, restore recorded qpos/qvel/time, apply known direct tension). Report its deviation from the original endpoint explicitly; do not silently label it an exact hidden-state restoration. Direct actuators are stateless in the saved XML, but this does not supply missing solver warm state. If a separately retained exact integration-state snapshot is discovered, bind and use it instead.

Authorization/budget needed: **new scientific authorization**, one comparison artifact, one GVS root integration and one 20-step MuJoCo interval, zero Agent/provider/NMPC calls, zero search/equilibrium/linearization solves, no full-task evaluation and no access that resumes the sealed study. Record actual timing and root iterations; historical per-update wall times are not a reliable cost estimate for this one interval. It is more discriminating than another 35-update rollout because it holds state/action fixed instead of changing 35 optimizations and their subsequent states. **Not executed here.**

## Incremental mathematical capabilities, ranked

Existing ownership was inspected: [tendon-family math](../../extensions/tendon_family/math_analysis.py) already constructs world position/velocity outputs including dJ/dq·qdot and A/B/drift; [GVS CasADi](../../extensions/tendon_family/gvs_casadi.py) supplies dynamics/AD; [kernels](../../extensions/math_analysis/kernels.py) already report poles, damping ratios, normalized drift/equilibrium qualification, headroom, ZOH held-control maps, endpoint and terminal braking. [trajectory](../../extensions/math_analysis/trajectory.py) already enforces a shared input sequence across sampled position/speed constraints, physical boxes, previous-input feedthrough, absolute-grid coverage, independent witness replay and checked necessary-constraint exclusions. [tools](../../extensions/math_analysis/tools.py), [analysis](../../tools/research/analysis.py), [contracts](../../tools/research/contracts.py) and [task applicability](../../tools/research/task_constraints.py) already bind scope and scientific status. No replacement equilibrium, linearization, controllability, endpoint, braking or trajectory tool is needed.

### 1. Extend sampled trajectory feasibility with a holding-speed margin

Input: existing candidate-bound saved-state request, preferably C10 update 20 or 25 (t=0.20/0.25), previous applied operating tension, exact projected state/model/protocol identities and frozen grid. Remaining horizon 0.15/0.10 s, respectively 15/10 intervals, four inputs each. Preserve all six holding position constraints and terminal position constraint; use `delta_u` bounds `-u0 ≤ delta_u ≤ 8-u0`.

Increment: epigraph `rho_hold ≥ 0`, minimize rho with `||v_tip,k|| ≤ rho_hold*0.020` at every holding sample, while enforcing `||p_tip,k-target|| ≤ 0.010`. Reuse affine drift/ZOH maps and independent replay; fixed-model constraints are convex. Existing feasibility minimizes tension energy subject to the original limits; it does not optimize this speed margin. Do not leave the original fixed speed bound active when measuring a ratio above one. Any declared local-validity/trust bound must be explicit; absence of a validated nonlinear validity radius must remain a limitation.

Output: exact start/time/operating tensions/horizon/grid, solver status and cost, replay-verified sequence, speed ratio upper bound, certified lower bound if available, optimality gap if certified, all position margins, physical headroom and covered sample indices. A solver result alone does not prove the minimum or infeasibility. If position feasibility fails without a checked certificate, return inconclusive; existing per-constraint separation is sufficient only when it actually verifies exclusion. `rho≤1` with verified margins is a local sampled witness, not nonlinear MuJoCo acceptance or robustness. Past sampled constraints stay unchecked; a preholding start does not certify earlier task history.

Ownership/size: `trajectory.trajectory_feasibility`, `verify_witness`, `tools/research/analysis.py:calculate`, and analysis protocol schema only if a new optional objective is required; roughly 80–140 implementation LOC. One existing graph/linearization plus a 41-variable problem from 0.25 (61 from 0.20), bounded iteration count and one recurrence replay; actual cost unmeasured. Future focused validation: analytically soluble drift example with exact rho, a violated 0.30 sample despite a passing endpoint, active unilateral bounds, and failed-solver/no-certificate classification. Explicitly version additive objective semantics without changing historical requests.

### 2. Add a bounded tip-velocity authority view to existing braking/linearization

Input: same exact candidate/model/saved-state identity and previous operating input, selected existing horizons and world velocity output. Reuse A/B/drift, poles/damping, input headroom and endpoint velocity maps. Increment only the **box-constrained directional velocity support/margins** and a concise linked view of these existing outputs: free drift plus min/max attainable change along specified world directions under the same physical tension box. Include active bounds and whether the point is an equilibrium or transient. This adds the missing velocity-directed bounded interpretation; it does not rename existing Gramian metrics or compute poles again.

Output: direction/unit/frame, finite held horizon, baseline velocity/drift, directional extrema and physical actions witnessing them, headroom/active bounds, links to existing pole/validity records. Directional projections do not establish simultaneous vector or multi-sample feasibility; use priority 1 for that. Frozen-Jacobian poles at a transient are not measured damping or a closed-loop stability result. Not applicable without compatible output, valid physical box, known remaining time and model scope. Cost: arithmetic on existing maps; no extra dynamics construction if reused, otherwise one existing linearization. Ownership: `kernels._output_endpoint`/`bounded_endpoint` and `analysis.calculate`; about 30–60 LOC. Validate against an exact two-input asymmetric box including a lower-active tendon and nonzero drift.

### 3. Qualify nonzero-tension equilibrium and expose complete static IFT sensitivities

Reference inspected read-only through Git objects: independent SoRoSim V2 commit `e1ae76331d37ca1258803def6f07219f00aa5352`, numerical source `930be983153f1170f52e57dd0ea14357e29dc660`, `validation/sorosim/README.md` V2 and `evidence/run_v2_20261016_02/{summary,delivery_manifest}.json` (SHA256 references in derived JSON). These are distinct one/two-segment static cases, not C9/C10 validation. V2 finds a locally regular two-segment/u2 saddle with two negative reduced-potential Hessian eigenvalues; regularity is not stability. Its endpoint-chord reference does not validate every guided route used here.

Input: existing candidate-bound converged equilibrium, exact fixed tension/design/coordinate order, model and residual convention; optional existing physical design coordinates. Reuse native residual and AD tangent, including tendon geometric stiffness. In V2 sign convention `R=elastic-gravity-B(q)u`: `Rq=A_passive-sum(u_i*dB_i/dq)`, `dq/du=-Rq^-1 Ru`, `dp/du=J*dq/du`; design sensitivity `dp/dd=partial_p/partial_d-J*Rq^-1*Rd`. Existing GVS residual has the opposite sign: convert residual and all derivatives consistently. Geometry partials must rebuild physical dependencies, including basis/length effects.

Output: residual convergence separately from conditioning/IFT regularity; full tangent symmetry check and conservative reduced-potential Hessian inertia where applicable; input/design derivatives with units, branch/locality scope and finite-difference validation. Do not classify a force Jacobian's sign as potential stability without the sign conversion. Singular/ill-conditioned tangents give unavailable sensitivities; nonconservative/contact/nonsmooth active-set cases give unsupported potential classification. A saddle is not an automatic design rejection: active feedback stabilization remains separate. Static Hessian positivity does not prove dynamic or closed-loop stability.

Ownership: `tendon_family/math_analysis.py:_candidate_points` and existing `gvs_casadi.py` static expressions, not a new MATLAB runtime/tool family; approximately 70–120 LOC plus focused tests. Cost: one existing equilibrium, full AD tangent and small dense solves; each design partial may require explicit graph rebuilds/extra residual calls, all counted. V2 static timings are context, not forecasts for this 12-coordinate guided model. Validate nonzero-tension total tangent against residual differences, deliberate omitted-tendon-term corruption, units/sign conversion, ill-conditioned refusal and a regular saddle. No new tools implemented in this milestone.

## Minimal Agent interface proposals — future only

| Issue / exact future owner | Small change and size | One focused test / compatibility |
|---|---|---|
| A: `tools/research/agent.py:decision_packet` | About 12–20 LOC: under existing `study.family_search`, add objective-specific `allowed_variable_groups` intersected with frozen grant and `unsupported_variable_groups: {control: static/Gramian proxies do not score weights}` for the two existing objectives. Point to generation plus actual control-dependent evaluation for speed weights; introduce no objective/evaluator. | Packet fixture checks both objectives exclude control and generation still accepts allowed speed weights; unchanged `FamilyMixedSearch.selected_coordinates` remains the authoritative rejecting validator. Additive presentation only; no scientific identity change. |
| B: `tools/research/feedback.py:facts` (consumed by `core.packet` and native error feedback) | About 8–15 LOC: concise `required_stop_experiment_refs` view of the same four source lists used by `core.dispatch`: results, mechanics_results, rl_evaluations, analysis_results. Exact references already exist in packet result/analysis lists: improve presentation, do not persist redundant acknowledgement state. If showing “unacknowledged,” distinguish already-read from still-required STOP citations; prior reads never waive citations. | Fixture includes a search's eight analyses and one direct analysis plus two physical results; view equals unchanged STOP rule's set, missing one citation still rejects and complete set succeeds. No auto-citations, invented refs, extra model query or weaker rule. |
| Optional C: `tools/research/agent.py:build_harness`, nested `handler/run` exception presentation | About 15–25 LOC if adopted: for a known `search.version`, show concise `ValidationError.errors()` paths/messages for that union branch, retain exact underlying validation/error record and fallback for unknown versions. Initial error feedback is 5,416 characters including facts and irrelevant legacy-union errors. | One invalid mixed-search fixture retains the control exclusion/error code and never dispatches science; unknown version retains full diagnostic. Keep native `Search`/`FamilyMixedSearch` union contract unchanged; no repair/retry mechanism. |

`STOP_MUST_CITE_ALL_NEW_EXPERIMENT_RESULTS` and both search validators remain authoritative. Existing packet already exposes mathematical references through `analysis_results`; merely displaying a clearly labeled STOP list avoids adding state. Any future native feedback truncation must preserve the original diagnostic in Store and keep exact error semantics. All LOC are estimates, excluding focused tests; no interface patch was applied here.

## Work performed and validation

Only new diagnostic Markdown and derived JSON were written. One-off Python used only standard-library JSON/tar/gzip/hash/math/statistics operations and read-only Git-object access; no permanent extraction script or production module was added. Archive/member/source integrity, all 70 motion and prediction norm checks, time/input/ownership consistency, original decision inputs, basic JSON/Markdown links/table structure and `git diff --check` were checked. Final tracked-change review permits only these two new artifacts; historical files, archives, sources, configurations and sealed Store remain untouched.

New provider requests **0**, Agent invocations **0**, research scientific actions **0**, GVS solves/linearizations **0**, IPOPT/MATLAB optimizations **0**, NMPC updates **0**, MuJoCo launches/steps **0**, candidates **0**, studies/resets/replays **0**, task evaluations **0**. No full test suite or scientific dispatch, including `diagnostic.diagnose`, was run. The proposed computation and implementation estimates are recommendations requiring later authorization, not completed science.
