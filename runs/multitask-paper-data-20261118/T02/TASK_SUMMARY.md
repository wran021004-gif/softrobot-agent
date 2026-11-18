# T02 — Load-Conditioned Hold

本目录仅整理历史研究证据，未运行新实验、优化或动力学积分。

实际研究 actor：codex_surrogate_main。不能将这些 Codex surrogate/expert 运行写成 Main SDK 研究。

结构差别主要是两段材料模量 14 MPa → 12 MPa，几何外观不变；适合受载状态/定量结果比较，不能靠颜色或尺寸制造结构演化。三负载工况分别评价。

最终原始验收：

| Condition | Run ID | Accepted | Key metrics (SI) |
| --- | --- | --- | --- |
| negative | codex-surrogate-T02-20261112 | True | {"geometric_stroke_max_m":0.005316207417810803,"geometric_stroke_min_m":-0.0034143066130029043,"geometric_tendon_speed_max_m_s":0.024736707763668535,"holding_max_error_m":0.009897088402492153,"holding_max_speed_m_s":0.019757280334218204,"terminal_error_m":0.00943946043182984} |
| positive | codex-surrogate-T02-20261112 | True | {"geometric_stroke_max_m":0.005093465479993953,"geometric_stroke_min_m":-0.0027839089451672794,"geometric_tendon_speed_max_m_s":0.024744238841624546,"holding_max_error_m":0.009880943306424453,"holding_max_speed_m_s":0.019725865714044232,"terminal_error_m":0.00953349902465537} |
| zero | codex-surrogate-T02-20261112 | True | {"geometric_stroke_max_m":0.0054192244835994385,"geometric_stroke_min_m":-0.0029546945485629528,"geometric_tendon_speed_max_m_s":0.02473691807375513,"holding_max_error_m":0.005357274331766039,"holding_max_speed_m_s":0.019790830274628676,"terminal_error_m":0.0050628666986212625} |

保留 8 个 Store 候选记录、6 个原 XML 引用、35 条去重原始决策（原始来源行 35，重复副本保留为 alternate_original_sources）、5 个代表节点。候选记录含条件/控制变体，不能当作不同实体结构数量。

`candidate_timeline.csv` 与 `agent_decision_timeline.csv` 的阶段名称是编辑分类；决策语句及 exact_arguments 为原文，缺失的独立假设字段标记 unavailable。`metric_history.csv` 仅列独立物理验收；不同 run_id / task_identity / profile_identity / condition 不应直接连成收敛线。

`evidence_bundle.json` 记录最终候选、原 Store artifact、原 XML、保存状态与时间字段。其余候选/条件和被否决步骤见 complete_* 索引。资源成本保留各原 COST_REPORT 引用，不跨 Study 简单相加。

后续视觉素材应优先使用 final_conditions.recorded_state_sources。没有中间原 XML 或状态的候选保留引用，不能制造截图。
