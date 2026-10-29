# P6.2-K 信息收尾与 P6.3 最小问题审计

本轮只读审计 P6.3；不实现新梯度系统，不启动真实 Provider 或任何科学 Worker。知识集成详见 [交付记录](p62k_knowledge_consolidation.md)，原案例复核详见 [机器可读记录](p62k_information_audit.json)。

## 信息问题的最小修复

**定量语义。** `reporter._comparison` 对同名、单位、时间口径与来源 pointer 相同的已记录资源做带符号差值，单列 `numeric_change`。`evidence_views._resources` 保留真实 wall-time 口径，并识别实际存在的 `cpu_time_s`；未记录的 CPU 时间仍未知。资源的科研优化偏好未知时，`preference/direction` 保持 unknown。原案例 simulation_wall_s 为 3210.219000000041 对 3316.3910000000615 s，差值 −106.17200000002049 s；numerical_s 差值 −109.42038300028071 s，均为 decrease，不能据此宣布科研表现改善。解释文本保留非权威角色，不能覆盖原值、差值、求解状态或任务接受。没有自然语言核查器。

**工具构造。** 原 P6-F Store 的 Main 请求事件 53 确认：`research_plan(diagnose)`、`selected_method=endpoint`、`requested_budget=0`，但缺少 `decision.selected_candidate`，意图是对既有结果作只读判断。原拒绝正确，本轮未放宽 `admit_decision`。能力目录现在同时显示：只读调查使用 `research_investigate`；绑定数学选择必须明确当前 Study 候选和注册方法。无候选标为 requires_owned_candidate；数学预算为零标为 insufficient_mathematical_budget；有候选提供其精确详情与 mathematical_capabilities 查询。`research_analysis` 仍独立检查原授权、来源和预算。保留旧版只读 diagnose，不替 Main 选择候选、假设或参数组。

**报告阅读。** 原事件 99 整读综合报告，后续原 Main 最大输入 109,144 tokens。本轮让现有 `evidence_read(view=summary)` 对科学报告直接复用 `reporter_handoff_summary`，避免通用嵌套 preview 遗漏约束；仅在 core 的既有 summary 分支增加这条投影路由。L0 和工具说明提供 summary_query、interpretation_query，必要时读 fields/range；显式 full 与 SELECT/STOP 原完整读取要求保留。未新增报告 Store，未无条件截断工具结果。

对原报告 `0b3b39a3bf3f2f3ae8c83801d657db74447df2a68c2001cde03e361cdf85f74f`，使用事件 96 保存的真实历史 source_state，只读回放原读取边界：

| 读取 | UTF-8 JSON 紧凑编码大小 | 保留内容 |
|---|---:|---|
| full | 287,721 bytes | 原报告全部内容，保持原样 |
| summary | 54,442 bytes | 三项结果、全部 13 项原指标（含 4 项失败）、完整定量事实、结论范围与原来源 |
| interpretations 精确 pointer | 10,673 bytes | 原解释文本，仅作非权威解释 |

summary 约为 full 的 18.9%，减少约 81.1%。逐项核对 value、threshold、passed、source、threshold_source，逐结果核对 quantitative_facts、claim_kind、verification_status、supported_inferences；全部相等。没有增加正式阅读信用。这是原保存数据的离线尺寸比较，不是新的模型效率实验。

## 可直接复用的链路

| 现有模块 | 已有能力 | 最小问题中如何使用 |
|---|---|---|
| `extensions/tendon_family/family_space.py` | parameter_capabilities 给出实际参数路径、SI 单位、连续域、有效性、拓扑依赖与原域来源 | 直接取两个 segment length；不把 cells 等离散参数或理想腱无效物理量当连续梯度 |
| `tools/research_tasks.py` | TaskAdapter、Reach/Hold 的末端位置、保持位置与速度约束及独立接受 | 固定原 M1 协议和评价；不把能力分数替换独立任务接受 |
| `tools/research/task_constraints.py` | 候选绑定方法目录、任务覆盖、授权/预算状态、精确 request_template | 只显示当前候选/任务真正支持的方法；T1/T2 原支持 task.reach，不能据此声称支持 BF5/BF6 或被动任务 |
| `tools/research/analysis.py` | 既有 dispatch、候选/模型/任务绑定、成本及可追溯结果 | 保留一个执行入口，复用已注册 T1/T2 请求 |
| `extensions/math_analysis/` | 局部 LTI、轨迹问题、采样仿射锥能力、受控敏感性；已有适用性和局限 | 需要局部模型问题时可复用，不能将局部模型导数泛化为原非线性任务梯度 |
| `tools/research/nonlinear_capability.py` | T1 有限预算最优已见任务能力；T2 聚合已完成 T1 的单/多方向有限差分、固定控制与重优化响应及验证方向 | 最小 Reach 问题优先直接复用，不新建梯度内核；保留 active-set/time 切换和预算限制 |
| `evidence_views.py`、Reporter、`research_context.py` | 原数值→确定性事实→紧凑报告→非权威解释→Main 决定 | 分别报告任务约束、能力分数和机制假说，保留单位、来源、差分模式和有效性 |

## 建议的最小参数化问题

选择已验证的 **M1 Reach/Hold**，从原 SELECT 包 `9e06f5455e3a9961f7139eef5a0624b121f26fc7b87b016a0a769c3f1b909136` 取得实际接受候选 `fef9a8198996105575d5d954ba7b24ab26b38722e56640fd476bfa39f5e2651a`，原 Study 的所有权已核实。当前原 Study 已封存；未来计算须在明确授权的可执行 Study 中拥有候选，不在本轮改写旧 Store 或复活其预算。

- 参数 θ₁=`segments.0.length_m`，已注册域 [0.08, 0.24] m。
- 参数 θ₂=`segments.1.length_m`，已注册域 [0.06, 0.20] m。
- 固定拓扑、材料、载荷、初始条件、时间网格、物理输入边界和一个明确冻结的 M1 condition；不得把不同目标混为一个同任务差分。
- 指标使用已有 T1 的 `best_found_J`：在相同有限控制搜索策略/预算下，已访问控制中的最小“各冻结任务约束的最大归一化有符号超限”。任务阈值与验收独立保留，J 不是全局最优值或成功证书。
- Main 选择参数组、步长及假设；固定程序构建合法候选、计算既有能力分数和 T2 差分。声明域内连续不等于扰动候选已经完成编译验证。

未来最小对照是共享一个基线和 θ₁/θ₂ 各 ±h，共五个候选的已有 T1 结果，使用相同控制搜索机会；再交给现有 T2 v2 directions 聚合。每个方向报告 `(J_plus-J_minus)/(2h)`，单位 m⁻¹，同时保留固定输入对照、重优化模式、实际花费、求解/有效性状态、约束激活时间切换和原结果引用。有限预算、分支变化或求解停滞时只称局部割线响应，不称已证明梯度。此处是未来问题定义，五个点均未在本轮执行。

**最小接口修改范围：** 上述任务能力实验可以直接用现有 family 参数目录、AnalysisRequest、T1 和 T2 v2 请求链完成，不必新增数学模块。若 P6.3 要求把“两参数→具名指标→结果”统一展示，优先只在 `task_constraints.py` 补参数与指标的明确映射、在 `analysis.py` 绑定该定义、在 `evidence_views.py`/Reporter 展示原结果；仅当现有请求缺少必需字段时扩展 `contracts.py`。`family_space.py` 与 `research_tasks.py` 对这两个参数/Reach 协议无需修改；`extensions/math_analysis/` 无需新增求解器。

尚缺的是通用的“Main 自选机制指标”的注册/单位/计算定义，以及跨任务的适用性绑定，不能从 task score 猜一个机制指标。需要机制研究时应另行定义量及物理模型。PHS/P3 被动问题也没有因此获得 Reach T1 的支持。本轮没有实现全参数自动微分、概率信息价值、Planner 或上述未来接口。
