# C3：正式冷启动自主 Softarm Study

2026-10-25（Asia/Shanghai）。当前阶段：工程预检完成，等待本提交冻结后使用原 CLI prepare/bind 和本次用户授权启动。

## 冻结范围

- 独立 worktree `.worktrees/c3-autonomous-softarm-study`，分支 `research/c3-autonomous-softarm-study`。
- 指定基线 `c950100a462df8037b38eadf271dfdb403c3ba2a`，未修改旧 Study、证据或主工作区。
- 新 Study `c3-autonomous-softarm-20261025`；新 Store、Provider/Strands session、数值目录和导出。
- `tasks/reach_hold_c3_mirror.json` extends 原 Reach/Hold，只改任务 ID、名称、来源和预声明目标 `[0.29,-0.035,0.19]` m。
- 原 0.35 s 时域，0.01 s 控制/采样，0.0005 s MuJoCo 步长，具名零初态、环境、六路 0–8 N 理想张力不变。
- 原终点/保持误差均 ≤10 mm，保持最大速度 ≤0.02 m/s，保持窗口 `[0.30,0.35]` s 六样本；全部原独立验收组件保留。
- 两段六腱、原 source-relative 结构/材料/截面/控制权重域；不引入历史控制、候选排名或诊断答案。
- history、mathematics、control_seeds、supplied_evidence 均为空。冻结源机器人、控制器默认和方法目录仅作工程先验。
- 不宣称该目标已可行或具有结构辨别力，未搜索目标、结构或成功控制。

| 资源 | 上限（收尾额度包含在总额内） |
| --- | ---: |
| Provider / 收尾保留 | 32 / 6 |
| Public operations / 收尾保留 | 120 / 12 |
| 数学评价 | 12 |
| 共享物理启动 | 8 |
| 完整 GVS NMPC | 1 |
| 固定张力独立回放 | 5 |
| PPO stages / actions | 1 / 4096 |
| RL 独立评价 / 额外成功确认 | 1 / 0 |
| 单次 native 搜索 callbacks / updates / knots | 60 / 2 / 4 |

NMPC、固定回放、PPO 训练和评价共享物理总额，原 PPO 评价保护和 rollout 对齐保留。
所有科学墙钟限额仍为 null，耗时只测量。native 内部积分、差分、前缀重建和实际成本沿原计数记录。
既有 GVS、native 数学、MuJoCo-direct、控制初始化、NMPC、direct/兼容 residual PPO 和合法结构变更保持开放，实际调用需原准入。

## 工程预检与最小修复

已阅读 AGENTS、C1、A 结构重优化、B 决策及 B 语义修复报告，以及 CLI、Store、Budget、Recovery、Provider、Session Handoff 实现。
现有搜索 Schema 允许 1000 callbacks/100 updates；此前无 Study 专属硬限额。
仅在原 config 校验、analysis.dispatch 和方法目录增加可选 `native_control_limits`：超限在 reservation/worker 前拒绝，旧 Study 无此字段时保持原行为。
不改变优化器、动力学、任务验收或科学行动选择；新加两项定向测试。

预检使用现有 `.s135-env` host、`.mainline5-env` 科学 worker、`.rl-pilot-env` PPO worker，均已导入实际依赖。
Python 数值库为 NumPy 2.4.6、SciPy 1.17.1、CasADi 3.7.2、MuJoCo 3.13.0；Strands 1.59.0、harness 0.2.0；PPO 2.9.0 / Torch 2.14.1+cpu。
凭据仅核验存在，DeepSeek 原 endpoint 完成 DNS/TCP/证书验证 TLSv1.3 握手，无 HTTP/模型预检请求。
原配置编译、合法源结构生成、ResearchTaskAdapter 数学/验收阈值与完整采样对齐、六路 SI 边界、48 具名零自由度、合法控制 source 绑定、native 方法适用性通过。
原目录仍准确报告需补 source/settings、saved-state 或不支持的模型条件，没有为消除提示放松准入。
实际预检物理积分步数 0；没有向正式 Agent 提供预检控制或科学结果。
首个独立预检脚本直接以文件运行时因 import 路径失败；改用模块入口后通过，失败时无 Provider 或积分。
两项新增硬限额/目录兼容测试及原 B 三项回归共 5/5 通过；测试只用内存/只读历史归档，不是科研证据。

## 授权、执行和封存约束

本次用户附件 `34acdd2b-0e07-48c5-8ba3-67f9218be1e8` 明确批准一次受限的真实 Study、既有 DeepSeek 推理、所列数学/物理计算、同 Study 工程监督与合法恢复、必要最小修复、普通 commit/push。
首次 Provider 请求前，以原 formal_study_authorization 事件将实际本次批准绑定到新 Study 的 resolved_identity 和源码提交。
外发仅限冻结任务、机器人参数和本 Study 决策、数学/执行反馈与证据摘要；不外发密钥或无关个人数据。
Codex 不提交科学 Plan、指定实验顺序、结构方向或控制系数；由原 Strands Research Agent 自主选择。
未知 Provider/worker 先查原 request_id/receipt，禁止盲目重发；有可信结果则用原 recover/SDK 边界恢复。
若确需运行中修复，在无未决 worker/未知请求时 commit 并按原 migrate --reason 迁移，不重置费用。
首次完整独立通过触发原 success gate、公开读结果、精确 SELECT，零额外确认；否则仅由 Agent 合法 STOP。
完成后使用原 export，保留原始 Store、会话、失败、receipt 和成本；最终报告另补真实科研与审计结果。
