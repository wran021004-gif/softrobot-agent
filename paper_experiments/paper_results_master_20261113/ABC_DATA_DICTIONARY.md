# ABC 数据字典（D1–D3，2026-11-14）

仅整理已完成的 11 项 FULL、第一批 8 次和第二批 14 次 A/B。未调用 Provider、仿真、优化或梯度验证，未绘图、改论文或历史 Store。CSV 使用 UTF-8 BOM、RFC 4180 引号规则；结构化单元格是 JSON。空单元格表示缺失或不适用，真实测量的 0 保留。

## 文件与统计

| 文件 | 记录数（不含表头） | 主键/用途 |
|---|---:|---|
| ABC_STATUS_MATRIX.csv | 33 | task_id + method；11 × A/B/C 的正式主记录 |
| ABC_CONDITION_METRICS.csv | 3679 | task_id + method + condition_id + condition_role + metric_name；逐工况评价及资格/确认指标 |
| ABC_EVIDENCE_ACTIONS.csv | 597 | run_id + decision_id；研究决策与实际返回证据 |

D1：PASS 11、EVALUATED_NOT_PASS 17、INCOMPLETE 5。D2：3446 条有值、233 条空值；required 3085、control 142、mechanism_confirmation 220、numerical_confirmation 232。行数是指标数，**不能当作通过工况数**。全部 30 个 required 工况在 A/B/C 均有记录。

D3：explicit_trace 133（A 3、B 23、C 107），chronology_only 464，inferred 0。506 条属于选定运行，91 条属于 T04/T10 的真实前序运行。不同 run_id 内相同事件名不是同一次实验；同一 run_id + decision_id 的镜像记录去重。

## D1 字段与状态

| 字段 | 定义 |
|---|---|
| task_id, task_name | 历史任务标识和名称；名称保留原来源文本 |
| method, method_name | A=LLM only；B=LLM + direct math tools；C=historical FULL |
| status | PASS：全部 required 通过；EVALUATED_NOT_PASS：已有有效物理/资格评价但要求不全满足；INCOMPLETE：尚无完整任务结论 |
| status_detail | JSON：原始 scientific_result、运行状态、停止/选择来源、资格失败原因及精确成本匹配信息 |
| required_pass, required_total, required_pass_ratio | 已确认通过数、协议 required 数、二者之比；INCOMPLETE 的 0/N 仅表示尚无已确认通过，不能解释为 N 次物理失败 |
| control_pass, control_total | control 单独计数；没有该角色时为空；有协议 control 但未执行时 pass 为空、total 保留协议数 |
| run_id | 正式 A/B 或实际选中的历史 FULL 运行；不是 task_id 的替代写法 |
| source_classification | 保留来源边界。T08-C 明确为 development_valid; development_not_registered_SELECT |
| source_reference | JSON：权威汇总文件及实际结果位置 |
| source_version | JSON：提取基线提交、快照日期、汇总归属、原始版本/配置位置。基线提交不代表所有实验的执行版本 |

第一批以 batch1_results_repaired.csv 为准；第二批 batch_results.csv 中的重复第一批行不覆盖修复表。T04-B targeted_supplement 不替换 original_formal，因此主矩阵恰好 33 行。补充位置为 `../ab_batch1_20261114/SUPPLEMENTS/issue1_20261114/T04/B/`，本表没有把其额外预算或执行结果拼入原运行。

原始科学分类映射：PASS→PASS；VALID_FAILURE、INITIAL_CONDITION_FAILED、QUALIFICATION_FAILED→EVALUATED_NOT_PASS；INCOMPLETE→INCOMPLETE。不是依据预期状态表硬编码，也不能只看 budget_complete 就断定未评价。

## D2 字段、比较与缺失

| 字段 | 定义 |
|---|---|
| task_id, method, run_id | 对应 D1 的实际选定运行 |
| condition_id | 原工况名；独立 T08 确认使用 `plus_x:baseline`、`minus_x:ablation`、`:half_timestep`、`:initial_perturbation` 等；saved_state_replay 为独立记录复核 |
| condition_role | required / control / mechanism_confirmation / numerical_confirmation |
| metric_name | 原评价器约束名、原始标量名；`qualification.<stage>.*` 是分阶段资格诊断，不能当作轨迹性能 |
| metric_value, metric_unit | 原测量/评价器标量及单位；另有 predicate 和 category 类型。m、m/s、N、N.m、rad、rad/s、s、count、1 等保留来源含义，不跨单位合并 |
| acceptance_operator, acceptance_threshold | 原比较方向和阈值；未定义验收界限的诊断值为空，不能自行推定通过 |
| acceptance_tolerance | 原始比较容差；`<`/`>` 与 `<=`/`>=` 严格区分 |
| normalized_violation, normalization_source | 仅复制原评价证据保存的归一化结果/来源。允许负值表示裕量；不统一截断为 0，不给主动任务自造归一化公式 |
| metric_pass | 原评价器该项检查结果；不是整个工况是否通过。测量可通过而该阶段资格失败；空测量不填 False |
| evaluation_status | evaluated、valid、qualification_failed 等保留评价层级；空测量统一 unavailable |
| source_artifact | 精确 Store artifact/JSON Pointer、result.json 或已有汇总记录；缺失行另列 threshold_template，明确阈值来源不等于测量来源 |
| source_version | 与 D1 相同的版本边界，实际执行 implementation/evaluation_version 仍以引用的 immutable artifact 为准 |
| missing_reason | 只在 metric_value 为空时填写；未执行、资格失败、原评价器 null、未序列化分别说明 |
| candidate_id | A/B 为该运行内实际候选别名；C 为原 artifact ID。部分已有辅助汇总没有重复候选 ID，可通过 run_id/原始来源定位 |

只取 selected 候选；同一候选同一工况多次评价，取结果中最后一次实际记录，不挑最优值。C 取历史已选结果，工况控制可不同，不能移植其他结构的最佳工况。约束量和评价器的描述性别名可同时存在（例如 terminal_position 与 terminal_error_m），不要相加或重复当作独立性能证据。

资格阈值的 `<=` 来自冻结评价实现 `extensions/reference/passive_program.py:qualification`（本地已读 core-five-task-native-feedback-20261113 工作树，core 56cc418）及 passive_evaluation_v2.py。qualification 指标的 qvel/tail_drift 可能是源协议中的 diagnostic；只有原始 checks/资格结果决定通过，不按行数重新投票。

关键缺失：T02-A 缺两个 required 工况；T02-B、T03-B 没有完整评价标量；T04-B 初态失败，完整 22 秒轨迹指标 unavailable；T08-A 墙钟停止；T10-A 缺两个冲击工况和两个 control。T03 arrival_time、terminal_speed 未被该评价器作为标量序列化，不用保持速度代替。T10-A/B 的全程 maximum_error 标量未保存；C 已从实际 profile 提取。未恢复的 recovery_time 保留 null/空，不记为 0 秒。T08-B paired_mechanism 的两条值因 recovery 资格失败而缺失。

### 必须保留的科学边界

- T04-B 的初态资格失败不是完整轨迹失败。
- PHS-2D A：加载阶段资格失败，且原评价明确报告 ILLEGAL_TENDON_ROUTE_AT_CHECKED_POSES。
- PHS-2D B：加载阶段 static_balance 资格失败；原始十个 episode 的 route_geometry 均为 legal_at_checked_poses。不能沿用预期说明将 B 也写成腱路不合法。
- PHS-2D A/B 实际已返回的加载测量保留，但 evaluation_status 为 qualification_failed；不把这些未合格测量当成任务通过。
- T08-B 正负方向 recovery/static_balance 失败，独立数值确认未完成。T08-C 已保存的独立机制/步长/初态/状态回放确认使用单独 role，不能增加 required 总数。
- T10 frozen control 两个方向均独立保留。C required=3/3，control=0/2；不把 control 失败改成 required 失败，也不隐藏 control 结果。

## D3 字段与因果强度

| 字段 | 定义 |
|---|---|
| task_id, method, run_id, study_id | 真实研究归属；前序运行保留自己的 run_id，不冒充最终通过运行 |
| decision_id, sequence_index | 原事件/请求编号及同一原 Trace 内顺序；跨运行不能直接排序比较 |
| hypothesis_before | 原 Trace 明确记录的研究问题/假设；不存在就留空 |
| evidence_type | mathematical / physical / task_evaluation / historical_knowledge；协议或既有来源先验归入最后一类，不代表数学结果 |
| evidence_source, evidence_artifact, source_trace | 原记录位置与 JSON 引用数组；完整数据始终留在原始来源 |
| evidence_summary | 实际被引用的证据或 Agent 公开引用文字；大 payload 仅摘录并明确完整来源 |
| observed_physical_phenomenon, mathematical_result | 区分物理/评价观察与数学工具返回；数学成功、物理成功与决策效果不能互相替代 |
| agent_interpretation, decision | 原公开解释和选择；保留当时接口故障、错误理解和不确定性，不用事后修复结论改写历史解释 |
| action_type | topology_change / geometry_change / material_change / tendon_routing_change / control_change / initial_condition_change / mathematical_method_change / research_question_change / rollback / stop_or_confirm；多种参数同时涉及时为主要行动分类，以原 commands/参数内容为准 |
| design_parameter_changed, control_parameter_changed | 保存请求的生成/控制参数；requested_generation 是所请求的候选配置，不表示每个字段都改变或生成必定成功。成功与否看实际返回/后续评价 |
| candidate_before, candidate_after | 已观察到的候选引用集合；一次请求可涉及多个候选，不能将集合拼成单一最终结构；未知为空 |
| subsequent_evaluation, evaluation_outcome | 实际后续工具结果、错误、数学/物理结论或可定位的后续观察；不自动将工具 completed 写成任务 PASS |
| action_effect | improved / worsened / mixed / unchanged / inconclusive / no_followup_evaluation；默认保守，只有有依据的局部比较才标改善/变差 |
| evidence_linkage | explicit_trace：明确证据、解释与行动关联且可定位；chronology_only：保存公开决策但尚不足以建立完整直接证据链；inferred：分析者推断（本次无此类） |
| confidence | high 表示链路可追溯，**不表示 Agent 解释科学上正确或效果已证实**；limited 表示关联不足 |
| agent_attribution, record_scope | 正式 A/B LLM 或历史 FULL surrogate Main；selected_run / precursor_run。C 本身是历史流程，不伪称本次新做的匹配实验 |

explicit_trace 只表示记录支持“该证据被用于决策”，不是隔离变量后的科学因果效应。绘图优先筛 explicit_trace，仍须分别审阅 effect 与 evaluation_outcome。T01-B c2→c6 的中心终点改善而保持速度变差标 mixed；T07-C 三条局部改善/变差只对 M1_A 有效，不泛化为四任务总体效果。其余 586 条 inconclusive、7 条 no_followup_evaluation 不填成功标签。

T10-C 的静力参考、完整切线、离散 LQR 和有界张力控制来自已选执行的 native_feedback_preparation 与实际 recipe；准备结果放在后续证据位置，不倒置为生成决策之前的数学原因。三 required 工况和两 frozen control 使用各自原独立结果。T01-A 当时的包装错误文字保留；D1/D2 使用后来修复的实际物理结果。

## 精确 FULL 来源与成本

| 任务 | 选中的 run_id |
|---|---|
| T01 | codex-expert-T01-20261113-s1 |
| T02 | codex-surrogate-T02-20261112 |
| T03 | codex-surrogate-T03-20261112 |
| T04 | codex-expert-T04-20261113-core029-interior |
| T05 | codex-surrogate-T05-20261112 |
| T06 | codex-surrogate-T06-20261112 |
| T07 | codex-expert-T07-20261113 |
| T08 | codex-surrogate-T08-20261112 |
| T09 | codex-expert-T09-20261113-core027 |
| T10 | codex-expert-T10-20261113-verified-common |
| PHS-2D | psd2d-core-fresh-20261112 |

11 个运行均与 RESOURCE_COSTS.csv 按精确 run_id 唯一匹配；匹配信息写在 D1 status_detail，不增加重复成本表。T01 使用 STORE_CORRECTED_PROTOCOL 的结果，研究过程仍对应原 STORE_RESEARCH；T04 使用 T04_RUN_03，T07 使用精确完成运行，PHS 使用七段四腱 fresh-store，不采用 main_nominal、halfstep 或九段成本。原成本未知字段依旧未知，未补 0。

第一批原始提交 9b06a07c9，修复基线 94f3ae60c（PR #2，未合并）。第二批汇总及 12.1 GB 原始数据是当前本地来源，未 Git 跟踪；不假称其内容属于 94f3ae60c。历史 C 的配置基线、实际执行 implementation、后续元数据修复版本分别存在；T08 特别保留原 a77d79e 执行及 development_not_registered_SELECT。精确版本以原 result、Trace、CORE_LOCK 和配置为准，不用当前分支版本替换。

来源引用约定：`.../platform.sqlite#artifacts/<id>#/pointer` 表示只读 SQLite artifacts 表的 body 与 JSON Pointer；`#L<n>` 为 JSONL 一基行号；`#event_id=`、`#call_id=` 为原 Trace 字段选择；CSV 后的 `#condition` 或 `#run_id=` 是逻辑行定位。路径保留当前 Windows 工作区，可通过相同根目录迁移；不会自动下载或恢复原始数据。

## 九段独立数学数据索引

`study_id=PHS2D_9SEG_INDEPENDENT_DEVELOPMENT`；`agent_attribution=not_agent_full_run`；原 recorded study_id 为 `phs2d-inverse-passive-design-20261028-v2`，source_commit 为 `9d6d160e050c836b87d0563a497fc0ec1c3761a8`。目录：

`D:\softrobot-agent\.audit-task-a\paper_experiments\paper_results_master_20261113\`

- PHS2D_9SEG_GRADIENT_VALIDATION.csv：6 条分支记录。
- PHS2D_9SEG_GRADIENT_FIGURE_DATA.csv：18 组梯度配对。
- PHS2D_9SEG_GRADIENT_VALIDATION.md：原证据说明与规范。

已核对文件存在、可读、行数和原 study_id。原文件保持不变，没有重做 18 组验证或新增哈希审计。九段共同模量方向的局部 KKT 隐式梯度属于独立 development；未加入 D1、D2 或 C 的 LLM Agent Trace。将来使用原 CSV 的 mm/du、m/du 与 ratio/du 时遵守其原单位/参数归一化说明。

## Skill 与复现

当前安装目录 `C:\Users\gugugaga\.codex\skills`、`C:\Users\gugugaga\.codex\plugins\cache` 及仓库 skills 的 SKILL.md 中未发现 Figures4Papers / Scientific Figure Making。没有虚构路径、下载或安装。D4 尚未执行。

只读复现：`python paper_experiments/paper_results_master_20261113/extract_abc.py`。脚本仅写三个 ABC CSV，依赖已有本地结果，使用标准库与 SQLite mode=ro，不导入实验运行代码。内置最小检查包括 33 行/三方法/三状态、原科学分类映射、所有 required/control 工况、唯一指标键、缺失原因/单位/比较方向、证据 Trace 行定位和九段独立文件计数。交付前额外逐个验证 D3 所引用的 Store artifact ID 和源文件可定位；没有全仓库哈希或大规模测试。
