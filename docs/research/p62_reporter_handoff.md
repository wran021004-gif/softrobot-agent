# P6.2：真实 Reporter 与 Main Handoff 审计

2026-10-29。两组有限真实验证已经完成，**整体尚未达到“可信 Reporter 可替代 Main 阅读”的完整验收标准**。传输和交接成功不等于科学解释正确。

| 验收层次 | Gateway `gpt-5.6-luna` | 官方 API `gpt-5.4-mini` |
|---|---|---|
| Reporter 真实调查 | **PARTIAL**：来源可恢复，但物理比较方向自相矛盾、混淆指标 | **PARTIAL**：主要数值正确，但混淆有效失败与无效、目标残差与平衡残差 |
| Handoff 语义连续性 | **PASS**：5 次真实反馈边界交接 | **PASS（修复后）**：1 次完成边界、5 次反馈边界交接 |
| 真实 Main 跨会话接续 | **PARTIAL**：成功委托调查，随后重复调查、无支持诊断 | **PARTIAL**：恢复历史并保留谨慎结论，但接续中 4 次错误引用报告 |

PASS 的范围是本次实际状态及边界；已读 Knowledge 正文的真实模型跨会话使用没有覆盖，只由离线测试覆盖。没有证明交互效率提升，也没有新可行结构或物理成功结论。

## 身份、条件与隔离

- P6.1 基线及核对的远程 HEAD：`7a2287325a882cb70b933d3ea07db909c58237f2`。
- 独立分支：[codex/p6-2-reporter-handoff](https://github.com/wran021004-gif/softrobot-agent/tree/codex/p6-2-reporter-handoff)，不合并主线。
- Luna 执行绑定 `55424df13`；Mini 初始绑定 `b900fd382`，在真实局部故障后绑定修复提交 [`f690125262a2e5288b6623f9265d1446101b3b93`](https://github.com/wran021004-gif/softrobot-agent/commit/f690125262a2e5288b6623f9265d1446101b3b93)。最终交付身份记录在同目录 `p62_delivery.json`；它指向包含本审计、最终机器记录及全部实现的提交，随后仅增加交付清单。
- 两个角色在各组内使用同一模型，均 `reasoning=none`。Gateway 响应模型为 `gpt-5.6-luna`；官方 API 的响应模型为 `gpt-5.4-mini-2026-03-17`。
- 各组独立上限都是总请求 10、Main 7、Reporter 3；用户追加授权官方 API 同条件组。失败发送也计费；没有自动网络重试、模型切换、补充额度或重建 Study 规避计数。
- 相同 reach/hold 来源、问题、角色规则、执行指令、工具接口和科学预算；`research_information_flow_v1`、`recent_round_trace_v1`、`research_roles_v3` 沿用现有实现。Main 合法动作仅调查/诊断/停止；数学、物理、NMPC、RL 全部为零。
- 两组初始 Reporter 问题只含 question + references，未人工预填 selected_reads。既有 Reporter 选择读取，建立 result_card/source_catalog，再调用模型；显式调查及自动报告共用 `reporter.investigate` / `complete_reports`，没有另建解释器。
- 原始证据以原 ID 复制 75 个传递依赖到隔离 Store，缺失数 0；仅为历史背景 `scoped_context`，当前研究验收信用为 0。未复制原执行所有者会话，因此隔离环境的部分 `ControlEvidence.resolve` 控制诊断不可用；不能据此宣称原研究缺失控制记录。运动采样可通过 motion 引用读取。

隔离目录为 `D:/softrobot-agent/.worktrees/p6-2-reporter-handoff/runs/research/p62-{luna,mini}-20261029`。原始 Provider wire、响应、SDK 快照及回执留在忽略目录；受版本控制的精简导出为 [Luna](p62_luna_results.json) 和 [Mini](p62_mini_results.json)，保留请求/响应引用、原模型调用、精确回执、原报告和账本，不导出凭据或不透明 reasoning。

## 原始案例和数值真值

来源是同一个封存 Study `s142-reach-hold-coldstart-20261023`，Store 位于 `D:/softrobot-agent/.worktrees/s142-reach-hold-autonomous/runs/research/s142-reach-hold-coldstart-20261023/platform.sqlite`。前后 SHA-256 均为 `bfc920b67e7c3f42795b408bc9a452210e4e78abff67ab06e76229883de8a581`；原 STOP、证据及预算未改。

| 身份 | 原始 artifact_id |
|---|---|
| 数学结果 | `912261925382c2402ab66c5ee01c975c58b51b54122ab02011e61e5964f08e36` |
| 第一列变体物理结果 | `e2a6f6f0dae49cf4f8f562e93d5233e2a96758a0cf8b99eee6b001ba515911bb` |
| 第二列基线物理结果 | `a54a68d40c9b65f32aa6b75422ce2db5e9c2afa6aa914fe577db0fc93ce1ea1b` |
| 数学/基线候选 | `dbb5a00a98ed74adf0aa42f571534421902536203c57d2bdbd47038fe1e67baf` |
| 变体候选 | `c0f655d12a96b93f59a9fcbd0a1b99dadf37cbe811b014d0e1088e70ba637516` |
| 原任务 | `2b26edb492214c426263441b6adb52d7aafe41a828436d6b48a1171374a1026c` |

目标为 world `[0.29, 0.035, 0.19] m`，时域 0.35 s；控制/采样步长 0.01 s，物理积分步长 0.0005 s。保持窗 0.30–0.35 s（含端点 6 样本），位置误差 ≤0.01 m，速度 ≤0.02 m/s。结构和控制同时变化，允许描述性分量对照，不能单因素归因；新 Study 的兼容性 reference candidate 不是历史候选验收结果。

数学结果使用局部 structural-linear GVS 仿射模型，12 广义坐标/24 状态、exact ZOH、张力 0–8 N。SLSQP 100 次迭代到达上限，status=9、success=false；101 次目标/102 次约束评估，18.24707129993476 s。宿主计算返回并不表示优化收敛。结论是 inconclusive，没有可行 witness 或排除证书。

- 最大保持速度出现在 0.33 s：`0.02000489088519356 m/s`，超限 `4.890885193561262e-6 m/s`。
- **不只有速度超限**：0.30 s 保持位置误差 `0.010000056805892363 m`，超过位置界 `5.68058923632736e-8 m`。
- 初始 `0.053749418601506754 m` 是到任务目标的距离残差，不能称为平衡残差；`static_equilibrium=false` 是另一个事实。
- 离散局部模型不证明连续时间合规、非线性全局可行/不可行或物理验收。

| 物理测量 | 第二列基线 | 第一列变体 | 变体 − 基线 |
|---|---:|---:|---:|
| 终点位置误差 m | 0.0031364418844500026 | 0.0027808380549602055 | −0.00035560382948979707 |
| 保持最大位置误差 m | 0.0031364418844500026 | 0.0030310250356348953 | −0.00010541684881510728 |
| 保持最大速度 m/s | 0.022849089710631265 | 0.05203049356582944 | +0.029181403855198178 |

物理评价均为 **valid_failure**：完整采样、force_bounds=0 N、solver_errors=0，位置通过、保持速度失败（峰值均在 0.35 s）。变体位置略好、速度更差。配置 `termination=[duration,numerical_failure]` 表示终止条件列表，不是已发生 numerical_failure。

## Reporter 输出核对

两组数学及物理初始 source_catalog 分别为 17、34 项；Luna 后续综合调查为 50 项，所有实际模型报告的 source_catalog 指针均可恢复。模型 `source_ids` 通过既有解析校验，导出保存解析后的原始引用。格式和来源合法不能保证句子含义正确。

Luna 数学报告正确区分求解失败与不可行，给出实际单位、时刻及限制，但将初始目标残差紧接“非静态平衡”叙述，容易混淆。物理报告首段数值大部分正确，却把变体终点误差当作终点/保持共同值；末段明确写成第一列“better holding speed but worse terminal and holding position”，与原证据及它自己的首段相反。它还把配置终止条件当成实际终止状态。后续综合报告修正物理方向，但宣称数学“only”速度约束失败，漏掉实际微小位置超限。不能把该后续报告当作重试修复原报告。

Mini 数学报告正确保留求解状态及速度数值，但明确将目标距离称为“offset from equilibrium”，且把 0.33 s 的保持速度称为 terminal/holding speed。物理报告主要数值及增量正确，文字一面写“improved ... unfavorable ... worsened”，末尾又写“holding-speed improvement”；并把两个有效但不通过的评价称为“both runs remain invalid”。这些是科学含义错误/歧义，不是证据损坏。两组都保留竞争解释和未决问题，未产生新梯度、新求解或伪造成功证书。

Luna 第四份报告因额度耗尽标记 `unavailable / REPORTER_SKIPPED_TO_PRESERVE_CLOSEOUT`，确定性事实仍在，没有真实 Reporter 发送。模型语义错误未通过人工改写原报告或额外重试掩盖。

## 实际 Main 行为及每次工具往返

每个 Main 响应均提交一个真实工具调用；两组各 7 次公共工具往返。HTTP 200 表示 Provider 接纳了请求 Schema，宿主随后独立校验参数及证据资格。

| Main 次序 | Luna | Mini |
|---|---|---|
| 1 | diagnose 路由成功，仅选择 Schema | 自主 STOP 成功，以三项原科研引用谨慎结束 |
| 2 | diagnose 被拒：缺 selected_candidate | 附加交接窗口 research_recall 成功，恢复原 STOP |
| 3 | experience_retrieve 成功，未送达 Knowledge 正文 | STOP 被拒：UNREGISTERED_RESEARCH_EVIDENCE |
| 4 | research_investigate 成功，实际触发第三次 Reporter | 同一证据资格错误再次拒绝 |
| 5 | evidence_read(full) 读取整份综合报告成功 | 同一错误第三次拒绝 |
| 6 | 只读 diagnose 执行成功；sources=[]，推断 unsupported | stop 路由成功，仅选择 Schema |
| 7 | 再次综合调查；仅确定性报告，无 Reporter 额度 | 仍含 Reporter 引用，第四次拒绝 |

Luna 第 6 次不是工具拒绝：它完成 read_only_diagnosis，但 `read_only_synthesis` 未获科学推断支持，且没有数值诊断来源。Luna 有一次有效 Main 委托调查（1 Main + 1 Reporter 往返）；后续大报告读取和重叠问题未显示节省上下文。纯路由 1、参数拒绝 1、无支持诊断 1、重复综合调查 1；没有重复科学执行。

Mini 的自然轨迹在 Main 第 1 次就结束，不能把这个 STOP 称为“交接后成功”。为完成用户授权的跨会话验证，操作者使用既有非成功 STOP continuation，在**同一账本**中追加只读验证窗口；原 STOP 及完整前状态保留，授权依据和事件在机器导出的 `operator_events` 中。这里没有声称用户在 STOP 后发过新指令，也没有增加预算。第 2–7 次须单列为附加轨迹。其同模型工具接续 admission 依据是既有官方 Mini P5 Store 的 6 份 HTTP 200 原生工具反馈 wire，仅用于传输准入，不转移科研结论。

Mini 在精确收到拒绝反馈后，仍反复引用 Reporter 报告作为原始已注册研究证据，没有按反馈查询 `/citation_eligibility`。叙述大体保持“物理速度失败、全局可行性未决”，但也沿用“相同候选”等不够精确的表述。回忆成功不能替代合法科研决策。附加轨迹纯路由 1、历史读取 1、被拒 STOP 4，没有成功后续 STOP。总消耗 9，Main 角色额度达到 7，保留未用 Reporter 1 次；最终为操作者工程收口，不伪造模型 STOP。

## Handoff：权威状态到实际新 wire

Luna 交接事件序号为 61/79/107/124/144，对应新请求 64/82/111/127/147。Mini 为 49/70/89/107/126/143，对应 53/73/92/110/129/146；49 是 completed_invocation，其余为 request_feedback。

| 检查 | 观察 |
|---|---|
| Frozen Study、候选及科学状态 | 现有 state_identity 校验全部权威状态，独立恢复 SDK 快照；历史 scoped_context 3 引用保持 |
| 目标、Focus、verified_facts、Trace、Knowledge、Reporter、Budget | 从交接 source_state 和当时事件/预算重建 L0，与实际新请求逐字段相等，11/11 |
| 工具反馈及配对 | 边界 toolUse/toolResult 无未匹配项；10 个反馈边界的 pending_feedback 与实际 wire 精确相等 |
| 工具选择与 Schema | selected/loaded 状态保留；实际请求载荷保存 schema_names，Provider 均 HTTP 200 |
| 历史与预算 | 新 wire 不携带旧原生 tool_calls/tool 消息；累计请求未重置；没有重启科学 Worker |
| Knowledge 局限 | 实际没有已读正文送达，空状态一致；正文保持只由离线真实 SDK + Mock HTTP 测试覆盖 |

不能机械要求所有表示字节相等：settled feedback 从 recent 投影为 pending_feedback；Mini 首次完成边界还包含上一个请求后才结算的 STOP，所以与旧 L0 的 Trace 等不相等是预期。机器导出的 `authoritative_snapshot_to_actual_wire` 才是同一时刻的权威对照；`actual_wire_field_equality` 保留旧 wire 对照，未删掉这些差异。

两组最终无 pending Provider、无未消费响应、无科学 pending。最后一次工具回执已落 Store，但因结束窗口没有再发送给下一次模型；不将其计为后续交付成功。

## 实耗与比较限制

所有 19 次实际 HTTP 请求均为 200；没有 Provider 格式拒绝或截断。宿主工具校验错误照常消耗 Main 请求。以下 tokens 全部是 Provider 实际返回值，缓存是输入 tokens 的子集，不额外相加。

| 组/角色 | 请求 | 输入 tokens | 输出 tokens | 总 tokens | 缓存输入 tokens |
|---|---:|---:|---:|---:|---:|
| Luna Main | 7 | 187471 | 1517 | 188988 | 0 |
| Luna Reporter | 3 | 191341 | 2349 | 193690 | 0 |
| Luna 合计 | 10 | 378812 | 3866 | 382678 | 0 |
| Mini Main | 7 | 80028 | 2918 | 82946 | 20992 |
| Mini Reporter | 2 | 88886 | 1253 | 90139 | 0 |
| Mini 合计 | 9 | 168914 | 4171 | 173085 | 20992 |

实际金额未由回执报告，记为 unknown；没有把估算金额当账单。Luna/Mini 工具计数均 7，数学/physics/backend/worker/RL 均 0。初始两次 Reporter 输入 tokens 在两组分别都是 35247 和 53639，输入字节有模型标识长度差异（Luna 122478/192699；Mini 122492/192713）。Reporter 提供现成事实，但实际仍发送大量底层 JSON；不能仅凭最终文本紧凑就宣称省 tokens。

Luna 整份报告读取后下一次 Main 输入达 474823 bytes / 116228 tokens。Mini 没有 Main evidence_read，但 4 次同类引用拒绝增加开销。两组没有绕过 Reporter 的对照臂，无法计算它避免的读取数。模型/provider 不同、自然停止长度不同、Mini 附加 continuation 和中途最小修复均是比较限制；总 tokens 较少不证明 Mini 能力或效率更好。

## 最小修复、验证与复查入口

1. 基线 `test_request_boundary_handoff` 仍按旧顶层 `allOf` 访问新 Schema；在 P6.1 基线也复现 KeyError。仅修正两处测试路径到 `parameters.then.allOf`，没有修改生产 Schema。
2. Mini 第一次反馈边界的自动 handoff 估算在 HTTP 预留/发送前抛 `TOKEN_HANDOFF_REQUIRES_PINNED_DEEPSEEK_TOKENIZER`。当时实际请求为 4，未发生隐藏发送。用真实 SDK + Mock HTTP、相同 token_handoff_v1 阈值复现失败，再把 `provider_context.handoff_input_estimate` 既有保守 capacity_estimate 路径从 gateway 扩展到官方 openai_api（生产逻辑一行及 docstring）。不引入新 tokenizer、记忆或接续机制；该估算不是实际 token 使用量。修复绑定保留同一账本，随后真实反馈交接成功。

离线验证：信息流/Recent Round/请求边界/Reporter/S129 定向组合 **61/61**；修复后的 P6.2 预算与真实 SDK 官方接续/Provider/OpenAI/请求边界组合 **28/28**。两组合有重叠，不相加成独立测试数。官方回归测试替换了两处 credential 入口，全部 Mock HTTP，无额外真实请求。

重建审计无需 Provider：

```powershell
$env:PYTHONPATH='D:\softrobot-agent\.worktrees\p6-1-research-information-flow\runs\p61-deps;C:\Program Files\MATLAB\R2024a\extern\engines\python\dist'
& D:\softrobot-agent\.mainline5-env\Scripts\python.exe -m tests.research.p62_results_audit --arm luna
& D:\softrobot-agent\.mainline5-env\Scripts\python.exe -m tests.research.p62_results_audit --arm mini
```

审计脚本对原 Store 哈希、导出前后审计 Store 哈希、每次请求 digest/扣费、角色上限及零科学消耗作断言。日志位于 `runs/p62/`，关键文件为 `offline_final.log`、`openai_handoff_before.log`、`openai_handoff_after.log`、`mini_final_window.log`。执行脚本是操作者入口，依赖本机封存 Store，不能把它当作无副作用单元测试重跑。

未解决项是 Reporter 数值语义一致性、Main 对解释/原始证据资格的区分、收到拒绝后的有效纠正，以及大报告展开开销。本轮已完成有界验证与交付；这些失败保留为后续改进依据，没有为取得 PASS 修改提示词再试或扩展到 P6.3。
