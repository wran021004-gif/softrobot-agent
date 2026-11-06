# 第三个 Gateway 账号：无痕浏览器登录

第三个连接沿用 V2 Gateway、固定 SIWC SDK 和 DPAPI；与前两个账号独立。

| 项目 | Account3 |
|---|---|
| API 地址 | http://127.0.0.1:8789/v1 |
| OAuth / DPAPI 状态目录 | `%LOCALAPPDATA%\LocalResearchChatGPTGateway-Account3` |
| 本地 API 凭据 | `C:\Users\gugugaga\.softrobot-agent\chatgpt-api-account3.json` |
| 网络代理 | http://127.0.0.1:7890 |

工作目录与登录命令：

```powershell
cd D:\softrobot-agent\.worktrees\research-harness-v2\local-chatgpt-gateway
npm run account3 -- login
```

入口不自动打开普通浏览器，而是显示本次官方授权网址。复制完整网址到**同一台电脑的无痕窗口**，
登录第三个账号、选择工作区并批准 ChatGPT plan usage。保留原登录进程，SDK 等待本地回调最多 10 分钟。
网址与该次 state、nonce、PKCE 和回调端口绑定，不能替换参数、复用过期网址或只打开 ChatGPT 首页。
完整网址仅用于当次登录，不写入文档或 Git；OAuth token 和 PKCE verifier 不显示。

授权成功后，入口导出 Account3 自己的本地 API Key；不会复制前两个账号的 OAuth 或 Key。
普通 CLI 新增的 `login --manual` 只替换 SDK 的 openBrowser 回调，其他认证、权限与恢复行为保持原实现。
Account2 与 Account3 共用一个启动脚本，目录、端口和凭据位置按账号编号构造，原 Account2 命令和地址保持可用。

手动启动、查看状态：

```powershell
npm run account3 -- start
# 先停止 Account3 服务，再查看状态或重新登录；Account1/2 无须停止。
npm run account3 -- status
```

`npm run account3 -- setup` 仅初始化独立本地存储，无须登录、不访问上游。
服务器启动也不发送推理；具体模型和工具能力在明确选择该账号后另行验证。
本次不创建 Study、不发送模型请求、不增加自动账号轮换或 Provider 回退。

本地验证：9 项 Windows DPAPI、共享账号入口、原 CLI、运行锁和 Mock OAuth 回归通过。
原 Account1/2 状态与原连接凭据共 9 个文件在 Account3 setup 和登录等待阶段内容未变，
8787 / 8788 仍由原进程监听。Account3 本地凭据已生成；浏览器授权、服务启动结果须另行核实。

官方依据：[OpenAI Docs：Registration and sign-in](https://developers.openai.com/siwc/token-sharing-open-source/sign-in)。
