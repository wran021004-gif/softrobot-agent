# H2 科研行动接口归因、最小修复与原 Study 续研（2026-11-04）

本轮完成零 Provider 归因、最小接口修复及定向离线验证；用户随后明确批准 +16、指定实现绑定及原 SDK 续研。
原机制两次 +8 已完成，累计上限64。新增12次 Main 均使用 Gateway gpt-5.6-sol，没有新的合法数学结果或结构候选。
在已结算边界监督暂停，保留9次额度（内含保护4次），非 Main STOP。本轮未发送至 DeepSeek。

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

## 原 Study、明确批准与正式续研

Study仍为 `passive-mechanism-autonomy-20261104`，没有创建替代Study或新harness。
离线阶段再次核实原Store/SDK的212个文件与共享授权库未改变，897个artifact哈希有效；旧费用与SDK历史完整保留。
用户随后对具体的48→64、两次+8、指定实现绑定、Gateway目标及科研上下文发送范围明确批准。
原共享授权库与Store采用既有ATTACH事务同步更新，每个+8均生成原正式授权、resolved identity、admission及core.bind。

实际绑定实现 `732856c62e90aa27e72e01c6c7a4f2a4ed1c956c`；
最终resolved identity `eca928ec8e579f2d7dcf564b98eb5b5fc9a824cf12c25eac0de5e55b409e5ede`。
科学profile `9f95b160c2aa80a89ca40d324d75fc33e660fd51a86f3fe6a65235cdc376dcd3` 不变。
原SDK restore_only后费用仍为43次/557754 tokens，实际下一条wire才刷新投影Schema，没有伪造旧历史。

保持Gateway `http://127.0.0.1:8787/v1`、精确模型 `gpt-5.6-sol`，Main none / Reporter medium。
数学累计次数null，单Worker180秒；原物理256 episode/128000步、独立Replay16次、public operations256均不增补。
没有修改原FamilySpace、任务、验收、科学参数授权、求解或积分算法。

## 请求44–55的实际行动

| 请求 | Main实际行为 | 结果 |
|---|---|---|
| 44–48 | 参数目录、数学结果、重复读取及目录下一页 | 全成功；47反馈中的授权杨氏模量完整行进入48实际wire |
| 49 | 自主改为截面方向与曲率的双参有限时域求导 | ORIGINAL_FROZEN_PARAMETER_AUTHORIZATION_REQUIRED，未启动科学执行 |
| 50–51 | 研究机会、数学结果及segment/assembly目录 | 全成功 |
| 52 | 自主提出payout敏感性的新H2，有预期、削弱条件、固定条件和停止条件；已省略research_intent | 同时提交decision.selected_candidate与多余顶层同名字段，Schema拒绝 |
| 53 | 读取研究机会 | 成功；52的精确错误在53及54实际wire可见 |
| 54 | 自主改为截面方向与半轴的双参有限时域求导 | 同一原授权门禁拒绝，未启动科学执行 |
| 55 | 再读数学结果及segment/assembly目录 | 成功；与51读取组合重复，无新科研结果 |

12次新请求均HTTP200；工具拒绝与Provider成功不同，不能把unsupported反馈计为完成求导。
Main没有提交通过的新diagnose，也没有新增inspect。原H2或替代假设均未获合法的新数值结果。
没有形成“数学反馈→新结构研究决策→新候选→独立Replay”的行动链。
没有要求Main选择某个参数、方向、方法或必须保留原H2。

实际44–55 Plan Schema均未要求research_intent，禁止顶层selected_candidate，decision内有候选字段，
且其描述明确写出“there is no top-level selected_candidate field”。52实际输入已正确填写内层候选，额外又复制到顶层。
这不是候选身份不明，也不是Schema漏送；但混合action的通用字段描述和嵌套合同仍增加理解负担，不能据此证明接口已最优。

参数枚举持续明确说明存在性不等于求导授权，数学执行入口持续可见。
47反馈的完整授权杨氏模量行在48实际wire内联，但49起已不内联该行；可通过原目录/恢复入口再读。
不能把“Store有记录”当作“之后每条wire持续展示”。旧被拒H2同样没有被冒充accepted Plan保留。
因此本轮结论限定为：在当前SDK上下文和卸载策略下，Main仍未持续遵循已交付约束采取合法行动；
归类为待验证的模型决策能力问题，尚不足以排除接口信息组织和上下文保留的影响，更不能判定模型本质无能力。

## 参数为什么被拒、是否缺少扩展

当前原冻结family_sensitivity_v2选择器只有 `segments.*.young_pa` 和 `payout_lengths_m.*`。
49/54所选截面方向、曲率、半轴不匹配该表；设计生成范围与求导授权范围是两个不同合同。
这些参数本身都已注册、连续且在当前生成模型有效，拒绝理由来自Study求导白名单，不是物理上不可研究的结论。
原用户科研指令允许Main改变研究参数组；不能把这份较窄的历史配置直接解释成用户只允许两类科学变量的永久意图。
本轮任务又明确要求不改冻结参数授权，因此没有通过接口修复偷偷扩展它。

为区别授权缺口和数学实现缺口，额外做了零Provider/Worker/积分的只读反事实：
仅在内存spec副本加入49/54实际路径，经原freeze_family_variables与parameters检查，原求导能力标记即变为supported。
原prepare_context随后继续原数值准入，发现两份双参请求至少需要10次局部评价：baseline1+两组各4个探针+joint check1。
49申请9、54申请8，仍不足；累计数学配额null并不取消单次问题的显式有限cap。
没有更改正式Store、授权或参数域，也没有执行这些探针；这不证明导数数值有效或存在改善方向。
由此目前不能把拒绝归因于“截面求导算法未扩展”，也不能声称补一个授权就能直接执行原问题。

信息呈现仍有局限：执行枚举包含不可求导参数，授权详情分离且会被卸载；
dynamic编译拒绝的顶层status为unsupported，具体reason才说明授权不足，容易混淆能力与权限。
这些是一般接口表达的候选改进点，尚未增设过滤、自动换参、重试或特例兜底。
若要扩展正式科学参数范围，应先核对范围与原科学版本迁移机制，取得相应授权；
不能用本轮纯实现bind绕过其禁止更换冻结spec的规则。

## 最终真实用量、暂停与交付边界

| 项目 | 续研前 | 本轮新增 | 最终累计 |
|---|---:|---:|---:|
| 全部Provider | 43 | 12 | 55/64 |
| Main / Reporter | 38 / 5 | 12 / 0 | 50 / 5 |
| 全部tokens | 557754 | 171278 | 729032 |
| Gateway gpt-5.6-sol Provider | 16 | 12 | 28（Main27、Reporter1） |
| Gateway tokens | 216952 | 171278 | 388230 |
| 数学评价 | 1 | 0 | 1 |
| 模型构建 / episode | 1 / 1 | 0 / 0 | 1 / 1 |
| 物理积分步 | 500 | 0 | 500 |
| 新候选 / 独立Replay | 0 / 0 | 0 / 0 | 0 / 0 |

历史其他Provider27次/340802 tokens仍保留在原账本，不代表本轮向该目标发送。
最终public operations76/256、backend solves1/256，账本worker_calls0，数学数值耗时2.177401200053282秒；货币费用unknown。
剩余9次共享Provider，4次收尾保护包含在内；原legacy准入计算还留1次预扣边界，当前可科研Main容量为4。
本轮无需新Reporter，因为没有新增已执行科学结果；没有为了用完额度发送收尾请求。

最终1141个artifact哈希有效；共享授权库config_hash匹配，全部55个Provider已结算。
无pending/unknown Worker、未结算receipt、未消费响应或占用。原SDK在已消费反馈边界暂停，非Main STOP。
所有新科学参数、Worker和物理用量为0，没有把数值失败当机制不可行或局部变化当正式验收。
没有合并main，没有启动PHS/P3。

下一阶段先做零Provider的范围与接口表达审查：厘清历史窄白名单是否符合自主结构研究目标，
以及当前action所需字段、可执行参数和卸载后的恢复信息是否构成足够清楚的决策输入；
随后才在正式授权和有限额度内验证模型的合法选择、单次预算推理及反馈利用能力。
先前更宽泛的“模型决策问题”归因已收窄；本轮实证是行动链没有完成，不是排除了所有架构因素。
私有Store、完整wire、凭据、批准全文及候选当前参数不公开。
