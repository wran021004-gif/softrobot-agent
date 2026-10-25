# C3：从空候选池自主生成结构与控制

2026-10-25（Asia/Shanghai）。本文件记录用户追加要求后的独立 Study，**不是旧 source-relative Study 的重置或改写**。
旧 Study 已由用户范围变更而中断、按原恢复接口结算、导出并提交推送 `e60c201f2`；实际消耗单列保留。

## 用户最新授权与设计起点

用户在当前聊天明确要求“直接从空白开始构造机器人”，并确认段数、腱数和结构参数均由 Agent 在现有生成器支持范围内自选。
用户另行授权新 Study 使用完整原额度：32 次 Provider、8 次共享物理启动、1 次 NMPC，旧消耗另列。
随后要求开放 PPO 等其他控制能力，完整执行生成—分析—控制—独立验收—终止链路，过程中简略说明实际输入和 Agent 决策，并允许依据过程动态调整预算。
既有确切 DeepSeek endpoint/数据范围以及 GitHub 仓库/研究分支普通推送授权继续有效。

Study `c3-blank-autonomous-softarm-20261025`；独立 Store、Provider/Strands 会话、数学/物理目录和导出。
使用原 `start_mode=family_space` 和 `serial_family_space_v2`，**初始 candidates={}、reference_candidate=null**。
不导入旧 C3、C1、A/B 的候选、成功控制、轨迹、结构排名、数学或诊断结果。
history、mathematics、control_seeds、supplied_evidence 全为空；由 Agent 自主 generate 或原注册 family search 生成首个科学候选。

原 Host 为校验接口而生成的最小兼容 scaffold 不是科学候选，不进入候选池，不产生比较基准或任务结论。
公开工程语法、部件物理原型、材料/尺寸/路由范围及默认值保留；不是从无物理模型任意发明机器人。
Agent 可自主选择 1–9 段、1–7 根可生成腱、合法 spans、长度、材料、截面、路由和原接口支持的控制参数。
1–12 腱是声明域，8–12 腱仍非执行验证范围；高段数动力学和控制仍需逐候选原准入，不能由声明域推定可控。
继承现有 family search 的 fidelity 约定：coarse 4 cells/段、standard 与最终评价 12 cells/段；首次成功门禁仅接受原最终 fidelity。
原搜索最多 16 个提案/12 次数学评价，仍受本 Study 共享数学额度；控制、结构方向和实验顺序不由 Codex 规定。

## 任务、能力与初始预算

复用预声明任务 `reach_hold_c3_mirror.json`：目标 `[0.29,-0.035,0.19]` m，0.35 s，控制/采样 0.01 s，MuJoCo dt=0.0005 s。
具名初态按每个生成候选展开为全部自由度零值，环境和原独立 evaluator/完整性规则不变。
终点/保持位置 ≤0.01 m，保持最大速度 ≤0.02 m/s，保持 `[0.30,0.35]` s 含端点六样本。
用户允许腱数自选，因此输入维数由生成候选决定；每通道使用原合法非负 SI 张力边界且上限不超过 8 N。

| 初始资源 | 总额 / 保护或子额 |
| --- | ---: |
| Provider requests / 收尾保留 | 32 / 6 |
| Public operations / 收尾保留 | 120 / 12 |
| 数学评价 | 12 |
| 共享物理启动 | 8 |
| GVS NMPC / 固定回放 | 1 / 5 |
| PPO stages / actions / 独立评价 | 1 / 4096 / 1 |
| 额外成功确认 | 0 |
| 单次 MuJoCo-direct callbacks / updates / knots | 60 / 2 / 4 |

GVS 与原生 MuJoCo 数学、受控 family 结构敏感性、控制初始化、MuJoCo-direct、原固定张力控制搜索、GVS NMPC、direct PPO 和兼容 residual PPO 均开放。
Residual PPO 仍需完整、真实、当前候选兼容参考；direct PPO 不依赖 NMPC。
所有物理子额度共享 8 次，PPO 评价保护及 rollout 对齐保持；没有科学墙钟超时。
方法开放不强迫 Agent 全部使用。若没有完整任务通过，由 Agent 依法 STOP；完整独立通过后公开读精确结果、SELECT，零额外确认封存。
初始额度不因“动态调整”变成无限额度；任何实际调整保留旧计数、用途、有限新上限和授权记录，不能靠改数据库或换 Study 逃逸成本。

## 启动前工程核验

新配置仅组合原 family defaults、v2 family space、任务、控制和运行环境，没有复制生成器、模型、Store、优化器或预算平台。
实际发现原首次 C3 新增的 native 限额字段不能经过 family defaults 严格 merge；在原 resolver 中与其他可选条款一样先提取、校验后冻结，修复 3 行，无科学数值改变。
复用两项 native 限额/旧目录回归，并加入 family 组合断言，2/2 通过。
零物理步预检通过原任务翻译、配置编译、native 全样本窗口适用性；没有生成科学候选或发送 Provider 请求。
使用兼容 scaffold 核验原 PPO 输入准备和实际 `.rl-pilot-env` 的 TensionEnv 初始化：1 通道、t=0、actions=0、physics_steps=0。
该检查只证明动态通道接口初始化，不是 PPO 性能、训练成功或全部拓扑兼容的证据；预检 XML/默认值不传入新候选池。
Strands/Provider、CasADi/MuJoCo/PPO 环境沿用已验证安装与单线程设置，未安装依赖。

## 监督与后续报告

首次 Provider 前提交配置并使用原 prepare/bind、formal_study_authorization 绑定新身份与最新用户确认。
实际 Provider 外发仍仅限冻结任务、工程语法/机器人参数、本 Study 数学与执行反馈、证据摘要和相关 Agent 对话；密钥仅鉴权。
监督更新简述“发给 Agent 的新事实”和“Agent 的实际决定”；不注入旧答案、控制方向或规定科研顺序。
未知请求/worker 先核验原 request_id、保存响应、生命周期和 receipt，按原 recover/Session Handoff 边界处理，不盲重发。
旧 Study 的消耗与新研究分开列示。以下记录本次实际运行和最终审计。

## 实际启动、候选与决策

冻结提交 `58a2b0240054b472aeebbfcb86125b893ea9a360`，resolved identity `a475211794a652b501233d75be4858d1d087e3e13c8396abf7bf8f9112e64190`。
第一次 Provider 前 candidates={}、reference_candidate=null，正式授权 `1e20a12f` 已绑定本次任务和实际用户批准。
Agent 收到冻结任务、家族生成语法/原型/参数域、注册方法、预算和本 Study 新反馈；没有旧实验结果或预置科学机器人。
公开工程默认值仍提供先验，因而“空白”不是无物理依据、无默认值的随机生成。

| Agent 的实际选择 | 原接口返回与后续决策 |
| --- | --- |
| 自主生成三段、三根全链腱机器人，最初指定圆截面 | 缺精确截面 stations，被拒绝；Agent 读取原型说明后改用继承截面 |
| 候选 A：长度 0.16/0.11/0.14 m，Young 4/3/3 MPa | 合法生成 `975aa07a`，未做数学或独立物理评价 |
| 候选 B：长度均 0.10 m，Young 15/15/12 MPa | 合法生成 `1237da3e`；三根全链 polar 腱、路由半径 0.018 m、guide_s=[0.5]、anchor_s=1；后续实算均用 B |
| 尝试 family mixed search | bounds/版本/必需字段错误，准入拒绝，没有实际结构优化求解 |
| sampled-affine-conic-minimax 能力分析 | halfway_waypoint 缺明确起始时刻，`KNOWN_ANALYSIS_START_TIME_REQUIRED`；反馈交回 Agent，数学计费 0，Agent 没有补齐重试 |
| 初始化 0.2 N pretension source，选择 native dynamics | 实算 t=0 力学 `4fcaf482`，0 个积分步；驱动映射奇异值约 196.62、155.34、2.64e-14，重力加速度约 [0,0,-9.81] |
| 首次 MuJoCo-direct：4 knots、40 回调、2 更新上限 | `32c60f88` 数值中断，保留 6 次完成进度，错误为 `FactorizeHessian: rank-deficient sparse Hessian` |
| 两次请求 GVS NMPC | 都在启动前因 host 解释器不等于冻结 research_python 被拒绝，NMPC 和共享物理计数未增加 |
| 选择原 physical control_search、局部有限差分 | `f4dd2486` 实际收费 4 次独立回放，3 个完整失败、1 个数值中断，没有通过任务 |
| 用重力矩/下垂估算初始化另一条控制，再请求独立回放 | source `2694405f` 合法生成，但 Plan 字段冲突，回放没有启动 |
| 再次自主选择 MuJoCo-direct，用上述 source 和新 knots/步长 | `36c6a8fb` 完成 27 次内部 rollout、18,900 步、2 次局部响应更新，返回 source `b1659375`；未独立回放 |
| 读取新证据并 STOP | 首次 STOP 缺精确实际读取被拒绝，Agent 修正后合法 STOP；没有 SELECT、成功门禁或任务通过 |

两个候选都是三段三腱；段数、腱数和参数由 Agent 选择，没有给定基准机器人。
A→B 确有长度、材料变化，但修改发生在数学/物理反馈之前，依据是 Agent 的几何、刚度和力矩启发式。
因此不是已经完成的数学结构优化，也没有结构收益对照；只有 B 进入动力学和控制评价。
继承截面实际来自不同部件原型；Agent 早期把它们当成统一圆截面，且最初使用 world 目标范数而非 mount-relative 距离，推理存在错误。
最终 STOP 已使用 mount-relative 目标半径约 0.2948 m，并承认先前校准不充分；不能因此追认早期假设已获验证。

## 数学优化与独立验收

本次确实使用了数学优化：完成的 MuJoCo-direct 对 3 通道 × 4 knots 的 12 个控制系数构造有限差分局部响应，再做有约束局部控制更新。
完成请求使用 knots=[0,0.08,0.18,0.30] s、difference_step=0.5 N、coefficient_limit=7 N、60 回调/2 更新上限；参数由 Agent 原请求决定。
其 baseline 是 source `2694405f`，不是原 pretension source，以下改善只属于该次局部预测。

| MuJoCo-direct 预测量 | 该次 baseline | 最佳预测 | 任务阈值 |
| --- | ---: | ---: | ---: |
| 保持最大位置误差 / m | 0.12580955 | 0.03590709 | 0.01 |
| 保持最大速度 / m/s | 1.25046943 | 0.09907601 | 0.02 |
| signed maximum excess | 61.52347 | 3.95380 | ≤0 |

最佳预测终点误差 0.03335428 m，停止原因为 iteration_limit，没有证明全局最优，仍未达到任务要求。
内部积分和预测不构成原独立 evaluator 的通过证据；该控制序列未做完整独立回放，不能作 SELECT。

| 独立回放 | 终点误差 / m | 保持最大误差 / m | 保持最大速度 / m/s | 状态 |
| --- | ---: | ---: | ---: | --- |
| `1900da20` | 0.1829815182 | 0.2045165255 | 0.7026189238 | 完整 valid_failure |
| `b71f7ec8` | 0.1830985098 | 0.2063212067 | 0.7281701175 | 完整 valid_failure |
| `d693bc81` | 0.1797167620 | 0.1930430869 | 0.4953749048 | 完整 valid_failure |
| `663a2387` | 未测完整终点 | 未覆盖保持窗口 | 未覆盖保持窗口 | execution_incomplete |

前三条各有 700 物理步、36 个含初态样本、6 个保持样本，张力边界和 solver_errors 检查通过。
最后一条保存到 0.21 s、22 样本，至少证明 420 个完整区间内积分步；异常区间的实际最后步数未知。
它也报告相同 Hessian 错误，不能把它算成完整失败轨迹或接受失败的有效任务分数。
只用保存样本重新调用原 evaluate_playback、playback_profile 和 assemble_acceptance，四条原 evaluator/profile/acceptance 均逐项一致；审计无新积分、训练或 Provider 请求。

Agent 的科学解释仍有局限：瞬时 tip 输入映射秩 2 不能推出整条机器人只有两个自由度，实际 native 模型是 72 个具名自由度、GVS 是 18 个坐标。
输入增益的单位带 N 的倒数，不能未经输入幅值/方向说明就和重力加速度直接比较并宣称驱动充足。
STOP 还把 `1900da20` 误称为派生索引；它实际是第一条独立物理结果，已由本次审计核验，原文错误不修改历史。
没有结构不可行、完整可控性、最优性、实时性、硬件有效性、鲁棒性、重复性或跨任务泛化结论。

## 数值错误的定位与恢复

失败原生搜索已完成 6 次 rollout 的进度/指标检查点，最后检查点证明 4,200 步、427 次 forward、1 次模型构建。
这些检查点不保存全部六条完整轨迹；第七次尝试的失败瞬间状态、约束信息和实际最后一步未留存，总尝试成本只能报告下界。
原 worker 把异常写成 execution_incomplete/error/reason，随后正常写文件退出，故 returncode=0 不表示科研计算成功。
没有把错误抹除或改写为优化不可行，也没有用成功请求替换失败记录。

报错位于 [MuJoCo 3.13.0 原生约束求解器的稀疏 Cholesky 分解](https://github.com/google-deepmind/mujoco/blob/3.13.0/src/engine/engine_solver.c#L2296-L2305)，不是外层控制目标的 Hessian。
另一次独立回放也触发此错误，而同一候选后来的另一组控制请求完成 27 次内部 rollout；这些事实都不足以唯一归因于模型参数、脚本调用或引擎数值问题。
中断物理回放最后 tip z≈-0.01746 m，冻结 floor z=-0.02 m；接近地面只是保存状态中的线索，尚未证明异常由接触触发。
已确认的工程诊断缺口是没有异常瞬间的完整故障快照；本次没有为追查根因另行改模型、切换求解器或额外启动科学回放。

监督进程原用 `.s135-env`，实际数学 worker 从一开始就使用冻结 `.mainline5-env`；因此不能将 native 搜索的前后差异归因于更换 host。
NMPC 的 exact-interpreter 门禁则确有 host 环境问题。所有 Provider 收据确定、无科学 pending 的边界暂停主进程，保存监督事件，改用冻结 `.mainline5-env` 并调用原 recover。
边界处 SDK 保留了一条 Agent 已提交但未启动的 analysis：原 tool ID `call_00_sRHu3s0cGBRgsmGnww833993`，原 Store/SDK 请求一致，outer/inner reservation 均不存在。
记录 confirmed-unstarted 证据后，以原输入和原 tool ID 调用现有 analysis.dispatch 一次；随后由原 recover_feedback 从真实 receipt 配对，未重算已完成操作、重发 Provider 或重写 SDK 历史。
恢复后的 Agent 没有重新选择 NMPC；PPO 能力一直开放但未请求，二者本次实际启动均为 0。
最终账本审计发现恢复工具的原 AfterToolCall 外层计数尚未落账；依照原 hook 用同一 tool ID、真实 feedback/inner receipt 补齐 1 次 public-operation 收据，没有新科研执行。历史 STOP 内容保持不变。
运行中生产代码修复和 migrate 均为 0；只纠正启动环境。

## 停止边界、预算与监督不足

本次共 31/32 个 Provider 请求，其中 25 个主会话、6 个 Reporter；HTTP 200 全部保存，没有未知结果或自动重发。
原收尾规则在剩余 Provider≤6 前就逐请求收紧动作，最终只允许证据读取和 STOP，尽管仍有 9 次数学、4 次共享物理、1 次 NMPC 和 1 次训练阶段额度。
Agent 原 STOP 明确引用这个受限边界，没有把预算停止解释成全局不可行。

用户允许过程中的动态预算调整，但监督没有在保护边界前完成有限追加；核验拟追加边界时 Agent 已合法 STOP，因此未追加、未重开 sealed Study、未重置成本。
这是监督不足，不是用户拒绝继续，也不是数学/物理额度耗尽。不能声称完成了 PPO/NMPC 实验或优化后独立验证的完整控制链路。
今后的有限预算追加应在保护生效前通过原授权/账本所有者完成；本次保留真实结果，不另建 Study 掩盖这一缺口。

| 实际资源 | 本次空白 Study | 已封存旧 Study（另计） |
| --- | ---: | ---: |
| Provider requests | 31/32 | 13/32 |
| Public operations | 32/120 | 14/120 |
| 数学评价 | 3/12 | 0/12 |
| 共享物理启动 | 4/8 | 2/8 |
| NMPC / 固定回放 | 0/1；4/5 | 1/1（中断）；1/5 |
| PPO stages / actions / 独立评价 | 0/1；0/4096；0/1 | 0/1；0/4096；0/1 |

本次 prompt 2,594,180 tokens（cache hit 1,764,480、miss 829,700），completion 143,872，total 2,738,052；金额未返回，保持未知。
原 ledger wall=877.5273754000373 s，是账本口径，不是纯 CPU 时间；已保存的数学内部积分至少 23,100 步，另有物理回放至少 2,520 步，不重复计成物理启动。

## 封存与可复查范围

原 export 在 `evidence/c3_blank_autonomous_softarm/`，保留原 artifacts、calls、会话、事件、预算、失败、参数和 design_package；`supervision_summary.json` 是适量审计摘录。
原文件检查点和最新 SDK snapshot 仅为归档追加到原 Store，不注册为新科研结果、不提供给已停止 Agent。
独立进程从原 SDK 恢复成功：Store 历史吻合、原 tool ID/result 配对、25 条 reasoning 消息和原 Provider 响应吻合，57 个 SDK 文件未改变；无审计 Provider 发送。
全部 70 个 calls 有收据（66 completed、4 failed），pending=null，无活跃资源占用；生产 core/science hashes 与冻结身份吻合。
注意原导出 claims 中“physically_constructed_and_validated_candidates”表示生成/编译合法性，不表示 A 已经通过动力学任务；A 未物理评价。
本次能证明空白候选生成、结构参数修改、局部数学控制优化和真实独立失败反馈的发生；不能证明结构优化收益或任何候选任务成功。
