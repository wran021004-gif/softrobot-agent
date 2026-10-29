# 三个 Provider 的明确选择

工作目录：`D:\softrobot-agent\.worktrees\research-harness-v2`。
三个连接独立保存。用户每次指定使用哪个，操作者在准备新测试或 Study 时选择对应 runtime；没有自动回退。
既有 Study 继续使用其冻结 Provider，不通过修改文件偷换已冻结的模型或计费账号。

| 用户指定 | runtime 文件 | 凭据位置 | 当前状态 |
|---|---|---|---|
| DeepSeek API | configs/research/runtime_harness_v2.json | ~/.codex/.env 中的 DEEPSEEK_API_KEY | 真实工具闭环及自主生成已通过 |
| ChatGPT Gateway | configs/research/runtime_p5_luna_none.json | ~/.softrobot-agent/chatgpt-api.json；OAuth 由原 Gateway 管理 | gpt-5.6-luna none 真实工具闭环及自主生成已通过 |
| 官方 OpenAI API | configs/research/runtime_openai_api.json | ~/.softrobot-agent/openai-api.json | 配置及 SDK/Mock 验证完成，尚未填写/验证新 Key |

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
默认模型是 gpt-5.6-luna、reasoning_effort=none、store=false；模型是显式预设，尚未通过新账号目录确认。
如设置输出上限，官方 API 映射为 max_completion_tokens。错误、未知结果与原始响应恢复沿用原边界，SDK/transport 重试为零。

赠送额度、有效期和模型权限未读取，不能保证 Key 已可推理，也不会因此自动调用或自动转为其他 Provider。
如用户指定不同模型，应先确认其账号准入和端点/工具支持，再冻结该次配置。
此入口当前使用 Chat Completions，不将仅支持 Responses 工具的型号声称为已兼容。

后续可以直接说“这次用 DeepSeek”“这次用 ChatGPT Gateway”或“这次用官方 OpenAI API”，并指定模型及预算。
本次只配置并运行离线测试，没有目录请求、真实推理、新正式科研 Study 或科学 Worker。
新增官方 API 的 3 项定向测试通过，既有 Provider 的 7 项回归通过：覆盖正式输入编译、
空 Key 提前报错、独立凭据与端点、真实 SDK/Mock function call ID 接续及共享计费。未安装新依赖。

官方依据：[API Key 设置](https://developers.openai.com/api/docs/quickstart)、
[Chat Completions 参数](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)、
[GPT-5.6 Luna 模型契约](https://developers.openai.com/api/docs/models/gpt-5.6-luna)。
