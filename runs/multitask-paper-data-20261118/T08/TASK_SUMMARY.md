# T08 — Passive Progressive-Stiffness Response

本目录仅整理历史研究证据，未运行新实验、优化或动力学积分。

实际研究 actor：codex_surrogate_main。不能将这些 Codex surrogate/expert 运行写成 Main SDK 研究。

被动 P3、0 主动执行器，2 段 2 腱，每段 2 单元。唯一修改为两腱固定放绳偏置 1.5 → 1.8 mm；正负向受载和撤载回弹应分别显示。不能套用主动控制策略。保留 development_not_registered_SELECT，物理通过不升级为注册基准 SELECT。

最终原始验收：

| Condition | Run ID | Accepted | Key metrics (SI) |
| --- | --- | --- | --- |
| plus_x | codex-surrogate-T08-20261112 | True | {"minus_x_high_maximum":0.02250849035374532,"minus_x_low_minimum":0.007928066911447379,"minus_x_paired_mechanism":1.0,"minus_x_residual_maximum":6.858960174326618e-07,"minus_x_slack_to_taut":1.0,"minus_x_stiffness_ratio":1.631454749259155,"no_contact":0.0,"plus_x_high_maximum":0.022508490353744023,"plus_x_low_minimum":0.007928066911447334,"plus_x_paired_mechanism":1.0,"plus_x_residual_maximum":6.858960174692536e-07,"plus_x_slack_to_taut":1.0,"plus_x_stiffness_ratio":1.6314547492588845} |
| minus_x | codex-surrogate-T08-20261112 | True | {"minus_x_high_maximum":0.02250849035374532,"minus_x_low_minimum":0.007928066911447379,"minus_x_paired_mechanism":1.0,"minus_x_residual_maximum":6.858960174326618e-07,"minus_x_slack_to_taut":1.0,"minus_x_stiffness_ratio":1.631454749259155,"no_contact":0.0,"plus_x_high_maximum":0.022508490353744023,"plus_x_low_minimum":0.007928066911447334,"plus_x_paired_mechanism":1.0,"plus_x_residual_maximum":6.858960174692536e-07,"plus_x_slack_to_taut":1.0,"plus_x_stiffness_ratio":1.6314547492588845} |

保留 4 个 Store 候选记录、8 个原 XML 引用、11 条去重原始决策（原始来源行 11，重复副本保留为 alternate_original_sources）、5 个代表节点。候选记录含条件/控制变体，不能当作不同实体结构数量。

`candidate_timeline.csv` 与 `agent_decision_timeline.csv` 的阶段名称是编辑分类；决策语句及 exact_arguments 为原文，缺失的独立假设字段标记 unavailable。`metric_history.csv` 仅列独立物理验收；不同 run_id / task_identity / profile_identity / condition 不应直接连成收敛线。

`evidence_bundle.json` 记录最终候选、原 Store artifact、原 XML、保存状态与时间字段。其余候选/条件和被否决步骤见 complete_* 索引。资源成本保留各原 COST_REPORT 引用，不跨 Study 简单相加。

后续视觉素材应优先使用 final_conditions.recorded_state_sources。没有中间原 XML 或状态的候选保留引用，不能制造截图。

被动机制证据要点：

- 原候选 e87a0bff...（1.5 mm 放绳偏置），执行 e3b1c46...：正/负向刚度比分别 1.3668366483436758 / 1.3668366483437635，低于固定下界 1.5，其余多数位移界满足；不能仅展示最终通过。
- 原 Trace T08-006 根据该测量只把两腱偏置增至 1.8 mm，固定几何/材料/离散/载荷。新候选 a0438dc... 在执行 264bc9... 的刚度比分别 1.6314547492588845 / 1.631454749259155；最终 d8b294... 完成源任务要求的独立基线、配对去限位机制对照、半步长及初始扰动。
- 最终最大高载位移 22.508490354 mm、撤载残留约 0.000685896 mm（0.685896 微米）；这是被动 P3 的数值，不能借用 PHS-2D 的 Tip 或传递比指标。
- `recorded_replay_model_index.csv` 将每个 baseline / ablation / half_timestep / initial_perturbation 的 XML 严格绑定到同文件夹 episode CSV。状态列 qpos_0...7，时间列 time_s，阶段列 stage；无需新积分。
- 主体和腱路几何形状无大幅变更，放绳长差异应通过相同受载阶段下的真实变形/松紧状态与刚度定量图表达。
