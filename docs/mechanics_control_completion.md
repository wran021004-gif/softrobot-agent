# Mechanics and control delivery, 2026-10-11

The current research core connects offline CasADi/GVS mechanics, retained trajectory evidence, candidate handoff, fixed-structure coordinate search, complete closed-loop records and native feedback decisions. Immutable configuration, fresh execution, historical evidence and cached receipt costs are explicit.

Engineering demonstration: `connected`. Native actions: propose, execute, propose, execute, stop. These activities are recorded separately.

| Execution / origin / role | d | Holding weight | Terminal weight | Holding position mm | Holding speed m/s | Joint acceptance |
|---|---:|---:|---:|---:|---:|---|
| 31eaa9f652cb / engineering / search | -0.439794 | 0.1 | 0.1 | unavailable | unavailable | execution_incomplete |
| a026efae5ce6 / engineering / search | -0.439794 | 0.1 | 0.1 | unavailable | unavailable | execution_incomplete |
| f1c1a6ba7f34 / engineering / search | -0.439794 | 0.1 | 0.1 | 3.960867 | 0.042033 | valid_failure |
| d42321543b9a / engineering / search | -0.439794 | 0.08125 | 0.1 | 3.861257 | 0.026947 | valid_failure |
| 69ee35f7343d / model / development | -0.439794 | 0.025 | 0.1 | 4.580266 | 0.065020 | valid_failure |
| c9c7cf5be05f / model / development | -0.439794 | 0.065 | 0.1 | 3.698927 | 0.049540 | valid_failure |

Mechanics solve: `converged`, charged 338.703s; original-task feasible=True, relaxed feasible=True. Returned structure: {'d': -0.43979400623619647, 'lengths_m': [0.15758113296570092, 0.11241886703429908], 'substeps': 1}. Replay gates and raw/retained selections are preserved in the archive.
Mechanics replay: `completed`, charged 193.567s; original-task feasible=None, relaxed feasible=None. Returned structure: None. Replay gates and raw/retained selections are preserved in the archive.

Independent post-selection confirmations: 0; failures: 0; limited repeat-supported acceptance: False. Improvement attribution permitted: False.

Costs: numerical 3578.923/10800s; standalone local solves 2/4, 78.606/600s; offline attempts 1/2; BDF replays 1/2; MuJoCo launches 6/8; provider requests 11/32; public operations 36/128. Activity elapsed 1.892h/12h including engineering. Internal NMPC recovery is included once.

Measured numerical components: offline and BDF 532.270s; physical runs including failed starts 2965.968s; standalone local diagnosis 78.606s. Provider response time 187.691s, usage {'prompt_tokens': 903191, 'completion_tokens': 36831, 'total_tokens': 940022}; monetary cost is unknown. Actual read-only experience retrievals: 0 (supplied startup history and native context reads are separate).

New controller attempts: 161; complete input records: 160; resolved serialized problems: 160; missing complete inputs: 1. The two failed starts each computed a final command before control assignment; neither has terminal/holding acceptance. All updates of completed runs are saved. Earlier replaced progress and final temporary progress are archived as exact compressed bytes.

Offline optimization passed its original sampled task (5.200 mm, 0.019525 m/s), but independent BDF replay failed holding speed (0.065883 m/s). The mechanics structure entered goal-based NMPC as exploratory evidence. BDF is model integration, not physical validation.

At the engineering-selected fixed structure, lowering holding weight from 0.10 to 0.08125 improved the observed fixed task ranking: holding speed 0.042033 to 0.026947 m/s and position 3.961 to 3.861 mm. Both failed joint acceptance. These are single executions without independent confirmation and cannot establish a causal or stable improvement. Weighted NMPC objectives are not used for this comparison.

Repeatability: two new local solves preserved original tracing off, matched serialized mathematical identity, ordering, initialized objective and selected constraint values, and agreed with each other. They differed from the original first action by up to 0.666004 N (9 versus 8 selected iterations). Original cached workspace/tail state and timing history were not recreated; the unique mechanism remains unresolved. An inspection-only sorted-JSON vector-order bug was corrected from existing solver checks without another solve; original reports remain archived.

No structural superiority, stable robustness, autonomous discovery or unique causal diagnosis is claimed. BDF is not physical validation. Optional offline trajectory initialization and legacy skill admission remain unfinished.

[Runbook](mechanics_control_runbook.md), [scientific summary](../evidence/mechanics_control_20261011/scientific_summary.json), [focused checks](../evidence/mechanics_control_20261011/verification.json), [archive manifest](../evidence/mechanics_control_20261011/archive_manifest.json).
