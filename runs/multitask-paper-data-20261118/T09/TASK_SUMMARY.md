# T09 — Guided Spring-Button Contact Manipulation

本目录仅整理历史研究证据，未运行新实验、优化或动力学积分。

实际研究 actor：codex_surrogate_main。不能将这些 Codex surrogate/expert 运行写成 Main SDK 研究。

最初因缺失 20 个实体导向硬件接口而阻塞；后真实导向质量/COM/惯量齐全，首轮暴露原应禁碰的眼孔/辐条被环境重启碰撞。最终接口修复保留原 no-contact 语义，并非人为删去失败碰撞。使用历史实际中点命令作为新 Store 未测输入，未复制历史状态或验收。

最终原始验收：

| Condition | Run ID | Accepted | Key metrics (SI) |
| --- | --- | --- | --- |
| default | codex-expert-T09-20261113-core027 | True | {"hold_valid_continuous_s":0.4999999999999559,"max_hold_contact_force_error_n":0.002465057424524908,"max_hold_depth_error_m":5.2752700179421914e-05,"max_rope_speed_m_s":0.018224426063267712,"max_stroke_m":0.0032966105752161856,"max_tension_n":4.402568121786447} |

保留 6 个 Store 候选记录、3 个原 XML 引用、22 条去重原始决策（原始来源行 22，重复副本保留为 alternate_original_sources）、5 个代表节点。候选记录含条件/控制变体，不能当作不同实体结构数量。

`candidate_timeline.csv` 与 `agent_decision_timeline.csv` 的阶段名称是编辑分类；决策语句及 exact_arguments 为原文，缺失的独立假设字段标记 unavailable。`metric_history.csv` 仅列独立物理验收；不同 run_id / task_identity / profile_identity / condition 不应直接连成收敛线。

`evidence_bundle.json` 记录最终候选、原 Store artifact、原 XML、保存状态与时间字段。其余候选/条件和被否决步骤见 complete_* 索引。资源成本保留各原 COST_REPORT 引用，不跨 Study 简单相加。

后续视觉素材应优先使用 final_conditions.recorded_state_sources。没有中间原 XML 或状态的候选保留引用，不能制造截图。

接触与硬件证据要点：

- 2026-11-12 前驱原 Trace 因源 v1.2 要求 20 个实体导向眼孔/辐条组件而接口无法表达，明确停止，数学/物理均未启动；该阻塞不是软臂控制或结构的物理失败。
- 后续完整硬件首轮执行 dcb0b53... 的原验收给出 9 个 unexpected collision 对、有效力/深度保持 0 s。原 Trace T09-210 记录环境装配错误重新启用了源定义禁碰的眼孔/辐条碰撞，接口修复恢复原语义，保持全部 20 组件的真实质量、COM 与惯量。
- 最终执行 450ac79... 在全 v1.2 任务中保持有效深度/力连续 0.4999999999999559 s（要求 ≥0.4 s），最大保持深度误差 0.05275270018 mm，最大接触力误差 0.002465057425 N，unexpected collisions=0；1.8/2.0 s 释放位置、力和速度均通过。
- 该案例适合真实接触前—按压—保持—释放姿态序列；不要将接口修复伪写成研究者减少真实硬件或删除源任务接触约束。

Full scene states: original result.json /task_evidence/arrays contains 2001 x 49 qpos/qvel and matched time_s. The original joint_layout maps button_slide to address48. samples.json contains only201 x 48 robot-only coordinates and is not a full scene state. Lightweight checks pass against the original49-coordinate dense evidence.
