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
