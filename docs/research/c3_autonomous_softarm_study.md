# C3：正式冷启动自主 Softarm Study

2026-10-25（Asia/Shanghai）。**旧 source-relative C3 已因用户改变设计起点而中断、结算并封存。**
它完成一次基线控制的独立有效失败，随后 NMPC 运行中被行政中断；没有任务通过、SELECT 或 Agent 科学 STOP。
用户随后明确要求候选池为空，段数、腱数及结构参数均由 Agent 自主生成，并另行授权新 Study 完整额度。
该新授权不重置或删除本报告记录的旧消耗；新研究需独立身份，本报告仅记录旧 Study。

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

## 真实运行与 Agent 决策

正式源码身份 `6f265da17f428e6bbb02558accdaf7ef47cb4faf`，Study `c3-autonomous-softarm-20261025`。
第一次启动和普通 push 均在创建进程前被自动审批拒绝；用户随后在当前聊天明确批准确切 DeepSeek endpoint/数据范围及 GitHub 仓库/分支。
新增原 formal_study_authorization 事件绑定本次确认后才启动，无拒绝后的绕过或未知发送重试。
原 prepare、bind、Strands run、Store、Reporter、ResultCard 和 L0–L3 均沿用；运行中生产修复及迁移均为 0。

发送给 Agent 的是本次冻结任务、合法源机器人及参数范围、注册数学/控制方法、额度、工具 Schema，以及新会话中真实得到的反馈。
没有发送 C1 成功控制、A 的最优序列、历史结构排名、S142 后续答案或 Codex 指定的科学路线。
旧 Study 有一个源候选；它满足原附件的 source-relative 条件，但不满足用户后来追加的“空白候选池”要求。

| Agent 自主选择 | 实际执行 / 反馈 |
| --- | --- |
| H1：长度核算导致几何可达不足；竞争解释为长度核算错误或局部模型不适用 | 最初将数学意图放进 execute，原门禁拒绝；Codex 未改写 |
| sampled-affine-conic-minimax 能力分析 | halfway_waypoint 缺明确起始时刻，返回 `KNOWN_ANALYSIS_START_TIME_REQUIRED`，未求解，数学扣费 0 |
| 六路恒定 1 N 控制初始化 | 先有参数/决策字段错误，Agent 自行修正后生成本 Study 合法 source，任务未测 |
| 对上述 source 做独立 MuJoCo 全程回放 | 完整 700 步，所有位置/速度任务指标失败，张力及执行完整性通过 |
| H2：撤回几何短臂解释，转向重力下垂、控制与 GVS/plant 预测差异 | 自主选择唯一 GVS NMPC；没有新结构，没有使用 PPO 或 MuJoCo-direct |
| NMPC 控制更新 | 保存 3 次更新，t=0/0.01/0.02 s；每次迭代上限、计划可用，但优化未收敛；尚无完整独立任务评价 |

Agent 能提出竞争解释、预测与反证条件，且确实根据新物理反馈调整了假设。
但这不等于科学推断完全可靠：初始几何核算把总长度估为 0.282 m，而冻结 native 零态 tip 为 `[0.298,0,0.15]` m。
它最初将几何误差预测写成约 1.28 的归一化违反量，也未扣减 signed residual 的 1，属于尺度/语义错误。
H2 将单个 NMPC 的边界饱和失败解释为“genuinely limited”驱动能力，也过强；局部控制失败不能单独排除模型、求解或初始化限制。
它同时正确声明未收敛不证明不可行、模型预测不等于独立验收；这些边界与上述过强文字并存，不能只摘取正确部分。
数学 minimax 没有实算，因此本次不能证明数学证据改善了结构选择；实际促成改道的是完整物理回放及 Reporter 反馈。

## 独立验收、消耗与用户中断

| 恒定 1 N 回放指标 | 实测 | 冻结阈值 |
| --- | ---: | ---: |
| 终点位置误差 / m | 0.1982345201881802 | 0.01 |
| 保持最大位置误差 / m | 0.21585184122916581 | 0.01 |
| 保持最大速度 / m/s | 0.541584392862904 | 0.02 |
| 实际张力越界 / N | 0 | 1e-8 |
| 积分步 / 控制区间 / 保持样本 | 700 / 35 / 6 | 完整覆盖 |

原验收为 `valid_failure`，不是结构不可行性证明。结果 `34d7eeb1`，原始轨迹 `80bd0d17`，独立 evaluator `c0687c4f`。
NMPC 前 3 个更新各耗时 118.8761、108.2163、112.0996 s，均 `Maximum_Iterations_Exceeded`。
用户在运行中明确改变要求后，Codex 核验没有未知 Provider 或未消费响应，保存原进程清单及用户指令，停止精确主会话并调用原具名 worker-job 终止接口。
4 个相关 PID 均验证退出；使用原 `record_orphan_exit` 和 `python -m tools.research recover` 结算原 pending/request_id/receipt，无新 worker 或 Provider 发送。
NMPC 结果 `dc9ad657` 明确为 `execution_incomplete`，保留原进度和共享图文件，不拼接完整轨迹或控制 source。
原终止边界保守计时 438.6351 s；中断时完整物理步数未知，原保存时刻仅证明至少 40 步，不虚报为 700 步。

原 `engineering_closeout` 封住旧 Store，记录 `model_stop=false` 及用户范围变更原因。
该接口沿用的事件名称为 `engineering_count_budget_closure`，但本次**不是预算耗尽**，不是 Agent 科学 STOP，也不是正常完成自主研究。
现有全部 28 个 calls 均有 receipt（completed 26、failed 2），pending=null，无未知执行或未决 Provider。
7 次工具请求错误及一次数学不适用反馈全部保留，不因中断或新授权抹除。

| 旧 Study 实际资源 | 消耗 / 原上限 |
| --- | ---: |
| Provider（主会话 / Reporter） | 13 / 32（12 / 1） |
| Public operations | 14 / 120 |
| 数学评价 | 0 / 12 |
| 共享物理启动 | 2 / 8 |
| NMPC（含本次中断） / 固定回放 | 1 / 1；1 / 5 |
| PPO stages / actions / 独立评价 | 0 / 1；0 / 4096；0 / 1 |
| 额外确认 | 0 / 0 |

13 次真实请求均 HTTP 200、未知 0、重新发送 0。prompt 586,975 tokens（cache hit 375,168、miss 211,807），completion 50,589，total 637,564；金额未返回，保持未知。
原 ledger wall 为 747.9718436 s，包含恢复的保守边界与其他活动口径，不当作独立 CPU 时间或与数值耗时相加。

## 证据与结论范围

原 export 位于 `evidence/c3_autonomous_softarm/`；单个约 1.62 MB 压缩包封存原 artifacts、会话、事件、calls、ledger 及原中断进度。
活跃 Store 及原 worker 文件保留在 `runs/research/c3-autonomous-softarm-20261025/`。
Git 只保留原导出及约 31 KB 的 `supervision_summary.json` 审计摘录，不另建 Store、哈希清单或复制优化矩阵。
源码修复仍限于首次冻结前的 3 文件净增 12 行；新增 2 项定向测试与原 B 3 项回归通过。
运行中工程修复、migration、重新 NMPC、PPO、额外确认均为 0。归档交付前检查实际凭据不在归档或文本中。

本次只支持有限事实：Agent 独立提出并修正过科研假说、修正部分接口错误、生成一条合法控制并完成一次失败的独立回放，随后自主启动 NMPC。
没有证明单任务自主控制成功、结构自主生成/修改、重优化后的结构收益或跨任务泛化。
候选数始终为 1，结构未变，无公平结构重优化对照。未测方法或被用户中断的分支均保持未决。
该旧研究的消耗单列保留；用户另行批准的新“空白生成”Study 不继承它的科学反馈或候选。
