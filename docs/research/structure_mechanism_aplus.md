# Structure mechanism A+: bounded local research and Main adoption

This continues the source/evidence published at `956daa9` on
`codex/structure-mechanism-m0-m1`. Its tree is identical to local A commit
`7e52989` (tree `7fff37eae3987dc4a7f70e622229c6a71cf891c5`). Historical A evidence
is immutable: the length/acceleration-map-norm probe was **unresolved**. Its five
native models, 16 forwards, zero integration and six reserved math units are
not repeated or relabeled by A+.

## Audited boundary and changes

A already rebuilt legal models and recorded two-scale central differences. Its
`optimize` meant choose an improving local probe and recheck it, not a complete
structural optimizer. A+ reuses those mechanics, rebuild, worker and accounting
interfaces. The length-only condition and fixed operation-cost table are removed.
The existing SciPy Powell implementation provides a bounded local best-found
mechanism search, with explicit normalized bounds and evaluation cap; no new
optimization engine, global optimum or task descent certificate is introduced.

`structure_research.parameters` projects the current FamilySpace capability rows
and the original frozen parameter grant. The actual selected topology, inherited
prototype values and implemented generator determine availability. Effective
continuous lengths, Young modulus, section dimensions and actual routing paths
are supported. Declared `physical_parameters` additionally expose density,
bending viscosity, intrinsic curvature and anisotropic section angle. These fields
are absent from spaces that do not declare their physical domains; isotropic
section angle and overridden/inactive routes retain the original unavailable
reason. Assembly-fixed objects without a continuous domain remain unavailable.

Controller weights, numerical cell counts, pretension/initialization, clearance-only
tendon diameter and bypassed servo gains are not structural derivatives. Tension
limits change the feasible input set and cannot enter fixed-input structural
sensitivity. Counts and topology remain discrete model comparisons.

## Numerical meaning and cost

One or two actual paths share a baseline. Each uses normalized domain coordinates;
positive domains spanning at least 100x use log coordinates. Central two-scale
stencils use four distinct probes; second-order inward one-sided stencils use
three. Values, steps, secants and units in physical coordinates are retained.
Consistency requires a distinguishable signal, matching derivative signs and
relative two-scale agreement. Zero/flat, inconsistent or insufficient responses
remain unresolved. These are numerical diagnostics, not strict error bounds.
Two parameters additionally require a small combined probe and a checked local
linear prediction; a selected combined search point is checked as well.

Required math evaluations are baseline + actual unique per-path stencil probes
+ one joint check for two paths. Optimize requires room for at least one extra
local probe and reserves the requested cap (at most 64). Actual attempted builds,
mechanics, forward calls, prefix reconstruction, integration and wall costs remain
recorded separately through original analysis admission; unused reserved math
units are not presented as physical model calls. Failed probes consume attempts.

Working points distinguish each model's task initializer, fixed generalized pose
(zero velocity), transferred named qpos/qvel, and actual owned saved native state.
A saved state is exact only for the baseline; other structures reset history and
transfer named coordinates. Cartesian pose, equilibrium and energy are not
preserved. Speed/braking research can select an actual execution interval with
nonzero velocity, near hold or with a large measured violation using the existing
source query and update_id admission. No state is generated merely to improve a
mechanism result.

## Mechanism selection and M0/M1 boundary

MechanismRegistry composes exported NativeModel quantities: signed world-direction
per-channel drive, legal-box directional acceleration bounds including drift,
normalized generalized force directions/projections, tendon-row residuals,
kinematic motion decoupling, total mass, body-local inertia trace, compiled hinge
stiffness/damping, and the prior Jacobians/inertia/drive/instantaneous-braking
metrics. It does not re-extract mechanics. Matrix norm remains an explicit choice,
not a universal task objective. Geometric row spaces are not passive constraints.

M0 is instantaneous mechanics and local structural effects. V2
`effect_semantics=fixed_input_response` compiles inspect to original
`short_input_response_v1`, or a selected single-parameter comparison to original
`fixed_input_structure_v1`, with an explicit legal short horizon (<= .05 s), fixed
absolute input and original source/cost checks. It does not claim the complete
Reach/Hold task. No new rollout, passive KKT, closed-loop derivative, PHS, NMPC
or RL adapter is added.

M2 should reuse existing T1 (`mujoco-nonlinear-task-capability-v1`): complete owned
control source, fixed task/candidate/channel/grid/bounds, chosen correction
window/knots/response-or-pattern settings and finite budget. It should aggregate
compatible baseline/minus/plus T1 results through existing T2
(`mujoco-reoptimized-structure-response-v1`), preserving source settings, scales,
active sample switches and held-out validation coordinates/T1 evidence. Existing
Conic bounded-affine model/source stencils remain separate and available. Failed
search or unresolved secants never prove infeasibility.

## Main adoption and evidence views

A StructureDirection is an immutable mathematical result with baseline candidate,
actual paths/values/units/bounds, metric, numerical consistency, physical model
scope, source pointers and unverified task risks. Its full generation_handoff
contains a validated original `serial_family_generation_v2` request. Other
parameters remain at their resolved baseline values. No Store registration happens.

Main reads `/mathematical_decision_view/structure_research` and the supplied full
generation query, then chooses adopt, reject, inspect further or change hypothesis.
If adopting, Main loads `research_plan(generate)` with existing `research_route`
when necessary and submits an ordinary generation Plan with supporting evidence.
Original schema, generation constraints, ownership and budget gates remain in
charge. There is no proposal Store or automatic candidate submission. L0 derives
formal candidate creation from the generated candidate's ordinary Plan provenance.

V2 preserves the existing mathematical_research view and adds compact
mechanism_research, with groups, direction/candidate status, available actions and
query links. L1 expands actual parameters, mechanisms, state sources,
applicability and costs; raw matrices, rebuilt configurations and all differences
remain in L2/L3. Reporter assembles fixed numerical facts and may interpret their
physical conflicts/competing hypotheses; it cannot edit facts or declare acceptance.

## Verification plan and stopping condition

The directed offline tests fabricate every numerical NativeModel output and mock
HTTP response; they validate real contracts, compiler, Store admission, Reporter,
Main reads/rejection/adoption, original tool routing and candidate generation.
Real evidence is separate: existing reach_free, one FamilySpace S7 candidate,
section width / declared density / routing phase, one predeclared directional
metric and one two-scale differentiation per category. The cap is 15 native
attempts, zero integration/Provider/control optimization/task evaluation. No old
A check, historical Benchmark or autonomous Study is run. Results and actual
costs are recorded in `evidence/structure_mechanism_aplus/validation.json`.
The preexisting family-summary size assertion is outside this change; its known
baseline failure remains recorded in A evidence without unrelated restructuring.
