# Base-only passive research implementation

The existing FamilyMixedSearch now routes explicit passive modes through
`passive_search.py`. Active mathematical_proxy/CONIC and mujoco_control defaults
and control objectives retain their existing paths. New searches use the same
conditional coordinate proposals, generator, candidate identities, checkpoints,
analysis Workers, budgets, Store and Evidence. Per-load references are sealed
before continuing; completed searches reuse their original receipts.

The opt-in `family_space_base_only_passive_v1.json` opens density, natural
curvature, viscosity and section rotation, lengths/modulus, analytic sections
and bounded polygon contours, routing/guide/anchor coordinates, independent
payout and mesh generation. No winning candidate, trajectory or warm start is
supplied. Domain sources:

| Domain | Source and meaning |
|---|---|
| 1–32 segments / 1–64 tendons | Configurable construction-cost caps, not generator-wide physical limits or historical feasibility limits |
| Length .005–1 m; E 10^4–10^8 Pa | Exploratory positive material/geometry domain; no material calibration claimed |
| Density 100–5000 kg/m³; curvature ±25 rad/m | Exploratory material/reference-state ranges; actual compiler mass/inertia and spring reference are rebuilt |
| Viscosity 0–.05 N m² s | Exploratory nonnegative bending viscosity, same constitutive implementation |
| Payout 10^-5–64 m | Positive assembly length domain spanning the chosen chain envelope; no guarantee every arbitrary zigzag route fits; independently editable per tendon |
| Polygon coordinates ±.02 m; 3–64 total vertices | Explicit construction-cost and envelope bounds; original ring intersection, hole containment, positive area and inertia checks apply |
| 1–64 cells per segment | Generator domain; convergence is a separate generation/comparison investigation. Frozen search fidelity remains 8 cells |

Polygon generation accepts arbitrary valid bounded rings/holes; mixed search
currently explores a square polygon subfamily and continuous scale. Arbitrary
polygon seeds are explicitly rejected rather than silently projected. Section
stations remain prototype-owned. Material and analytic section variables rebuild
area, COM, mass, inertia, stiffness and reference curvature through the existing
compiler. Rigid guide/connector inertias remain supplied prototype data; hole
size, friction, tendon mass and unsupported torsion are not falsely advertised
as coupled physical variables. Base-only generation still requires the original
fixed base, owned serial parts, ordered routes, real holes and clearance; no
world anchor or extra support is introduced.

`passive_equilibrium` reuses true nonnegative cable multipliers, length bounds,
complementarity, KKT, capacity and reduced-stiffness qualification. Every selected
load uses the same design and payout but may have a different active set.
It ranks the worst frozen normalized static observation when available, or
explicitly selected equilibrium qualification diagnostics. Original PHS has no
static task observation objective: such a request is rejected, never silently
replaced by a weakened dynamic objective. A named load subset is diagnostic.

`passive_task_response` uses existing complete finite-time mechanism evaluation
and task constraint normalization. All original conditions, validity gates and
thresholds are retained, without PHS metric names in the search kernel. It needs
the original physical episode/time budgets. Paired-ablation tasks require an
explicit intervention and are currently unsupported by this mixed-search mode;
the existing high-level paired analysis remains available. No full original
ten-condition evaluation was run for this development task.

The existing `research_plan(search)` scientific contract accepts
passive_structure_research/no_active_control. `research_analysis` retains
scientific_question_v4 and now accepts a passive parameter group without raw
paths: fixed code chooses at most two representative fields, holds other
coordinates fixed and records selected coverage. M0 mechanism and M2 complete
finite-time response remain independent. Parameterized problem and sensitivity
evidence bind actual FamilySpace rows, observable units/frames/source/validity,
physical problem, differentiation method, raw stencil/implicit-KKT checks,
active sets, cost and scope. Existing two-scale consistency and implicit KKT
regularity gates still withhold unreliable gradients.

Search aggregates now enter the existing citation/Reporter directory. Fixed
facts include score semantics, condition eligibility, costs and termination;
Reporter cannot grant physical acceptance. Raw matrices remain in Evidence.

Directed checks completed during implementation: physical density/inertia and
curvature linkage, polygon/bounds/mesh and Base-only rejection; real static
Worker + Store + idempotent reuse; group selection/static-objective admission;
formal high-level Plan → two-load native computation → accounted read-only
Mock Reporter. Existing passive real equilibrium and active search-contract
compilation checks passed. The real active two-scale regression requires a
clean implementation bind and is run after this implementation commit; its
initial dirty-tree refusal did not execute physics. No real Provider used here.
