# H2 科研行动接口归因与续研准备（2026-11-04）

本轮完成零 Provider 归因、最小接口修复及定向离线验证。原 Study 未改绑、未增补、未续跑。
48→64 的 +16 共享 Provider 范围已准备，仍待用户明确批准；不发送至 DeepSeek。

## 实际请求37–43归因

基线报告 c981056；原执行实现 a9873b9。独立修复分支 `codex/h2-action-interface-20261104`。

| 请求 | 实际行为及归因 |
|---|---|
| 37 | 采用修复后的 mathematical_results，获得真实基线事实与限制，非目录替代 |
| 38 | 选择授权杨氏模量与未授权截面参数做求导；原门禁正确拒绝，未启动 Worker |
| 39 | 读取数学结果、注册参数及研究机会；目录/事实可达 |
| 40 | 提出H2，但多余顶层 selected_candidate 和错误 intent 均不符合已交付 Schema；Host先报告前者 |
| 41 | 读取数学结果；实际 wire 中可见前一拒绝提议的H2原文 |
| 42 | 删除多余候选字段，intent仍不是 DIAGNOSE，Host正确拒绝 |
| 43 | 再读已有数学结果，没有获准的H2新 Plan |

请求38前，已读取的 segment 目录明确展示杨氏模量 study_authorized=true、selectable=true，
但该次读取未展示被选择的截面参数。数学工具实际 parameter_paths 枚举却包含后者，
只称其为 registered physical parameter，没有同时标出未授权；不能推断 Main 当时已看见该参数的拒绝标记。
目录的 parameter_catalog 投影还省略了原注册行的范围、设计支持和具体求导限制。
原 FamilySpace/数学授权源明确区分：该截面参数可用于合法生成，但不在本 Study 的求导授权内。
原拒绝被只读 compile_question 精确复现；未扩大授权。

请求40/42的实际 research_plan Schema 正确交付，禁止顶层 selected_candidate，
要求 decision.selected_candidate，并包含 diagnose→DIAGNOSE 条件常量。
用原实际 Schema 校验，删除多余顶层字段并修正 intent 后，两份完整科学提议均通过 Schema。
因此两次拒绝不是 Schema 交接错误；但 intent 的确是 action 的唯一确定性重复字段。

请求37–43的数学数值、数值限制和 research_analysis Schema 持续可见。
H2只在提议后的精确反馈请求41/43内联可见，当前 SDK snapshot 未内联H2；
两份被拒提议的完整 hypothesis / weakening_observation 及原输入恢复入口仍保存于原 Store。
H2未成为 accepted Plan，程序没有把被拒提议冒充已获准意图。Main仍可从原输入恢复它，或自主提出其他假设。

## 最小修改与边界

1. `object_choices.main_tool_schema`：只在高层 Main Plan 投影删除 research_intent，包括条件/required位置。
   `bind_plan_selection` 使用原 PLAN_RESEARCH_INTENTS 按 action 补齐缺失值，随后进入原完整 Plan 校验。
   原 ResearchDecision 合同保持必填；旧输入已显式提供的值不被静默改正，仍受原一致性验证。
2. 候选仍由 Main 明选 decision.selected_candidate。没有顶层候选别名，没有从唯一/当前候选静默推断；
   歧义与缺失仍拒绝。hypothesis、预期/削弱观察、固定条件、解释和停止条件逐字保留。
3. `parameter_catalog` 只投影原注册 domain、design_supported、differentiation、authorization_reason，
   以及 execution_admission=not_checked；语义 summary 也保留这些区别。
   数学 Schema 明确枚举代表存在性而非求导授权，要求核查原目录并经原方法/工作点准入。
   没有自动换参、第二套参数域/Registry、关键词映射或新的 Worker/调度器。

`agent.plan_schema`、原 ResearchDecision 和 structure_research.parameters 的原始约束正确，无须改写。
数学支持是候选级注册能力，不是实际工作点数值有效性证明；后者仍由原编译/Worker检查。
科学模型、算法、任务阈值、评价器、参数授权均未修改。

## 回归

25项不同定向测试通过，其中6项H2新增回归覆盖：
全action意图补全、候选绑定只读diagnose、科学字段完整保留、候选歧义不代选、
设计/授权/求导能力及范围区分、V4合法编译和未授权拒绝、实际SDK Mock高层Plan、旧Schema恢复刷新。
合法单参V4请求进入原准入，5点评价需要5个episode/2500步的上界被正确计算，但未执行 Worker。
既有 SELECT/STOP、证书阅读信用、Reporter真实来源、Store反馈和预算恢复回归通过。

另1项旧F2大结果夹具失败于 OWNED_RESOLVED_CANDIDATE_REQUIRED；在未修改c981056上复测同样失败，
不属于本次回归，也未为它改生产来源门禁。保留失败日志，不计作通过。
初始新夹具还暴露有限默认数学额度不足5点评价、误用已去除SDK别名映射的wire Schema两项测试问题，
仅修正离线夹具后通过，没有修改生产预算或授权。

## 原 Study 与待批准增补

原 Study：`passive-mechanism-autonomy-20261104`。
原实际实现仍为 `a9873b995150afd499182f3817d1df1c72d297aa`，resolved identity为 `d9ef09d43645415a67c79980631c9cf145c06abaa3ec070453ae2372d6713fc3`。
科学 profile `9f95b160c2aa80a89ca40d324d75fc33e660fd51a86f3fe6a65235cdc376dcd3` 保持。
最终再次逐文件核实原Store/SDK及共享授权库与本轮开始相同；897个artifact哈希通过，
43个Provider已结算，无pending/unknown Worker、未消费响应或占用；原完整备份复用，无第二份Study备份。

| 项目 | 当前 | 待批准后 |
|---|---:|---:|
| 共享Provider总额 | 48 | 64（两次原子+8） |
| 已用 / 剩余 | 43 / 5 | 43 / 21 |
| 总额内保护收尾 | 4 | 4 |
| Main / Reporter累计 | 38 / 5 | 保留并继续累计 |
| 累计tokens | 557754 | 保留并继续累计 |
| 数学评价 / 积分 | 1 / 500步 | 保留并继续累计 |

限定同一Gateway `http://127.0.0.1:8787/v1`、精确 `gpt-5.6-sol`，Main none / Reporter medium。
数学累计次数null，单Worker180秒；原物理256 episode/128000步（已用1/500），独立Replay16次（已用0），
public operations256（已用60）均不增补、不重置。Main/Reporter/保护收尾同账本。
费用货币值仍unknown；本轮新增真实Provider、正式Worker、物理积分均为0。

待批准的操作是：明确新累计上限64，按原每次最多+8机制更新授权/共享索引/预算/身份，
正式绑定本轮已提交接口实现，再 restore_only 核验旧历史，发送前刷新工具Schema，
使用原有限请求入口进行约每4次Main的只读监督。不注入H2方向或参数/方法，不保证必须执行求导。

H2尚无合法的新数值结果，没有新增候选或独立Replay；数学指导结构研究仍待真实续研检验。
若合法数据和工具已充分交付仍不行动，将归为待验证的模型决策能力问题，停止扩建兜底。
本轮报告提交不代表Store已升级。不得在批准前发送，不合并main，不开启PHS/P3。
私有Store、完整wire、凭据、原批准全文及当前候选参数不公开。
