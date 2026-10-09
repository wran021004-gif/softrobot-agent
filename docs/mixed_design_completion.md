# Bounded mixed robot design study, 2026-10-10

The reusable generator and mixed optimization interface are implemented. The real
study completed four development evaluations and one fresh exact confirmation.
All five were valid physical failures; **no feasible design was observed**.
The principal consumed the evidence and sealed STOP. This is a bounded search
outcome, not proof that the family has no feasible design.

The work starts from delivered Mainline 5 commit
`600fab815fc048fbe251b4594cc39411e2bf58ab`. Actual executions were frozen at
`8220d634fa369eec65691a8779f4f87357b6329d`, using
`hierarchical_coordinate_v1`. The post-study coordinate recovery repair is
`d67147190accfa7fb4283b2b58508eae989ffba6`; new requests default to
`hierarchical_coordinate_v1_1`. Completed evidence retains its original method
and dependency closure. The reused Python 3.11.16/Mainline 5 environment was
checked once and was not upgraded or rebuilt.

The public contracts are `research.design_optimization_problem@1.0.0` and
`research.design_optimization_result@1.0.0`. The registered
`search.design_mixed@1.0.0` tool, direct `tools.design_optimization.solve` service,
and native Strands `solve_design` share one numerical service. See the
[runbook](mixed_design_runbook.md), [free-count example](../examples/mixed_design/free_counts.json),
[fixed-count example](../examples/mixed_design/fixed_counts.json),
[typed contracts](../schemas/design_optimization.py), and
[generator](../extensions/tendon_family/generated_serial.py).

The first study fixes 0.27 m of flexible length: 0.16 m proximal and equal shares
of 0.11 m across the selected distal segments. Each topology has its own baseline
and individual ±5% bounds. The bounded-simplex parameterization respects those
bounds and the total simultaneously, deriving the last free length by subtraction.
Other public problems may explicitly provide different legal positive baselines.
Counts are genuine integers; fixed/equal-bound and inactive coordinates are absent
from the optimizer vector. Tendon/actuator totals are derived under one independent
actuator per tendon, and incompatible fixed totals are rejected.

Numerical initialization is frozen to `initial_state_pretension`: 0.2 N per tendon
in newly compiled channel order, repeated for initial horizon input guesses, with
warm states regenerated for each candidate. It is a numerical guess, not an
equilibrium claim. Physical initialization is separately recorded as named zero
joint positions and velocities. The first study does not search pretension.
Omission in the public contract defaults to fixed 0.2 N; search requires an
explicit continuous `pretension_n` declaration.

The task is target `[0.29, 0.035, 0.19]` m, mount `[0, 0, 0.15]` m, gravity
`[0, 0, -9.81]` m/s², seed 17, duration 0.35 s, control/sample period 0.01 s,
physics step 0.0005 s, and final holding window 0.05 s. Terminal/holding position
limits are 0.01 m; holding maximum speed is limited to 0.02 m/s. Each tendon has
an ideal 0–8 N input. Controller 11 inherits the existing NMPC algorithm:
structural-linear basis, horizon 10 with deadline truncation, tolerance 1e-6,
120 iterations, 30 CPU seconds, and 5/15-second feasible-return settings.
Material, section/routing scales 1.0, terminal speed weight 0.1, and mesh were fixed.

Problem identity is
`9f35ea5c0a8abb28acfab6d0f77cda320198de7547a733cbf87f53244547e976`.
Candidate suffixes below refer to `mixed-9f35ea5c0a-<suffix>`.
The signature is physical segments / proximal tendons / distal tendons. Decimal
values are abbreviated here; the [machine result](../evidence/mixed_design_20261010/result_summary.json)
retains exact returned floats, full geometry, routing, actuator mapping,
controller parameters, initialization, constraints, receipts, and source IDs.

| Candidate | Signature | Active lengths (m) | Terminal error (m) | Holding max error (m) | Holding max speed (m/s) |
|---|---|---|---:|---:|---:|
| 0, structural initialization | 3 / 3 / 3 | 0.16, 0.055, 0.055 | 0.100750068 | 0.201058068 | 3.218886401 |
| 1, structural initialization | 4 / 3 / 4 | 0.16, 0.036666667, 0.036666667, 0.036666667 | 0.173876978 | 0.209626622 | 2.496834754 |
| 2, feedback coordinate | 4 / 3 / 4 | 0.16275, 0.036208333, 0.035520833, 0.035520833 | 0.174043762 | 0.210066471 | 2.512747175 |
| 3, feedback coordinate | 4 / 3 / 4 | 0.15725, 0.037125, 0.0378125, 0.0378125 | 0.173837427 | 0.209287381 | 2.480060210 |
| `confirm-9f35ea5c0a` | 4 / 3 / 4 | Same as candidate 3 | 0.173837427 | 0.209287381 | 2.480060210 |

Every execution completed 35 applied updates with valid evaluation, holding
coverage, force bounds, and zero solver errors. Every one failed terminal position,
holding position, and holding speed. Every one also recorded 35 wall-clock
deadline misses; this is not evidence of real-time control performance.

Numerical feedback selected candidate 1 after structural coverage, then generated
positive and negative `length/0` proposals. The bounded parameterization changed
the other lengths to preserve the total. Candidate 2 did not improve the ranking;
candidate 3 became the best observed infeasible design under maximum normalized
ratio, then sum. Its maximum ratio is 124.003010476, dominated by holding speed.
The holding-weight axis was declared free over `[0.025, 0.1]` but remained at 0.05
in all executed proposals. These small ranking differences establish no statistical
superiority. Fewer actuators are preferred only among accepted designs; none qualified.

Candidate 3 has seven independent actuators, baseline material, pretension 0.2 N,
holding/terminal weights 0.05/0.1, modeled mass 0.071447713153 kg, zero-state
base-to-tip centerline length 0.298 m, and sum of individual tension limits 56 N.
The latter is neither net tip force nor power; motor mass is not established.
Modeled development masses for candidates 0–2 are 0.069811584271,
0.071811584271, and 0.072175455333 kg. Flexible length is 0.27 m throughout.

Confirmation has a new execution ID and fresh trajectories. Input except run ID,
dependency closure, and frozen commit match candidate 3 exactly. All three
physical metrics happened to match exactly in this pair. This supports the
reported failure observation, not a deterministic or statistical reproducibility
guarantee. Original principal decisions and raw provider responses are retained;
their wording “no replication” does not erase the fresh confirmation. No broader
repeatability campaign was performed.

The declared family has 2–4 physical flexible segments, independently 3/4 tendons
per group, and 6/7/8 one-to-one actuators. It uses archived executed-radius T0
profiles (Young moduli 7.2/5.4 MPa proximal/distal), actual asymmetric three-tendon
layouts, T1 four-tendon layouts, interpolated distal taper/routing at physical
positions, and an explicit 0.002 kg split-guide rule for added boundaries. Guide
clearance, mass/inertia, envelope, and once-owned holes are constructed explicitly.
Historical T0–T3 remain unchanged; generated designs receive new identities.
The mesh is always 24 bending cells: 12 proximal and 12 equally distributed distal.

| Signature | Declared | Constructed / physical compilation | Numerically prepared | Fully executed |
|---|---|---|---|---|
| 2 / 3 / 3 | Yes | Offline | Not demonstrated | No |
| 3 / 4 / 4 | Yes | Offline | Not demonstrated | No |
| 3 / 3 / 3 | Yes | Yes | Yes | One development |
| 4 / 3 / 4 | Yes | Yes | Yes | Three developments + one confirmation |
| Other supported combinations | Yes | Not checked in this study | Not demonstrated | No |

Three- and four-segment executed configurations have respectively 18/24 reduced
coordinates and 6/7 tendon inputs, with 48 backend positions from the fixed mesh.
Thus the study actually changed segment and tendon counts, generated a four-segment
robot beyond T0–T3, and executed feedback-generated continuous proposals. It did
not cover all declared structures, material choices, or the continuous domain.

Seven focused initial checks passed. After STOP, a read-only reproduction showed
that canonical JSON changed dictionary key order and therefore legacy v1's next
coordinate after interruption. The repair orders lengths by index and scalars by
name, rebuilding vectors from those names. Three affected checks passed in 12.233 s,
including interruption/restoration with no reevaluation. An offline replay of actual
stored feedback produced the same four uninterrupted physical proposals. No new
physical experiment or provider request was made for this repair. See
[repair evidence](../evidence/mixed_design_20261010/recovery_coordinate_observation.json)
and [all repairs](../evidence/mixed_design_20261010/implementation_repairs.json).
Substituted-backend checks are not physical validation.

Actual resource use is 7 provider sends, 7 conservative request reservations,
30 public tool operations, 1 public search operation, 0 public mathematical
operations, 4 development backends, 1 confirmation backend, 0 technical replacements,
175 applied NMPC updates, and 0 additional research-model workers. All request
outcomes are known; the ledger has no occupied unknown reservations. Provider
usage reports 292,954 prompt and 27,869 completion tokens (320,823 total);
monetary cost is unknown. Elapsed implementation/research/reporting time at export
was 7,545.416 s (2.10 hours), within the 16-hour ceiling. Upload time is recorded
separately in the local `runs/mixed-design-20261010/push_receipt.json` after push.
The final handoff supplies the verified remote branch SHA.

The one focused export check passed: 304 members, 33 execution evidence references,
5 sealed simulations, and 0 new backend launches. The 4,505,940-byte
[immutable archive](../evidence/mixed_design_20261010/immutable_artifacts.tar.gz)
has SHA-256 `b2641ebb180425ce013946d81896181e8efbb8fed121c3f5800df7ed35d8148e`.
[Archive manifest](../evidence/mixed_design_20261010/archive_manifest.json),
[Store manifest](../evidence/mixed_design_20261010/store_manifest.json), and
[integrity record](../evidence/mixed_design_20261010/delivery_integrity.json)
support retrieval without redundant expanded physics copies. Credentials are not
included in transport request bodies or framework configuration.

The requested historical stiff comparison is read-only and retains original
ownership. Scientific configuration and initialization match; both have 35 updates
and identical first commands. Applied commands first differ at 0.22 s, with 13
differing updates. Solver stopping counts and summed update times differ; this
does not identify random noise or a software bug. Original holding speeds
0.09248004936 and 0.21090377835 m/s both fail 0.02 m/s. See
[comparison](../evidence/mixed_design_20261010/historical_comparison.json) and
[original archive manifest](../evidence/research_mainline5_20261009/archive_manifest.json),
whose archive hash is `4a71016a3c40168b63b4642a09436a84d2e5c5700aa7d751c61cd385a9a6a987`.
The earlier six T2 developments and confirmation remain failures, and Mainline 4's
accepted T0 remains valid in its original scope. No completed activity was resumed
or rebound to the new generator.

Remaining limits include unexecuted structures and length/weight axes, one seed,
ideal tension without actuator travel/velocity or motor dynamics, sampled acceptance,
and confounded cross-topology changes in guides, dimensions, and force-limit sum.
The study establishes no global optimum, arbitrary graph/coupled actuation support,
robustness, or later-mainline completion.
