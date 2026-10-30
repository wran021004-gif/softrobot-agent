# P6.3-F0/F1/F2：结果反馈修复与连续自主科研真实验证

本轮完成了只读归因、最小反馈修复和一个真实 F2 Study。F0/F1 通过；F2 实际发送 **11/20** 次 Provider 请求，观察到 Main 从数学结果自主形成 H2 并执行独立物理 Replay。随后完整结果读取使待发送请求超过原网关的 1 MiB 上限，尚未发送第 12 次请求即中断。因此 **A1/A2 通过；A3 有明确部分证据，但完整多结果更新闭环未通过验收**。这次中断不是数学额度耗尽，也不是再次出现六次重复索引循环。

机器审计：[p63f2_live_audit.json](p63f2_live_audit.json)。前置复盘：[F0](p63f0_feedback_audit.md)；修复和离线验收：[F1](p63f1_result_feedback.md)。本报告只陈述保存的原始 Plan、工具回执、数值证据和实际 Provider wire，不推断模型内部理解或推理。

## 冻结条件和所有权

- 分支：`codex/p6-3c4-result-feedback-validation`，基于已发布 C3 `f49014880525bfb510499050c4cb829a2dbb0567`。
- 本次真实代码 freeze：`835ab4fe376e6e975661dd699871aa65db0c2cbd`。F2 开始后没有修改源码、提示、配置、工具状态或科学问题。
- 唯一新 Study：`p63f2-m3-result-feedback-sol-20261030`；原 Store 位于本 worktree 的 `runs/research/<Study>/platform.sqlite`。
- Main 与 Reporter 均为原 `gpt-5.6-sol / none`；未切换模型、开启 Thinking 或新增 Agent。
- 0.50 s 原 Reach/Hold、最后 0.05 s 保持、位置 0.01 m、速度 0.02 m/s、控制/采样 0.01 s、积分步长 0.0005 s、目标 `[0.29,-0.035,0.19] m`，原零初态、环境和张力边界均保持。
- 配置核对与准备时十项有效值比较全部相等：canonical task、protocol、family、robot structure、task、seed、backend、dynamics model、discretization、controller。仍为原两段六腱、每段 12 cells 的起点。
- Operator 通过原 generator 和 `initialize_control` baseline 准备初始结构和完整输入序列；二者未验收，不能记作 Main 决策或成功证据。没有导入 C3 科学结果。

初始候选 `bde5f590e49e828fbf650f8509657d1ba9a249c67a46e32fec7da11646fdb3ee`；初始 source `a82fb459ece8259c8424046e105a3d36789e4e559a20741936f4803e2222216e`。原授权、环境检查、干净代码绑定与 request-feedback handoff 准入均已记录。首次发送前账本模型/数学/物理操作均为 0。

Provider 总上限 20，含 Reporter、失败发送和保护收尾；保留原 1 次 Provider 收尾预留。必填 public/math/backend/local/NLP/BDF 额度均为 1,000,000；可省略的额外 Replay/训练 action 上限为空，科学时间额度为空。原科学操作、四个特殊数学方法、独立 Replay、结构/控制搜索、GVS/mechanics、NMPC、PPO 均授权；实际执行仍遵守原模型、来源、适用性和环境条件。没有把 PHS/P3 伪装为可执行工具。

Native Study 上限为合同最高的 1000 callbacks、100 iterations、4 knots；混合结构搜索使用原 schema 最高的每请求 128 proposals/evaluations；RL training stage 上限 10 是原 schema 技术约束。原 C2 adapter 的可表达语义及 solver defaults 保留。特别是本次 ScientificQuestion 选择了 `pattern` 和 1000 callbacks，但原编译默认 `iterations=16`，实际以 `iteration_limit` 结束；并未撞到 1000 回调或数学 Study 额度。不能把授权充足说成修改过求解器或无限搜索。

## 实际请求和行动

以下编号包括 Reporter。每次实际工具/Schema、wire/response/feedback 引用、所见预算与结果/Reporter 交付情况均保存在机器审计的 `requests`。

| 请求 | 角色与自主动作 | 结果和新增信息 |
|---:|---|---|
| 1 | Main：`experience_retrieve` search | 程序性知识查询，未算科学证据 |
| 2 | Main：diagnose，提出 H1 | 假设初始控制序列满足全部冻结阈值，记录候选、可反驳观察和固定条件 |
| 3 | Main：ScientificQuestion `control_feasibility`，full_task，pattern，requested_budget=1000 | 原 Native T1 实际 computed；84 callbacks，1 个数学结果 |
| 4 | Reporter | 原保存解释 available，3 段来源关联解释 |
| 5 | Main：读取 `/control_result_links/1` 的 source 等字段 | 实际获得固定数值、结果后交接及完整 Reporter 解释，并查询优化序列来源；没有读旧索引循环 |
| 6 | Main：`research_route` 切换 physical_replay | 仅选择工具，未算科学执行 |
| 7 | Main：提交 H2 的 physical_replay Plan | 自主预期优化序列仍失败，说明模型样本与独立验收的区别，并用原数学结果支持独立验证；实际完成 1 次完整物理 Replay |
| 8 | Reporter | 对独立结果的解释 available；下一 Main 获得解释与固定验收事实 |
| 9 | Main：`view=full` 读取 `/all_fresh_results` | 使用了错误 view；原工具拒绝，未启动科学执行，费用保留 |
| 10 | Main：自行改为 `view=working_set` | 首次成功获得包含数学、独立物理两项结果的完整索引；没有禁止重读或替 Main 决策 |
| 11 | Main：同一响应内请求两份结果的 root full read | 工具分别返回完整正文并保存；后续待发送请求过大，正文没有实际进入新的 Provider wire，不能记作已确认全量交付 |

Main 的正式后续科学决策最早是 **第 7 次请求**；更早第 5 次已开始有针对性的证据读取。数学结果后新 Plan **1** 个；有效完成的科研行动合计 **2** 个（1 次数学 + 1 次独立物理），其中后续科学执行 1 个。两次 `/all_fresh_results` 尝试中，1 次因 view 错误失败、1 次成功；**同一有效索引 exact_repeat=0**。

首次数学结果实际进入 Main 5 的 `mathematical_research.latest_result`；`analysis_handoff.status=result_completed`，以 `post_result_decision` 交接。相同固定视图随后保持可见。Reporter 4 的三段完整 kind/text/sources 在 Main 5–7 与保存内容一致；Reporter 8 的三段完整解释在 Main 9–11 一致。Reporter 并非新的 Plan 执行者。

H1 提出的是“初始序列的独立验收”，实际第 3 次执行的是“有限控制重优化”；第 7 次回放又使用优化后的序列。这是不同实验，不能把优化序列的独立失败无条件写成初始序列已经接受了同一项独立反证。Main 的显式 H2 正确限定在优化序列；其解释中回指原 pass hypothesis 的措辞仍需注意这一来源差别。

## 数值结果和证据强度

原数学结果：`c8972bd16a75b3977e9779147587fbeb7c2573c2015c025e3de9881814ae044f`。输出控制 source：`2ee67580fd12b1307b4d77c7e3356b1b36f1f8b35906297a253293ca2ba9cec5`。独立物理结果：`07e6ca56b47c67a65e3ff785bfe8de5b75c025066354aba8c7e0959345096e88`。

| 指标 | 初始模型样本 | best-found 模型样本 | 独立 Replay | 冻结阈值 |
|---|---:|---:|---:|---:|
| J，dimensionless | 20.45175494 | 14.97747027 | 不作为独立验收分数替代 | ≤0 为该模型样本约束可行 |
| 终点位置误差 m | 0.11142702 | 0.15160972 | 0.15160972 | 0.01 |
| 保持最大位置误差 m | 0.12531739 | 0.15977470 | 0.15977470 | 0.01 |
| 保持最大速度 m/s | 0.42903510 | 0.31377399 | 0.31377399 | 0.02 |

J 改善 **5.47428467**，速度下降但两项位置误差变差，最坏约束由速度切换为保持位置。三项仍全部违规。独立 Replay 的原 evaluator/acceptance 为 **valid_failure / accepted=false**；执行完整、无 solver error、张力边界通过，故不是数值失败伪装成任务失败。

这仍未建立收敛、全局最优、结构不可行、硬件性能、稳健性或连续时间保证。两次使用相同 MuJoCo 动力学，数值相等不等于跨模型泛化。`completed_response_steps=0` 在这里是 **pattern 不执行 response proposal** 的结果，不能照搬 C3 的“response 部分探测不足”解释。本次未发现 passing control，也没有 SELECT 或 Benchmark 成功。

## 真实接口阻断和停止边界

第 11 次请求后，原严格 root-full 读取返回物理正文 **34,494 UTF-8 bytes** 和数学正文 **1,013,814 bytes**。最新保存的 Research Packet 单独按 Provider 原序列化方式已为 **1,077,843 bytes**，大于冻结 `max_request_bytes=1,048,576`；HTTP 格式还需要工具和消息封装。该 packet 引用为 `e09b225fc85075db5fc01e198a51cded4edeb5e3d558a48d1de93ad04d49d811`。

原 `provider_context.capacity_estimate()` 抛出 `GATEWAY_REQUEST_BODY_TOO_LARGE`，外层 SDK 包装成 `openai.APIConnectionError`。该检查发生在 reservation 和实际 send 之前：没有第 12 个 `r3_request`，没有第 12 次计费，11 次已发送请求全部 HTTP 200。这里给出的 packet 大小不是伪称已保存的精确失败 HTTP wire；原始异常证明实际格式化请求越过了该上限。

没有修改本轮冻结配置、压缩或替换 Main 请求的精确正文、伪造读完状态、绕过网关上限、向模型插入新提示，或为追求成功重开 Study。相同未变的待发送内容会再次触发确定性检查，因此不做无信息重试。原 CLI exit=1，日志与旁路审计文件保留于 ignored `runs/`。这是真实接口故障，按任务约定提前结束监督窗口，Provider 尚余 9。

`read_coverage` 只确认工作集 source/index 已进入实际 wire；最后两份完整正文均为 `not_confirmed_in_provider_request`，`full_artifact=false`。原本地 `evaluation_reads` marker 已在工具返回时写入，但原 SELECT 同时要求实际 wire 的 complete-read coverage；不能单凭 marker 宣称取得正式阅读资格。未调用 SELECT，也没有把索引阅读升级成完整科学读取。

最后 Store `research_status=ready`，并未伪造 Main STOP。科学 pending、unconsumed response 和未封口 calls 均为空，两个 Worker 均 returncode=0、termination_confirmed。待交付的正文和原会话仍保存；没有后台继续运行的新 Study 或模型请求。

## 实际费用

| 项目 | 原记录 |
|---|---:|
| Provider：Main / Reporter / 总量 | 9 / 2 / 11，授权上限 20 |
| 实际失败发送 / pre-send 拒绝 | 0 / 1 |
| public operations / backend launches | 10 / 1 |
| prompt / completion / total tokens | 131337 / 3170 / 134507 |
| usage.reasoning_tokens / 金额 | 0 / 未知，不按 tokens 推算 |
| Provider elapsed 合计 / ledger.wall_s | 168.862 / 179.9728214 s |
| 正式数学评价 / 实际数学 Worker | 1 / 1 |
| Native 数学 model builds / rollouts / callbacks | 1 / 84 / 84 |
| Native 数学 physics steps / attempted steps | 84000 / 84000 |
| Native 数学 forward evaluations / kernel wall | 8485 / 8.8586300 s |
| 数学 Worker charged numerical_s | 9.9245505 s |
| 独立 Replay model builds / rollouts / physics steps | 1 / 1 / 1000 |
| 独立 Replay forward evaluations / kernel wall | 101 / 0.2571159 s |
| 独立 Replay charged wall | 1.1862709 s |
| 原 numerical_s / construction_numerical_s | 11.6067325 / 0.3580203 s |
| NMPC / PPO / T2 新计算 / 新结构搜索 | 均未选择，实际 0 |

总计两类执行为 85 rollouts、85,000 physics steps；其费用分别来自数学 Worker 与独立 backend receipt。Kernel 时间包含在 Worker 时间内，不重复相加。原 ledger.worker_calls=0 是账本分类，并不表示没有真实 Worker。科学时间和构造时间遵循原状态口径，不强行与 Provider elapsed 相加制造新费用定义。

## A1/A2/A3 与 C3 对照

| 能力 | 判定 | 依据与边界 |
|---|---|---|
| A1 科学问题提出 | 通过 | Main 自主提出可检验 H1，绑定对象、条件、阈值和反驳观察；上述初始/优化序列语义差别单独保留 |
| A2 合法科学行动 | 通过 | 原 T1 computed，随后原独立 Replay evaluated；真实结果与费用均保存，任务本身未通过 |
| A3 结果后自主决策 | 未完整通过，已观察到部分能力 | Main 自主提出 H2、解释独立验证理由并执行后续 Plan；第二结果后只观察到证据查询，尚无显式再更新、新 Plan 或合理 STOP，下一次 Main 请求已被接口阻断 |

相比 C3，结果后新 Plan 从 0 到 1，同一有效索引重复从 5 次 exact_repeat 到 0，且出现独立物理验证。不能据此宣称 F1 单独造成改善：本轮同时开放此前为 0 的物理与其他科学能力、提高科学额度、将 Provider 上限由 12 改为 20，Main 又自主选用 pattern 而非 C3 response，实际回调 84 而非 8。J 的变化也受这些条件影响，位置指标并未改善。

本次支持“在这些条件下，Main 能从第一次数学结果形成并执行一项自主后续研究”；不支持普遍连续自主科研能力，也不支持第二结果后模型停滞或能力不足的归因。A3 不因 Reporter 的建议、Operator 准备或框架中止而自动通过。

剩余的明确工程问题是大规模精确 root-full 证据与原网关请求体积契约的冲突；本轮只记录，不进行运行后提示调优或扩建。未来需要在保留原完整阅读/SELECT 语义的前提下单独处理该接口问题；若再比较 Main Thinking，应预先冻结同一反馈、任务与预算条件，不能把本次工程中断当成更换推理模式的因果证据。本轮到此停止，不扩充 Provider、不自动开第二 Study、不合并到任何基线分支。
