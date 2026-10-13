The code integration is implemented and focused checks pass. The scientific milestone remains incomplete: Phase A's real training succeeded, but its one independent evaluation failed in result packaging; Phase B was correctly withheld and no solution was selected or confirmed.

`378b106d30fdb94dd3696fe484997a66ba7c7c8e` was committed and bound before live research. The subsequent local reporting repair did not grant a second training run or evaluation, modify the closed ledger, or replace the model's original decision. Delivery uses `feat/rl-control-pilot`; the final pushed SHA is reported with the delivery.

Changed responsibilities:

- `research_core_mechanics.py`: existing constructor handoff retains mathematical source, objective, trajectory, relaxation and feasibility; it launches and selects no controller.
- `research_core_rl.py`: declared capabilities, owned compatible existing-format references, per-trial/cumulative allocations, formal reconciliation, evaluation reservations and exact checkpoint confirmation through the existing runtime.
- `research_core_feedback.py`: one common result view reads original acceptance/metrics and exposes route, completeness, failure stage, costs and provenance; unavailable evaluation stays unmeasured.
- `research_core.py`: formal RL preparation, declared tools/dispatch/instructions, route-aware selection, configured confirmation count, separate four-NMPC allowance, original-task Phase A dependency and existing-evidence timing admission before NMPC.
- `schemas/research_core.py`: positive finite generic allocations, study-enforced ceilings and either-route selected result reference.
- Existing runtime files received only local failure-stage/file-identity additions and the discovered missing `json` import repair. Mathematical solvers, NMPC, GVS and the RL environment/training algorithms were not rewritten. Successful future workers retain their last known stage separately from actual failure stage.

Phase A reused d=0.5, lengths 0.16275/0.10725 m and the identical XML SHA256 (`phase_A_parity.json`). The original task remained target [0.29,0.035,0.19] m, zero named state, 0.35 s, 0.01 s control period, 0.0005 s physics step, inclusive holding samples 30-35, limits 0.01 m/0.02 m/s. Current serialization explicitly names the existing 0.01 m terminal fallback. PPO/reward settings matched the historical selection: rollout 128, batch 64, four epochs, learning rate .0005, gamma .99, holding-speed reward 2.

The real configured DeepSeek/Strands model launched direct RL, queried terminal status, dispatched evaluation, explicitly read its immutable failure evidence and chose `diagnose` in native STOP. Original requests, tool feedback, evidence reads and decision are preserved. The one training run attempted 1024 actions, completed 1002 physical transitions and attempted 20251 physical steps; it recorded 15 completed and 22 failed training episodes. It completed eight rollout optimizations, 32 epochs and 64 optimizer steps in 4.3372795 active seconds, with no active-time overrun. Checkpoint `step-00001024-5c37317d` exists; file digest and optimizer/schedule identities are in `phase_A/runtime_artifacts.json`. This repairs the previously missing live sampling/optimization/checkpoint evidence, without claiming a new configuration search.

The single independent evaluation reached physical stepping, emitted a MuJoCo QVEL instability warning at simulation time .2205 s, saved a partial trajectory, then raised `NameError: json is not defined` while packaging the result in `checks.py`. Its episode remains charged, with uncertain physical cost and no complete acceptance metrics. No task metrics were reconstructed from the trajectory and no second episode was run. The missing import is fixed; a frozen-policy packaging fixture and 29 existing runtime checks pass without real training or evaluation. The warning's root cause remains unresolved. Original unavailable-evaluation evidence is unchanged; factual corrections to stale last-stage/model interpretations are separate in `factual_corrections.json`.

Phase A is therefore not complete. Its one evaluation episode is exhausted. Phase B requires a complete Phase A independent saved-policy evaluation and was not started: zero mathematical attempts/objectives, zero formal candidate/controller trials, zero NMPC executions, zero diagnostics and zero confirmations. No robot/controller solution is selected and task performance remains unmeasured. Phase B's additional budget is unused; it was not borrowed to retry Phase A. The code exposes the required objective options and control routes, but no autonomous formal study or confirmed task success is claimed.

NMPC admission uses only existing timing bound to the exact scientific configuration, checks the 1800-second cap, shared remaining phase time and configured confirmation reserve. Missing/mismatched/oversized evidence produces route unavailability within budget and retains RL as a permitted alternative; it never establishes design infeasibility. The historical 4758/4858-second estimate belongs to a different recipe and was not transferred. No calibration, timeout-only launch or ceiling increase occurred.

| Consumption | Historical closed study | Phase A | Phase B | Combined |
|---|---:|---:|---:|---:|
| Provider requests | 23 | 8 | 0 | 31 |
| Public operations | 23 | 9 | 0 | 32 |
| Training runs | 1 failed before sampling | 1 | 0 | 2 |
| Attempted training actions | 0 | 1024 | 0 | 1024 |
| Active training seconds charged | 90 conservative | 4.3372795 actual | 0 | 94.3372795 |
| Evaluation episodes charged | 0 | 1 failed reporting | 0 | 1 |
| Complete evaluation results | 0 | 0 | 0 | 0 |
| Live elapsed seconds | 401.1002543 | 84.9483771 | 0 | 486.0486314 |

Phase A elapsed is derived from its original native STOP event, not later delivery time. Its 90-second allocation was not refunded to the historical study. Provider wall time, RL active time and enclosing live phase time are distinct; they are not added as overlapping consumption.

Focused verification: 32 research core/mechanics checks and 29 existing RL runtime checks passed; syntax and whitespace checks passed. Coverage includes compatible/incompatible reference identity, formal initialization, exact older-generation RL confirmation with one retained failure and no NMPC/training, configured counts/reserves, oversized allocation rejection, idempotent receipts/reconciliation, missing evaluations, existing-timing cap rejection and frozen-policy result packaging. The live 2048-action recovery campaign, full repository suite, old successful-policy evaluation, BDF campaign and physics sweeps were not repeated.

Compact nonsecret evidence is under `phase_A/`, including compressed original provider bodies, immutable artifact archive, receipts, explicit reads and original model decision. Full runtime config/XML, checkpoints, optimizer state, captures and worker log stay in `runs/rl/rl-validation-A-20261013-723ce58d`; the full state snapshot stays in `runs/rl-validation-A-20261013/delivery_artifacts/state.json`. Retrieval paths and hashes are recorded. Another physical policy evaluation requires a separate explicit allocation; this delivery contains no robustness, global optimum, superiority or numerical-root-cause claim.
