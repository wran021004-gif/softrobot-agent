# 数据字段与计量范围

每行 task_id × condition 对应一个正式原生 Store。空值表示未知或不适用，不表示零。原始数据、计算输出、模型公开判断分别保留。

- `accepted`：原任务验收且原生正式 SELECT；`not_selected` 不等于科学不可行或所有方法失败。
- `required_pass_count`：顶层冻结协议的 required case 数。T08/PHS2D 的多次物理响应封装在一个顶层协议内，因此此字段可以是 1；PHS2D 的十个内部工况仍必须全部验收，不是只测试一个载荷。
- `initial_candidate`：初始文件中已存在的候选引用。无候选的 family-space 初态为空。`final_candidate` 是选择绑定候选，未选择时保留最后公开 Plan 指定的候选，不把它标作通过。
- `candidate_count`：原生候选对象数，包含控制变化，不等于唯一物理结构数。物理结构身份单列在候选与证据表。
- `maximum_violation`：所有有效完整物理评估中记录的最大归一化违约。`best_violation`：同一物理结构完整覆盖必需工况时的最佳协议违约。`final_violation`：已正式选择的必需协议违约。最后一个可选工况或局部轨迹不代替这三个定义。
- `research_action_count`、`total_core_calls`：桥接接口原始操作数，包含诊断、读取及拒绝，不是有用决策计分。原生账本调用数、未封口条目与错误另列。
- `completed_mathematical_evidence`：返回中明确 `scientific_computation.complete=true` 的操作数，仅证明所声明计算完成，不证明模型证书可靠或物理验收。
- `mathematical_cost`：原生数学评估计数。`physics_cost`：原生 shared ledger 的已计费 `backend_solves`，可包含保留的中断费用，不等于实际完成仿真次数。NMPC/replay 启动计数、完整性与已记录积分步另列，不能相加为重复成本。
- `native_charged_numerical_s` 可含保守退出观测上界；`measured_solver_runtime_s` 缺失时保持为空。`recorded_math_kernel_wall_s` 等内部数值计数仅汇总明确返回的观测，同时报告未记录条目数。
- `total_tokens` = 已记录完成回合的 input + output，input 已含 cached input；reasoning 是输出的子集，不再相加。不是货币账单。provider 请求数和中断缺失用量不估算。
- `wall_clock_time`：原生研究起止之间的日历秒数，包含排队和中断，不是纯计算时间。`time_to_formal_select_s` 只在观察到 SELECT 时给数值，未观察到不补零。
- `RESOURCE_TO_ACTION` 区分可选 typed 检索和 `delivered_context` 的显式读取。`RESOURCE_AVAILABILITY`、`CONTEXT_EXPOSURE` 只证明可见性。返回正文、模型自述 adopted/rejected/context_only、显式操作引用、后续时间顺序与因果效应分别记录。因果效应未建立时保持未建立。
- `original_budgets` 与 `recorded_final_budgets` 按实际值保留，不能据最终端点宣称各单元始终有完全相同的资源条件。
- `FACTORIAL_EFFECTS` 是逐任务终态的描述性差，成本和时间的量纲在列名与协议中给出。不同任务的违约不直接合并，不进行未经支持的显著性结论。
