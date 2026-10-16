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
