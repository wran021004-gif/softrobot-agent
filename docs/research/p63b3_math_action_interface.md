# P6.3-B3 — 数学研究行动接口最小修复

基线 `88c01b0f3e4bf6b9269a73093f96e6360c7da9ed`，独立 worktree / 分支
`codex/p6-3b3-math-action-interface`。依据 B2 G/M 真实审查中的失败形态修复接口；
没有修改旧 Study、Store、授权、证据或预算，没有合并主线。

## 已修复的边界

| 原问题 | 修改位置与结果 |
| --- | --- |
| G 第 6 次、M 第 12 次照 L0 查询仍触发 TOOL_SCHEMA_ENUM | `research_context.decision_brief` 优先使用既有 FamilySpace 作为通用 working_set 锚点。数学详情仍绑定真实候选，科学结果仍保留各自原始引用。`state.readable_results`、保护期枚举、`core.read_evidence` 权限均未修改。 |
| 单方法 6750 字节对象先返回导航第一页，看不到模板 | `core.read_tool_evidence` 对单个注册方法返回 `task_constraints.mathematical_action_view`。目的、前提、缺参、来源、绑定字段、费用及下一入口优先；模板给准确子路径。显式 fields 仍精确读取原方法，完整对象可按原 fields 限额分两次恢复；整个 methods 等大型对象仍使用原导航。 |
| fixed_input_structure_v1 把内核适用误写成输入齐备 | `analysis_capabilities` 把合法连续变量和同任务可比较结构候选列为实际参数前提，状态为 requires_parameters。`design_sensitivity` 同类参数也补齐；不替 Main 生成或选择对照。固定输入比较按原契约消耗 1+对照数量，即 2–3 次评价，规划预算据最小合法请求判断，实际准入照旧。 |
| L0 难以区分起点、route、提交与科研结果 | `current_research_state` 由已有候选 provenance、原 Plan/receipt、行动 trace、Knowledge 阅读收据和预算投影；经 v3 和 information_flow 进入实际 L0。显示来源、编译、控制、数学、独立评价、任务接受及最近有效行动，不建立新状态库。 |
| diagnose 已加载但 Main 继续 route/检索 | `information_flow_brief` 明示直接提交 research_plan(diagnose)，列出原科学字段。完成后展示所选方法、绑定字段、缺参/来源、预算和 research_analysis 是否加载；剩余必填字段来自 `agent` 当次真实工具 Schema。 |
| 唯一工作点仍要手填 | `selected_analysis_schema` / `bind_selected_analysis_request` 复用 AnalysisRequest 的合法工作点集合。唯一且无需保存态的工作点由原绑定器填写并记录 field_sources；多个合法工作点保留给 Main，保存态来源要求照旧。 |
| 检索 receipt 被当作 entry_id；候选索引被当作原文 | `experience.retrieve` 的 search 回执及工具说明提示执行条目 read_query。候选索引增加原 candidate 的 parameters/provenance 精确查询。方法行动视图提示派生子路径继续使用 mathematical_capabilities。Knowledge manifest/已读进度未改。 |

## 实际 Mock Provider 展示

[完整序列化示例](p63b3_action_interface_examples.json) 来自新增四项测试的实际 Mock HTTP
请求、工具响应和下一次 Provider L0。其中所有引用属于明确标记的合成 fixture，
不是新的科学实验或 B2 原 Store 引用；本地 fixture Store 不提交。

G/M 的 `stop_index.query` 均为：

```json
{"reference":"<原 FamilySpace EvidenceRef>","view":"working_set","pointer":"/all_fresh_results"}
```

JSON 中保留真实对象形式的 reference、同请求 allowed_reference_enum 和读取结果。
G 准确返回 `[]`；M 注入两条明确标记的合成数学结果，准确返回全部两条原引用。
同请求枚举严格等于原 `readable_results` 集合，未加入候选或所有错误回执。
候选原文在保护期仍被原权限拒绝，预算不变。

首次读 `mathematical_capabilities /methods/fixed_input_structure_v1` 返回 3692 字节行动视图，
下一次真实 Mock wire 的原 Handoff 摘要保留了：

```json
{
  "scientific_purpose": "Native structure and function response",
  "planning_status": "requires_parameters",
  "missing": [
    "structure_response.variable: choose a legal continuous structure variable",
    "structure_response.candidates: select owned same-task legal comparable single-parameter candidates"
  ],
  "request_template_query": {
    "reference": "<当前候选 EvidenceRef>",
    "view": "mathematical_capabilities",
    "pointer": "/methods/fixed_input_structure_v1/request_template"
  },
  "next_submission": {
    "tool": "research_plan", "action": "diagnose", "available": true,
    "after_completed_diagnose": "research_analysis; original source, parameter and budget admission applies."
  }
}
```

该代码块为便于阅读的字段节选，准确完整对象见 JSON。
同一测试验证模板子查询、显式 fields 恢复原对象及 methods 原大型导航，
因此没有靠丢弃原始详情解决问题。Handoff 实现未修改。

M 路由后、Plan 提交前的实际 L0 节选：

```json
{
  "phase": "research",
  "object": {
    "origin": "Operator", "compiled": true, "control_initialized": false,
    "mathematical_result": false, "independently_evaluated": false,
    "task_acceptance": "unmeasured"
  },
  "methods_read": ["fixed_input_structure_v1"],
  "last_effective_action": {"status": "tool_selected_not_submitted", "action": "diagnose"}
}
```

相邻 `direct_plan` 明示工具已加载、无需再次 route；科学字段仍要求 Main 提出
hypothesis、selected_candidate、selected_method、expected_observation、
weakening_observation、fixed_conditions，原 Plan 的其他要求仍由原 Schema 执行。

合成 Main 自选 `native_dynamics_v1`，正式提交 diagnose 后，同次 L0 与实际 Provider Schema：

```json
{
  "tool": "research_analysis", "loaded": true, "method": "native_dynamics_v1",
  "planning_status": "ready", "formal_execution_authorized": true,
  "execution_status": "conditional_on_admission",
  "remaining_scientific_fields": ["operating_point"]
}
```

实际 Schema 允许 `standardized_initial_pretension` 和 `saved_state` 两个工作点，
没有替 Main 选择。fixture 只验证合法 payload 的绑定，不提交数学执行。
完成 diagnose 后 `diagnose_plan_completed=true`（在 completed 列表中），
`mathematical_result=false`、`task_acceptance=unmeasured`；route 和只读诊断均未冒充数学计算。

## 科学选择与确定性绑定

- Main：假设与反证目标、候选/方法、参数/指标、结构或输入对照、合法步长、存在选择时的工作点、有限搜索预算、结果解释。
- 程序：已选候选 identity、冻结 task/protocol、operation、唯一 model_source、注册方法唯一决定的字段；T1/T2 的唯一初始工作点也写入原绑定审计及来源。保存态方法仍要求真实来源。
- 没有自动初始化控制、生成对照、选择参数方向或继承上一轮科研结论。原数学内核、AnalysisRequest 科学含义、独立接受、Reporter、Store、Session Handoff 和计账未变。

## 验证与停止

新增 `test_p63b3_action_interface.py` 四项测试：保护期 G/M wire；首次方法详情与
下一请求交付；方法前提/预算状态；Operator → route → diagnose → analysis Schema。
另复用五项相关旧测试：P63A selected binding，B0 正式范围交接与已有 T2 ready 的只读投影，
information_flow 直接读取保留 Plan，B2 零科学预算生成/收尾。
**共 9 项通过，66.347 秒，无跳过。** 控制台 RequestBoundaryHandoff 日志来自原 Mock 会话切换，测试最终为 OK。

命令使用已有 `D:/softrobot-agent/.f3-prestudy-env/Scripts/python.exe -m unittest`，
仅运行上述指定测试；`git diff --check` 通过。系统默认 Python 缺少 jsonschema，未安装依赖。
真实 Provider、数学 Worker、物理 Worker、NMPC、RL 均为 0；未重跑五候选链、九任务或 G/M。

生产改动限于 research_context.py、task_constraints.py、core.py、agent.py，以及一行相关
experience.py 查询提示；测试新增四项，并更新两份旧测试以匹配唯一工作点绑定。
附本说明及 Mock 示例 JSON。未改 state.py、求解器、FamilySpace 规则、Knowledge manifest 或历史证据。

B3 的工程接口验收已完成，建议结束本阶段开发。下一次应单独授权有限预算的真实数学决策验证：
Main 能否理解前提、提交自己的科学选择、执行合法数学请求，再根据原结果继续判断或停止，
仍未由本次 Mock 证明。本次不申请、不启动该验证。
