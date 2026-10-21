# S12.7.4 外部传输授权范围

2026-10-21；本文件仅供独立授权审阅，不构成用户授权。旧 S12.5/S12.6 授权不适用。

## A：冻结决策对照

[逐请求审计](../../evidence/s127_4_decision/scope.json)核对原清单身份
`330d4b06ec479abcf97a08996430ed601de6cf751bd6c4cd1eee609571929c6a`，
六对共最多 12 次 POST 到 `https://api.deepseek.com/chat/completions`，
模型 `deepseek-flash`，thinking enabled，reasoning_effort high，非流式，
每次最多 8192 输出 tokens，无自动重试，不替换模型，不增加请求。

发送内容仅为原清单中 hash 校验的 system/user 请求：冻结项目任务、结构/控制域、
候选与科学结果摘要/引用、预算及五个工具 Schema。每份只有两条消息，
不含旧 assistant/tool 历史，不读取无关文件；API 密钥只作认证请求头。
离线检查未发现密钥字段、凭证文件内容或无关用户路径。

拦截一切科学 dispatch、MuJoCo、NMPC、数学 worker、PPO 和真实搜索。
证据可本地读取；提案只作无副作用契约/引用检查，完整科学准入标为 `not_tested`。
冻结设计每组只有一次请求，因此新读取详情不能再次交付给模型，不能测量自适应读取净成本。
第六对单列为独立会话条件，不纳入纯压缩因果比较。

原请求、响应、完整 reasoning 和 Store 留在被忽略的 `runs/`，不上传 GitHub。
普通 Git push 仅包括代码、派生统计、hash 和文档。

[DeepSeek 官方思考模式](https://api-docs.deepseek.com/guides/thinking_mode/)及
[Chat Completions](https://api-docs.deepseek.com/api/create-chat-completion/)
于本日核对上述格式；账户侧可用性只能在独立授权后的实际请求中确认。

授权前 A 状态为 `not_run`，所有真实 token、质量与缓存指标均未知。

## B：独立 SDK 接续

B 不包含在 A 的 12 次额度中；待独立新 Study、最多 6 次请求、低成本工具边界、
数据范围和真实 SDK 持久化验证驱动冻结后单独申请。不得复用 A 或历史授权。

未获授权仍完成所有离线恢复、控制分析与可执行工程验证。
