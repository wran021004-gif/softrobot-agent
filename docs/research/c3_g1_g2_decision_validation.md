# C3 G1/G2：每轮 Plan 通过，首次读取验证仍有混杂，科学判断未通过

2026-10-25，Asia/Shanghai。开发基线
`fix/c3-feedback-math-decision@5e5f6532406eb7616f8da2d8984d74ba3f63f9af`；
独立分支 `fix/c3-g1-g2-decision-validation`，独立工作树
`D:/softrobot-agent/.worktrees/c3-g1-g2-decision-validation`。

**每轮新 Plan 实测通过；跨会话没有重读，但收尾 Schema 存在混杂，不能认定首次读取验收通过。
G1 的有效科研判断修订也未通过。
遵照用户的前置门槛，G2 未启动，未追加修复请求。此次没有证明真实数学科研决策闭环。**

## 修复、授权与隔离

开始时核对了远端指定基线、当前分支、所有 worktree 的位置/HEAD/分支与已跟踪改动。
主工作树在 `feat/gvs-dynamics@d629a80d0027209ef6d41d65fdb69b168727bff7`，
有大量既存未跟踪环境和 runs 文件；保留原样。其他树未见已跟踪改动，未清理它们。
本分支从指定基线建立；未改旧 C3、A/B、F1/F2 Study 的配置、账本、证据或 STOP。

修改仅在测试/验证入口，**生产代码变动 0 行**：

- `c3_f1_f2_validation.py`：启动要求按整个 Study 的 `read_state` 和
  `pending_feedback_delivery` 判断，已完成并交付/随本包交付时继续判断；保留有科学目的的复核。
  参数化既有授权、冻结、导出及实验身份，原 F1/F2 默认身份保留。
  最终审阅后另把摘录登记为原 `scoped_context`，让未来收尾阶段也可读取原引用；此补丁本次未重发验证。
- `agent_math_decision_probe.py`：系统指令与本轮用户包都要求每个 evaluation turn
  提交一个新 Plan；包中带 turn_id、轮次、上一 Plan 工具 ID、当前问题和第二轮观察。
  上一轮完整 Plan 与原 response/reasoning 继续保留。复用正式 Host 的账本作为可选入口。
- `c3_g1_g2_validation.py`：本任务的有限验证及原结果只读审阅；没有新的科研 Agent、求解器或证据系统。
- `test_c3_g1_g2.py`：两项离线协议回归。

用户附件 `b47b5887-0227-426f-9031-13cbb0fdda25/已粘贴的文本.txt` 的明确授权，
经原 `formal_study_authorization`、resolved_identity/scope_identity、`require_authorization`
与 `core.bind` 登记；没有绕过准入开关。新 Study 分别是
`c3-g1-continuity-20261025`（Provider 上限 2，数学 0）和
`c3-g1-decisions-20261025`（Provider 上限 4，数学 0）。两者物理/NMPC/PPO 均为 0。
决策 Study 冻结源码 `fccc8b245571a7b6edeb6489b68642a42b8505bc`，连续性 Study 冻结源码
`ae91c6b013a2595c5ba9fedf5f26e8b0e3e1fa3b`。连续性配置中的旧 base_commit 标签沿用原验证配置，
不代表执行了旧源码；本分支祖先和 `implementation_binding` 是实际代码身份。

Provider/model/thinking/reasoning/max_tokens 均沿用原配置，`tool_choice=auto`，自动重试 0。
决策对照只校验原生产 `Plan` / `ResearchDecision`，不派发其机器人提案。
每轮 JSON 的通过不等于该提案已通过候选所有权、科学执行或费用准入。

## G1.1：原反馈交付、已读状态与恢复

复用原 F1 的同一历史事实摘录和查询，artifact
`7a1ff0ae028c832f292eb475d6c11bb0c534dcd2dc03476d4a7edcdf8144e146`。
其原来源仍为 B Study 的 `ead9bd6e…474f`，候选 `e0f2ccf5…5ac1d`。
旧 F1 的重读失败永久保留；新验证没有覆盖它。

| 项目 | 实测 |
|---|---|
| 真实请求/响应 | 2/2，全部结算 |
| evidence_read | 1 次成功，公共调用收据已结算 |
| 真实 request-feedback Handoff | 提交并核验成功 |
| 第二请求 wire | 原工具 ID、查询、success、完整反馈逐值匹配原反馈 |
| wire 大小/消息数 | 41,683 bytes / 3；42,979 bytes / 4 |
| 已读状态 | 第二包 completed_reads=1，原查询/内容身份存在 |
| 第二请求重复读取 | 0；模型明确使用已完成读取和当前 pending 反馈 |
| 原查询在第二次 Schema 中可选 | **否；既有收尾过滤形成混杂，不能算独立语义通过** |
| 独立新进程 restore-only | 通过；未配对工具 0，新增发送 0 |
| 最终未决 reservation / 未消费响应 / 待交付投影 | 0 / 0 / 0 |

构造第二包时尚未收到其响应，因此 read_state 如实保留
`not_confirmed_in_provider_request`；同包 `pending_feedback_delivery` 带原完整反馈。
第二响应确认后，原 `read_coverage` 记录 successfully_provided=true、complete_data=true，
投影不再附加。没有提前把“已构造”当成“已发送并确认”。

模型正确报告 holding_speed=0.18173358255275762 m/s、阈值 0.020 m/s、原 B 来源和历史范围。
它的解释符合整个 Study 只读一次的指令，但最终逐项审查工具 Schema 发现：
第二请求的 evidence_read 仍在，且可读原反馈 wrapper 的 `/result`，原摘录引用却不在
既有收尾过滤后的 artifact_id enum 内。因此不重读的行为还受到可选参数范围影响，
不能把本例当成“允许同查询重读时仍自主避免重读”的无混杂证据。
最后用原 scoped_context 登记机制补了这个实际缺口；不修改旧冻结 Study、不扩额补发，
其真实效果留为未验证。首版审阅中“启动通过”的判断已由保留 supersedes 指针的新审阅纠正，
原记录不删除。后续科学提案仍有未经验证的单调干预预期，交付与基本事实理解也不代表全面科研能力。

L0 继续包含极简 `action_trace`、`research_intent` 和已读状态；此连续性例没有先前 Plan，
故 trace 为空而不补造。原 A/B 归档回归继续保留已有科研轨迹和原 Plan 指针。
没有恢复 C3 完整历史；本轮 wire 量级远小于原 639,373-byte 长会话样本，后者仅作量级参照。
详见 [交付核对](../../evidence/c3_g1_g2/continuity_review.json) 和
[连续性标准导出](../../evidence/c3_g1_g2/continuity/immutable_artifacts.tar.gz)。

## G1.2/G1.3：四个新 Plan 通过，科学修订不通过

[首发前冻结协议与原量表](../../evidence/c3_g1_g2/decision_protocol.json)
保留同一历史候选、任务、共同物理事实、方法目录、提议预算、第二轮观察和 Provider 设置。
首轮唯一关键输入差别是额外数学证据；没有向模型提供评分、预期方法或未来观察。
两组同用修订后的系统与轮次协议。

| 请求 | Schema | 主要选择/修订 |
|---|---|---|
| A1，无额外数学证据 | 通过 | instantaneous_braking_v1，另提平衡检查与一次物理回放 |
| B1，有额外数学证据 | 通过 | 瞬时制动 + native dynamics + 诊断回放 |
| A2 | 通过，新工具 ID | 改选全保持窗口 sampled-affine-conic-minimax-v1 + 回放 |
| B2 | 通过，新工具 ID | 保留瞬时制动/native，改为沉降相位解释及恒值输入回放 |

原 wire 核对证明第二轮保留上一轮实际 Plan，四个工具调用 ID 不同；没有只输出正文、
没有删历史 Plan、没有自动重试或补发。全部原 Plan 见
[结果摘要](../../evidence/c3_g1_g2/decision_summary.json)，完整 wire、response/reasoning、收据见
[决策标准导出](../../evidence/c3_g1_g2/decisions/immutable_artifacts.tar.gz)。

两组确实引用了新事实，也改变了描述或方法。但以下问题使“有效的科研判断修订”未通过：

1. **跨控制比较被误当成模型误差。** B1/B2 把 CONIC 见证的模型速度与另一套 NMPC
   的 0.1817 m/s 相除，声称约 13 倍幅值和约 0.04 s 相位失配。冻结输入已说明
   partial_comparison、对齐预测样本缺失和控制不同；不能据此否定速度通道或断言不应再用 CONIC。
2. **两个标量样本被扩大成整条动力学规律。** A2/B2 从 0.31 s 与 0.35 s 的速度模长
   宣称单调衰减；B2 进一步给出 0.24 s 上升穿越和 0.378 s 下降穿越，及确定的到达相位缺口。
   两点可在额外假设下拟合指数，但原轨迹未证明该假设，更不能反推出未观测的上升穿越。
3. **瞬时量被当成有限时域必要条件。** A1/B1/B2 将单点最优减速度与
   (v−阈值)/剩余时间比较，进而区分结构/控制限制。缺少沿后续状态有效的全时域界，
   单点权限不足不能否定未来制动，权限充足也不证明全窗口可行。正文附带的限制声明没有修正这些分支。
4. **状态时间和执行前提错误。** B2 将 update 30 说成约 0.31 s 峰值状态，实际是 0.30 s；
   还提出延长到 0.40 s。虽标注协议外诊断，原冻结接口/0.35 s 时域没有准入这个动作。
5. **预算不完整。** 准备、精确前缀重建、内部积分/FD，以及额外减半步长运行没有完整计入。
   A2 更把步长重跑称作无需新增启动的状态记录。

以上按内容与可执行性审阅，不按文字长度或形式完整性评分。原量表 0/1/2 的人工结果：

| 内容 | evidence_scope | testable_hypothesis | discriminating_action | feedback_revision | complete_cost |
|---|---:|---:|---:|---:|---:|
| A1 | 1 | 2 | 1 | 不适用 | 1 |
| B1 | 0 | 2 | 0 | 不适用 | 1 |
| A2 | 1 | 2 | 1 | 1 | 1 |
| B2 | 0 | 2 | 0 | 1 | 1 |

竞争假设与反证表述的存在单列计分，其因果判据错误另在证据范围/区分动作中扣分。
`independent_direction_support` 未评分，没有执行提案或独立留出验证。
数学信息改变了两条轨迹的后续选择，但 B 的变化依赖错误比较；**未证明选择质量改善**。
每臂只有一条两轮轨迹，不作统计或一般性优劣推断。
G1 的反馈交付和每轮 Plan 门槛通过，启动作用域行为验收有混杂，第四项科学修订未通过；
不是因数学组没有得高分而停止。
详见 [审阅与停止记录](../../evidence/c3_g1_g2/review.json)。

## G2 与原生状态资格

依照用户“如果 G1 无法通过，停止 G2”，未建立 G2 Study、未选择或执行 G2 数学方法，
没有数学结果可交付、没有基于新数学结果的第二 Plan。G2 成功标准均未得到验证。
没有把 G1 的方法描述、历史 CONIC 结果或读取成功包装为新的数学实验。

仅作只读前提核查：B 仍 stopped；原 `native_point` 接口能定位 update 30 的原生
qpos/qvel 各 48 维、四路实际 SI 张力、原场景及此前 30 个已测输入区间，时间 0.30 s。
所选来源没有完整 integration_state checkpoint，提供的是原接口允许的原生前缀重建来源。
真正重建和一致性核验属于需计费的数学 Worker，本轮均未执行；未替换成 GVS 状态。
也未声称它已合法绑定到新 Study 候选，跨 Study 所有权/任务/初始化/通道绑定尚未尝试。
原来源和边界见 [状态只读核查](../../evidence/c3_g1_g2/historical_state_qualification.json)。

下一缺口是 Agent 的证据可比性、两点时间推断及瞬时/有限时域范围理解；
状态来源可读取不等于这些理解问题已解决。本任务没有据此开新实验或扩额。

## 成本、验证和交付状态

| 项目 | 实际 | 本轮上限/剩余 |
|---|---:|---|
| G1 连续性 Provider | 2 | 2 / 0 |
| G1 决策 Provider | 4 | 4 / 0 |
| G2 Provider | 0 | 8 未使用，G1 失败后不得启用 |
| 总 Provider | 6 | 14 / 8 未使用 |
| Prompt / Completion / Total tokens | 74,487 / 33,511 / 107,998 | Provider 原用量 |
| Cache hit / miss；reasoning tokens | 27,648 / 46,839；19,714 | reasoning 已含在 completion |
| Reporter | 0 | 未调用 |
| 数学评价/原生积分步 | 0 / 0 | 数学上限 4 全部未使用 |
| 独立物理 / NMPC / PPO | 0 / 0 / 0 | 上限均 0 |

六次请求均有确认响应与结算收据，无未知发送、未消费响应或自动重试。
Provider 未返回金额，金额为 unknown。原收据 elapsed_s：连续性 20.562 s，决策 194.624 s；
这是请求耗时口径，不冒充数学计算资源或自然经过时间。两新 Study 经原
`engineering_count_budget_closure` 封存，model_stop=false，无伪造 Agent STOP。
决策 Plan 为描述提交，不执行公共科研动作，因此该 Study tool_calls=0；连续性公共读取为 1。

定向 unittest 7 项通过，报告时间 10.044 s：新增协议两项、原 probe 四项和原 A/B
交接反馈回归一项。随后仅核对保存的真实 wire、Plan Schema、反馈、原始收据、
restore-only 与只读状态来源；未运行全仓测试、半径敏感性或旧 A/B。
最终 scoped_context 修复另以真实摘录/原收尾读取边界做离线检查，检查用状态副本，未改冻结 Store。
最终审阅脚本曾把 read_coverage 字段误写为 delivery；改为原 successfully_provided/
complete_data 后通过，只重做只读审阅，没有补发请求或改变模型结果。

严格区分本轮结论：读取工具执行成功；反馈送达与基本事实理解通过；首次读取作用域真实验收未定；
四个新 Plan Schema 通过；有效科学修订失败；新数学结论未计算；新独立物理任务未测量。
它们不能互相替代。

首个修复提交 `fccc8b245571a7b6edeb6489b68642a42b8505bc`；
首发前冻结提交 `ae91c6b013a2595c5ba9fedf5f26e8b0e3e1fa3b`；
本报告及标准导出所在最终提交的完整 SHA 随最终交付给出，避免文档自引用。
普通推送目标为 `origin/fix/c3-g1-g2-decision-validation`，不强推、不合并 main。
最终远端 HEAD 与目标工作树干净状态在推送后核对并随交付给出。
