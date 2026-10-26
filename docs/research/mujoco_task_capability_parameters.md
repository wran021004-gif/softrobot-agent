# A1/A2/A3 implementation audit

Base: `c153e1731ae0925e756467f75a783b28abce2873`. Reference: `ae3f94f272518fa17fe81d10cea9a61d6a67652b`.

Plan: A1 selectively integrate native T1/T2 using existing analysis/worker/Store; A2 derive executable parameters and legal comparison directions from FamilySpace; A3 expose bounded decision evidence and a reproducible offline example. No sealed Study/configuration/evidence will be changed.

Validation uses targeted offline contracts and capped engineering smoke checks only. No provider, Agent Study, PPO, or broad structural scans.

A1: selected seven integration files plus nonlinear interpretation kernel/test from reference; unrelated Agent changes, Study configurations and historical evidence excluded. Old methods remain unauthorized. Existing `.f3-prestudy-env` supplies all dependencies. Initial regression exposed two pre-existing test assumptions: exact floating solver coefficient equality (differences <1e-15) and the baseline ResultCard's additive scientific interpretation. Corrected assertions without changing solver or reporting semantics; the original reporting failure was reproduced using the sealed baseline analysis functions.

A2: candidate-specific capability rows now include actual inherited values, units, domain sources, physical ownership, continuous eligibility and restrictions. New `family_sensitivity_v2` retains the same `variables` grant and adds token-scoped `*` selectors; selectors authorize only paths that exist in the current candidate. Physical bounds are never copied into the grant. V1 authorization and sparse normalization remain unchanged.

`nonlinear_response_v2` is an additive request form: explicit directions share one baseline T1; `variables` gives dp/ds, `coordinates=[0,-h,h]` defines the legal one-dimensional path, and `coordinate_unit` makes mixed-unit coefficients explicit. `finite_comparison` uses named comparison variables with no derivative coordinate. Topology-dependent segment/span choices are disclosed as multi-factor contrasts. No Cartesian product is constructed.

Targeted A2 validation: 22 tests passed (new dynamic parameter tests, original T1/T2, original FamilySpace sensitivity). Real candidate rebuilds cover 14 material/length/section/physical/routing/input-bound edits; all checks are offline and use synthetic T1 fixtures explicitly labeled as such.


## Parameter coverage

All paths are resolved from the current request and frozen FamilySpace, then checked by the original generator; the table is a summary, not a parameter configuration. Actual values, units, bounds, affected components, authorization and reasons are available through `evidence_read(reference=candidate, view="capabilities")`.

| Current FamilySpace parameter | Analysis | Conditions / limitations |
| --- | --- | --- |
| Each selected segment length and Young modulus | Continuous fixed-input and reoptimized responses | Legal rebuilt candidate; fixed task, source, mesh and search conditions |
| Current section dimensions (circle, tube, ellipse, rectangle when granted) | Continuous | Uses selected section kind and station dimensions, including clearance / ordered geometry checks |
| Density, two bending viscosities, two natural curvatures | Continuous when the frozen physical domain exists | Inherit actual prototype values; no new material catalog or undeclared physics |
| Section rotation | Conditional continuous | Anisotropic bending section and representable uniform station rotation; isotropic rotation is not applicable |
| Span radius, phase, individual guide stations, anchor station | Conditional continuous | Actual spans/guide indices only; route overrides can shadow parameters |
| Per-tendon angular offsets, guide/anchor angle offsets | Conditional continuous | Existing affected route/guide holes; a retained generated guide hole can still depend on polar parameters despite an override |
| Explicit route override station `s` | Conditional continuous | Existing segment attachment only; original radial, order and clearance validators still own legality |
| Tendon force limit | Conditional continuous / finite contrast | Changes the legal input set; each initial and optimized schedule must remain legal |
| Segment/tendon counts, section kind, routing topology / route objects | Finite contrast; no ordinary derivative | Own legal channels/initial states; disclose dependent topology choices and multi-factor scope |
| Mesh cells | Numerical finite comparison only | Numerical resolution is not a physical structural gradient |
| Tendon diameter | Not applicable to native task sensitivity | Geometry/clearance and visualization only; no native tendon inertia/friction effect |
| Length-servo gain | Not applicable | Ideal tension bypasses the servo |
| Pretension and controller weights | Initialization/control analysis, not a structure gradient | A common absolute-tension sequence supersedes pretension; weights belong to controller performance |
| Missing topology paths, absent physical domains, fully shadowed or inactive routes | Not applicable | No fabricated zero derivative |

The retained one-segment/three-tendon S7 engineering candidate exposes 35 directory rows and 20 conditional continuous paths. This is a candidate-specific count, not a global fixed list. More segments, sections, spans or explicit override points expand only their actual existing paths. Arbitrary explicit route Y/Z coordinates do not acquire invented rectangular bounds; compare legal route objects or use the generator's polar coordinates instead.

## Unified evidence and verified example

A1 `23711071a` and A2 `a654a7b4f` were ordinarily pushed to `feat/mujoco-task-capability-parameters`; A3 is the final implementation commit. No existing configuration or evidence path was edited. The optimizer, rollout, candidate generator, Store, Reporter, budget owners, analysis protocol and independent evaluator remain the original implementations. New methods require frozen `mathematical_methods` grants and actual paths require `family_sensitivity_variables`; old Studies are never upgraded automatically.

`nonlinear_response_v2` adds source-linked observations, metric matrices, explicit dp/ds coefficients, legal domains, physical changes, worst constraint/time, own initial state, actual search settings/stops, saturation, costs and original charges. Its unique T1 cost index is informational: those computations were already charged. T2 charges one aggregation evaluation plus actual worker and preparation wall time; native model builds/rollouts/integrations remain zero. Partial native callbacks now publish confirmed model/rollout/integration costs durably before failure; their original mathematical attempt remains charged.

The existing `mathematical_capabilities` view exposes admitted `ready_requests` and a common-baseline `batch_request`. `AnalysisRequest` / `research_analysis`, the normal Worker and Store process them. `ResultCard`, `mathematical_decision_view` and Reporter use bounded projections (at most four direction summaries); matrices, all input sequences and complete rollouts stay in Store. The query itself supplies the exact L1/L2 pointer.

Retained real engineering evidence: [`example.json`](../../evidence/mujoco_task_capability_parameters_smoke/example.json), with the original immutable Store export beside it. The original `tools.research.numerics.archived(folder, reference)` reads and hash-verifies every archived source; `exact_l1_query` records the evidence-read request tested against the live Store. This is an engineering smoke check, not a new formal research Study.

Five candidate T1 searches used at most three callbacks each: **15 real rollouts, 2,625 MuJoCo steps, 5 native models**. T2 used **zero new integrations**, referenced five original T1 costs, and reused its completed result without another charge. The original numerical ledger records 6 mathematical evaluations and about 8.04 s including setup/initialization; T2 preparation was 0.252 s and its worker 0.929 s. No Provider, NMPC, PPO or independent physical evaluator ran. Young-modulus and tendon-radius directions share the same baseline/task/input sequence. Radius fixed-control and reoptimized secants even have different signs in this finite search; neither is a proven design gradient. Both directions remain unresolved at the iteration cap / practical discrimination threshold.

The initial two-segment smoke encountered the native contact-free restriction. A later numerical run completed but exposed an invalid additive ResourceUse time label, fixed to the existing contract. Early unsealed unittest fixtures were cleaned before the durable export point; exact step counts for those temporary attempts are unavailable. They are explicitly bounded, never recorded as zero: the complete engineering-debug upper bound is **14,525 steps**, below the announced 14,700-step ceiling. The retained failed Store export and [`audit.json`](../../evidence/mujoco_task_capability_parameters_smoke/audit.json) preserve the available receipts, charges, limitations and conservative bounds. No sealed scientific failure was removed or rewritten.

Validation: 44 broad targeted regression cases passed (one explicitly gated smoke skipped), then 28 final targeted cases passed (one skipped); the real capped smoke passed separately. New tests cover material/routing/section rebuilds, physical eligibility, shared baselines, coupled paths, discrete channel/section changes, model/control/initialization mismatches, original read pointers, failure costs and idempotent reuse. The original CLARABEL numerical-accuracy warning remains a diagnostic; no stronger mathematical claim is inferred.

Native support remains Reach/Hold through the original task adapter and requires contact-free unconstrained ideal-tension physics. No continuous-time certificate, global optimum, rigorous derivative/error bound, hardware claim, independent task pass or GVS/MuJoCo agreement is established. No final structure is selected.
