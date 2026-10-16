# Independent SoRoSim mathematical validation

2026-10-16, Windows / MATLAB R2024a. **The shared bending model corresponds within the declared finest-resolution tolerances.** Both cases and all finest-level derivative checks pass. This is numerical cross-validation of reduced mathematical models; it establishes neither physical accuracy nor complete robot task feasibility. No Harness, Agent tool, task evaluator, or existing kernel was changed.

## Reproduce and inspect

Repository starting tree: `eddbcb26a393c8919ac88886c0c1f7d280c374f9`. Reference: [GVSRobotics/SoRoSim at 24d573a3e864ffda87c42ee462a6ed620133cc7b](https://github.com/GVSRobotics/SoRoSim/tree/24d573a3e864ffda87c42ee462a6ed620133cc7b), specifically `Differentiable_SoRoSim`. The clean, detached upstream checkout is outside this repository at `%TEMP%\softrobot-sorosim-24d573a3`; it is disposable and can be recreated. Submodules are not initialized.

From the validation worktree:

```powershell
./validation/sorosim/run.ps1 `
  -Python D:\softrobot-agent\.pilot-env\Scripts\python.exe
```

The wrapper creates a new evidence directory, verifies kernel contents against the starting SHA, verifies the clean pinned reference, runs one segment, gates its correspondence and derivatives, then runs two segments. It refuses to overwrite previous evidence. For this machine's direct HTTPS route, pass `-DirectHttps` when cloning; the initial sandbox proxy route failed, while Git's OpenSSL HTTPS backend with a per-command empty proxy worked. No global Git settings were changed. MATLAB needs ordinary machine access: sandbox startup failed with `failed to load settings errors_warnings plugin`.

Actual results are in [evidence/run_20261016_01](evidence/run_20261016_01). The `gvs_*.json` and `matlab_*.json` files contain operating points, matrices, solver statuses, FD step/error records, perturbed solve statuses, and timings. The `comparison_*.json` files contain discrepancies at every resolution and refinement differences. [cases.json](cases.json) owns the physical values and numerical tolerances. [provenance.json](evidence/run_20261016_01/provenance.json) records source/binary hashes, reference identity, and evidence hashes. Run the six independent physical-invariant and corruption-detection tests without MATLAB:

```powershell
D:\softrobot-agent\.pilot-env\Scripts\python.exe `
  validation/sorosim/test_validation.py `
  --evidence validation/sorosim/evidence/run_20261016_01
```

MATLAB: `24.1.0.2537033 (R2024a)`, `PCWIN64`, Optimization Toolbox `24.1`; `fsolve`, `fmincon`, and `lsqnonlin` were actually exercised successfully. No `startup.m` resolved before path setup. Python: 3.11.16, NumPy 2.4.6, SciPy 1.17.1, CasADi 3.7.2. Existing local MATLAB, third-party, research, Desktop and Downloads locations were checked before fetching; no reusable SoRoSim work was found in those searches.

Upstream `startup.m` clears variables, resets paths, attempts an iDCOL build, and later deletes temporary GUI files. We audited it and used explicit paths plus empty object constructors instead. No contact calculation requires iDCOL here. No selected C++ MEX compiler was found; no build or installation was necessary. The supplied upstream `mexw64` binaries loaded successfully. Executed reference MEX files were `variable_expmap_g_mex`, `variable_expmap_gTg_mex`, `RigidJointKinematics_mex`, and `compute_dSTdqFC_Z4_mex`; soft Zanna kinematics also uses upstream MATLAB code. Expmap MEX versus MATLAB smoke errors were zero for poses and at most `2.08e-22` for tangent operators. This does not certify every bundled MEX or dynamic/contact path.

## Exact physical correspondence

| Property | Common definition / mapping |
|---|---|
| Units | m, kg, s, N, Pa; radians dimensionless. Curvature coefficients `q_g`: rad/m. |
| One segment | Length 0.20 m, circular solid radius 0.010 m; four bending coefficients. |
| Two segments | Welded serial rods: lengths `[0.12, 0.10]` m, radii `[0.010, 0.008]` m; eight coefficients. Identity connection transforms, no rigid connector mass. |
| Material | Homogeneous isotropic `E=1e6` Pa, density `1000` kg/m³. `I_y=I_z=pi*r^4/4`; `EI=0.007853981634` and `0.003216990877` N·m². SoRoSim Poisson ratio 0.49 sets shear modulus, which has no effect in the disabled modes. |
| Strain | `xi=[0,kappa_y,kappa_z,1,0,0]`: no torsion, extension or shear. Natural curvature zero; no damping in static calculations. |
| Basis | `kappa_a(u)=q_a0+(2u-1)q_a1`, `u=s/L`. Order per segment `[ky0,ky1,kz0,kz1]`; concatenate base to tip. GVS `first_order` and SoRoSim linear Legendre modes agree. |
| Coordinate scaling | Upstream rotational basis includes `1/L`: `q_s=D*q_g`, `D=diag(repeat_each_length_4_times)`. Virtual work requires `r_g=D'*r_s`, `A_g=D'*A_s*D`, `K_g=D'*K_s*D`. Generalized force unit N·m²; tangent stiffness unit N·m³. |
| Frames and boundaries | Right-handed robot-base frame; undeformed backbone along +x. Positive ky bends toward −z, positive kz toward +y. Fixed base, free tip, welded internal connection. SoRoSim body Jacobian becomes `[R*J_angular;R*J_linear]*D`, with linear velocity at the tip origin. This is not a spatial twist translated to the world origin. |
| Gravity | Uniform world/robot-base `[0,0,-9.81]` m/s²; distributed circular-section mass, no tip payload. |
| Inputs | Four frictionless straight spans from fixed base offsets to corresponding terminal-tip offsets: `+y,-y,+z,-z`, each 7 mm. Positive tension pulls endpoints together: `B=-dl/dq_g'`, `Q=B*u`. Probe tensions `[0.3,0.1,0.2,0.1]` N; configured limit 5 N/channel. Required Design actuator metadata is not executed. |

GVS poses use midpoint constant-strain exponentials; reference poses use order-4 Zanna integration. Both use Gauss spatial quadrature for gravity and elasticity. One-segment resolutions are `(GVS steps, Gauss nodes)=(24,5),(96,10),(192,20)`; two-segment resolutions are `(96,10),(192,20)`. SoRoSim adds zero-weight endpoints to its Gauss grid. All refinements retain the same physical model.

Straight, constant-curvature, and varying-curvature probes are retained. The one-segment variable probe is `[1.2,0.8,-0.7,0.4]` rad/m; the second rod's variable coefficients are `[-0.9,0.6,1.1,-0.5]`. Equilibrium starts from zero curvature with zero tendon tension under gravity. Small positive-tension equilibria are also solved for local sensitivity checks. There is no time integration or task horizon.

## Actual numerical results

The following discrepancies use the finest resolution. Fixed-probe force differences compare identical q; equilibrium differences compare each solver's own converged configuration.

| Quantity | One segment | Two segments |
|---|---:|---:|
| Variable-probe tip position norm, m | 1.600e-7 | 7.947e-8 |
| Variable-probe rotation Frobenius norm | 2.649e-7 | 8.227e-8 |
| Variable-probe gravity generalized force max, N·m² | 5.486e-8 | 2.469e-8 |
| Variable-probe force-map max, m² | 3.937e-9 | 1.503e-9 |
| Variable-probe equilibrium tangent max, N·m³ | 3.704e-10 | 1.397e-10 |
| Constitutive stiffness max, N·m³ | 2.168e-18 | 1.301e-18 |
| Equilibrium tip position norm, m | 1.161e-6 | 4.284e-7 |
| Equilibrium rotation Frobenius norm | 1.752e-6 | 5.160e-7 |
| Equilibrium curvature max, rad/m | 9.492e-5 | 7.463e-5 |
| Equilibrium tip/tension sensitivity max, m/N | 3.412e-7 | 2.363e-7 |

One-segment equilibrium tips: GVS `[0.1848574733,0,-0.0703210058]` m; SoRoSim `[0.1848570860,0,-0.0703221006]` m. Two-segment tips: GVS `[0.2036285204,0,-0.0772252026]` m; SoRoSim `[0.2036283940,0,-0.0772256119]` m. Full poses and coefficients are in raw JSON.

SciPy `hybr` and MATLAB `fsolve` returned status/exitflag 1 for all base equilibria. Finest residual infinity norms are `(GVS,SoRoSim)=(4.34e-19,1.04e-17)` and `(1.99e-17,2.91e-18)` N·m². Finest solver function counts are 10 and 6 respectively. Tangent condition numbers are about 3.29 and 9.80. These local solves do not prove uniqueness or global feasibility.

One-segment equilibrium tip discrepancies decrease `75.81 → 4.881 → 1.161` μm; curvature discrepancies decrease `0.006247 → 0.0004123 → 0.00009492` rad/m. The coarse level exceeds several finest acceptance thresholds; it is preserved, not treated as a pass. Refinement changes both pose integration and quadrature, so it does not isolate each error source. NumPy public-kernel checks agree with the repository CasADi adapter within the recorded small finite-difference errors.

SoRoSim's native continuously guided cable is **not the straight endpoint-span model**. At the variable probes their force maps differ by `8.100e-4` and `2.821e-4` m², orders of magnitude above the matched endpoint-map discrepancies. The reference map comparison therefore uses its analytical body Jacobian plus explicit endpoint virtual work. For the native guided-cable diagnostic, upstream positive force is extensional; tensile magnitude uses its negative. This sign convention does not remove the path difference. Motor dynamics, payout control, friction, routing contact, tendon elasticity, full Cosserat modes, transient dynamics, and dynamic derivatives are outside the established correspondence.

## Derivatives, tolerances and costs

Centered differences use `h=[1e-4,1e-5,1e-6]` rad/m, including straight and nonzero configurations. Available upstream analytical `Jacobian` and `Equilibrium` tangents are checked directly. GVS uses existing CasADi AD. Maximum finest-level errors across all declared steps/probes:

| Error | GVS one | SoRoSim one | GVS two | SoRoSim two |
|---|---:|---:|---:|---:|
| Tip Jacobian, angular/linear blocks | 3.49e-10 | 5.40e-10 | 1.06e-10 | 1.67e-9 |
| Static residual Jacobian, N·m³ | 2.41e-12 | 2.48e-11 | 2.78e-12 | 1.13e-11 |
| Endpoint length Jacobian, m² | 3.61e-10 | 1.07e-10 | 1.15e-10 | 2.67e-10 |
| Implicit tip/tension sensitivity, m/N | 6.52e-9 | 6.01e-9 | 5.78e-8 | 1.48e-7 |

The local sensitivity is `dq/du=-R_q\B`, `dp/du=J_p*dq/du` at `u=0`. Since `dB/dq*u=0` there, the upstream unactuated tangent suffices. It is checked with second-order forward differences at positive `h=[1e-3,1e-4]` N; all perturbed solves meet the `1e-10` N·m² residual bound. At nonzero baseline tension a chord-load derivative must be added; it has not been validated here.

Declared finest acceptance limits: position `2e-5` m, rotation Frobenius `2e-4`, curvature `2e-3` rad/m, generalized force `2e-6` N·m², residual tangent `2e-6` N·m³, stiffness `1e-12` N·m³. Tip-Jacobian comparison uses per-entry bounds of `2e-5` m in angular rows and `2e-5` m² in linear rows. FD limits are `2e-6` per tip-Jacobian block, `2e-7` N·m³ for residual tangents, `2e-6` m² for length Jacobians, and `2e-5` m/N for implicit sensitivity. Values were declared before numerical comparison and were not relaxed to pass.

| Measured cost | GVS one / two | SoRoSim one / two |
|---|---:|---:|
| Finest construction, s | 0.901 / 5.643 | 0.016 / 0.023 |
| Finest base equilibrium, s | 1.096 / 4.368 | 0.010 / 0.027 |
| Entire case checks, s | 49.85 / 266.37 | 1.87 / 3.90 |

These are local observations, excluding MATLAB launch/license/path setup, with different expression construction and solver evaluation behavior. The validation GVS callable computes all terms, including Jacobians, even during FD calls; this is not an optimized production benchmark or a general MATLAB-versus-CasADi speedup claim. Small-angle polynomial approximations in upstream exponentials also limit exact orthogonality/differential identities; observed probe rotation orthogonality defects remain below `1e-9` in the one-segment run.

## Recommendation and future interface

Keep SoRoSim as an offline mathematical reference first. Its analytical recursive static tangent, body Jacobian, and virtual-work force decomposition are useful for diagnosing unit/frame/basis errors, discretization dependence, near-singular equilibrium tangents, and misleading cable-model substitutions. For candidate search, validated implicit equilibrium sensitivities could support local refinement or sensitivity screening. Existing GVS already supplies AD; these results justify further independent checks, not replacing that backend. Higher Cosserat modes might diagnose omitted physics later, but then disagreement represents a changed model.

If pursued, the minimal interface should be an optional offline MATLAB batch request/result pair, outside active Harness execution. Request: exact source revisions, supported-physics flags, SI section/material/length data, normalized basis and coefficient order, base transforms, gravity, `q`, and explicit endpoint spans/tensions. Result: unsupported reasons or `T_tip`, body `J_qs`, `R`, `R_q`, `R_u`, coordinate transform `D`, solver status/residual, discretization, and timings. Consumers must transform forces and Jacobians through D and reject unsupported cable/contact/strain semantics. Start with a cached static residual/tangent and pose/Jacobian call, then independently validate any scalar task or design gradient before candidate search uses it. No such integration is included here.

No project-wide redistribution grant was found in the pinned tree/README. Generated C headers, including `Basic_functions/codegen/mex/compute_dSTdqFC_Z4/compute_dSTdqFC_Z4.h`, carry MathWorks Academic License restrictions tied to degree-granting institutions and excluding commercial, government, and other organizational use. Citation requests do not establish permission, and this validation does not determine the user's license eligibility. Upstream source and MEX binaries remain external. Clarify upstream and generated-code permissions before any implementation reuse or broader deployment. This branch contains only validation glue, original tests, documentation, and numerical evidence.

## V2: nonzero-tension and physical-design sensitivities

V2 preserves all V1 evidence and uses only its finest `(192,20)` settings.
The physical model, channel order, units and frames are exactly those above.
Two positive tensile baselines are `[0.3,0.1,0.2,0.1]` and
`[0.6,0.2,0.4,0.2]` N. Each base equilibrium starts from the same zero physical
curvature; each nearby input/design equilibrium starts from its own backend's
converged base. No global uniqueness or branch certification is asserted.

V2 deliberately reverses the V1 residual sign in **both** implementations:
`R=elastic-gravity-B(q)u`, `B=-dl/dq'`, `Ru=-B`.
Thus `Rq=A_passive-sum(u_i*dB_i/dq)`, `dqdu=-solve(Rq,Ru)`,
and `dpdu=J*dqdu`. The passive-only tangent is retained exclusively as an
incorrect-tangent diagnostic. GVS uses the existing native static CasADi graph
and AD. SoRoSim uses its upstream analytical passive tangent and tip Jacobian,
plus centered differences of the endpoint virtual-work force map at
`1e-5 rad/m`. This mixed derivative is **not fully analytical**.
Independent total-residual differences use `1e-4,1e-5,1e-6 rad/m` without
calling the numerical chord tangent. Input checks use centered, independently
resolved equilibria at `h=1e-3,3e-4,1e-4 N`, all within `[0,5] N`.

Design variables are first-segment length (m), homogeneous Young modulus (Pa,
all segments), and first-segment circular radius (m). Routing offsets stay
fixed in metres. Every changed physical design constructs a fresh linkage or
native GVS graph: stiffness, mass, quadrature, kinematics and `D(d)` are updated.
Existing `sv_model.m` already rebuilds all these quantities; it needs no new
design abstraction. Centered partials hold `q_g,u` fixed, with relative steps
`1e-4,1e-3`. Thus the numerical derivative includes the length dependence in
`D(d)'*r_s(D(d)*q_g,d)`. The tip derivative includes its explicit geometry term:
`Rd=partial R/partial d`, `pd=partial p/partial d`,
`dqdd=-solve(Rq,Rd)`, `dpdd=pd+J*dqdd`.
Both backends' design sensitivities are semi-analytical IFT calculations with
numerical physical-design partials. Predictions use that `1e-4` partial and
actual newly solved designs at both signs of `0.1%` and `1%` changes.

The authoritative V2 configuration and **pre-execution** bounds are in
`cases.json:v2`. Tangent FD requires both max error `2e-7 N*m^3` and relative
max error `2e-4`. Input/design centered derivative relative bounds are `0.005`;
input tip absolute bound is `2e-5 m/N`. Prediction errors must be below
`2e-6 m + 0.08*max(abs(actual displacement))`, with correct component signs
above `1e-8 m`. Local regularity requires successful solves, residual below
`1e-10 N*m^2`, condition below `1e8`, and linear-system relative residual below
`1e-10`. A relative q displacement guard of `0.25` rejects distant warm-start
solutions; passing it alone does not prove that no branch change occurred.

Run only V2 numerical experiments, followed by V1 evidence tests and V2 tests:

```powershell
./validation/sorosim/run.ps1 -V2 `
  -Python D:\softrobot-agent\.pilot-env\Scripts\python.exe `
  -Matlab 'C:\Program Files\MATLAB\R2024a\bin\matlab.exe'
```

The wrapper refuses an existing output directory, snapshots the frozen config,
gates the one-segment case before the two-segment case, and retains failures.
Repeated timing requests return only residual and total tangent, excluding
pose/sensitivity outputs. Full experimental time also includes independent
checks and model rebuilding; it must not be called a production benchmark.

V2 execution and observed results (2026-10-16, Asia/Shanghai):

[Run 02 evidence](evidence/run_v2_20261016_02), including
[summary](evidence/run_v2_20261016_02/summary.json), raw backend matrices,
both comparison reports, process timings and source/MEX provenance, passes all
frozen mathematical gates. Numerical source: `930be983153f1170f52e57dd0ea14357e29dc660`,
continuing branch starting SHA `c3bcbc2c00566c25de1d5f57950c07a795474ce3`.
The original GVS kernel identity remains `eddbcb26a393c8919ac88886c0c1f7d280c374f9`.
MATLAB is `24.1.0.2537033 (R2024a)`, Optimization Toolbox 24.1; Python is
3.11.16 at the specified `.pilot-env` executable, NumPy 2.4.6, SciPy 1.17.1,
CasADi 3.7.2. Upstream remains clean at the exact V1 pinned SHA; the same
external MEX route is used, with 198 upstream source/binary hashes retained.

All **248 solves** succeeded: eight base equilibria, 192 input perturbations,
and 48 physical-design perturbations across the two backends and structures.
The largest residual is `1.781e-11 N*m^2`; conditions range from 2.043 to 11.821.
No nonfinite result, failed numerical solve, tension-bound violation or local
q-displacement guard failure occurred. This does not prove global uniqueness.
The initial [Run 01 launcher failure](evidence/run_v2_20261016_01/run_status.json)
is preserved: PowerShell expanded a single `--v2` string as characters; no
numerical experiment ran. The corrected launcher used the fresh Run 02 folder.
Thirteen tests passed: all six V1 evidence tests plus seven V2 tests, including
deliberate sign, dimension, unit, nonfinite, omitted-term and failed-solve corruption.

Here `u1` is the original positive probe; `u2=2*u1`. Tips are SoRoSim results;
the last column is the norm of the GVS/SoRoSim tip difference.

| Structure/input | Tip [x,y,z], m | Base condition | Cross tip error, µm |
|---|---|---:|---:|
| One/u1 | [0.177443375, 0.004353518, -0.084024566] | 2.646 | 0.985 |
| One/u2 | [0.159904487, 0.012808944, -0.106532848] | 2.044 | 0.720 |
| Two/u1 | [0.175195504, 0.011749723, -0.113189823] | 11.431 | 0.692 |
| Two/u2 | [0.208809726, -0.019196154, 0.006139391] | 5.603 | 3.892 |

**Regularity is not stability.** At Two/u2 both zero-start solvers select a
saddle: the symmetrized conservative static-potential Hessian has two negative
eigenvalues, approximately `[-1.214e-4,-1.182e-4] N*m^3`. Its local IFT and
warm-start perturbations are valid mathematical checks, not evidence of stable
holding. No continuation connection between u1 and u2 is asserted. The other
three operating points have positive Hessians in this reduced subspace; all
design checks use u1. This is not a full-physics dynamic stability certificate.

Worst total-tangent FD errors, including every declared step and both inputs:
GVS one/two `1.139e-11 / 1.620e-11 N*m^3`; mixed SoRoSim one/two
`1.027e-11 / 1.868e-11 N*m^3`. Maximum relative error is `3.41e-8`.
SoRoSim symmetry defect is at most `5.57e-8` relative; AD defects are below
`1.34e-15`. Omitting the tendon state derivative produces **25.5–95.8%**
relative tangent error and **24.8–136.3%** tip/input-sensitivity error.
The diagnostic is rejected by the tests and is never used for design predictions.

`Rq` is 4×4 / 8×8, `Ru` and `dqdu` are 4×4 / 8×4, `J` is 3×4 / 3×8,
and `dpdu` is 3×4. Each design derivative has n×1 state and 3×1 tip dimensions.
Centered input re-solves agree within `2.04e-8 / 2.02e-6 m/N` for one/two;
maximum relative state/tip errors are `9.74e-6 / 8.76e-6`. Direct Ru FD error
is below `1.23e-12` relative; IFT linear-system residual is below `4.32e-16`.

The following SoRoSim tip design derivatives include the explicit geometry
partial. GVS agrees within `1.48e-5` relative. `dqdd`, `Rd`, `pd`, and all
actual perturbed q/p/status/cost values are retained in the raw evidence.

| Variable | Unit of derivative | One dp/dd [x,y,z] | Two dp/dd [x,y,z] |
|---|---|---|---|
| First length | m/m | [0.238661, 0.0414241, -1.53280] | [-0.376349, 0.0880330, -1.74060] |
| Common E | m/Pa | [4.64890e-8, -4.70784e-9, 7.93573e-8] | [1.35591e-7, -2.00049e-8, 1.28080e-7] |
| First radius | m/m | [11.4256, -2.10487, 19.3149] | [28.1217, -2.55905, 30.3962] |

Design-partial step sensitivity is at most `1.63e-6` relative. Centered,
independently re-solved design derivatives agree within `7.52e-4` relative,
including the 1% checks. All 48 design predictions have the correct signs
for meaningful components. At 0.1%, maximum error is `1.024 µm` (0.337% of
displacement); at 1%, `104.474 µm` (3.404%). Errors decrease with perturbation
size. Illustrative **+1%** changes below use u1; both negative changes and both
sizes are in the evidence. Each vector is [x,y,z] displacement in **µm**.

| Structure/variable | Predicted | Actually re-solved |
|---|---|---|
| One/length | [477.3, 82.8, -3065.6] | [439.6, 82.6, -3089.1] |
| One/E | [464.9, -47.1, 793.6] | [458.3, -46.6, 787.4] |
| One/radius | [1142.6, -210.5, 1931.5] | [1103.5, -203.8, 1896.1] |
| Two/length | [-451.6, 105.6, -2088.7] | [-472.7, 104.8, -2091.2] |
| Two/E | [1355.9, -200.0, 1280.8] | [1328.2, -197.6, 1273.3] |
| Two/radius | [2812.2, -255.9, 3039.6] | [2712.3, -251.8, 3007.3] |

At the **same u1 pose**, endpoint-chord versus native-guided force maps differ
by `2.154e-3 / 2.563e-3 m^2` for one/two. Their different path assumptions
explain this diagnostic; it is not a matched-model error. The IFT equations
apply to either smooth residual, but each needs its own complete tangent.
V2 does not validate guided-cable equilibrium sensitivities, routing-offset
gradients, contact, internal routing optimization or cable active-set derivatives.

Actual timings below are seconds; repeated residual/tangent calls return
equivalent requested outputs (median of ten calls across two base poses).

| Measured operation | GVS one | SoRoSim one | GVS two | SoRoSim two |
|---|---:|---:|---:|---:|
| Initial model/graph construction | 1.881 | 0.154 | 11.896 | 0.168 |
| Repeated residual + full tangent | 0.09608 | 0.00485 | 0.39667 | 0.01413 |
| u1 equilibrium solve, including cold solver effects | 1.267 | 0.247 | 6.038 | 0.358 |
| u2 equilibrium solve | 1.383 | 0.0357 | 6.065 | 0.0989 |
| Input IFT + omission diagnostic, warm u2 | 0.000056 | 0.000088 | 0.000070 | 0.000156 |
| Design fixed-q partial evaluations (12 calls) | 2.057 | 0.0569 | 8.260 | 0.180 |
| Design partial differences + IFT (six calculations) | 0.00643 | 0.00224 | 0.00031 | 0.00232 |
| 18 changed-design model/graph builds | 38.113 | 0.109 | 275.980 | 0.148 |
| 48 input-perturbation equilibrium solves | 43.210 | 0.649 | 166.144 | 1.933 |
| 12 design-perturbation equilibrium solves | 10.690 | 0.176 | 44.756 | 0.510 |
| Entire mathematical verification batch | 121.026 | 2.158 | 629.746 | 5.206 |

MATLAB process launch to function entry costs `6.837 / 6.596 s`; environment
setup `1.515 / 1.460 s`; serialization/shutdown and remaining wrapper overhead
`2.549 / 2.530 s`; complete MATLAB processes `13.059 / 15.791 s`.
These are single-workstation observations, with no host isolation, differing
integration algorithms, AD versus mixed tangents, MATLAB cold JIT and separate
SciPy residual/Jacobian callbacks. They establish neither general MATLAB
superiority nor guaranteed search speedup. The larger verification totals
include deliberately redundant independent checks, not just the requested derivative.

Changed file responsibilities and source line counts, relative to the initial
`c3bcbc2c` tree (numerical evidence excluded):

| File | Before → after LOC | Responsibility |
|---|---:|---|
| cases.json | 43 → 79 | Frozen physical cases, steps, units and acceptance limits |
| run_gvs.py | 225 → 334 | Existing static AD graph, loaded solves, design/input IFT probes |
| sv_terms.m | 43 → 64 | Common residual sign, endpoint force and mixed total tangent |
| sv_v2.m | 0 → 108 | Bounded MATLAB solves, rebuilt design partials and timings |
| sv_run.m | 115 → 128 | Existing entrypoint, version dispatch, environment/source identity |
| sv_fd.m | 8 → 8 | Reused centered-difference helper, explicit caller units |
| compare.py | 129 → 253 | Recomputed mathematical, prediction and corruption gates |
| test_validation.py | 85 → 151 | V1 compatibility and seven focused V2 tests |
| run.ps1 | 49 → 61 | One launch path, config snapshot, timings, retained failure status |
| setup_reference.ps1 | 36 → 34 | Verify existing pinned checkout without rewriting it |
| provenance.py | 57 → 57 | Kernel and validation source identities plus file/binary hashes |
| README.md | 103 → 313 | Preserved V1 report plus V2 methods, findings and costs |

V2 is **complete for the declared local static scope**, including the explicitly
classified saddle. No new numerical kernel, Harness/controller integration,
optimizer, NMPC experiment, RL training, provider request, package installation
or upstream source modification was performed. No upstream code/binaries were
vendored; the V1 licensing restrictions and unresolved redistribution/enterprise
eligibility remain unchanged. Successful local execution establishes no license grant.

**Recommendation C:** reproduce the validated complete static IFT calculation
and rebuilt physical-design partials using the existing GVS/CasADi toolchain,
without a permanent MATLAB runtime dependency. The derivatives predict real
local parameter changes and GVS already supplies the required AD tangent.
SoRoSim's measured static cost is attractive, but these examples establish no
unique missing design-derivative capability; licensing and runtime deployment
remain unresolved. Future structure/control search can use these sensitivities
for bounded local screening only with conditioning and equilibrium-class checks,
followed by actual changed-design evaluation. No integration or merge is made here.
