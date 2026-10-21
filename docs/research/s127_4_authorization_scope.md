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

B 不包含在 A 的 12 次额度中。[B 冻结范围](../../evidence/s127_4_handoff/scope.json)
和 `configs/research/study_s127_4_handoff.json` 定义独立新 Study，最多 6 次
同一 endpoint/model 的请求，每次最多 8192 输出 tokens，零重试。
最多 40 次公共工具操作，数学/NMPC/PPO 为零；共享最多 2 次小型固定输入物理启动。
Agent 可选结构生成、显式控制初始化、固定输入评价、证据读取或 STOP，
每个 SDK invocation 最多执行一项科研动作；达到验证目标即结束，不消费剩余额度。

传输仅限该新 Study 的任务/设计域、自产候选/控制、预算和结果，
`research_plan`/`evidence_read` Schema，以及本 invocation 必需的完整推理和工具回合。
新会话只装入权威交接工作集，不拷贝旧 tool-use/tool-result 历史。
不导入 S12.6 数据或授权，不发送无关文件和凭证内容，不上传原始 SDK/Store/对话。

离线驱动已使用真实 Strands Harness、SDK 文件存储、独立重开、原子指针提交，
并通过正式工具实际生成候选和初始化控制；HTTP 和决策是明确的合成 fixture，
不能作为真实 DeepSeek 科研决策证据。B 的 live 两项及生产准入仍为 false。
生产 `--session-handoff` 门禁保持原样，未修改任何生产批准标志。

未获授权仍完成所有离线恢复、控制分析与可执行工程验证。
