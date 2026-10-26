# C3.2 — 科研证据理解与自主实验选择离线冻结

2026-10-26，Asia/Shanghai。**结论：证据不足。** 六份配对输入已完成零 Provider 冻结，
但没有新模型输出，不能比较新旧科研判断，也不能支持进入完整自主 Study。
本轮未获得针对这些新冻结输入的明确外发授权，因此停在真实请求之前。

## 两个确切基线

- Control：`research/c3-agent-decision-efficiency@2aedb99c6ef222f6f84e0731561339b0c9883914`。
- Treatment：`fix/c31-scientific-decision-feedback@e52b71c9e62fef7d4a34b145ec63789db44d0bb5`。

首次核实时本地和远端均没有 C3.1 提交。用户随后提供 C3.1 实施任务，修复已在独立工作区
完成、经 13 项定向测试和 C3-A 复核后提交并推送；远端 HEAD 已核对为上述 SHA。
没有用较早的其他 feedback 分支替代 Treatment。
C3.2 独立分支 `research/c32-scientific-decision-probe` 从 Control 建立，只修改原探针/审计及测试、协议和报告。
两版生产目录与其确切提交一致。没有重建 Harness、Provider 适配器、Store 或历史重建器。

## 场景与原始事实

| 场景 | 封存目录 / preparation 事件 | 科学状态与判断标准 |
|---|---|---|
| N：有限负结果 | `c3_heuristic_ab_100ms_20261025` / 338 | NMPC 的终点误差 0.0219121 m、保持位置 0.0301895 m、速度 0.522187 m/s 均违反原阈值；一个 task_capability 结果为 inconclusive，sampled violation=15.200000000000118，虽 numerically_checked 仍非结构不可行证明。数学已计费 2。 |
| K：历史与当前成本 | `b3_t2_pilot_050_b` / 152 | 当前 NMPC 终点 0.00314837 m、保持位置 0.00603803 m 通过，速度 0.111374 m/s 失败；当前数学计费 0。历史有另一 Study 的数学及物理结果，历史时域 0.35 s，当前 0.5 s，不能转移结果或支出。 |
| M：其他研究路线 | `c3_math_search_ab_100ms_20261025` / 184 | 六个候选数学结果、计费 12，当前独立物理结果 0；其中两个 feasible_witness 的 sampled violation 约 −0.2，尚非独立物理通过，近乎相同的数值不能直接推出结构优势或可信梯度。 |

三个状态原位置阈值均为 0.010 m，保持速度阈值 0.020 m/s，保持窗 0.05 s；
原任务、时域、初态、候选、预算及权限不改。逐项原数值、状态、精确引用在 summary 中保留。

| 场景 | source_state artifact |
|---|---|
| N | `674aab2fa6d71affc3bde34f1e21e5a37956f9ba5c0ac1854295d6dd8c9d9629` |
| K | `ef897ef6cf071c1fcd55989cb3a271ef80b0ac15a0c1f22d3e20642d0d06b2dd` |
| M | `90410a7fe2525c8eb921115056f96945694eb1d01aa3d6ae1efc1fef8e484d5b` |

这些不是 C3 原配对的 R1@425、R1@2110、pilot-C@425。
不过 N/M 来自同一既有 A/B 协议，K 又含其历史背景；部分底层证据已用于旧研究及 C3.1
对照范围测试。它们是不同封存 Study 的独立保存状态，**不声称完全盲测或统计独立**。

覆盖范围有两项限制：

- N/M 当时的正式数学 scope authorization 缺失，两版均保留全部 16 方法及相同权限状态，
  不补授权。可检验证据解释与带前提的提案，不能证明可执行数学路线之间的自由切换。
  K 的多数方法已获授权，但仍保留其真实不支持或缺参数状态。
- K 没有当前/历史 native 优化总账可作精确配对；未找到足够可靠且不复用旧主场景的替代。
  因而 native 积分归属与完整成本理解只获得不完整覆盖，不能凭空加入 8,000 步或零成本。

## 历史隔离与对称性

复用 FrozenDecisionBoundary：源状态来自 preparation.source_state，剩余额度来自 preparation.budget，
可读引用仅为源状态及边界前事件引用的传递闭包；最终 snapshot 仅定位既存成员。
写入、reserve 和执行链 SQLite 均禁止。双方源状态、原始科学事实、任务、非 research 外层包、
全部方法目录及权限相同；代码中的证据交付和 EvidenceQuery Schema 差异为干预变量。

N/K/M 的原下一请求事件分别为 342/156/188。preparation 与下一请求之间仅有两条
session_handoff、model_decision_packet、r3_model，没有新科学事件。
相应闭包含 287/150/142 个 artifact；对各归档之后独有的 467/271/650 个输出，
双方逐项验证全部拒读，R1 最终成功引用也不在输入或可读闭包。
当前投影的推荐查询全部可读，状态未改。K 新版多出的三个检查是离线查询审计，
不记为 Agent 公开工具调用或真实 Provider 交互。

## 输入大小与预先冻结的评价

下表是实际三工具子集、原生产参数及共同只读说明组成的首轮完整请求，
使用仓库固定 tokenizer 对序列化 JSON 的离线估计。不是 Provider usage。

| 场景 | 旧完整 bytes / tokens | 新完整 bytes / tokens | 旧/新动态 tokens | 旧/新 Schema tokens |
|---|---:|---:|---:|---:|
| N | 122,154 / 35,965 | 123,833 / 36,343 | 26,526 / 26,862 | 8,731 / 8,773 |
| K | 89,378 / 25,825 | 91,089 / 26,293 | 17,930 / 18,356 | 7,119 / 7,161 |
| M | 120,471 / 34,718 | 122,486 / 35,164 | 25,281 / 25,685 | 8,731 / 8,773 |

第二轮由实际首轮输出和真实只读反馈决定，当前无法给出完整字节/Token 数；
不会编造回答、worker 回执或科学观察来填充。第二轮规则已冻结。

评分标准已在首次真实发送前保存于
`tests/research/fixtures/c32_scientific_decision_protocol.json` 的 rubric_offline_only，
不进入六份请求。按事实范围、实验辨别力、适用性/自主性、成本分别评为 accurate/partial/error/unassessable，
无加权总分、不指定唯一方法、不要求用完数学工具或虚构机制概率。
可信提案必须同时合法、有事实依据、提出区分竞争解释的观察及分支预测，并明确成本和未核准前提。

仅列方法名、Plan 被接受或详细参数都不算已完成有价值科学计算。
预先区分 pass、partial_pass、fail、insufficient_evidence，完整判定口径见协议。
任何未来真实错误、超时和无效 JSON 都保留并计费，不补抽样或事后改评分。

## 执行、逐场景比较与未解决问题

真实 Provider **0**；真实输入/输出/总 Tokens **0/0/0**；Agent 公开工具调用和 evidence_read **0/0**。
科学 worker、数学求解、native 优化/rollout、MuJoCo/GVS 积分、NMPC、RL、独立物理评价、
Reporter 和正式 Study 全部 **0**。未建立 C3.2 Provider 账本，原 C3/R1 额度消耗 **0**。
尚无 Provider 金额记录，不推算费用。

| 场景 | 旧/新科研判断比较 | 当前能确定的范围 |
|---|---|---|
| N | 未运行 / 未运行 | 源事实与有限负结果标准已固定；没有推理改善证据。 |
| K | 未运行 / 未运行 | 历史/当前来源与零当前数学计费可读；native 完整成本覆盖不足。 |
| M | 未运行 / 未运行 | 六个数学结果及未测物理状态可读；执行授权限制已保留，不能把条件提案当执行能力。 |

首次可信提案的实际交互成本为 null，因为没有模型输出。
无效 JSON、错误查询与可确认无信息读取的实际事件数均为 0，不能解释为效率提升。
不存在可归因的新科学判断改善或退化；也不能把任何后续推理错误预先归因于上下文长度。

未来若获本轮明确授权，候选设计至多 3×2×2=12 次：先 N旧/新、K新/旧、M旧/新六次，
核对实验有效性后才按逆序执行预定第二轮。端点 `https://api.deepseek.com/chat/completions`，
沿用 deepseek-flash、high、thinking enabled 和原生产参数；独立账本，不重试、不换模型、不扩额。
当前没有启用 C3.2 live 入口，原 c3-live 因 scope 不同拒绝该冻结包。
这同时遵守新增 C3.1 任务的零 Provider 边界。数学执行授权和 Provider 外发授权是不同前提。

## 测试、复核与交付

- 新增归档回归通过：真实未来物理结果拒读、评分不进入请求、原 AnalysisRequest 仅记录提案、
  成本未知与未检查前提明确、零 worker/网络、C3 旧 grant 不能发送 C3.2 包。
- 复用原两轮共用 12 次额度的 mock 回归通过：拒绝第 13 次及重复启动、零 dispatch。
  其中十二次是本地模拟响应，不是 DeepSeek 调用或科学证据。
- 六份最终配对离线冻结通过；git diff --check 通过。没有全量 pytest 或科学重跑。

复核：在本工作区用既有 `.f3-prestudy-env` 执行
`python -m tests.research.agent_math_decision_probe c32-freeze --out <新的 runs 子目录>`。
原 Control 和 Treatment 工作树需保持上述确切 HEAD；本命令无网络/凭据读取或 live 路径。
早期离线准备保留于忽略目录，最终冻结为 `runs/c32-final/`；评分与输入修改均发生于 Provider=0 时。

公开交付仅有必要测试/审计适配、冻结协议、此说明和
`evidence/c32_scientific_decision_probe/summary.json` 的标量/来源汇总。
完整输入仅保留本地忽略目录；没有新增原始 Provider trace，也没有公开冻结输入或 Store。
普通 push 到独立分支，不合并 main，不改原 R1/C3/C3.1 分支。
