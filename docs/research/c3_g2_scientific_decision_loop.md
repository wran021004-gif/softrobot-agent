# C3 G2：真实数学闭环完成，新增科研区分尚未证明

2026-10-25，Asia/Shanghai。基线 `576a18a0be6e77da6840d09ab1a2f4360d499f30`；
独立分支 `codex/c3-g2-scientific-decision-loop`，工作树
`D:/softrobot-agent/.worktrees/c3-g2-scientific-decision-loop`。

**真实 Agent 已自主选方法，经正式数学 Worker 得到结果，再提交第二项科研决策并 STOP。
但本轮没有新增对结构/控制失败机制的区分：计算完整复现了历史见证，历史背景又在 SDK 交付时被截断。
因此不把本轮宣布为“数学帮助提高科研决策质量”的通过案例。**

没有重跑完整 G1、A/B、半径敏感性，没有新独立物理、NMPC 或 PPO。
旧 Study、历史结果和费用均未修改。本 G2 完成后停止，未使用剩余额度重试。

## G1 混杂与最小工程修改

复用已有 scoped_context 登记及 Study 范围的启动说明，没有修改 Handoff 主体。
新离线状态使用原 B 组事实摘录，查询与原 F1/G1 查询逐值相同，artifact 为
`7a1ff0ae028c832f292eb475d6c11bb0c534dcd2dc03476d4a7edcdf8144e146`。
SDK request-feedback Handoff 后第二次请求仍在正常探索状态：

- 未进入 Provider 收尾保护；原查询通过实际第二次 evidence_read Schema。
- 当前 Store 有原摘录且能够合法读取，既有 scoped_context 中有该引用。
- read_state 显示首次读取；pending_feedback_delivery 携带原查询及完整成功反馈。
- 已确认第二请求之后，原 read_coverage 才给出完整交付信用。
- 启动要求明确是整个 Study 一次，Session 重启不重新触发；有科研目的的复核仍合法。

因此，**离线协议层面的 Schema 混杂已排除**。这不是新的真实模型不重读行为对照，
不补做或重新宣称上轮真实 G1 的独立语义验收通过。正式收尾保护及 SELECT/STOP 既有读取规则未改变。

生产修改只有两个文件，相对基线新增 23 行、删除 2 行，净增 21 行：

| 文件 | 修改 |
|---|---|
| tools/research/task_constraints.py | 单一公共 scientific_interpretation_v1，区分具名测量、模型计算、可检验假设和有识别力的因果结论；保留模型、输入、初态、通道、时间及有限时域边界 |
| tools/research/evidence_views.py | 将同一说明投影到 L1 方法/ResultCard/diagnostic_relations；诊断关系升为 v2；不能计算模型误差时明确标记 not_comparable_as_model_prediction_error 并列出缺失对齐条件；选定时间点标为离散观察 |

没有改研究 Agent、Reporter、数值求解器、物理模型或验收阈值；没有新解释模块或评分系统。
L0 仍是任务、重要候选、预算、最新反馈、简短轨迹与 L1 入口，完整新规则不进入 L0。
L2 仍保留原矩阵、轨迹、工具请求/反馈及来源。离线回归验证了 L1 规则存在、L0 不含完整规则、
对齐不满足时不产生 sample_differences、时间点列表与原观察一致。

## 新 G2 身份、授权与状态资格

Study 为 `c3-g2-scientific-20261025`。本轮用户附件
`0b9bc8a1-5d03-48e6-84fc-1edfee7abd87/已粘贴的文本.txt` 的新授权经既有
formal_study_authorization、resolved_identity/scope_identity、require_authorization 与 core.bind 登记。
冻结上限为 Provider 8（含 Reporter）、数学评价 4、public operations 24；独立物理/NMPC/PPO 均为 0。
保留 1 次 Provider 和 2 次公共操作的原收尾保护，未移除或扩大。

从原 FamilySpace 重新生成历史 B 组第 6 个合法设计，而不是将旧候选 ID 注册成新候选：

- 当前候选：`a69eab40a69718d1c6e4f5a395d4615eea68c1e13392e39a2a5d335d3159f374`。
- 实际为 **2 个柔性段、4 根腱**，段长 0.16/0.11 m，杨氏模量 10.45/5.4 MPa，
  各段 12 cells，四路由半径均为 0.018 m；控制速度权重均为原 0.1。
- 原参数、robot/task、backend/discretization/dynamics_model/controller 与历史设计逐值核对一致；
  当前候选通过 verify_candidate，带当前 profile、任务及模型身份。
- 任务目标 [0.29,-0.035,0.19] m，时域 0.35 s；位置限 0.010 m，
  最后 0.05 s 保持速度限 0.020 m/s；控制/采样 0.01 s，物理网格 0.0005 s，原零初始化不变。
- 原 B 执行终点误差 0.0040920124283 m，保持误差 0.0045172352418 m，
  保持峰速 0.181733582553 m/s（0.31 s），0.35 s 约 0.050052 m/s。
  这些是原 Study 的历史观察；没有登记到当前 results 或 physical_replays。

完整来源保存在当前 Store 的原始历史 artifacts 和独立背景引用中，仍保留历史身份。
原 update 30 对应 0.30 s，有原生 qpos/qvel 和 30 段实测输入前缀，没有完整 integration checkpoint。
现有 native_point 的 execution 路径要求当前 Study 拥有执行；没有已登记的跨 Study 原生状态重绑定。
未手工改 candidate、configuration_identity 或准入标志，未伪造工作点，也未启动前缀积分。
初态的原生方法及符合原前提的有限时域方法仍可由 Agent 自选。

准备阶段验证入口漏导入 record，已在任何 Provider/数学请求前修复，并恢复同一 Store；
没有重建 Study 或重置预算。随后通过 core.bind 明确迁移到
`fc170f6f43ea0e1c4095b37e106e3bf3b347bd81`，原候选/profile 和零费用保留。

## Agent 自主选择和真实执行

Host 没有指定研究方法、控制改进方向或失败机制。Agent 读取通用规则及两个候选方法说明，
最终选择 **sampled-affine-conic-minimax-v1**，operation=task_capability，
operating_point=controller_start_input，申请 2 次数学评价。

首个 Plan 的问题是：当前设计在输入盒和冻结时域内是否存在同时满足终点位置、保持位置和速度的
局部采样模型控制见证；用负违规值及独立离散回放支持它，非可行结果或不收敛削弱它。
其理由是据此决定后续是否保留结构并研究控制/物理实现。

首次 Plan 引用了可读但未注册的 FamilySpace 来源，被正式准入以 UNREGISTERED_RESEARCH_EVIDENCE
拒绝，没有执行科学计算。Agent 自行删去该引用、提交合法 diagnose Plan，再自行调用 research_analysis。
没有由 Host 改写假设或补造工具参数；没有因为其自然语言错误阻断第二次决策。

唯一数学结果为
`72e8f77672d288b6cc48e20a6344792eb626cb1f3722e59a622a678b13819a16`。
原始请求、Worker 边界、结果、运行环境、原 response/reasoning、Plan 和收据均在
[标准原始证据导出](../../evidence/c3_g2_scientific_decision_loop/immutable_artifacts.tar.gz)。

| 真实数学计算 | 数值 |
|---|---:|
| 状态 / 结论 | computed / feasible_witness |
| 重放归一化最大违规值 | -0.19999999999954968 |
| 终点误差，0.35 s | 0.008000000000002585 m |
| 保持位置最大误差，离散样本 | 0.008000000000004504 m |
| 保持速度最大值，离散样本 | 0.013754640667324113 m/s |
| 任务检查 | 13/13 通过：终点 1、保持位置 6、保持速度 6 |
| Solver | CVXPY/CLARABEL，optimal，16 iterations |
| 重放 support gap，浮点估计 | 8.498421411e-11 |
| 见证最小张力裕度 | 1.464828119952446 N |

这是 model.gvs@1.0.0 的局部连续仿射模型、24 维状态，工作点来自冻结零初态与预张力准备，
不是静力平衡点；未使用历史 0.30 s 状态。计算张力边界是每路 [0,8] N；预张力为 0.2 N，
结果中的 lower=0.2 / upper=7.8 是该工作点到两边的裕度，不是新的输入边界。
见证张力实际范围约 1.466559–6.535172 N。控制见证是四路、35 个 ZOH 区间，
0–0.35 s、步长 0.01 s；保持检查只覆盖 0.30–0.35 s 的六个离散点。
模型假设包括不可伸长、无剪切/扭转、无摩擦直腱及所选应变基适用。

独立离散 replay 通过及 numerically_checked 是模型内数值状态，不是严格最优值、连续时域合规、
全局非线性可行、MuJoCo 任务通过或硬件结论。没有用另一套控制的历史速度相除来计算预测误差。

## 反馈与第二次科研决策

实际第 7 次 Provider 请求（第 6 次主 Agent 请求）携带新 ResultCard/L1、结果引用、
精确 witness 值、2 次评价成本、模型/时域范围和 Reporter 的非权威解释。
核对的是保存且已确认响应的原始 wire，不是事后重构包。
第二个成功 Plan 为 STOP，引用新数学结果，描述了保持结构、把 capability_sequence
转成完整控制序列并做独立物理回放的后续方向；本次没有执行该方向。
Reporter 只解释了结果，没有替主 Agent 选择该行动。

模型确实使用了新数值、13 个检查和原时域，承认局部模型与物理实现之间仍有差距。
但它没有按额外启动说明对数学原文或 STOP 全索引再做公开 evidence_read；原核心接受了本轮 STOP。
没有补造读取、没有为报告授予 SELECT/STOP 的独立读取信用，也没有更改既有准入规则。

有三类限制需要与闭环执行成功同时保留：

1. **科学信息重复。** 与历史结果 `87d62673…22931` 比较，A/B/C/D、x0/u0、drift、
   endpoint_outputs 完全一致，applied_input_n 与重放分数也完全一致。
   新增的是当前 Study 拥有的合法见证及来源绑定，没有新增对控制不足、结构限制或模型误差的区分。
2. **历史背景没有完整交付。** 8661-byte 原背景被既有 SDK offload 截为 2122 字符预览；
   历史速度失败阈值可见，但旧见证分数和原 Study 来源不在该预览，Agent 没有取回全文。
   read_coverage 正确保留 not_confirmed_in_provider_request，不能把“工具 full 读取成功”称作完整交付。
   因而不能将重复选择完全归因于 Agent，也不能声称它在看到完整既有见证后仍独立选择了信息增益最高的实验。
3. **解释和成本仍不可靠。** Agent 把实际 2 段说成 3 段，写了不符原记录的历史位置误差
   0.00305 m；又从模型见证和张力裕度过度推断不能再归因于结构/张力限制，并声称后续只需调控制权重。
   这些因果排除没有得到本轮验证。它还把工作点张力裕度误写为 [0.2,7.8] N 输入盒；真实边界为 [0,8] N。
   window_normalized_v1 在原控制 Schema 中合法，但原冻结模式仍为
   time_integral_v1；更改模式需要新的绑定与准入，本轮没有验证改善效果。它把提前量、模式和速度权重
   统一说成 [0,1] 域，没有按各字段的真实单位与域说明。它对控制初始化和物理回放的预算口径也未分清。

后续成本的审阅口径是：合法 capability_sequence 初始化不调用求解器或物理；
一次完整独立回放另需 1 个物理启动、约 700 个原生步，初始化与回放各有公共操作，读取/决策另计。
跨新的执行身份仍须走正式来源准入，当前已 STOP Study 不因此重新开放。
这是审阅者对已有接口的核对，不是 Agent 自己已正确提交并执行的完整下一实验预算。

## 科研价值评价与最终问题

| 观察维度 | 本轮结果 |
|---|---|
| 科研有效性 | 合法方法覆盖真正未满足的速度约束，但重复已有同一模型/输入见证，未减少机制不确定性 |
| 行动相关性 | 产生当前候选绑定的控制见证；Agent 提出同输入物理回放，具有明确可验证对象 |
| 任务针对性 | 同时检查原位置/速度/时域，无无关数学扫描；没有改验收条件 |
| 反馈利用 | 消费数值并具体化未来控制序列/物理验证；核心假设未因新证据发生有辨别力的修订 |
| 资源效率 | 未越界或追加实验；重复计算和一次引用修复消耗了预算，不能称为高效科研探索 |
| 证据可信度 | 原准入、Worker 与交付真实；Agent 的跨模型因果排除、细节和预算解释仍有错误 |

**最终回答：严格按“比实验前更清楚如何找到任务可行解、且有新增可信依据”衡量，本轮答案是否定的。**
不能因为工具跑通、分数为负或错误数量减少就认定自主科研决策能力通过。
本轮的有限价值是补齐当前 Study 的合法见证和具体实验对象；它没有证明更应该改哪一项结构、
哪一项控制参数，亦未证明可以排除结构限制。保留该价值与错误，不将整轮当作毫无结果。

主要瓶颈先在**历史证据交付与状态来源绑定**，随后是 Agent 对结果的因果解释和重复实验的信息增益判断。
最小下一步是在另行授权的合法范围中，将历史核心事实压成能够完整交付的简短摘要，
把旧数学见证和原 Study 来源放在摘要内，原轨迹留 L2；再以本轮 Agent 已提出的同候选、
同初态、同通道、同完整 ZOH 输入和原网格做一次独立物理回放，保留对齐预测与原生状态。
它才可能区分该见证在后端的实现与模型预测差异，并给后续控制改进或原生数学方法提供真实工作点。
这不是当前 Study 已执行的行动，也不能预先断言结果会支持控制权重优化。本轮到此停止。

## 成本、验证与提交

| 资源 | 实际 / 上限 |
|---|---:|
| Provider，主 Agent + Reporter | 6 + 1 = 7 / 8 |
| 确认响应 / 未定发送 / 自动重试 | 7 / 0 / 0 |
| Prompt / Completion / Total tokens | 166267 / 12348 / 178615 |
| Cache hit / miss；reasoning tokens | 46720 / 119547；7237（含在 completion） |
| Public operations | 8 / 24 |
| 数学评价 | 2 / 4：模型准备 1、CONIC 内部求解 1 |
| 主要数学实验 / 内部 CONIC / dual-face | 1 / 1 / 0 |
| 数学 Worker 计时 | 9.1907582 s |
| 内核 / solver wall / solver solve | 0.6892389 / 0.0160400 / 0.0027954 s（嵌套，不能相加） |
| Provider 计时合计 | 76.485 s |
| 原生积分步 / 独立物理 / NMPC / PPO | 0 / 0 / 0 / 0 |
| 余额 | Provider 1、数学 2、公共操作 16，均未使用 |

Provider 未返回金额，金额为 unknown。通用 ledger.worker_calls=0 是其公共账本字段，
不表示数学 Worker 未启动；真实数学执行由 analysis reservation、Worker result/boundary 和数学评价计数记录。
没有 pending 数学任务、未消费 Provider 响应、未结算 reservation 或占用资源。
无同查询重复 evidence_read；两种 task_capability 方法说明的读取是方法比较。
没有把摘要视图或 SDK 截断预览当成完整原始读取。

定向 unittest 共 4 项通过；将 G1 回归进一步收紧为原历史摘录和原查询后，仅重跑该项，3.141 s 通过。
另对实际 G2 原始请求/候选/Worker/成本/第二决策包做只读 audit-g2，通过；
不以自然语言审阅断言替代科学准入。未跑全仓测试或追加科学实验。
SDK 测试中 RequestBoundaryHandoff 是预期轮换控制流，最终测试结果为 OK。

工程提交 `d03fb39b5fbe385e0eac2af8d936601896473f5d`；准备恢复修复及真实执行冻结提交
`fc170f6f43ea0e1c4095b37e106e3bf3b347bd81`。验证代码仅扩展既有
`tests/research/c3_g1_g2_validation.py` 和 `test_c3_g1_g2.py`，没有新运行框架。
原始证据使用 core.export 的现有 archive/calls/configuration/disposition/ledger，
没有新增 SHA manifest 或第二套收据系统。

详细核对见 [review.json](../../evidence/c3_g2_scientific_decision_loop/review.json)，
冻结授权与候选资格见 [protocol.json](../../evidence/c3_g2_scientific_decision_loop/protocol.json)。
本报告及证据所在最终提交 SHA 随最终交付给出，避免文档自引用；普通推送目标为
origin/codex/c3-g2-scientific-decision-loop。最终交付同时核对远端 HEAD 与本地一致、目标工作树干净。
主工作树的原有未跟踪文件和其他 worktree 保留原样。
