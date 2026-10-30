# P6.3-G0：有限正文交付与正式验收视图

基线为 `d3abff14c6a56e6e9677ef17d7280a60e72807f1`，独立分支 `codex/p6-3g-autonomous-research`。本阶段只进行原 F2 证据只读检查与离线 Mock 验证，没有真实 Provider、数学或物理 Worker。

## 版本和交付边界

新 Study 在原 `research_decisions` 中显式启用 `evidence_read_policy={"version":"bounded_scientific_evidence_v1"}`，并沿用 `research_information_flow_v1`。未启用的旧 Study 保留原 root-full 和 SELECT 阅读合同，旧 wire schema 不提供新视图；F2 Store 没有被改写或重新解释。

`core.read_tool_evidence` 使用既有 Provider 请求容量的 **1/32** 作为单条新证据正文额度；本次 1 MiB 网关对应 32,768 bytes。没有提高网关上限。小型 root-full 保持原始正文；大读取返回 `raw_result_not_delivered`、原引用、既有固定事实或其当前决策视图位置，以及原 `fields`、`range`、JSON Pointer 查询。完整数值和数组仍以原身份保存在原 Store。内部 `read_evidence` 原值读取不变。

限制在工具输出处已经明确，不把一个被限制的读取标成完整交付。原 read coverage 会比较实际发送的原反馈文本与原数据；导航或摘要不等于完整结果，也不产生 SELECT 资格。没有大文件平台、新 Store、读黑名单或新增顶层工具。

## 正式验收视图

新 `evidence_read(view="acceptance_certificate")` 必须读取整个视图，不接受局部字段冒充完整证书。它投影现有 `research.task_acceptance` 合同，包含：

- 完整原结果引用、当前及原所有者、候选和配置引用；
- 实际控制 source、既有 solution identity、backend/model/discretization/profile；
- 原冻结及有效任务身份、评价器、工况及共同结构身份；
- 执行完整性、有效性、实际通过/失败状态、全部原验收 components、metrics、阈值和时域；
- 原 sampled settling / tracking / tool-axis 覆盖信息；
- 原评价、profile、simulation、trajectory 引用与独立验证/历史范围限制。

所有数值来自已保存的原评价和 profile。校验复用 `_source_issue`、`_outcome_issue`、`result_view` 和原 `assemble_acceptance`：对封存评价、profile、采样时刻重新组装同一个验收合同并核对，不启动 evaluator、求解或积分，也不复制一份新评价器。不支持的合同（例如缺少该完整物理验收结构的数学结果或其他评价类型）保持原严格全量读取路径；视图本身若超出正文额度，会明确返回未交付，不能偷偷截断后仍认作完整证据。

`evaluation_reads` 仍只是工具端 marker。`read_coverage.formal_acceptance_view` 只有在**配对成功的工具反馈确实进入后续真实 Provider 请求，且与当前完整确定性视图一致**时才成立；该视图不冒充 `full_artifact`。原 SELECT/confirm 接受该阅读事实或原精确全量结果阅读，其余新鲜度、独立性、成功、来源、候选/模型、保真度、多工况和确认规则保持。

因此程序内部生成视图、Store 存有结果、返回本地 marker、SDK 预览或 Reporter 阅读都不等于 Main 正式收到证据。多工况仍需逐项完整阅读且通过原 `joint_assessment`，只交付一个工况不能 SELECT。

## 实际交接修复

原 SDK 在成功结果后保留当前会话并可能 offload 工具正文，导致完整精简证书只剩预览。新版本复用原 `feedback_delivery` 与 Current Research Packet 的精确反馈位置，只补交**Main 已显式请求、尚无实际 wire 确认、且已受单条额度约束的验收视图**。确认后不再补交；不会恢复被阻止的原始大数组。没有修改 SDK、Provider 或 Gateway。

正向 wire 测试还确认：`success_gate` 已要求 SELECT 时，原展示路径仍可能沿用探索 Schema，随后被原发送准入拒绝。新版本让已有保护状态参与原 Schema 收尾判断，并在仅有 SELECT 的目录中加载合法 SELECT Schema；只加载工具，不代 Main 提交 Plan。此修复亦按新版本启用，未放宽任何科学准入。

STOP 保留完整新结果引用索引和逐项结论要求，没有要求读取全部原始轨迹。G0 的实际 Mock STOP 只读取索引、引用原新数学结果并完成关闭，没有任何 root-full 读取。

## 实验语义和搜索能力

最新数学事实额外保留原输入 source 与实际优化控制的来源查询，明确控制重优化和独立检验初始序列是不同实验；Main 原 Plan 仍单独持有假设。验收视图的控制 source 则指向独立物理评价实际使用的序列。没有假设管理状态机或程序自动判定假设成败。

已有 `research_plan(control_search)` 使用原 `LocalControlSearchSettings`，可选择最多 4 个 knot、100 次迭代及合法的回调预算；其回调是独立物理 Replay，费用区别于 Native 数学 rollout。C2 ScientificQuestion full_task 仍为两个端点、默认 16 次迭代。方法详情准确说明区别，`focus_metric` 不改变完整任务目标。没有扩展 ScientificQuestion、替换算法或改数学内核。

## 离线验收

23 项直接相关测试全部通过，耗时 **188.428 s**；`git diff --check` 通过。测试范围为：

- 新 `test_p63g_bounded_evidence.py` 的五项实际 SDK/Mock wire 测试；
- C0 原能力目录、C1 发现接口；
- C2 原 T1 编译计费和 C3 三节点 handoff；
- F1 固定结果/Reporter 交付及索引进度回归。

真实 F2 数学结果 `c8972bd16a75b3977e9779147587fbeb7c2573c2015c025e3de9881814ae044f`（原正文约 1,013,814 bytes）仅作为独立离线 fixture 的只读来源，未成为 G1 证据。工具输出明确未交付原始正文，下一次实际格式化 Mock HTTP 请求为 **78,428 bytes**（原始请求前为 50,267 bytes），小于 1,048,576。固定事实和保存 Reporter 解释正常进入 Main；原 F2 DB mtime 不变，旧读取仍返回完全相同原值。

正向 fixture 使用原生成、独立 Replay 调度及原 evaluator/acceptance 组装，只有底层运动输出被明确标记的完美合成运动替代。实际 wire 收到证书后，Main 的 Mock SELECT 成功；这些数字不是科学成果。失败、无效、历史和错误保真度在证书查询后仍拒绝；两个原工况必须均交付且通过，缺一即拒绝。未对九项历史 Trace 重跑科学计算。

## G1 冻结设计和用户后续指示

新配置 `study_p63g1_m3_autonomous_sol.json` 保留原 M3 task、FamilySpace、物理模型、控制合同和协议，候选池为空，由 Main 自主生成/搜索。Main/Reporter 沿用 `gpt-5.6-sol / none`，Provider 总上限 **80**，其中 4 次为原保护收尾预留；数学、物理等使用充足合法整数和原技术限制。该 80 次来自本次 G0/G1 用户请求的新授权，不借用旧 F2 的 20 次窗口。

用户随后明确允许简短历史 trace（包括 M3）作为 Knowledge，与通用经验一起开放。因此该后续指示覆盖附件中最初关闭 M3 trace 的要求：现有 Knowledge 开启，`procedure` 和 `success_case` 均允许，冻结目录有 25 个条目并包含 M3。不会预载、导入或复制历史完整结构、控制轨迹和结果 Store。G1 报告会区分 Main 实际检索的历史知识、程序计算和当前独立证据；不声称完全盲发现。

通过 G0 后直接开展同一个新 G1 Study，约 12、30、55 次只读监督，若无真实故障继续至正式成功、Main 科学 STOP 或本窗口上限。不动态更换模型、提示或替 Main 生成研究 Plan，不自动开第二个 Study。
