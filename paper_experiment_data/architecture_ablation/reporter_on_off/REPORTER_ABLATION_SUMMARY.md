# Reporter ON/OFF Research Architecture Ablation

已实际完成六个真实历史节点、六份完全匹配的历史 Reporter 报告复用、十二个独立 Main 决策 Session，以及六次独立模型匿名成对盲评。未执行数学求解、结构搜索、MuJoCo 或完整 Study。M1/P3 各 A/B/C；类别近似匹配和原证据引用见 snapshot_manifest.csv。

## 成对结果

质量分为独立模型 gpt-6-astra 的五项 0–4 盲评分等权平均。评审只获共同原始证据和 A/B Plan，不获条件标签、Reporter 报告、历史下一步决策或成本。分词数字为标准 o200k_base 对**可见上下文文本**的统一代理计数，不能当作 Provider 实测或账单 Token。

| 节点 | OFF 质量分 | ON 质量分 | ON−OFF | OFF 上下文代理 Token | ON 上下文代理 Token | 增量 |
|---|---:|---:|---:|---:|---:|---:|
| M1_A | 4.00 | 4.00 | +0.00 | 47,654 | 49,360 | +1,706 |
| M1_B | 4.00 | 4.00 | +0.00 | 19,717 | 21,455 | +1,738 |
| M1_C | 2.80 | 3.60 | +0.80 | 16,639 | 17,690 | +1,051 |
| P3_A | 3.00 | 4.00 | +1.00 | 187,680 | 188,636 | +956 |
| P3_B | 3.80 | 3.80 | +0.00 | 191,274 | 192,859 | +1,585 |
| P3_C | 3.00 | 3.00 | +0.00 | 91,520 | 93,187 | +1,667 |

六组 OFF 均分 **3.433**，ON 均分 **3.733**；配对差均值 **+0.300**，中位数 **+0.000**。ON 胜/平/负为 **2/4/0**。这是小样本、单次回放和单模型评审结果，不构成充分统计显著性或机器人任务成功率改善证明。

| 指标 | 配对差均值 | 配对差中位数 |
|---|---:|---:|
| physical_interpretation | +0.167 | +0.000 |
| evidence_consistency | +0.500 | +0.000 |
| limitation_recognition | +0.167 | +0.000 |
| research_actionability | +0.333 | +0.000 |
| main_decision_quality | +0.333 | +0.000 |

无证据支持结论数由盲评模型判定：OFF 2，ON 0。逐条结论、严重程度、引用语义问题及理由保留在 blind_review/*/independent_model_review.json，条件解盲后的逐项表在 scores_unblinded.csv。解释更长本身不加分；假设不因尚未证实而自动算作无支持事实。模型评分仍须人工复核，human_scoring.csv 留空供复核，未伪造人工分数。

## 对实验问题的直接回答

- **整体质量是否提高：** 本轮独立模型盲评均分提高 0.30/4，但中位配对差为零，四组持平；不能写成普遍改善。
- **哪类证据体现价值：** 胜出的两个节点分别是 M1 C 的适用性/执行约束边界，以及 P3 A 的有限参数对照与缺失成对机制验收。两个竞争解释 B 节点均未拉开差距。
- **物理机制理解：** 指标均差 +0.167；P3 A 的 ON 将实际参与承载的腱与所需的干预对照联系起来，OFF 的完整未消融 Replay 未明确覆盖缺失的成对机制指标。
- **限制识别：** 指标均差 +0.167；M1 C 的 OFF 提议 120 次迭代，超过冻结 100 次上限，并假设了未被所给证据证明的初始化选项，ON 避免这些缺陷。P3 C 两组仍同分，不能说 Reporter 一定能解决证据边界理解。
- **无支持解释是否减少：** 盲评模型识别的无支持结论由 2 降至 0，两条 OFF 问题均判为 moderate；这是模型评审记录，仍待人工复核。
- **行动是否更具体有效：** Research Actionability 均差 +0.333。P3 A 的区别是成对腱约束消融与仅完整协议 Replay，比较的是补齐机制证据的针对性，不是行动文本长短。
- **额外 Token 成本：** ON 平均增加 1450.5 个可见上下文代理 Token。P3 三节点分别增加 956/1585/1667，约 0.51%/0.83%/1.82%。Provider 实测和隐藏推理用量未返回；报告历史生成成本另计，不能把代理数当成精确总成本。
- **是否有 ON 更差：** 本轮主要指标下有 0 组 ON 落后；样本太少，不能据此排除 Reporter 在其他节点产生负效应。

## 逐节点解释与是否值得写入论文

- **M1_A**：Both decisions choose the same scientifically appropriate next action: replay candidate 697fd5d6… with saved control schedule 49ec0d18… from the frozen initialization over 0–0.6 s. The native result ddc70950… records favorable sampled metrics, including holding speed 0.028321836968032563 m/s against 0.03 m/s, but explicitly lacks independent replay and original task acceptance. Both decisions address that gap without converting the numerical observation into an established pass or claiming executable admission merely from the request. Their references correctly identify the numerical evidence, schedule, and candidate. A is more explicit about inapplicable results; B is more precise about the limiting sample time and the absence of mechanism identification. These differences do not justify unequal scores.
- **M1_B**：Both decisions request one unchanged, full 0-to-0.6 s replay of the correctly referenced candidate and saved schedule, directly addressing the evidence's missing independent acceptance check. A frames the test neutrally, whereas B proposes a passing outcome as an explicitly falsifiable hypothesis. Neither claims established success, executable admission, global feasibility or structural infeasibility. Their substantive actions and safeguards are equally well grounded.
- **M1_C**：Both decisions appropriately interpret the evidence as an incomplete, contact-associated numerical diagnostic rather than task success or infeasibility. A addresses explicitly missing qualification and solver-progress information while preserving frozen conditions, although identical diagnostic repetitions may have limited discriminating power. B offers a potentially useful seed contrast, but its 120-iteration request violates the frozen 100-iteration limit, and the supplied evidence does not establish either the prior seed or admission of the proposed initialization. These defects make A the better-grounded action as written.
- **P3_A**：Both decisions reasonably seek fresh full-protocol evidence and preserve known qualification failures as unresolved rather than inventing success. B is preferable because it explicitly intervenes on the two observed direction-associated passive limits and requests the contrasts required by the frozen mechanism evaluator. A's intact replay can address independent qualification but does not, as specified, establish the missing paired-mechanism comparison. This preference concerns scientific design, not assumed executable admission or future outcomes.
- **P3_B**：Both choose the same exact candidate and the same fresh intact-versus-joint-ablation experiment, preserving the frozen task and directly addressing independent acceptance and missing paired-mechanism evidence. Their expected passing outcomes are explicitly testable hypotheses, not invented successes. Both appropriately withhold acceptance for failed or non-comparable executions, although neither fully foregrounds the existing sampled qualification violations or explains the fidelity change. No supplied evidence establishes executable admission of either request, and neither is credited with an executed or passing replay. The scientific actions are equally reasonable.
- **P3_C**：Both choose essentially the same reasonable next action: obtain an authoritative fresh evaluation with the frozen protocol and fuller coverage. Neither invents an observed pass or a strict derivative, and their optimistic predictions are explicitly testable hypotheses. Both nevertheless underemphasize already observed qualification failures and leave execution of the required paired-mechanism contrast unspecified. A's additional threshold detail and B's additional protocol reference do not materially distinguish the scientific quality of their actions.

最值得写入论文的是**按证据类型报告差异和无改善案例**，并说明 Reporter 的价值是否落在机制解释、证据边界或行动选择上。应按以上真实分数和逐条理由报告，不预设 ON 必须更好。两个行动不同本身不是质量提升；行动相同也可能在证据忠实度和限制识别上存在差异。

## P3 完整 Agent 历史节点参照

按用户补充要求，已保存三个节点的完整历史 Main 请求、下一步原始 ResearchDecision/Plan 和实际 Provider 用量，入口为 P3_historical_agent_nodes.csv 与 historical_agent_nodes/。

| 节点 | 历史下一次 Main 输入实测 Token | 输出实测 Token | 历史下一步行动 |
|---|---:|---:|---|
| P3_A | 163,684 | 1,362 | generate / joint_length_redistribution_design |
| P3_B | 169,091 | 1,397 | search / finite joint passive structure performance search |
| P3_C | 195,720 | 1,212 | generate / matched distributed damping intervention |

这些是原 Agent 的完整累积上下文，不是本次受控 ON/OFF 的对照分数。本次是相同数学节点状态的独立重启决策回放，并未恢复整段历史记忆。因此不能直接用历史 Main 输入 Token 减去本次 OFF 代理 Token，声称这是关闭 Reporter 节约的量。

## 成本与 Token 口径

每个 Main Session 实际获得一次完整模型响应。首批十二次原接口请求因本地 Gateway 不支持 tools/reasoning_effort，在入口检查阶段被明确 400 拒绝，未进入上游推理；拒绝记录保留且计入各 Session 四次发送上限。修正后每 Session 共两次发送（一次拒绝、一次推理），累计 Main 发送 24 次、成功 Main 推理 12 次。另有独立盲评 6 次，Reporter 新生成 0 次，已复用报告 6 份。

当前网关不返回 usage，Main/评审模型实测输入/输出及实际总 Token 记为 null，**不是零**。本地使用 tiktoken 0.12.0 / o200k_base 统一计数可见文本，尚无该模型精确 tokenizer、聊天 framing 或隐藏推理用量的验证；因此只作为上下文和可见输出的代理指标。ON 可见上下文增量均值 **1450.5**、中位数 **1626.0**；含报告阅读开销。

复用的六份已完成 Reporter 报告均由历史 gpt-5.6-sol、medium 配置生成（历史传输包含 API 和 Gateway）。历史生成用量另列：输入 540,933、输出 5,891 Token。本次无新增生成费用，不意味着从零部署 Reporter 免费；历史完成请求用量也不等于所有历史失败尝试成本。token_costs.csv 同时保留实际值缺失、代理计数、报告历史生成用量和墙钟，未混为一个精确总账。墙钟单次测量含服务/网络波动，不做速度优劣的统计推论。

## 执行口径与限制

Main 均为 gpt-5.6-sol、相同当前网关默认推理设置（具体档位不可见，不能声称 medium）、相同原始 JSON、候选、冻结任务、证据权限、文本化工具 Schema 和四次发送预算。ON 仅追加匹配报告的 interpretations。成对原始请求已核对共同前缀完全一致。前一 Session 输出未进入后一 Session。

当前网关只提供文本，返回的工具请求按现有 Core Plan/ResearchDecision、EvidenceQuery 校验；这是最小决策回放入口，不是已恢复生产 native function-call Harness。记录了下一步请求但未测试其任务专属执行 admission。M1 A 是局部控制系数响应，P3 A 是有限尺度对照而非严格梯度，结论应保留这些证据类型限制。

独立评审配置在确认已连接模型目录有 gpt-6-astra 后为本实验建立，复用现有网关，未新增科研 Agent/Planner 或修改生产 Main、Reporter、Harness。它与 Main 模型不同，所有匿名材料也保留人工复核入口。

实验已在六组完成后停止；未启动 Knowledge/Skill 或 Context 消融，未改动原主实验结果。
