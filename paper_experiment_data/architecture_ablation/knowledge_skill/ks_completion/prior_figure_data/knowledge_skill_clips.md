# Knowledge / Skill 决策原文素材

六个新回放的 Decision Quality 均为 4/4；以下展示经验利用和拟议流程差异，不表述为总体决策质量分或机器人成功率改善。使用澄清参考库作用后的独立模型盲评，人工复核待完成。

## T04：原生路线与合法初态流程

**Knowledge：历史经验用于路线选择（K+S-）**

> The supplied expert history, method-selection guidance, and phase/preload guidance are used only to choose the sequence: legal structure first, then native equilibrium construction with interior tension search, independent initial qualification, schedule binding, and full replay.

来源：[result.json](D:/softrobot-agent/paper_experiment_data/architecture_ablation/knowledge_skill/sessions/f962ce0d-cc86-4c5b-ae2d-6a8579115b07/result.json) · `/decision/interpretation`

**Skill：资格验证与张力初始化流程（K-S+）**

> The delivered skill-native-equilibrium-reference-bank@1 is adopted for the planned post-generation route: use the registered native initial-state construction interface, inspect returned residuals and errors, independently qualify time zero, initialize compact absolute-tension knots, and only later request an independent complete replay.

来源：[result.json](D:/softrobot-agent/paper_experiment_data/architecture_ablation/knowledge_skill/sessions/4afdde5b-6e0f-4e46-9e03-4f1434e7e0d4/result.json) · `/decision/interpretation`

**双 OFF 对照：较一般的后续分析计划（K-S-）**

> after successful generation, a future decision should determine whether qualified equilibrium and scoped capability evidence justify control search.

来源：[result.json](D:/softrobot-agent/paper_experiment_data/architecture_ablation/knowledge_skill/sessions/10fe9d9a-ad75-45f0-a77b-5b8c4026681b/result.json) · `/decision/interpretation`

经验利用盲评分：K+S−=3、K−S+=3、K−S−=0；三者 Decision Quality 均为 4。新回放没有执行初态构造或完整跟踪。

**历史真实行动：独立初态资格验证：历史工程动作，非 LLM 输出**

> Independently qualify the recomputed interior-preload time-zero state against the unchanged force-balance gate.

来源：[T04.json](D:/softrobot-agent/paper_experiment_data/architecture_ablation/knowledge_skill/historical_reference/T04.json) · `/subsequent_actual_actions/2/reason`

历史后续链包含 211 点组构造失败、216 局部初态重试、217 独立 qualify、219 节点初始化、220 完整独立回放；不能写成首次构造即成功。最终历史 FULL 的 RMSE 为 0.0006878528448055238 m，最大误差为 0.0010206639031726755 m，仅作历史验收背景。
来源：[原始 FINAL_RESULT.md](D:/softrobot-agent/paper_experiments/five_task_completion_20261113/T04_figure_eight_tracking/T04_RUN_03/FINAL_RESULT.md) · [历史动作映射](D:/softrobot-agent/paper_experiment_data/architecture_ablation/knowledge_skill/historical_reference/T04.json)

## T07：历史布线与共同结构流程

**Knowledge：选择历史 split-span 结构起点（K+S-）**

> The key research question is whether a frozen-domain reconstruction of the historically useful two-root-only plus two-full-span, four-independent-tendon architecture provides a credible shared structural starting point for all four T07 tasks without assuming historical acceptance.

来源：[result.json](D:/softrobot-agent/paper_experiment_data/architecture_ablation/knowledge_skill/sessions/5147d10f-391d-4bac-8e16-f150b8037ea3/result.json) · `/decision/hypothesis`

**双 OFF 对照：四条全长腱起点（K-S-）**

> The key research question is whether a minimally complex two-segment structure based on the supplied family prototypes and four symmetric full-length tendons is a suitable first scientific candidate for the three reach tasks and the position-plus-tool-axis task.

来源：[result.json](D:/softrobot-agent/paper_experiment_data/architecture_ablation/knowledge_skill/sessions/439c18bd-9aa0-4fba-befd-4b65532cd8bd/result.json) · `/decision/hypothesis`

**Skill：同一结构标识上的全任务验证（K-S+）**

> The delivered shared-structure feasibility skill is adopted: it recommends stating one shared-structure hypothesis, generating a current owned candidate, then diagnosing the hardest task and validating every task on the same identity.

来源：[result.json](D:/softrobot-agent/paper_experiment_data/architecture_ablation/knowledge_skill/sessions/1b35c5a6-478e-4864-8e02-1a5917d26d80/result.json) · `/decision/interpretation`

经验利用盲评分：K+S−=4、K−S+=3、K−S−=0；三者 Decision Quality 均为 4。这里观察到流程被明确写入计划，未实际测试结构版本结果拼接或控制迁移。

**历史真实行动：仅迁移控制初始化：历史工程动作，非 LLM 输出**

> Use the preceding current-Study native control only as a named-channel initialization for a changed structure. No physical acceptance or state is inherited; all controls are freshly reintegrated.

来源：[T07.json](D:/softrobot-agent/paper_experiment_data/architecture_ablation/knowledge_skill/historical_reference/T07.json) · `/subsequent_actual_actions/8/reason`

**历史真实行动：结构版本一致性：历史工程动作，非 LLM 输出**

> All four original C1 conditions independently passed on the identical circular-root/original-tail, 14 mm-routing structure. Select the exact publicly read current physical results; no ellipse-root or other-body acceptance is substituted.

来源：[T07.json](D:/softrobot-agent/paper_experiment_data/architecture_ablation/knowledge_skill/historical_reference/T07.json) · `/subsequent_actual_actions/46/reason`

K+S+ 沿用原始首个工程 Core Plan 及其后续真实行动，未新增回放；其正式 LLM Main / Provider 调用数为零。它能提供历史联合使用的行动例证，不能作为严格匹配的联合 LLM 条件。
来源：[原始 FINAL_RESULT.md](D:/softrobot-agent/paper_experiments/five_task_completion_20261113/T07_C1_four_tendon/FINAL_RESULT.md) · [读取来源表](D:/softrobot-agent/paper_experiment_data/architecture_ablation/knowledge_skill/figure_data/snapshot_manifest.csv)
