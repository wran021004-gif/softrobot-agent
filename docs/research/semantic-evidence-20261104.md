# 科研语义取证接口（2026-11-04）

## 基线与安全封存

基线与远端 `codex/passive-autonomy-live-20261104` HEAD 均为
`8517772445741d7871a5b0c468249637e5688ce1`。
独立开发分支：`codex/semantic-evidence-20261104`。
原 Study：`passive-mechanism-autonomy-20261104`。不更换其绑定，不执行续跑。

开始时直接通过 SQLite `mode=ro` / `query_only` 核实暂停事件 510、授权事件 359。
26 次 Provider 调用全部结算；无 pending、Worker、占用或 unconsumed SDK response。
Main 22 次、Reporter 4 次、321,492 tokens；数学、物理执行均为 0，剩余请求 6。
SDK session 的 running 是可恢复状态，不是实际运行中的请求；监督暂停不是 Main STOP。
540 个不可变 artifact 的 SHA-256 全部正确；当前 Store 的 133 个文件匹配既有封存清单。
完整 Study、SDK 文件及共享授权库已备份到工作区 `runs/semantic-evidence-private/`，
未提交私有数据库、授权、凭据或完整 wire。只读审计和恢复副本不产生新的执行授权。

## 真实请求归因（22 Main / 4 Reporter）

以下 Main 序号保留原顺序。原始输入、反馈、请求/响应绑定和哈希保存在私有审计 JSON，
原始 wire 仍由原 Store 所有。科研假设原文与未公开参数不随源码发布。

| Main | 信息需求与实际操作 | 归因 / 信息增量 |
|---|---|---|
| 1 | 参数分类 fields；provenance full | assembly/segment 等科研分类不是 `/parameters` 子键，首读拒绝；来源读取成功 |
| 2 | 参数 summary；结构研究能力目录 | 首次获得真实参数键；能力返回有界导航，非完整目录 |
| 3 | 委托调查结构/历史/机会；spans range | Reporter 1；获得腱路数据，有增量 |
| 4 | 参数 full；Reporter interpretations | 获得参数事实；解释过大转导航，尚非完整解释 |
| 5 | 委托解释/机制调查；action recall | Reporter 2；派生能力访问合法，但解释交付仍有缺口 |
| 6 | 保存报告的空 interpretations；重复结构能力目录 | 空解释确为原记录；相同导航未增加机制事实 |
| 7 | 委托配置/机制；机制目录 | Reporter 3 的 `/configuration` 科研分类 fields 不对应原结构树；目录不是新计算 |
| 8 | raw fields 读取 `/structure_research`；参数目录 | 错误视图：此路径仅存在于 mathematical_capabilities；显式拒绝 |
| 9 | 再读机制目录；finite_time_response | 前者重复；后者首次获得有限时域目标/操作/成本语义 |
| 10 | primitives；working_point_semantics | primitives 仍分页；工作点语义有真实增量 |
| 11 | action recall；机制目录 | 无新科学结果；同目录第三次读取 |
| 12 | 工作点；参数目录 | 工作点完全重复；参数目录尚未展开到具体对象 |
| 13 | 机制目录；Reporter 解释导航 | 相同目录第四次；报告来源不同，不能把整次请求当作重复 |
| 14 | 指定 primitives；compositions | 有选择性读取但大结果仍导航；组合操作列表新增 |
| 15 | 参数目录；机制目录 | 相同数据导航，未出现计算结果 |
| 16 | recall；指定 primitives | 默认结构事实/参数选择修复已到 wire；继续有界目录读取 |
| 17 | diagnose 提交假设 | research_intent 与动作不匹配，拒绝；不是取证/物理计算 |
| 18 | diagnose 修正为 DIAGNOSE | 下一轮自行修正，正式假设登记；没有 Worker |
| 19 | 结构能力多 fields；旧诊断详情 | 原目录仍过大；已加载实际 V4 Schema，不等于提交数学问题 |
| 20 | 委托机制、参数、冻结评价调查 | Reporter 4 的四项派生路径用 raw fields/range，机会视图也用 raw fields，未获得所求事实 |
| 21 | 空 interpretations；结构能力多 fields | 空记录和目录重复均未带来计算事实 |
| 22 | 同一拒绝诊断详情；参数目录 | 重复查询原反馈和目录；无新科学结果 |

Reporter 请求分别位于总 Provider 序号 4、7、10、24。全部只解释既有资料。
Reporter 1 的来源与历史区分有价值；Reporter 2/3/4 的来源缺口和空解释必须保留，
不能说“工具成功”就代表所需科学信息已交付。
30 次 evidence_read 有 20 种输入（fields 顺序归一化），10 次重复输入；其中 8 次反馈字节完全相同。
其余重复输入的反馈发生过分页修复或投影变化，不能仅按输入重复判作零增量。
Main 1/8 的错误反馈及纠错导航实际进入下一次 Main wire（反馈事件 24→请求 37、205→217）；
Main 17 的动作错误也实际进入下一次 wire（397→407），并在 Main 18 修正。
后续仍出现 raw/derived 混用，说明纠错消息不能替代统一查询契约。

## 原接口根因

`EvidenceQuery` 把 reference、pointer、view、fields 暴露为普通发现入口；
`evidence_query_schema()` 直接投影该底层类型。`read_tool_evidence()` 的大数据结果再转为路径目录。
上下文同时提供科研分类和 `/parameters` 等 raw 路径，模型须自行判断两者是否同构。
`read_evidence()` 已区分 working_set / mathematical_capabilities，但需要调用者保留 view。
Reporter 的 reads 使用同一底层类型，自动读取与 `_source_catalog()` 另行推导字段来源。
已有 navigation/corrected_query 是该缺口的补救；本轮不再新增特定字段别名纠错表。

## 契约设计与边界

新增薄类型 `EvidenceIntentQuery`：subject、topic、可选 group、selection、detail_level、continuation。
topic 是访问类别，不是另一份参数/机制注册表。group 和 selection 必须来自原 parameter_catalog、
mathematical_method_view、机制目录、冻结 TaskAdapter、已注册候选/结果或报告。
科学不等价的多个对象返回 choices，不替 Main 选择。

`evidence_read` 默认接受该语义输入；完整旧 `EvidenceQuery` 通过同一工具保留，
供显式原始复核、完整证书与正式 SELECT/STOP。原有授权和阅读门禁不变。

解析器只定位并投影既有事实：结构、参数、任务、机制、方法、数学结果、物理结果、对比、报告。
不运行数学、不建第二个 Store/缓存、不推断新假设。来源分为：

- 原始科学证据：不可变 EvidenceRef + 真正 raw pointer；权威资格由原 evidence_policy 决定。
- 派生视图：包含 Study、对象、主题和内容身份；不是原始 artifact 的虚构路径。
- Reporter 解释：绑定报告与真实原始来源；不是证书、计算结果或完整结果阅读信用。

分页返回完整语义查询，含程序生成、带内容身份的 continuation；
对象、视图或内容变化明确拒绝旧句柄。最新反馈交付一次，历史可压缩而不伪造新结果。

## 实现与实际接口

| 文件 / 函数 | 作用 |
|---|---|
| contracts: EvidenceIntentQuery / EvidenceContinuation / EvidenceReadQuery | 科研主题与原精确读取联合合同，禁止混合两类输入 |
| evidence_intent: resolve_evidence_intent | 只读编译；复用原注册参数、方法、TaskAdapter、result_card、报告对比和 working_set |
| core: read_tool_evidence | 语义输入接入；原 read_evidence / 证书 / 精确路径实现不变 |
| agent: evidence_query_schema | 实际 Provider Schema 同时校验两种合同；typed short refs 继续走原适配器 |
| research_context: agent_decision_brief / information_flow_brief | L0 仅显示有效参数组与计数，完整表在语义 L1；原事实与假设分离 |
| object_choices: main_projection | 保留可执行 continuation 的完整身份，避免普通显示脱敏删除分页字段 |
| reporter: investigate / _source_catalog / _wire | question + subject/focus，复用编译器；从保存的真实 sources 建目录，避免把派生路径当 raw 引用 |
| session_handoff: selected_evidence_facts / feedback_delivery | 旧反馈保留语义恢复入口、对象和分页身份；最新 exact/preserve_once 路径不改 |
| test_request_boundary_handoff: provision / 旧 Schema 恢复用例 | 旧夹具补录明确的离线数学 scope；从真实旧 EvidenceQuery 工具 Schema 恢复，再刷新新联合 Schema |

实际 Main 输入 Schema 由旧的 `EvidenceQuery(reference, view, pointer, fields, start, count)`
改为 `EvidenceIntentQuery | EvidenceQuery`。顶层平铺 properties 供原 short-ref 适配器使用，
原 provider_schema 将联合约束放入其已有 conditional 适配；Host 的规范类型校验仍拒绝混合输入。
Reporter 的 `reads` 同样采用联合合同；references 可省略，subject 可指定当前候选或已有结果。
没有增加顶层工具、科学状态机或注册表。

```json
{"subject":"current_candidate","topic":"structure"}
{"subject":"current_candidate","topic":"structure_parameters"}
{"subject":"current_candidate","topic":"mechanism_capabilities","group":"primitives","selection":["constraint_length_residual"]}
{"subject":"current_candidate","topic":"mathematical_methods","selection":["mechanism_structure_v1"],"detail_level":"targeted"}
{"subject":"current_task","topic":"task"}
{"subject":"registered_results","topic":"comparison","selection":["evaluation_1","evaluation_2"]}
```

group/selection 示例必须先由本 Study 返回；不存在的 material 等名称返回真实参数组选项，
不会别名映射。比较必须显式选两个不同的已注册结果，复用原比较资格/限制。
注册结果投影的 `view_kind=raw_scientific_projection`，能力/任务视图是 derived_research_view，
比较是 derived_research_comparison，解释是 reporter_interpretation。
所有普通查询 `formal_read_credit=false`、`scientific_result_created=false`。
精确原始来源位于 sources，绝不把派生 facts 路径包装成原始字段。

分页返回整个 next_query（固定对象、topic/group/selection/detail_level、Study/query/content 身份与 offset）。
新候选成为 current 不改变旧页所属对象；依赖投影内容变化则拒绝旧页。
没有永久查询缓存，继续使用原 Store 的短期 read_snapshot 和原不可变查询缓存。

## 历史离线复现

`python -m tests.research.semantic_evidence_history ORIGINAL_STUDY OUTPUT` 可只读重现归因的信息需求。
原连接强制 readonly，Provider/Worker/积分入口显式禁止；验证全部来源可读及前后 133 个文件哈希相同。
已成功覆盖原 22 Main 的信息需求（17/18 为 diagnose，不冒充查询），以及四次 Reporter 调查的问题类别。
原任务确无数学/物理新结果，查询如实返回空集；没有补造一个计算结果。
原被动目录中的 constraint_length_residual 确实由注册 primitive 查询取得。
四次原 Reporter wire 的 selected_reads 数量为 3/4/3/5，其中 unavailable 为 0/0/1/5；
第四次调查的五项读取全部失败，不能以外层工具 success 认定信息已交付。
完整遍历页数：结构 2、参数 6、机制概况 3、方法 8、任务 3、报告 8、历史 1、机会 3。
这些页数证明可导航性，不宣称每个问题需要遍历全部目录或一定节省 tokens。

## 验证与剩余边界

**40 项不同的定向测试通过：新增语义/SDK 测试 13 项，既有精确证据及恢复回归 27 项。**
详见 [验证摘要](semantic-evidence-validation/summary.json)、
[实际 Provider Schema 对照](semantic-evidence-validation/actual-provider-schemas.json)、
[历史回归](semantic-evidence-validation/history-regression.json) 与同目录保留的完整测试日志。

- M1：结构、合法参数组、方法前提、已有结果、分页与下一轮实际 SDK wire；不手写 JSON Pointer。
- 冷启动：尚无候选时，current_task 直接绑定本 Study 不可变 snapshot 的 `/input/task`；实际 SDK 可读，未先生成候选。该 raw 位置仅为来源，普通查询不需要填写。
- 被动 v2：固定 payout、无主动控制、注册单侧约束 primitive、连续参数、静态/有限时域区别、V4 Schema 准备与实际 SDK wire；无计算。
- M5：原工具轴任务、位置与工具轴约束、合法 Direct / 不支持的 task_capability 明确区分；实际 SDK wire 保留工具轴语义。
- Reporter：Main 通过实际 SDK 以 question + subject/focus 调查已保存的合成测试结果；Mock Reporter 使用真实 raw source_catalog，解释完整进入下一轮 Main。解释不具备科学引用/证书资格。
- 负例：未知主题/参数组、外来对象、混合语义/raw 输入、错 Study/错主题页、真实投影内容变化造成的过期页；新 current 不改变旧页绑定。
- 原始证据：完整 acceptance_certificate 交付后才允许 SELECT；失败/历史/错误 fidelity 不授信；完整 STOP 索引、所有工况、精确读取及旧 Schema SDK 恢复保持。
- 保存回执恢复、未知 Reporter 请求的费用/幂等/SDK 保护及未配对反馈拒绝继续通过。测试中的 RequestBoundaryHandoff 日志是预期的安全边界控制流。

初次兼容批次 27 项中 23 通过、4 项因测试环境缺少 matlab.engine 未进入测试主体。
改用已有 `.f3-prestudy-env` 后 1 项通过，3 项暴露旧夹具未登记原门禁要求的数学 scope；
补齐明确的离线夹具授权、更新实际旧 Schema 注入位置后 3 项均通过。
原门禁没有被关闭；保留首次失败及定向补测日志，没有隐藏为全程首次全绿。
仅补入任务目录中缺少的固定 tokenizers 0.22.2，复用已安装的 Strands 1.59.0 / Harness 0.2.0；
没有安装/启动 MATLAB 科学计算。

全部 Provider 采用离线 Mock；没有真实 Main/Reporter Provider、正式数学 Worker 或新物理积分。
最终再次检查原 540 个 artifact、133 个 Store/SDK 文件及共享授权库哈希一致，原六次请求不变。

删除了 Reporter 默认按卡片猜 raw 子字段的自动读取逻辑，改用公共语义编译。
保留已保存的精确 reads、旧导航纠错与原源引用资格；未证明无用的兼容规则不删除。
新 raw review 仍完全受原 read_evidence 保护，语义查询不自动取得完整证书或 SELECT/STOP 阅读信用。

下一次真实验证仅可在用户确认后：只读复核原 Store、费用、授权及 SDK 文件，
以原版本化授权 / implementation_binding 流程明确绑定新提交，保留旧身份和全部费用；
先 restore_only，核验旧快照后再由原 before_model 刷新 Schema。授权范围只增加本次接口实现身份，
原任务、候选、评价器、证据等级及剩余预算不变。本轮不实际授权、绑定或发送。

**已证明的是取证接口和离线交接；尚未证明真实 Main 能自主提交数学研究，
也未证明数学结果能指导结构修改。三者不能互相替代。**
