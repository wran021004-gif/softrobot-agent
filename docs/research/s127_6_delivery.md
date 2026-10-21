# S12.7.5 修复与 S12.7.6 验证准备

2026-10-21。**离线修复和验证已完成；新的真实 DeepSeek 验证等待本轮独立授权，不能宣称 S12.7.6 live 完成。**
分支 `feat/sorosim-matlab-nmpc`，指定工作树；已重新 fetch，起点与远端均为
`f351104d75bd598ee14446589b50795bb9d1f129`，起点干净。其他工作树未改。

## A. 工程修复

`LiveBoundary` 原截断异常被本机 OpenAI `_base_client.AsyncAPIClient.request()` 的普通
`Exception` 分支包装为 `APIConnectionError`。原 Strands 连续路径还显式开启了截断放行；
默认重放路径也没有再次执行相同输出检查。

现在 SDK adapter 在输出交付前读取已持久化原字节，区分确认收到 HTTP、模型结束原因、
未验证工具字段和科学准入。HTTP 200 的 length/content_filter/aborted/资源中断/缺失完整结束
均不能作为 native 工具输出；SDK 包装异常会被还原成携带事实诊断的 `IncompleteModelOutput`。
CLI 输出结构化 `confirmed_incomplete`，以退出码 2 停止。
真正网络未知结果仍保持未知 reservation 并阻止重试，不被重新分类为模型截断。

首次收取、相同请求重放、SDK 重开和 `consumed()` 均保护不完整响应；
即使诊断调用显式允许读取原字节，SDK 仍不会交付任何部分工具字段，`consumed()` 也不能清除它。
未结清但已保存的完整响应在相同请求重放时使用原 receipt 结清，已结清响应不会再次计费。
原 body/reasoning 不改写，不创建 assistant 内容或工具调用，不修改第三方安装包。
本轮没有增加解除 incomplete 阻断的终态捷径；需要新请求时必须使用独立合法 Study。

[原 S12.7.4B 只读诊断](../../evidence/s127_5_provider/classification.json)仍为 HTTP 200、
length、8192 上限、1 次已计费请求、无工具调用、保存未消费响应、零未知发送。
原配置、字节、reasoning、账本和安全阻断保留；没有重发、迁移或使用其剩余 5 次额度。

科学引用增加按需 `/citation_eligibility` 视图：由唯一 `registered_references()` 清单派生
候选、任务、claim kind 与 supported inferences；默认摘要只展示简短规则、计数和最后一个登记条目。
可读 FamilySpace 或未登记运动样本不会自动获得支持证据资格，读取也不登记。
资格错误反馈给出被拒引用、原因、合法清单查询和缺少的验证。
原 `admit_decision()` 规则没有放宽；两次真实历史错误原样重放仍拒绝，合法数学/物理引用仍通过。
原默认摘要 <36,000 UTF-8 B 的限制仍通过；**字节不作为实际 tokens 报告**。

新发送增加输入 UTF-8 字节保守估计 + 最大输出 + framing 的容量门禁，超过冻结 context guard
时在 reserve/发送/计费前拒绝。该估计明确标记，不伪称 tokenizer 测量。

## B. 多回合决策准备

[冻结 manifest](../../evidence/s127_6_decision/manifest.json)、
[独立范围](../../evidence/s127_6_decision/scope.json)、
[合成 HTTP 的反馈交付检查](../../evidence/s127_6_decision/offline.json)。

三个真实截止状态：合法候选无性能结果、同候选已有完整物理失败、NMPC 完整但原任务失败。
完整/分层两组具有完全相同的任务、工具 Schema、初始科学证据和预算；每组至多三次连续请求，
总上限 18。初始均没有旧聊天，后续只传递该组自己的完整 reasoning、原工具 ID 和实际反馈。
18 次合成 HTTP 检查确认各后续 wire 实际携带上一轮工具反馈；不是预先拼入结果的大 prompt。

`evidence_read` 复用正式 Store 及派生视图。科学提案在一次性本地副本内经过正式 dispatch、
契约、证据和实际前置检查；只给副本重新绑定当前代码，原科学状态和预算不变。
正式分析的启动边界已用 fixture 验证可拦截，没有启动数值 worker。
`passed`、`prelaunch_passed`、`not_tested` 和 `rejected` 分开报告；RL worker 内部检查未运行，
不能据此宣称其完整训练准入。副本输出不导入冻结状态，不伪造物理观测。

**真实模型是否按事实调整决策、纠正错误引用、选择合法方法，以及实际 P/C/cache tokens
尚未测量。** 合成 usage 仅用于协议 fixture，不计入真实 Provider 统计。

## C. 新 Strands 会话

[新 Study](../../configs/research/study_s127_6_handoff.json)、
[SDK 范围](../../evidence/s127_6_handoff/scope.json)、
[真实 SDK/合成 HTTP 的完整本地结果](../../evidence/s127_6_handoff/offline.json)。
复用原 `build_harness()`、Store、Plan 和 `session_handoff.py`，没有复制 Agent 运行器。
新验证 Study 无旧候选/实验/数学/控制导入，Provider 上限 12，公共操作 60，固定输入物理最多 2，
数学/NMPC/PPO 为零；它是接续准入实验，不是完整科研成功试验。

合成 HTTP 下实际 SDK 经过四次响应：旧会话通过正式 Plan 生成结构、收到反馈并完成 invocation；
持久化旧 history，准备交接，保存新快照，独立恢复验证，原子提交 Store 指针；
新会话再实际初始化控制并消费反馈。新 SDK 没有复制旧工具历史，原候选和账本连续，
原工具 ID/结果配对，无 pending 或未结 receipt，零物理启动。

| 准入项 | 当前状态 |
|---|---|
| offline_protocol_passed | true，真实 SDK + 明确合成 HTTP |
| live_old_tool_round_passed | false，待独立批准后测量 |
| live_sdk_continuation_passed | false |
| live_scientific_action_passed | false |
| production_recovery_validated | false |
| production_handoff_admitted | false |

没有手工修改任何生产准入标志。生产默认连续 Strands 路径保留；真实接续请求本身不能代替合法
科学动作。待批准后必须由真实模型完成旧工具回合、新 SDK 请求和至少一次新合法工具动作。

## D. 验证、成本及后续科研

[验证清单](../../evidence/s127_6_handoff/verification.json)记录 **82 个不同通过测试 ID**：
53 项聚焦、10 项会话恢复、4 项新驱动、13 项旧契约/预算选择、2 项旧 Provider 恢复检查。
包含原 14 个进程终止子场景，不重复计为 14 个额外测试。
另有完整新版 SDK 四响应集成试验，以及 A 组三回合真实反馈传递的 18 响应合成试验。
一次旧 wire 捕获 fixture 补齐了新的输出检查边界接口；它从未接收或执行模型响应。
`git diff --check` 通过。测试使用原 Windows Python 和已有本地 MATLAB Python 依赖副本，
三个数值线程变量均为 1，没有启动 MATLAB/NMPC/PPO 或安装/升级依赖。

本轮**真实 Provider 请求 0、真实 token 用量 0、新物理启动 0**。
生产 `tools/` 和 `extensions/` **+92/-11，净 +81 行**，没有新生产模块。
测试代码较多是为了覆盖真实 SDK 异常包装、重复重放和隔离准入，而不是新增科研框架。
原任务、评价器、科学模块、正式 runtime 和封存证据无改动。
S12.6 原状态身份仍为 `d366a9a2791a6d35d881ca5c11bf82c182e03c38b912536ce8b900dfb071b5f3`。
原始 Provider、SDK 和 Store 文件只在忽略的本地 `runs/`；Git 只有代码、配置、派生统计和引用。

[容量与 S12.8 预检](../../evidence/s127_8_preflight/preflight.json)区分正式 32768 与新验证 65536。
本日核对 [官方 API](https://api-docs.deepseek.com/api/create-chat-completion/) 和
[模型资料](https://api-docs.deepseek.com/quick_start/pricing/)：1M 上下文，思考模式默认 64K 输出，
文档最大输出 393216；本轮只准备明确的 65536，不静默升至更高。
所有六个初始 wire 的保守输入+输出+8192 framing 均在冻结的 1,000,000 限制内。
Offload 仍只处理工具结果（500 preview / 1500 threshold），没有辅助模型调用或历史 reasoning 删除。

S12.6 实际消耗 43/48 Provider、8/64 物理（其中 2 NMPC）、1 次数学；首先短缺的是决策空间，
不是增加同一失败候选的零散物理扰动。因此提出讨论预算：96 Provider/8 protected、
300 公共操作/20 protected、64 共享物理、8 数学、4 NLP、4 BDF、4 NMPC、
2 PPO stages/131072 aggregate actions/每次最多 65536、2 独立 RL evaluation episodes，输出 65536。
这些只是新 Study 前需要独立批准和冻结的建议，绝不在运行中临时追加。

S12.8 尚未启动。真实决策验证仍缺，当前不能给出最终科研 Go。
接续是辅助优化：若 live handoff 安全性仍未获准，但真实多回合决策证明可行，
可用原连续 Strands + 分层证据 + 足够输出预算继续主科研；不让接续优化无限期阻碍研究。
新研究必须使用原任务、全新 Store/SDK/Study、空实验/数学/控制种子/外部科学证据。
结构生成/修改、数学、NLP、NMPC、固定/时变控制、局部/模式搜索、Direct/Residual PPO 全部仍可选；
数学预测不替代原 MuJoCo 独立验收，不规定方法顺序。

## 提交与待授权事项

已普通 push 并核对远端：

- `75f38de2ed50b29cb1248dd17b3d4aeec552b42f`：截断分类、拒绝与引用说明。
- `2843dcddf85a1b0b2cf9daa8a92bdc9002d6c0e4`：独立验证驱动、范围、配置与预检。

本文及新版 SDK 离线结果为后继提交。未 force push 或重写历史。
实际 live 执行需要用户独立批准 [A/B 完整范围](s127_6_authorization_scope.md)，
此要求来自用户任务说明第 6.4、7.2 节；不是 Git push 许可或旧授权可以替代的步骤。
