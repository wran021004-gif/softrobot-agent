# P6.3-C2 科研问题适配器

基线为 C1 `f5d176e9ffd84e3d19826b54d8e06c774f064d7d`，独立分支
`codex/p6-3c2-scientific-intent-adapter`。本轮仅离线工程验证，不启动 C3。

## 修改前的调用关系及字段所有权

`research_plan(diagnose) → core.dispatch → admit_decision → 保存完成的 Plan`
`→ agent.selected_analysis → selected_analysis_schema → bind_selected_analysis_request`
`→ AnalysisRequest → analysis.dispatch → 原来源/适用性/预算准入 → 原 Worker/费用/证据`。

| 字段 | 权威来源；C2 的处理 |
|---|---|
| hypothesis、candidate、证据 | 已完成的原 diagnose Plan；不推测候选，不重复填写 |
| task、protocol、评价时域、阈值 | 冻结 Study 和候选；focus_metric 只描述关注对象 |
| 方法身份、模型、必需执行字段 | C0 正式目录及原模板；语义唯一匹配后绑定 |
| 参数路径、域、有效性、授权 | 原 FamilySpace / family_analysis_parameters；不新增注册 |
| 科学问题、固定输入/重优化语义 | Main 明确选择；不互相替代 |
| 控制调整范围、策略、成本上限 | Main；原设置默认值只补齐算法数值细节 |
| 完整控制源 | 复用保存来源；有多个不同来源则 Main 选择；缺失则准备 initialize_control |
| 固定输入、短响应时域、扰动候选 | Main 的科学选择；已有唯一合法对照可复用 |
| T2 三点结果及单位 | 原 candidate_responses / saved_context；多个可比较组合需选择 |
| 请求校验、执行授权、计费、保存结果 | 原 AnalysisRequest / analysis.dispatch；编译不产生科学结果 |

## 新接口与实际改动

新 Study 可在原 `research_decisions.analysis_interface` 选择 `scientific_question_v1`，
仍须使用原英文架构与角色配置。没有修改任何既有配置文件、冻结 Study 或历史请求。
旧 `bound_scientific_variables_v1/v2` 的 Schema、候选绑定和交接继续沿用。

新链路：`diagnose(hypothesis, decision.selected_candidate)`
`→ 原完成 Plan → 原按需 research_analysis 加载 ScientificQuestion`
`→ scientific_intent.compile_question → 原 bind_selected_analysis_request`
`→ 原 AnalysisRequest Pydantic / 精确 Schema → 原 analysis.dispatch`。
没有新增工具、Tool Router、子 Agent、方法注册、参数域或执行框架。

| 修改脚本 | 原因 |
|---|---|
| contracts.py | 新增 ScientificQuestion 和两个小型嵌套字段契约；原 AnalysisRequest 不变 |
| scientific_intent.py | 单一职责：语义匹配、前提/必要选择反馈、原请求编译 |
| agent.py | 新版本按需加载轻量 Schema；共用原精确绑定和执行入口；原绑定事件记录真实 Main 输入、编译变量及字段来源 |
| core.py | 仅新版本 diagnose 缺省 selected_method 记录通用意图标签；反馈直接提交科研问题，不执行计算 |
| evidence_policy.py | 仅新版本 diagnose 要求显式合法候选；沿用原候选验证 |
| config.py | 原配置校验增加一个显式接口版本 |
| research_context.py | 新版本的交接文字不再要求 Main 选择求解器；不展开科学概念到 L0 |
| test_p63c2_scientific_intent.py | 合成状态、原合同与 Mock wire 定向测试 |

未修改 analysis、Worker、native_control、control_correction、任务 evaluator、Native/GVS 内核、
FamilySpace、Store、Reporter、Provider、Gateway。C0/C1 的正式目录及机会计算保持原实现。

## Main 填什么，以及如何匹配

所有问题先由原 Plan 记录假设及候选；ScientificQuestion 不复用 `ResearchDecision.research_intent`。
新版本 diagnose 可以省略 selected_method，程序仅记录 `scientific_question` 意图标签。
不需要额外选择五类操作或 18 个方法的工具回合。

| 科学问题 | Main 的科学选择 | 程序匹配及绑定 |
|---|---|---|
| 控制可行性/改进 | control_scope、search_strategy、requested_budget；存在多个不同合法序列时选 control_source | 原 Native T1；绑定候选、模型、初态、完整冻结任务/协议、唯一合法序列和原数值设置默认值 |
| 固定输入结构响应 | fixed_input_response、一个真实参数路径、固定输入条件、短响应时域；多个合法对照时选候选 | 原 fixed_input_structure_v1；同一绝对输入和命名初态、重建合法单参数候选，保留短响应限制 |
| 重优化后的结构响应 | reoptimized_task_capability、一个真实参数路径；多个合法三点组合时选保存结果 | 原 T2；复用 candidate_responses 的合法请求和原 saved_context 比较条件；没有新 T1 或候选生成 |

Plan 已有的 selected_variables 和正 requested_budget 可分别作为结构路径和 T1 成本上限，
无需重复填写；当前科研问题明确提供时使用当前选择。任务和候选始终由 Plan/Study 绑定。
focus_metric 仅允许已注册任务约束 ID，记录于真实 Main 输入，不改变目标函数、阈值或验收。

科研含义说明只随 Schema 加载：mechanism_effect、fixed_input_response、
reoptimized_task_capability、closed_loop_performance、re_equilibrated_passive_response。
复杂区别继续查询原 mathematical_capabilities；未建立 M0–M3 工具或四选一体系。

### 最小输入示例

以下是工程接口示例，要求已有完成的候选绑定 diagnose；不代表执行过真实研究。
有唯一合法控制源时，完整任务范围内的有限控制搜索：

```json
{"question_type":"control_feasibility","control_scope":{"mode":"full_task"},"search_strategy":"response","requested_budget":8,"focus_metric":"holding_max_speed_m_s"}
```

仅调整 0.25–0.50 s，仍完整评价冻结任务（该区间须落在实际任务时域内）：

```json
{"question_type":"control_feasibility","control_scope":{"mode":"time_window","window_s":[0.25,0.50]},"search_strategy":"pattern","requested_budget":8}
```

固定初始绝对张力下的结构短响应；若存在唯一合法对照，程序复用它，否则返回候选选项：

```json
{"question_type":"structure_parameter_effect","effect_semantics":"fixed_input_response","parameter_paths":["segments.0.length_m"],"fixed_input":"frozen_initial_tensions","response_horizon_s":0.01}
```

查询同一参数在控制重优化后的变化；只有现成唯一合法三点证据才编译，不会用上一例替代：

```json
{"question_type":"structure_parameter_effect","effect_semantics":"reoptimized_task_capability","parameter_paths":["segments.0.length_m"]}
```

## 前提、失败反馈与范围

`ready` 只表示已编译为原合同；最终执行准入仍由 analysis.dispatch 所有。
未准备好时不调用该执行入口、不保留科学预算、不制造 J 或敏感性结果。

| 返回值 | 可操作反馈 |
|---|---|
| needs_choice | 列出缺少的科学字段、合法不同来源/对照/三点组合；固定输入和重优化不明确时要求选择 |
| needs_prerequisite | 缺完成的候选 Plan、完整控制源、合法结构对照或可比较 T1；提供原 diagnose/initialize_control/generate 入口及需 Main 决定的步长/方向等 |
| unsupported | 不支持的物理语义、非真实/无效/非连续参数、未知 focus_metric、超出 C2 形状的输入；不自动降级 |
| blocked | 原冻结授权、参数授权、预算、Native 上限或保护收尾不允许 |

结构路径只来自原 family_analysis_parameters；候选实际变化由原 structure_context 校验。
T2 候选组合只来自原 candidate_responses，保留相同任务、来源、搜索设置、初始化、对称步长和可比较性条件。
多个步长/结果组合不选择第一项；没有结果时不触发三点实验。

C2 有意只适配单一连续结构路径、冻结初态、固定绝对张力的短响应和现成对称 T1 三点。
机制导数、完整闭环性能、被动重平衡、多参数耦合/离散比较、任意保存工作点、任意波形或通道子集搜索尚未适配。
原方法中已存在的能力仍可由旧精确接口使用；C2 不把未适配语义替换成固定输入或 T1/T2。

控制范围的有限参数化在 Schema 中明确说明：full_task 为所有通道的两个独立端点系数，
time_window 为每通道一个三角脉冲。数值幅值、有限差分步长及信赖域等继承原 LocalControlSearchSettings 默认值。
局部模式的首末修正系数固定为零，只激活中间结点；np.interp 的端点延拓因此在区间外严格为零。
送入原 Native 的 correction_window_s 始终是完整冻结时域，评价没有缩成局部窗口。
不增加插值框架，不修改优化器；原研究上限不允许此参数化时返回 blocked。

## 执行、费用和证据边界

编译不调用数值 Worker，审计沿用原 analysis_request_binding / validated 事件，无第二份结果账本。
T1 保持原模型/回调/rollout/physics_steps 费用；requested_budget 不是免费物理积分额度。
T2 仍收一次聚合评价，零新模型、rollout、优化和物理步；原 T1 成本仅引用，不重复收费。
T1 是有限预算 best-found 结果；T2 保留有限差分、比较有效性、未收敛和非光滑限制，
不能解释为严格最优值梯度、全局最优能力、不可行性证明或独立任务验收。

## 离线验证

定向验收 **32/32 通过，零跳过，133.853 秒**：C2 新测试 12、P6.3-A 原数学接口 4、
C1 状态投影 8、C0 目录 6、B5 原来源准入边界 1、B3 旧 wire 交接 1。
准确命令、初轮修正及边界见 [验证记录](p63c2_validation.json)。
所有数值输出均来自明确标记的合成 fixture；
真实 Provider、Reporter、MuJoCo 积分、GVS、NMPC、PPO、新优化实验及新 Study 科学执行为零。
测试临时 Store 是隔离的工程 fixture，未修改 C0/C1/B6 保存状态。

C2 工程完成不等于 Main M3 自主决策通过；C3 真实研究验收未启动。
