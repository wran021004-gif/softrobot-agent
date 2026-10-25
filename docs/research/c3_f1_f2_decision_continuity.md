# C3 F1/F2：反馈连续性、数学—物理诊断与决策验证

2026-10-25，Asia/Shanghai。基线 `1879b79976bbc267f09406f18be40001dd01de70`；
专用分支 `fix/c3-feedback-math-decision`。

**工程修复和限定验证已完成，但“不立即重复读取”的真实语义验收未通过，不能认定数学证据改善了 Agent 决策。**
本轮共 7/8 次 DeepSeek 请求、8/10 次数学评价，没有新独立物理评价、NMPC 执行、PPO 或完整 A/B。
失败与未决结论全部保留；不扩额补跑。

## F1：准确复现、交付与已读状态

原 A #19 的 `/control_result_links` 读取成功并结算，原反馈
`5b81946825e082d1439c8b8eafad0ad989af6dc10d82e9d19e47a071e61052fb`
在 Handoff 后没有进入 #20 wire；#20 随即同参数重读。交叉案例选 B #41→#42，
也是 `/control_result_links` 读取、切换、立即重读。两者直接读取原封存档案；未改原 Store/证据。

| 完整 Provider wire | 原实际 bytes | 新离线投影 bytes | 交接内容 |
|---|---:|---:|---|
| A #20 | 126,038 | 129,375 | 控制链接紧凑事实与原反馈指针；另一 summary 的原反馈完整交付 |
| B #42 | 142,828 | 143,687 | 控制链接紧凑事实与原反馈指针 |
| 旧长会话 C3 #25 | 639,373 | — | 直接读取原 wire `9edfbf23…6a30` |

这些是**完整 wire 的离线投影**，没有重发历史 A/B 请求。投影包含生产 L0、原工具 Schema 和交接反馈，
新长度约为旧长会话样本的 20.2%/22.5%，不是仅比较 L0 JSON。
旧长会话是跨阶段量级参照，不能将差额直接当作同一请求可节省的 Provider tokens。
原始引用及测量见 [offline.json](../../evidence/c3_f1_f2/offline.json)。

实现沿原路径 `request_feedback_boundary → handoff preparation → before_model/agent_decision_brief → CURRENT_RESEARCH_PACKET`。
原边界继续核对真实响应、工具 ID、配对结果、结算收据和 SDK snapshot。
preparation 只保存最近一轮的确定性 `pending_feedback_delivery` 投影：工具 ID、原查询、执行状态、
原反馈引用、小结果原文；大结果保留关键事实和精确 `/result` 读取指针。
不重发工具调用，不伪造 assistant/tool 消息，不复制完整历史。

交付是否完成从**成功响应对应的已保存 wire**核对，构造包、尚未发送、未知发送都不算确认；
未知结果仍由原 reservation/replay/reconcile 阻断新发送。确认后投影不再重复附加。
原 SDK/Store 仍是唯一恢复来源，没有新队列或已读数据库。
当前 Handoff 绑定的原反馈也进入原读取白名单，保证收尾保护下 `/result` 指针仍可读；
它只是反馈 wrapper，不登记科学证据、不获得物理结果的正式 SELECT 读取凭据。

L0 沿已有 `read_coverage/read_counts` 增加完成读取数、最近 3 项查询/Pointer、内容身份、交付状态、
重复分类及完整清单查询指针。新动态 working_set 反馈另存原状态身份；历史未记录的版本为 null，
不补造。相同 working_set 查询若内容改变仍是合法新读取；不可变且已交付的同内容读取才标记重复。
完整字段、summary/派生视图和未确认交付严格区分；交付不等于理解。
A/B 投影分别保留 4/7 个 Decision Trace 节点和最近原 Agent 假设摘录及原 Plan 指针。

`DISPOSITION_REQUIRES_EXACT_ACTUAL_READ` 现在准确指向 `experience_disposition`：
只可引用实际经验 read 收据或精确 entry_id@revision；科研 artifact、假设名、搜索结果、SELECT 物理结果都不是经验键。
无合法 experience_retrieve 时删除不适用字段，不猜 ID。用 A 的原始错误输入回归。
STOP 全结果引用及 SELECT 正式完整读取要求未放宽，summary 不获得完整读取凭据。

## F2：按需关系、瓶颈与可信范围

L0 只增加一个 `diagnostic_relations` 查询入口和比较限制提示；不计算、发送完整关系历史。
`evidence_read(view=working_set,pointer=/diagnostic_relations,reference=<当前物理结果>)`
沿原 core 读取边界生成 L1，优先选当前候选的原数学控制回放、所选结果和最近结果。

L1 从原 evaluator、任务适配器、ResultCard 输入和方法目录生成证据关系与任务诊断；
保留候选/结构、任务、控制来源与通道、初始状态指针、模型/方法、工作点、网格/时域、单位、
solver/replay/support 可信状态、缺失对齐条件和不支持的结论。Reporter 解释仍是 hypothesis。
L2 的完整模型、状态、控制、原始轨迹、对偶变量和收据保持在原 Store，按需读取。

严格区分：

1. 同候选同实际控制的数学—物理预测比较：须有一致任务/通道/实际输入/网格/初始状态、
   绑定预测样本和完整已记录的对齐差值，才显示逐采样位置/速度差。
2. 同候选不同控制的独立物理表现：只描述观测，不标为模型误差或单因素因果。
3. 不同结构或控制条件的任务结果：只在记录范围内比较，不推断结构优劣或原因。

B 的 CONIC 第 6 候选数学见证 `87d62673…2931` 与对应实际控制回放 `3f67ca10…612f`
确有同控制、网格、通道与零初始状态依据，但原 source 未保存绑定的完整预测输出，
原 comparison.aligned=false。因此为 **partial_comparison**，只给已记录的任务聚合事实，不重建逐采样误差。
该回放终点误差 13.7064 mm、保持最大速度 0.274126 m/s，任务失败。

B NMPC `ead9bd6e…474f` 采用另一控制方式：终点误差 4.0920 mm、保持位置最大误差 4.5172 mm，
保持最大速度 **0.1817335826 m/s**，阈值 **0.020 m/s**。
速度峰值在 **0.31 s**，保持窗口 **[0.30,0.35] s**；0.35 s 的速度为 0.0500520 m/s。
这些是独立物理记录，不是全窗口持续以峰值运动。数学序列回放与 NMPC 不能相减后称为 GVS/MuJoCo 模型误差。
NMPC 自身另有保存的 prediction evidence 查询入口，不把较早的 CONIC 见证绑定给它。

局部制动/原生动力学/短输入响应和有限时域能力方法通过原方法目录列出适用条件与成本。
本轮没有新做制动数值实验。精确已保存状态与输入是前提；
`min_{u∈U} v_hatᵀ a(x,u)` 只表示瞬时速度方向加速度趋势，不能推出剩余 0.05 s 内可停稳。
控制选择、结构权限、局部模型差异仍是竞争假设。

第 4、第 6 数学候选的实际变化为根段 Young 7.2→10.45 MPa。
原 signed score 分别 −0.19999999999981213、−0.19999999999954968，差 2.62457e−13。
各自记录的 support/replay 区间为
[-0.2000000001349602, −0.19999999999981213]、
[-0.2000000000845339, −0.19999999999954968]，相互重叠。
显示 `indistinguishable_at_recorded_numerical_precision`，未引入全局 1e−6 阈值。
区间也是浮点诊断而非严格界；两者局部采样约束检查通过，第 4 项无独立物理支持，
第 6 项有失败的物理结果。原搜索 incumbent/排名不变。

## 半径数值链与 NMPC 来源

独立 Study `c3-f2-radius-20261025` 使用原 T2/FamilySpace/GVS/CONIC。
固定 B 第 6 候选的合法拓扑，只改变 `spans.0.radius_m`：0.0175/0.0180/0.0185 m，
在冻结 [0.014,0.023] m 内。对应首 span 的真实腱路改变，三个模型身份与 GVS B 矩阵不同；
任务、其余结构、模型规则、控制通道/边界保持一致，并通过原 sensitivity_context 绑定检查。

3 次真实模型准备 + T2 内 3 次 CONIC + 2 次 dual-face 尝试 = **8 次数学评价**；
T2 复用已注册的三个模型，没有隐藏重建。固定输入 replay 不调用额外求解器。
基准 r、r−h、r+h 固定同一输入的 score 依次约 −0.2、0.269778、0.026828；输入合法、replay 有效。
控制重优化后三者均约 −0.2。中心重优化差分约 1.5715e−10 /m，记录的数值区间
[-2.2318e−8,5.0328e−8] /m 包含零；dual-face 未决、有限差分/步长可靠性检查未通过，
故 `directional_comparisons_only`、`preferred_parameter_direction=unresolved`，不声称更优半径。
ResultCard/L1 已由原 sensitivity_summary/populate_sensitivity 接入，L0 沿原极简数学投影。
完整原始结果仅在 [标准数学导出](../../evidence/c3_f1_f2/math/immutable_artifacts.tar.gz)。

NMPC 科学设置未改：0.1 s **重规划**、0.01 s 控制/验收采样、0.0005 s 物理步。
预测积分仍用 `period/substeps`（本例 0.01 s），不是 0.1 s；更粗预测步会改变离散动力学、
节点/保持约束覆盖与 warm-start，不能只按节点数推断成本或速度改善，须另冻对照。
本轮只读核实两组各 4 次真实求解、31 个缓存沿用区间、35 个实际控制区间。

A/B 的 measured_nmpc_trajectory 均可读取 35×4 的实际施加 SI 张力、36 个时间点，
并通过现有来源绑定/张力/通道/任务/时间网格构造检查。
既有接口已支持 `initialize_control(method=baseline,candidate=C,parent=C,source=<完整同候选 NMPC结果>)`，
无 channel_map；输出可作 MuJoCo-direct 或显式控制搜索初始，任务验收不继承。
本轮只补方法目录的具体合法例子，没有新增转换器。
A 原先的 `method=measured_nmpc` 是不存在的 Schema 枚举，不是数值转换失败。

## 真实决策验证：成功项与失败项分开

反馈 Study `c3-f1-live-20261025` 有独立冻结配置、身份绑定授权和 Store。
真实 evidence_read 读取带原 B 来源的限定摘录，经过原 SDK Handoff；下一真实 wire 原样包含
tool ID、查询、success 和原反馈正文，字节一致。三次 wire 为 41,107/44,683/45,242 bytes。
新 Python 进程 restore-only 验证工具配对、快照与恢复，不新增发送；没有未决 reservation 或未消费响应。
原请求、响应、收据与验证见 [标准交付导出](../../evidence/c3_f1_f2/continuity/immutable_artifacts.tar.gz)
及 [交付核对](../../evidence/c3_f1_f2/continuity_review.json)。

第 2 请求的模型推理已经正确识别 0.1817335826 m/s、0.02 m/s 与原来源，
却再次执行同一读取。原推理明确再次遵循系统的 “First call evidence_read” 指令。
第 3 请求给出正确失败项、历史身份和可证伪问题，但仍有从最大值泛化持续运动、用权重扫描区分结构原因的过度解释。
因此：**真实交付通过，基本事实理解通过，立即避免重读失败**；不能将此测试包装成消除循环。
一次性启动指令的跨会话作用域是明确的测试混杂因素，未追加请求更改结果。

决策对照复用原 `agent_math_decision_probe.py` 与 C3 模板，独立 Provider Store，
同一历史候选、任务、物理失败、方法目录、提议预算与预先冻结的相同第二轮历史反馈。
A 只获共同物理观察；B 另获核验的局部数学见证、关系限制与近似平分诊断。
未把历史场景伪装为本测试的新候选或执行。协议/量表在首发前冻结，未按结果修改。

| 请求 | 原生 Plan | 观察 |
|---|---|---|
| A 第一轮 | 通过 | 瞬时制动+native dynamics+物理回放；存在将瞬时权限与有限时域混用 |
| B 第一轮 | 通过 | 改选瞬时制动+短输入响应+回放；引用数学 scope/近似平分，但也提出不成立的 50 ms 降幅上限 |
| A 第二轮 | **失败** | 只返回正文，误把“一个 Plan”理解为整个对话已提交；未修复、未补发 |
| B 第二轮 | 通过 | 更明确提出实际张力/松弛张力对照，仍从两时刻衰减过度推断结构/控制因果 |

按冻结量表人工审阅（0/1/2；不作显著性或总体优势推断）：

| 内容 | evidence_scope | testable_hypothesis | discriminating_action | feedback_revision | complete_cost |
|---|---:|---:|---:|---:|---:|
| A1 | 1 | 1 | 1 | 不适用 | 1 |
| B1 | 1 | 2 | 1 | 不适用 | 1 |
| A2 正文，非有效 Plan | 1 | 1 | 1 | 1 | 1 |
| B2 | 1 | 2 | 1 | 1 | 1 |

两臂都未完整计入后续 native 内部积分/前缀重建等成本；B 还把离线求解墙钟时间当作可能的执行延迟而无对应证据。
`independent_direction_support` 保持未评分：没有执行提案、没有独立留出物理验证。
数学信息促成了更具体的竞争实验描述，但作用域误用仍在，A2 又有协议混杂，**结论是未证实决策改善**。
[冻结协议](../../evidence/c3_f1_f2/decision_protocol.json)、[结果与用量](../../evidence/c3_f1_f2/decision_summary.json)、
[原请求/响应/原调用收据](../../evidence/c3_f1_f2/decision_originals) 均保留；本轮没有修复型额外请求。

## 成本、验证与版本

| 项目 | 实际 | 上限/未用 |
|---|---:|---:|
| 真实反馈测试 Provider | 3 | 4 / 剩 1 |
| 决策对照 Provider | 4 | 4 / 剩 0 |
| 总 Provider | 7 | 8 / 剩 1 |
| Prompt / Completion / 总 tokens | 88,057 / 32,085 / 120,142 | — |
| Prompt cache hit / miss；reasoning tokens | 35,840 / 52,217；21,032 | — |
| Reporter 请求 | 0 | — |
| 半径数学评价 | 8 | 10 / 剩 2 |
| 新独立物理 / NMPC / PPO | 0 / 0 / 0 | 未授权、未执行 |

API 金额未返回，unknown。反馈/决策 Provider receipt wall 分别 18.765/168.359 s；
数学 worker/账本时间 26.9066795 s（其中 T2 内核 0.6918295 s）。这些口径不相加冒充自然经过时间。
离线针对性 unittest 最终有效 16 项通过；最后集合中的两个类名写错后仅重跑对应两项，
随后收窄的对齐回归与收尾读取/正式凭据回归通过。所有调试轮累计 unittest 报告时间约 147.660 s。
没有全仓测试或重复旧数值内核求解；旧测试中的样例是明确标注的 fixture。

生产代码 9 个既有文件，相对基线 +241/−5，净 +236 行：
`agent.py`（错误反馈/动态读取版本）、`session_handoff.py`（一次性交付）、
`research_context.py`（已读 L0/交付/入口）、`core.py`（L1 按需路由）、
`evidence_views.py`（当前候选关系/诊断）、`capability.py`（原 support 区间可信度）、
`contracts.py`（经验键说明）、`task_constraints.py`（现有来源合法示例）。
第九个 `state.py` 仅补 3 行当前 Handoff 反馈白名单，修复收尾阶段精确读取指针会被拦住的实际缺口。
测试、冻结协议、标准导出和本文单列，没有新管理器、优化器、Agent、数据库或额外 SHA 清单。

实现提交 `4a01f1356e73fd0ae925009e9c9ea5a9769f5664` 已普通推送；
数学导出提交 `fdc0dcf717bf339136f60cc9c906ee0e6a5dcd1e`。
数学冻结源码为 4a01f1356；真实反馈冻结源码为 fdc0dcf71；最终只读关系元数据和报告随后收尾提交。
本文所属提交即最终交付提交，最终回应另列普通 push 后实际 HEAD，避免文档自引用 SHA。
发布前确认专用树除本轮收尾文件外无其他改动；其他工作树及原有未跟踪文件未触碰。

下一步值得先做**独立授权、明确每 Study 启动/每轮 Plan 作用域的两轮复测**，再决定是否做
绑定 update-30 精确状态的有限时域制动/同输入预测对照。现有证据不支持直接开启完整 A/B、
权重扫描或结构优劣研究；本轮到此停止。
