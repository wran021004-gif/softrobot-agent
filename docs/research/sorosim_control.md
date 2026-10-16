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
