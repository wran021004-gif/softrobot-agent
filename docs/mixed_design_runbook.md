# Bounded mixed robot design optimization v1

`research.design_optimization_problem@1.0.0` and
`research.design_optimization_result@1.0.0` are the public contracts.
`search.design_mixed@1.0.0` is a registered native tool. Direct Python callers
use `tools.design_optimization.solve(problem, authorized_host)`. Strands and
direct calls share the numerical solver and receipt-backed execution service.

The rule-generated `serial_two_group_v1` family supports 2–4 physical flexible
segments, a proximal and a distal tendon group, independently 3 or 4 tendons
per group, and one actuator per tendon. Total tendon and actuator counts are
derived (6, 7, 8). Requested fixed totals filter compatible groups; incompatible
combinations fail validation. Coupled actuation and arbitrary graphs are excluded.
Historical T0–T3 and their original version meanings remain intact. New candidates
use `candidate.family@3.0.0` and `controller.gvs_nmpc@11.0.0`, inheriting the
V7 NMPC algorithm and deadline stopping rules.

The first study fixes total flexible length at 0.27 m. Default baselines are:

| Physical segments | Length baseline (m) | Numerical cells |
|---|---|---|
| 2 | 0.16, 0.11 | 12, 12 |
| 3 | 0.16, 0.055, 0.055 | 12, 6, 6 |
| 4 | 0.16, 0.11/3, 0.11/3, 0.11/3 | 12, 4, 4, 4 |

Each component is bounded by its topology-local baseline ±5%. A sequential
bounded-simplex parameterization maintains the sum and individual bounds at
every proposal; the final free length is derived by subtraction. Fixed and
equal-bound coordinates are absent from the optimizer vector. Arrays follow
the selected topology, and inactive coordinates never enter scientific identity.
Other public Python requests can explicitly supply lawful `baseline_by_count`
vectors and corresponding bounds/fixed coordinates. The authorized first live
activity freezes the table above. Rigid connector/tip offsets are additional
to flexible length and are separately reported as zero-state base-to-tip length.

The fixed source recipe uses the archived executed-radius T0 proximal/distal
profiles: Young moduli 7.2/5.4 MPa, original density/viscosity, sections and
natural curvature. This “baseline” is that recipe, not a newly measured material.
Three-tendon angles preserve the actual archived asymmetric layouts. Four-tendon
groups use T1's explicit quadrature layouts. Distal taper, section orientation,
and routing interpolate archived physical-position profiles. Each added boundary
uses the existing split-guide mass (0.002 kg), inertia, envelope, and hole rule.
Shared entrance guide holes are generated once. Absolute scales always start
from the source recipe, never a prior candidate. Mesh is frozen at 24 cells.

Numerical initialization is explicitly `initial_state_pretension`: **0.2 N per
tendon**, ordered by the newly compiled tendon channels, bounded by 0–8 N.
The projected measured initial state starts at zero; the nominal input and all
initial horizon tension guesses repeat that vector. Candidate dynamics regenerate
every warm state before optimization. These are numerical guesses, not equilibrium
solutions or physical state claims. Physical initial position and velocity are
recorded separately as zero for every generated joint. No historical tension
guess is selected by matching names. Pretension is fixed in this first problem;
the public API only searches it when a caller explicitly declares a continuous
`pretension_n` variable. Omission defaults to fixed 0.2 N.

The outer solver enumerates legal integer/categorical structures. Declared
initial structures are coverage points. Subsequent inner coordinate proposals
use actual feasibility/normalized constraint feedback to choose the incumbent
and active continuous vector. Ranking is feasible first; infeasible designs use
maximum normalized metric ratio then sum. Fewer actuators are preferred among
accepted designs. The reported sum of tension limits is neither net tip force
nor power; ideal tension establishes no motor mass. Full reach-and-hold evaluation
is decisive. Cached points are no new experiment or independent confirmation.

Examples: `examples/mixed_design/free_counts.json` and `fixed_counts.json`.
Set `lengths.free=false` and fix both weights to evaluate one specified design.

```powershell
$studyPython = 'D:\softrobot-agent\.mainline5-env\Scripts\python.exe'
& $studyPython -m tools.research_mixed_design prepare
# Freeze and commit implementation, examples and scientific settings first.
& $studyPython -m tools.research_mixed_design bind
& $studyPython -m tools.research_mixed_design run
& $studyPython -m tools.research_mixed_design status
& $studyPython -m tools.research_mixed_design recover
& $studyPython -m tools.research_mixed_design export
```

`direct --problem <json>` invokes the same registered service in the authorized
activity without a model. It must not be run alongside `run`. The live principal
owns interpretation, optional justified refinement, exact confirmation nomination,
and STOP. Only STOP follows confirmation; failures remain visible.

One Store/grant/clock belongs to `runs/mixed-design-20261010`. Ceilings are 60
actual provider sends, 1024 public operations, 48 search/math operations, 8
development backends, 2 confirmations, 2 identified technical replacements,
12 backends total, zero other workers, and 16 hours including implementation.
The final 30 minutes are reserved. Credentials load only for live dispatch through
the existing loader, and are never archived. The reused accounted DeepSeek
transport and Strands harness own request reservations, context, original
responses, sealed-response replay, and persistent framework checkpoints.

Pending proposals and optimizer state are committed before execution. Recovery
reuses `complete_execution` receipts and never repeats a sealed simulation.
Unknown backend/provider outcomes retain reservations and block blind replay.
Use original Store and framework sessions for recovery; exported archives are
evidence, not a fresh grant. Historical roots/owners are linked explicitly;
historical evidence is never rebound to the new generator for exact execution reuse.

The export keeps exact requests/responses, search states, solver/controller
inputs, trajectories, receipts, and checkpoints once in `immutable_artifacts.tar.gz`.
`store_manifest.json` maps content IDs to archive members;
`archive_manifest.json` provides byte hashes. Expanded physics folders are omitted
because their exact file blobs already live in the content-addressed Store.
`delivery_integrity.json` records one focused integrity check. This bounded
demonstration establishes no global optimum, statistical superiority, robustness,
real-time control, arbitrary topology support, or completion of later mainlines.
