# 11 项任务的 Knowledge × Skill 最终结果

原生记录重建出 44 个已结束研究单元，26 个同时取得原任务验收与正式 SELECT。K+S+ 在 11 项任务中全部通过。无科研重跑，未修改原始单元。

|条件|通过|比例|
|---|---:|---:|
|K−S−|3/11|27.3%|
|K+S−|6/11|54.5%|
|K−S+|6/11|54.5%|
|K+S+|11/11|100.0%|

|任务|K−S−|K+S−|K−S+|K+S+|
|---|---|---|---|---|
|T01|未选择|未选择|通过|通过|
|T02|通过|未选择|通过|通过|
|T03|未选择|通过|未选择|通过|
|T04|未选择|未选择|通过|通过|
|T05|未选择|通过|通过|通过|
|T06|通过|通过|通过|通过|
|T07|未选择|通过|未选择|通过|
|T08|未选择|通过|通过|通过|
|T09|通过|未选择|未选择|通过|
|T10|未选择|通过|未选择|通过|
|PHS2D|未选择|未选择|未选择|通过|

Knowledge 的描述性边际差为 +36.4 个百分点，Skill 为 +36.4 个百分点，差中差交互项为 +18.2 个百分点。计算采用 11 个任务的配对二元终态，逐任务值在 summary/FACTORIAL_EFFECTS.csv。没有据此进行显著性、普遍协同或无限推广的判断。

Knowledge 条件的独特通过模式出现在 T03、T07、T10；Skill 条件的独特通过模式出现在 T01、T04。PHS2D 仅联合条件通过。T02 的基线也通过，T08 的两个单资源条件均通过，因此 T08 不是 Skill 独有贡献案例。T06 四条件通过。T09 的 1/0/0/1 模式和 T02 的 1/0/1/1 模式提醒我们，资源开启与结果不是逐任务单调对应。

## Trace 对论文叙事的支持范围

Knowledge 资源正文确实包含把物理能力、数值收敛和任务验收分开分析的科研经验。T02 的精确读取与后续 equilibrium 能力查询形成明确的诊断链。Skill 正文把匹配参数干预组织成可执行步骤，T10 的精确读取、引用和 max_iterations 单因素构造记录了这种程序变化。它们分别支持“经验供给”和“策略组织”的具体过程描述，但没有单独识别对最终验收概率的因果贡献。

44 单元共有 16 次可选 Knowledge/Skill 检索接口操作，其中 3 次实际取得该接口的正文。实际交付的上下文及其显式证据读取另列于 CONTEXT_EXPOSURE.csv 和 CONTEXT_READS.csv，并保存原始交付包，不能将可选检索数误当成全部上下文暴露量。大多数优先候选没有独立 Knowledge/Skill 检索链，所以不能用它们的通过结果补写未发生的特定资源采纳。资源总表区分空搜索、读取、adopted、context_only、显式动作链接和未知因果作用。

“Knowledge 提供物理与科研经验，Skill 提供可执行研究策略，联合条件在本组 11 项任务全部通过”可以作为资源设计与实测终态的叙述。把它写成“Trace 已证明每项任务由双资源协同而成功”则超出证据。

本报告比较已记录的最终工作流结果。各单元的最终上下文和实际资源上限存在差异，物理预算原始值与最终值均逐单元列出；时间终止和接口中断也影响成本与可达阶段。因此这里的因子对比是描述统计，不能解释为严格固定资源、随机重复条件下的独立因果效应。

## 过程、成本和可比性

完整候选、数学完成状态、物理证据和实际调用分别统计，操作数不作为有用决策数。物理成本使用原生 shared ledger 的 backend_solves 实际计费，独立保留启动计数，防止把中断或恢复的计数差异混算。数学计数、完整数学证据、物理积分步和保守数值计费也分列。

Token 来自已记录 turn.completed 的去重计数，input 包括 cached input，reasoning 不再次相加。中断而缺失的用量与 provider 请求次数仍未知。物理积分步仅报告有原生记录的合计及缺失条目数。墙钟时间包含等待，不能解释为纯求解器时间。任务违约值按原生有效性和同一结构的完整必需工况计算，未覆盖工况保留缺失；不混合异质任务的量纲与约束强度。

## 案例、盲评和历史参考

六项主案例为 T03、T05、T01、T04、T09、PHS2D，24 条条件匹配详细轨迹见 selected_cases/CASE_STUDIES.md。T02/T10 的资源读取链、T06 的中性对照和 T07 的条件模式另行保留。实际作用链强度限制已写入每项案例，选择主案例不隐去其余单元。

既有盲评报告没有有效评分，仍为 0/44。本次没有制造评分或将非盲阅读伪装成独立盲评。历史 FULL 参考表独立归档，不作为四条件中的额外重复。

## 交付内容

44 个清单、完整决策和操作摘要、资源及费用表、候选演化、逐任务因子差、全部验收与最终回执，以及 7 张主图和 5 张补充图。每张图同时提供 PNG、矢量 PDF 与独立 CSV 源数据。

|文件|内容|
|---|---|
|[figure_01_acceptance_matrix](figures/figure_01_acceptance_matrix.png)|All 44 native endpoints. No accepted SELECT is not an impossibility result.|
|[figure_02_factorial_effects](figures/figure_02_factorial_effects.png)|Task-paired differences, no significance or resource-isolated causal claim.|
|[figure_03_research_progress](figures/figure_03_research_progress.png)|Stages are independently observed, not ordinal scores or useful-decision ratings.|
|[figure_04_action_evidence](figures/figure_04_action_evidence.png)|Replay operations are a subset of physical evaluations, not an extra disjoint total or an assumed confirmation requirement. Operation count is not useful-science count.|
|[figure_05_progress_cost](figures/figure_05_progress_cost.png)|Shared ledger physical charges; failed or incomplete launches remain in costs. No equal-limit efficiency claim.|
|[figure_06_resource_transfer](figures/figure_06_resource_transfer.png)|All three successful resource body reads, including a neutral disposition and an unaccepted endpoint.|
|[figure_07_case_studies](figures/figure_07_case_studies.png)|Selected for diagnostic value, including empty retrievals and atypical comparisons, not all positive transfer examples.|
|[supplement_01_candidate_evolution](figures/supplement_01_candidate_evolution.png)|Violation definition and validity are recorded per evidence artifact. No missing or partial point is assigned zero.|
|[supplement_02_resource_access](figures/supplement_02_resource_access.png)|Resource availability is distinct from retrieval, reading, adoption, and beneficial transfer.|
|[supplement_03_token_tool_usage](figures/supplement_03_token_tool_usage.png)|Input includes cached tokens; provider request counts and missing interrupted usage remain unknown.|
|[supplement_04_decision_timelines](figures/supplement_04_decision_timelines.png)|Colors: structure blue, mathematics purple, physics amber, closeout green. No useful-decision score is inferred.|
|[supplement_05_transfer_contrasts](figures/supplement_05_transfer_contrasts.png)|Endpoint transitions are descriptive associations. A negative transition alone is not a proven negative-transfer mechanism.|

原始 44 单元目录共索引 623,454 个文件，合计 299.58 GiB。原始大型 Store 和逐步数值文件留在本地原目录，完整文件索引为 raw_archive/ORIGINAL_FILE_MANIFEST.csv.gz。Git 交付压缩的精选原始 Trace、全部紧凑统计、证据元数据、配置、图和复现脚本，不宣称把所有大型原始数组上传。实际提交文件及 SHA256 见 raw_archive/DELIVERY_FILES.csv。
