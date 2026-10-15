# Runtime and module ownership

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
| `design.py` | Physical candidate construction, compiler validation, source identity and immutable provenance. |
| `search.py` | Coordinate proposal (absorbed its sole helper), frozen task ranking limits and immediate internal-batch stop on pass. |
| `feedback.py` | Evidence/solution identity, exact read/selection, task-derived holding window, truthful confirmation and result facts. |
| `diagnostic.py` | Existing exact-problem replay plus core's read-only/contained diagnostic orchestration; task-derived thresholds and finite solve counts/iterations. |
| `analysis.py`, `mechanics.py`, their workers | Candidate-bound mathematical protocols and optional solve/replay routes, with finite allowances and disabled time plumbing. Mathematical evidence never grants task success. |
| `numerics.py` / `experience.py` | Retained exact historical artifact/state imports and evidence-backed experience. Reads do not repeat computation. |
| `tools/research_tasks.py` | Shared task acceptance meaning, holding-window bounds and ranking normalization. |
| `tools/platform_host.py` / `platform_store.py` | Transactional receipts and actual numeric costs; null limits disable elapsed-time rejection while count checks remain. |
| `tools/service_execution.py` | Existing contained process ownership and tree termination; `None` means unbounded wait. |
| `tools/platform_tools.py`, `execution_completion.py` | Retained scientific dispatch and sealed complete/incomplete stages. Optional timeout passes to backend without a sentinel. |
| `platform_registry.py` / family `manifest.py` | Registry and source identities; sole hash helper absorbed, obsolete service dependency branch removed, sources grouped by real responsibilities. |
| family `backends.py`, `gvs_reporting.py` | Null timeout reaches MuJoCo loop; repaired report construction retained and expanded for review. Saved-observation verification runs no solver. |
| GVS/NMPC/IPOPT/compiler/section/routing kernels | Retained physical horizons, finite iterations, solver/feasibility/numerical meanings and extension boundaries. |

Deleted only `tools/rl/config.json` (competing defaults), `tools/optimization_interfaces.py` (sole coordinate helper merged into search), and `tools/artifact_tools.py` (sole hash helper merged into registry). `file_lock.py`, `paths.py`, schemas and numerical capabilities with real callers remain. The [caller audit](../../evidence/research_count_20261015/caller_audit.json) and final module inventory record actual moves and line changes; estimates did not determine the diff. Inline statement expansion was verified to preserve the AST and comments.

Physical source remains `robot.json`: independently addressed segment lengths, section dimensions and continuous/named modulus changes use existing compiler/routing/initializer checks. Total length is derived unless explicitly constrained; routes never scale implicitly. Density, viscosity, station coordinates/angles, tendon and segment counts remain fixed. Speed-cost weights are control penalties, not acceptance conditions. A normalized held-input Gramian is local authority, not damping, unilateral-tension feasibility or task holding. Saved-state calculations retain exact robot, update, previous applied input and remaining physical task time.

Historical evidence retains original content and bindings, including the sealed nominal holding-speed failure and pre-training RL boot failure. Engineering and scientific ledgers are separate. A new profile or code repair cannot rewrite historical receipts or silently reset/increase current counters. Implementation migration requires a committed reason and keeps frozen study configuration unchanged.

Next extension boundary: explicit variable tendon start/guide/anchor routes with candidate-specific ownership/channel-order validation, then variable segment count and conditional continuous optimization. Neither is implemented in this cleanup. Current continuation intentionally cannot transfer weights or residual references across those changes.
