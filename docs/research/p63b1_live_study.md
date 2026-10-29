# P6.3-B1：Knowledge-enabled, success-case-accessible

本次从 `codex/p6-3b0-math-study-preparation@ae90e2c2ffe4ef7699aec57204b24c793c42f4eb` 派生独立分支和新 Study。附件明确授权一次真实 B1；随后用户明确将 Provider 上限从 8 调整为 **12**，其他额度保持不变。不启动第二个窗口，不为 Main 指定方法、结构、参数、步长或科研顺序。

- 配置：`configs/research/study_p63b1_m1_traces12.json`。
- Study：`p63b1-m1-traces12-20261029`。
- Resolved identity：`7d3b77c45234e58316bd8d93d6cc34dd6464a6b39e9772c188cfbddde82e9763`。
- Store：本 worktree 的 `runs/research/p63b1-m1-traces12-20261029`，与 B0 Store 分离。
- Provider：原 runtime_p5_luna_none，gpt-5.6-luna，本地 gateway；Main/Reporter reasoning=none。12 次总额包含失败、Reporter 和 1 次 closeout；Public operations=32（含2次保护），共享数学=4，Native 每请求 callbacks≤24、iterations≤3、knots≤4；独立物理/NMPC/RL/Offline NLP/BDF=0。
- Knowledge：enabled，allow_benchmark_answers=true，allowed_kinds=[procedure,success_case]。english_decision_v1，删除 language_policy；role v3、bound v2、information flow、原 Handoff 不变。P3 是原始中文，未翻译或添加人工审核声明。

[必要离线准备记录](p63b1_preflight.json)：九条 success_case 搜索均返回，16 条 procedure 可用；精确抽查 M1 英文和 P3 中文成功。operator_preflight 读取不计为 Main 阅读，正文不在 L0 hint 中。准备时科研候选、控制、数学/物理结果均未导入；旧 B0 Store 未修改。仅做 resolver/prepare 与必要权限检查，未重跑五候选链或 B0 套件。

准备阶段只新增配置与审查材料。完成干净 commit/bind 后，通过原 formal_study_authorization 绑定用户授权、准确 identity、Provider、Knowledge、方法及预算，复用已有真实同模型反馈的 Handoff 准入，使用现有 run 入口、--session-handoff、--max-new-provider-requests 12。

首发请求 `r3-request-87b9e29c71234a9ba26e2e7073cec0d7` 在本地连接层抛出 ConnectError，8787 无监听、无 HTTP/模型响应、无工具或科学执行。用户随后明确指示“请审查这次连接阻断？不计入12次总额，然后重新验证study”。原失败事件和请求保留，通过原 Store.complete(actual_cost=zero()) 结算失败回执，单独记录本次用户豁免；model_calls=0，wall_s=2.058569。12 次上限及冻结 identity 不变，原始 attempted 计数仍含这次失败。

恢复既有 V2 gateway 的进程级代理启动脚本后，GET /v1/models 返回 200，原模型可用；没有 smoke 推理请求。restore-only 复现首轮 ConnectError 后 `SDK_HISTORY_HAS_NO_TRUSTED_STORE_ANCHOR`。仅扩展现有 rejected_initial_request 分支，允许已结算、无响应的初次 ConnectError 在原提示严格匹配时续接；未知 ReadError 等不在该分支。没有新增恢复系统、改写 SDK 历史、重置预算或修改科学准入。新增一项 Mock HTTP 定向测试，覆盖未结算仍阻断、只读恢复不发请求、续接不重复提示及计账；同时复用原初轮 Schema 拒绝恢复测试。

运行结果将以原请求、工具回执、实际数学/资源记录和后续 Main 决策审查，不以 HTTP 200、生成候选或完成计算单独宣称自主科研闭环成功。原始 Store 和凭据留在本地，不提交完整历史 Store或私有环境文件。

## 实际窗口结果与连接审查

本次已完成并停止。配置冻结 identity 未变；准备绑定为 `f6b58fa1110e4135f1a09ba42a1176ceb9385286`，首轮续接修复绑定为 `a9c04d86b8f2589c944060eff19a951680c80cca`。实际使用同一 Store、同一 12 次额度；原始发送尝试 13 次，其中首个本地 ConnectError 按用户明确指示豁免，计入额度 12 次。未启动第二个 Study、补充额度或切换模型。

初次阻断的可证实原因是 8787 无监听，7890 原代理仍有监听。既有 V2 gateway 启动脚本恢复监听后，非推理模型目录检查返回 200、gpt-5.6-luna 可用，随后 11 个真实 Main 请求成功，证明初次本地连接阻断已解除。无法从现有证据确定旧 gateway 进程为何退出。第 12 个计入请求由已连接的 gateway 返回 HTTP 502、`network_error: Could not reach ChatGPT`，与首个本地 ConnectError 不同；保留为计费失败，不作追加豁免或自动重试。现有错误不足以区分代理暂时波动或上游网络问题。

[真实 Store/wire 的有界审查投影](p63b1_live_audit.json) 保存每次请求 ID、时间、原始引用、计账、工具输入及结果状态，并保存首个真实请求、首次 route 后和最后 closeout 的真实 L0 摘要。不是合成 fixture，也不宣称包含完整 wire；完整原始请求/响应留在本地 Store。

| 计入序号 | HTTP | Main 工具行为 | 实际结果 |
| --- | --- | --- | --- |
| 豁免 | 无响应 | 首发连接失败 | ConnectError；0 model_calls；保留原失败和 2.058569s |
| 1 | 200 | experience_retrieve search reach, limit=5 | 搜索成功；只返回目录信息 |
| 2 | 200 | research_route research_plan/generate | 选择入口，未提交 Plan |
| 3 | 200 | experience_retrieve search reach, limit=10 | 搜索成功，扩大目录范围 |
| 4 | 200 | research_route research_plan/generate | 再次选择，未提交 Plan |
| 5 | 200 | experience_retrieve search reach, limit=5 | 重复首次搜索 |
| 6 | 200 | research_route research_plan/generate | 再次选择，未提交 Plan |
| 7 | 200 | experience_retrieve read research-bounded-continuation@2 | 精确读取一条 procedure，未读取 success_case |
| 8 | 200 | evidence_read mathematical_capabilities /research_opportunities | 引用的是 FamilySpace，非自有候选；正确拒绝 OWNED_RESOLVED_CANDIDATE_REQUIRED，未启动 Worker |
| 9 | 200 | research_route evidence_read | 选择读取工具，未完成读取 |
| 10 | 200 | research_route research_plan/generate | 再次选择，未提交 Plan |
| 11 | 200 | research_route research_plan/generate | 再次选择，未提交 Plan |
| 12 | 502 | 无模型输出 | 原 closeout 请求，仅允许 stop；上游 network_error，窗口终止 |

Knowledge 权限维持 enabled + procedure/success_case。准备时九条均被搜索到、冻结 manifest 和本地源存在；只精确抽查了 M1 英文与 P3 原始中文，并未逐条阅读全部九篇正文。这些 operator_preflight 读取不计为 Main 阅读。真实首个请求的 system prompt 明确告知九项 success_case 可用、P3 为原始中文且不自动导入历史候选/控制。Main 本轮只读取上述 procedure，success_case 阅读数为 0；不能宣称它已利用历史成功 Trace。

实际 wire 证明：无候选时 Design/generate 可用，research_plan 的 action=[generate] 及 generation/decision/科研说明字段已进入请求；route 后的 tool_continuation 明确是 selected_not_submitted，Schema 仍在。数学 L0 明确 requires_owned_candidate，并提供候选绑定查询入口。Main 没有提交任何 research_plan，因此没有可审查、可证伪的正式假设、候选、diagnose 或 research_analysis。第 8 次失败是原准入对错误引用的拒绝，不是数学工具未注册或求解器失败。本轮未实际到达合法候选后的数学提交，不能据此证明那条执行链已通过真实 Agent 验证。

实际消耗为 Provider 12/12（11 个 200、1 个 502），public operations 11/32；其中 6 次 route、4 次 Knowledge 操作、1 次证据查询。ledger.wall_s=102.042569，包含首发连接失败的 2.058569s 和 Provider 回执耗时，不等同于完整 Study 墙钟时长。数学 0/4、模型构建/rollout/callbacks/Native 物理积分步/数值耗时均为 0；原因是未发生数学请求，不是将 Native 积分视为免费。独立物理/NMPC/RL/Offline NLP/BDF 均为 0。原 callbacks≤24、iterations≤3、knots≤4 和 Native 实际成本记账语义不变。

Reporter Provider 请求与解释均为 0，没有科研结果可交付；不能报告数学可靠性、收敛/失败/局部割线结论，也没有基于数学证据的后续 Main 决策。Store 原 research_status 仍为 ready、没有 Main STOP 或 SELECT；外部窗口因上限和 API 故障已停止，并添加 supervisor_review 记录，未伪造 Main 科学结论。所有 Provider 回执已结算，无待处理 Provider/科学执行，剩余额度 0。

本轮主要观察是 Main 在入口选择和重复检索之间停留，尽管生成 Schema 与选择状态已在真实请求中交付；这支持“本次工具使用未转化为科研提交”，不支持对所有模型或 Handoff 压缩影响的普遍归因。末次 502 又使真实 STOP 收尾未验证。没有发生数值求解失败，也不能把这一轮归因为 T1/T2 算不动。应先审查已保存的 route/检索行为与信息负担、确认 gateway 稳定性，再决定是否单独授权后续实验；现有证据不支持直接扩大为完整 M1 Study，单纯增加请求数也没有已验证的收益。后续仍应由 Main 自主选题，不改成固定路线。

最小修改：新增独立 Study 配置、准备与真实审查 JSON/本文；session_handoff.py 只修复首个已结算 ConnectError 的原提示续接；新增一项定向 Mock HTTP 测试并复用一项 Schema 拒绝续接测试，两项均通过。未改 Agent、Knowledge、Reporter、Store、FamilySpace 或数学内核，未运行大型回归。至此停止，不自动启动其他 Benchmark 或请求。
