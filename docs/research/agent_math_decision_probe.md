# B：数学证据与主动科研决策 Probe

2026-10-25（Asia/Shanghai）。基线 `515500267`，独立分支
`research/agent-math-decision-probe`。本文件先冻结 B1/B2 设计，真实请求后追加结果；
评分规则冻结于首次 Provider 请求之前，不按回答修改。

两个情境、每组两轮，最多 8 次主 Agent 请求；Reporter、科学 worker、新物理步、
正式 Study 均为 0。不是一次新的机器人研究，也不执行 Agent 建议的实验。

## 输入与证据隔离

共同输入是冻结 Reach/Hold 任务、合法两段六腱结构、工程先验、相同方法目录、
方法成本、剩余行动预算与 production `Plan` / `ResearchDecision` 输出契约。
方法说明直接读取 `task_constraints.METHOD_MEANINGS`。两组唯一初始差别为
`diagnostic_evidence`。来源短标签对模型可见；报告文件路径和全文不发送。

| 情境 | 共同首轮事实 | Evidence 额外事实 | 两组共同第二轮观察 |
| --- | --- | --- | --- |
| Reach/Hold | S142 增刚执行位置通过、0.35 s 速度 0.02284909 m/s、张力合法、35 次 IPOPT 未收敛 | S143 同状态同输入 GVS/MuJoCo 速度差；S145 已检查力学链路及范围 | S144 同 NLP 120→480 次迭代对照；同输入一步与两个半步对照 |
| 结构 | A 的三合法刚度及同固定 U0 的 J=1.517493/0.160493/0.263424 | S140/S141 初态轴向一阶退化、非线性几何与动力学一致性、数值最优范围 | A 的三个重优化 J 及独立通过；回调、初始化、病态性和目标截断 |

Reach/Hold 的两轮诊断始终指向 S142 同一个增刚结构；A 的结构情境始终指向
C1 基准结构及远段 ±10% 模量。两者没有混用控制或结构身份。
S140/S141 是不同诊断目标/长度变化的数学模型限制，明确不充当当前刚度导数。
第二轮固定观察与 Agent 首轮选择无关，显式告知不是执行其提案所得反馈。
首轮原回答完整保存，两组及两个情境各有独立历史。

冻结数据及离线来源见 `tests/research/agent_math_decision_cases.json`；
精确线上的请求与响应保存在忽略的 `runs/agent-math-decision-probe/`。
Git 摘要为 `evidence/agent_math_decision_probe/summary.json`。

## 决策调用与预算

沿用 C1 的 `https://api.deepseek.com/chat/completions`、`deepseek-flash`、
thinking enabled、reasoning_effort high、max_tokens 32768、stream false；重试为 0。
这里是在既有 Provider 传输边界上调用同一科研决策契约，不运行完整 Strands 工具循环。
没有新增 Agent、Provider 适配器、调度器、任务 Schema、Store 实现或生产修改。

薄入口只允许 `research_plan` 提交一次 `Plan`，action 为 diagnose 或 stop；
其 `ResearchDecision.selected_method/research_intent` 与 Plan 原有假设、观察、固定条件、
解释和停止字段描述自主选择的科学行动。其余工具执行没有接入。
不要求另填未实际准入的执行 payload；所以本 Probe 不验证具体工具参数或正式 SELECT 准入。
复用既有平台 Store 与 `LiveBoundary` 记 Provider 费用；只建立传输 session，
没有调用 `Host.create`、Research Study prepare、科学 dispatch 或伪造执行 receipt。
正式 Study 的授权函数属于该生命周期，本实验没有创建其授权或伪装为已准入 Study。

授权来自用户本轮附件第六节的原 Provider/最多 8 次外发范围。
具体目的地与数据范围随真实启动一并经过正常执行审批；审批拒绝即停止真实请求。
凭据仅由原 `load_credential` 在进程内读取，HTTP 授权头不持久化。
请求额度包括失败与未知结果；已有运行目录拒绝自动重发，不换 ID 重试。
每轮在交付下一观察之前保存首轮原响应、解析结果与原 usage。
HTTP 原始字节由原边界先保存，两个 response 事件按 request_id 去重统计。
Provider 没有返回的金额与用量字段保持 unknown/null。

## 首次请求前冻结的审查规则

评分单位是一条情境/组别的完整两轮轨迹，共四条；每项 0–2，总分 10。
不将“选了哪个方法/结构”本身作为正确答案。可替代的合法、有辨别力且成本合理的
实验同样可得满分。自动检查仅负责格式、输入隔离、请求计数、用量和零科学派发。

| 指标 | 0 | 1 | 2 |
| --- | --- | --- | --- |
| 证据理解 | 关键事实/范围混淆 | 基本正确，遗漏相关限制 | 区分代理、求解状态、真实执行与未知量 |
| 假设质量 | 无可测竞争解释 | 解释重叠或预测不足 | 至少两个不同机制及可测预测 |
| 诊断辨别力 | 实验不能区分解释 | 有测量，控制/归因不充分 | 固定条件和结果分支能改变判断 |
| 决策适应 | 忽视/抵触新观察 | 知道新观察但更新过强/弱 | 按证据修正，或说明为何保留原解释 |
| 研究成本 | 超预算或无依据昂贵追加 | 有界但核算/前提缺失 | 预算、准入、停止规则与辨别收益一致 |

评分保留逐项理由、回答出处及人工复核空间，不采用关键词评分器。
“证据理解/诊断辨别力”等属于本次 Codex 人工式科学审查，尚不是独立人类复评。
两个情境、每组一条推理轨迹，只支持小样本诊断；不宣称统计显著或跨任务泛化。

## 离线验证和后续结果

定向测试覆盖输入仅预定证据差异、首轮无未来数值/报告/评分、八次单决策与独立历史、
production Schema 解析、原边界用量去重、无科学 dispatch，以及未知请求停止且不重发。
模拟返回仅是测试夹具，不计入科研观察或真实 Provider 消耗。
真实结果、评分与最终科研判断将在冻结后附于本节。
