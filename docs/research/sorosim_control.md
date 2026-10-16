# SoRoSim + MATLAB NMPC delivery

Starting commit: `5dd325eb2c179c01d13aba50074b15db64a0cfdb`.
Branch: `feat/sorosim-matlab-nmpc`. Independent validation reference:
`e1ae76331d37ca1258803def6f07219f00aa5352`. External upstream:
`GVSRobotics/SoRoSim@24d573a3e864ffda87c42ee462a6ed620133cc7b`.

## S0

The new model/controller have independent version 1.0.0 registrations. The
predictive model is distinct from the unchanged `backend.family_mujoco@1.1.0`
execution model. The default remains GVS/CasADi/IPOPT. The sparse
`control_sorosim.json` inherits scientific fields from `control.json`; it does
not contain robot dimensions, goals, horizons, weights or force limits.

Three contract tests pass, including regenerated actual final M3-D geometry,
candidate-builder admission, default invariance and explicit midpoint rejection.
Model conversion is preparatory at S0; no robot numerical capability is advertised
until measured. S4 operations are outside this delivery.

`evidence/sorosim_control/s0.json` records actual MATLAB Engine execution from
Python 3.11, MATLAB R2024a, Optimization Toolbox 24.1, a successful SQP smoke solve,
external source/binary hashes and measured session times. MATLAB's already built
Engine package is used via PYTHONPATH; no dependency was installed or rebuilt.
The `.pilot-env` lacks an actual MuJoCo installation, so robot checks use the
verified `.mainline5-env`. Initial namespace-only detection was insufficient.
Sandbox Engine startup failed before any computation; ordinary machine access
succeeded. No shared desktop was attached and no upstream startup.m ran.

Authoritative physical inputs, evaluators, budgets and historical records are
unchanged. No live Agent, provider, RL or full task campaign has been launched.

## S1

The full regenerated M3-D model has five links, including the guide, connector
and payload with their actual COMs and full inertia tensors. Custom SoRoSim
section matrices preserve the ellipse/rectangle axes and interpolated orientation.
The custom structural nodal basis has rank 12. `q_s=T*q_g` uses six coefficients
per segment here, derived from the resolved basis. Actual geometric curvature is
independent of natural curvature; natural curvature contributes an elastic load.
The gateway caches the constructed candidate. Native actuation is disabled.

The frozen one/two-segment V1/V2 scripts and cases are selectively imported without
modification; `validation/sorosim/source.json` preserves their commit and hashes.
Only fixed loaded probes ran, not the historical 248 equilibrium solves.
Production has no dependency on these validation files.

Real results in `evidence/sorosim_control/s1.json` pass the predeclared bounds:
M3-D max length error `5.949e-8 m`, tip-position component error `1.243e-7 m`,
force-map error `4.630e-8 m^2`. Independent MATLAB differences give routing
Jacobian error `2.252e-10 m^2`, tip Jacobian error `5.965e-9 m^2`, and nonzero-input
routing-tangent error `4.570e-13 N*m^3`. Frozen reference force maps agree to
`1.302e-18 m^2` and loaded tangents to `1.566e-13 N*m^3`.
GVS uses 192 midpoint steps; both sides use Gauss integration per structural
interval. All original probes, matrices, tolerance definitions and times remain
in evidence. Five focused contract/physics tests pass. An initial test assertion
compared tuple/list containers for equal inertias; array comparison corrected
that test without changing mathematics or thresholds. Its numerical attempt is
preserved as `s1_attempt01.json`.

Unsupported external forces, off-chain components, interior component connections
and eccentric distributed sections are rejected explicitly. This bounded adapter
does not claim arbitrary-robot coverage, contact or S4 analysis support.

## S2

The complete convention is `M*qdd+c+elastic+viscous-gravity-B*u=0`.
`DAEJacobians` supplies recursive inverse dynamics, mass and analytical passive
state/rate derivatives. The custom chord state derivative and tip-velocity/q
derivative use declared MATLAB-local centered differences, not analytical claims.
Acceleration and input derivatives are exactly M and -B. The model is built once;
adjacent derivative outputs share the same recursive evaluation and routing data.
Full force decomposition additionally uses the validated upstream Equilibrium
recursion for gravity. The pinned `GeneralizedExternalForce` is stale: it references
the nonexistent `SorosimLink.lp` field. No upstream file was patched. Optimizer
callbacks omit the optional force decomposition pass.
The pin's standalone GeneralizedMassMatrix/GeneralizedCoriolisMatrix methods
also reference this obsolete field; their required terms instead come from the
current, independently checked recursive DAE interface.

Six operating points cover zero state, curvature, velocity, acceleration, tension
and their combination. The initial 96-step reference passed force/residual checks
but failed the independently declared forward-acceleration absolute bound:
546.950 rad/(m*s^2), relative 0.000525, with mass condition 173759. The failed
comparison is preserved. A term-isolation refinement using existing NumPy kernels
localized the discrepancy to geometry/mass integration; its partial substitutions
are explicitly diagnostic, not acceptance evidence. The complete matched CasADi
comparison was rerun at the supported 200-step resolution, keeping every physical
quantity, basis, quadrature and tolerance unchanged. Final results are in
`evidence/sorosim_control/s2.json`; earlier attempts remain available.

S4 static-analysis/linearization requests now identify the SoRoSim predictor and
return unsupported instead of silently executing the old CasADi analysis. MuJoCo
continues to declare its original serial-cell execution model.

Final S2 maxima: mass error `9.745e-11 kg*m^4`, elastic error `4.337e-19 N*m^2`,
viscous error `1.695e-21 N*m^2`, gravity error `6.315e-8 N*m^2`, tendon force error
`3.217e-8 N*m^2`, complete residual error `6.439e-8 N*m^2`, and tip velocity error
`1.176e-8 m/s`. Forward acceleration error is `81.465 rad/(m*s^2)` absolute and
`7.823e-5` relative at this stiff, non-equilibrium curved probe; this is not a
uniform acceleration-accuracy guarantee. Independent residual derivative errors
are q `3.123e-11`, qd `2.051e-14`, qdd `2.066e-14`, and u `1.572e-15` in their
respective SI derivative units. Tip velocity derivative errors are below
`2.471e-12` for q and `6.086e-15` for qd. A combined derivative call took
`0.0327 s`; warmed force-decomposition calls were approximately `0.02–0.04 s`.
The refined independent CasADi reference graph took `131.156 s` to construct.

## S3

The MATLAB SQP problem has 304 variables and 264 equalities at the initial full
10-interval horizon: fixed measured initial state, implicit Euler defects with
the original `/10` and `/0.001` normalization, exact physical reconstruction,
state/input scaling and the original tracking, terminal, rate, input, variation,
terminal-speed and task-scheduled holding-speed costs. The original deadline
horizon behavior is retained. Unsupported midpoint integration is rejected.

Objective/constraint gradients are supplied in MATLAB's required layout. A shared
callback cache reuses adjacent dynamics/routing outputs; callbacks never call
Python. Derivative checks cover the initial plan and a declared late-task point
whose prediction spans the original holding window. Maximum directional relative
errors are objective `2.282e-6`, constraints `8.347e-10`; declared bounds remain
`2e-4`. The initial input-only difference step lost precision in a small quadratic
penalty; using a resolvable step for that exactly quadratic direction fixed the
check without changing its bounds. Failed callback evidence remains available.

The real isolated solve has exit flag 1, 69 iterations, objective
`874.658038743 -> 2.696707993`, independently checked scaled violation
`2.681e-13`, and first command `[0,2.241321773,8,8] N`. Independent Python cost
summation agrees to floating-point precision. SQP time was `38.178 s`, warm-state
regeneration `6.274 s`, validation `0.864 s`. Tiny negative solver roundoff
(`3.031e-22 N`) is projected onto exact tension bounds and the entire plan is
revalidated afterward. Initialization alone is never selected as a fallback.

Three real MuJoCo updates reused one MATLAB Engine process and one model:

| Time (s) | Exit flag | Iterations | Scaled violation | Complete update (s) |
|---:|---:|---:|---:|---:|
| 0.00 | 1 | 69 | 2.681e-13 | 45.163 |
| 0.01 | 1 | 105 | 1.206e-12 | 66.052 |
| 0.02 | 0 | 120 | 3.693e-13 | 74.028 |

All three commands were feasible and applied. Exit flag 0 is explicitly a feasible
iteration-limit plan, not convergence. The shifted controls were regenerated from
changed measured states. Bounded previous-tension response and the original
consecutive-failure stop rule pass an explicitly labeled isolated software fault
test. Returned-iterate reintegration recovery is implemented with independent
checking, but was not triggered in these real solves; its numerical success is
not claimed.

First-step tip discrepancies against independent MuJoCo execution were
`3.190,0.886,3.930 mm`; velocity-vector discrepancies were
`0.1641,0.1425,0.1023 m/s`. These are observed prediction errors, not task-bound
changes. One Engine startup cost `6.571 s`, construction `0.174 s`, per-update
Python/Engine transfer+dispatch+serialization overhead `0.0050,0.0572,0.0510 s`.
Engine quit call took `0.0028 s`; the entire contained worker took `194.957 s`.
The parent confirmed worker termination. These costs do not establish 100 Hz
operation.

The execution stopped after three updates through an explicit engineering bound
on the existing backend, leaving the original `0.35 s` task and evaluation grid
unchanged. Both original evaluator and shared acceptance composition returned
**incomplete**, with task success **null**. No full task or 35-update comparison
was run. Raw observations, commands, XML, task evaluation, common report and
acceptance are retained under `evidence/sorosim_control/` and the existing Store.
Facts, existing ScopedMathematicalClaim conclusions, and empty interpretation
lists remain distinct. The evidence reader exposes these solver-neutral facts.

The first return-packaging attempt expanded a cell field into a MATLAB struct
array; it is preserved as an execution error, not a successful measured result.
The short-loop log also exposed a Windows `_elementtree` DLL import exception
after MATLAB Engine changed DLL search paths. The run still completed and passed.
The controller now preloads the existing XML compiler before Engine startup. A
separate zero-update native check confirms the accelerator loads and generates
byte-identical XML. Machine-specific original log/Store bytes remain locally in
`runs/`; the committed log redacts personal paths and records the original hash.

## Selection and reproduction

Select the new profile with the existing resolver:

```python
spec = resolve('configs/research/study_m3d_agent_feedback.json',
               backend_profile='sorosim_matlab_v1')
```

This selects `control_sorosim.json`; the original study file and default resolution
remain unchanged. The backend stays `backend.family_mujoco@1.1.0` with its existing
serial-cell dynamics identity. Predictor identity is `model.sorosim_gvs@1.0.0`;
controller identity is `controller.sorosim_matlab_nmpc@1.0.0`. Unknown profiles,
unsupported physics and unimplemented S4 analysis fail explicitly. No second
robot configuration, Harness, Store implementation, budget or research pipeline
was introduced.

From the isolated worktree, these exact PowerShell commands use already verified
local dependencies. MATLAB needs ordinary machine access on this installation.
The external checkout must remain clean at the pinned SHA; do not run startup.m.

```powershell
Set-Location D:/softrobot-agent/.worktrees/sorosim-matlab-nmpc
$p='D:/softrobot-agent/.mainline5-env/Scripts/python.exe'
$env:PYTHONPATH='.;tests/research;C:/Program Files/MATLAB/R2024a/extern/engines/python/build/lib'
$env:SOROSIM_ROOT="$env:TEMP/softrobot-sorosim-24d573a3"
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'

# Read/recheck committed numerical evidence and software contracts; no new solves.
& $p -m unittest test_sorosim_contract test_sorosim_physics test_sorosim_nmpc test_sorosim_integration -v

# Fresh bounded numerical reproduction; every destination must be new.
$out='runs/sorosim-reproduce-'+[guid]::NewGuid().ToString('N')
New-Item -ItemType Directory $out | Out-Null
& $p -c "from test_sorosim_contract import environment_evidence; environment_evidence('$out/s0.json')"
& $p -c "from test_sorosim_physics import run_s1,verify_s1; verify_s1(run_s1('$out/s1.json'))"
& $p -c "from test_sorosim_physics import run_s2,verify_s2; verify_s2(run_s2('$out/s2.json'))"
& $p -c "from test_sorosim_nmpc import run_update,verify_callbacks; verify_callbacks(run_update('$out/callbacks.json',True))"
& $p -c "from test_sorosim_nmpc import run_update,verify_solution; verify_solution(run_update('$out/update.json',False))"
& $p -c "from test_sorosim_integration import launch,verify; verify(launch('$out/loop.json',3))"
```

S1 reproduces two fixed frozen V1/V2 probes plus actual M3-D probes; S2 uses the
same design and 200-step independent reference. S3 retains the original scientific
horizon. The commands make no provider requests, train no RL model, and launch
no full task campaign. Dependencies were not rebuilt or installed. Final focused
regression includes the five original M3-D feedback tests and the unchanged
historical acceptance-contract test, with the documented single-thread environment.

All **21 focused tests pass** (15 new backend tests and six retained baseline
tests). The baseline feedback test initially ran without its required thread
environment and was correctly rejected before execution; rerunning with the
documented environment passed. The final suite took `16.994 s` and did not run
additional numerical solves. A Git-content proof confirms 17 authoritative
compiler, baseline kernel, evaluator, budget and physical/configuration files are
unchanged from the authorized base. The backend source identity and external
dependency digest are in `evidence/sorosim_control/source_freeze.json` (56 relevant
source/configuration files; no CasADi/IPOPT implementation list reuse).

[Complete changed-file inventory, actual line counts and duplication audit](sorosim_control_inventory.md)
includes source, tests, configuration, frozen regressions and numerical artifacts.

## Remaining work

- S4: migrate static operating-point construction, controllability, broad
  sensitivity/trajectory analysis and co-design tools, with their own evidence
  contracts and validation. They are not silently routed to CasADi here.
- S5: separately authorize and execute the full original 35-update MuJoCo task;
  measure terminal and holding-window joint acceptance, robustness and repetition.
- S6: separately authorize a matched formal comparison and live Agent research
  integration. This delivery makes no efficiency or research-quality comparison.
