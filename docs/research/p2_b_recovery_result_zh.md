# P2-B 截断恢复与单次真实决策，2026-10-28

## 结果与证据

原第四次响应在 HTTP 200 下因 `finish_reason=length` 不完整；保存的原请求明确设置 `max_tokens=32768`，实际输出恰为 32,768 tokens，其中 reasoning 31,365。工具字段未执行，不等同于模型 STOP 或有效科研决策。

在原 Store 上使用正式 `core.bind` 工程迁移，原冻结 `661ee842c2496d60e5a3ceffa3a4ba4e4ce7ca07` 迁移到 `fc4d1b490ee453314901ca88717bcaf81c11b7dd`；迁移记录包含 `previous_commit`、原因和 `material_behavior_change=false`。原冻结规范、候选、证据和计数未变。恢复入口独立核对了原请求 hash、原决策包和工具 Schema 身份、连续迁移链、已结算收据、原响应、SDK 快照及所有先前工具反馈；检查无未知 Provider 或科学 Worker、截断后无工具执行。

确认后，在同一原 Store 完成 prepare → 保存新 SDK 快照 → 独立重新打开 → 身份核验 → 原子提交。处置 artifact `aeab8406f1f2be8cd6421197fa0c05b48d56c9cb44a6d78c19bfb55816a50ecc` 将原响应标记为已计费、归档但不执行；handoff artifact `8c0927bcdbba399f7d9f7d1ed280cfcf7e6042703a8f1736f8a6abac5dbabdad`；独立验证 artifact `0b1c87c0996463c08e0e3c72544fe8437844e57eb700a1e6904a33d9710b94a4`。原请求 `r3-request-2df3e7c839024d128e0a27537e65f93c`、响应 `7d10db25a566a512afc4054b97dabadb60c955b3a0d36f5bdf414915b6c14dda` 及旧 SDK 历史保留；清除阻塞指针只与处置证据、已验证新快照和会话指针的事务提交一起发生。

新会话 `rh-58660e428c941b388b0322e4` 仅接收权威当前状态、最后可信工具反馈和工程处置事实，不导入截断推理或其工具字段。独立重开验证没有发送 Provider，也没有新增科学工作或费用。此项证明工程接续，并不单独证明 Agent 科研能力。

## 唯一新增真实请求

随后在同一 Store 使用 `max_new_provider_requests=1` 发出 `r3-request-fcacd8a931d847aca84b6dd23b6c2772`；原 Provider 冻结配置未变。HTTP 200，`finish_reason=tool_calls`，input 28,434 tokens、output 26,384（reasoning 24,013），共 54,818 tokens，149.765 s。模型提交 `initialize_control`，引用原候选 `ef2fbc71dc15f1e4fee75687e462e46f4d3d166702693be33d432f0969441a02`，工具成功生成绑定的完整控制源 `67395ed42e34265a501c1fb6d8ec6f0601a9d860733d1c1911ecc618d9131130`：0–0.6 s，31 时间点对应 30 个零阶保持区间，三条腱的有限张力范围 0.2–7.3 N。原任务 acceptance 为 unmeasured；模型的弯曲和到达预测是未经物理验证的假设。

这是一个可执行的控制初始化行动，不是 Native 控制优化、数学分析、物理回放或任务通过。模型并未先查询候选能力，也未根据新物理任务反馈再决策。本次没有新的数学、Native 或物理条目。单次请求上限触发监督暂停，工具反馈经独立校验后保存 `request_feedback_boundary_v1` artifact `415eb3b9bc0949971960839e1029e53d174d44d8408b780e26f42dc799c58b2f`；Study 仍为 ready，未伪装为 Agent STOP。

## 上下文与费用

| 指标 | 原截断请求 | 恢复后请求 |
|---|---:|---:|
| 请求体 bytes | 196,007 | 104,917 |
| Provider input tokens | 52,386 | 28,434 |
| Provider output tokens | 32,768 | 26,384 |
| 其中 reasoning tokens | 31,365 | 24,013 |
| 历史 reasoning 内容 bytes | 70,152 | 0 |
| tools 紧凑 JSON bytes | 47,337 | 45,206 |
| L0 尾消息紧凑 JSON bytes | 52,934 | 54,326（内容字段） |

两列 L0 数字采用不同的消息/内容口径，不适合相减或与其他字段简单相加。新请求体减少约 46.5%，实际 input tokens 减少约 45.7%；这是一对请求观察，不证明一般性效率改善。输出和 reasoning 仍很高，不能认为长推理成本已经解决。三次请求产生首个合法候选；恢复后一次请求产生首个合法控制初始化，但首次真实数学或控制优化动作尚未发生。

真实新请求中，V3 Schema 不再展示 `spans`、`route_overrides` 或旧 `strategy`，包含 `routes` 及分段路径；section 提示冻结根原型 1 个、每个后续段 2 个站点。模型本轮选择控制初始化而非新生成，因此只验证了实际发送的 Schema，没有验证新的 V3 生成纠错表现。V2 Schema 保持原样，后端真实非法站点请求的定向 fixture 返回各段要求与可省略 sections 的提示。

P2-B 累计 5 Provider 请求（含 Reporter 的合计；Reporter 0）、5 public、0 数学条目、0 独立回放、0.6466425 数值秒；Provider usage 累计 input 164,458、output 80,620、total 245,078 tokens。整个 P2 累计 5 Provider、9 public、2 数学条目、1 次真实 P2-A T1、26 callbacks、15,600 积分步、0 独立回放、4.9074117 数值秒。P2-B 还有 3 次 Provider 计数余额，其中 2 次受保护；未扩额，也不假设余额必须花完。金额未知。

## 验证与 P3 判断

定向离线测试覆盖正常响应拒绝处置、未知 Worker、历史不一致、截断后动作、原计费保留、准备前/准备后/快照后崩溃、重复调用、SDK 独立重开、Windows 长路径快照读写与哈希、V3 与 V2 Schema、截面错误提示，以及仅一次新 Provider 请求后暂停。模型/Provider 使用 Mock 的部分均是工程 fixture。当前真实 Store 的工程恢复、新发送请求、控制来源和费用以实际收据为准。

**P3 NO-GO**：还没有 P2-B 的真实数学/Native 控制优化、基于实际任务反馈的下一步决策、独立物理回放或真实 T2 敏感性；长 reasoning 成本依然突出。P3 待批准配置未启动。当前报告提交后的源码 HEAD 与上述 Study 冻结版本不同，未来任何继续必须再次走正式迁移和恢复准入，不能默默替换冻结实现。
