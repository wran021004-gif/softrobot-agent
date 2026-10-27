# P2-B 截断与上下文审计

原冻结版本 `661ee842c2496d60e5a3ceffa3a4ba4e4ce7ca07`。Store 独立核验：请求 `r3-request-2df3e7c839024d128e0a27537e65f93c` 的保存请求 artifact `8bbeaf0005dc5db9297c9b95d69bd92cc024df8b2b3ba505348e4fc2619555cd` 与调用行 hash 一致；已结算收据 `3ced815258eb4208ba6e77f41584791c` 计 1 Provider 请求；HTTP 200 原响应 artifact `7d10db25a566a512afc4054b97dabadb60c955b3a0d36f5bdf414915b6c14dda` 的 finish reason 为 length，usage input 52,386、output 32,768（reasoning 31,365）。该请求实际冻结 `max_tokens=32768`、`thinking.enabled`、`reasoning_effort=high`；请求上限和输出一致，但无法仅据此证明增加上限可解决模型决策问题。

保留的原 SDK 快照 7 条消息格式化后与第四请求去掉最新 L0 包的历史前缀逐项一致；4 个之前的工具请求及结果与 Store 原始反馈一致，截断请求之后没有执行工具事件。候选 artifact `ef2fbc71dc15f1e4fee75687e462e46f4d3d166702693be33d432f0969441a02` 保留。没有未知 Provider 请求或活跃科学 Worker；第四响应仍未消费，研究未 STOP。

第四请求分字段的 UTF-8 紧凑 JSON 测量：tools 47,337 bytes；system message 838 bytes；L0 尾消息 52,934 bytes；三轮历史 reasoning 内容合计 70,152 bytes；四条工具结果消息合计 10,334 bytes。各分类口径为所测字段/消息，不应简单相加作为 Provider token 数。实际 Provider 请求字节 196,007，输入 tokens 52,386。第四响应花费 189.344 s；旧会话完整保留 DeepSeek thinking-mode 工具历史的 reasoning_content。原 Handoff 没有启用实时请求反馈边界，且未消费响应本就不能通过正常安全边界；不是普通已完成轮次。模型实际因何长推理未知。

DeepSeek 官方文档说明 thinking 模式含 tools 的后续请求需传回全部之前轮次 reasoning_content；支持 low/high/max effort，但低 effort 对本任务的实际效果尚未验证。冻结 P2-B 不改变模型参数。新会话可在合法边界不复制旧历史，但权威证据仍在原 Store，实际效果须单独测试。

更新：2026-10-28 用户授权的狭窄恢复已完成，实际恢复和一次真实后续请求见 `p2_b_recovery_result_zh.md`。这段文件前面的四次请求审计保留为恢复前事实，不能据此推断原响应仍未处置。
