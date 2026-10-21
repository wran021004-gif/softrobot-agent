# S12.7.6 独立外部传输授权范围（A+B 已批准）

2026-10-21。用户对本轮完整范围独立回复“批准 A+B”。
批准记录见 [A](../../evidence/s127_6_decision/authorization.json) 与 [B](../../evidence/s127_6_handoff/authorization.json)，
机器 scope 保持批准时的语义与 hash，未借用 S12.7.4 授权。
任务说明第 6.4、7.2 节要求本轮在发送项目数据前取得独立授权。
API key 仅用于请求头，不进入请求正文、Store、报告或 Git。

| 范围 | A：多回合决策对照 | B：真实 Strands 接续 |
|---|---|---|
| Endpoint | `https://api.deepseek.com/chat/completions` | 相同 |
| Model | `deepseek-flash`，thinking enabled，high effort，非流式 | 相同 |
| 新请求上限 | **18**：三个状态 × 两组 × 三回合 | **12**，旧/新 SDK 会话共享 |
| 每请求输出上限 | **65,536 tokens**（包含 reasoning） | 相同 |
| 自动重试 | 0 | 0 |
| 新数值计算 | 0；数值启动被隔离拦截 | 数学/NMPC/PPO 为 0，固定输入物理最多 **2** 次 |
| 传输范围 | 三个冻结状态的原 Reach 任务、FamilySpace、候选/控制、原科学结果及预算、原工具 Schema、真实按需读取和正式准入反馈 | 全新空历史 Study 的原任务/FamilySpace、Agent 自主生成的候选/控制、该 Study 自己的反馈/结果/预算、Plan 和 evidence_read Schema |
| 既有聊天历史 | 不含旧聊天。每组新交互自己的完整 reasoning、工具 ID 与反馈在本组三回合间传递 | 只在旧 invocation 内回传其自己的 reasoning/工具历史；新 SDK 会话只接收权威科研交接包 |
| 原始物理记录 | 可按需读取截至冻结时刻可达的原始样本、实测 NMPC 数组 | 仅新 Study 自己至多两次固定输入评价的原始记录 |
| 本地保存 | 原请求/响应字节、完整 reasoning、反馈、Store 留在忽略的 `runs/` | 原请求/响应、完整 reasoning、Store、SDK 快照留在忽略的 `runs/research/s127-6b-sdk-20261021/` |
| Git 上传 | 代码、配置、派生统计、hash 和精确引用；不上传原始 Provider/SDK 对话或完整 Store | 相同 |

A 的三个状态是合法候选无性能结果、同候选已有完整物理失败、完整 NMPC 原任务失败。
完整组与分层组的初始任务、科学状态、工具和预算完全相同；后续读取反馈真实传递。
数值拦截不会被当作新科学结果；局部检查和完整启动前检查分开记录。
原始历史仅用于隔离对照，不得导入 S12.8 Cold-start。

B 使用新 Study `s127-6b-sdk-20261021`、新 Store 和新 Strands session；
保留旧 `s127-4b-sdk-20261021` 的 8192-token 截断、原始 reasoning、账本和安全阻断。
不重发原请求、不扩大旧额度、不人工构造 live 工具调用、不修改生产准入标志。
SDK 仍走“准备 → 持久化 → 独立重开 → 验证 → 原子提交”协议。
模型自由选择允许的动作或 STOP；不保证它会产生指定方法或成功接续。

冻结机器范围：[A scope](../../evidence/s127_6_decision/scope.json)、
[A manifest](../../evidence/s127_6_decision/manifest.json)、
[B scope](../../evidence/s127_6_handoff/scope.json)、
[新验证 runtime](../../configs/research/runtime_s127_6_validation.json)、
[B Study](../../configs/research/study_s127_6_handoff.json)。
本轮总请求最多 **30** 次；输出容量上限合计 1,966,080 tokens，实际可能远低于此。
没有静默升至 131,072 的授权。真实 token 用量以 Provider 返回 usage 为准。

授权已分别绑定 `stage`、完整 scope 的 `digest`、`request_ceiling` 和用户实际批准文字，
在首发前保存在忽略的本地授权记录；实际使用 A 18/18、B 11/12 次，物理启动均为零。
任一 scope、预算或数据范围变化需要重新确认。
此授权**不包含自动启动 S12.8**。
