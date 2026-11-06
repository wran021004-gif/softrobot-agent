# 阶段二交付：科研工作流连续性

分支：`codex/stage2-research-workflow-20261106`。基线为阶段一 `15835ddd590f11f108b886b7e2bdc248ae6a6248`。独立 worktree 位于 `D:/softrobot-agent/.worktrees/stage2-research-workflow-20261106`；不合并 main，不改原 `feat/gvs-dynamics` 工作区。

## 1. 阶段一的最小语义修正

- `analysis.diagnostic_layers` 分开返回 `computation_status` 和原资格 `status`。228 个接触是已完成的几何观测；没有几何资格证书时资格仍是 `not_evaluated`，不另设接触阈值。积分完成也只表示计算完成；动态层通过仍要求完整独立执行与原验收。
- `diagnostic_overview` 用 `observed_layers`、`qualified_layers` 和各层计算状态替代 `highest_passed_layer`。四层是独立信息范围。
- 主动静力判断读取 `model.operating_point.available`。False 不因优化器 success 而通过；缺少明确资格不默认通过。保留 SoRoSim 原明确静力事实；非平衡点导数失败的静力层为 `not_applicable`。
- 被动 `solve()` 中断使用当前 trial 的 `initial_forward_completed`，保留第一个初值成功、第二个初值首次 forward 失败的各自记录。
- 原始数值结果、物理内核、KKT、求解器、协议与验收阈值均未修改；历史结果和账本不重写。

## 2. Candidate—Hypothesis—Plan—Evaluation

只在已有 `research_context.working_set()` 中生成只读 `research_workflow`，不保存第二份状态。所有 `ordered_candidates()` 候选均有简短记录，详细结构仍按需读取。原最近三个候选及当前对象的详细预览继续保留。

关联来源为原 Store 引用与 Plan receipt：

1. Plan 来自 `state.plans` 的 `original_plan`；假设、预期观察和反证条件可从其 `/original_plan` 精确读取，当前 Plan 的原假设直接展示。
2. 生成 Plan 的实际 receipt 建立 `generated_by`，不把该 Plan 的研究父候选误作新候选。
3. 数学分析编译携带已完成 diagnose 的 `plan_reference`，dispatch 核对原 Plan 候选，pending/recover 将该引用保存到结果。
4. 历史评价仅通过明确 `plan_reference` 或 receipt 中完全相同的结果引用关联。无关联则 `plan=null` 并列入 `unknown_plan_links`；不匹配文本、参数或时间。
5. Plan 登记/完成、pending 的预留或运行状态、Worker 是否启动、结果是否记录、完整物理执行和验收分别展示。Worker 启动事实缺失时为未知，不能用请求接受补齐。

`completed_question_plan()` 在已完成的 generate/propose 之后保留原显式 diagnose；生成不会切换研究对象。新候选必须由 Main 提交新 diagnose 才绑定分析。主动和被动共用这条路径。

## 3. Main 工作视图示例

以下为本次离线 Store 测试的真实短引用，数值 Worker 为明确的中断 fixture，不能作为科学证据。编号沿用原 Store 行序号机制，不承诺连续。

| 时刻 | 原当前对象 | 新候选 | 当前研究 Plan |
|---|---|---|---|
| 生成第四个候选后 | `candidate_10`（第三个） | `candidate_17`，未评价 | `plan_1 → candidate_10` |
| Main 显式重新 diagnose 后 | `candidate_17` | 同一已保存候选 | `plan_3 → candidate_17` |
| 记录 fixture 数学结果后 | `candidate_17` | 1 次数学记录，`execution_incomplete` | `result_1 → candidate_17 + plan_3` |

`plan_2` 是生成动作，生成来源与研究对象分别展示。四个候选始终同时可见；结果记录不表示通过。

每条候选记录包含生成来源、当前 profile 兼容性、Plan 列表、数学记录数及最近状态、完整动态执行、独立验收、未评价标记和详情查询。评价记录包含候选、Plan、方法、原状态、Worker 事实、诊断摘要和已记录成本。

## 4. 短引用与唯一绑定

沿用 `reference_choices/reference_schema/expand_references/main_projection`：候选为 `candidate_N`，Plan 为 `plan_N`，分析为 `result_N`，独立评价沿用 `evaluation_N`。对象创建顺序决定导航名称，底层科学身份仍由原 Store/候选模型任务检查负责。

每次广告 Schema 在 `x-research-reference-choices` 保存当时的精确映射，Provider 只接触短引用。收到请求后按该冻结 Schema 扩展；随后生成对象不会改变已广告别名。未知短引用明确拒绝。Main 不重复填写已被 Plan 唯一绑定的 candidate。

## 5. 导航与字段纠错

参数组默认页保留参数 ID、物理含义、当前值、域、单位、授权/可选择状态与 `applicable_methods`，移除反复出现的执行元数据。组页最多六条，字节上限提高到 6000，参数详情仍按需读取。

ScientificQuestion v4 错误只返回最多四个简短字段问题；常见顶层错放字段带 `expected_field`，枚举问题带允许值，并明确未启动计算、额外数学/物理计数为零。原验证及准入保留；不自动改变参数、方法或预算。

## 6. 执行前信息与模式兼容

`execution_preview` 从现有 Task Adapter、候选、已存结果和预算账本读取信息，展示在工作视图和 Main information-flow brief：

- 当前候选与模式、冻结准入/验收要求、初始化方式；
- 同候选最近静力诊断引用、失败阶段事实及之后已有结果；
- 主动模式的实际 initializer 和已有控制来源；被动模式的原冻结初始化；
- PHS 十工况一次完整执行预留十个 episode，并明确会重新执行无载硬平衡及原两个初值，不能绕过先前初始化失败；
- 当前物理剩余额度、已记录执行的预留 episode 与实际 `actual_resource_consumption`；缺失事实保持未知。

失败重复提示只提供信息，不新增门禁、不增加自动数学检查、不启动 Worker、不修改预留或计费。Main 自主决定是否尝试。主动 GVS 实计算及保存的 SoRoSim 路径通过定向回归。

## 7. STOP 交接

原冻结域 `research_opportunity_review` 增加统一工作流、完整 `all_fresh_results` 和执行预览；复用已有候选、已尝试方法、未覆盖方向、前置与预算信息。读取该机会视图不先读取完整会话快照。

STOP Schema 提醒通过短引用引用全部新结果，跨候选有限搜索使用原 `empirical_search` 语义。漏引结果仍拒绝；更强的候选特定结论跨设计仍拒绝。SELECT 的独立验收及 Main 完整读取要求、Knowledge 非证据、Reporter 非决策者等原门禁均未放宽。未尝试方向不阻止自主 STOP。

## 8. 定向验证

环境：已有 `.mainline5-env/Scripts/python.exe`，`PYTHONPATH=.;tests/research`。没有真实 Provider 请求，没有完整物理 Study，没有重跑阶段一 41 项。

| 最终通过批次 | 数量 | 实测耗时 |
|---|---:|---:|
| `test_stage2_workflow.WorkflowTests` 全部六个方法（主动/被动子用例） | 6 | 62.694 s |
| 扩充 Main 最终投影与跨设计拒绝断言后的两项复验，以及六项既有/必要回归 | 8 | 37.724 s |
| 合计（12 个不同方法，两项有目的复验） | 14 次 | 100.418 s |

后一批六项为：228 接触实际初始化失败、第二初值首次 forward 失败、保存的 SoRoSim、GVS 导数子检查、实际 GVS 初始线性化、protected closeout 冻结机会读取。多初值只新增一个必要测试。短引用冻结、自动候选继承、结果 Plan 归属、预算/参数不变和全部结果 STOP 均有针对性断言。

测试代码位于 `tests/research/test_stage2_workflow.py` 和 `test_diagnostic_layers.py`。`git diff --check` 通过。工程测试记录不加入新 Study 的科学证据。

## 9. 独立后继 Study 准备

配置：`configs/research/study_phs2d_workflow_successor_20261106.json`，Study ID 为 `phs2d-workflow-successor-20261106`；配置解析身份为 `17f3a5e3facc70217332f3889336e92ab5437572fbdbe2ec9dcfcebdabb1a6a5`。

父 Store 位于原 `runs/phs2d-initialization-successor-20261105/runs/research/phs2d-mechanism-successor-20261105`。只读核对其 104 次请求、9 条数学结果、4 个候选。第四个候选无数学评价；精确候选与生成 Plan 两个对象以现有 archive 格式导出到 `evidence/stage2_workflow_preparation_20261106/history_c4`。原历史、失败和费用保留。

后继通过原 `import_history.background` 导入历史设计/原假设，当前候选须用原 `generate_candidate()` 重新绑定后再评价。不导入旧数学/物理结果、不继承 Plan、控制来源或任何授权。C4 是可选历史线索，Main 仍自行选择科研对象。

保留原九段四腱 FamilySpace、原十工况任务、物理配置、验收、求解器和工作者 watchdog。采用已有按次数预算模式，`analysis_cap_s=null` 满足原配置校验，数学 Worker 仍有原 7200 s watchdog，物理 Worker 为 1800 s。运行时复制父 Study 最终冻结配置，只包含凭据引用、不含凭据内容；未调用 Provider 检查。

拟申请的独立总上限：64 次 Provider（Main/Reporter 共用，含 6 次收尾保留）、32 次数学评价、80 个物理 episode、320 次公开操作（含 10 次收尾保留）；NMPC、RL、offline NLP、BDF 为零。Native 动态数学方法仍按原账本同时消耗适用物理额度。没有继承父 Study 的条件追加请求权限。

配置使用现有 `PENDING_EXPLICIT_APPROVAL:` 门禁。新 Study 的身份与预算必须获得用户独立明确授权；当前只准备和绑定，不启动正式研究或 Provider 预演。准备后的准确候选引用、实现冻结及授权申请见 `evidence/stage2_workflow_preparation_20261106/preparation.json` 和 `authorization_request.json`。

阶段二测试通过后停止工程扩建，等待审查及新 Study 授权。
