# T01 — Multi-target Reach-and-Hold

本目录仅整理历史研究证据，未运行新实验、优化或动力学积分。

实际研究 actor：codex_surrogate_main。不能将这些 Codex surrogate/expert 运行写成 Main SDK 研究。

共享结构确有变化：历史路线基线 → 14.1 mm → 14 mm 腱路半径，再将两段各加长 2.5 mm；不同目标的控制分别重新优化。早期无独立物理 XML 的数学候选只能引用配置，不能伪造截图。

最终原始验收：

| Condition | Run ID | Accepted | Key metrics (SI) |
| --- | --- | --- | --- |
| central_high | codex-expert-T01-20261113-s1 | True | {"geometric_stroke_max_m":0.006242437087095598,"geometric_stroke_min_m":-0.00854727312436876,"geometric_tendon_speed_max_m_s":0.02475,"holding_max_error_m":0.009146735638176468,"holding_max_speed_m_s":0.029699999854067648,"terminal_error_m":0.009146735638176468} |
| negative_low | codex-expert-T01-20261113-s1 | True | {"geometric_stroke_max_m":0.008884071935855276,"geometric_stroke_min_m":-0.008142095679415817,"geometric_tendon_speed_max_m_s":0.024772647745639094,"holding_max_error_m":0.009905895250612671,"holding_max_speed_m_s":0.0297196178042583,"terminal_error_m":0.009833273979196665} |
| positive_high | codex-expert-T01-20261113-s1 | True | {"geometric_stroke_max_m":0.004063966875702596,"geometric_stroke_min_m":-0.008651931381412348,"geometric_tendon_speed_max_m_s":0.02474999999999999,"holding_max_error_m":0.009899999999999973,"holding_max_speed_m_s":0.029699999928910016,"terminal_error_m":0.009813057962543706} |

保留 45 个 Store 候选记录、11 个原 XML 引用、144 条去重原始决策（原始来源行 239，重复副本保留为 alternate_original_sources）、5 个代表节点。候选记录含条件/控制变体，不能当作不同实体结构数量。

`candidate_timeline.csv` 与 `agent_decision_timeline.csv` 的阶段名称是编辑分类；决策语句及 exact_arguments 为原文，缺失的独立假设字段标记 unavailable。`metric_history.csv` 仅列独立物理验收；不同 run_id / task_identity / profile_identity / condition 不应直接连成收敛线。

`evidence_bundle.json` 记录最终候选、原 Store artifact、原 XML、保存状态与时间字段。其余候选/条件和被否决步骤见 complete_* 索引。资源成本保留各原 COST_REPORT 引用，不跨 Study 简单相加。

后续视觉素材应优先使用 final_conditions.recorded_state_sources。没有中间原 XML 或状态的候选保留引用，不能制造截图。
