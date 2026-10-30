# P6.3-G2：Mixed Search 科研意图适配

基线 `891c679c9d47dbcb39a8cbb00adffa74220f6222`，独立分支 `codex/p6-3g2-mixed-search-intent`。G1 的原 Store 只读；不延长其预算、不重新解释其失败。本轮先完成接口修复和定向验收，再进行唯一一次最多 12 请求的短窗口验证。

## 原缺陷与修改

G1 的 18 个 search 请求在执行前被拒绝。新 Study 显式启用 `research_decisions.structure_search_interface=scientific_structure_search_v1`；仍使用原顶层 `research_plan(action=search)`。`structure_intent.py` 只编译科研选择，执行链为：

`research_route(search) → 精简 Plan Schema → ScientificStructureSearch → 原 FamilyMixedSearch → 原 Plan/准入 → search.run_search → 原 analysis.dispatch/Native Worker → 原 Store`

Main 填写原 Plan 的假设、依据、预期/削弱观察、固定条件和停止条件，以及 search 中的：

- `research_goal`、真实结构 `design_variable_groups`、`evaluation_model`、`control_treatment`；
- `structure_search_effort.max_proposals/max_evaluations`；
- Native 的 `control_search_effort.method/knot_count/iterations/evaluation_requests`；
- 可选预张力、拓扑研究范围、span 策略、截面种类。

冻结空间只有唯一段/腱计数时自动绑定；显式越界则拒绝。唯一 FamilySpace identity、原 method、唯一与最终离散一致的 screening fidelity、Native 起点 `standardized_initial_pretension`、完整 `task_violation` 目标和内部 `MATHEMATICAL_ANALYSIS` 分类由程序绑定。新精确 Schema 不展示 `research_intent`、内部 method 或重复 requested_budget；假设和用户选择保留，原请求与编译后的 Plan/准入存于原 Store 的 `structure_search_intent_binding`。

结构变量枚举不再含 `control`；逐结构控制重优化由 `control_treatment=reoptimized` 单独表达。Native 与数学代理不互换：代理必须明确选择 `structural_capability_screening/proxy_objective`；静力/保持输入代理用 `not_optimized`，CONIC task_violation 的仿射模型控制求解用 `proxy_optimized`，不接受 Native effort。省略 Native 预张力只使用冻结 tendon-domain 的唯一默认值；无该来源则要求选择。实际张力、来源、模型和预算仍由原合同及 Worker 检查。

原 mixed search 的初始化语义未改变：previous candidate 只为段参数提供 seed，未完整继承其路由和控制；未选的路由/span 使用原 search defaults。该范围明确写入指引和编译记录，不能把重新构建的搜索基点误称为原候选原样续算。

## 控制努力与时间语义

`ScientificControlEffort` 复用原 `LocalControlSearchSettings` 的技术范围，最终仍用原模型校验。新 `scientific_question_v2` 与结构搜索共用 `scientific_intent.control_settings`；旧 `scientific_question_v1` 保留两个端点及原默认行为。

- `knot_count` 默认为 4，实际时间由冻结时域均匀生成；允许原合同的 2–4 个 knot。
- `iterations` 和 `evaluation_requests` 是两个独立上限。显式 80/120 忠实保留；省略 iterations 时为 `min(callback cap, frozen Study iteration cap, original contract maximum)`，不隐藏恢复为 16。
- 不突破原 100/1000 技术范围或更严格的冻结 Study 限制。原收敛、半径和预算停止条件不变，不要求耗尽回调。
- 局部窗口至少三个 knot，仅内部系数激活、端点修正为零，因此实际窗口外修正为零；评价仍覆盖完整原任务。

没有修改 Native 搜索算法、任务约束或物理内核。返回的 callbacks、iterations、终止原因、best-found 指标和数值范围沿用原结果及费用投影。

## 纠错与直接相邻缺口

`agent.error_feedback` 根据明确版本筛选实际合同分支，并让紧凑 reason 使用筛选后的错误，不再使用联合错误原文前 1000 字符。对 G1 直接问题补充起点、control 结构变量和实际 knot 字段路径，返回少量 issues/error_type/expected；完整原文、请求和 traceback 留在 Store。新意图的拓扑、模型语义和冻结选择错误在编译前或原准入前拒绝，无 Worker 或科学费用。

diagnose Schema/反馈明确 `decision.selected_candidate` 所有权，不引入第二套候选转换。新版本 Knowledge 返回冻结合法过滤值及原 `read_progress` 的 prior 状态；确切正文交付仍须由真实 wire 确认。重复查询未被禁止，无新 Memory 或知识路由器。

## 离线验收

38 个不同定向测试完成并通过：新 G2 六项（含一个隔离真实 Worker）、C0 六项、C1 八项、C2 十三项、G0 五项。合并运行最初 37 项通过、一项新增断言误读旧默认值省略序列化而失败；修正该断言后，新合同类五项复测通过，再为 C2 v2 补充实际 Schema wire 断言并通过。没有为此改变旧序列化。合并日志耗时 186.458 s，最终新合同五项复测 22.787 s；额外 C2 v2 wire 定向复测 5.665 s。`git diff --check` 通过。

使用原 G1 第 20、21、29、46、59、62、65、67 次保存输入，覆盖起点/变量组、联合分支和五 knot。原 DB 以 SQLite mode=ro/query_only 读取且 mtime 不变，未重试任何旧失败科学请求；八份原输入及其原事件引用提取为可提交的离线 fixture，后续回归不依赖私有 Store 路径。实际 SDK/Mock wire 证明加载的是 `ScientificStructureSearch`，无需内部分类；可省略版本默认值，编译后通过原 Plan/数学准入。非法五 knot 的字段纠错实际进入下一请求，科学评价数保持 0。代理仍按原代理合同解析，未改成 Native。

小规模真实测试使用新隔离 fixture 和原 search.run_search/Native Worker，不是 M3 科研成果或历史成功答案。最近一次：1 build、2 rollouts、1200 physics steps、123 forward evaluations、1 次正式数学评价；worker_started/termination_confirmed=true，returncode=0，wall 1.2010049 s，kernel 0.1355643 s。开发期间共运行两次这种小型真实接入测试，合计 2 builds、4 rollouts、2400 steps；所有 Provider wire 测试均为 Mock，无真实模型请求。未运行九项历史实验或全仓回归。

短窗口关闭后复核代理控制语义：CONIC task_violation 必须显式 proxy_optimized，静力/保持输入代理仍为 not_optimized，不能暗示 CONIC 没有控制求解。修正后新合同五项再次通过（22.174 s），补充“显式授权的 CONIC 仍保持代理、无 Native effort”定向断言后单项通过（7.941 s）。没有新科学 Worker 或真实 Provider 请求；真实窗口仍冻结在原 e86097d，不声称其验证了这项末尾修正。

## 短窗口冻结计划

新配置 `study_p63g2_m3_mixed_search_sol.json`：Main/Reporter 保持 `gpt-5.6-sol / none`，总 Provider 12（含准备 Reporter、失败实际发送及其中 2 次保护收尾），原充足科学额度与 1000 callbacks/100 iterations/4 knots 技术上限不变。新任务、FamilySpace、analysis_protocol 和 control 与 G1 解析后逐项相等。

用原工具在新 Store 重建一个合法候选、baseline、真实 Native 优化和一次完整有效失败 Replay；这些准备都标明 Operator 所有权，费用单列。准备优化采用四 knot、80 次迭代/120 回调，既不伪造失败，也不设置 8/16 人为限制。若独立结果不是有效失败，保留结果并报告，不能伪造或重试至得到指定数值。

原 Reporter 的真实解释也计入 12 总量。Main 从失败事实与解释自主选择后续行动；Operator 不提交替代搜索。监督在请求/反馈封口边界检查原 lifecycle、模型构建和费用；确认自主合法 mixed search 已启动真实 Worker 且记录封口即可结束，不为 SELECT 再开完整研究。运行时代码、模型和提示冻结；最终实际结果另存 `p63g2_live_validation.md`。
