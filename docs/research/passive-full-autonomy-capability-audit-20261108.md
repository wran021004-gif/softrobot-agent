# Full Base-only autonomous Study capability audit

New Study: `passive-base-only-full-autonomous-study-20261108-02`.
Profile: `configs/research/study_passive_base_only_full_autonomous_20261108.json`.
Store: `runs/research/passive-base-only-full-autonomous-study-20261108-02/platform.sqlite`.
The unique suffix preserves an earlier zero-request startup failure (legacy Knowledge metadata missing an optional summary) and an offline name reservation; no reservation,
candidate, budget, checkpoint or Worker is transferred. The original Study is
read-only historical background. Its failed observations are supplied as a small
source-linked report, without successful design parameters or an old Store copy.

## Identity and objective

The source `base_commit: HEAD` resolves once to the exact implementation commit
when preparing the new frozen Study. It must equal the subsequently bound HEAD;
existing Stores never reload this source. The runtime `startup-summary.json`
records that commit, profile identity, exact original Plans and actual costs.

Original task: `tasks/phs2d_original_ten_v1_2.json`, canonical identity
`5420ad0d87475ac3fb651e3ef63ec0ba97250a346feb1d3f2df5ea95bcf3c42a`.
Canonicalization replaces only named initializer coordinates with the existing
all-candidate-DOFs-zero rule. The complete original task, ten programs, timing,
evaluator, thresholds, local/tip/ratio/path constraints and route/contact gates
are preserved. No task file or evaluator is changed.

Family: `serial_base_only_passive_open_v2`, identity
`1eb0010fc36f45b590a758f53d71b9cb69c55b000a568b48a07025c62ed2840f`.
Model: `model.serial_bending_cells@1.0.0`; no external fixed anchors or support.
Primary objective: a new, fully verified ten-condition feasible structure.
Fewer tendons are a secondary preference reflecting actuator complexity; they
are neither a hard cap nor a substitute for feasibility. Segment count stays open.
Fixed-payout execution itself has no active controller.

## Parameter coverage

`parameter_capabilities()` / `resolved_request()` in
`extensions/tendon_family/family_space.py` own actual paths, effects and domains.
The new `family_sensitivity_v2` all-registry selector `['*']` authorizes concrete
registry paths rather than maintaining a second parameter list. Existing sparse
grants retain their meanings; existence, effectiveness and physical admission are
still checked against each current candidate.

| Parameter category | Registered / enabled | Executable / conditional scope |
|---|---|---|
| Segment/tendon counts, consecutive spans | Yes; counts `[1,null]`, no fixed count list | Generation, finite Coordinate comparisons; topology is discrete, no continuous derivative |
| Each segment length, Young modulus | Yes; positive, no artificial upper bound | Generation, Coordinate, M0/M1 and Coupled with a Main-selected finite local interval |
| Density, bending viscosity, natural curvature | Yes; registry physical domains preserved | Generation, Coordinate materials group, effective M0/M1 and Coupled; nonnegative/positive domains retained |
| Circle/tube/ellipse/rectangle dimensions | Yes; actual section parameters | Generation, Coordinate, M0/M1 and Coupled with physical section qualification |
| Polygon vertices and holes | Yes; actual ring coordinates | Generation and registry-based local probes; simple rings/positive area required. Coordinate polygon scale does not span arbitrary polygons |
| Section angle | Yes | Conditional on anisotropy and representable station angles; rotating an isotropic section has no mechanical effect |
| Routing radius, phase, anchor/guide stations, angular offsets | Yes; original physical station bounds | Generation, Coordinate supported span representation, registry-based M0/M1/Coupled; overridden/absent route effects are marked ineffective |
| Explicit route attachment and guide-hole positions | Yes; actual body-local YZ coordinates | Generation and effective registry-based M0/M1/Coupled. Coordinate mode rejects lossy seeds with explicit route overrides |
| Each fixed payout | Yes; positive, no artificial upper bound | Generation, Coordinate, M0/M1 and Coupled; zero-state route-length initialization retained when omitted |
| Tendon diameter / force capacity | Yes | Geometry/capacity qualification, not an identified smooth force-law direction; generate and independently qualify |
| Tendon pretension / length-servo gain | Registered; not applicable | Fixed payout bypasses active pretension initialization and servo |
| Control weights | Registered; not applicable | No control effect in the frozen passive execution |
| Cell count | Registered; conditional numerical choice | Model resolution, not a physical design gradient; frozen final fidelity remains authoritative |

Every single search/analysis is finite. `parameter_bounds` in V4 questions and
Coupled blocks supplies a request-local domain for open continuous coordinates.
It must contain the current value, respect strict physical endpoints, refer only
to selected registered paths and leave the original FamilySpace unchanged.
Coordinate retains its existing finite `bounds` contract and rejects omitted
open coordinate intervals. The two search modes have different representations;
their combined availability does not imply arbitrary geometry is a Coordinate seed.

## Tools and mathematical methods

| Interface | Registered | Enabled | Executable / conditional / unavailable |
|---|---|---|---|
| `research_plan` generate/propose/diagnose/search/select/stop | Yes, `agent.py`, Plan | Yes | Original action admission, identities, receipts and evidence-read requirements |
| `research_analysis` / `mechanism_structure_v1` | Yes, `scientific_intent.py`, `structure_research.py` | Yes, explicit method grant | Conditional on owned candidate, qualified working point, legal target/paths and whole-request admission |
| `experience_retrieve`, `evidence_read` | Yes | Yes | Read safe frozen Knowledge, current Store and source-linked historical background |
| `research_recall`, `research_route`, `research_investigate` | Yes | Yes, recent-round/on-demand/role policies | Recall/navigation are read-only; investigation uses accounted Reporter requests |
| `research_opportunities` | Evidence view, not a standalone registered tool | Yes | `evidence_read` at working_set `/research_opportunities`; no invented tool |
| Reporter | Existing accounted role, `reporter.py` | Yes | Source-linked explanation before the next scientific decision; Main owns choices |
| `bounded_mixed_coordinate_v1` | FamilyMixedSearch | Yes | Finite chosen counts, groups and intervals; both passive evaluation modes |
| `bounded_coupled_block_v1` | FamilyMixedSearchV2 | Yes, `coupled_block_enabled=true` | Exactly two effective continuous registry parameters; four-point admission, matched identity, failed/skipped points and costs retained |
| M0 equilibrium, KKT, active/slack/boundary sets, constrained tangent stiffness/compliance, material-point response | Existing passive `mechanism_structure_v1` primitives | Yes | Frozen-load re-equilibration; baseline/probes must qualify. Static convergence does not establish task performance |
| M0 parameterized differentiation, bounded optimization and matched four-point interaction | Same method and differentiation router | Yes | Main chooses targets, local intervals and scientific intent; finite numerical estimates, no strict derivative/global law |
| Multi-load / matched-candidate comparison | Same method | Yes | Exact frozen loads or owned same-task candidates, matched conditions and source references |
| Complete passive finite-time M1 | Same method, `finite_time_task_violation` | Yes | Original full ten-condition protocol and initial qualification. TaskGap retains observables; a scalar violation is not the sole scientific explanation |
| Full original task evaluation | Registered passive execution and original evaluator | Yes | Complete dynamic M1 or passive task-response search; invalid/incomplete results have no comparable task score |
| Independent `physical_replay` Plan | `physical_replay.py::passive_source` / passive execution | Yes | Separate execution and acceptance; static/KKT/finite-time mathematics cannot replace it |
| Active T1/T2, Conic input optimization, NMPC, PPO/RL | Registered elsewhere | Not applicable here | They optimize active legal tension/control sequences; frozen payout has no such control input. Missing cvxpy is irrelevant to the enabled passive method |
| M2 consistently reoptimized / M3 closed-loop interaction | No passive backend | Unavailable | No passive reoptimization or closed-loop interaction adapter; not advertised as executed |
| Generic active-trajectory BDF / offline NLP | Existing active interfaces | Not applicable here | No registered full passive original-task verification route; cannot substitute for passive Replay |
| Axial extension, shear, torsion, friction, full swept self-collision | Unsupported physics | Unavailable | Current serial bending / frictionless / checked-pose route model does not implement these capabilities |

All eight existing search groups are granted: segment_count, tendon_count,
spans, lengths, materials, sections, routing, payout. Final task acceptance
remains independent of method convergence and search ranking.

## Knowledge and costs

All 72 safe registered Knowledge revisions are frozen and discoverable, including
the requested PHS procedures, six Skills, mechanism process, routing@2 and
material-inertia@2. Only the explicitly stale General Knowledge references in
parameter-model@3 and local-to-experiment@3 and their index entries are corrected;
earlier revisions remain. Theory, historical observations and current experimental
evidence retain distinct evidence levels. Benchmark answers remain excluded.

Provider: initial 24 shared requests including four protected requests; usage and
tokens recorded. Existing extension policy allows progress-based 12/24 additions
at settled request/Worker/Reporter boundaries, with preserved history and no
Study-wide ceiling. The initial 24 are not an automatic scientific STOP rule.
Main cannot extend its own allocation.

Mathematical evaluations, cumulative analysis seconds, physical launches,
public operations and Replay limit are null (usage-based, not zero or free).
Per-worker watchdogs: mathematics 7200 s; physics 1800 s. Per-search proposal
and evaluation ceilings 256 are engineering batch limits only. Receipts retain
actual attempts, failures, skips, charged units, numerical seconds and available
episode/integration-step counts; reservations are not physical execution counts.
Unobserved costs remain unknown. NMPC/RL/offline-NLP/BDF allocations are zero.

## Necessary preflight

Four focused offline checks passed: actual registry/discovery/grant coverage;
request-local interval validation and admission of both passive Coupled modes;
Coordinate admission plus actual V4 Schema; exact original task/knowledge/budget
and independent new-Store state. No synthetic four-point numerical tests or SDK
cross-task tests were repeated. No full suite, Provider call, equilibrium or
physical Worker was used in these checks. Environment/import/interpreter/thread
admission is ready with the configured research Python and MuJoCo backend.

Launch uses existing prepare/bind/Harness/Store admission. The supervisor must
verify zero candidates, Plans, analyses, requests and occupied reservations at
creation, then let Main choose freely. Initial live decisions, tool registry,
Worker starts and costs must be read from the new Store and its local
`preflight.json` / `startup-summary.json`; configuration alone is not a live result.
