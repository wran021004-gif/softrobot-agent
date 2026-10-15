# Serial family-space research: M3-C1 and M3-C2

## M3-C2 current interface

`study_variable_segments_dev.json` composes `family_study_defaults.json`, the
independent task/control/runtime sources, and `family_space_v2.json`. No family
preparation reads `robot.json`. Reference-candidate studies keep the old resolver
and effective configuration hash. Existing studies use their frozen Store state.
V2 uses one same-directory `base_space` composition over the v1 family declaration
to share its physical prototypes and unchanged domains. The sole resolver freezes
the complete validated definition and fingerprints both sources; nested family
bases are rejected. Runtime candidate generation reads only the frozen definition.

The Host requires a concrete SessionInput to validate backend signals and physical
compatibility. Its deterministic bootstrap is generated from the frozen family,
using its minimum executable segment/tendon counts. It has no candidate reference,
is absent from the candidate pool, and never establishes a scientific design,
comparison baseline, or task acceptance. The frozen study records the exact
bootstrap request and the reason it exists. Every candidate replaces the entire
physical structure, discretization and builder and derives its named initializer.

The optional analysis normalization map uses length defaults from the frozen
family domains for every declared segment index (`frozen_family_domain_defaults_v1`).
These are declared scales, not a reference robot or an initial scientific design.

The new contracts are `serial_family_space_v2`, `serial_family_generation_v2`,
`family.serial_space_build_v2@1`, and registered `candidate.family@6.0.0`.
The v5 two-segment generator and source-relative v3/v4 remain available. V2 uses
one assembly loop: the frozen rule names root/repeated flexible prototypes and
guide/connector/payload prototypes. Index 0 uses the root, every later segment
uses the explicitly named repeated prototype with its indexed or generic domain.
Each boundary owns a guide and connector. The terminal segment owns the payload.
Density, viscosity, station locations/angles and rigid inertia remain fixed.

All selected segments admit independent length, Young modulus, granted section
dimensions and an explicit integer `cells` override (1–32; default 12).
Spans support any `0 <= first_segment <= last_segment < segment_count`.
Routes and independent actuator channels are generated in span/group order.
Physical checks retain ordered stations, owned named holes, section envelopes,
pairwise clearances, nonzero spans, force limits and pretension constraints.
Unsupported declared tendon counts (8–12) remain distinct from invalid geometry.

Example action payload, embedded in the existing research_plan fields:

```json
{
  "action": "generate",
  "generation": {
    "version": "serial_family_generation_v2",
    "family_space_identity": "<exact frozen identity from packet>",
    "segment_count": 5,
    "tendon_count": 3,
    "segments": {"4": {"length_m": 0.12, "young_pa": 8000000, "cells": 4}},
    "spans": [
      {"first_segment": 0, "last_segment": 0, "count": 1},
      {"first_segment": 0, "last_segment": 2, "count": 1, "phase_rad": 0.8},
      {"first_segment": 1, "last_segment": 4, "count": 1, "phase_rad": 1.6}
    ]
  }
}
```

The Agent receives a deterministic summary with exact bounds encoded as
`[minimum, maximum, default]`; indexed segment fields override the generic domain.
It includes executable/declarative topology, routing and attachment constraints,
control domains, granted operations and numerical limitations. Component meshes
and inertia tensors are omitted. `study.family_space.full_specification` is the
exact immutable EvidenceRef for `research evidence_read` / normal Store paging.
That reference remains readable after recovery. No second design-space store exists.

`family_space_claims_v1` separately reports generated/physically validated
candidates, distinct designs and pairs of identified different candidates,
evaluated search operations, selected candidate, independent task acceptance and
confirmation. Reference-comparison fields are null with an explicit
`not_applicable_no_reference_design` reason. Generation is never an improvement
over the bootstrap. Historical reference-study claim values are unchanged.
RL input preparation, when independently authorized, compares the canonical task
rule while retaining the candidate-specific physical initializer; no training was
used to validate that input path.

### Measured compatibility and boundaries

The [physical table](../../evidence/m3c2_variable_segments/physical_generation.json)
uses explicit four-cell segments and three tendons, not a silent change of mesh:

| Segments | Physical DOFs | GVS coordinates / state | Materialized + MuJoCo XML loaded | GVS recipe/basis built | Zero-state dynamics | One real update |
|---|---:|---:|---|---|---|---|
| 1 | 8 | 6 / 12 | Yes | Yes | Tested separately at 12 cells | See short evidence |
| 2 | 16 | 12 / 24 | Yes | Yes | Tested separately at 12 cells | See short evidence |
| 3 | 24 | 18 / 36 | Yes | Yes | Tested separately at 12 cells | See short evidence |
| 4 | 32 | 24 / 48 | Yes | Yes | Not tested | Not tested |
| 5 | 40 | 30 / 60 | Yes | Yes | Not tested | Not tested |
| 6 | 48 | 36 / 72 | Yes | Yes | Not tested | Not tested |
| 7 | 56 | 42 / 84 | Yes | Yes | Not tested | Not tested |
| 8 | 64 | 48 / 96 | Yes | Yes | Not tested | Not tested |
| 9 | 72 | 54 / 108 | Yes | Yes | Not tested | Not tested |

The default 12-cell mesh hit a native Windows main-thread stack overflow loading
six segments (144 physical DOFs). Counts 1–5 loaded before that boundary; 7–9 were
not attempted at that mesh. Preserve the [native failure](../../evidence/m3c2_variable_segments/windows_xml_limitation.json).
This is an unresolved XML-loading resource limit, not structural infeasibility.

The exact C1 dense 22-coordinate failure was reproduced. All implicit terms were
finite; NumPy, CSparse and LAPACK solved the same mass/RHS, while default CasADi QR
failed. Its absolute R-entry singularity cutoff is 1e-12 in CasADi 3.7.2. Dividing
both mass and RHS by the mass Frobenius norm removes this unit-dependent rejection
without regularizing the model or changing forces. Rechecked 12/14/22-coordinate
dynamics pass, with residuals and NumPy agreement recorded in the
[diagnostic](../../evidence/m3c2_variable_segments/gvs_dense_diagnostic.json).
The historical controls differ in routing/tendon layout, not dimension alone.
No representation-only basis comparison is supported by the existing
structural-station semantics. The [original failure](../../evidence/m3c2_variable_segments/gvs_dense_original.json)
is retained. No universal dense-layout or high-segment control claim follows.

The opt-in `SOFTROBOT_M3C2_CONTROL=1` verification uses the existing registered
controller/backend and original Store, binds a committed implementation, admits
at most three cases, and stops before a second command. Each case permits one
0.01-second interval (20 steps at dt=0.0005). Exact numerical/control outcomes,
costs, states, bounds and failures are in [short_control.json](../../evidence/m3c2_variable_segments/short_control.json)
and its [Store export](../../evidence/m3c2_variable_segments/control/).
That study is single-use: read/recover it rather than rerun the fixture. No full
task evaluator, provider call or RL training is authorized by this entry.

M3-C3 still owns mixed discrete/continuous search and a non-Agent baseline; M3-D
owns mathematical decision utility; M4 owns frozen multi-task benchmarking.

## Retained M3-C1 contract

`configs/research/study_family_space_dev.json` now composes family-only study defaults,
task, control and runtime with `family_space_v1.json`. It explicitly grants only
offline generation and STOP: provider requests, backend executions, mathematical
worker evaluations and RL stages are zero. `research_analysis` remains registered;
its existing frozen count boundary rejects computation in this example.

Preparation freezes the canonical task, initialization rule, family declaration,
control, permissions and budgets in the existing Store. It stores no scientific
reference candidate. Status, decision packets, export, recovery and re-preparation
accept `reference_candidate: null`. The Agent sees the family declaration and
`generate` action. No mathematical analysis is required before generation.

The original C1 delivery used a robot-derived Host scaffold. Current family-only
preparation uses the family-derived bootstrap described above. Its segment, guide,
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

The historical C1 delivery deferred variable-segment assembly to M3-C2;
8–12-tendon execution and dense-node numerical compatibility also require explicit
validation. No provider request, full NMPC rollout, RL training or full-task
evaluation was performed for this delivery. Historical outcomes remain sealed.
