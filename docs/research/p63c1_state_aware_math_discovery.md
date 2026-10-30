# P6.3-C1：研究状态感知的数学能力发现

基于 `codex/p6-3c-math-capability-catalog@6634b88633ba24c268de193fe85e5e9666af9668`，
独立分支 `codex/p6-3c1-state-aware-math-discovery`。本轮完成工程投影和离线验证；
没有真实 Provider/Reporter 请求、科学 Worker、MuJoCo 积分、GVS/MATLAB 数值运行、NMPC、PPO、NLP 或新 Study。
原 B6 Store 只以 SQLite `mode=ro` / `query_only` 读取，未写入或恢复执行。

## 调用链与实际缺口

已读根 AGENTS.md、[模块职责](modules.md)、[C0 审计](p63c0_math_capability_catalog.md)，
并检查 task_constraints、research_context、agent、analysis、core、contracts 及相关测试。

原链路是 `agent.decision_packet → agent_decision_brief → mathematical_method_view`，
再经 `mathematical_catalog / mathematical_opportunity_summary → research_decision_brief_v3 → information_flow_brief`。
Provider 的动态状态仍由原 `CURRENT_RESEARCH_PACKET` 放在当前请求末尾。
`research_route` 只加载工具，完成 diagnose 后仍由原 selected_analysis_schema 提供科学输入 Schema。

C0 已有正确的静态目录与候选准入信息。本轮发现的展示缺口是：
原机会摘要按参数链接选择方法，没有使用当前失败约束；action menu 又展开完整正式方法列表；
最近数学数值可能分散在 Reporter findings、verified_facts 与 latest feedback 中。
原 `planning_status=ready` 也需要与“具体请求已通过执行准入”明确区分。

## 修改与职责

生产只修改两个现有文件，没有新增生产模块：

| 文件 / 函数 | 修改 |
|---|---|
| `task_constraints.mathematical_method_view` | 在原 mathematical_capabilities 视图中允许冻结域引用查询同一 C0 静态目录；无候选时 methods 为空，没有执行模板或候选适用性结论；其他非自有引用仍按原规则拒绝 |
| `task_constraints.mathematical_opportunity_summary` | 复用原 planning/execution/missing、coverage、required_outputs、参数 method_links、C0 分类及原控制准备入口；生成最多四项具体机会、三项约束焦点和一个不可用原因示例 |
| `research_context.mathematical_discovery_observations` | 只读当前候选的已登记 computed scoped result；复用 ResultCard/decision_result；Native 观测复用原 task proxy 处理保存的输出，不积分、不重优化、不改变独立接受 |
| `research_context.agent_decision_brief` | 在原 mathematical_research 字段组合候选/source/结果和已有保护状态；无候选时展示五类能力、18/9 计数、冻结域/模型说明查询和原 generate/search 入口 |
| `research_context.research_decision_brief_v3` | 移除 action menu 的完整数学方法列表，改为指向 mathematical_research；最近数学数值集中在 latest_result，其他位置仅保留引用 |
| `research_context.information_flow_brief` | 对同一数学结果的 flow_facts/额外 quantities 保留 facts_at 引用，避免重复传数值；Reporter 的解释仍独立归属 |

另新增一个定向测试文件，以及本文、[示例输出](p63c1_examples.json) 和[验证记录](p63c1_validation.json)。
未修改 C0 静态分类模块、agent、contracts、analysis、内核、FamilySpace、TaskAdapter、Store、Provider 或 Reporter。

## 状态组合与展示

这些状态不构成强制顺序，也不保存新的路由状态。

| 当前情况 | Main 获得的信息 |
|---|---|
| 无候选 | `requires_owned_candidate`、固定五类操作、正式/未接入计数、原参数域与 model/method scope 查询、原合法初始入口；候选数学 methods 为空 |
| 有候选、无完整 source | 适用方法及其原状态；控制方法明确缺 `legal_control_source`，可查看原 initialize_control 准备入口；不创建 source |
| 已记录完整 source | 标明 source 可查询，但仍需 Main 选择 source/科学设置；`request_admission=not_checked`，不把记录存在当请求合法 |
| 独立评价失败 | 仅使用同候选、完整且有效的原 physical diagnostic；按失败约束关联 coverage/物理信号，突出若干可研究问题；不输出根因或唯一正确方法 |
| 已完成数学计算 | 展示原数值、模型/时间范围、计算和验证等级、未决问题、当前能力；模型观测与物理接受分开。未覆盖的约束仍为 unmeasured |
| 任务/方法不适用 | 不进入机会列表；原不可用状态计数、原因示例及完整方法详情可查询；不改变原 TaskAdapter 的覆盖判定 |
| 未授权、预算不足、保护收尾 | 原方法被标记不可用时不填充机会。保护阶段复用 current_research_state 的原候选可读性结论，延后不可读候选目录，保留原合法 STOP 结果索引读取 |

展示排序只用已有约束覆盖、信号、完整任务覆盖标志、原规划状态和不同操作/模型范围。
没有任务名、错误码或 Reporter 关键词推荐表；没有新增硬准入、预算校验或来源授权逻辑。
相似作用范围只合并默认展示机会，不合并底层方法；完整目录仍保留全部 18 个正式方法与 9 个未接入能力。
GVS、Native、结构对照等未被优先展示的方法仍可通过原 mathematical_capabilities 目录发现。

每项机会包含 purpose、原 status/execution_status、readiness、主要 missing、必要准备入口、数学评价成本、
wall_cost=unknown 与精确 detail_query。`request_preparation_available` 只表示可准备请求；
所有机会均写明 `request_admission=not_checked`。准备入口只有原工具/动作，不替 Main 生成 Plan 或选择科学输入。
完整模板、全部缺失项和精确 AnalysisRequest Schema 保持原路径与原读取语义。
新增的冻结域静态入口只使用原 mathematical_capabilities 视图和 C0 capability_inventory 工厂，
不会新增目录定义或放宽任何候选分析/执行准入。

## 数学结果与证据边界

最近结果由 `mathematical_research.latest_result` 持有客观数值；其他 L0 位置使用
`facts_at=mathematical_research.latest_result`，原 Store 结果和完整报告不变。
约束焦点另外携带 `evidence_scope`，避免将 model_sample 超限写成独立物理失败。
Native 保存轨迹的极值只按原冻结 task proxy 读取；没有新的接受阈值或成功判定。
其他结果优先使用原 ResultCard 的逐约束 metric；未观测约束明确保留未知。

只读原 B6 结果 `a0658019…` 的投影实际保留：

- 原 initial J = 13.45390642085818，best-found J = 11.269234347898596；
- 末端/保持位置及保持速度三个模型观测仍超限；
- stop_reason = evaluation_request_budget，convergence = unresolved，global_optimality = not_established；
- task_acceptance = unmeasured，模型/时域和原始查询仍可见。

该检查通过隔离的展示夹具读取原 SQLite 数据，不改原 Study 的候选、预算、读取信用或科学事实。
Reporter 解释未用于生成 Main 假设、Plan、参数修改或 STOP。C1 工程通过不能证明 Main M3 已通过。

## 上下文开销与验证

L0 不展开 18/9 项目录、参数行、执行 Schema、原始轨迹或求解器矩阵。
示例包含无候选、source 前后、未授权、预算耗尽、保护收尾、合成 computed、实际 Mock wire 和原 B6 只读结果。
这些是工程示例，不能成为新 Study 的候选/source 或科学证据。

同一合成保存状态的 C0/C1 **纯 v3 JSON 投影**采用紧凑 UTF-8 编码比较：

| 状态 | C0 整体字节 | C1 整体字节 | C1 数学发现字节 |
|---|---:|---:|---:|
| 无候选 | 9,074 | 9,947 | 1,019 |
| 候选、无 source | 15,622 | 16,486 | 5,395 |
| 候选、有 source | 16,364 | 17,154 | 5,321 |
| 已有合成数学结果 | 19,222 | 21,952 | 7,837 |

完整方法列表和重复数值减少，但新增科学问题、前提和结果边界后，总字节仍增加；不宣称总体压缩、token 减少或模型效率提高。
这不是实际 Provider 计费或性能实验。真实 Mock wire 另验证请求末尾位置、按需方法查询和固定系统提示词不被动态状态污染。

使用既有 `.f3-prestudy-env`，不安装依赖。测试覆盖 C1 八项、C0 六项、P6.3-A 四项及 B5 原 source/admission 边界一项；
准确最终结果与命令见验证记录。早期修正包括夹具字段名、原 B6 SQLite 路径/引用形状，以及去除超过字节上限的重复查询。
没有为通过测试放宽科学授权、来源、预算或执行合同。Mock HTTP 日志中的 RequestBoundaryHandoff 是既有测试边界。

本轮没有修改科研意图、完成 diagnose 后的交接或科学执行合同。C2 仍需另行处理意图到科学输入的适配；
本轮不实现 C2、不启动新 Study、不合并其他分支，交付后停止。
