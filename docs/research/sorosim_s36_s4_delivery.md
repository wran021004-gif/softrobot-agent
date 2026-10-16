# SoRoSim S3.6 and S4 delivery

Starting and fetched remote SHA: `eb3907c5fb4710137be2af0f874e67eadbdf2f9e`.
Its ancestry was checked before changes. Development remains on
`feat/sorosim-matlab-nmpc`. The authoritative design, physical compiler, task,
acceptance thresholds, default controller and RL route are unchanged.

## Stage status

| Stage | Implemented and executed | Acceptance | Source commit |
|---|---|---|---|
| S3.6 | Three matched static states, 50 frames each, separated forces, additive link inertia/gravity, controlled geometry substitutions, immediate replay persistence | Passed within bounded diagnostic scope | Recorded after stage commit |
| S4-A | Pending | Not complete | Pending |
| Performance | Pending | Not complete | Pending |
| S4-B | Pending | Not complete | Pending |

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
# New bounded static calculations; new destination required, normal machine access.
$out='runs/sorosim-s36-'+[guid]::NewGuid().ToString('N')
& $p tests/research/sorosim_s36_probe.py $out
& $p tests/research/sorosim_s36_probe.py $out --isolate
# MATLAB release, toolbox, binaries and actual startup recorded in $out/environment.json.
```

## Remaining milestones

S5 complete MuJoCo closed-loop physical task evaluation and S6 formal backend /
Agent control-method comparison are not authorized and are **not completed**.
S4 and the final inventory/Git verification will be recorded as work proceeds.
