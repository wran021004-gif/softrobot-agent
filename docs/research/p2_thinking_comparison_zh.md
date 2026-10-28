# P2 Thinking 配对对照：真实只读结果

## 2026-10-28：用户批准后完成一次配对

用户明确批准在原 P2-B 账本预留并计入一次对照，并保留两次保护额度。以原第五次真实请求为 Thinking-On 基线，使用同一 Store 中的新子会话 `p2b-thinking-off-shared-ledger-20261028` 发出一次 Thinking-Off 请求 `r3-request-c069e48978114d3fb921bcbaad269e96`。子会话限额是 1 Provider、0 public 工具、0 backend、0 worker；原项目与父会话均计入该请求。预留事务同时检查源状态未变、项目原用量 5/8、没有未确认执行及剩余保护额度为 2。未自动重试。源 Study 的状态摘要在对照前后相同，旧请求、响应、候选及控制源未改写。

请求使用同一模型、完整消息、原决策包、工具及 Schema、输出上限；仅将 `thinking.type` 改为 `disabled`、移除 `reasoning_effort`。两次均为非流式，未显式指定 tool_choice，按原配置使用 auto；原包发生于候选已生成、**控制源数为 0** 的时点。原请求 artifact `b0c3cd5a679ae21b6056f7e56bd22cb91bfe8985f5905a521935e977d8b067e9`，对照请求 artifact `0906b2ae49ff6ade0ce791f17d6bbe27c82d89fc1a6f78c8ec4dca494e7de618`，新响应原始字节 artifact `00168915f4c943884648531be9d53ce9081cdd4b5249d667ae5a7f4f77e2f53e`；原始内容、usage、收据和验证摘要保存在原账本。实现提交 `fdbf2acc8`；源 Study 原冻结实现仍为 `fc4d1b490`，本对照不迁移研究执行语义。

| 实测指标 | Thinking-On，高 | Thinking-Off |
| --- | ---: | ---: |
| HTTP / finish reason | 200 / tool_calls | 200 / tool_calls |
| 输入 tokens | 28,434 | 28,414 |
| 输出 tokens | 26,384 | 256 |
| reasoning tokens | 24,013 | Provider 未报告，未知 |
| 总 tokens | 54,818 | 28,670 |
| Provider 墙钟秒 | 149.765 | 1.782 |
| 请求体字节 | 104,917 | 104,892 |
| 返回截断 | 否 | 否 |

这是一个样本：Off 的输出 tokens 少约 99.0%，总 tokens 少约 47.7%，墙钟少约 98.8%；网络条件、缓存和采样波动未控制，不能推广成总体效果。输入 token 的 20 个差异来自 Provider 实际计数，不把相同消息视为相同 token 收费。金额未由响应报告，保持未知。

On 提交 `research_plan.initialize_control`，引用当时已存在的 V3 候选 `ef2fbc71dc15f1e4fee75687e462e46f4d3d166702693be33d432f0969441a02`，给出 30 行张力和可检验假设；原历史中该调用已实际生成绑定的控制源，任务表现仍未测。Off 提交两个 `evidence_read`：读取 generation 反馈 `fa5ff23bb0d66ddb1ecbd16b20b1863fe299e0557e8ff6b3dc2d544cbec90587` 的 `full /result`，以及候选 `ef2f...` 的 `working_set /candidate_index/0`。两项均通过发送时 Schema、Pydantic 和原决策包可见引用检查；第一项的原 artifact 存在 `/result`，第二项与当时包中声明的候选索引及候选数一致。没有分发这两项读取，动态视图、保护模式和完整工具准入未实际验证，不能称作已执行成功。原 On 提案也通过同口径只读校验；其真实历史后端执行结果是额外证据，并非 Off 的执行结果。

Off 选择先核对反馈和候选，未虚称任务通过，也未再次生成结构；但没有给出具体控制、数学或诊断行动、可检验的行动假设，也没有展示对 Native J 或受限驱动力的理解。历史决策包说明后续读取会挤占探索决策额度；两次读取还需要后续模型轮次才能决定科研行动，本次对照未测这个后续。On 在该样本直接提出并实际形成了合法控制源，因此具有更明确的即时科研进展；其手工推测的张力和到达假设尚无物理验证。Off 在此样本大幅降低成本，但仅证明输出了两个可解析的读取提案，暂不足以推荐它直接替代真实反馈研究中的决策模式。两者都不能据此证明结构改善或任务通过。

当前原项目及父会话均为 **6/8 Provider**，剩余 **2 次全部受保护**，无可用探索 Provider；子会话只消费 1 Provider，未消费 public、数学、backend、worker 或回放。整个 P2 累计 6 Provider、9 public、2 数学条目、1 次 T1、0 次独立回放、4.9074117 数值秒；六次 Provider 共 192,872 input、80,876 output、273,748 total tokens，其中前五次已报告 reasoning 小计 72,925，Off 未报告，故全部 reasoning 总量未知。后续 T1—反馈—修订仍需另获预算和正式来源/实现准入；P3 保持 `PENDING_EXPLICIT_P3_APPROVAL`。

## 历史：批准前的离线准备与阻断

## 已核验的 Thinking-On 基线

原 Study `p2-v3-positive-high-agent-remaining-20261028` 中的真实第五次请求 `r3-request-fcacd8a931d847aca84b6dd23b6c2772` 已核对原始请求、HTTP 收据、响应及发送前的决策包：模型 `deepseek-flash`；`thinking.type=enabled`、`reasoning_effort=high`、`max_tokens=32768`、非流式，未显式指定 `tool_choice`（现有边界按 `auto` 处理）。消息只有 system/user，历史 reasoning 和 assistant 工具字段均为零；第四次截断响应的原始 reasoning 内容及其 tool call ID 不在拟配对请求中。该请求的工具定义和 L0 与保存的原始 Store 证据一致。原请求 artifact `b0c3cd5a679ae21b6056f7e56bd22cb91bfe8985f5905a521935e977d8b067e9`，响应 artifact `40a9bab270ca9df01de03e766279c3d086d8f172bdb0847e4269723992fd19a4`。

注意：第五次请求的决策时 L0 有一个合法 V3 候选、**零控制源**；其后实际返回 `initialize_control` 并生成了控制源。当前 Store 的状态已有控制源，不能将当前状态误当成历史决策时状态。原响应为 `tool_calls`，28,434 input / 26,384 output / 24,013 reasoning / 54,818 total tokens，149.765 s。原始 action 通过真实后端并创建了合法绑定的控制初始化；真实物理结果和任务验收未测。

## Non-thinking 准备与停止原因

`matched_thinking_decision_v1` 离线配对器对原始请求作深拷贝，仅将 thinking 改为 `disabled` 并移除 `reasoning_effort`；模型、完整消息、工具定义、原 L0、max_tokens 和原有工具选择语义保持相同。拟发送的冻结 artifact 为 `0906b2ae49ff6ade0ce791f17d6bbe27c82d89fc1a6f78c8ec4dca494e7de618`，原请求身份为 `b0c3cd5a679ae21b6056f7e56bd22cb91bfe8985f5905a521935e977d8b067e9`，两者存放在本地只读 context archive `runs/p2b-thinking-comparison-offline-20261028/context-archive`，不含 API key，不是科研 Study 和预算授权。配对器只校验 JSON Schema、现有 Pydantic 契约和决策包中可见的引用，永不分发科学工具；完整科学准入仍未检查。

原 P2-B 剩余 3 次 Provider，其中 2 次受保护；整轮 P2 实际已用 5，数学上 `5 + 1 + 2 = 8`。然而现有 Store 的 `remaining` 和 `reserve` 都只覆盖各自独立项目。若在独立 Provider-only Store 扣 1 次，原 P2-B Store 仍会显示 3 次可用；独立 Store 不能原子占用或保护它，未来沿旧账本继续有将累计总额推到 9 的风险。题目同时禁止修改原 P2-B Store，现有授权账本无法证明跨两个 Store 的永久累计约束，因此离线预算门禁明确返回 `INDEPENDENT_STORE_HAS_NO_SHARED_ATOMIC_P2_BUDGET_AUTHORITY`，`admitted=false`。没有发送 Non-thinking 请求，没有生成 Provider 费用、工具动作或科学 Worker；原 P2-B 的 Store、候选、账本未变。

要真实发送一次对照，需先提供能够在不改写原 P2-B Store 的前提下原子保护源 Study 两次保留额度、并对原 Study 后续发送强制计入对照费用的共享预算授权；或者由用户单独授权对原账本进行正式计数处理并允许重新审查当前“不可修改原 Store”约束。还需对同一作用域维持一个真实 Provider 收据、无自动重试及失败费用。不能用额外独立 Store 配额充当已获授权的总预算。

[DeepSeek 官方 Thinking 模式文档](https://api-docs.deepseek.com/guides/thinking_mode/)说明 `thinking.type=disabled` 为受支持开关；[Chat Completions 参数文档](https://api-docs.deepseek.com/api/create-chat-completion/)说明工具请求与输出上限协议。文档支持并不代表本次真实请求被服务端接受：Non-thinking 的 token、延迟、finish reason、工具动作和科研质量全部未知。无法判断哪种模式更合法或更有研究价值，也不能推荐 Non-thinking 进入真实科研。

控制初始化工具提示已解释：可以省略输入沿用候选预张力，也可以给一行有界肌腱张力，由工具展开到整个零阶保持窗口；有假设或证据支持时仍可提供完整序列，Native 控制优化可进一步计算序列。这不会改变原第五次请求或其实际结果。

现有真实 P2-A 控制初始化可核对该能力：来源 `fd837e66e7c24017818a7a14fae14f13c3c310ecd48b12dcdbbf3b2752121f6d` 由一行 6 通道 0.2 N 输入扩展成 30 个相同的区间值和 31 个 0–0.6 s 时间点。此处仅读取原 Store，没有重新运行控制生成或 Native 计算；它证明紧凑输入扩展，不证明该控制通过任务。
