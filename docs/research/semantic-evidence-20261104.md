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
Main 1/8 的错误反馈及纠错导航进入后续 SDK 交接；Main 17 的动作错误在 Main 18 实际修正。
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

## 验证与交付

待实现后补充实际 Schema、SDK Mock wire、M1/被动 v2/M5、Reporter、精确证据与恢复回归。
本轮全部 Provider 采用离线 Mock；不执行正式 Worker 或新物理积分。
接口可用、真实 Main 自主提交数学、数学指导结构修改是三项独立结论。
