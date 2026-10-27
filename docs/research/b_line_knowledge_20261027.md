# B 线经验接入与只读审计（2026-10-27）

生产起点 `c190f64ae`；分支 `integration/research-next` 已 fetch 并快进核对，远端无更新。B 来源固定为 `8a6a15d4667b946d4e1dd6b20e544cc8d683452a`。只读正式报告与公开 summary/audit 中的真实收据、验收和费用，没有打开或复制私有 Store、成功结构/控制数组，没有重算 evaluator、建立 Native model、forward、搜索或物理回放。来源 blob 哈希见本次公开 `evidence/research_knowledge_20261027/source_audit.json`。

用户后续明确：不提炼数学结构搜索 Skill；经验应像教师传授判断方法，重点是成功任务类型、路线、分析，以及失败触发的诊断，而非逐步操作指令。故本次不创建 Skill、Runtime、记忆库或经验 Schema。S3 仅在本审计中分析，不进入结构搜索知识条目。

## 可复用经验（6 条，revision 1）

均为原 `project_diagnostic_procedure_v1`，保留 trigger、procedure、bindings、status、evidence、applicability、escalation；procedure 用解释性段落表达成功经验、竞争解释、辨别观察、后续判断和反例，最后一段记实际历史费用。每个来源都有 B commit、原路径和 Git blob SHA256。适用范围有约束，泛化均未验证。

| entry_id | 经验主旨 | 失败触发的分析 |
| --- | --- | --- |
| `research-timed-tracking` | BF4 全时域定时位置，Native 控制重新优化与独立验收 | 中途误差与末点不同；有限迭代与停滞不同；优化机会不匹配不能比较结构收益 |
| `research-strict-near-tolerance` | BF5 联合位置—有向工具轴控制，小残差下的有效续算 | 单项通过、chord/真实角度、未舍入余量和联合验收 |
| `research-stable-start` | BF6 从绳路/重力分析得到完整无接触起点 | 无法完整运行与完整但任务失败是不同障碍 |
| `research-bounded-continuation` | BF6 同结构 Native 响应优化，经残差/边界/收敛分析逐批精化 | 位置与工具轴耦合；物理界、系数界、信赖域和模型误差的区别 |
| `research-contact-causality` | 接触与失稳的证据判别 | warning、采样相位、稀疏速度/加速度及缺失 contact frame 不支持唯一因果 |
| `research-witness-and-cost` | BF5/BF6 成功见证与首达费用分析 | 数学预测、Native 内部达标、独立物理验收和不同费用口径 |

条目传授“为什么、怀疑什么、什么观察有区分力”，不选择下一动作、不提供控制参数配方，也没有成功结构坐标或完整控制序列。

## B 的真实路线和结论

研究路线、预定结构/顺序、额度与续批选择由 Codex 及固定监督脚本编排。原生成器/局部有限差分响应/受约束 minimax 优化器计算结果，原独立任务 evaluator 决定验收。B 的 Provider、PPO、NMPC 调用为零，不是 LLM 自主发现的证据。

BF4 S1 三个相同预算的组均失败，末轮仍改善；S1b 从自己失败控制续算后首个独立通过即封存。额外优化机会使它不能与其他 S1 组直接比较结构收益。公平 S2 的三结构×两起点全部有限失败，结构效应仍未决。Tracking 曾出现末点达标但中途失败，不能用终点 Reach 替代。

BF5 首次完整独立回放位置 7.969945402 mm 已通过，轴 3.001717641° 仍严格失败。新授权续段第 3 个 Native 回调（有限差分探针，零个完整 response proposal）找到候选；新的独立执行在原两时刻同时通过位置与有向轴，立即 SELECT。没有因近阈值放宽标准；方向仅是工具轴，不是完整 6D 姿态或 roll。

BF6 初始失败：接触记录在先，QVEL warning 在后，但失败调用前状态已极端，缺少逐积分步加速度及实际 contact pos/frame；接触引起失稳、失稳导致接触或耦合仍未决。R1 只读分析没有建立新物理模型。

R2 按绳路/重力力矩的假设得到一次完整 600 步、真实负载匹配且无接触的稳定起点，第二起点未运行。任务仍失败；它排除了“此配置没有任何可完整执行起点”的实际障碍，不证明稳定性理论或任务可达。

R3–R7 固定同一 P1、原任务、零物理初态、20 g 真实刚性负载与地面。完整时序显示后段位置偏低同时轴向上仰；Native 与独立回放一致，不能据残差推断模型迁移错误。R3 人工修正系数界活跃而真实 8 N 上界未触；R4 以后主要看信赖域、非负张力下界及耦合，不能用一种触界解释所有阶段。R6/R7 退步 proposal 触发原算法缩半径，有限正改善支持过有界新批次判断，但不保证最终可行。

各失败批次 STOP、保留原费用；R7 轴已通过，唯一末点位置 12.034913020 mm 仍超原界 0.034913020 mm，虽局部模型预测可进入界内，仍未 SELECT。R8 来自用户新增授权，不能描述为绕过 R7 STOP 自动续算。R8 硬阈值代理在回调 26 达标、冻结内部裕量在 76 达标，随后唯一独立回放全 30 点、真实负载、每积分步无接触等 10 个原组件通过，立即 SELECT，未花剩余回调追分。

以上“独立”指同一 MuJoCo 模型下的新实例执行与独立任务评价。没有跨模型、硬件、鲁棒性、普遍结构收益、全局最优或连续时间位置/方向保证；BF6 无接触则确实逐独立积分步检查。

## 原始费用及停止原因

下表取原公开账本，数值时间包含构建/初始化等 Store 口径，driver 含数值与编排，两列不可相加。秒数不是货币账单，机器货币费用未知。callback、数学请求、嵌入 evaluator/profile 与外层 receipt 也不是同一计数。

| 阶段 | Native / 独立回放 | 确认步 / 调用尝试 | Store 数值 s | driver s | 停止原因 |
| --- | --- | --- | ---: | ---: | --- |
| BF4 S0 | 1 / 1 | 1,200 / 1,200 | 2.651406 | 6.6551613 | 预检结束 |
| BF4 S1 | 228 / 3 | 138,600 | 20.423402 | 29.620165 | 有限迭代失败 |
| BF4 S1b | 101 / 1 | 61,200 | 8.206989 | 12.836997 | 独立通过 SELECT；代理硬界先达，内部裕量仍耗真实费用 |
| BF4 S2 | 606 / 6 | 367,200 | 51.497991 | 87.084570 | 六组有限失败，结构效应未决 |
| BF5 预检 | 51 / 1 | 31,200 | 5.672948 | 9.403430 | 两轮耗尽，方向微超限 |
| BF5 续段 | 3 / 1 | 2,400 | 2.893614 | 6.907970 | 独立通过 SELECT |
| BF5 首次通过累计 | 54 / 2 | 33,600 | 8.566562 | 16.311400 | 前置运动学另计 1 build/3 forward/0 step |
| BF6 原失败 | 1 不完整 / 1 不完整 | ≥452 / 453 | 3.1501073 | 历史 validation 未记 | 接触/数值不完整，因果未决 |
| BF6 R1 | 0 / 0 | 0 | 0 新科学计算 | 未记只读整理时间 | 诊断结束 |
| BF6 R2 | 0 / 1 | 600 | 1.6259945 | 4.8035293 | 首个稳定起点，任务失败 STOP |
| BF6 R3 | 151 / 1 | 91,200 | 11.5574382 | 15.4045685 | iteration_limit，任务失败 STOP |
| BF6 R4 | 51 / 1 | 31,200 | 5.6956721 | 9.5225476 | iteration_limit，任务失败 STOP |
| BF6 R5 | 101 / 1 | 61,200 | 8.8649125 | 12.7946522 | 有限额度，任务失败 STOP |
| BF6 R6 | 151 / 1 | 91,200 | 11.7691171 | 15.6798663 | 有限额度，任务失败 STOP |
| BF6 R7 | 151 / 1 | 91,200 | 11.6393395 | 15.6206751 | 微小正残差仍失败 STOP |
| BF6 R8 | 76 / 1 | 46,200 | 7.0940742 | 11.4023622 | local_target_reached 后独立通过 SELECT |
| BF6 首次通过累计 | 682 尝试/681 完整；8 回放/7 完整 | ≥413,252 / 413,253 | 61.3966554 | 历史总额未知 | 15 科学 model builds，未转移余额 |

S1 的线程环境未被旧驱动落实，不能声称单线程归一化耗时。失败 mj_step 内部进度未知，所以 BF6 完成步是下界，不能写成精确总步。B 的原 452/453 与 A 集成检查的 450/451 是不同执行，不能相互更正或混计。

## BF4 S3：数学排名改善未转化为效率/精度改善

首轮任务/族域默认值冲突，六次 generation 拒绝，无数学模型、CONIC 或物理调用；0.4500102 s 数值、4.0838841 s driver 的失败费用保留。R1 科学调用前的 manifest 检查失败另计 1.4803855 s 命令时间，不能解释为物理失败。

修正后原工具实际生成 5 个合法结构、5 次 GVS build 加 5 次 CONIC，共 10 数学单位。局部有符号分数从 S0 的 0.0833333 改善到工具选中结构的 −0.125；该局部仿射模型没有独立物理一致性验证，负分数仅为模型内结论。

两臂使用匹配的新鲜控制起点与 Native 设置，硬阈值首次内部达标均在回调 151，实际各执行 201 回调/8 response/1 replay/121,200 步。独立最大误差都约 11.94 mm；结构优先 RMS 10.984884 mm，高于直接控制 10.633249 mm。独立均通过原位置任务，但未观察到回调减少或精度改善。

含失败/搜索的结构优先为 60.2999294 s 数值/74.7801948 s driver；直接控制为 13.5226999/17.9741834，即 4.46/4.16 倍成本。整个配对为 73.8226293/92.7543782，402 Native/2 replay/242,400 步，另有 10 数学单位。151 是内部硬界首达，不是当时已经独立验收；后面真实调用不能删掉。

局部模型偏差、评分目标与控制算法的容限/迭代设置可能解释这种脱节，但本次没有辨别性对照能证明唯一原因。一个确定性配对不支持“结构搜索普遍无效”或统计性能结论，也不因此提炼结构搜索策略。

## 接入及权限

`memory/diagnostic_index.json` 沿用原索引，新增条目标记 `public_procedural_guidance; generalization_unverified`。正式 Agent 原先无条件移除 `experience_retrieve`，现在仅由原检索函数开放这批公开 procedure；旧 NMPC/RL 案例草稿不会进入正式 Study。没有开放 workspace 任意文件读取。

L0 仅有按当前 task family 生成的短 search 提示；不放案例正文、成功指标或自动动作。L1 search 返回简短索引与内容哈希；L2 exact read 返回冻结条目正文和来源。沿用 `ExperienceQuery`，没有新增经验 Schema。现有 tool_calls、Provider 账本、scoped authorization、closeout 与 RL follow-up 限制继续使用；protected closeout 仍移除检索/Reporter，不额外消耗探索。

原公开读取记录核对：提交树内能找到经验处置字段的 6 份公开 JSON（F3 formal/prestudy artifacts、research_chain、research_count、s8 accounting、topology_control）中，13 个 `experience_read_bindings` 均为空，未发现已公开的实际经验读取正文/收据。因此不能声称旧正式研究已使用这些经验，也不能从提示或空处置推断阅读。此结论仅覆盖提交的公开记录，不推断私有 Store 或压缩历史档案。

Agent 的 `experience_disposition` 仍只接受实际 read 收据或准确 `entry_id@revision`。search/启动提示不能冒充已读；原内容 SHA256、revision、read receipt 均保留。新增 reader 区分主 Agent 与 Reporter；旧收据未写 reader 时仍解释为原 Agent 读取。

`research_investigate` 在原请求中可选传 `experience_queries`（原 ExperienceQuery，最多 8 个），委托 Reporter 分析当前证据时参考经验。实际检索收据保存到原 report request；Reporter 下次请求读取保存正文，避免后来条目更新改变已保存阅读内容。经验不进入 `source_catalog`，Reporter 解释仍必须落在当前证据来源，内部读取不给 SELECT/STOP 阅读资格。

经验收据及其原历史 artifact 引用都没有添加到 `registered_references`、物理结果、验收、科学报告事实或当前证据白名单。处置 adopted 表示采纳指导，不是科学证明。知识不授予预算、通过资格、自动续算或自动科研动作。

## 方法目录与下一轮准备

原 Native `mujoco_direct_control_v1` 已覆盖 Reach/Hold、BF4 定时位置、BF5 位置—工具轴、BF6 真实负载定向样本任务；须使用合法候选、完整绑定控制和原明确时窗，独立回放决定通过。其接触/数值适用性检查仍可能拒绝探针；不能承诺一定找到解。

GVS/affine/CONIC 支持声明的模型内位置/速度范数、分量及定时样本约束；几何路径 progress 是另有边界的代理。BF5/BF6 的方向及整个负载/接触验收并未被支持，不能降级成只位置问题。CONIC 的数值 primal/dual/gap 不建立严格最优，更不建立物理验收。目录说明现已明确这些边界。

`design_sensitivity` 为固定物理输入的静态响应；`fixed_input_structure_v1` 为固定控制 Native 响应。CONIC controlled sensitivity 对成对模型重优化控制，Native T1/T2 另有保存控制重优化及 fixed-U 对照。本次发现目录误继承 direct-control 的支持列表，现复用原 Native 适用性理由，明确 T1/T2 仅 Reach/Hold；BF4/BF5/BF6 在目录即为 unsupported，不能据名字声称完整适用。对齐要求和未决梯度条件不变。模型与物理对照须对齐候选、实际输入、初态、通道、输出、时间格与时域，不同控制下的差别不能单独归因为模型误差。

PPO 兼容性与最小适配见 `ppo_cross_task_audit_20261027.md`。本次仅增加诚实能力投影与既有不支持语义的提前拒绝；不实现新环境或训练。

下一轮可使用现有公开 BF4/BF5/BF6 模板和上述按需经验入口；模板零额度/待授权状态保持原样。正式研究仍需新冻结身份、明确共享额度/方法授权、合法自有候选与控制、新独立验收。现有 Study 必须按原 implementation migration 机制接入代码变化，不能无声 reinterpret 已冻结结果。Knowledge 不构成 ready-to-run 授权；PPO 三类任务均仍未就绪。

## 定向验证

`test_research_knowledge` 7 项通过：正式索引隔离、search/read/处置与科学注册边界、L0 不预载、Reporter 实际读取与来源隔离、BF4/BF5/BF6 在模型/XML 前拒绝 PPO、真实 Harness/mock HTTP 读取及 Plan 拦截，以及 Native T1/T2 的跨任务目录拒绝。Reporter 原 13 项定向检查通过。fixture 不构成科学结果。

真实 Provider 对照的固定输入与范围见 `evidence/research_knowledge_20261027/protocol.json`，结果和实际 Token 成本另记 `decisions.json` 与本报告后续记录。仅使用 A 集成的公开失败投影和原任务，不提供 B 成功轨迹/控制/结构。所有提议拦截，无新正式 Study、科学 worker、Native、物理回放或训练。


## 真实小型对照结果与局限

在实现提交 `1256b0964` 后，复用原 production Harness、LiveBoundary、Plan/EvidenceQuery 与独立零科学账本完成一次 held-out A 集成失败对照。模型 `deepseek-v4-pro`、thinking enabled/high、输出上限 8,192；顺序 off 后 on，最多 8 次、实际 4 次请求，全部 HTTP 200 已确认。原请求/响应与 reasoning 留在 ignored `runs/kdiag`；公开 `decisions.json` 保留 Plan 原文、工具检查和账本计数，`review.json` 区分观察与评价。

| arm | 实际请求/确认 | Prompt | Completion | Total Token | 实际观察 |
| --- | ---: | ---: | ---: | ---: | --- |
| off | 3 / 3 | 38,273 | 13,942 | 52,215 | 1 次 evidence_read，1 个合法只读 DIAGNOSE，第 2 请求产生 Plan，第 3 请求完成后续 |
| on | 1 / 1 | 5,339 | 8,189 | 13,528 | 首次响应 length 截断，原边界拒绝未完成输出；没有经验读取、Plan 或最终答复 |
| 合计 | 4 / 4 | 43,612 | 22,131 | 65,743 | 科学 worker/物理步/Reporter Provider/正式 Study 均 0 |

Prompt cache hit/miss 为 27,904/15,708；reasoning 为 19,755 Token，已包含在 Completion 中，不重复相加。货币账单未知，不写成零。on 的较低费用源于提前截断，不是已证明更省 Token。未重发或追加“凑成功”的对照。

off 正确区分有效完整失败与执行不完整，承认缺少 BF5 误差量级及 BF6 接触/失稳因果；零科学授权边界也正确。但其 expected_observation 把 BF6 的 12 mm/10° 用于 BF5，成功路线用 tip 高度表达整个负载的间隙也不足。它把 1,200 合计步解释为独立执行步数；输入投影没有拆分这项计数，对此有歧义。该小输入还没有完整 BF5 TaskDefinition，故不应编造其阈值。工具合法仅指隔离探针的 schema/reference/intent 通过，不是正式 scientific admission 或实际 STOP。

on 有简短提示及原检索工具，但在第一次完整工具调用前截断，诊断、路线、STOP 判断和实际 Knowledge 阅读均未建立。**本次真实对照不能证明 Knowledge 改善决策**；已有的是按需入口、阅读/权限/Reporter 隔离的离线验证，以及一次需要保留费用的真实失败观察。不得用 mock 成功冒充实际效用。

保存结果后的可选控制台全文打印因 Windows GBK 无法编码上标字符而退出；两个结果文件此前已经落盘。已将控制台日志改成 ASCII 计数，没有重发 Provider。

额外旧 C1 applicability 测试有一处历史断言失败：它预期带外力的 direct Native 为 unsupported，当前为 requires_parameters。用 `c190f64ae` 的 task_constraints/native_control 两个相关原模块在同一环境加载后复现相同断言，未修改旧测试或 sealed evidence。此次 T1/T2 三任务目录拒绝由新的只读 fixture 独立验证。

收尾还令 protected closeout 的 L0 不再展示已被移除的经验检索提示，避免提示与实际工具可用性不一致；该定向边界复查通过。B worktree 的 tracked status 仍干净，HEAD 仍为原来源提交。

下一轮状态：Native 公共任务接口与 Knowledge 检索接入已准备，公开模板仍零额度/待授权；Knowledge 的真实决策增益未证，不能据此宣称 Agent 已学会成功路线。PPO 三类任务仍需本报告列出的明确适配。没有启动或批准下一轮正式 Study。


## 用户授权取消显式输出上限并重做对照

用户随后明确要求“输出不限制 token 上限”及“重新做对比”。据此另行冻结 v2 cohort（`protocol_v2.json`，本地独立 `runs/kdiag2`）：相同公开 case、模型、thinking/high、提示和任务；关闭/开放 Knowledge 各至多 4 次，共最多 8 次新请求。首轮 4 次仍计入历史，累计请求上限 12，不恢复或重写截断请求。

`ModelConfig.max_tokens=null` 现在表示不发送这个字段，原整数配置/默认值保留原含义；production Harness、Reporter 和真实 transport 校验都识别这种显式选择。原 SDK/mock HTTP 检查确认出站 JSON 无 `max_tokens`，没有 SDK 默认补回。上下文 guard 继续检查输入与 framing 空间，输出 reservation 标为 null，不能声称预留了一个有限的最坏输出额度。请求/科学额度、timeout 和不完整响应处理不因此解除。

[DeepSeek 官方 Chat Completions 文档](https://api-docs.deepseek.com/api/create-chat-completion/)（本次 2026-10-27 核对）说明：省略时 thinking/high 使用服务端 64K 默认，API 接受的最大输出为 393,216 Token；应用不设显式上限并不代表服务端无限输出。没有把旧 8,192 改成另一固定客户端上限来冒充取消。

`test_provider_context` 5 项在已有 `.f3-prestudy-env` 通过；真实 Harness 省略字段及 Reporter wire 的定向 mock 检查通过。`.mainline5-env` 缺少旧 context fixtures 所需的 matlab.engine/tokenizers，首次整组检查因此没有进入目标断言；使用已安装的 f3 环境完成，没有安装依赖。该环境问题与 actual Provider 失败分别记录。

v2 实际请求、Token 与诊断观察将在 `decisions_v2.json` 和后续结果段落记录；这段执行前声明不预判效果。
