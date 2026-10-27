# P2 Thinking 配对对照：只读准备与预算阻断

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
