# Runtime and module ownership

Current V2 ownership and final engineering checks are in [harness_v2.md](harness_v2.md).
Provider transport/credentials belong to provider.py; bounded evidence reads belong
to core.py; SDK storage and snapshot paths belong to session_handoff.py. The CLI
default is the pending no-reasoning V2 configuration. Older entries below describe
their historical frozen versions.


## Codesign integration (2026-10-23)

The current baseline is [mainline/softarm-codesign](softarm_codesign_mainline.md).
`tools/state_io.effective_input` extracts saved envelopes without heavy imports;
`config.effective_input` keeps the historical import as an alias. `config.resolve`
alone composes new source configurations. Existing studies consume frozen inputs.
`research_tasks` owns derived conditions, mathematical/evaluator bindings and
execution requirements. `task_constraints`, `analysis` and `search` consume those
views, preserve method coverage and account for actual internal solver costs.
`generated_serial.checked_control(execution=False)` prepares mathematical inputs
without physical admission; its default execution mode retains route checks.
`gvs_profile` exposes thin compatibility aliases and one numerical preparation.
`scene.assemble_physical` owns task-independent physics; `scene.assemble` binds
control references. Backend measurements and registered evaluators remain separate.

## S5.5 and S5-T preparation (2026-10-17)

`feedback.py` compares effective experiment configurations before expensive
reservations and exposes saved direct/residual PPO numerical-failure facts.
`sr_diagnose.m` and `sorosim_codesign.refine_fixed_sequence` own the bounded
fixed-input implicit integration route; `mechanics.py` settles it through the
existing Store and mathematical replay allowance. `sr_codesign.m` now accepts
verified full-state warm starts for `task_capability` and removes exact
duplicate optimization inequalities while retaining all original predicates
in independent task reporting. `core.packet` exposes compact refinement and
raw KKT fields. See [S5.5 and S5-T delivery](sorosim_s55_s5t_delivery.md)
for actual execution status and limitations.

`tools/research/matched_state.py` owns the three bounded S5-A checkpoint
reconstructions and same-input, single-interval comparisons. It verifies
every reconstructed MuJoCo sample against the original archive, recovers
warmstart through the original prefix playback, projects through the existing
GVS map, and calls the existing SoRoSim fixed-sequence diagnostic at two
resolutions. The usual Host Store and research packet own its budget,
receipt, recovery and Agent evidence pointer.

## SoRoSim S4.5–S5 additions (2026-10-16)

`matlab/sorosim_control/sr_codesign.m` now owns the original sampled task
violation epigraph, exact cross-design replay, and raw full-NLP multiplier/KKT
diagnostics. `sr_trajectory_outputs.m` converts saved mathematical states to
world tip position/velocity without dynamics reintegration. The existing
`sorosim_codesign.calculate` and `mechanics.dispatch` retain MATLAB Session,
candidate binding, complete-solve and replay settlement.

`extensions/tendon_family/backends.playback_tensions` applies an exact fixed
SI tension schedule in the existing candidate MuJoCo compiler. The narrow
`tools/research/physical_replay.py` reserves one backend launch, validates
candidate/model/task/order/grid, settles the task-derived sample grid, and calls the
task's registered evaluator plus shared acceptance assembler. `core.packet` and
`state.readable_results` expose the result through the original Store.

`tools/research/rl.py` admits a sealed same-candidate mathematical tension
sequence as an existing residual PPO reference. Its configured action caps
are enforced at stage admission. `core.packet.stage_context` presents compact
P1–P5 source summaries and Store pointers for the live Agent; no second Agent
or evidence system was added. The stage outcomes and limitations are in
[S4.5–S5 delivery](sorosim_s45_s5_delivery.md).

`CLI prepare → config.resolve → Store frozen study → bind → agent/typed dispatch → candidate → contained backend or owned RL worker → settlement → immutable evidence read → exact selection / STOP → export`.

| Module | Final responsibility and important calls |
|---|---|
| `tools/research/__main__.py` | Sole public CLI. Preparation resolves sources; existing commands require run ID. |
| `config.py` | Sole reference composition, recursive sparse patching, effective validation, provenance/identity and declared profile resolution. |
| `state.py` | Store state/evidence and implementation hashes; shared execution guards. No mutable configuration loader. |
| `budget.py` (added) | Count admission, protected closeout, durable training-stage count, usage presentation, common fresh-pass gate and explicit engineering closure. Uses the existing ledger. |
| `core.py` | Study preparation, binding/migration, native plan lifecycle, receipt recovery, selection/STOP, status/export. Execution and diagnostics were extracted. |
| `execution.py` (added) | Owned NMPC dispatch, contained process, completion packaging, exact configuration/binding and elapsed settlement; extracted from core. |
| `agent.py` | Strands/DeepSeek integration, credential loader, accounted transport, saved conversation, sequential tools, wait for terminal workers and count closeout. |
| `contracts.py` | Typed sparse requests; distinct start/resume/continue semantics. No second set of effective PPO/reward defaults or fixed saved-update upper bound. |
| `rl.py` | Frozen candidate XML/task preparation, effective stage input/lineage, stage admission, real interpreter bridge, terminal summaries and independent evaluation evidence. |
| `tools/rl/run.py` | Owned paths and process identity, atomic writes, launch/stop/status/recovery and boot failure records. Accepts complete inputs; no default file. |
| `tools/rl/train.py` | PPO sampling/optimization, finite steps, original-stage recovery, atomic checkpoint generations, measured work. |
| `tools/rl/continuation.py` (added) | Published checkpoint/hash/schedule validation, compatibility and actual optimizer/schedule/buffer reconfiguration. Preserves policy and optimizer moments. |
| `tools/rl/checks.py` / `env.py` | Independent exact-checkpoint task evaluation/replay and unchanged physical/action/observation semantics. Removed dead historical evaluation branches; env kernels retained. |
| `design.py` | Physical candidate construction, compiler validation, source identity and immutable provenance. Topology proposals require the frozen study grant and retain the source, patch, resolved order/bounds, basis, initializer and evaluation profile in the effective configuration. |
| family `generated_serial.py` | Unchanged `family.generator_space@1` / `candidate.family@3` source semantics; additive `family.topology_space@1` / `candidate.family@4` applies explicit typed Tendon/RoutePoint patches and authorized named holes, with deterministic independent actuator construction and stable channel order. Shared compiler owns physical route validation. |
| family `family_space.py` / `generated_serial.generate_family` (M3-C1) | Versioned declarative domains and conditional compact requests; independent polar routes and actuators over indexed two-segment assembly prototypes. `candidate.family@5` binds the frozen space and request. Unsupported topology is distinct from invalid geometry; candidate projection is distinct from numerical-model validation and task acceptance. See [contract and boundaries](family_space.md). |
| family `family_space.py` / `generated_serial.serial_components` (M3-C2) | Additive v2 contracts and `candidate.family@6`: one loop expands explicitly named frozen root/repeated segment, guide, connector and payload prototypes into a 1–9 serial chain. Per-segment cells and consecutive tendon spans own dimensions. Shared compiler checks remain authoritative; old generator identities remain stable. |
| `config.family_bootstrap`, `core.family_claims`, `family_space.decision_summary` (M3-C2) | Family-only defaults never read the historical robot source. A deterministic Host compatibility input stays outside the candidate pool. Claims identify generated designs without a nominal comparison. Compact exact domains link the immutable full-family Store artifact; evidence reads/recovery use existing paths. |
| `search.py` | Legacy coordinate and versioned mixed-family dispatch in one lifecycle: pending proposals, immutable scores/lineage, count admission, reuse and checkpoints; frozen task ranking and immediate stop on final pass. |
| `structure_intent.py` (G2) | Versioned scientific structure choices compile to original FamilyMixedSearch/Plan and admission. No Worker, budget or optimizer ownership. Shared control effort lives in scientific_intent.py; old interfaces retain their frozen semantics. |
| `mixed_moves.py` (M3-C3) | Pure conditional mixed-coordinate arithmetic and compact family proposals. No Host, Store, workers, budgets or evaluator. |
| `runtime_capability.py` (M3-C3) | Exact XML/environment capability binding and contained bounded load preflight through existing process ownership; native failure never establishes task failure. |
| `feedback.py` | Evidence/solution identity, exact read/selection, task-derived holding window, truthful confirmation and result facts. |
| `diagnostic.py` | Existing exact-problem replay plus core's read-only/contained diagnostic orchestration; task-derived thresholds and finite solve counts/iterations. |
| `analysis.py`, `mechanics.py`, their workers | Candidate-bound mathematical protocols and optional solve/replay routes, with finite allowances and disabled time plumbing. Mathematical evidence never grants task success. |
| `task_constraints.py`, `schemas/platform_analysis.py` (M1) | Frozen task requirements, signal/grid/input semantics, actual model applicability and explicit checked/unchecked coverage. Task adapters own task meaning; analysis binds scoped claims to exact candidate/model/protocol identities. |
| `extensions/math_analysis/trajectory.py` (M2) | Shared sampled affine sequence with exact ZOH, physical total-tension box, analytic normalized-margin Jacobian, independent recurrence witness checks and rechecked necessary-constraint exclusion. Solver failure stays inconclusive. |
| `analysis.decision_result`, `core.packet` | Deterministic small Agent entries, copied decisive replay margins and limited evidence relevance. `compact_result` retains compatible public responses; full original evidence remains in Store at exact pointers. Existing evidence paging and Strands offload own retrieval. |
| `numerics.py` / `experience.py` | Retained exact historical artifact/state imports and evidence-backed experience. Reads do not repeat computation. |
| `tools/research_tasks.py` | Shared task acceptance meaning, holding-window bounds and ranking normalization. |
| `tools/platform_host.py` / `platform_store.py` | Transactional receipts and actual numeric costs; null limits disable elapsed-time rejection while count checks remain. |
| `schemas/platform.py` | Distinct optional elapsed limits (`Budget`) and finite measured receipt/event costs (`MeasuredCost`). |
| `tools/service_execution.py` | Existing contained process ownership and tree termination; `None` means unbounded wait. |
| `tools/platform_tools.py`, `execution_completion.py` | Retained scientific dispatch and sealed complete/incomplete stages. Optional timeout passes to backend without a sentinel. |
| `platform_registry.py` / family `manifest.py` | Registry and source identities; sole hash helper absorbed, obsolete service dependency branch removed, sources grouped by real responsibilities. |
| family `backends.py`, `gvs_reporting.py` | Null timeout reaches MuJoCo loop; repaired report construction retained and expanded for review. Saved-observation verification runs no solver. |
| GVS/NMPC/IPOPT/compiler/section/routing kernels | Retained physical horizons, finite iterations, solver/feasibility/numerical meanings and extension boundaries. |

Deleted only `tools/rl/config.json` (competing defaults), `tools/optimization_interfaces.py` (sole coordinate helper merged into search), and `tools/artifact_tools.py` (sole hash helper merged into registry). `file_lock.py`, `paths.py`, schemas and numerical capabilities with real callers remain. The [caller audit](../../evidence/research_count_20261015/caller_audit.json) and final module inventory record actual moves and line changes; estimates did not determine the diff. Inline statement expansion was verified to preserve the AST and comments.

Against baseline `b0c83b860dce0c218a4302496c7f72386746bf6f`, the production/configuration/test diff is **2850 added / 1374 deleted lines**, including formatting and moved code. Separately identified relocations contain **371 original definition lines**, a subset of those totals rather than an additional change count. [Per-file decisions, before/after sizes and exact moves](../../evidence/research_count_20261015/module_inventory.json) bind to final code commit `076d89e0`; documentation/evidence-only delivery commits do not change that source comparison.

For historical reference-candidate studies, physical source remains `robot.json`: independently addressed segment lengths, section dimensions and continuous/named modulus changes use existing compiler/routing/initializer checks. Total length is derived unless explicitly constrained; routes never scale implicitly. Density, viscosity and section station coordinates/angles remain fixed. Historical studies retain their fixed tendon/segment counts; only the separate M3-A topology grant permits tendon/route changes, with two flexible segments retained. Speed-cost weights are control penalties, not acceptance conditions. A normalized held-input Gramian is local authority, not damping, unilateral-tension feasibility or task holding. Saved-state calculations retain exact robot, update, previous applied input and remaining physical task time.

Historical evidence retains original content and bindings, including the sealed nominal holding-speed failure and pre-training RL boot failure. Engineering and scientific ledgers are separate. A new profile or code repair cannot rewrite historical receipts or silently reset/increase current counters. Implementation migration requires a committed reason and keeps frozen study configuration unchanged.

Final configuration ownership removes the former `CURRENT_NMPC_STOPPING` override constant: `config.resolve` freezes normalized `ReachControl` and `MujocoParameters`; `core.prepare` uses that configuration directly, and the diagnostic helper validates an explicit patch to the recorded/frozen recipe. Solver iteration and tolerance edits therefore survive preparation. This post-closure validation correction leaves the studied default numerical settings unchanged and does not alter the scientific binding. Stage feedback separately reports verified lower/conservative upper action counts when terminal consumption is uncertain.

M3-A now implements explicitly granted variable tendon start/guide/anchor routes and candidate-specific ownership/channel-order validation. Existing physical/compiler/GVS/XML/control kernels derive dimensions from the candidate; only the control compatibility description needed its fixed-six wording removed. The two added lines in `agent.decision_packet` expose the grant that its prior fixed study-field projection would otherwise hide. Next boundaries are M3-B common-condition physical comparisons, then variable segment count and conditional optimization. Current continuation cannot transfer incompatible weights, residual references or states across topology changes.

M3-B1 reuses the registered preparation/controller/backend unchanged. The opt-in
`RealVariableTendonControl` fixture stops the existing backend before its second
command, saves one genuine update and physical interval per case, and never calls
the task evaluator. `core.export` now accepts an engineering scope with no research
decision packet, exporting its actual ledger. No controller/backend was added.

For the new study, `config.resolve` composes one same-directory, single-level task
source patch and freezes both source fingerprints. Historical sources remain
unchanged. A study without the RL capability may explicitly declare zero training
stages; the existing RL-enabled study's stage validation remains in force.
