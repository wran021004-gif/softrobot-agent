# 三个 Provider 的明确选择

工作目录：`D:\softrobot-agent\.worktrees\research-harness-v2`。
三个连接独立保存。用户每次指定使用哪个，操作者在准备新测试或 Study 时选择对应 runtime；没有自动回退。
既有 Study 继续使用其冻结 Provider，不通过修改文件偷换已冻结的模型或计费账号。

| 用户指定 | runtime 文件 | 凭据位置 | 当前状态 |
|---|---|---|---|
| DeepSeek API | configs/research/runtime_harness_v2.json | ~/.codex/.env 中的 DEEPSEEK_API_KEY | 真实工具闭环及自主生成已通过 |
| ChatGPT Gateway | configs/research/runtime_p5_luna_none.json | ~/.softrobot-agent/chatgpt-api.json；OAuth 由原 Gateway 管理 | gpt-5.6-luna none 真实工具闭环及自主生成已通过 |
| 官方 OpenAI API | configs/research/runtime_openai_api.json | ~/.softrobot-agent/openai-api.json | 130 个模型可见；gpt-5.4-mini 的真实推理和工具闭环通过，科研测试未达 D4 |

官方 API 密钥填写文件：

`C:\Users\gugugaga\.softrobot-agent\openai-api.json`

```json
{
  "base_url": "https://api.openai.com/v1",
  "api_key": ""
}
```

将完整 API Key 填入 api_key 的引号中并保存。文件在 Git 仓库外，不需要把 Key 发到聊天中，
也不把它写入 runtime、Study、Store 或提交。已有 Gateway 凭据不会被覆盖。

新增的 openai_api 直接访问官方 Chat Completions，复用现有 OpenAI SDK、Harness、原生工具与共享计数账本；
不经过本地 Gateway，不借用其 OAuth、模型目录或计费授权。OPENAI_API_KEY/DeepSeek 的其他环境变量不会覆盖此选定文件。
按用户后续指定，默认模型是 gpt-5.4-mini、reasoning_effort=none、store=false；该型号已在真实目录中确认可见。
直连曾在建立连接阶段报 ConnectError；当前 runtime 显式设置 proxy_url=http://127.0.0.1:7890，目录验证已成功。
模型目录及实际调用均使用所选代理，无自动直连/代理切换；未设置代理的旧冻结配置继续保持原序列化和行为。
如设置输出上限，官方 API 映射为 max_completion_tokens。错误、未知结果与原始响应恢复沿用原边界，SDK/transport 重试为零。

用户提供的 25 万/250 万每日共享额度按用户来源记录，接口未独立返回额度、有效期或剩余额度；目录可见不等于赠送额度适用。
完整 130 个模型名称及授权边界见 [官方 API 目录审计](openai_api_models.json)，不自动调用目录里的其他模型。
如用户指定不同模型，应先确认其账号准入和端点/工具支持，再冻结该次配置。
此入口当前使用 Chat Completions，不将仅支持 Responses 工具的型号声称为已兼容。

后续可以直接说“这次用 DeepSeek”“这次用 ChatGPT Gateway”或“这次用官方 OpenAI API”，并指定模型及预算。
目录核验与用户授权的 mini 测试结果见 [mini 实测报告](p5_openai_mini_acceptance.md)，不把其他目录型号声称为已逐一实测。
最初配置阶段只运行离线测试。后续目录检查、短文本验证脚本错误与用户授权的 mini Study 分别保留，不能将其混成配置阶段的零请求。
官方 API 配置与原 Provider 回归覆盖正式输入编译、
空 Key 提前报错、独立凭据与端点、真实 SDK/Mock function call ID 接续及共享计费。未安装新依赖。

官方依据：[API Key 设置](https://developers.openai.com/api/docs/quickstart)、
[Chat Completions 参数](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)、
[GPT-5.6 Luna 模型契约](https://developers.openai.com/api/docs/models/gpt-5.6-luna)。
