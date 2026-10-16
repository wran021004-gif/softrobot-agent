# SoRoSim S3.6 and S4 delivery

Starting and fetched remote SHA: `eb3907c5fb4710137be2af0f874e67eadbdf2f9e`.
Its ancestry was checked before changes. Development remains on
`feat/sorosim-matlab-nmpc`. The authoritative design, physical compiler, task,
acceptance thresholds, default controller and RL route are unchanged.

## Stage status

| Stage | Implemented and executed | Acceptance | Source commit |
|---|---|---|---|
| S3.6 | Three matched static states, 50 frames each, separated forces, additive link inertia/gravity, controlled geometry substitutions, immediate replay persistence | Passed within bounded diagnostic scope | `3f45b849` (normally pushed) |
| S4-A | Candidate-bound operating points, MATLAB statics/linearization/IFT, existing shared feasibility/Gramian kernels and scoped evidence | Passed in measured local scope | `8f4c642b` (normally pushed) |
| Performance | Shared kinematic traversal, matched old/new derivative and full-NLP evaluation | Passed for measured kernel/callback speedup | `bb7b947f` (normally pushed) |
| S4-B | Two actual physical designs, full-task control optimization, recipe-consistent recovery and separate mathematical replay through Harness | Passed for bounded co-design and verified relaxed trajectories; optimizer convergence and original task satisfaction not achieved | `602c66f3` numerical source; `a5347183` final validated evidence |

## S3.6 evidence and findings

Real evidence: `evidence/sorosim_s36/attempt02/`. The earlier `attempt01/`
preserves the MATLAB heterogeneous-JSON sample parsing failure. No result was
fabricated or discarded. There were **zero new MuJoCo time steps/replays and
zero NMPC solves**. Three successful MATLAB static diagnostic calls reused
S3.5's saved q, qdot and actual tensions. One earlier diagnostic failed before
any complete mathematical result. Each expensive successful call was persisted
before Python postprocessing began.

`provenance.json` binds the exact physical/model identities, coordinate and input
orders, original source hashes and numerical settings. The original candidate
reference is in `isolation.json` (the earlier provenance exporter incorrectly
wrote its optional candidate field as null; the design/physics identities were
present). `rod_*.json` includes each complete input and MATLAB output.
`comparison_*.json` contains all poses, world spatial Jacobians, force arrays,
absolute/relative norms, units and conditioning. The sample convention uses
angular rows followed by linear rows; velocities use the same represented rate.
The S3.5 physical artifact and archived XML remain untouched.

| Checkpoint (s) | Tip discrepancy (mm) | Orientation (rad) | Restricted mass relative Frobenius error | Gravity relative norm error |
|---:|---:|---:|---:|---:|
| 0 | roundoff | 0 | 0.100945 | 0.068147 |
| .01 | .987994 | .00167917 | .100480 | .067986 |
| .02 | 2.278464 | .00685087 | .098969 | .067441 |

At .01 s the discrepancy is .233 mm at the guide/connector and .988 mm at the
payload. At .02 s it is .317 mm and 2.277 mm respectively. The geometry error
accumulates along the flexible chain. The independently reused GVS midpoint
implementation at 400 steps agrees with SoRoSim at every sampled position to
5.65e-8 m; 200-to-400 refinement changes positions by at most 1.62e-7 m.
Compiler-derived attachment positions agree with actual MuJoCo tendon/tip sites
to 3.47e-18 m at the moving states. No principal-axis or connector correction is
justified by these results.

The controlled calculation in `isolation.json` reconstructs physical serial
hinge/straight-cell tip positions to 2.24e-16 m, then changes one kinematic
mechanism at a time while retaining integrated curvature and physical lengths:

| Time (s) | Ordered hinges to single exponential rotation (mm) | Straight translation to constant-curvature arc (mm) | Arc versus continuous-rod remainder (mm) |
|---:|---:|---:|---:|
| .01 | .007230 | .961730 | .026427 |
| .02 | .075149 | 2.217676 | .059420 |

This supports rigid-cell translation as the dominant **tested instantaneous
position** mechanism. Sequential hinge rotations also contribute. These are
path-dependent vector changes, not additive causal fractions of dynamic error.
The remaining arc/rod discrepancy includes variation of curvature within cells.
No physical definition or production kinematics was modified.

Gravity is isolated at identical q with zero velocity. Elastic force is minus
zero-rate passive force; viscous force is minus its rate-induced difference.
Velocity-dependent bias is the difference of MuJoCo bias at matched and zero
rates. Tendon force uses the same actual nonnegative tensions and input order.
Both sides use `M*a + velocity_bias + elastic + viscous - gravity - tendon`.

At .01/.02 s the force discrepancy norms (N m²) are respectively:

| Term | .01 s | .02 s |
|---|---:|---:|
| Gravity | 6.2468e-4 | 6.1539e-4 |
| Velocity-dependent inertia | 4.2262e-4 | 8.4884e-4 |
| Elastic | 1.1507e-5 | 2.0585e-5 |
| Viscous | 1.3482e-5 | 1.7219e-5 |
| Tendon | 1.0516e-4 | 2.4595e-4 |
| Complete zero-acceleration residual | 2.9879e-4 | 4.4206e-4 |

Additive link kinetic-energy and gravity calculations reconstruct each model's
full mass/gravity to relative roundoff. At .02 s the mass discrepancy norms for
segment 0, guide, connector, segment 1 and payload are 6.6545e-7, 7.5680e-8,
1.2175e-7, 8.8726e-7 and 7.9987e-7 kg m⁴. These identify affected link contributions;
their matrix norms are not additive. Even rigid payloads differ because their
restricted Jacobians differ. This does not isolate intrinsic inertia parameters
from geometry. Gravity and velocity bias exceed elastic/viscous discrepancies in
these probes, but a unique dominant cause of future trajectory error remains
unresolved. Acceleration solves and mass condition numbers are retained and
must be interpreted with their conditioning. A constant-L instantaneous pullback
is not a complete equivalent nonlinear reduced MuJoCo dynamics model.

Previous S3.5 integration/projection conclusions remain valid, including the
unavailable checkpoint-1 replay. No replay was rerun to fill that historical gap.
The new persistence fix writes each replay before the next begins, and writes
refinement/calibration results immediately. A synthetic injected later failure
verifies earlier atomic output survives; its mock stepping is not physical data.
Of 27 focused checks, 26 passed in the sandbox. The persistence fixture was
blocked by sandbox temporary-directory ACLs and passed separately with normal
machine access. Both logs are retained; no numerical failure was hidden.

## S4-A implementation and measured results

`sr_analysis.m` owns MATLAB statics, constrained target construction, geometric
waypoint construction, residual-based dynamic derivatives, conservative tangent
classification and input/design sensitivity. `sorosim_analysis.py` binds the
existing candidate initializer, compiler and protocol to `EndpointLinearizedModel`.
`tools/research/analysis.py` selects the actual provider before importing legacy
CasADi code. Existing SciPy kernels and `ScopedMathematicalClaim` classification
remain authoritative. Only lazy imports and an optional model identifier changed
in the original mathematical adapter; its calculations are unchanged.

Seven candidate-bound MATLAB investigations ran, including two perturbed-design
models inside the seventh operation's length investigation (nine if each physical
design evaluation is counted separately). Finite-difference equilibrium checks
are included in these investigations, not hidden as a separate campaign. All
remain within the twelve-evaluation allowance. No physical execution occurred.
Evidence is `evidence/sorosim_s4a/attempt01/`. The exact canonical configuration,
protocol, model specification, dependency hashes and every successful raw return
are saved. The final stage source freeze records delivered source identities;
after numerical execution a local MATLAB variable was renamed and Python compact
diagnostics/contract tests were added without changing the measured equations.

The existing standardized initial pretension and controller-start work points
both use the existing initializer projection and declared preparation input.
Their agreement here is expected: both have four .2 N tensions. Neither is a
static equilibrium. The target equilibrium uses the frozen goal and actual force
bounds; MATLAB SQP converged in 14 iterations / 40 function evaluations, with
3.79595e-9 m position residual and 1.18395e-16 N m² static residual. Its tensions
are approximately `[2.44102, 1.60782, 3.04774, 3.17983] N`. The geometric halfway
point converged in 11 evaluations; it is explicitly **not** an equilibrium.
The saved-state calculation uses the archived .02 s represented state and input,
retains its .33 s remaining task horizon, and is a frozen nonequilibrium model.

All exported models have 24 states, four physical tension inputs, and world-frame
position and velocity outputs. Acceleration Jacobians solve the complete residual
mass equation at the returned acceleration. Independently perturbed MATLAB-local
states/inputs pass the original protocol's normalized checks. Dynamic derivative
relative errors at the initial/target/halfway points are 2.08e-11, 2.23e-9 and
1.89e-8; raw absolute errors are retained because acceleration is stiff and scaled.

A fixed-input .2 N equilibrium converged in four iterations, residual 4.505e-17
N m². Its total loaded static tangent includes tendon-load state derivatives.
All symmetric tangent eigenvalues are positive (minimum 5.945e-5), with relative
asymmetry 1.16e-9: this supports a strict local conservative potential minimum,
not a closed-loop stability claim. The independently re-solved input perturbation
agrees with implicit position sensitivity to relative 1.253e-7.

`sorosim_static_ift_v1` extends the existing typed research analysis request with
input/design sensitivity and `fixed_input_equilibrium`. Design sensitivity requires
two existing, verified study candidates differing in exactly one supported
continuous parameter. The existing family generator and domains own admission.
Topology and nonsmooth derivative requests are rejected explicitly. For segment
0 length, the pair is .2 ± .00002 m. All physical terms and the length-dependent
coordinate transformation are rebuilt. The direct geometric partial is
`[.839758,.115823,-.578250] m/m`; total equilibrium position sensitivity is
`[.727085,.184639,-.913305] m/m`. Independent perturbed equilibria agree to relative
1.98e-9. These are local derivatives, not evidence of an improving global design.

Existing shared Gramian/spectrum kernels execute on these models. The bounded
target-equilibrium endpoint has a verified local affine feasible witness. At the
standardized initial point, the sampled affine calculation produces a verified
necessary-constraint box exclusion certificate. This excludes only that frozen
local affine problem. The .02 s saved-state trajectory attempt is **inconclusive**:
SLSQP returned status 8 and its replay failed; it was not relabeled infeasible.
All task acceptance fields remain unmeasured. Exact solver outputs, margins,
replay records, assumptions and unsupported conclusions are retained.

Raw facts, scoped verified claims, and separate research interpretations are
available through the existing evidence reader. The length-sensitivity result
contains a `diagnostic` scoped claim and an empty interpretation list; no LLM
was called. A missing tension-limit key in the engineering test binding caused
saved-state final packaging to fail. The raw MATLAB result had already persisted;
recovery reused it without a new MATLAB evaluation. The failure and recovery
are explicitly recorded. The production worker now also atomically checkpoints
successful numerical returns before later packaging can fail.

**34 focused tests pass**, including the real original GVS initial linearization,
legacy acceptance semantics, S0–S3/S3.5 evidence, no-CasADi shared analysis dispatch,
real S4 derivatives/sensitivities, unsupported topology sensitivity, and injected
solver failure remaining inconclusive. Synthetic interface checks are not physical
validation. The historical source-freeze tests read their original Git trees.

## Performance implementation and verification

The optimization is a private fused kinematic traversal in the existing routing
owner. It shares transforms and body Jacobians using the pinned upstream Zanna-4
recurrence and already installed expmap MEX. It supports exactly the adapter's
fixed-joint serial chain, one flexible division per segment, real rigid COMs and
all existing attachment/guide nodes. It does not change the rod basis, quadrature,
chord routing, finite-difference step, integration, objective, bounds or tolerances.
No new cache or optimizer was introduced. The upstream repository is unchanged.

For each endpoint chord, with delta = p2-p1, length l, unit direction e and
Jacobian difference D, dl/dq = e' D and the tendon force is -D' e u.
The Hessian is D'(I-ee')D/l plus the contraction of endpoint position Hessian
difference with e. Cross-segment/rigid-offset attachment derivatives belong in
that second term. This change retains the verified centered derivative of the
complete chord force map; it does not substitute a continuously guided-cable
Hessian. The saved computation is the duplicated geometry traversal underneath
each perturbation. An analytical second-derivative replacement remains optional.

`evidence/sorosim_performance/attempt01/` contains the exact baseline routing source
from `8f4c642b`, source hashes, matched cases, every timing sample and complete
objective/constraint arrays and Jacobians. One Engine/model alternates baseline
and optimized order across three archived selected trajectories and the original
initialized full-horizon trajectory. Each case warms four times and records nine
samples. No full solver was run and no horizon was shortened.

| Case | Routing before/after (ms) | Derivatives before/after (ms) | Unique full trajectory before/after (ms) | Full callback speedup |
|---|---:|---:|---:|---:|
| Saved 0 | 19.467 / 15.958 | 24.025 / 19.775 | 253.124 / 213.771 | 1.1841 |
| Saved 1 | 19.613 / 16.134 | 25.244 / 20.356 | 245.159 / 207.232 | 1.1830 |
| Saved 2 | 19.675 / 16.757 | 23.843 / 20.193 | 240.339 / 206.596 | 1.1633 |
| Initial | 19.766 / 15.970 | 23.891 / 20.442 | 247.528 / 217.173 | 1.1398 |

The consistent median reductions exceed typical within-batch median absolute
deviations: routing .40–.68 ms and callbacks 2.80–12.56 ms. Occasional scheduling
outliers overlap raw timing ranges; all samples remain visible. This is a measured
kernel/callback gain, **not a complete NMPC solver-level speedup** or real-time
control result. Historical S3/S3.5 timings remain historical measurements.

Maximum full constraint-Jacobian component difference is 2.334e-7 in scaled NLP
units, with relative norm at most 7.95e-11; centered finite differences amplify
roundoff. Objective, gradient, constraints, tendon lengths/forces/tangents,
tip-velocity derivatives and dynamics pass matched tolerances. Independent
directional objective/constraint checks pass the unchanged 2e-4 bound. Nine
focused saved-evidence/analysis/NMPC tests pass. No mathematical or physical task
acceptance threshold changed.

## S4-B implementation, failures and verification

The existing `research_plan` generate/mechanics/replay/stop actions execute a
bounded sensitivity-directed outer step and candidate-local full-task inner SQP.
The changed variable is `segments.0.length_m`: **.200 to .195 m**, within the
original family interval **[.080, .240] m**. The .005 m proposal uses the sign of
the already verified S4-A static squared-position-error derivative. This is a
proposal, not a certificate of full-task improvement. All other physical choices
and control-objective settings remain identical. Both candidates are generated,
compiled, identified and owned by the existing Store; each Engine constructs its
own mathematical model. The two physical design hashes are:

- .200 m: `e6baadb5c508345a5a0bbd6df4da9794290e976d4f56ec40ac2e4b540f3dd828`
- .195 m: `10035885ded80b7afbf2faa28988c6275a18ac04f3232c5d0972acced81af9ad`

Each full problem has 36 state nodes, 35 held four-tension commands, 24 states,
two nonnegative slacks, 1,006 variables, 864 equalities and 13 sampled task
inequalities. The frozen task translator supplies terminal/holding position and
holding speed requirements at their original world-frame post-step times. For
each sample, `||y-reference||^2/radius^2 - 1 <= slack_group`. The objective is
`position_slack + speed_slack + .001*(mean((u/8)^2) + .1*mean(diff(u/8)^2))`.
Initial conditions, implicit Euler at .01 s, .35 s duration, physical 0--8 N
bounds, original SQP tolerances and 120-iteration limit are unchanged. No slack
is treated as original task satisfaction. Independent initialized full-problem
derivative errors are 3.706e-7 (objective) and 1.930e-10 (constraints), below the
unchanged 2e-4 threshold.

The first implementation/source freeze was `5403348e`, following integration
commit `f6fe2eac`. Both genuine solves reached their iteration limits. Their low
raw objectives (.000323258 and .000308880) were **not valid ranking evidence**:
constraint violations were .993236653 and .037512614, and both independent
replays failed. The first study consumed two nonlinear solves and two replays,
425.165471 s of recorded numerical work, and is sealed at
`evidence/sorosim_s4b/pilot/`. Raw optimizer vectors, outputs, worker boundaries,
logs, candidate configuration, scope claims and costs remain in its immutable
archive. The original results were never replaced with corrected numbers.

The omission was the existing frozen recipe's `recover_returned_tensions=true`
behavior in the new offline adapter. The correction uses the original NMPC
preparation/root solver to reintegrate the returned bounded tensions from the
actual initial state, then recomputes the **same** epigraph slacks on that
trajectory. It retains the raw optimizer result and reports recovery separately.
It changes neither solver convergence nor the unrelaxed task definition.
Independent replay starts another Engine/model and recomputes implicit roots and
separate `sr_dynamics` force balance. Acceptance still requires scaled violations
and reintegrated state mismatch at most 1e-5.

The supplementary study is explicitly linked to the first authorization and
limited to the remaining two complete solves, on the same two physical designs.
Its frozen source is `602c66f3` (numerical recovery implemented in `dbcd057b`).
The two Store ledgers remain separate and cumulative assignment use is four
complete solves and four mathematical replays; no counter was reset. This is
implementation validation after a diagnosed omission, not repeated timing trials.

Harness preflight failures are preserved in `preflight_failures.json`: the
observation resolver did not recognize the existing SoRoSim controller, and
registry availability required package metadata even though the installed Engine
imports through PYTHONPATH. The fixes reuse existing signal and registry owners.
The supplemental config initially tried nested defaults, which the existing
loader rejects; `602c66f3` uses its supported single-level contract. These failures
occurred before numerical reservations. A topology test initially collided with
the production grant and subsequently hit Windows SQLite cleanup locking; both
logs remain. The final isolated test uses the repository's existing test-grant
pattern and closes connection cycles before cleanup.

Actual one- and three-segment candidates also pass the existing generation,
physical compilation and SoRoSim model-specification route, with distinct
dimensions and identities. They perform no mathematical solves or physical steps;
this checks dimension rebuilding, not dynamic validity of untested topologies.
There are two unique optimized physical designs plus two unique topology-test
designs in S4-B. No live provider call, RL training or MuJoCo step is involved.

Final evidence is `evidence/sorosim_s4b/recovered_pilot/`, with cumulative cost
and compact comparison in `evidence/sorosim_s4b/aggregate.json`. Both independent
replays pass. Both optimizers still report exit flag 0 after 120 iterations
(335 and 345 function evaluations); neither is claimed to have converged.

| Root length (m) | Verified relaxed objective | Position slack | Speed slack | Independent scaled violation | Solve worker / replay worker (s) |
|---:|---:|---:|---:|---:|---:|
| .200 | .987058566 | .000763355 | .985971953 | 1.24553e-12 | 193.571 / 23.336 |
| .195 | .037970658 | 0 | .037661778 | 4.38018e-13 | 196.247 / 24.038 |

Reintegrated scaled state error is zero in both cases. Separately recomputed
force residual maxima are 1.246e-15 and 4.380e-16 N m². The objective decreases
by **96.1532%** between the two verified evaluated candidates; the Frobenius
norm of the 35-by-4 tension-sequence change is **12.6430 N**. The full original
and changed control trajectories, states, times and exact channel order are in
`summary.json` at `rows[i].solve.trajectory`. Representative commands in that
same order are:

| Root length (m) | First held command (N) | Last held command (N) |
|---:|---|---|
| .200 | [0, 0, 6.33849, 5.44277] | [3.40024, 3.05345, 3.24681, 3.33379] |
| .195 | [0, 0, 6.91971, 3.49380] | [2.13053, 1.20616, 2.30784, 2.93987] |

These improvements rank only the two evaluated relaxed trajectories. Both fail
the original unrelaxed sampled requirements: the changed robot still exceeds
the .02 m/s holding speed bound. Positive slack, incomplete optimizer convergence,
single-step design exploration and the separately quantified rod/cell mismatch
preclude global optimality or MuJoCo task-success claims.

The corrected validation study records 437.794620 s numerical work; including
the preserved first study gives **862.960091 s**, four complete nonlinear solves,
four mathematical replays and 14 public plan operations. Kernel checks, prior
S4-A investigations and cheap topology compilation are separately reported and
are not presented as physical trials. Two final saved-evidence/derivative tests
pass, as do the earlier 21 integration checks, 28 targeted regression checks and
the final topology compilation check. Both immutable archive SHA-256 checks pass.
Synthetic failure fixtures and software-only checks remain labeled as such.

## Reproduction

```powershell
Set-Location D:/softrobot-agent/.worktrees/sorosim-matlab-nmpc
$p='D:/softrobot-agent/.mainline5-env/Scripts/python.exe'
$env:PYTHONPATH='.;tests/research;C:/Program Files/MATLAB/R2024a/extern/engines/python/build/lib'
$env:SOROSIM_ROOT="$env:TEMP/softrobot-sorosim-24d573a3"
$env:OPENBLAS_NUM_THREADS='1'; $env:OMP_NUM_THREADS='1'; $env:MKL_NUM_THREADS='1'
# Cheap: saved evidence only, no Engine or optimization.
& $p -m unittest test_sorosim_s36 test_sorosim_s35 -v
# Verify clean pinned upstream and hash source/binaries.
& $p -c "import os; from extensions.tendon_family.sorosim_session import dependency_identity; print(dependency_identity(os.environ['SOROSIM_ROOT'])['commit'])"
# Compare every pinned upstream MATLAB/MEX hash, without starting MATLAB.
& $p -c "import os,json; from extensions.tendon_family.sorosim_session import dependency_identity; e=json.load(open('evidence/sorosim_s4b/check01/environment.json')); assert dependency_identity(os.environ['SOROSIM_ROOT'])==e['dependency']; print(e['environment']['version'],e['environment']['optimization'])"
# New bounded static calculations; new destination required, normal machine access.
$out='runs/sorosim-s36-'+[guid]::NewGuid().ToString('N')
& $p tests/research/sorosim_s36_probe.py $out
& $p tests/research/sorosim_s36_probe.py $out --isolate
# MATLAB release, toolbox, binaries and actual startup recorded in $out/environment.json.
# Cheap S4 saved-result and original-contract checks.
& $p -m unittest test_sorosim_analysis test_task_analysis_contract -v
# Fresh S4 batch: five initial investigations plus saved-state/design investigation.
$analysis='runs/sorosim-s4a-'+[guid]::NewGuid().ToString('N')
& $p tests/research/test_sorosim_analysis.py --run $analysis
& $p tests/research/test_sorosim_analysis.py --extend $analysis
& $p tests/research/test_sorosim_analysis.py --shared $analysis
# Cheap performance evidence verification.
& $p -m unittest test_sorosim_performance -v
# Fresh matched warmed kernels; no full optimizer solve.
$perf='runs/sorosim-performance-'+[guid]::NewGuid().ToString('N')
& $p tests/research/test_sorosim_performance.py --run $perf
& $p tests/research/test_sorosim_performance.py --verify $perf
# Cheap: real saved co-design outcomes, no Engine startup or nonlinear solves.
& $p -m unittest test_sorosim_codesign.CodesignTests.test_full_problem_derivatives test_sorosim_codesign.CodesignTests.test_real_design_control_and_replay -v
# Expensive: fresh authorized workspace only; two full .35 s mathematical solves.
# On the already-used workspace, inspect existing evidence instead of copying grants.
& $p tests/research/test_sorosim_codesign.py --pilot runs/sorosim-s4b-recovery-20261016 --study configs/research/study_sorosim_s4b_recovery.json
# Export defaults to that run's new export/ directory, preserving committed evidence.
```

## Remaining milestones

S5 complete MuJoCo closed-loop physical task evaluation and S6 formal backend /
Agent control-method comparison are not authorized and are **not completed**.
Neither physical completion nor an Agent/backend comparison follows from the
mathematical experiments in this delivery.

## Source inventory and reuse

Counts include blank/comment lines in the delivered files; they are total file
lengths, not added lines. The comparison base is `eb3907c5`. N means new, M means
modified. Numerical JSON, immutable archives and test logs are evidence, not
additional implementations.

| Script | N/M | LOC | Responsibility, reason and existing reuse |
|---|---|---:|---|
| `extensions/tendon_family/manifest.py` | M | 238 | Register implemented operations and source dependencies in the existing registry. |
| `extensions/tendon_family/math_analysis.py` | M | 266 | Lazy legacy CasADi imports and provider-specific boundary identity; legacy equations retained. |
| `extensions/tendon_family/model_applicability.py` | M | 215 | Qualify supported local SoRoSim statics/linearization; retain shared assessment. |
| `extensions/tendon_family/signals.py` | M | 53 | Recognize SoRoSim's existing direct-tension observation channel; reuse signal expansion. |
| `extensions/tendon_family/sorosim_analysis.py` | N | 130 | Bind MATLAB work points and IFT to existing initializer, compiler, model contract and applicability. |
| `extensions/tendon_family/sorosim_codesign.py` | N | 81 | Candidate-local MATLAB solve/replay adapter and compact diagnostics; reuse task translation, compiler and Session. |
| `matlab/sorosim_control/sr_analysis.m` | N | 167 | MATLAB residual statics, work points, dynamic linearization and static IFT; reuse routing/dynamics/derivatives. |
| `matlab/sorosim_control/sr_codesign.m` | N | 134 | Full-task epigraph objective and sampled task constraints; reuse NMPC initialization/recovery and complete dynamics callbacks. |
| `matlab/sorosim_control/sr_diagnose.m` | M | 120 | Geometry/mechanics decomposition and warmed kernel instrumentation in existing diagnostic gateway. |
| `matlab/sorosim_control/sr_gateway.m` | M | 66 | Dispatch two numerical operations; existing model ownership and error handling. |
| `matlab/sorosim_control/sr_nmpc.m` | M | 175 | Expose full-task preparation to offline mathematics; reuse exact implicit roots and context. |
| `matlab/sorosim_control/sr_nmpc_callbacks.m` | M | 101 | Optionally expose already computed endpoint derivatives for explicit offline constraints. |
| `matlab/sorosim_control/sr_routing.m` | M | 111 | Shared transforms/Jacobians and diagnostic sample frames; same pinned recurrence, tendon chords and FD derivatives. |
| `tests/research/sorosim_s35_probe.py` | M | 373 | Persist each expensive successful result immediately; existing experiment and calculation unchanged. |
| `tests/research/sorosim_s36_probe.py` | N | 198 | Matched saved-state rod/cell probes and controlled substitutions; reuse S3.5 mappings, actual compiler and GVS. |
| `tests/research/test_sorosim_analysis.py` | N | 199 | Bounded real analysis driver, saved-result checks and preserved-result recovery; existing shared kernels. |
| `tests/research/test_sorosim_codesign.py` | N | 150 | Bounded genuine Harness driver, derivative/evidence and discrete topology compilation checks. |
| `tests/research/test_sorosim_contract.py` | M | 134 | Update locally supported analysis assertion; retain controller/default/scientific identity tests. |
| `tests/research/test_sorosim_performance.py` | N | 88 | Matched warmed old/new kernels and full callbacks in one Engine; no benchmarking framework. |
| `tests/research/test_sorosim_s35.py` | M | 112 | Compare historical source hashes to their frozen Git revision. |
| `tests/research/test_sorosim_s36.py` | N | 73 | Real geometry/force checks and synthetic interruption persistence test. |
| `tools/platform_registry.py` | M | 236 | Detect the installed MATLAB Engine on PYTHONPATH without import/startup when distribution metadata is absent. |
| `tools/research/analysis.py` | M | 447 | Provider dispatch and sensitivity evidence within existing typed analysis service. |
| `tools/research/contracts.py` | M | 325 | Versioned paired-candidate static sensitivity request; preserve legacy serialization. |
| `tools/research/execution_worker.py` | M | 44 | Atomically save successful numerical analysis returns before packaging. |
| `tools/research/mechanics.py` | M | 100 | Admit SoRoSim through existing reservations; export raw worker checkpoints through Store artifacts. |
| `tools/research/mechanics_worker.py` | M | 54 | Select actual provider before legacy imports; retain one worker/ledger/lifecycle. |
| `tools/research/task_constraints.py` | M | 121 | Static sensitivity applicability; preserve original task translator and constraint semantics. |
| `evidence/sorosim_performance/attempt01/reference/sr_routing.m` | N | 73 | Exact frozen baseline for reproducible comparisons; deliberately retained evidence copy, never a production owner. |

The proposed size ranges were guidance. Smaller adapters reuse existing contracts,
initialization, task translation, workers and persistence rather than restating
them. `sr_derivatives.m` needed no change: the measured saving occurs inside its
existing routing dependency. The two co-design files are justified because the
offline epigraph objective and hard sampled task inequalities differ from the
online NMPC soft cost; the dynamics and root solver are not duplicated. Remaining
intentional repetition is the analytical evaluation/checking of residuals in
independent verification and the pinned upstream kinematic recurrence in the
private optimized traversal. No second robot family, Store, Agent, or optimizer
framework was introduced.

The only new configuration files are `study_sorosim_s4b.json` and
`study_sorosim_s4b_recovery.json`. Both use the existing single-level family
defaults, existing family definition and sparse `control_sorosim.json` override;
neither contains a second robot definition. They separately retain the first
attempt's budget and the authorized remaining validation allowance.

The listed authoritative compiler, MJCF, GVS basis/projection/dynamics/CasADi/
trajectory/co-design files, shared mathematical kernels, search/budget/state,
task and control configurations and RL route have zero Git diff from the
starting revision. The narrow observation/registry preflight fixes above are
the only additional platform changes outside the proposed file list.

## Final Git delivery receipt

Starting SHA: `eb3907c5fb4710137be2af0f874e67eadbdf2f9e`.
Stage commits, in order: S3.6 `3f45b849`, S4-A `8f4c642b`, performance
`bb7b947f`, S4-B integration `f6fe2eac`, Harness fixes `5403348e`, preserved
failed study and recovery `dbcd057b`, runnable recovery study `602c66f3`, and
final validated evidence/report `a5347183`.

Final code, tests and numerical evidence SHA:
`a53471830b70d59ddde6eecb4732f2486cb329e9`.
Normal push succeeded, and `git ls-remote origin
refs/heads/feat/sorosim-matlab-nmpc` returned that exact SHA. `git status
--porcelain` was empty. This receipt is a subsequent documentation-only commit;
the final checkout/receipt SHA is obtained with `git rev-parse HEAD` and is also
reported in the delivery message, avoiding a self-referential commit hash.

All relevant source, tests, raw successful/failed numerical evidence and archives
are published. Ignored `runs/` directories retain local Store working databases
and temporary test artifacts; all scientific outcomes and costs are already
exported in committed immutable archives. No scientific artifact remains
unpublished. S5/S6, unrelaxed task success, optimizer convergence, global
optimality and closed-loop physical validation remain unclaimed as specified.
