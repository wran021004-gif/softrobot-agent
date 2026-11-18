# T03 — Fast Target Reaching

本目录仅整理历史研究证据，未运行新实验、优化或动力学积分。

实际研究 actor：codex_surrogate_main。不能将这些 Codex surrogate/expert 运行写成 Main SDK 研究。

单一结构；展示 0–0.5 s 的姿态和终端保持，不是结构演化案例。原任务 development draft 分类保留。

最终原始验收：

| Condition | Run ID | Accepted | Key metrics (SI) |
| --- | --- | --- | --- |
| default | codex-surrogate-T03-20261112 | True | {"geometric_stroke_max_m":0.006274302285623923,"geometric_stroke_min_m":-0.0036801474059404704,"geometric_tendon_speed_max_m_s":0.024749984920440206,"holding_max_error_m":0.002662671632155634,"holding_max_speed_m_s":0.019783051372062464,"terminal_error_m":0.002109920802953995} |

保留 2 个 Store 候选记录、1 个原 XML 引用、8 条去重原始决策（原始来源行 8，重复副本保留为 alternate_original_sources）、4 个代表节点。候选记录含条件/控制变体，不能当作不同实体结构数量。

`candidate_timeline.csv` 与 `agent_decision_timeline.csv` 的阶段名称是编辑分类；决策语句及 exact_arguments 为原文，缺失的独立假设字段标记 unavailable。`metric_history.csv` 仅列独立物理验收；不同 run_id / task_identity / profile_identity / condition 不应直接连成收敛线。

`evidence_bundle.json` 记录最终候选、原 Store artifact、原 XML、保存状态与时间字段。其余候选/条件和被否决步骤见 complete_* 索引。资源成本保留各原 COST_REPORT 引用，不跨 Study 简单相加。

后续视觉素材应优先使用 final_conditions.recorded_state_sources。没有中间原 XML 或状态的候选保留引用，不能制造截图。
