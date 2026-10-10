# SoRoMoX bounded pilot completion, 2026-10-10

**Decision: defer adoption.** The minimal native GVS mapping does not preserve
this robot's structural-linear strain field and section inertia. The permitted
model-incompatibility stop rule was reached before trajectory optimization.
The delivered interface resolves and checks the robot, retains numerical
evidence, and returns typed solve/replay admission rejections. It does not
deliver a runnable trajectory NLP or a physical-equivalence claim.

The fetched remote base matched `2d13dfcc6395e09b53f6241dac3cae24ee69abb8` on
`feat/mixed-design-optimization`, four ahead and zero behind
`600fab815fc048fbe251b4594cc39411e2bf58ab`. An isolated worktree and branch
`feat/soromox-codesign-pilot` were created. Unrelated local changes and the
accepted Mainline 5 environment were preserved. Historical mixed-design STOP
was never reopened, and its offline two-segment design was never described as
an executed successful baseline.

Implementation and frozen specifications were committed at
`156b3de72743c6e014f5545e8f15b90240213185` before scientific dispatch.
The machine [freeze record](../evidence/soromox_pilot_20261010/implementation_freeze.json)
is authoritative for the full SHA and dependency closure. A reporting repair
at `1811aa6c18deeef892db3053a737b00816d12a7b` separated a successful source
mapping check from a failed native probe and wrapped an empty log in valid
JSON. The original result and incorrectly JSON-labelled empty log are retained
unchanged in the archive. The exact dependency migration, unchanged science,
and zero repeated numerical checks are recorded in the
[repair receipt](../evidence/soromox_pilot_20261010/reporting_repair.json).
The native follow-up used that second commit. `bb4c2d42` corrected transport
cleanup and exported Strands checkpoints; no extra provider send was made.

`generated_serial.dimensions(...)` and the current interfaces resolved 12
curvature coordinates, 24 reduced state entries, 48 physical positions and
velocities, and six one-to-one tendon/actuator channels. The explicit prescribed
zero joint state projects to zero reduced position and rate. The 0.2 N input
vector remains a numerical guess and is not equilibrium or initial physical
tension. Full orders, geometry, guide holes, task, initializer and controller
11 recipe are in the immutable snapshot and
[admission evidence](../evidence/soromox_pilot_20261010/admission.json).

The native factory actually rejects `structural_linear` with `KeyError`. Its
supported basis list contains monomial, Legendre, Chebyshev, Fourier, Gaussian
and IMQ. Interpolating the three source nodal values with quadratic Legendre
coordinates agrees at knots but differs between them: at normalized arc 0.25,
the middle hat coefficient is 0.5 versus 0.75. The 0.25 discrepancy is a strain
field change, not a harmless coordinate transformation. This is consistent
with the [native GVS basis API](https://tud-phi.github.io/soromox/api/systems/gvs/gvs/).

The source proximal ellipse is rotated 0.35 rad; its bending area tensor has
off-diagonal entry −5.9344e−10 m⁴. The tapered distal rectangle rotates from
−0.25 to +0.15 rad, with changing off-diagonal entries. The installed native
section interface returns principal moments, without this rotating tensor
profile. Explicit generalized stiffness/damping matrices could preserve some
constitutive effects, but would not alone restore distributed inertia. The
minimal mapping also has no validated representation of the separately owned
guide, connector and payload masses, inertias and offsets. None was dropped
or homogenized to obtain eligibility.

Subdivision into computational links with tied coordinates could address the
basis; tensor rotation and discrete rigid-body inertia would still need an
expanded mechanics adapter and validation. We did not prove that SoRoMoX is
incapable of this representation. We determined that a faithful model was not
available through the bounded minimal adapter. Private cache mutation or a
package mechanics rewrite would undermine the maintainability question.

The 89-line JAX diagnostic map preserves the source knot basis, discrete
asymmetric routing and rigid offsets. Length allocation remains a runtime
tracer throughout tip and tendon geometry, including `L_distal=0.27-L_proximal`.
Three representative states include zero and two nonzero configurations.
Tolerances were fixed before comparison. Results were:

| Check | Largest observed error | Interpretation |
|---|---:|---|
| Source JAX versus existing CasADi tip/tendon values | 1.67e−16 m | Passed 1e−9 m tolerance |
| State Jacobian comparison | 1.04e−17 | Passed 1e−8 absolute tolerance |
| Length partial derivative versus central differences | 2.93e−8 | All three steps passed mixed 1e−8 absolute + 1e−5 relative tolerance |
| Tendon virtual-work force sign | 1.27e−11 | Passed 1e−8 absolute tolerance |
| Native endpoint-abscissa length derivative | 0.5 | Failed 1e−7 tolerance |
| Native dedicated tips API length derivative | 5.19e−9 | Passed at zero and nonzero states |
| Native interior-abscissa length derivative | 3.40e−9 | Passed at zero and nonzero states |

The source comparison is JAX diagnostic code versus CasADi, not a full native
SoRoMoX versus CasADi dynamics benchmark. Finite input forces use
`−(∂tendon_lengths/∂q)ᵀu`, with actual channel order and the checked work sign.
These are partial geometry derivatives. Length derivatives through candidate
mass, constitutive dynamics, transcription constraints and a reoptimized
optimum remain **not established**. No objective-gradient or sparse
constraint-Jacobian check was represented as completed.

The first native probe used the native default pose, which is different from
the source mounting convention. The focused follow-up explicitly used identity
pose. At zero curvature, `forward_kinematics(q, L)` produced AD 1.5 versus
central difference 1.0 for the axial tip-length derivative, at all three step
sizes. The dedicated tips API returned 1.0 and passed. The same pattern held
at nonzero curvature. This isolates an endpoint-abscissa differentiation
hazard, with a tested API alternative; it is not a general indictment of JAX
or SoRoMoX differentiation. The
[follow-up evidence](../evidence/soromox_pilot_20261010/native_endpoint_followup.json)
retains exact calls, states, steps, tolerances and costs.

Case A fixes [0.16, 0.11] m. Case B exposes only proximal length
[0.1545, 0.1655] m under exact total 0.27 m. Section/routing scales, material,
holding weight 0.05 and terminal speed weight 0.1 are fixed in both explicit
[specifications](../examples/soromox/case_A.json),
[including B](../examples/soromox/case_B.json). They retain 35 identical
piecewise-constant tension intervals. The prospective normalized objective and
two reproducible input recipes were frozen before dispatch. Neither case was
solved: zero primary and zero additional NLP solves, zero returned candidates,
zero independent replays, and zero closed-loop launches. There is no A/B
optimization outcome or design-quality comparison to interpret.

No candidate passed replay because no candidate existed. The 1 mm/0.002 m/s
replay discrepancy gates and original task limits remain intact. MuJoCo was
not launched. A future controller-11 run on optimized geometry would validate
that geometry/controller combination, separately from executing the optimized
open-loop tension schedule; neither claim is made here.

The single live Strands smoke made four actual DeepSeek requests, all HTTP 200,
with known saved responses. It used one describe and five evidence reads,
and subsequent requests explicitly consumed `model_incompatible` feedback.
The model kept inspecting evidence and did not produce a final recommendation
before the ceiling. The attempted fifth request was rejected before sending.
There were no retries, summaries, additional model workers or unknown outcomes.
The first invocation also exposed an invalid cleanup property, subsequently
repaired by closing the existing transport. This repair did not rerun the
smoke. See [smoke outcome](../evidence/soromox_pilot_20261010/smoke_outcome.json).
The adoption decision above is the implementation pilot's evidence-based
decision, not an attributed final LLM decision.

| Actual resource | Cost/count |
|---|---:|
| Isolated numerical processes, including justified follow-up | 2 |
| Total numerical process wall time, including compilation/imports/checks | 32.9577 s of 7,200 s |
| Source JAX cold compile + first evaluation | 1.3908 s |
| Existing CasADi mapping construction | 0.0194 s |
| Native initial construction / cold compile + first evaluation | 7.2991 / 3.1085 s |
| Follow-up native construction / three unique cold compilations + first evaluations | 7.2542 / 7.1186 s |
| Warm source JAX evaluations | Per-state timings retained; not a controlled performance claim |
| NLP solving / replay / physical validation | 0 s / 0 s / 0 s |
| Actual provider response time | 8.0330 s |
| Provider prompt / completion / total tokens | 17,963 / 1,180 / 19,143 |
| Provider monetary cost | Unknown |
| Accounted public/check operations | 11 |
| Activity elapsed at scientific STOP | 3,033.0317 s (50.55 min) |

Installation/setup and modeling wall time were not separately instrumented.
They are included in the engineering/activity clock; no reconstructed precise
split is claimed. The environment was constructed once: Python 3.11.17,
SoRoMoX 0.5.0, JAX/JAXlib 0.10.2, cyipopt 1.7.0, IPOPT 3.14.20, CPU float64,
without optional rendering/RL extras. The accepted study interpreter remains
Python 3.11.16, CasADi 3.7.2, MuJoCo 3.13.0, Strands 1.59.0/Harness 0.2.0.
Exact setup and execution commands and locks are in the
[runbook](soromox_pilot_runbook.md). Cold timings include first evaluation and
are not pure compiler-only costs.

Five focused offline checks passed in 2.358 s, covering frozen A/B allocation,
physical versus numerical initialization, typed domain rejection, isolated
registration, and the existing generated-design caller. Actual Host integration
retrieved the corrected log and returned typed B solve and invalid-candidate
replay rejections without numerical or backend repetition. `pip check` found
no broken requirements. The archived artifact and framework hashes were checked
once, with zero scientific dispatch for delivery verification.

The capability gained is an accountable differentiable source-geometry probe,
native model admission evidence, and native LLM mathematical feedback with full
immutable retrieval. Differentiable candidate dynamics and joint trajectory
co-design were not gained. The new pilot Python code totals 768 lines: 89 mapping,
190 primary checks, 46 follow-up checks, 392 contracts/registration/runtime, and
51 one-time repair recording; focused tests add 70 lines. Maintenance includes
a separate Windows numerical environment, two lock layers, API/coordinate
mapping checks and the endpoint API caveat. Extending this to faithful mechanics
would add appreciable work, so adopting the package for the requested backend
scope is not justified by this pilot.

The fresh activity is sealed STOP, with unused experiment capacity unavailable
for automatic continuation. Detailed original and corrected artifacts plus
Strands checkpoints are in the
[immutable archive](../evidence/soromox_pilot_20261010/immutable_artifacts.tar.gz),
indexed by its [manifest](../evidence/soromox_pilot_20261010/archive_manifest.json).
The [machine summary](../evidence/soromox_pilot_20261010/result_summary.json) and
[ledger](../evidence/soromox_pilot_20261010/ledger.json) preserve counts and costs.
No global optimum, physical impossibility, robustness, real-time control,
motor validation or task success is inferred.
