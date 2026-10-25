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
运行结果、消耗、真实错误、科学限制和最终 export 在完成后补充；旧 Study 的消耗与新研究分开列示。
