# Research Mainline 3, Version 1

Engineering delivery, 2026-10-07, on `feat/gvs-dynamics`. New provider/model requests and scientific executions in this round: **zero**. Mainline 1/2 historical results, STOP, later promotion, task definitions and dependency seals remain historical evidence. Full empirical acceptance of Mainline 3 is pending.

## Public scope

| Entry | Implemented scope |
| --- | --- |
| `research.capabilities@1.0.0` / `research_capabilities.effective_capabilities` | Registry and builder declarations supply purpose, contracts, units/domains, representation, public integration, compatibility, activity permission, resource availability, evidence scope and distinct reasons. Invocation-specific analysis bindings remain required. |
| `candidate.family@1.2.0` | Existing structural/control variables plus independent segment-owned `design/near_routing_radius_scale` and `design/far_routing_radius_scale`. Any permitted joint subset is selectable. |
| `controller.gvs_nmpc@9.0.0` | New reach routing envelope; inherits v7 deadline horizon, solver stopping rules, feasibility thresholds and measured-state regeneration. v8 remains experimental and separate. |
| `research.prepare_candidate@1.0.0` / `research_execution` | Actual mutation, compiler/compatibility checks, candidate/content identity, saved configuration and simulation request construction; shared with fixed workflows and existing public simulation preflight. Construction does not execute its request. |
| `analysis.linearize_configuration@1.0.0` | Existing candidate-local algorithm on an owned prepared configuration, with exact content identity, task/model/basis/input order, initializer, protocol and working-point binding. Scientific working-point construction is explicitly a computation boundary. Reach only. |
| Existing `analysis.control_metrics@2.0.0`, `analysis.bounded_endpoint@1.0.0`, coordinate/explicit searches | Shared discovery and Host dispatch. Algorithms retain their interfaces and limits. Exact historical reads check binding, protocol and upstream references. Routing changes invalidate old scientific results. Explicit enumeration and coordinate search do not imply arbitrary optimizer support. |
| `research.investigate`, `research.investigation_status`, `research.investigation_read`, `research.investigation_disposition` | Principal handling, direct investigator assignment, or temporary coordinator with investigator children. Uses `platform_workers.Coordinator`, existing Store reservations, bounded evidence pages, context assembly and complete-request checks. |

The scheduler now calls versioned task compatibility instead of assuming every research controller must be v7. Existing reach and time-reference tracking adapters/evaluators retain separate semantics. Tracking v5 has a length-only mutation envelope; changed routing is rejected. Controller selection, controller-objective search and online input solving remain distinct. Restoring research evidence never resumes a partially integrated trajectory.

Capability and investigation pools are frozen within running activities by dependency snapshots and a checked investigation-grant identity. Catalog declarations cannot create authority. Host retains dispatch checks, current ledger capacity, task ownership, failures and receipts. New general principals may advertise these public tools directly; the old specialized `research.decide` protocol is not a mandatory ordering policy. Mathematical analysis, direct search, diagnosis, re-evaluation and stopping remain independently grantable choices.

## Geometry and family coverage

Routing scale is dimensionless and absolute relative to immutable `semantic_source`: `[x,y,z]` becomes `[x,scale*y,scale*z]`. Station fraction, longitudinal offset, quaternion and angular/relative layout remain fixed. Each flexible location is owned by its physical segment, regardless of tendon name. Fixed-base points belong to the root flexible segment. Rigid guide/attachment locations belong to the closest upstream flexible ancestor. Thus **all** mid-guide holes, including distal-tendon holes, have proximal ownership. Flexible terminal anchors belong to their attachment segment. Shared named holes transform once. Repeated edits use the source, so they do not compound scales.

Hole diameter, backbone section dimensions and actuator drum radius are separate quantities. Positive-scale bounds derive from actual rigid envelope clearance and strict hole separation; the implementation uses an open upper bound for clearance. The entire candidate still passes compiler topology, transmission, tendon-diameter and span checks. No universal radial range or backbone-containment constraint is invented. Flexible routing may be exterior to the section in the underlying model. The illustrative `[0.98,1.02]` range is a proposed small activity domain, not a universal capability bound. An unbounded geometric side is represented as `null`, not as a guessed physical limit.

Candidate facts include actual changed routing coordinates. Routing changes rebuild physical/backend identities, tendon lengths/derivatives and force mappings, reduced geometry, controller graph and numerical preparation. Input ordering remains tied to actual tendon/entity IDs. Compatible historical tensions remain bounded numerical guesses; historical states, equilibria, plans, trajectories, evaluations and local analyses cannot be rebound to a changed candidate.

| Coverage | Engineering reason |
| --- | --- |
| Version 1 | Segment lengths, independent uniform section/material scenarios, supported speed-cost weights and fixed-topology radial routing. Current near/far declarations describe the existing two-segment family; routing ownership itself follows actual component IDs. |
| Version 2 | Finite tendon-count/layout and segment-count choices need topology-aware initialization, remeshing, actuator/force mappings, input-order and controller-dimension reconstruction. |
| Later gaps | Natural curvature needs preload-consistent initialization; payload properties need consistent mass/COM/inertia mapping; further section/material properties need coupled physical declarations and controller preparation. |
| Absent physics | Shear, axial stretch, torsion, tendon friction, rope elasticity, motor dynamics and self-collision remain omitted by the serial bending model. |

## Investigations and recovery

Every node binds its question, source/query scope, read-only tools, return contract, one-model-call budget, timeout and stopping conditions. A child must be explicitly proposed by its coordinator and remain within root, parent and per-node permissions/budgets. Investigators cannot delegate. The grant sets total count, concurrency and cumulative resources; SQLite `BEGIN IMMEDIATE` checks scope/count and reserves through the common ledger atomically. Reservations and settlement are counted once; coordination creates no quota.

Version 1 uses **one bounded response per node**, with independently prefetched scoped evidence pages; it does not offer an interactive child tool loop. Facts and counterevidence must match original source values and pages actually made visible to that role. Returns also carry unknowns, interpretation and suggested checks, with a 16 KiB cap. Suggestions do not execute anything. New computation uses ordinary shared Host tools and their own bindings/grants. A principal's disposition requires independently recorded source inspection; a child's source access is not principal inspection.

States distinguish pending, running, unconfirmed, confirmed failed and completed. Active local requests remain running. Recovery first checks the original request identity, sealed receipt, saved validated response and ledger. Saved completed responses settle without redispatch. Unreturned requests become unconfirmed, retain reservations and receive no automatic retry or release. Frozen grants, request collisions and concurrency ceilings survive recovery.

The future interface scenario has two distinct saved-evidence questions (reach/settling and complete-update timing), then bounded principal synthesis with independent original-source inspection. Direct and coordinator-mediated modes are engineered interface tests, not physics acceptance or causal studies.

## Offline verification and evidence

Compact evidence: [offline_verification.json](../evidence/research_mainline3_v1_20261007/offline_verification.json). Checks used isolated stores and authority anchors; no real activity grant or archive was changed. Provider transport, backend solves, optimization, equilibrium fitting and integration were blocked in the new suite.

- Eight new focused cases pass after affected reruns: actual independent routing and source-relative repeat edits; cross-segment ownership and coupled bounds; historical-v7 rejection; actual static derivatives and input ordering; actual MJCF/MuJoCo model compilation; actual candidate numerical guesses, public numerical-import hook with artifact persistence, and symbolic controller/analysis graphs; public discovery/request/binding paths and tracking separation; direct/coordinated investigations, permission narrowing, atomic sibling budgets, bounded native returns, independent principal reads, and completed/unconfirmed recovery.
- The integrated case crosses discovery, real candidate preparation, real mathematical binding with only the scientific preparation function substituted, fixed mathematical/simulation/evaluation orchestration with explicit substitutes, saved-evidence retrieval, investigator return and principal disposition.
- Final affected rerun: numerical/symbolic preparation and integrated discovery/orchestration cases both pass, including future interface commands reporting rejected dispatch or synthesis without treating them as completed handoffs.
- Existing focused catalog checks: three pass; the existing `test_registered_pool_flows_through_shared_plan_and_batch` fixture remains limited by its missing `project_id` in `batch_budget.operational_view`. Its historical dependency seals and fixture have not been bypassed or rewritten. Five existing fixed-workflow checks pass.
- The saved Stage 3.35 linearization envelope was read from the Stage 3.36 Store and checked for exact binding/protocol/upstream identity. This is historical evidence, not a new calculation. The saved Stage 3.36 free-reach facts used in diagnostic fixtures still report failure.

Actual engineering construction established 48 backend coordinates, 12 reduced coordinates, six ordered tendon inputs, a `(6,48)` static tendon-length Jacobian, and 240 symbolic shooting constraints at the preserved ten-step horizon. No graph evaluation to generate new scientific analysis, trajectory integration, working-point equilibrium construction or optimizer/controller solve was performed. Numerical preparation contains placeholders and compatible historical tension guesses; it does not establish dynamically feasible warm states. Those require implicit trajectory regeneration during execution. The existing mathematical working-point routine uses equilibrium/inverse construction, so its actual scientific preparation remains pending; the substitute is explicitly labelled and supplies no scientific result.

There is no remaining identified implementation blocker for the delivered engineering scope. Changed-radius closed-loop outcomes, actual scientific mathematical preparation and live provider diagnostic handoffs remain unvalidated. The earlier scheduler fixture limitation remains a verification limitation. Empirical acceptance and real-time feasibility are not claimed.

## Future commands and proposed budgets

Preparation only (authorized in this round):

```powershell
conda run -n softagent python -m tools.research_mainline3 --prepare runs/mainline3_v1_prepared_20261007/future_request.json
```

The following commands require **separate operator-issued ProjectConfig grant files**, unique grant IDs and new output directories. The grant files do not exist as active authorization in this delivery. The runner freezes a new session and never reopens archived work.

```powershell
conda run -n softagent python -m tools.research_mainline3 --execute-grant grants/mainline3-fixed-approved.json --mode fixed --directory runs/mainline3_fixed_validation_new
conda run -n softagent python -m tools.research_mainline3 --execute-grant grants/mainline3-direct-approved.json --mode direct --directory runs/mainline3_direct_interface_new
conda run -n softagent python -m tools.research_mainline3 --execute-grant grants/mainline3-coordinated-approved.json --mode coordinated --directory runs/mainline3_coordinated_interface_new
```

| Separate proposal | Provider calls | Mathematical computations | Backend attempts | Tool calls / wall ceiling | Correction allowance |
| --- | ---: | --- | ---: | --- | --- |
| One joint near +1% / far -1% radius case | 0 | One existing candidate-local preparation/linearization (including its bounded working-point attempts), one metrics call, one endpoint call | 1 | 7 / 4,000 s | 0 automatic retries; any corrective execution needs its own grant |
| Direct questions + principal synthesis | 3 | 0 | 0 | 8 / 900 s; node timeout <=180 s, concurrency <=2 | 0 retries |
| Coordinator + two questions + principal synthesis | 4 | 0 | 0 | 10 / 1,200 s; node timeout <=180 s, concurrency <=2 | 0 retries |

All proposed grants have zero worker-process calls. The mathematical allocation is a count of public operations plus their existing bounded internal working-point attempts, not a claim that each tool performs only one numerical solve. These small shared cases cover multiple connections; they are not an exhaustive combination campaign.

Before publication the entire `origin/feat/gvs-dynamics..HEAD` range must be inspected. Unrelated unpublished commits would block pushing; they must remain intact. Publication status and delivered commit are reported separately after that check.
