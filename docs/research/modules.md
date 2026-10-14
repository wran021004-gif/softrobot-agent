# Runtime and module ownership

`__main__ → config.resolve → core.prepare/bind → agent.converse → native plan/analysis/RL → candidate → physical compiler → contained worker → Store settlement → evidence read → select/STOP → export`.

The implementation starts from research-chain `5cf08f8ef9323e4309dbc7206366c728ee59b3fd`. Obsolete callers are excluded from the dependency roots. The old implementations remain on that branch and in Git history. No executable legacy/archive tree or compatibility entrypoint is retained here. Required historical records remain byte-identical under their original evidence folders; only the nominal source and supplied failure JSON data were copied to `evidence/research_mainline_inputs/`.

| Module | Responsibility and important interfaces | Dependency direction |
|---|---|---|
| `__main__.py` | prepare, bind/migrate, run, status, recover, export CLI | Calls config/core/agent |
| `config.py` | `resolve`: explicit references, ownership, ceiling validation, SessionInput adaptation, nonsecret resolved identity | Shared platform/physical contracts |
| `state.py` | `state/update/save`, guards, numerical/provider capacity, hashes | Store; candidate verification imported only when needed |
| `core.py` | lifecycle, binding/migration, `dispatch`, execution settlement, status/export | Shared state, candidates, focused services |
| `agent.py` | production Strands harness, accounted `LiveBoundary`, native structured tools, session recovery, context offload, sequential mutations | Core only for orchestration calls; no pilot/example imports |
| `contracts.py` | segment-addressed Parameters, Search, AnalysisRequest, select, RL and mathematical requests | Shared typed contracts |
| `design.py` | `configuration_for/resolved_configuration/construct/verify_candidate`, physical identity | Source generator/compiler; no search persistence duplication |
| `search.py` | fixed-topology coordinate proposals, evaluator binding, sealed pending proposals, checkpoints | Candidate/analysis/execution callbacks; shared coordinate kernel |
| `analysis.py` | contained candidate mathematics, scalar semantics, explicit score window and once-only settlement | Existing GVS/CasADi/SciPy kernels |
| `feedback.py` | exact science/policy identity, result facts, fresh selection, configured confirmation progress | State/candidate/shared capacity, no core helper imports |
| `rl.py` | resolved candidate XML/configuration, bounded training, exact checkpoint evaluation | Shared RL runtime plus state; no reverse core import |
| `numerics.py` | explicitly imported historical artifact/state identity and exact previous applied input | State and candidate projection; no experimental CLI |
| `diagnostic.py` | exact serialized problem versus explicit reconstruction; retained stopping/recovery evidence | Existing trajectory/IPOPT kernels |
| `mechanics.py` / worker | fixed exact physical candidate full-horizon solve and model replay; explicit capability allocation | Existing GVS transcription/IPOPT/BDF; no old restricted length substitution |
| `experience.py` | small reference-backed case/procedure reads and dispositions | Store state and explicit index |

The existing Host/Store, execution completion, task acceptance, containment, RL machinery, physical Design/contracts/compiler/sections/geometry/routing, GVS/projection/NMPC/MuJoCo and mathematical kernels remain shared. `file_lock.py` extracts the required OS owner lock; `paths.py` extracts the shared root constant. The unused old optimizer and schema are removed; `search.py` retains its bounded coordinate proposal, pending-proposal checkpoint and evaluator accounting logic for the current fixed topology. The full old topology enumeration is retired.

`configs/research/study.json` owns topology scope, editable grants, variable/fixed choice, controller defaults, score window, budgets, confirmation policy and explicit history. `robot.json` owns physical source and discretization. `tasks/reach_hold.json` owns task/acceptance/seed. `runtime.json` owns provider, interpreter, threads, process caps and RL defaults. Derived protocol timing/lengths and controller acceptance payloads are resolved once. Controller cost scales/weights remain separate from task acceptance thresholds. The original historical controller recipe is data, not an active default.

## First-stage design space

Segment IDs are stable keys. `segments.<id>.length_m` changes one segment independently; total flexible length is derived. `length_constraint.fixed_total_m` or `aggregate_bounds_m` are optional explicit study constraints. No automatic opposite length edit or hidden 0.27 m total exists.

`segments.<id>.sections.<station_index>.<dimension>` addresses existing ellipse semi-axes and rectangular station width/height. Existing station coordinates, interpolation and section angles remain intact. Routes never scale implicitly. The established compiler derives section area/inertia, cell mass, rotational inertia, stiffness, and dependent attachment geometry. Other section kinds remain supported by the shared compiler but are not exposed/validated by this initial study.

Continuous `young_pa` requires material authority; named baseline/compliant/stiff simulation scenarios resolve to actual physical values and share the same grants. A modulus value is not a verified manufacturable material. Density and bending viscosity are fixed; independently specified material EI is not exposed. Speed-cost weights share the frozen candidate. A mathematical structure proxy rejects searches over control weights; combined design/control search requires the backend task evaluator.

Only hierarchical coordinate search is exposed. Conservative bounds are editable study choices, not universal family physics restrictions. Candidate construction validates positive physical values, identities, actual physical compiler/routing checks and named zero initialization. The fixed-candidate mathematical solve/replay route has no numerical allocation in this assignment; its output is never task acceptance.

## Evidence and lifecycle

Held-position minimum Gramian eigenvalue is a local finite-horizon position-output controllability score under declared normalization. Input is held over each control interval; it does not mean the task holding window passed. Signed incremental Gramian authority does not fully represent unilateral bounded-tension feasibility. It is not damping, decay, global feasibility or structural improvement. The score window is explicit in the request/protocol and objective identity. Equilibrium residuals describe a bounded local construction. Saved-state analysis retains exact robot/execution/update/projection and previous applied input, using actual remaining time; no transfer to changed robots is supported. GVS estimates and measured MuJoCo motion remain distinct.

`select` requires exact completed, passing, fresh current-study backend evaluation and explicit evidence read. It freezes effective science and evaluated policy bytes. Zero extra repetitions seal immediately: `task_passed=true`, `confirmation_status=not_required`, `reproducibility_assessed=false`. Positive counts use the configured policy, retain failed/invalid confirmation history by science/policy identity, and permit revision only after a genuinely changed fresh passing solution. No hardcoded two-repetition rule exists. RL always requires independent evaluation of its usable exact checkpoint before selection.

Four protected sends are inside the total 24; 600 closeout seconds are inside the live 14,400. Independent RL evaluation has an explicit 120-second hard process cap, also bounded by remaining cumulative numerical/activity time. All mathematical attempts (including failed preflight), search internals, diagnostics and incomplete backend attempts share the study ledger. Code-only lifecycle tests are separate and launch no scientific solves.

## Migration inventory and next boundary

The exhaustive [module inventory](../../evidence/research_mainline_20261015/module_inventory.json) records each affected script's previous/new paths, keep/split/merge/delete/add/modify decision, public interfaces, incoming/outgoing dependencies, before/after physical lines, substantive additions/deletions and exact detected relocated definitions. The [deletion audit](../../evidence/research_mainline_20261015/deletion_audit.json) records exact removed paths and their preserved source-branch Git blobs. Acceptance inspects the Git-controlled file inventory, not just entrypoint imports.

Next: variable tendon count with explicit start/guide/anchor routes across segment identities, validating guide ownership and channel order for every candidate. Then: variable segment count and conditional continuous optimization. Neither is currently connected by the research interface.
