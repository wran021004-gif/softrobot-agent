# P2-B 独立 Agent 实证审计，2026-10-28

结论：部分验证，未达到 P2-B 完成标准。真实 Agent 经纠错后生成了一个 V3 候选；尚未验证它能查询候选参数能力、根据真实计算反馈做下一步决策或正确使用无 J 结果。没有模型 STOP，Study 未封存，不得将运行中断描述为 Agent 主动停止。

## 边界与入口

使用 `study_p2_v3_agent_positive_high.json`，独立空候选池和 Store `runs/p2-v3-positive-high-agent-remaining-20261028/private-store`；P2-A 的候选、控制和结果没有导入。用户在本轮明确批准向 DeepSeek API 发送指定 P2-B 任务、设计域、工具 Schema、会话消息和研究动作及结果摘要。不启动 P3。

当前 Study 冻结实现 `661ee842c2496d60e5a3ceffa3a4ba4e4ce7ca07`。首次启动前预检错误地因可选 CVXPY 缺失阻断 V3 agent-choice，修复限定在 V3 注册适用方法范围：可选 CONIC 在其独立发现及准入中仍明确显示不可用，旧 Study 预检保持严格。其后 Windows SDK 快照临时文件超过传统路径限制，修复采用扩展长度路径和规范化的 SDK 文件存储；包括命名空间存储的长路径读写已测试。两次问题均在 Provider 首次发送前发生；原 Store 通过正式迁移保留冻结规范与零计数，并非重建或清零。

## 实际决策

1. 模型选择直接生成三段三腱结构，但将 V2 `spans` 用于 V3，按 V3 验证规则被拒绝，未启动数值 Worker。
2. 它查询程序经验（没有匹配结果），改为显式 V3 基部锚定路由，但每段只给一个 section；某段原型需要不同数量的截面站点，实际生成返回 `EXACT_SECTION_STATIONS_REQUIRED`，科学验收未测。
3. 模型保留 V3 routes 并省略 section 覆盖，成功生成三段三腱候选 `ef2fbc71dc15f1e4fee75687e462e46f4d3d166702693be33d432f0969441a02`，计划引用 `2df3b8673facf680e48d2fced0297c267918c4ceec3850c9100dedd25e9664c8`。三段长度 0.16、0.11、0.14 m；三条肌腱沿各段走线、锚定第 2 段末端。生成合法不代表其设计目标或任务性能得到证明。
4. 第四个响应 HTTP 200，但 `finish_reason=length`；原始响应为 Store artifact `7d10db25a566a512afc4054b97dabadb60c955b3a0d36f5bdf414915b6c14dda`，请求 `r3-request-2df3e7c839024d128e0a27537e65f93c`。它包含未经验证的工具字段，未被准入或执行，保留为 `pilot.unconsumed_response`。没有待确认的未知 Provider 请求，也没有数值 Worker 挂起；该已保存但未消费的响应仍阻止正常后续发送与 Handoff。不要伪造一次模型动作、清除状态或重发原请求来恢复。

实际首次错误暴露 V3 JSON Schema 仍继承并展示不允许使用的 `spans`、`route_overrides`。后续修复只改变 V3 暴露的生成 Schema，移除这两项及旧 `strategy`，并说明 section 覆盖需与各原型站点数严格一致；V2 Schema 不变。修复通过离线测试，但没有应用于这次仍有未消费响应的冻结 Study，也没有真实复测证明该修复改善了 Agent 表现。

## 费用与上下文

| 请求 | 输入 tokens | 输出 tokens | 其中 reasoning | 请求字节 | 结果 |
|---|---:|---:|---:|---:|---|
| 1 | 21,466 | 5,167 | 4,112 | 76,491 | V2 spans 请求被拒，程序经验查询 |
| 2 | 27,751 | 5,635 | 4,197 | 100,133 | V3 路由，section 站点数无效 |
| 3 | 34,421 | 10,666 | 9,238 | 125,025 | 合法 V3 生成 |
| 4 | 52,386 | 32,768 | 31,365 | 196,007 | 长度截断，未执行任何输出动作 |

合计 4 Provider requests、136,024 input tokens、54,236 output tokens（其中 48,912 reasoning tokens）、190,260 total tokens。首次合法科研动作之前包含前三个请求，共 105,106 total tokens。工具定义的 JSON 序列化约 50,718 bytes；记录的完整请求实际大小从 76,491 增至 196,007 bytes（其他单独序列化值受格式影响）。第四请求耗时约 189.344 s，总 Provider 墙钟约 310.032 s；美元费用未知，不由 token 数自行臆造。上下文增长和截断已实测，不能把本轮视为真实 Handoff 恢复成功。

P2-B 账本：4 public calls、0 数学条目、0 Native 回调及积分步、0 独立物理回放、0.4234899 数值秒；Study 仍有 4 Provider 和 24 public 的计数余额，但未消费响应门禁阻止继续。整个 P2 累计：4 Provider、8 public、2 数学条目、1 次 T1、26 回调、15,600 步、0 独立回放、4.6842591 数值秒。真实账本还保留先前准备且零消耗的旧 P2-B Store，不纳入科学结果。

## 剩余问题

需要有证据保持、计数不重置的已确认截断响应处置与会话恢复路径，再验证已修复的 Schema、候选能力读取、真实反馈驱动动作和预算内停止。还需真实独立回放；P2-C 尚无可比较的重新优化 V3 T1 集合，真实 T2 敏感性未验证。一次真实局部驱动力计算没有证明它能改善 Agent 决策。P3 仍 NO-GO；不能把本轮合法起点提升为自主科研完成或任务通过。
