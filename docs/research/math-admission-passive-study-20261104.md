# 统一数学准入与被动自主 Study 准备（2026-11-04）

本轮只做工程审计、最小接口修改、离线验证和新 Study 准备；真实 Provider 请求为 0。正式科研授权门禁仍关闭。

## 1. 基线与旧 Study

GitHub 分支核验起点为 [052d08f](https://github.com/wran021004-gif/softrobot-agent/commit/052d08f49555a0e78ea50ed5f52e4a79d0fdf6b0)。与实际绑定实现 `732856c62e90aa27e72e01c6c7a4f2a4ed1c956c` 的差异只有两份报告。

旧 Study `passive-mechanism-autonomy-20261104` 的 1141 个 artifact 哈希全部有效。其 Store、SDK 文件及原共享授权库已逐文件复核保持原样；没有改绑旧实现或冻结参数表。

| 旧事实 | 核验值 |
|---|---|
| resolved identity | `eca928ec8e579f2d7dcf564b98eb5b5fc9a824cf12c25eac0de5e55b409e5ede` |
| 科学 profile | `9f95b160c2aa80a89ca40d324d75fc33e660fd51a86f3fe6a65235cdc376dcd3` |
| Provider / public operations | 55/64；76/256 |
| 数学评价 / 物理成本 | 1；1 model / 1 episode / 500 steps |
| 新结构 / 独立 Replay | 0 / 0 |
| 状态 | 已结算边界监督暂停；state=ready，非 Main STOP；无 pending、unknown Worker 或未消费响应 |

## 2. 旧白名单的来源与科学适配性

`0457012` 在 `study_passive_engineering_v1.json` 增加了明确标为 Stage III-A/B 工程验证的数学授权，选择器仅含 `segments.*.young_pa`、`payout_lengths_m.*`。原自主 Study 继承了这份窄表。`family_sensitivity_v2` 本身是按实际候选匹配的路径授权规则，不定义第二套物理参数域。

这份工程授权适合最初的有限刚度/payout 检查，但不能据此把自主结构设计永久限制为这两类变量。当前参考装配有 18 条连续有效参数路径，其中 16 条被旧授权挡住；截面方向、曲率和半轴的拒绝来自授权表，而非缺失生成接口。历史 49/54 两个中心双参问题另有独立成本缺口：至少 10 次评价，显式只给了 9/8 次。扩大授权不自动消除该缺口。

证据分层：`family_space.parameter_capabilities` 负责注册、域、连续性与实际物理效果；`family_analysis_parameters` 加入方法与 Study 授权；`structure_research.parameters` 限定结构数学参数；`prepare_context` 检查所选问题、工作点、合法探针与成本；原 Worker 才产生数值证据。只读授权投影、合法编译或模型系数来源都不证明导数数值有效。

## 3. 可选择参数及范围

旧 Study 在当前装配上的条件可选路径只有 `segments.0.young_pa` 和 `payout_lengths_m.tendon_0`；每个具体目标与工作点仍须原准入。完整目录继续展示不可用项，不将其伪装为执行选项。

| 物理变量 | 冻结 SI 域 | 生成重建与方法边界 |
|---|---|---|
| 截面方向 | [-π, π] rad | 改变各向异性截面主轴、惯量/刚度方向；圆形或各向同性截面不适用。非一致站点角度不能用一个隐含标量耦合修改。 |
| 自然曲率 y/z | [-10, 10] rad/m | 重建自然角/弹性参考；保持相同初始化规则不等于保持相同笛卡尔形态或平衡态。 |
| 椭圆半轴 y/z | [0.003, 0.012] m | 重建面积、质量、惯量、弯曲刚度与几何；其他截面尺寸按所选 kind 的原域解析，管截面还须 inner < outer。 |
| 杨氏模量 | [2e6, 15e6] Pa | 重建 EI 与 hinge stiffness；不自行修改任务或控制。 |
| 固定 payout | [0.1598, 0.1604] m | 每次执行中固定，允许跨结构生成改变；重建单边长度约束与激活状态。不是主动输入或 pretension，约束切换可能导致导数不可靠。 |
| 长度 / 密度 / 黏性 | 长度 [0.08, 0.24] m；密度 [500, 2500] kg/m³；两轴黏性 [0, 0.05] N·m²·s | 重建几何、质量或阻尼；边界可用单侧探针，最小成本与内部点不同。 |
| 当前 span 的连续布线参数 | radius [0.014, 0.023] m；phase [-2π, 2π]；anchor_s [0.8, 1]；guide_s [0.15, 0.75]；角偏置 [-π, π] | 重建路径与约束几何；override、缺失 guide、索引和清隙检查仍可能使请求不适用。 |

不可作为普通结构梯度：离散段数/腱数/截面 kind、拓扑对象、cells 等数值分辨率、控制器权重。当前被动模式中 servo gain、pretension 没有相应主动控制作用；diameter 只有清隙/视觉效果；force_limit 是容量资格阈值，不是结构力律。没有把这些字段纳入新求导授权。声明模板 `spans.*` 也不是可执行的具体索引。

新精确授权输入为 `configs/research/family_sensitivity_passive_design_20261104.json` 的 24 条显式选择器，复用原 `family_sensitivity_v2` 语义，覆盖长度、材料/自然曲率/截面方向、各已声明截面的合法尺寸、payout、连续 span 布线和柔性段 route attachment.s。只有实际存在、连续、有效且方法适用的具体路径才可选择；不会授予未声明物理域或离散拓扑。

在旧参考装配上的只读授权投影为 18 条：2 段属性、6 物理属性、2 半轴、1 payout、7 span 参数。新正式 Store 目前没有候选，且未获正式科研授权，所以没有可直接启动的正式数学请求。18 是条件能力投影，不是新 Study 已执行的结果。

## 4. 数学发现、最低成本与请求编译

主要执行选择器按候选和操作投影可选择路径；完整 `parameter_catalog()` 保留设计域、授权、方法支持、有效性和未检查的工作点准入状态。没有新增 Registry、预算器或顶层工具。

`prepare_context()` 仍是合法探针和最低评价数的唯一计算来源。原发现视图展示 baseline、每条路径的实际两尺度探针、双参 joint check，以及 optimize 的至少一次试验。原编译器把这些依赖和共享物理成本返回给 Main。

| 当前中心探针问题 | 最低评价 | 普通有限时域成本 | 配对消融成本 |
|---|---:|---|---|
| 单参数 differentiate | 5 | 5 model / 5 episode / 2500 steps | 10 / 10 / 5000 |
| 双参数 differentiate | 10 = 1+4+4+1 | 10 / 10 / 5000 | 20 / 20 / 10000 |
| 双参数 optimize 的最小合法请求 | 11 | 11 / 11 / 5500 | 22 / 22 / 11000 |
| 单 Worker 最大合法 64 次配对评价 | 64 | — | 128 model / 128 episode / 64000 steps |

域边界使用实际合法单侧模板，不能把所有双参问题机械写成 10 次。上述物理成本来自原 1 load、0.5 s、0.001 s 时间网格；静态重平衡不冒充有限时域积分。

Main 的 question cap 优先，其次为已完成 diagnose 的非零 cap。任何明确的低上限都准确拒绝，不静默上调。两处均未明确 cap 时，编译器在原参数/方法/工作点准入之后选择最小合法值，产出原 `AnalysisRequest`；原执行授权、预算、保护收尾和 Worker 预约仍掌握执行权。授权不足、方法不支持、工作点不适用和预算不足分别可见。

按用户后续明确指令，新 Study 的数学、分析及共享物理计算累计上限均为 `null`，实际评价/模型/episode/积分成本继续计数。复用原 Store 已有的 null 限额机制，并保持 `MeasuredCost.backend_solves` 必须为数值；不能用 null 伪造免费消耗。新 null 物理入口限定为正式被动分析、数学无累计配额、无 RL/NMPC 且独立 Replay 子限额有限的 Study。旧有限总额含义不变。

## 5. 聚焦 Plan

`agent.plan_schema`、`object_choices.main_tool_schema`、`bind_plan_selection` 和原 `Plan` 已提供唯一的 diagnose 候选位置 `decision.selected_candidate`。Main 填写假设、预期/削弱观察、固定条件、停止条件、解释与假设标识；不必重复填写 `research_intent` 或求解器名。action 确定性绑定 intent，显式错误值仍由原合同拒绝。

实际 SDK 聚焦 Schema 与投影合同的所有执行约束一致，SDK 仅补充属性说明。重复顶层候选字段、跨 action 错误字段和冲突候选均拒绝；不会删掉坏字段制造合法请求。仅修复了既有候选绑定器可能覆盖矛盾引用的具体公共缺陷。没有进一步增加候选别名、推断或机械兜底。历史请求 52 已获正确 Schema 却多填顶层字段，属于未遵循 Schema 的证据。

## 6. 离线回归

本轮最终覆盖 49 项不同测试：48 项通过，1 项旧合成夹具断言在 `052d08f` 基线同样失败。最后新增 null 物理语义后的 25 项定向复核全部通过；没有把基线失败计为通过。

通过项包括：合法单/双参数、独立扩大授权 Study、旧授权拒绝与保留、静态和动态最低成本、双参 10 次与准确积分成本、低 cap 非执行、最小 optimize 和最坏合法配对调用、无累计物理上限但数值账本继续累计、SDK 的 null 序列化、聚焦 Plan 与实际 SDK 约束一致、冲突候选拒绝、M1/被动 v2/M5 基础入口、Reporter 来源、正式证书和 SELECT/STOP。

使用已有 HTTP Mock、合成数值夹具及冻结被动 v2 的短 500/1000 步执行检查；无真实 Provider。合成的 100000 episode 记账测试仅验证限额/账本，不是实际物理计算或科研结果。旧失败 `test_l0_l1_wire_and_reporter_preserve_direction_as_diagnostic_only` 把合法语义目录中的 `mass_matrix` 名称也当作不允许出现的数值内容；基线同样失败，没有为它修改生产来源门禁。

## 7. 最终新 Study 与预算

最终身份 `passive-design-autonomy-unmetered-20261104`；resolved identity `8ae6e11d4e55f4233c5fb35bb3f55223e5a841a4296fe81e4031648e939e15cf`。绑定实现 `d68e14a961abc61169ed8cd031adaa35c0b112bb`，科学 profile 与旧 Study 相同。新 Store 与旧 Store 完全独立，准备时没有候选、数学结果、Replay、Provider 使用量或导入历史获胜结构。原型、结构生成能力、物理任务、初态规则、时序、评价器、积分和确认协议均保持一致。

科学差异是对有效连续结构参数的明确授权扩展；执行差异是当前接口、无累计数学/共享物理限额及新的独立账本。未导入旧失败上下文、H2 或旧候选作为研究路线。原 544 episode 方案按用户澄清被替代，未启动的早期准备 Store 以零成本保留，没有重置旧 Study 的 55 次历史。

| 项目 | 最终准备 |
|---|---|
| Provider | 初始共享 24，内含 4 次收尾；Main/Reporter 同账本；用户允许监督者按需追加，保留历史与原增补绑定机制 |
| 数学、分析、共享物理累计上限 | `null`；完整记录实际成本，最坏成本预览仍保留为资源事实 |
| 单 Worker | 原 180 s 有限保护；原请求合同至多 64 次评价；Main 显式更低 cap 继续有效 |
| 独立 Replay | 16 次原子子限额，配对成本如实计数 |
| 通用公共操作 | 256，内含 8 次收尾；不是新增的数学专属配额 |
| Provider 目标 | Gateway `http://127.0.0.1:8787/v1`，仅 `gpt-5.6-sol`；Main none / Reporter medium |
| 监督 | 每 4 次 Main 检查，及时最小接口修复；第 8 次阶段审查，有进展不机械 STOP |
| 正式执行状态 | `PENDING_EXPLICIT_APPROVAL`；原授权门禁已实际测试拒绝；本轮不启动 |

## 8. 下一轮真实 Main 验收

1. 正式批准绑定上述新 identity、实现与科学范围后才允许发出真实请求。实际 wire 只发往指定 Gateway/model；Main 自选物理问题、变量、努力和是否保留/替换假设，不注入 H2 或历史赢家。
2. 形成合法的候选绑定 diagnose，实际 SDK 交付可选择参数、完整目录恢复入口、精确失败类别和成本依赖。无显式 cap 的问题进入最小合法选择；显式低 cap 必须零科学执行并得到准确成本反馈。
3. 原 Worker 产生真实、有范围和有效性说明的数学证据；不能以编译成功、目录、只读投影、优化失败或局部一致性冒充导数有效、全局不可行或任务成功。
4. Main 用真实结果选择生成/验证、继续计算、反驳假设或有证据地拒绝方向。若采纳结构变化，须走原生成和独立 Replay；无改进结果也如实保留。SELECT 仍须独立正式验收与完整证书阅读。
5. 每 4 Main 在已结算边界核查动作、数值证据、真实消耗、失败与接口/模型归因。第 8 Main 评估信息增益和剩余问题，避免机械终止或单纯为用完额度运行。具体接口缺陷实施最小修复并绑定；预算接近保护区时可按既有机制追加 Provider，不能重置历史或伪造授权。
6. 完成、失败、工程阻断或需要人工行动时明确报告；保留独立 Replay 与 SELECT/STOP 原合同。科学范围或物理语义变化仍需单独版本化，不能用接口修复暗改。

只发布源码、离线测试、精确选择器和精简报告；Store、完整 wire、凭据、批准全文及候选当前数值保持本地。工程准备完成即停止，等待正式科研启动授权。
