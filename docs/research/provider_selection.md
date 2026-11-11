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

## 新增 Gateway 第二个账号

原三类 Provider 及已有凭据继续保留。新增连接使用同一个 `chatgpt_gateway` 适配，
独立地址 `http://127.0.0.1:8788/v1` 和凭据 `~/.softrobot-agent/chatgpt-api-account2.json`。
账号由 `npm run account2 -- login` 登录，`npm run account2 -- start` 通过 7890 代理启动。
后续明确指定“Gateway 第二个账号”；账号目录和模型权限单独验证，既有 Study 的冻结连接不变。
详见 [第二个账号说明](gateway_account2.md)。

第三个 Gateway 账号使用 `http://127.0.0.1:8789/v1` 和 `~/.softrobot-agent/chatgpt-api-account3.json`。
`npm run account3 -- login` 显示官方授权网址供复制到无痕浏览器，`npm run account3 -- start` 启动独立实例。
后续明确指定“Gateway 第三个账号”；前两个连接不切换。详见 [第三个账号说明](gateway_account3.md)。

2026-11-06 用户批准后，第二、第三账号各自目录均返回 8 个型号，gpt-5.6-luna / none 短文本推理均通过。
首轮共两次 empty_response 保留，移入已有完成事件修复后各复验一次成功；总四次尝试。
具体工具调用能力未在这两个新账号测试。见 [真实验证报告](gateway_accounts23_validation_20261106.md)。

## 官方 OpenAI API 第二份 Key

2026-11-11 新增独立凭据文件 `C:\Users\gugugaga\.softrobot-agent\openai-api-account2.json`。
在该文件的 api_key 引号内填写新 Key；base_url 保持 `https://api.openai.com/v1`。
原 `openai-api.json` 保留，用于第一份官方 API Key。

第二份连接使用 `configs/research/runtime_openai_api_account2.json`，只改变 credentials_reference；
继续复用原 openai_api 适配、7890 代理和 none 配置，不自动轮换或回退。
配置默认模型仍为 gpt-5.4-mini，但新 Key 的模型权限及额度尚未验证；本次只准备配置，不发送 API 请求。
后续明确指定“官方 API 第二个”，再按该 Key 实际目录和授权选择模型；不更改既有 Study 的冻结凭据。

用户填写后于 2026-11-11 明确批准验证：经独立凭据和原 7890 代理，一次目录 GET 返回 HTTP 200、96 个型号；
一次 gpt-5.4-mini / none / store=false 短文本请求返回 HTTP 200 和 OK，实际响应型号 gpt-5.4-mini-2026-03-17。
usage 为 prompt=10、completion=4、total=14，reasoning=0；费用与剩余额度未知。
无重试、切换 Key/模型或科研 Study；本次只验证文本推理，没有验证新 Key 的工具调用或其他型号权限。
原始本地请求、响应及结果保存在 ignored 的 runs/openai-api-account2-validation-20261111，未上传 Key。
