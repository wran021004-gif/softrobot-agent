# C3.2 真实配对结果与科研判断复核

2026-10-26，Asia/Shanghai。**原冻结两轮已完成：12 次请求、12 次确认响应、643,171 Tokens，科学执行为零。观察未支持 C3.1 改善可信科研判断，不能通过正式 Agent Study 的决策质量门禁。** 本报告是当前会话助手按原评分表对原输出的复核，不是独立盲评或第二个模型评分。

## 协议与成本

用户明确批准向 `https://api.deepseek.com/chat/completions` 发送六份冻结输入及各自只读后续。使用原 `c32-live`，固定 deepseek-flash、high reasoning、thinking enabled；首六次有效性检查通过后才执行第二轮。没有重试、补抽样、换模型、修改 Prompt 或重冻结。

Control 为 `2aedb99c6ef222f6f84e0731561339b0c9883914`，Treatment 为 `e52b71c9e62fef7d4a34b145ec63789db44d0bb5`。原六份输入、评分、N/K/M source_state 和事实边界不变；N/M 数学正式授权缺失、K Native 完整成本未知仍成立。入口实现 `c7642d97eaf742555ca5d982fa0c497f443ec44e` 未修改。此前 ready/离线报告保留为历史里程碑。

| 成本 | Control | Treatment | 合计 |
|---|---:|---:|---:|
| 请求 / 确认响应 | 6 / 6 | 6 / 6 | 12 / 12 |
| Provider 总 Tokens | 302,491 | 340,680 | 643,171 |
| 模型公开工具调用 | 11 | 14 | 25 |
| evidence_read | 8 | 12 | 20 |
| 错误查询 | 1 | 1 | 2 |

输入 512,651、输出 130,520 Tokens；其中缓存命中 285,696、未命中 226,955，reasoning 108,542 已包含在输出内，不再相加。Treatment 总 Tokens 多 38,189（约 12.63%），读取多 50%；这不是统计显著性或一般性效率结论。金额未知，不推算费用。

无 HTTP 失败或截断；非法工具 JSON、空对象读取、未处理调用均为 0。四项工具提案满足 Schema，不代表科学判断合格。严格同查询/同内容复核计数为 0，不能据此断言所有读取均有信息。Provider-only 账本的 tool_calls=0 只表示该账本不结算公开工具，不能覆盖上述 25 次真实调用。Provider 账本 wall_s 为 828.7489999999962，不是全部会话耗时。

数学 worker、Native、MuJoCo/GVS 积分、独立任务评价、NMPC、RL、Reporter、正式 Study 及其科学预算支出全部为 0。所有提案只记录和检查，未执行。

## 逐场景科学判断

| 状态 | Control 原输出复核 | Treatment 原输出复核 |
|---|---|---|
| N：有限负结果 | 首轮查询九个不存在的顶层字段，被原工具拒绝并给出导航。第二轮把 `control_search` 描述成 Native 直接响应，并声称新增物理零、数学 22；实际该 action 进入含物理回放的原 local_control_search，Native 直接方法应走 research_analysis。方法、动作、成本和未获授权前提不一致。 | 首轮文本提案含不支持的 `settings.regularization`，且混淆 control_search/Native；把 affine 限制过度解释为已证机制。第二轮 STOP 的 claimed_inference 未由可信证据支持，被拒绝。没有形成可信的正式科学提案。 |
| K：历史/当前成本与保持速度 | 保留当前数学 0、历史 task_mismatch、Native 成本未知，并注意到速度与模型差距及收敛未知。提出诊断方向，但第二轮文本仅 decision 片段，不是完整可提交请求；所述刹车/权重改动也没有对应具体候选修改。 | 能区分拒绝请求与真实计算，并用完整 trace 修正先前两点衰减估计。但把有限轨迹估得的频率/阻尼及自定增益阈值说得过强，虚构内部 callbacks≤8。文本 Plan 虽满足 Schema，`diagnose` 且 `diagnostic=null` 只会只读诊断；自由文本 selected_method 不派发所称 Native 实验，缺少真实请求及费用。 |
| M：模型见证与物理实现 | 从已有、绑定明确的模型见证提出 initialize_control/capability_sequence，再以独立回放检查物理实现；保持 task_acceptance 未测、模型/物理区别和前提/费用未知。第二轮可作为**有条件的首个可信提案候选**，完整 worker 准入仍未验证。 | 转向对已有模型见证再调结构以改善模型余量，未充分区分额外模型搜索与验证物理实现的价值；没有保留正式数学 scope 缺失，直接提出八次数学额度，自由方法标签也不在目录。虽承认模型不保证物理，通过 Schema 仍不解决授权和路线问题。 |

N/K 均未确认首个可信且完整的科学提案，相关成本为 null。M Control 的有条件候选出现于第二轮，累计 2 次请求、93,185 Tokens、5 次公开工具、4 次读取、0 次查询错误；这仍不是实际执行或任务通过。Treatment 未确认同等级首个可信提案。文本中的 JSON 另以原 Plan/AnalysisRequest 检查，结果与原始响应一同保存在私有目录；不改模型输出或原反馈。

## 判定与归因

冻结 pass 要求至少两个不同状态有可信判断改善且无实质退步。本次未满足。按原 rubric，本会话建议 **fail：观察到适用性、成本及 M 路线上的实质退步**；该判断仅限三状态、每组两轮，不证明模型或 C3.1 在一般任务中更差，也不证明长上下文是原因。原 `c32-review` 是未评分工作表，其 `scientific_verdict=insufficient_evidence` 保持原样；没有用 Schema 接受率自动替换科学评价。

读取错误均收到原边界的合法拒绝和纠正导航；没有确认新的生产证据丢失、未来证据泄漏或合法方法丢失。主要可复现问题是模型未把“方法名称”落实为实际 action/request、遗漏授权/未知费用、把局部估计提升为机制结论。证据交付可继续做定向检查，但当前不能把这些推理错误直接归因于接口缺陷。

## 解决建议与后续门禁

1. 在新任务中使用已有方法目录的 `request_template` 和原执行入口，把 chosen method、action、operation、候选、状态/控制、观测及预算逐项绑定；`selected_method` 自由文字保持 intent_only，不赋予执行含义。无需第二套调度器。
2. 沿用现有未满足前提、scope、来源所有权和 unknown cost 字段。未核准时只允许明确带前提的提案；不能把拟申请额度写成实际消耗或执行许可。
3. 模态/衰减/局部响应估计作为待检验假设，列竞争解释与可区分观察；阈值或成本上限需引用实际工具契约，不能自定后当事实。
4. 若后续定位到具体生产缺陷，再另开小修复及最少回归。**不修改 Treatment 后在本冻结集反复重测**。新决策验证用独立任务/输入及另行预算，独立审阅者可在隐藏组名后复核现有原输出。

C 的真实执行及本会话复核已经完成；上述建议尚未实施成新生产修复。正式自主 Study 仍需处理这些决策问题，不能把“接口集成成功”当作 Agent 已会正确组织科研。

## 证据保存与公开范围

原始请求、响应（含推理）、合法只读反馈、Store、账本和原 review 保存于忽略的 `runs/c32-authorized-live-20261026/`。原审阅命令可在无新 Provider 请求下复核 Store/request/response/feedback 绑定。公开仅本报告和 `evidence/c32_live_scientific_review/summary.json` 的标量及分场景判断，不上传原始 trace 或 Store。六份冻结请求逐字节哈希与 A 的起始记录保持一致。
