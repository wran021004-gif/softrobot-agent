# S12.8 正式 Cold-start 自主研究交付

2026-10-21，正式研究及独立验收完成。DeepSeek Agent 从空科研状态生成 7 个合法候选，
完成 79 次独立物理评估，未找到通过原任务的结构—控制方案，最终自主 **STOP，无 SELECT**。
保留全部失败与剩余额度，不自动进入 S12.9、S13 或追加研究。

## 冻结、授权与执行

- Study：`s128-cold-live-20261021`，分支 `feat/sorosim-matlab-nmpc`。
- 原基线：`096488569644d8bdd9b2907486585adec563b41e`。
- 正式源码：`988acfe3339dc4a55b6a46df7349ed98783ae4ee`，冻结时已普通 push 并核对远端一致。
- 冻结时间：2026-10-21 14:08:26 +08:00，324 个源文件 hash 保持一致。
- 配置身份：`ba4b62cc3e1efe04c0742bdbb6d64ba3e1546502b9a22e7ef9635251432b3833`。
- 授权范围身份：`416dc421be8453ea40b583fa23a69f28b344343d4e4d8cc85c961c53da19db28`。
- 用户对完整范围回复“批准”，首次 Provider 请求前已绑定 Store 授权记录。
- 实际运行：14:15:11.117 至 14:59:46.851 +08:00，约 44 分 36 秒。

启动前，新 Store 和独立重开的新 Strands SDK 均为空；history、mathematics、control_seeds、
supplied_evidence 为空，0 候选、0 Provider、0 科学执行、0 pending。未导入旧实验证据。
方法与变量均由真实 Agent 选择，Codex 只监督和审计，没有插入科学提案。
运行中未修改源码、任务、模型、预算或验收规则。使用 deepseek-flash、thinking enabled/high、
max_tokens=131072；59 次正式请求均 HTTP 200，没有额外真实 Provider 工程探测、自动重试、
确认截断、未知发送或中断 worker。保持 count-mode，无科学时间提前停止。

准备证据见 [冻结协议](s128_protocol.md)、[授权范围](s128_authorization_scope.md)、
[冻结记录](../../evidence/s128_preflight/freeze.json)、
[空状态](../../evidence/s128_preflight/cold_start.json)及
[授权 receipt](../../evidence/s128_preflight/authorization.json)。

## 原任务与独立结果

原任务 `tasks/reach_hold_mirror_v1.json` 未改：目标 `[0.29,-0.035,0.19] m`，0.35 s 时域，
0.01 s 控制周期，0.0005 s MuJoCo 步长；原初始条件、张力范围、数值有效性、采样覆盖及执行完整性均保留。

| 原任务指标 | 上限 | 最佳统一指标结果 | 两段 NMPC | 三段 NMPC |
|---|---:|---:|---:|---:|
| 终点误差 / mm | 10 | 32.494 | 25.076 | 48.066 |
| 保持最大误差 / mm | 10 | 32.625 | 28.380 | 49.340 |
| 保持最大速度 / m/s | 0.02 | 0.065250 | 0.085642 | 0.092205 |
| 统一归一化违反量 | 0 | 2.262483 | 3.282081 | 3.934046 |
| 原任务完整验收 | 通过 | 未通过 | 未通过 | 未通过 |

统一违反量为已有约束分量 `max(0, value/limit - 1)` 的最大值，仅用于合法完整结果排序。
两段 NMPC 位置更好，但速度更差。79 次均合法完整（77 重放、2 NMPC），完整通过数为 0。
表中结果的执行、数值、输入和覆盖要求通过，三项任务指标均未达标。
最佳结果属于 `cfddd272…` 候选，证据
`569a406dd84017cd950b7be9fe5da24902c950d106a4ecc0d69b45d1313f38e4`，
控制来源 `c7747a5d6d9a60dd17dc6f300caf8f0f068f2cd9c2192e755381f8969facb42a`。
首个固定输入结果为 152.460 mm / 152.460 mm / 0.176025 m/s，存在实测改善但未达标。

独立审计只读已保存样本，重建原注册评价器及完整 assemble_acceptance：77 次重放的网格、
700 物理步、实际输入、位置/速度范数、保持窗口核对通过；2 次 NMPC 保存状态、命令、运动、
profile 和验收也一致。没有再次仿真、训练或优化。详见
[逐项原验收重建](../../evidence/s128_acceptance/reconstruction.json)及
[最终状态](../../evidence/s128_acceptance/status.json)。

## 自主结构与方法选择

11 次生成请求得到 7 个不同合法候选，4 次非法；6 个合法候选被物理测试。
下表按生成顺序列主要变化。每段 12 cells，密度 1100 kg/m³；黏性为各段相同 y/z 系数，单位 N·m²·s。
完整身份及参数见 [设计统计](../../evidence/s128_research/designs.json)。

| 候选前缀 | 段/腱数 | 各段长度 / m | 各段 E / MPa | 黏性 y/z | 预张力 / N | 物理评估数 |
|---|---:|---|---|---:|---:|---:|
| c5db6ee4 | 2/6 | 0.19, 0.19 | 7.2, 5.4 | 0.02 | 0.2 | 0 |
| a0a831fd | 2/6 | 0.19, 0.19 | 2, 2 | 0.02 | 0.2 | 2 |
| 54ff3fe5 | 2/6 | 0.24, 0.06 | 2, 2 | 0.02 | 0.2 | 7 |
| cfddd272 | 2/6 | 0.24, 0.06 | 2, 2 | 0.02 | 0 | 60 |
| 8334e480 | 2/6 | 0.24, 0.06 | 7.2, 5.4 | 0.05 | 0 | 2 |
| cb9e9bfc | 2/6 | 0.20, 0.068 | 2, 2 | 0.05 | 0 | 7 |
| 318c922b | 3/7 | 0.10, 0.10, 0.10 | 2, 2, 2 | 0.05 | 0 | 1 |

以下概述原记录中的假设与选择，不公开原始模型推理：

- H1–H5：提出两段结构，按合法性反馈修订，随后降低弹性模量。
- H6–H11：试验恒定张力、反向腱输入和离线 NLP，检查输入方向及优化起点。
  warm source 被拒后自主改为 cold NLP；完成 78 次迭代、目标值 115.64175490824711，
  结论为 inconclusive、需独立重放，未提供物理成功或不可行证明。
- H12–H17：缩短结构、取消预张力，做物理响应初始化及 8 N 固定输入测试。
- H18：在 0、0.12、0.25、0.35 s 四个结点搜索前三腱系数。12 维 response 搜索上限 60，
  4 次迭代、48 次差分评估；53 次回调含 1 次缓存基线及 52 次新物理执行，停于 iteration_limit。
  得到本轮统一指标最佳值，保持速度仍超限。
- H19–H28：路由变化因超出 FamilySpace 被拒，再尝试刚度/黏性变化、长度匹配结构及末结点
  2 维 response 搜索。第二次 6 回调含 1 缓存基线、5 新执行、4 差分评估，
  停于 evaluation_request_budget，未超过整体最佳结果。
- H29：长度匹配两段 NMPC 位置误差下降，但保持速度仍不合格。
- H30–H31：三段七腱 NMPC 三项任务指标均未达标。
- H32–H34：两次 STOP 因证据不全被拒；第三次引用全部 80 个新科学结果
  （77 重放、2 NMPC、1 NLP），STOP 被正式接受。

控制初始化共 8 次：6 次 baseline/显式或继承控制，2 次 physical_response。
物理启动构成为响应初始化 14、直接固定输入验证 6、局部搜索 57、NMPC 2。
两次搜索共记录 10 次裁剪后输入不变的无效方向尝试，没有为这些方向重复执行相同实际输入，
duplicate_applied_sequences 均为 0。但局部搜索占大量物理额度、改善有限，不能声称没有低效决策。
派生元数据见 [决策与搜索统计](../../evidence/s128_research/decisions.json)。

两次 NMPC 均完整执行、无 solver errors，是离线仿真结果。两段平均每次更新约 7.759 s，
超过 0.01 s 控制周期；原配置 real_time_required=false，不把实时性额外加入原验收，
也不宣称证明实时控制或硬件性能。

未选择独立数学分析、BDF、pattern search、Direct PPO 或 Residual PPO。
PPO 预检已验证高额度事务准入；正式训练、动作、checkpoint、独立 RL 评价均为 0。
Agent 使用物理预算后只剩 1 次启动，低于原训练加独立评价需要的 2 次预留。
不能据此评价 PPO 学习效果或未尝试方法。

## 输入错误与失败分类

输入或准入问题共 8 次，全部保留：4 次结构 invalid（3 次 EXACT_SECTION_STATIONS_REQUIRED、
1 次 OUTSIDE_FAMILY_DOMAIN: base_radius_m）；4 次工具 error feedback（fields 证据指针错误 1、
warm source 不合法 1、STOP 引用不全 2）。结构 invalid 的 SDK 包装状态仍为 success，单独计数。
Agent 按反馈重交，没有自动修复后代替执行；重复 station 错误也计入成本。
这些拒绝未启动科学 worker，Provider/公共操作消耗仍记账。
本轮没有实际漏 hypothesis 或 Pydantic extra-field 报错，不混入历史失败。

科学失败表现为合法完整执行仍违反任务约束；位置/速度存在权衡；局部搜索改善不足；
单次近似 NLP 结论不建立物理可行性。有限结果不证明全局不可行、结构族不可控或 PPO 无效。
后续科学问题是原时域内如何同时降低三项误差，以及方法间预算分配是否有效；本文不启动后续研究。

## 实际成本

| 项目 | 冻结上限 | 实际 | 剩余 |
|---|---:|---:|---:|
| Provider requests | 128（含 12 protected） | 59 | 69 |
| Public operations | 400（含 24 protected） | 145 | 255 |
| Shared physical launches | 80 | 79 | 1 |
| Mathematical evaluations | 8 | 0 | 8 |
| Offline NLP | 4 | 1 | 3 |
| BDF | 4 | 0 | 4 |
| NMPC | 4 | 2 | 2 |
| PPO stages | 8 | 0 | 8 |
| PPO training actions | 4,194,304 | 0 | 4,194,304 |
| RL independent evaluation episodes | 12 | 0 | 12 |

PPO 单阶段上限 1,048,576 不变，全部为上限，不要求用满。没有追加预算。
实际 usage：prompt 7,093,807、completion 144,255、总计 **7,238,062 tokens**；
prompt cache hit 146,560、miss 6,947,247；59 响应的 reasoning 合计 103,138，属于 completion 子集。
Provider 未报告美元费用，不推算金额。见 [逐请求成本](../../evidence/s128_costs/counts.json)。
Study 总历时 2675.733 s，账本计入执行耗时约 1673.914 s，两者定义不同。
保守容量峰值 864,652 / 1,000,000，含最大输出 131072 及 framing 8192；
容量检查以序列化字节为基础，不能当作实测输入 tokens。

## 历史完整性与封存

全程 1 个新连续 Strands session，无 handoff。新进程只读重开后，历史身份与 Store 完成回合一致，
59 段 reasoning 与原 HTTP 按序一致，工具 ID/结果配对。模型原生调用 68 次
（research_plan 34、evidence_read 34）：49 个完整反馈与 18 个精确配置 Offload preview
被后续请求发送；终止 STOP 的最后反馈保存但没有为此再发请求。全部原始反馈留在 Store。
最终 pending、未知发送、未结 receipt 均为 0，状态 stopped。

- Store 身份：`6e1c7e68685679a8ff91134cbf1a190b8e2a52d4644e7be2b9be6f9e0b8cdab8`。
- SDK 消息身份：`f57d9d6be977bc36572e5e21888494b0e33e59c39ace0a78bc92aaf2b8b2721a`。
- 审计未改 Store 状态/账本/事件和 71 个 SDK 文件，新增 Provider/科学执行均 0。
- 324 冻结文件、science/core 身份、旧任务和 S12.7.6 封存保持一致。

现有 export 生成本地归档：`runs/research/s128-cold-live-20261021/export/immutable_artifacts.tar.gz`，
14,143,716 bytes，1421 成员逐项 hash 核对；SHA256：
`acb3ab8f6cabbdf9239c5bc0e80784dd09356e53a2aa3194873b08d96fc29604`。
原始 HTTP、reasoning、SDK、Store、科学数组及完整归档只留本地 runs；Git 只公开代码、配置、
派生统计、必要引用和本报告。`tests/research/s128_delivery_audit.py` 是 STOP 后新增只读审计器，
复用原评价器，不修改冻结运行源码；该模块实际运行通过。

## P0 最小修复及工程验证

原恢复主要核对会话/标记/Schema，initial_messages 全量比较仅在初次验证执行，普通恢复
没有充分使用 Store 完成回合身份，且反馈恢复可能先于验证写入。现采用已有 Store 权威记录：
初始 handoff 核对初始消息及提交信息；完成回合后复用同 session 最新 sdk_message_identity，
允许正常增长；未完成回合保留已有 pending/receipt 恢复。启动先验证，再允许合法反馈恢复及写入。
不新增签名、数据库、逐条验签或科学框架。

| 准入项 | 结果 |
|---|---|
| snapshot_content_integrity_passed | true |
| trusted_history_reconciliation_passed | true |
| legitimate_history_growth_passed | true |
| unsafe_snapshot_rejected_before_side_effects | true |
| cross_process_recovery_passed | true |
| production_handoff_admitted | false |

54 个不同回归通过，包含既有 14 个进程中断场景；旧 hook fixture 更新后单独复测通过，原日志保留。
S12.7.6 真实旧/新 SDK 在新进程只读恢复，原 7/4 段 reasoning、工具反馈一致。
生产净增 59 行（恢复 41、独立授权保护 18）。详见
[P0](../../evidence/s128_preflight/p0_consistency.json)、
[真实会话复核](../../evidence/s128_preflight/p0_live_reopen.json)、
[回归](../../evidence/s128_preflight/regression.json)。
完整生产轮换的全部工具组合中断/接续场景未单独准入，继续关闭；连续 Strands 已完成本轮研究。
冻结前 MATLAB/SoRoSim readiness、RL 构造（48 DOF、4 动作、107 观测、35 控制区间）和
高额度真实 dispatch 预留通过；仅在 worker 边界拦截训练，没有把合成 usage/预留算作正式科学消耗。
正式阶段没有再运行大规模 Harness 实验。
