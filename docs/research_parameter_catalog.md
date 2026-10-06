# First-study parameter capability and grant, version 1.0.0

The first study uses `candidate.family@1.1.0`, registered in the tendon-family
manifest. Its trusted `parameter_declarations` hook owns the stable semantic IDs,
physical coupling, mutation implementation, legal domains and integration backlog.
`tools.parameter_catalog.effective_catalog` joins those declarations to the actual
controller/model/backend/task, configured builder domains, study grants, and
separately supplied validation evidence. The catalog does not enumerate arbitrary
configuration fields or treat an unsupported implementation as a permission issue.

`study_input` projects the pool onto the exact retained M4 incumbent configuration
`285236abf99bf36894fa08410ac82fefa177a80179c4ceba15d95f8d1bc8d978`, from execution
`91c3ba1b01d6499fb26df8f95409401b` in
`runs/milestone4_autonomous_20261006`. It preserves the original robot bytes and
execution scope before any edit. The common selectors are replaced in the new
builder specification by disjoint per-segment selectors with incumbent defaults
`.95` and `compliant`; their source stays the original physical design, rather
than rebasing a new scale on an already scaled candidate. Historical artifacts and
`candidate.family@1.0.0` behavior remain intact.

| Family | Stable IDs | First-study domain | Meaning and fixed coupling |
| --- | --- | --- | --- |
| Segment lengths | `components/near/length_m`, `components/far/length_m` | near `[.15,.17]` m; far `[.11,.13]` m | Fixed segment topology, 12 cells per segment, section stations, tendon routes and attachment fractions |
| Per-segment section scale | `design/near_section_scale`, `design/far_section_scale` | `[.95,1.05]` | Absolute multiplier of original dimensions; preserve shape, station layout, aspect ratios and orientation |
| Per-segment material scenario | `design/near_material_scenario`, `design/far_material_scenario` | `baseline`, `compliant`, `stiff` | Original Young modulus × `1`, `.9`, `1.1`; original density and bending viscosity retained |
| Controller speed objectives | `control/recipe/terminal_tip_speed_weight`, `control/recipe/holding_tip_speed_weight` | `[.025,.1]` | Squared world tip speed normalized by the frozen speed scale; objective weights do not alter acceptance thresholds |

These material scenarios are numerical simulation inputs, not validated commercial
materials. No arbitrary independent density/viscosity/modulus combinations are
exposed. A common and per-segment selector for the same physical quantity cannot
overlap. The new expansion modifies only the fields it owns; it does not reconstruct
whole physics or section records over other requested edits.

The supported first-study combination is `controller.gvs_nmpc@7.0.0`,
`backend.family_mujoco@1.1.0`, `model.serial_bending_cells@1.0.0`, and `task.reach`.
Structural technical compatibility is checked against the declared physical source,
separately from a historical task/performance match. A catalog row keeps technical
support, study permission and evidence in distinct fields. Numeric bounds and
discrete options must remain inside the connected builder and legal domains.
All comparison groups may select any subset of this same pool without per-batch
user approval. Newly connected capabilities require a new shared capability and
study version. The execution grant remains separately bounded by the study budget.

Every row supplies its effective named configuration locations, components,
couplings, derived quantities, rebuild obligations and reuse rules. Physical edits
rebuild resolved geometry/mass/inertia/stiffness/damping, backend mesh/model, reduced
geometry/basis and projection, controller workspace, initializer binding and warm
states. Control objective edits rebuild the controller workspace and warm states.
Historical bounded tensions may remain numerical guesses; saved states,
candidate-dependent analyses, plans, trajectories, evaluations, profiles and joint
acceptance cannot be rebound to the changed configuration. Replayed/cached results
are not new repetitions.

The concrete backlog is exported alongside the pool: segment-count changes need
topology and comparable initialization mapping; tendon-count changes need input
dimension/order, actuator transmission and controller reconstruction; routing and
shape changes need a research mutation adapter, projection and stable controller
validation. Density/viscosity changes need a manufacturing-consistent material
mapping. Changed discretization needs a new state mapping, compatibility and cache
policy. Shear, stretch, torsion, tendon friction, rope elasticity and motor dynamics
are absent from the model. Arbitrary solver recipes remain fixed in this study.
Natural curvature is represented but requires preload-consistent initialization
and changed-rest-shape controller validation. Payload mass/COM/full inertia are
represented but lack a coupled physically consistent research mutation and
projection/controller validation; rigid payloads remain fixed in this version.
Existing compiler representations alone do not establish these research paths.

Focused offline validation: `python -m unittest tests.test_parameter_catalog`
passes four checks. A combined edit of all eight parameters survives the public
`_candidate`/`candidate.apply` path and reaches resolved mass/stiffness/damping and
generated MuJoCo XML. The tests also verify unchanged topology/input order,
source-relative follow-up edits, preservation of unowned fields, independent subset
masking, overlap rejection, exact source science, and separate capability/grant
status. XML is checked in memory; no backend/controller solve or provider request
is used. Three existing historical structural parameter checks also pass. These
checks validate mutation plumbing; they establish no closed-loop robustness or
performance for newly combined values. The first-study integration evidence is
recorded separately by the shared runner.

The future builder also connects this pool to the existing shared LLM plan/batch
interfaces: `parameter_impacts` projects catalog rows into their existing schema;
plan validation and offline batch preparation accept any registered granted subset;
comparison scope masks the actual pool; planning projection retains the archived
source's common/per-segment selections without changing its scientific execution
scope. The fourth check uses an explicitly labelled in-memory engineering fixture
with archived input and plan schemas to validate an immutable mixed numeric/discrete
plan through real domain, candidate, scope and ask/tell preparation. Host event/alias
lookups are fixture substitutions; no result is presented as newly measured science.
The old builder continues to use the frozen historical mapping and behavior.
