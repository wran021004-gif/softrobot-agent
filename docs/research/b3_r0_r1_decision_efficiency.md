# B3 R0/R1：科研决策交付修复与有限自主研究

2026-10-26，Asia/Shanghai。基线 `research/b3-m2-live-pilot@f98b979fbbc69f77f8593ad1759cb4a761545332`。
独立工作树 `.worktrees/b3-r0-decision-efficiency`；旧工作树、未跟踪文件及 M2 STOP Store 保持原样。
授权来源为用户本轮附件 `64a01c75-f0df-477b-95aa-ad3d952d4231/已粘贴的文本.txt`。

## R0：已完成的最小修复

M2 C 逐轮审计已证实：native 方法的完整 L1 反馈带 `execution_limits=8/2/4`，
SDK offload 后该字段可能处于被截断的中间；`mathematical_catalog` 已保留它，
但 `compact_scientific_delivery(decision_only=True)` 再次按白名单投影时删掉它。
因此不能将后来的所有越限都解释成模型明知上限仍忽略。

修复仅让原 `native_control_limits` 派生字段通过 L0，未增加第二份限制配置。
候选身份仍由目录顶层 candidate 和方法键标识；同一短包每次在 SDK offload 后加入完整 wire，
Handoff 新会话继续从 Store 重建，因此无须扩展 `session_handoff.feedback_delivery` 或复制历史。
大型反馈仍有原 `original_result_query`；完整方法、矩阵、控制和轨迹仍在 L1/L2。

| 已有文件 | 最终行为 |
|---|---|
| research_context.py | L0 保留 execution_limits 及两个准确的 L1 查询，不复制方法详情 |
| task_constraints.py | 实测 NMPC 控制初始化 source/parent 查询；已授权 T2 缺模型组时给 readiness 查询和准备说明 |
| agent.py | 真实 Plan Schema 对有实际候选的四类动作要求非空 decision.selected_candidate；缺动作 payload 指明字段；非 evidence_read KeyError 不再误报 JSON Pointer；不支持方法—模型组合、protocol 扩展和控制 parent 反馈精确化 |
| contracts.py | 现有候选/source/parent、analysis protocol、JSON Pointer/fields 描述明确绑定和按需读取；不改变 Plan 版本或替 Agent 填参 |
| native_control.py | 原 not_applicable 原因显示选定状态时间、收到的窗口及冻结初态 0 s；数值算法不变 |

Schema 不能表达两个 EvidenceRef 的运行时相等关系；原 `admit_decision` 仍是唯一权威验证，
未复制候选身份检查。R0 减少的是重复调用错误的接口来源，不宣称此后模型永不犯错。
T2 保留 registered / study_authorized / authorized / applicable / executable 和实际 missing，
准备提示不覆盖依赖、预算、STOP 或收尾保护，也不自动选参数/执行 T2。
原 readiness 提供五个授权参数的值/界、h 与 h/2、模型组、成本与原请求模板。

## R0 验证与资源

六项定向 unittest 全部通过（59.432 s）：

- 新 M2 B/C 原始完整 wire 对照：开局、首反馈、收尾各一边界；真实 formatter 和 Schema；同会话及 Handoff 投影。
- 新真实 Schema 和准确错误反馈：缺 candidate、缺 selected_candidate、非指针 KeyError、JSON Pointer 子键、MuJoCo/instantaneous_braking 不支持及非法 protocol。
- 复用 M1 缺组/完整组/原 dispatch/生成/L1 测试（明确的离线合成模型，不是新数学证据）。
- 复用 B3 G2 完整历史 wire、offload 及 L1/L2/历史所属 Study 隔离两项回归。
- 复用真实 SDK request-feedback rotation（显式 mock HTTP，原恢复/配对边界）。

简洁对照见 [offline_wire_comparison.json](../../evidence/b3_r0_decision_efficiency/offline_wire_comparison.json)。
原六个请求成员另用既有 `archived` 校验归档与内容身份；原 messages 和 STOP 身份未写回。
对照是离线重建的完整请求，不冒充真实新增发送。实际 rotation 是独立离线 SDK 测试。
最终对照进一步固定为原封存 L0，仅替换本次改变的方法目录和真实 Schema，
避免用最终 snapshot 的控制/报告字段推断早期上下文；该单项收紧后再通过（9.363 s）。
首轮发现新增目录常量缺局部导入、archive fixture 用最终余额误触收尾保护，均已修正；
这些失败发生在零 Provider/科学执行下。保存对照重复了唯一 archive 测试，没有扩展全仓测试。
未修 S130 无关 fixture。

生产五文件 `+31/-14`，净增 **17 行**；测试只扩展既有 `test_b3_t2_readiness.py`。
R0 实际 Provider、真实数学、MuJoCo 步进、NMPC、PPO 全为 **0**。
读取了 M1/M2、C 逐轮审计、C3 A/B、F1/F2、G2 与 S140–S145；
保留局部模型平台/退化、历史跨任务及同输入预测对齐的科学边界，未重算封存实验。

## R1 最终结果：找到名义仿真任务的通过解

唯一 Study `b3-r1-history-assisted-050` 最终为 **stopped / accepted**。
主 Agent 完整读取 fresh 回放，精确 SELECT，配置的额外确认次数为 0，因此立即封存。
没有在首次通过后启动新的科学实验。交付物是当前结构及一条完整开环张力序列，
不是已验证可泛化的 NMPC 闭环策略。见
[design_package.json](../../evidence/b3_r1_history_assisted_050/design_package.json)、
[final_audit.json](../../evidence/b3_r1_history_assisted_050/final_audit.json)。

| R1 独立评价 | 终点误差 m | 保持位置峰值 m | 保持速度峰值 m/s | 结论 |
|---|---:|---:|---:|---|
| 开局参考结构 NMPC | 0.003148373 | 0.006038027 | 0.111373944 | 完整失败，仅保持速度不满足 |
| 新结构/新配方 NMPC | 0.004033428 | 0.004033428 | 0.043009682 | 完整失败，仅保持速度不满足 |
| 同一新结构，native 优化序列的独立回放 | 0.004169056 | 0.004504720 | **0.019934320** | **全部验收项通过** |
| 冻结上限 | 0.010000000 | 0.010000000 | 0.020000000 | 原 evaluator |

保持速度余量仅 **0.00006568027 m/s（阈值的 0.3284%）**。全程 0.50 s，
保持窗 [0.45,0.50] s 的六个采样点完整；张力边界、执行完整性和评价有效性均通过。
原结果明确 continuous_time_guarantee=false。没有实机、扰动鲁棒性、连续时间保证、
重复性或全局最优证明；本轮不追加成功确认或大型 Benchmark。

## 授权、冻结与首段 STOP 的保留

初始研究身份为 `a5754add34ed56639bacb431e256569d03a99c9094a1f7af63f75d56411b718a`，
执行冻结从 `7283d07d652d2a382e16e2ba33e9b99533572414` 开始。
最初自动审批要求聊天确认 DeepSeek 地址/数据范围及公开 GitHub 披露；用户分别确认后，
`7922de156` 已推送并启动真实运行。出口始终为
`https://api.deepseek.com/chat/completions`，使用 `deepseek-flash`。
仅发送冻结任务、必要结构/控制、授权 M2 背景、工具定义及本 Study 反馈；凭据仅认证。
[preflight.json](../../evidence/b3_r1_history_assisted_050/preflight.json) 保留初始零费用快照，
不能把它当成最终账本。

累计预算经三次明确聊天授权增加：

| 阶段 | Provider 总额 | 公开操作总额 | 生命周期 |
|---|---:|---:|---|
| 初始 | 48 | 96 | 原唯一 Study |
| 首次增额 | 96 | 192 | 同一累计账本，修复后继续 |
| 第二次增额 | 144 | 192 | 用户选择再加 48 Provider |
| 已封存非通过段后的授权追加段 | 144 | 288 | 用户明确批准 +96 公开操作并保留旧 STOP 继续 |

保护额度仍为 Provider 4、公开操作 6，包含在总额中。数学 26、独立物理 4、NMPC 2、
回放 2、native 每次至多 24 callbacks/3 iterations/4 knots、总 native 积分 60,000、
两结构各至多一次 NMPC/native 优化/完整回放、PPO 0 等科学上限均未提高。

首段在 Provider 99、公开操作 190 时因公开操作保护合法 STOP，并非 Provider 用尽。
旧 STOP `90e356dcc684c02f4e557065afc9f982d235dd8b14e777b62bc8d6e35ae0221a`、
其封存状态 `3ec99043dd08a2f5c198e92b53c3fef308c0159bf6413896aa93ca8cf48faf21`
及全部收据/费用保存在原 Store，见 [closed_segment1.json](../../evidence/b3_r1_history_assisted_050/closed_segment1.json)。
追加授权 `450679a6abd1bb18bda17d1a9209b5e30cef730d70cf582e5c0e602f71b3588d`
经原 completed-invocation Handoff 建立新 SDK 会话，恢复关闭阶段移除的合法工具。
普通 STOP 封存规则未放宽；模型没有获得自行重开或自动扩额工具。

最终 resolved_identity 为 `023ff511358affa9f4cbcdf118b742a01f5e60ecea7c4916108e97ab0cd9df52`，
实际执行冻结为 **`b00484525cbb4514896d50757755841d91fd2d01`**。
全部迁移保留结果与费用，scientific profile 仍为 version 1、
`ac839350f3b571664cdfbb38d88a90859971b21be7d8b06d0a420c1f95dea37c`；
没有改变动力学、求解器、任务或独立评价的科学语义。

## Agent 的实际研究路线与新信息

1. 使用 M2 历史但重新执行参考结构 NMPC。Agent 假设显式保持/终端速度代价能进一步
   降低历史余速；实际仍是参考配方，结果与旧参考速度 0.11137394399884916 m/s
   一致，是新的 fresh 复现，不是新控制机制或性能改善。
2. 自主生成新结构：近端首段 Young 模量 10.45→9.0 MPa；同时将保持/终端速度权重
   0.1→1.0、制动提前量 0→0.06 s，并执行该候选自己的 NMPC。
   原机器人差分还记录一处 angle_rad 浮点表示归一化，详见 physical_comparison.json。
   Agent 依据参考结果仅速度超限，选择更强且提前生效的制动代价。速度降到
   0.043009681835387996 m/s，仍失败。材料与配方同时改变，不能作结构单因素归因。
3. 多次调用/引用错误后，成功绑定本结构实测 NMPC 序列。部分 diagnose Plan 仅完成
   只读诊断，numerical_evidence=[]；两次早期 research_analysis 均在计算前被拒。
   不能把这些记录描述为优化器已经运行或搜索证实失败。
4. Agent 判断余速仍可通过当前结构的后段张力修正消除，授权追加段终于通过
   research_analysis 执行 mujoco_direct_control_v1。
   实际设置为 4 knots [0,0.3,0.4,0.5] s、8 个活跃系数、2 N 系数界、
   24 次评估请求上限、最多 2 次外层迭代、safety_margin_fraction=0。
   在原 0–0.50 s 全窗完成 **10 次 rollout、1 次响应更新**，局部目标达到即停。
   最佳非线性预测速度 0.019934319730102207 m/s，数学结论仍为 native 数值诊断，
   本身不授予任务通过信用。
5. 对返回的精确序列执行独立完整回放。终点/保持位置/保持速度与 native 最佳预测
   在记录精度内一致；原 evaluator 首次通过。随后公开完整读取并精确选择该回放，自动停止。

最终序列来自 **当前新结构自己的实测 NMPC 输入**，不是把历史 M2 成功信用或控制源
重新标为 fresh。相对该结构 NMPC，保持速度下降约 53.65%；相对历史 M2 C 最好速度
0.08788779126447174 m/s，下降 **77.32%**。这证明当前固定新结构上的控制修正可以
完成本名义任务，不能证明参考结构充分控制优化后不可行，也不能证明改结构额外有益。

T1/T2、CONIC、dual-face 和相关模型组准备实际均为 **0**。
真实 L0 持续给出 T2 registered/authorized/applicable=true、executable=false、
missing_validated_model_stencil 和准确 preparation_query；进入保护后另有 protected_closeout。
Agent 未读取或准备 T2 模型组，实际偏向实测输入的 native 控制路线。
不是无数学预算或无授权，也没有新证据证明 T2 平坦、退化或无效。

113 个主请求中，真正发起新科学计算并产生结果的主请求为 **#5、#16、#109、#111**：
两次 NMPC、一次 native 分析、一次独立回放。#5 是历史结果的 fresh 复现；
其余三个带来不同性能、控制见证及任务验收信息。Reporter 解释与历史阅读不计作新科学计算。
追加段合计新增 **18 次 Provider、30 次公开操作、1 次数学分析、1 次独立回放**。
这不是修复有效性的受控对照，不能单独作因果效率结论。

## 交付与恢复中实际修复的缺口

| 提交 | 最终行为及定向验证 |
|---|---|
| b5362f9c3 | Reporter 保留派生查询 view，raw 引用不伪造投影子路径；准备失败回退，五项测试 2.743 s；真实恢复报告 available |
| 69a82930f | 精确 request_template_query，原 Handoff 3,000 bytes 内保留模板/限制/初始化，三项测试 25.185 s；真实长反馈保留 2,849 bytes |
| a29f37134 | 原动作意图映射直接返回所需字段和值，不复制验证权威；定向测试 1.066 s |
| 3b5d68bd8 | 仅明确授权的非通过 STOP 可追加段，原 Handoff/旧状态/费用保留；两项测试 5.566 s，中断恢复单项 3.336 s |
| 58e84d45c | 派生视图保留 view 后选择对象 fields；错用 raw 路径返回经原读取器验证的查询及缺键，三项测试 16.493 s，补充单项 22.671 s |
| 19b3cc1b6 | 只恢复固定初始消息/固定提示且 Handoff 后尚无发送的 SDK 边界；任意改写仍拒绝，三项测试 6.557 s |
| b00484525 | 原快照/响应按旧 Schema 验真，新请求再更新当前查询 Schema；定向测试 3.241 s |

所有测试显式离线/mock HTTP，未为测试新增真实科学执行。对真实追加段失败请求的离线纠正
可得到 **459 bytes** 的绑定字段结果；不冒充新增实际发送。原错误、失败与历史 Snapshot 未改写。真实新请求
`750f31021872678dc1f10dfcd86038d80fa19be875489ff8240c91aac0812888`
已含新 fields 说明、24/3/4 限制和追加授权说明，且未处于保护。
首次科学反馈后的实际完整 wire 及后续迁移证据见 first_feedback_wire.json、
reporter_repair.json、template_delivery_repair.json、derived_fields_repair.json、final_audit.json。

## 科研效率、错误与后续计划

| 同口径原 Store 统计 | M2 B | M2 C | R1 累计两段 |
|---|---:|---:|---:|
| Provider，主 Agent + Reporter | 32，31+1 | 29，26+3 | 117，113+4 |
| tool_request_error | 13 | 9 | 42（含 1 次监督迁移门禁） |
| candidate mismatch | 4 | 1 | **0** |
| evidence_read | 26 | 19 | 178 |
| 完全相同读取载荷重复 | 8 | 4 | 76 |
| 只读主请求 | 18 | 11 | 90 |

R1 另有 3 条 SDK/钩子失败（临时引用失效 2、收尾动作钩子 1），合计 45 个原始失败工具反馈。
不能把监督门禁归责 Agent，也不能把全部路径拒绝归为模型故意忽略已知字段。
具体错误与完整原输入查询见 [agent_error_inventory.json](../../evidence/b3_r1_history_assisted_050/agent_error_inventory.json)。
完全相同请求可能读取已变化的动态视图，76 不等于 76 次无价值读取；但最终整体读取比例
与错误/重复数仍高。候选绑定和真实约束可见性改善，不代表科研效率已经充分解决。

[Agent 错误修复计划](b3_r1_agent_error_repair_plan.md) 已分清已实施和待实施：
优先继续改善已有绑定源/来源状态的短包、raw/wrapper 查询配对、意图 Schema 的单一映射、
只读诊断与实际计算状态、列表对象 fields 的具体导航及 STOP 预算表述。
不新建 Agent、Store、计费账本、搜索器或通用调度框架。

## 最终资源与结论范围

| 资源 | 实际消耗 | 未使用 |
|---|---:|---:|
| Provider / 公开操作 | 117 / 220 | 27 / 68 |
| 数学分析原账本 | 1 | 25 |
| 独立物理 / NMPC / 完整回放 | 3 / 2 / 1 | 1 / 0 / 1 |
| NMPC 在线 NLP | 10（两次各 5，均达迭代上限但按原规则可用） | 不解释为收敛 |
| T1/T2 模型准备 / CONIC / dual-face / PPO | 0 / 0 / 0 / 0 | 原上限保留 |
| native model build / callbacks / rollouts / response step | 1 / 10 / 10 / 1 | 上限未用尽 |
| native 外层迭代 / 内部局部 solver 迭代 | 1 / 16 | 两个不同口径 |
| native 积分 / 独立物理积分 | 10,000 / 3,000 | 总实际 MuJoCo 积分 13,000 |

Provider 原接收 usage：主 Agent 4,942,458 tokens，Reporter 76,808，总计 **5,019,266**；
金额未由原回执提供，记为 unknown。原共享 wall 计费 6,265.649 s，numerical_s=959.233 s；
它们与 worker/kernel 时间属于不同口径，不能重复相加收费。
最终所有 117 个唯一请求均确认 HTTP 200，无未知发送、pending、占用、未消费响应或悬账。
停止原因是首次 fresh 独立通过及精确选择，不能把剩余额度写成耗尽。
公开操作是原共享账本的工具操作：178 次 evidence_read、12 次 retrieve_context、
20 次 Plan、3 次 analysis、1 次 investigate，加上原执行链 simulation/evaluation/profile
各 2 次，共 220。原 Agent 工具请求 214 与共享账本 220 是两个明确口径。

工程链路已接通并实际交付；Agent 最终正确完成源绑定、native 计算和 fresh 选择，但效率仍差。
新数学信息是当前结构上的 native 非线性控制见证；新独立物理信息是其名义完整任务通过。
结构修改的额外价值仍未证明。后续科学问题是极小通过余量是否稳定，以及相等控制机会下
参考结构能否同样通过；需另行授权的对照或鲁棒性研究，本轮不继续。

## 可复核交付与原引用

最终设计包、configuration/disposition/ledger/calls、review/final_audit、原不可变 artifacts
及 snapshot 已由原 export 导出到 `evidence/b3_r1_history_assisted_050`。
完整归档只保留一份累计版本，首段封存状态和 STOP 仍在其中；初始 preflight 保留其时间语义。
archive_manifest 给出原归档与成员身份；凭据扫描通过，见 delivery_verification.json。

| 对象 | 原 artifact_id |
|---|---|
| 当前结构 | e85fc8e3eb57e05bfef71db74885db619ce316f90cb9e9b88dc3e971e01f7543 |
| 本结构 NMPC 实测输入来源 | e3a06aa1b8d89ec98216cf6d86edfe264c22f8f725b453ded02e1ed0cfaa4a48 |
| native 数学结果 | bc67e08a41e529120c54086ba2e0dcf16f0b6de35fff941b054165f658089ff8 |
| 优化后完整控制序列 | b34d0feb1a38617f8b7dadd8c7aea92c08940042124786de359ccc0d5c8f2115 |
| fresh 独立通过结果/选择对象 | b5b6cac95a96ab3ce235cb1e4244ffdaa5de34777ec379788d32a8b1adbda95f |
| 原独立 evaluator | e9071ee24a4c62123c8651729e1bb851c1b72a0735935958e28d899da159ef5a |
| 完整仿真轨迹 | 5ff0ffeed6ef9c35ea34d8360b8f4e94cf78f29906f2b5625d5e1b2be1937250 |
| selected_solution | 5665d483dfc7873f6349f3cc84114d96696ccf76e9d6e97d93dbea8c9abe50ac |
| 最终 SELECT disposition | a445b9128435365e9c7429fea54329ea6a3a958351e2b604170752619c1af0d8 |

普通推送目标始终为 `wran021004-gif/softrobot-agent` 的
`research/b3-r1-autonomous-pilot`。执行冻结 SHA 与后续文档/证据交付提交分开；
最终交付 SHA、远端 HEAD 和工作树状态在推送核对后于聊天报告。
