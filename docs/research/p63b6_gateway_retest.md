# B6 网关响应修复与独立重测

基线 `172ad585a3037251c80ce5296720abcee0184ce2`，分支
`codex/p6-3b6-gateway-repair-retest`。用户后续明确要求「修复网关响应，然后重新测试」。
旧 B6 的 HTTP 502 请求与已扣 1 次 Provider 原样保留；本轮另建独立 Study，不重发或重置旧请求。

## 可复现的响应丢失路径

确认实际监听 127.0.0.1:8787 的旧进程 PID=640676，来源为
`.worktrees/research-harness-v2/local-chatgpt-gateway`，不是仓库根目录的旧副本。
该推理转换只处理 terminal `response.completed.output`，忽略此前 `response.output_item.done`。
当 completed 事件缺少 output 或为空，而前面已有完整 item 时，本地丢失文本/工具调用并误报
empty_response。这条路径已用原 HTTP→Responses→工具反馈测试复现。

历史 B6 只保留了本地 502 错误，没有保存上游 SSE；因此不能证明该缺陷是那次失败的唯一原因。
真正的模型空输出仍可能发生，不能通过伪造回答或把半截调用当成功来掩盖。

修复仅在 inference.mjs 累积原始 completed item，按 output_index 排序；只有全局响应 completed
且 terminal output 为空时采用它们。非空 terminal output 仍优先。原始 call ID、参数、opaque
reasoning 和 usage 保留，不猜测缺失 token；全局 incomplete/failed/中断及未完成 item 仍拒绝。
server.mjs 允许合法的仅工具响应，保留真正 empty_response，并附带无敏感内容的输出来源/计数。
自动重试仍为 0，未修改 OAuth、DPAPI、账户/权限、代理路由、额度或 Agent 科研代码。

参考 [官方 Responses 事件定义](https://developers.openai.com/api/reference/resources/responses/streaming-events)
和 [官方 Sign in with ChatGPT 集成说明](https://developers.openai.com/cookbook/articles/sign-in-with-chatgpt)。
事件完整性依赖实际终止状态；离线测试不代表账户或模型行为已经真实验证。

## 离线验证与运行切换

`node --test --test-isolation=none test/inference.test.mjs test/server.test.mjs`：**25/25 通过**。
使用已有依赖；node_modules 和 .devkit 只在忽略目录中关联到旧运行安装，未修改其中的认证源码、
依赖或受保护状态。测试覆盖漏 terminal output、仅工具调用、call ID 与 reasoning 精确保留、
后续工具结果、terminal output 优先、真正空输出及各类失败；所有上游推理均为 Mock。
同进程测试避免当前 sandbox 的 Node 子进程 spawn EPERM，不需要网络或真实模型。

旧网关 health=ok、connected、plan_usage=true。只替换该端口已识别的网关进程，沿用相同受保护
账户状态与本地代理；不登录、重授权或切换账户。修复版从本分支启动并保留运行来源记录。

## 新 M 范围

[冻结配置](../../configs/research/study_p63b6_gateway_retest_sol.json)：
`p63b6-m-native-sol-gateway-20261030`。沿用 B6 冻结任务、FamilySpace、零初始态、数值协议和
九项 success_case 权限，原生成器与 seed_control baseline 提供 Operator 未评价结构/控制。
不导入旧控制结果、数学结果、科研判断或预算；Main 仍自主选择 Native 方法与科学参数。

Sol/none；Provider≤12（含 Reporter、失败与最后 1 次保护收尾），公共操作≤32（含 2 次保护），
共享数学≤4，Native callbacks≤24、iterations≤3、knots≤4；独立物理/NMPC/RL/NLP/BDF 全 0。
原环境、代码绑定、formal_study_authorization 和 live_handoff_admission 通过后只运行一次原入口，
不加 smoke 推理、不代交科学请求。Native 工作完整计账，任何数值都是仿真参考，不是实物真值。

实际启动来源、授权、逐请求回执、网关输出来源和 M1/M2/M3 在本次运行结束后追加；真实窗口内
不修改代码或冻结配置。
