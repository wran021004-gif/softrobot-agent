# 原 Study 官方 API 接续（2026-11-10）

用户明确要求“使用官方API接续”。原 Gateway 第 39 次请求因 `subscription_sharing_usage_limit_exceeded` 返回 HTTP 429；该失败继续计入原 80 次共享总预算，接续前为已用 39、剩余 41。

复用既有 `transition_transport`、`core.bind`、身份绑定授权、SDK restore 与原后台 launcher，只切换至 `https://api.openai.com/v1` 和独立本地凭据引用。保留 gpt-5.6-sol、Main/Reporter medium、原 Study、Store、SDK session、所有候选、Plan、科学要求和历史成本。没有额外推理探测，没有重置预算。本次不 Push。

官方账号只读 `GET /v1/models` 返回 HTTP 200，确认精确模型可用。官方适配器已有 medium 加工具调用的 Responses 转换；依据 [OpenAI Responses 迁移文档](https://developers.openai.com/api/docs/guides/migrate-to-responses) 使用现有 stateless reasoning 处理，不新增 API 框架。

`official_api.py before` 保存接续前不变量，提交后 `apply` 使用既有迁移与 admission 入口，逐项核对科学配置、profile、候选/结果、账本和 SDK session，并在零次推理发送下恢复 SDK。正式恢复的真实 HTTP 收据随后追加；绑定成功本身不代表科研完成或验收通过。

接续暴露了通用 admission 的传输识别遗漏：它将实际 endpoint 固定为 `/chat/completions`，因此无法复用已完成的官方 `/responses` 交接证明。本次保留原全部模型、HTTP 200、请求哈希、SDK 独立 restore、工具 ID 和 exact feedback 核验，新增对既有 Responses 协议的验证：实际与 SDK endpoint、原始 upstream 模型和推理设置、原始响应重新转换后的 SDK view 必须完全一致。两项定向回归通过，覆盖合法 Responses/旧 Chat 路径及错误 endpoint、模型、推理、派生消息拒绝；原 PHS-2D 官方历史交接也只读核验为 ready。没有发起验证推理或科学积分。

## 真实恢复核验

执行绑定为 `96a5269fec32b9c1a55b354a7c44fec38eec2613`。[绑定收据](official-api-continuation-bound.json) 确认零次推理发送下，科学配置、profile、7 个候选、7 份 Plan、9 个分析结果、原账本及 SDK session 完全保留。原 base_commit 仍为 `4245e5a4501e6ee915877ab0b80892e4a799bf7a`。

随后通过原 launcher 后台恢复。首个真实官方请求 `r3-request-43d0496600384bab8c0315f39d596178` 发往 `/v1/responses`，HTTP 200、`tool_calls`，SDK wire 590,506 bytes、实际 upstream wire 590,637 bytes。Main 随后完成一次工具调用并发送下一次正式研究请求；[恢复快照](official-api-continuation-after.json) 时为共享额度已用 41/80、剩余 39，其中下一请求仍在途。该快照不是最终成本或最终研究结论。

原旧 Study 状态和账本再次核对未变。当前没有新的正式 physical Replay、任务验收通过或 SELECT。后台进程及原 Store 继续维护后续证据和成本；本次未 Push。
