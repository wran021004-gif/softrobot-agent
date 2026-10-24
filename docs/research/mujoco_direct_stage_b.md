# 阶段 B：MuJoCo-direct 离线控制优化

基线 `codex/mujoco-native-math-stage-a@904f4932a`；独立工作树
`.worktrees/mujoco-direct-control-stage-b`，分支 `codex/mujoco-direct-control-stage-b`。
已读取 AGENTS、阶段 A、S142–S148 报告和原数学、控制搜索、回放及证据实现。
主工作树现有未跟踪文件和历史研究 Store 保留不动。

工程范围：原 `research_analysis` 新方法 `mujoco_direct_control_v1`，使用原
`local_control_search.search` 和受限响应求解，仅替换为克隆 native checkpoint
的多区间回调。优化覆盖全部保持样本，内部裕量不改变冻结阈值。
输出原 `explicit_control_schedule_v1`，通过原 `physical_replay` 完整重放与独立验收。

预定有界验证：一次 0–0.30 s 核验前缀；最多 80 个尾段求值、4 次局部响应迭代、
18 个系数（3 个时间结点 × 6 腱），内部 5% 裕量；原控制与最佳控制各一次完整回放。
独立 engineering_numerical 配置、Store 和预算；零 Provider、自主 Study、PPO、完整 NMPC。
失败、未决与实际成本在执行后补入本报告。
