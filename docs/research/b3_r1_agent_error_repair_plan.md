# R1 Agent 错误记录与后续修复计划

2026-10-26，唯一 Study `b3-r1-history-assisted-050`。本计划基于原 Store 事件，
不把失败请求、只读诊断或历史阅读算成新科学计算。后续项目尚未实施。

## 取证快照

快照截至事件序号 **1511**（序号仅便于定位，内容身份见 JSON 原引用）。
累计 Provider **82/96**、公开操作 **151/192**；数学 **0/26**、NMPC **2/2**、
独立物理 **2/4**、完整回放 **0/2**、native 优化和积分均 **0**。
用户已再次明确批准 Provider +48，迁移后总上限为 **144**，公开操作仍 **192**。
因此仅增加 Provider 不能消除公开操作先进入保护的风险。

原始错误记录 **32** 条，其中 **1** 条是监督者为授权增额设置的迁移门禁，
不能归责 Agent；其余 **31** 条是 Agent 请求被拒记录。它们也不能全部归因于模型，
其中既有参数错误，也有视图/引用交付易混淆。详见
[agent_error_inventory.json](../../evidence/b3_r1_history_assisted_050/agent_error_inventory.json)。

| 请求被拒的原错误码 | 次数 | 可观察行为 |
|---|---:|---|
| INVALID_EVIDENCE_POINTER | 20 | 派生路径配 raw/full 引用；将 wrapper 的 `/result/...` 路径配到原始诊断对象；fields 猜测不存在键 |
| RESEARCH_INTENT_ACTION_MISMATCH | 3 | diagnose 配 CONTROL_SEARCH 或 MATHEMATICAL_ANALYSIS |
| EVIDENCE_RANGE_REQUIRES_LIST_POINTER | 2 | 对对象节点按列表读取 |
| missing | 2 | Plan 动作必填字段缺失，包括漏填 action |
| extra_forbidden | 1 | 向冻结 protocol 添加未声明字段 |
| NATIVE_ANALYSIS_REQUIRES_EXACT_STATE_OR_FROZEN_INITIALIZATION | 1 | native 请求遗漏明确初态选择；实际精确模板含该字段 |
| UNREGISTERED_RESEARCH_EVIDENCE | 1 | 可读来源被当成已注册科研证据 |
| EVIDENCE_MISSING_OR_CHANGED | 1 | 使用不可定位的来源身份 |

原工具调用中 evidence_read **120** 次、retrieve_context **9** 次、research_plan **13** 次、
research_analysis **2** 次、research_investigate **1** 次。120 次 evidence_read 有 **40** 次
完全相同请求载荷的重复；动态视图可能已改变，不能直接把这 40 次都判为无效。
此快照没有 DECISION_CANDIDATE_MISMATCH；候选约束修复有具体收益，整体科研效率仍低。

## 已实施的交付修复

1. `b5362f9c3`：Reporter 保留查询 view；派生路径以原始 artifact 根作来源；
   准备 wire 的异常进入既有 unavailable 回退。五项离线回归通过，真实 Reporter available。
2. `69a82930f`：原目录提供精确 request_template_query；Handoff 在原 3,000 bytes
   事实限额内保留执行模板、上限、必填参数与初始化绑定。三项回归通过；
   原 8 KB 以上方法反馈现能保留 2,849 bytes 的执行字段；Agent 已实际读取精确路径。
3. `a29f37134`：原唯一意图映射直接返回动作所需字段/值；定向回归通过。
   之后出现成功的 DIAGNOSE Plan，说明该拒绝关口确已通过。

这些修复后仍有重复读取和错误路径。已通过的 diagnose 只做只读诊断，
不是执行 selected_method 文本中的 native 优化；其 numerical_evidence 为空。
不能把这项计划的成功收据报告成一次完成的优化。

## 待修复项目与验收

| 优先级 | 最小改动位置 | 具体计划 | 验收标准 |
|---|---|---|---|
| P0 | `evidence_policy.py`、`agent.py` 的现有 Plan Schema | 将 action→research_intent 的唯一映射提取为现有模块常量，Schema 依动作收窄允许意图，错误反馈继续引用同一映射 | 对 execute/initialize_control/diagnose/replay/select/stop 的真实 Schema 验证；错误组合在提交前可见，原运行时校验仍拒绝 |
| P0 | `research_context.py`、`task_constraints.py` 的原方法投影 | 从当前 control_initializations 显示当前候选已有的可用绑定源、来源状态与精确小查询；显示已初始化状态，避免只给“可初始化”入口。来源列表由原 Store 派生，保留未测状态 | 在同会话和 Handoff 完整 wire 中识别 e76d3b34… 与候选 e85fc8e3…；无需读 44,522 bytes 的整个 control_result_links；不复制张力数组、不自动选源 |
| P0 | `core.py` read_evidence、原 evidence 导航投影 | 明确 raw 对象和 retrieval wrapper 的引用边界；提供可直接使用的 reference+view+pointer 查询。对 raw/full 使用派生路径、对对象使用 range、对 fields 缺键，返回精确的父节点与合法查询 | 使用本 Study 的 `/control_result_links`、4ea52762… 原诊断及 b29073a3… wrapper 做零计算回放；每条建议查询在其声明视图上真实可读，不能混搭引用/路径 |
| P1 | `diagnostic.py`、`agent.py` 的原工具描述与反馈 | 只读 diagnose 明确报告未发起所选数学方法、实际新增计算数为 0，并链接原数学模板；计划、诊断、analysis 执行分别陈述结果 | 成功 diagnose 后明确 numerical_evidence=[]、无 native cost、数学计费不变；不凭 selected_method 字符串隐式派发实验 |
| P1 | `research_context.py` 的原 read_coverage 投影 | 使用已有 delivery_identity/source_state_identity 显示“相同内容已交付”及精确小查询；把当前已知来源 metadata 放到原短包所需位置 | 完全相同请求且同状态/内容时可识别；动态视图变化、公开完整读取、重复性验证均正常，不封锁合法读取、不绕过读信用 |
| P2 | 原 budget/监督报告 | 同时显示下一阶段 Provider 与 public-operation 可用额、保护额、有效计算和只读调用数，帮助识别公开操作先成为瓶颈 | 本次第二增额后显示 Provider 144、public 192，累计消耗不变；不自动扩额，不新增计费账本 |

P0 的来源显示与导航先做，再评估是否仍需调整 SDK offload/Handoff 大小策略。
目前每次轮换保留边界与配对事实已核验；不能仅因反复阅读就擅改准入机制或放宽科学验证。

## 实施顺序与研究边界

1. 冻结当前错误清单，利用原不可变请求/反馈和既有 archive 测试定位字段。
2. 先做 P0 绑定来源和查询导航，再做意图 Schema；每项只跑对应定向离线回归。
3. 做 P1 的执行状态与读取覆盖说明，沿用原 Store 的来源和内容身份。
4. 提交可审阅的代码与 wire 对照，在 settled 边界通过原 bind/restore-only 显式迁移。
5. 用同一 Study 的剩余额度观察真实请求是否转化为计算与独立验收；新增预算须另有明确授权。

后续验收同时看：请求是否被接受、真实反馈是否交付、是否产生新数学/物理信息、
每项科学结果消耗多少 Provider/公开操作。不能用总工具成功率替代科研效率。
保留原 evaluator、任务、初态、结构身份、科学预算、历史结果和费用；
不会根据未收敛 NLP、native 未执行或单次物理失败声称任务不可行。

当前最佳新独立物理结果 holding_speed=0.043009681835387996 m/s，阈值 0.02；
结构与控制配方同时改变，相对历史最佳约 51.06% 的速度下降不能归因于结构单因素。
最迫切的工程目标是让已有合法控制源、调用模板与计算状态清楚可用，
再由 Agent 在原预算内判断控制搜索、局部模型或结构对照的科学价值。
