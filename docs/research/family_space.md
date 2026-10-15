# M3-C1 family-space-first candidates

`configs/research/study_family_space_dev.json` composes the existing study defaults,
task, control and runtime with `family_space_v1.json`. It explicitly grants only
offline generation and STOP: provider requests, backend executions, mathematical
worker evaluations and RL stages are zero. `research_analysis` remains registered;
its existing frozen count boundary rejects computation in this example.

Preparation freezes the canonical task, initialization rule, family declaration,
control, permissions and budgets in the existing Store. It stores no scientific
reference candidate. Status, decision packets, export, recovery and re-preparation
accept `reference_candidate: null`. The Agent sees the family declaration and
`generate` action. No mathematical analysis is required before generation.

The Host still needs a concrete SessionInput for interface checks. `robot.json`
supplies that explicitly labeled implementation scaffold. It is never added to
the candidate pool or exposed as an Agent proposal. Its physical segment, guide,
connector and payload prototypes are separately frozen in the family declaration,
with segment IDs `segment_0` and `segment_1`; source routes and source actuator
objects are excluded. Density, viscosity, section stations, guide envelope/hole
radius, connector, payload and mesh remain explicit assembly defaults. The task
owns mount, gravity, floor and external forces.

| Domain | Example declaration | Current materialization |
|---|---|---|
| Flexible segments | 1–9 | Exactly 2; all other declared counts return `not_yet_supported` |
| Independent tendons | 1–12 | 1–7 subject to physical checks; 8–12 explicitly unvalidated |
| Segment lengths | General .06–.24 m; index 0 .08–.24, index 1 .06–.20 | Independent continuous values |
| Young modulus | 2–15 MPa | Independent per segment; density/viscosity fixed prototypes |
| Sections | Circle, tube, ellipse, rectangle | Independent typed sections at prototype stations; dimensions checked against per-kind domains |
| Radial attachments | .014–.023 m | External section-plane routes; station envelopes and tendon clearance checked |
| Guides / anchors | Guide s=.15–.75; anchor s=.8–1 | Normalized local segment coordinates; ordered guides precede anchor |
| Angular layout | Phase ±2π, offsets ±π rad | Uniform or individual offsets; independent guide/anchor angular offsets |
| Tendon physics | Diameter .5–1.2 mm, force 1–8 N, pretension 0–1 N, servo gain 300–1500 N/m | Pretension ≤ force limit; named holes enforce diameter and clearance |
| Speed penalties | Holding / terminal weights 0–1 | Existing NMPC recipe; task acceptance unchanged |

The generic segment domain also describes indices not constructed in C1. Indexed
domains apply when those segments exist. Span endpoints, segment overrides and
individual route overrides must refer to the selected topology. Sections omitted
from a request retain the declared physical prototypes; domain defaults provide
scalar defaults and representative dimension values. This is a set of allowed
designs subject to coupled physical checks, not a claim that every Cartesian
combination is valid. The compiler supports polygon sections, but this example
does not grant a polygon domain. No general constraint DSL or new registry exists.

After preparation and committed binding, use the existing CLI `execute --plan`
with a native Plan containing the usual hypothesis/evidence/interpretation fields
and the following action payload (replace the identity with the packet value):

```json
{
  "action": "generate",
  "generation": {
    "version": "serial_family_generation_v1",
    "family_space_identity": "<frozen family_space_identity>",
    "segment_count": 2,
    "tendon_count": 5,
    "spans": [
      {"last_segment": 0, "count": 2, "phase_rad": 0.3},
      {"last_segment": 1, "count": 3, "phase_rad": 0.8,
       "angular_offsets_rad": [0, 0.13, -0.08], "radius_m": 0.021,
       "guide_s": [0.4], "guide_angle_offset_rad": 0.06,
       "anchor_angle_offset_rad": -0.09}
    ]
  }
}
```

Omitting spans distributes the requested count around a full two-segment span.
`first_segment: 1, last_segment: 1` starts on the intersegment guide and actuates
only segment 1. Span counts must sum to tendon_count. Stable `tendon_i` and
`actuator_i` order follows group order and then angular index. Typed individual
RoutePoint overrides remain subject to span ownership, local envelopes, stations,
named guide holes and the physical compiler. Actuators are built independently
from the declared displacement/ideal-tension rule, limits and velocity.

Successful generation returns an immutable candidate reference, resolved segments,
routes, actuator/channel order, force limits, physical DOFs, GVS coordinate/state
and input dimensions, and initial projection/pretension preparation status. It
does not construct a dynamics graph or execute control. Invalid requests return
`invalid`; declared unimplemented topology returns `not_yet_supported`. All
construction attempts record actual local elapsed cost.

Identity includes the effective physical/control configuration, frozen family
identity and evaluation profile. Compact request spelling is provenance: omitted
versus explicit defaults reuse an equivalent candidate. Different physical
routes, geometry, actuation spans or control weights obtain different identities.
The builder retains the exact generation contract and request. The authorized
`all_candidate_dofs_zero_v1` rule materializes candidate-specific joint names;
`task_identity` identifies the canonical objective/rule, while
`effective_task_identity` and `initialization_provenance` identify the concrete
SessionInput representation. Existing source-relative task/candidate identity and
legacy Plan serialization retain their previous meanings.

Focused tests exercise 1/3/5/6/7-tendon designs, asymmetric mixed spans and distal
actuation. Representative genuine model checks have Jacobians (1,12), (5,14),
and (7,12), with state dimensions 24, 28 and 24. MuJoCo XML compiles without
stepping physics. A denser layout with 22 GVS coordinates compiled physically
and had a full-rank finite mass matrix, but its zero-state CasADi dynamics solve
failed. That is a numerical limitation, not structural infeasibility. Dense
station layouts remain unchecked for control compatibility; C1 does not change
GVS/NMPC kernels to resolve it. Station checks do not certify swept self-collision,
manufacturability, controllability or task feasibility.

M3-C2 owns variable-segment assembly and progressive numerical compatibility;
8–12-tendon execution and dense-node numerical compatibility also require explicit
validation. No provider request, full NMPC rollout, RL training or full-task
evaluation was performed for this delivery. Historical outcomes remain sealed.
