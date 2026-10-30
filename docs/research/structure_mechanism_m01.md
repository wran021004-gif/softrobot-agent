# Native mechanism and structure research, M0/M1

This change extends the existing scientific-question interface, analysis worker,
Store, accounting, result cards and Reporter. It adds no controller, evaluator,
search engine, candidate store or autonomous research loop.

## Read-only audit and source selection

The isolated development worktree starts from the local mathematical research
worktree `softrobot-h`, branch `codex/p6-3h-conic-native-study`, commit `25374a3`.
Its ancestry includes the C1 discovery, C2 scientific intent and F result-feedback
repairs. The local G/G2 branches were also inspected: G2 `e86097d` has a newer,
separate structure-search intent adapter based on G `891c679`. It is not an
ancestor of H. This change does not merge those branches, import their research
results, or modify any historical Study. The older D: main checkout was inspected
and is not the selected mathematical baseline.

| Existing capability | Decision | Concrete reuse or boundary |
| --- | --- | --- |
| `NativeModel.mechanics()` | Reuse | Native tip/length Jacobians, mass, active force map, acceleration/input map, singular values, braking range and force residual. No second engine computation implementation. |
| FamilySpace capability rows | Reuse | Actual selected paths, physical effectiveness, SI domains and discrete/continuous classification. Existing `family_variable_authorized` and frozen sensitivity-variable grants remain authoritative. |
| `generate_candidate` materialization | Share | Extract `family_configuration`; formal generation and mathematical perturbations call the same family builder. Only formal generation registers candidates. |
| Existing analysis dispatch/recovery | Retain | Original candidate/source checks, task protocol, contained worker, reservations, mathematical count, wall time and immutable receipts. New numerical modules join the original science freeze. |
| V1 scientific questions | Retain | Existing fixed-input response, Conic initialization, Native T1 and saved T2 keep their behavior. V1 mechanism/closed-loop/passive-re-equilibrium semantics were declarations without adapters. |
| L0 catalogs and fine method menu | Consolidate for V2 | Four scientific operations, mechanism categories, effective length group and direction/detail queries. Legacy method templates remain in L1, rather than being deleted or duplicated in L0. |
| `endpoint`, `braking`, `native_dynamics_v1`, `fixed_input_structure_v1` | Retain | Existing numerical kernels and callers remain compatible. Their meanings are recorded in the shared mechanism catalog. |
| Reporter/result-card path | Extend | Deterministic mechanism values, proposal direction and numerical consistency are source-bound facts; the Reporter may add interpretations only. |
| PHS-2D equilibrium/Jacobian/KKT | Read-only | Inspected `StaticProblem`, `solve`, `row_match`, `matching`, and passive `design_sensitivity` at `research/phs2d-inverse-passive-design`. Passive KKT requires qualified equilibrium, LICQ, strict complementarity, fixed active set and material-point binding. No passive runner or acceptance rule is migrated. |

No legacy numerical kernel is retired: callers are not yet fully replaced.
The removed duplication is the V2 default display of detailed legacy methods
and the copied family-materialization code.

## Opt-in contract and actual scope

Only a new configuration explicitly selecting `scientific_question_v2` and
granting `mechanism_structure_v1` can execute this route. The completed
`research_plan(diagnose)` supplies its candidate, hypothesis, selected variables,
budget and frozen task. Formal mathematics scope authorization is still required.
All four operations use the original `research_analysis` tool.

| Operation | Current mechanism behavior | Mathematical evaluations reserved |
| --- | --- | --- |
| `inspect` | Read a registered primitive/composition at the declared native state | 1 |
| `differentiate` | One authorized effective segment length, rebuilt at `-h,+h,-h/2,+h/2` | 5 |
| `optimize` | Same local stencil, select its improving half-step if consistent, then rebuild/recompute that proposal once | 6 |
| `compare` | One owned same-task comparison candidate under explicit point/input semantics | 2 |

`optimize` is a bounded local proposal check, not a new optimizer or a claim of
local/global optimality. Formal design changes still require the existing
generate/propose path, followed by their own evidence and independent evaluation.

Targets are registered primitives composed with identity, norm, minimum, maximum
or a unit-world-direction norm. No Python expression evaluation is accepted.
The native maps retain units, dimensions, named hinge/tendon order, coordinate
frame, model source, state, actual tensions/bounds and parameter dependencies.
Identity matrix/vector inspection remains raw evidence, not an L0 matrix dump.

Active tendon force channels are not fixed-length constraints. Tendon Jacobian
row projection is a geometric relation only. Passive taut-active-set nullspaces
are explicitly unavailable. Instantaneous braking is unavailable at zero speed.

Both `frozen_task_initial_state` and `same_generalized_coordinates` reset solver
history in every compared model. The former uses each structure's task initializer;
the latter transfers the same named generalized coordinates/velocities. Neither
means identical Cartesian pose, energy, equilibrium or preserved physical state.
Saved sources retain the original native checkpoint/prefix admission; prefix
reconstruction work, when requested, belongs to the existing numerical cost.

The central step is bounded by the actual parameter domain and distance from its
boundaries. Sign agreement and a 10% two-scale relative check qualify a local
numerical direction only. Flat response, illegal reconstruction, nonfinite state,
changed constraints or inconsistent scales cannot produce a verified direction.
The existing attempt reservation is retained even when a calculation fails early;
raw work counters distinguish actual attempted/built models from the reservation.

## Evidence and verification

L1 `/structure_research` joins the original capability rows with the mechanism
catalog, evaluation counts, applicability and the existing method directory.
L2/L3 result `/structure_research` stores model configurations, states, mechanics,
observations, two-scale samples, consistency, costs and proposal source pointers.
`StructureDirection` reports the exact candidate, path/unit, baseline and changed
metric, local delta, tradeoffs, point/model scope and actual work. It explicitly
sets `full_task_improvement_verified=false`, `formal_candidate_created=false` and
`proposal_only=true`. It never becomes an independent acceptance result.

Targeted tests extend `test_p63c2_scientific_intent.py`; existing native-analysis,
capability-catalog, family-generation and V1 Conic-initialization tests cover the
affected boundaries. Synthetic fixtures are labeled and do not represent physics.

The separate command `python -m tests.research.structure_mechanism_check` runs
the committed `study_structure_mechanism_m01_check.json` configuration. Its cap
is six native model/mechanics attempts, zero integration steps, zero Provider,
zero control search and zero independent task evaluations. It uses the registered
`reach_free` family/task and the production worker, Store and accounting. Frozen
sources, source states, actual numeric results, costs and assertions are exported
alongside the validation summary; no historical evidence is rewritten.

### Observed result, 2026-10-30

The committed worker result is a valid **unresolved local observation**, not an
improvement. The first segment length was 0.16 m, with steps 0.0016 m and 0.0008 m.
The acceleration/input-map norm was 286.07851839741716 m/s^2/N; all four changed
values differ by only about 2.4e-11. The two secants were 4.689582056e-9 and
-6.394884622e-10 per metre. Opposite signs fail the direction check. The mass
matrix changed by 3.135345369e-5 kg*m^2 in maximum absolute entry, confirming that
the rebuilt physical parameter was effective even though this selected metric
was flat. No proposal is emitted for this observation.

Actual work: five model builds, five mechanics evaluations, sixteen native
forward calls, zero integration steps and zero rollouts. The original six-count
reservation remains charged; worker time is 2.2880335 s. No Provider, control
search or independent task evaluation ran. Only the original baseline candidate
is registered. The raw result and original ledger are in the existing export
under `evidence/structure_mechanism_m01`.

The initial validation assertion incorrectly required six builds and an improving
direction. Its failure log is preserved. The validator was corrected to accept
the scientifically valid unresolved branch, then checked the same saved result;
there was no second native worker or additional model build. A synthetic native
fixture separately exercises the full six-build proposal/recheck branch through
the production orchestration; those numbers are not physical evidence.

Across the five selected test modules, 53 test cases passed. One unchanged
family-summary size assertion failed (`6313 < 4702.2`) and was reproduced in an
isolated checkout of the original `25374a3` baseline. The relevant summary and
packet functions are unchanged; this pre-existing display-size issue is outside
the V2 route. The V1 Conic compiler tests passed using the already installed H
cvxpy/Clarabel dependencies. Earlier missing-dependency and validation logs are
retained alongside the final results; no full suite or historical replay ran.

## Unsupported now and M2 reuse

- Structural FD is limited to one interior, effective, authorized segment length.
  Other continuous groups are discoverable but are not yet adapted or validated.
  Topology/counts require discrete candidate comparison; no ordinary derivative.
- Joint-coordinate comparisons across incompatible named coordinate/channel sets
  are rejected. Cartesian-state preservation and re-equilibrium mappings are not
  implemented. Domain endpoints currently need a future one-sided stencil.
- Native structural analytic/AD/KKT derivatives are unavailable for this binding;
  the route returns controlled finite differences with no strict derivative,
  regional error bound or descent certificate.
- V2 fixed-input trajectory, reoptimized task capability, closed-loop performance
  and passive re-equilibrium semantics return explicit unsupported reasons.
  Registered real task-constraint targets are recognized but need M2 response
  semantics; they are never substituted with a local mechanism norm.
- M2 should reuse V1 fixed-input structure response, `native_point` source binding,
  T1 control schedules and full-task quantities, saved T2 comparability/scale
  checks, Conic/controlled-capability stencils where applicable, the original
  search/generation entry, and independent `physical_replay`/task acceptance.
  Keep the same worker reservations, Reporter and main-Agent decision ownership.
