# 第二个 ChatGPT Gateway 账号

继续使用 V2 的固定 DevKit 和原 Gateway 实现。新增的是同一代码的独立本地实例，
不切换原账号 profile，不停止 8787，不复制 OAuth token 或本地 API Key。

| 项目 | 原连接 | 新增 Account2 |
|---|---|---|
| HTTP 地址 | http://127.0.0.1:8787/v1 | http://127.0.0.1:8788/v1 |
| OAuth / DPAPI 状态 | `%LOCALAPPDATA%\LocalResearchChatGPTGateway` | `%LOCALAPPDATA%\LocalResearchChatGPTGateway-Account2` |
| Harness 凭据 | `C:\Users\gugugaga\.softrobot-agent\chatgpt-api.json` | `C:\Users\gugugaga\.softrobot-agent\chatgpt-api-account2.json` |
| 网络代理 | 保持现有进程配置 | http://127.0.0.1:7890 |

新增入口的工作目录：

```powershell
cd D:\softrobot-agent\.worktrees\research-harness-v2\local-chatgpt-gateway
```

2026-11-06 已完成新账号授权并在后台启动 8788，无需重复执行启动命令。
以下命令用于日后的手动登录与启动。

首次登录：

```powershell
npm run account2 -- login
```

在系统浏览器中选择**新账号**和目标工作区，批准 ChatGPT plan usage。即使浏览器已经登录原账号，
也应确认这里授权的是要新增的账号。OAuth 由原固定 SDK 验证；浏览器授权完成前不声称已连接或有调用权限。
登录成功后会导出独立的本地 API 凭据文件，无须把 Key 填入源码或发到聊天中。

启动新账号网关：

```powershell
npm run account2 -- start
```

此命令已经包含 7890 代理，不需要再运行原 `start:proxy`，也不用设置 `SIWC_GATEWAY_KEY`。
原网关可继续占用 8787。停止 Account2 时只在它自己的终端按 Ctrl+C。
需要重新登录或查看状态时，先停止 Account2；原账号仍继续运行。

```powershell
npm run account2 -- status
```

`npm run account2 -- setup` 仅用于初始化本地状态和新凭据，不打开登录页或发送上游请求。
入口固定设置 Account2 的目录与端口，忽略继承的原 `SIWC_STATE_DIR` / `SIWC_PORT`；父终端的变量不被改写。
存在不同内容的 Account2 凭据文件时拒绝覆盖，原 `chatgpt-api.json` 从不作为写入目标。

后续指定“ChatGPT Gateway 第二个账号”即可明确选择此连接；仍然使用原 `chatgpt_gateway` Provider 适配。
新账号的目录、工具支持和额度需单独验证，不继承原账号的模型验证结论。
本次不创建 Study、不发送推理请求、不增加账户自动轮换或失败回退。

验证：新增 Windows DPAPI/CLI 回归确认两账号的状态、Key 和凭据隔离，即使继承原目录环境变量也不会覆盖原文件；
重复 setup 保持相同凭据，冲突文件保留并报错。连同原 CLI/运行锁回归，共 4 项通过。

2026-11-06 本地核查：原 8787 进程 PID 为 56416，实际源码来自
`D:\softrobot-agent\.worktrees\p6-3b6-gateway-repair-retest\local-chatgpt-gateway`，
不是本次编辑的 V2 工作树。没有切换该进程；原 OAuth、host、本地 API Key 和两份既有连接凭据，
共 5 个文件在新增 setup、登录和启动后内容不变。

用户在浏览器完成新账号授权后，原 SDK 返回 connected / sharing=true。
Account2 已后台启动，PID 为 623620，8788 的带认证 `/health` 返回 HTTP 200、
account_status=connected、plan_usage=true。原账号 Key 访问 8788、新账号 Key 访问 8787 均返回 401，
确认两个本地认证入口独立。原 8787 仍由 PID 56416 监听。
当次进程记录和检查结果保存在 ignored 的 `runs/gateway-account2-20261106/`，不提交凭据。
这些 PID 仅表示当次启动记录；后台实例的生命周期与后续手动终端启动分开管理。

本次真实推理请求为 0，没有读取新账号模型目录，也没有创建 Study。
connected / plan usage 表示身份与授权通过，不替代具体模型的实际调用能力验证。

官方依据：[OpenAI Docs：Accounts and sessions](https://developers.openai.com/siwc/token-sharing-open-source/profiles-and-sessions)
要求不同注册的账号信息、client ID 和凭据分开保存；不以 email 作为唯一账号身份。
