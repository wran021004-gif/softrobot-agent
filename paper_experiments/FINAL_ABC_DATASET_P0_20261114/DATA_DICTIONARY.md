# P0 数据字典

本目录是只读原始证据的派生数据集，未执行研究、求解、物理积分或绘图。
CSV 为 UTF-8；列表与对象字段使用 JSON。所有缺失/未知值明确为 `UNKNOWN`，不适用为 `NOT_APPLICABLE`，真实零保留为 0。

## 数据粒度

- D1：一个 task_id × method 的最终选中结果，共 33 行。
- D2：一个 task/method/selected candidate/required condition/metric 的记录。资格失败时保留已测值，并保持 evaluation_status；辅助观测不进入约束违反分母。
- D3：一条原始 Trace 或数学调用日志记录。原始调用 start/return 是不同记录；不是两次数学调用。一个事件可显式关联多个证据。
- RESOURCE_COSTS：33 条当前正式选中运行的累计成本，替换前旧 B 不进入此表。
- SOURCE_MANIFEST：指定原始实验目录及准确引用文件的清单与 SHA256；原文件留在原位，旧 B 标记为归档。
- PHS2D_9SEG_GRADIENT_FIGURE_DATA：独立九段四腱研究的原 CSV 精确字节副本。它不进入 ABC 的任务状态和违反量计算。

## 归一化定义

令测量为 x、原边界为 b、同量纲尺度为 s、原容差为 t。
上界的 signed = (x-b-t)/s；下界的 signed = (b-x-t)/s；等式为 (abs(x-b)-t)/s。
严格判据使用 t=0，边界等号仍按原判据记为违反；此时数值正向超限可以为零，不人为增加 epsilon。

- 张力：使用同一原始协议的上下限区间宽度；0–8 N 的尺度为 8 N。零边界的饱和裕量同样使用原张力区间。
- 几何行程：使用同工况原始上下限之差；±0.015 m 的尺度为 0.03 m。
- 其他非零单侧边界：使用 abs(b)，保留原物理单位。
- 零阈值的计数/布尔条件：采用一个离散单位；非零计数/周期边界仍采用 abs(b)。
- 零阈值且无原始同量纲尺度的连续量/混合量不任意除以 1：scale 和 signed 保持 UNKNOWN。
- 原始 normalization_source / normalized_violation 原样保存在 original_* 列，可对照派生统一指标。

被测且可判定的约束才进入 violation_fraction。未执行工况不能当作零违反。
maximum/total 仅统计已评价约束；若存在已评价但正向超限无法归一化的项，主汇总为 UNKNOWN，并单列已知下界。
worst_conditions 为已评价约束中最大正向违反量对应工况列表，零违反时可并列；它不代表未执行工况已被验证。

## 字段

| 字段 | 含义 |
|---|---|
| task_id | 原始任务标识；PHS-2D 为七段 C 对照任务，九段梯度研究独立存放。 |
| method | A / B / C；B 的执行主体由 method_variant 区分。 |
| method_variant | llm_only、llm_direct_math_tools、codex_direct_math_only、historical_FULL。 |
| status | PASS、PASS†、VALID_FAILURE、INCOMPLETE、QUALIFICATION_FAILED；development_valid 单独保留在 source_classification。 |
| required_conditions | 原始 required 工况数。控制及机制/数值确认不增加该分母。 |
| evaluated_conditions | 选中候选具有 valid 且 accepted 为真/假的完整合格任务评价的工况数；资格失败、未完成不计入。 |
| completion_fraction | evaluated_conditions / required_conditions。完成与通过分开。 |
| violated_constraints | 已评价且可判定的 required 数值/布尔约束中不满足原始判据的条数。 |
| violation_fraction | violated_constraints / evaluated_constraints；没有已评价约束时 UNKNOWN。 |
| maximum_violation | 已评价约束的最大 positive_violation；不是不同物理量的平均。 |
| total_violation | 已评价约束 positive_violation 之和；仅累加归一化量。 |
| evaluation_coverage | evaluated_constraints / expected_constraints；包含原始资格要求，A/B/C 同任务同工况采用同一约束模板。 |
| protocol_deviation | 真实协议偏离标志；T03-B 为 true。 |
| source_refs | JSON 字符串数组；原始路径及 #L行号、#artifacts/ID、JSON Pointer 或 CSV 行/条件定位。阈值模板引用有 use=threshold_only_not_measurement 注记。 |
| candidate_id | 原始候选 ID 或原始运行内的候选别名；新 B 为验收记录中的 design_identity。别名必须按 task/method/run 作用域解释。 |
| condition_id | 原始 required 工况 ID。 |
| metric_id | 原始评价器约束或观测名。qualification.* 为既有资格记录。 |
| metric_value | 原始 SI 数值或类别观测；原始布尔观测明确转为 1/0。缺失为 UNKNOWN。 |
| unit | 原始量纲；N*m 统一拼写为 N.m，不改变数值。 |
| threshold | 原始任务或资格记录中的边界。无验收阈值的辅助观测为 UNKNOWN。 |
| bound_type | upper / lower / equal；非约束观测为 UNKNOWN。严格性由 strict 单列记录。 |
| normalization_scale | 同量纲归一化尺度，规则见下。没有合法尺度时 UNKNOWN。 |
| signed_normalized_violation | 有符号超限量；负值为裕量，零为边界，正值为违反。 |
| positive_violation | max(0, signed_normalized_violation)。若尺度未知但原始已测判据满足，正向违反量可确定为 0，signed 和 scale 仍为 UNKNOWN。 |
| is_violated | 按原始上下限、strict 和 acceptance_tolerance 判定；未测量为 UNKNOWN。 |
| source_execution_id | 仅保留原始明确记录的执行 ID；不使用研究 ID 或推定时间段代替。 |
| source_artifact_id | 原始 Store 的 artifact ID；文件/缺失阈值模板来源无此 ID 时 UNKNOWN。 |
| event_id | P0 的可逆定位键 task/method/trace/L行号；原始事件 ID 另存 original_event_id。 |
| sequence | 原始文件中的行号；每个 trace_id 内排序。 |
| event_type | 原始 kind/type，或新数学记录的 math_start / math_return；不改写成新的研究事件。 |
| evidence_id | 同一原始事件显式引用且已定位的证据列表；无显式引用为 UNKNOWN。 |
| decision_id | 同一原始决策的 ID；非决策事件为 UNKNOWN。 |
| action_id | 同一事件明确声明的动作或原始工具调用的定位键；不由相邻事件反推。 |
| relation_id | 显式 evidence-to-declared-action 关系 ID 数组；无关系为 UNKNOWN。 |
| record_scope | selected_run / precursor_run；前驱研究事件保留但不增加 required 成功数。 |
| core_shas | 原始 Trace 的 Core SHA 集合，保留多版本；七段 PHS 的配置 base_commit 有 core_sha_basis 注记。 |
| wall_time_s | 来源明确的原始耗时；必须联合 wall_time_scope 解释，UNKNOWN 不能当零。 |
| llm_tokens | Main Provider Token；未知为 UNKNOWN，新 B 无 Provider 因而为实测确定的 0。Codex 自身对话 Token 另列 codex_llm_tokens=UNKNOWN。 |
| integration_steps | 原始累计积分计数，不从 CSV 行数擅自替代；T08-A 总数 UNKNOWN，单列已确认下界。 |
| sha256 | 原始文件精确字节的 SHA256；不是候选设计 ID。 |
| source_id | 来源清单唯一键；同一路径仅一条。 |
| snapshot_status | 读取前后大小与 mtime 不变为 UNCHANGED_DURING_READ。 |
| formal_scope | ARCHIVED_REPLACED_B 明确表示旧 T03-B/T05-B 仅归档；不得用于正式绘图。 |

其他字段：run_id 保留原运行标识；required/evaluated_condition_ids 为工况列表；evaluated/expected_constraints 为覆盖率分子分母。
selected_candidate_ids_by_condition 保留原始各工况候选配置 ID。T01/T02/T07/T10 的 C 组存在不同工况绑定 ID，已从 Store 精确核对 robot.structure 和 discretization 相同；不合并或改写这些原始 ID。
normalization_basis、source_validation、missing_reason、acceptance_tolerance、strict 解释单行派生口径。
original_* 保留原始标记，不用于替代当前正式状态。method_variant 和 discretization_note 是新 B 的必要比较背景。
evidence_action_links 是显式关系条数，selected_run_evidence_action_links 排除前驱研究；声明关系不证明动作执行或改善效果。
资源字段 math_cpu_s、physics_cpu_s、internal_*、physical_steps、math_internal_physics_steps 均只使用已有记录；无计数保持 UNKNOWN。
SOURCE_MANIFEST 的 bytes、mtime_utc 是原文件快照元数据；mtime 保留原字符串微秒精度，未通过电子表格日期自动转换。

## 使用限制

T03-B 使用 PASS† 并保留意外 GVS 元数据投影尝试的协议偏离。T05-B 为标准物理 PASS。
两项新 B 每段仅一个合法弯曲单元；不能推断到旧 B 的较细网格。B 是混合执行主体，按 method_variant 明确标注。
T08-C 的 development_valid / development_not_registered_SELECT 标签不能删除。
控制组与机制/数值确认数据仍完整保存在原始 Store、Trace 和 SHA 清单中，未作为 D2 required 工况重复计数。


## Git 发布版路径与原始证据（2026-11-15）

本次发布仅包含本目录列出的九份交付文件。SOURCE_MANIFEST.path、source_refs、source_version、evidence_id 中的路径，以及配置和成本来源中的路径，统一为以仓库根目录为基准、使用 `/` 的相对来源标识；行号、Artifact ID、JSON Pointer 等定位片段保留。`.audit-task-a/` 表示审计时实际使用的本地工作树来源，不改写为另一份来源。

来源标识用于离线追溯，不保证原始证据可通过 GitHub 下载。46,238,300,835 字节的原始证据、Store、Trace、完整轨迹与 `_build` 均不随本数据包上传。SOURCE_MANIFEST.sha256、bytes、mtime_utc 仍对应审计时的原始文件，未重新计算或更改。

发布前九份文件的精确本地副本保存在 `_build/local_frozen_before_publication_20261115/`，该目录不提交。仅替换来源路径表示并补充发布说明；所有实验数值、状态、阈值、资源记录、事件关联和行数保持不变，独立九段梯度 CSV 保持原始字节不变。
