# S3.5 — SoRoSim NMPC cost and prediction-gap diagnosis

2026-10-16, Windows 11; branch `feat/sorosim-matlab-nmpc`.
Starting local and verified remote SHA: `cdb2f8d196af7f7d04c14efda3b960b88c20a782`.
That is the S0–S3 completion commit; no later branch work was reset.

The full evidence is in [evidence/sorosim_s35](../../evidence/sorosim_s35).
[diagnosis.json](../../evidence/sorosim_s35/attempt02/diagnosis.json) separates
`raw_facts`, existing `ScopedMathematicalClaim` diagnostic conclusions, and
`research_interpretations`. This report supplements the unchanged S0–S3 delivery.

## A. Computational cost: observed facts

Historical, immutable short-loop measurements:

| Start s | Iterations | Function evaluations | Warm regeneration s | SQP s | Validation s | Complete update s | SQP s / function evaluation |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.00 | 69 | 227 | 6.278574 | 37.604870 | 0.973620 | 45.163 | 0.165660 |
| 0.01 | 105 | 356 | 2.542796 | 62.379426 | 0.840067 | 66.052 | 0.175223 |
| 0.02 | 120 | 404 | 2.269395 | 70.547625 | 0.922179 | 74.028 | 0.174623 |

The last column is an optimizer-count timing proxy, **not** time per distinct
trajectory evaluation. Function evaluations per iteration are 3.29, 3.39, 3.37.
The increasing number of iterations/evaluations explains most of the time growth;
these data do not support progressive MATLAB slowdown or progressively costly
warm regeneration. Changed states and shifted warm controls are associated with
different optimizer difficulty; their separate causal contributions are unresolved.
Historical initial objectives are 874.658039, 13.168621, 4.807577, and delivered
objectives are 2.696708, 1.834637, 1.181983. Lower initial cost alone did not predict
fewer iterations. Historical initial-violation/line-search traces were not archived.

One fresh, unchanged full-horizon update at **0.02 s** used its saved measured
state, previous applied tensions, and shifted update-1 warm plan. It reproduced
the historical objective, tensions, states, 120 iterations, 404 evaluations, and
`3.6927926e-13` scaled violation. Exit flag **0** means a feasible iteration-limit
plan, not convergence. Initial first-order optimality was 641.072356 and final
optimality 0.0006827473. Its complete trace is in
[update.json](../../evidence/sorosim_s35/attempt02/update.json).

| Fresh stage | Seconds |
|---|---:|
| Engine startup, outside update | 7.995188 |
| Candidate construction, outside update | 0.177673 |
| Warm-state regeneration | 2.211837 |
| Nonlinear SQP | 68.553705 |
| Independent validation, including separate physical defects | 0.854399 |
| MATLAB update | 71.861659 |
| Python/Engine call | 71.880113 |
| Transfer, dispatch, and serialization residual | 0.006892 |
| Session quit call, outside update | 0.006767 |

SQP accounts for 95.40% of this MATLAB update. The historical shared-session
startup was 6.570856 s, construction 0.174447 s, quit call 0.002821 s; historical
per-update boundary residuals were 0.005011, 0.057233, 0.050992 s. Quit-call time
does not prove OS process termination latency.

The fresh callback counters directly measure:

| Quantity | Value |
|---|---:|
| Objective / constraint / inspect requests | 404 / 404 / 121 |
| Cache hits / misses / distinct vectors | 645 / 284 / 284 |
| Full trajectory evaluation total | 66.711821 s |
| Mean full trajectory evaluation | **0.234901 s** |
| Derivative calls, 10 nodes per miss | 2,840 |
| Derivative evaluation total | **66.338734 s**, 96.77% of SQP |
| Constraint/Jacobian assembly | 0.186217 s |
| Node objective/output/gradient assembly | 0.111314 s |
| Objective-request time / constraint-request time | 66.495260 / 0.007705 s |

Request times overlap the full-evaluation categories; do not add them together.
Input-penalty/final-vector assembly and bookkeeping occupy the unallocated small
remainder. All 284 misses were distinct. Adjacent requests share work, and this
solve did not recompute an evicted vector. A separate declared `z, z+1e-8, z`
probe gives three misses and two unique vectors, documenting the existing
single-vector cache's behavior without claiming that this artificial pattern
occurred in SQP. A second cache is unsupported by the measured solve.

### Kernel measurements and instrumentation qualification

Three warmed calls at each saved operating point, excluding force decomposition:

| Checkpoint s | First derivative call s | Median derivative ms | Routing including differences ms | Recursive dynamics/residual ms | Routing without differences ms |
|---:|---:|---:|---:|---:|---:|
| 0.00 | 0.340722 | 66.555 | 32.546 | 33.315 | 1.338 |
| 0.01 | 0.024642 | 23.773 | 19.715 | 3.949 | 0.863 |
| 0.02 | 0.026662 | 27.773 | 20.998 | 4.568 | 0.910 |

Column medians are taken independently and need not sum. Initial calls retain
JIT effects; the zero-state three-call sequence has not reached the later
steady regime. The long solve averages 23.359 ms per derivative call.
Later warmed routing occupies about 76–83% of the combined kernel cost.

One derivative call performs exactly **25 forward-kinematics calls, 25 kinematic
Jacobian calls, 525 attachment evaluations, and one DAEJacobians recursion**.
There is one base routing evaluation and 24 perturbed routing evaluations for
12 centered coordinate differences. Tendon-force and tip-velocity state
derivatives share those perturbations. This repeated geometry is the dominant
warmed calculation; the full SQP slowdown combines that cost with optimizer work.

Raw profiler times at the nonzero 0.01 s point: forward kinematics 28.825 ms,
Jacobian 46.611 ms, routing inclusive 105.901 ms, DAEJacobians 111.681 ms, and
complete derivative 225.879 ms. **These instrumented times are not production
kernel costs**: profiling inflates the complete kernel by 9.51 times there and
7.52 times at 0.02 s, disproportionately inflating recursive dynamics. Raw
function tables and counts are in `kernels_*.json`.

[calibration.json](../../evidence/sorosim_s35/attempt02/calibration.json) retains
executed-line timings. Across 12 columns, force-difference arithmetic took
0.257 ms and tip-velocity-difference arithmetic 0.389 ms; their shared kinematics
line took 70.027 ms across 25 calls. The complete force-residual subtraction
took 0.332 ms and tip-velocity multiplication 0.205 ms. These are profiled line
measurements, not separately transferable warmed costs. Chord assembly and
attachment work are retained by line/function; shared geometry cannot be
uniquely allocated to the two derivatives without an arbitrary convention.

Counter-enabled callback evaluation samples versus disabled samples differed
by approximately −2.4%, +8.2%, and −0.6%. These short samples measure noise plus
instrumentation effects, not a strict overhead bound. Disabled callback baselines
are 0.258306, 0.272811, 0.272494 s; no MATLAB profiler ran during the fresh solve.
The measured complete-update timing therefore remains useful, but its roughly
2-second difference from the historical update is **not an optimization speedup**.

Same-data serialization microbenchmarks: Python encoding 0.702–0.783 ms, Python
decoding 0.413–0.423 ms, MATLAB encoding 4.574–4.958 ms, MATLAB decoding
1.091–1.237 ms. The live Engine boundary timer aggregates these with dispatch;
the microbenchmark cannot exactly apportion that live residual. Serialization
is far below the physics cost.

The scaled delivered-plan constraint Jacobian condition estimates are 76,932.6,
73,374.7, 69,313.6. They do not increase with update time. Trial-point Jacobian
conditioning and separate scaling interventions were not measured; a dominant
conditioning explanation remains **inconclusive**. Original state scaling
10/1000 and defect normalization /10 and /0.001 remain unchanged.

## B. Prediction comparison and controlled findings

The authoritative archived candidate and physical identities, model specification,
XML hash, channel order, initial/next full states, actual input forces and timing
are in `physical.json`, `provenance.json` and `environment.json`. Python is
3.11.16; MATLAB is R2024a 24.1.0.2537033; installed MuJoCo is 3.13.0. The pinned
SoRoSim checkout remains clean at `24d573a3e864ffda87c42ee462a6ed620133cc7b`.
The independent GVS reference uses the historical S2 200-step spatial resolution
and five quadrature points, not a changed robot. Its graph built in 118.457 s.

The comparison contract is verified for these three checkpoints:

- 48 named hinge positions/rates project to the archived 12-coordinate state;
  reconstruction uses the existing integrated-cell mapping.
- Commands are held for 0.01 s, with 20 authoritative 0.0005 s MuJoCo steps.
  Actual tensions equal prediction inputs in the recorded channel order.
  Positive tension uses negative MuJoCo actuator force; existing bounds remain
  [0,8] N. At the first two updates two channels reach 8 N.
- Measurements are interval-end positions and `mj_jacSite(tip_site)*qvel`, in
  world coordinates. Predictions use the same declared physical tip attachment
  and world frame. Reconstructed archived tip positions agree below 1e-12 m.
- Mount rotation is identity, translation [0,0,0.15] m, gravity [0,0,−9.81] m/s².
  There are no applied external forces, contacts, active constraint dimensions,
  or actuator internal states at the tested checkpoints.
- Re-solving the production first implicit step reproduces the archived predicted
  tip below 2e-15 m and 9e-15 m/s. Observation timing, input sign/order and a
  different held command are rejected as explanations within this checked scope.

### Per-checkpoint observations

All position entries below are **mm** and velocity entries **m/s**, shown as
position / velocity. Deltas are norms of paired outputs, not additive shares.

| Comparison | Start 0.00 s | Start 0.01 s | Start 0.02 s |
|---|---:|---:|---:|
| Historical prediction vs original MuJoCo next | 3.189659 / .164063 | .885877 / .142499 | 3.930318 / .102339 |
| Projection maximum, rad/m | 0 | .102457 | .535309 |
| Original vs reconstructed instantaneous tip | 0 / 0 | .002044 / .000584 | .018031 / .002870 |
| SoRoSim vs original GVS, same implicit Euler | .000011 / .00000201 | .000172 / .00000692 | .000329 / .00001272 |
| SoRoSim production vs 64-substep prediction | 3.170897 / .182741 | 1.426611 / .027322 | .469943 / .083922 |
| Last refinement change, 32 to 64 substeps | .060663 / .003407 | .023183 / .000969 | .012369 / .001274 |
| Original vs reconstructed MuJoCo next | 0 / 0, identical zero state | unavailable | .069927 / .007127 |
| Refined SoRoSim vs original MuJoCo next | .047600 / .021339 | 2.267945 / .123049 | 3.750661 / .169439 |
| Refined SoRoSim vs reconstructed MuJoCo next | .047600 / .021339 | unavailable | 3.716297 / .163637 |

“Refined” is a finite-resolution result, not an exact continuous-time solution.
The last refinement remains comparable to the small initial position residual;
that residual cannot be assigned entirely to physical-model differences.
Later millimeter-scale residuals are substantially larger than the last
refinement changes. Checkpoint 1's remaining paired residual is unavailable;
the original-state residual is retained instead of inventing a reconstruction.

### Mathematical implementation comparison

Same state/input comparisons evaluate complete residuals at declared acceleration
`linspace(-10,20,12)` rad/(m·s²), mass, tendon force, tip motion, and forward
acceleration. Both implementations then use the same one-step implicit-Euler
equations and residual normalizations.

| Maximum component discrepancy | 0.00 s | 0.01 s | 0.02 s |
|---|---:|---:|---:|
| Mass, kg·m⁴ | 9.529e-11 | 9.583e-11 | 9.590e-11 |
| Complete residual, N·m² | 6.304e-8 | 1.876e-7 | 3.234e-7 |
| Tendon generalized force, N·m² | 5.204e-18 | 2.234e-7 | 3.182e-7 |
| Initial tip velocity, m/s | 0 | 8.880e-6 | 8.377e-6 |
| Forward acceleration, rad/(m·s²) | 287.111 | 350.915 | 722.761 |
| Relative forward acceleration | 3.725e-5 | 1.300e-4 | 1.893e-4 |
| SoRoSim mass condition | 173,951 | 172,854 | 168,367 |

The forward accelerations reach millions of rad/(m·s²) at these nonequilibrium
states; absolute differences are amplified by the conditioned mass inversion.
All three exceed S2's earlier 100 rad/(m·s²) probe bound. The last two also exceed
S2's earlier absolute tendon-force and tip-velocity probe bounds. This is an
observed accuracy limitation beyond those historical probes; no historical
acceptance or tolerance was rewritten. Small matched one-step differences do
not establish uniform transient acceleration accuracy.

Matched one-step generalized-state norm differences are q = .000176, .000416,
.000545 rad/m and qdot = .017571, .041644, .054515 rad/(m·s). Independent forward
balance and positive mass checks pass. Counter-enabled and disabled callback
outputs, gradients and Jacobians agree **exactly** at all three saved vectors.
Directional relative objective errors are at most 2.972e-8, and constraint
errors at most 3.474e-9; absolute maxima are 5.613e-8 and 5.072e-7 respectively.
These are local checks; raw matrices and vectors remain in the evidence.

**Conclusion:** a large SoRoSim-versus-GVS one-step implementation discrepancy is
rejected for these matched states and inputs. A uniform forward-acceleration
accuracy claim is unsupported. The original GVS model is an independent
mathematical reference, not physical truth.

### Integration and representation interventions

SoRoSim refinement uses 1, 2, 4, 8, 16, 32, 64 implicit-Euler steps over the same
0.01 s, with fixed actual tensions. No production integrator changed. Maximum
normalized root residual is 8.742e-12, and force residuals are below 8.8e-15 N·m².
Tip and generalized-state changes decrease with refinement. From 32 to 64,
q changes are .017989, .009414, .008432 rad/m, and qdot changes are 1.365197,
.543222, .614770 rad/(m·s). These provide convergence evidence, not exactness.
64-step integrations cost 10.347, 9.004, 8.649 s; production-step diagnostic
costs are .705, .372, .299 s. They include root initialization effects and are
not optimized rollout benchmarks.

At zero state, integration refinement reduces observed position discrepancy
by 98.5% and velocity discrepancy by 87.0%. **Supported:** coarse implicit Euler
is a major cause of that initial transition's error under this intervention.
At later checkpoints refinement worsens position or velocity agreement; it
does not explain the entire prediction gap and is not a universal remedy.

Rate-projection residual maxima are 0, 22.108705, 61.169039 rad/(m·s).
Initial represented-cell tip errors and the checkpoint-2 next-state intervention
are much smaller than total errors. **Supported:** discarded components affect
this short transition, but projection residual magnitude alone is not a tip-error
attribution. **Unresolved:** checkpoint 1's paired one-step influence.
The checkpoint-2 reconstruction changes potential energy from .145415320 to
.145378706 J and kinetic energy from .017552410 to .017508868 J; these differences
qualify the intervention. It does not establish a uniquely additive causal share.

### Rod versus rigid-cell execution

With exactly the same represented q/qdot, SoRoSim and reconstructed MuJoCo already
differ instantaneously by **.987994 and 2.278464 mm**, and **.134613 and .137714 m/s**,
at the later checkpoints. Zero-state differences are roundoff. This controlled
kinematic comparison demonstrates a rod/rigid-cell geometry and output-map
difference beyond discarded modes. It must not be relabeled as a frame bug or
as proof of a particular dynamic-force error.

An instantaneous virtual-work diagnostic uses the existing reconstruction matrix
L: `Lᵀ M_mj L`, `Lᵀ qfrc_passive`, `Lᵀ qfrc_actuator`, `Lᵀ qfrc_bias`. It is
not another backend or a trajectory intervention. Relative Frobenius mass
differences are 10.0945%, 10.0480%, 9.8969%. Passive-force norm differences are
0, 2.186e-5, 3.533e-5 N·m²; tendon-force differences are 3.810e-17, 1.052e-4,
2.459e-4 N·m². Complete zero-acceleration force-balance differences are
6.269e-4, 2.988e-4, 4.421e-4 N·m². Full pulled-back arrays are retained.

**Supported:** restricted instantaneous rigid-cell mechanics differ from the
rod model. **Inconclusive:** ranking distributed inertia, connector/payload
inertia, joint damping, tendon geometry, accessible deformation modes, and
their interactions as causes of the remaining trajectory residual. No physical
terms were changed or fitted. Contacts/external forces are absent in the checked
states, and actuator saturation/sign/order do not explain these matched inputs.

## C. Changes and scope

| File | Change and responsibility |
|---|---|
| `sr_nmpc_callbacks.m` | About 30 added lines: optional request/cache/evaluation counters and stage timing in the existing cache |
| `sr_nmpc.m` | Six added lines: opt-in profiling and optimizer trace; mathematical problem/stopping rules unchanged |
| `sr_derivatives.m` | One additional routing-time evidence field |
| `sr_gateway.m` | Two lines dispatch the narrow diagnostic operation |
| `sr_diagnose.m` | 77 lines: bounded kernel/callback/integration/serialization probes using production mechanics |
| `manifest.py` | One line binds diagnostic source into backend provenance |
| `sorosim_s35_probe.py` | 366 lines: archive-based experiments, independent GVS comparison, summaries and reproduction CLI |
| `test_sorosim_s35.py` | 112 lines: eight focused numerical/source/contract checks |
| `test_sorosim_contract.py` | Historical freeze checks S3's committed tree; new test checks current S3.5 source freeze |

No performance optimization was implemented. Shared finite differences dominate,
but replacing them analytically would require a larger validated mechanics change.
The measured cache already suffices. There is no demonstrated complete-controller
speedup, new cache framework, backend, robot configuration, Store, Agent rule or
automatic RL fallback. The driver has one experiment path and explicit small
refinement/calibration modes; no redundant diagnostic script remains.

## D. Validation, failures and evidence limits

**29 focused tests pass**, including all 15 existing SoRoSim tests, eight S3.5
tests, five existing feedback tests, and the historical acceptance-contract check.
The exact output is [focused_tests.txt](../../evidence/sorosim_s35/focused_tests.txt).
The first check run passed 20/21 tests; its sole failure correctly detected that
current instrumented files differ from S3's historical source freeze. Historical
freeze data remain unchanged; both historical and current source identities now
have explicit checks. No evaluator or feasibility threshold was changed.

[attempt01/failure.json](../../evidence/sorosim_s35/attempt01/failure.json) and
`failure_context.json` preserve the failed archive lookup. The final raw
`nmpc_updates.json` export lacks post-command `actual_tension_n`; actual forces
are available in every trajectory row's `tension_n`. Two checkpoint-1 replays
were computed before the exception, but their outputs were lost in memory before
persistence. They were **not** rerun. The corrected batch used the remaining
checkpoint-2 reconstruction replay. Thus there were exactly **three new
one-interval MuJoCo replays**, with checkpoint 1's numerical result unavailable.
There was exactly **one full-horizon NMPC solve**, zero full-task executions,
zero RL training runs and zero provider requests. Each MATLAB batch owns one
Engine session; refinement and calibration use separate bounded batches.

The original qpos/qvel are complete for this memoryless articulated model;
qacc warm-start values were not archived. No active constraint solve exists at
the sampled states, but this remains a reproduction qualification rather than
an invented saved variable. The frozen `validation/sorosim/`, all S0–S3 artifacts,
RL route, task evaluator, task duration/budgets and scientific acceptance are intact.
Early velocity errors are not the final .02 m/s holding requirement. Mathematical
plan feasibility, model prediction quality and physical task acceptance remain
separate. S4, S5 and S6 are **not complete**.

## E. Research recommendation and hypotheses

Prioritize a scoped investigation of the **represented rod-to-cell geometry and
mechanics**, using the measured instantaneous differences to choose discriminating
tests. Use finer integration as a diagnostic reference; a production integration
change needs separate cost/acceptance evaluation because later agreement can
worsen. Analytical/shared kinematic derivatives are the measured computation
opportunity, with validation effort required before implementation. More caching
and Engine-transfer optimization have little support in this measured solve.

The remaining physical cause ranking is **inconclusive**. Do not tune the frozen
robot to three transitions. Preserve this discrepancy as Agent feedback and leave
later choice among NMPC, design/model work, direct RL, valid residual RL and STOP
to the existing research architecture. These findings do not independently justify
proceeding to S4 migration or selecting either controller family.

## F. Git identity and reproduction

The current 60-file source freeze is
[source_freeze.json](../../evidence/sorosim_s35/source_freeze.json).
Invocation-time byte hashes remain in each `provenance.json`. The Python CLI was
finalized after the batch to restore normal three-replay defaults and add
summary/refinement/calibration modes; the executed resume batch used one remaining
replay. MATLAB kernel/callback changes preserve all numerical physics. The later
diagnostic-only calibration adds executed-line fields and serialization probes.

Diagnostic/evidence commit: `54de40c3ada737ece146bab87d452ca64402392a`
(`feat(sorosim): profile S3.5 callbacks and preserve matched prediction diagnostics`).
The subsequent documentation commit carries this report. The final pushed SHA
is obtained with the exact `git rev-parse HEAD` / `git ls-remote` commands below
and is recorded in the delivery response; a file cannot embed its own commit SHA.
Normal push target is `origin/feat/sorosim-matlab-nmpc`. No force push or merge.

```powershell
Set-Location D:/softrobot-agent/.worktrees/sorosim-matlab-nmpc
$p='D:/softrobot-agent/.mainline5-env/Scripts/python.exe'
$env:PYTHONPATH='.;tests/research;C:/Program Files/MATLAB/R2024a/extern/engines/python/build/lib'
$env:SOROSIM_ROOT="$env:TEMP/softrobot-sorosim-24d573a3"
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'

# Saved-evidence/source/contract checks; no new engines, solves or physical steps.
& $p -m unittest test_sorosim_contract test_sorosim_physics test_sorosim_nmpc test_sorosim_integration test_sorosim_s35 test_agent_feedback test_task_analysis_contract.TaskAnalysisTests.test_old_contracts_and_acceptance_unchanged -v

# Fresh independent reproduction, within a fresh equivalent diagnostic budget.
# Destination must not exist. This uses three replays and one full NMPC update.
$out='runs/sorosim-s35-'+[guid]::NewGuid().ToString('N')
& $p tests/research/sorosim_s35_probe.py $out --full-update
& $p tests/research/sorosim_s35_probe.py $out --refine
& $p tests/research/sorosim_s35_probe.py $out --calibrate
& $p tests/research/sorosim_s35_probe.py $out --summarize "$out/diagnosis.json"

git log --oneline cdb2f8d196af7f7d04c14efda3b960b88c20a782..HEAD
git rev-parse HEAD
git ls-remote origin refs/heads/feat/sorosim-matlab-nmpc
git status --short
```

Fresh timings may vary with JIT and machine load. Numerically meaningful values,
residuals, failed attempts and local limitations must remain visible. The initial
recorded batch's uninstrumented physics, refined predictions and fresh update
are all real computations from this work session, not synthetic fixtures.
