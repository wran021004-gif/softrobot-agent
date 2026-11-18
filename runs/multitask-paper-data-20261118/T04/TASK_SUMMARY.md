# T04 — Figure-Eight Trajectory Tracking

本目录仅整理历史研究证据，未运行新实验、优化或动力学积分。

实际研究 actor：codex_surrogate_main。不能将这些 Codex surrogate/expert 运行写成 Main SDK 研究。

研究路线由长期 GVS NMPC 比较改为原生静力平衡参考库和绝对张力前馈。原 GVS 执行未完整完成并在成功后终止，不应写为已完成的性能失败或全局不可行。89 点静态库不构成轨迹验收。

最终原始验收：

| Condition | Run ID | Accepted | Key metrics (SI) |
| --- | --- | --- | --- |
| default | codex-expert-T04-20261113-core029-interior | True | {"cycle_phase_matched_max_difference_m":0.0010088782522628332,"max_error_m":0.0010206639031726755,"terminal_speed_m_s":8.880355752485461e-05,"tracking_rmse_m":0.0006878528448055238} |

保留 7 个 Store 候选记录、7 个原 XML 引用、43 条去重原始决策（原始来源行 43，重复副本保留为 alternate_original_sources）、5 个代表节点。候选记录含条件/控制变体，不能当作不同实体结构数量。

`candidate_timeline.csv` 与 `agent_decision_timeline.csv` 的阶段名称是编辑分类；决策语句及 exact_arguments 为原文，缺失的独立假设字段标记 unavailable。`metric_history.csv` 仅列独立物理验收；不同 run_id / task_identity / profile_identity / condition 不应直接连成收敛线。

`evidence_bundle.json` 记录最终候选、原 Store artifact、原 XML、保存状态与时间字段。其余候选/条件和被否决步骤见 complete_* 索引。资源成本保留各原 COST_REPORT 引用，不跨 Study 简单相加。

后续视觉素材应优先使用 final_conditions.recorded_state_sources。没有中间原 XML 或状态的候选保留引用，不能制造截图。

研究路线证据要点：

1. 原已读 `T04_RUN_03/KNOWLEDGE/expert-t04-method-selection@1.json` 明确区分：历史成功使用准静态张力前馈；当前 GVS 2200 更新比较仍在运行；SoRoSim 仅支持 reach，PPO 不支持本任务定时/外力语义。其当时决策为先尝试原生平衡延续，不能写为 Agent 从已完成 NMPC 失败中推断全局不可行。
2. `T04_RUN_03/NATIVE_REFERENCE_BANK.json` 原始输出：89 次数学评价，零积分步；最大静力残差 5.075230166684541e-12 Nm，最大静态位置误差 0.0006110494311492155 m。`optimizer_success=false`、250 迭代上限必须保留；这些静态点本身不是轨迹通过证明。
3. 初次全 4 N 初始化导致不允许的优化器试点、未产生 bank（原 Trace T04-211）；随后改为从此前计算的时间零平衡出发、0.2 N 预载移至 0.21 N 内部并重建 bank（T04-216）。
4. 原 `BANK_FEEDFORWARD_REPLAY.json` / 原 Store f9d19d...：独立完整 22 s 验收后才通过，RMSE 0.687852845 mm、最大误差 1.020663903 mm、周期漂移 1.008878252 mm，两周期各两叶、无接触/警告与行程/速度均通过。
5. 原 `INITIAL_EXECUTION.json` 的 GVS 比较是 execution_incomplete/worker exit；`SUPERSEDED_NMPC_TERMINATION_REQUEST.json` 明确在前馈方案被选择后终止旧比较，并不给予其完整科学验收信用。
