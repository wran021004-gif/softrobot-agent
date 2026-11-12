# Contribution–Mechanism–Ablation Map

本表冻结论文贡献、可观察机制和实验问题，避免将理论名称、Schema 准入或工具授权直接写成实际科研收益。历史 Full 与 No-Math Pilot 结果只复用，不重跑。本轮准备 Full-Selective 与 Direct-Math-Tools 两组，均未启动。

## 三个论文贡献

| 贡献 | 论文主张与系统机制 | 理论依据 | 可检验的证据 |
|---|---|---|---|
| C1: Mechanism-Guided Autonomous Research（机制驱动的自主科研决策） | Main 根据物理现象提出可检验假设，自主选择数学分析或物理实验，依据新证据调整研究方向 | Abductive Reasoning；Hypothesis Testing；Active Diagnosis；Sequential Research Decision Making | 假设—预期/削弱观测—行动—结果—下一决策链；由 Fixed-Plan 对照动态规划价值 |
| C2: Composable Mathematical Research（可组合的数学研究能力） | 将底层数学能力组织成能够理解显式科研意图、构造数学问题、选择并组合数学操作的结构化研究层；必要的模型绑定和合法性验证始终保留 | 参数化数学问题；KKT/活动集、局部敏感性、有限尺度交互及数值有效性 | 核心对照为 Full-Selective vs Direct-Math-Tools；前者保留现有结构化组织，后者由 Main 直接组合相同底层 API。No-Optional-Math、No-Pairwise-Interaction 为补充问题；不独立消融意图投影 |
| C3: Evidence-Grounded Iterative Research（证据驱动的迭代与记忆） | Knowledge、Store、Trace、Reporter 支撑跨轮次研究、证据追溯、上下文压缩和结果解释 | 科学证据可追溯性；外部记忆；信息组织与上下文管理；证据驱动的迭代决策 | No-Knowledge 测领域知识输入；Reporter ON/OFF 采用相同历史证据快照的小实验；Store/Trace 本轮始终保留 |

上述数学理论与科研推理思想已有成熟基础。系统创新是科研决策、问题组合、确定性验证和证据迭代的组织与连接；不宣称提出新的 KKT、敏感性或双因素交互理论，也不把所有 C3 组件的价值都归于一个 No-Knowledge 对照。

## 当前 C2 核心对照（2026-11-12）

| 能力 | Full-Selective | Direct-Math-Tools |
|---|---|---|
| Main 自主假设、行动、证据调整和停止 | ON | ON |
| 结构化科研意图/数学问题编译与语义操作组织 | ON：现有 scientific_question_v4 与五种 operation | OFF：不暴露高层 mechanism_structure_v1；Main 明确组织底层函数及输入 |
| 数值能力 | 现有平衡/约束/观测、有限差分、Powell、算术对照、有限四点交互 | 相同共享函数，经 research_math_api 薄适配器调用；无任意代码或表达式执行 |
| 普通物理搜索 | v1 mixed + passive_task_response + finite physical budget 的直接 Replay 路径 | 完全相同 |
| 研究动作选择指导 | 同版 research-action-selection-and-stopping@1，完整内容自动进入 Main system prompt | 完全相同 |
| Knowledge / Reporter / 初始候选 | 历史45条加共同Skill；Reporter相同；空池、agent_choice | 完全相同 |
| 硬预算 | Provider 200（含保护4）、math 100、physical 150、public 800；search每次24/16 | 完全相同 |

这是结构化数学研究组织方式的对照，不是移除数学算法。Direct 可以直接求值、差分、调用求解器、对保存数值做算术并自行组合四点研究；Full 不额外获得数学算法、领域指导或更高预算。共同的动作选择 Skill 优化 Main 的信息价值、重复识别、成本与停止策略，不能归为 C2 结构化层独有收益。

历史 No-Math 更准确称 No-Optional-Math：主动五类机制数学操作为0，但物理评价器仍计算机制指标，Main 曾收到并引用张力/松弛/招募信息；因此它不是 Task-Only Feedback。历史 Full 普通搜索借道数学适配器，和该 Pilot 不匹配，不能用150对42归因 C2。本轮两组明确统一直接物理路径与数值停止合同，不给 Full 单独追加成对因果或独立 Replay 要求。

单次匹配运行仅是探索性对照，稳定量化结论需独立重复。No-Pairwise-Interaction、Fixed-Plan、No-Knowledge、Reporter 快照配对与跨任务案例继续作为其他明确问题，均不在本轮启动；本轮不增加第三组。

细节及未启动声明见 [本轮实验计划](P3_structured_vs_direct_math_plan.md)。旧配置和历史结果保留，下面原有机制盘点不代表本轮新增实验组。

## C1 与 C2 的区别

| 实验 | 数学能力 | 科研规划 |
|---|---|---|
| Full | ON | 自主、根据证据动态调整 |
| No-Math | OFF | 仍然自主、根据物理反馈动态调整 |
| Fixed-Plan | ON | 预先固定研究路线，不根据中途证据重新规划 |

No-Math 关闭数学研究能力；Fixed-Plan 关闭动态科研决策能力，两者不等价、不能互相替代。Fixed-Plan 保留全部数学操作，在开始前固定研究路线、参数组、数学操作顺序和停止规则，后续证据只按预定规则执行，不重新规划。本轮只定义，不开发执行框架、不新增配置。One-shot LLM Plan 可作为将来的中间对照，暂不实施。

## C2 的四层组成与决策归属

| 层 | 研究功能 | Main 的科研决策 | 固定程序的确定性工作 |
|---|---|---|---|
| 1. Research Intent Projection | 把高层科研意图转为可计算问题 | 假设、目标类型、参数组、希望观察的现象和期望研究结果 | 当前 V4 仅将显式结构化选择编译并绑定到已有注册语义；不从自由文本自动发明数学目标 |
| 2. Parameter / Observable Composition | 确定设计参数、观测量、任务约束和内层求解问题 | 选择注册参数及观测、效应语义、固定输入或重新优化控制；P3 只能无主动控制 | 解析冻结结构/任务，校验参数与观测注册，绑定物理模型、约束、状态和内层问题，检查方法适用性 |
| 3. Composable Mathematical Operations | 在具体问题上执行 inspect、differentiate、optimize、compare、interact | 选择操作及可承受的局部范围与评价额度，根据结果继续或改向 | 编译精确请求，按原权限、成本和求解入口执行 |
| 4. Differentiation / Numerical Validation | 确定数学结果在何种条件下有效并形成证据 | 解读有效性、比较结果和研究局限，决定下一个问题 | 求导/数值路由、KKT/活动集与约束检查、数值有效性检查、证据生成；无效导数不能改写为有效设计梯度 |

C2 不能缩减为五种 operation 列表。问题构造、参数/观测/约束组合和数值证据边界共同决定数学研究是否可用于科研。

## 冻结的消融问题

| 实验 | 关闭能力 | 保留能力 | 对应问题与本轮状态 |
|---|---|---|---|
| No-Math | 全部可选机制数学研究，五种 operation 均关闭 | Main 自主研究、普通 FamilySearch、完整被动物理响应与原任务评价、结构生成和参数修改 | 数学研究体系整体是否有价值；配置已修订 |
| No-Intent-Projection | 不作为独立实验组 | 必要的模型/任务绑定与验证保留 | 沿用不可独立关闭的审计结论；本轮改为比较完整结构化研究层与直接底层 API，不再单独开发此开关 |
| No-Pairwise-Interaction | MechanismStudy.operation=interact 的双参数四点交互 | inspect、differentiate、optimize、compare、普通坐标搜索、联合参数修改、FamilySearch 的其他合法功能 | 双参数有限尺度交互是否有独立价值；沿用文件名 no_interact |
| No-Knowledge | Main/Reporter 领域知识检索、同源缓存、预载和正文输入 | System Prompt、TaskDefinition、工具 Schema、必要物理模型说明、原数学与物理工具、Store/Trace | 领域知识是否改善效率与决策；配置已修订 |

No-Math 包含 No-Pairwise-Interaction 的能力移除，不能作为完全独立的加性贡献。No-Intent 与 No-Math 也不能混淆：前者若实施，应保留数学能力，仅改变问题构造方式。

## Research Intent Projection 的实际审计结论

**Not independently ablatable in current implementation**

Core 存在真实的 V4 科学问题编译路径；Main 实际选择研究目标、参数和物理语义。历史 P3 Store 保存了 25 份意图编译收据；首个活动集 inspect、payout/radius 与远段 density/radius 两次 interact 均可连接 Main 请求、确定性编译和已完成结果。payout/radius 结果被后续长度重分配 Plan 引用，支持研究路线受到结果影响；不证明该编译层的独立因果收益。

但当前没有独立于 Main 的结构化选择及必需模型/任务绑定的自适应投影模块。关闭字段补全只改变输入填写；关闭整个编译器会同时去掉合法数学问题的绑定和检查。新建模板限制会引入尚未验证的实验处理，不能冒充移除了一个已独立存在的模块。因此不开发开关、不新增 No-Intent 配置或专门测试。保留未来“自适应问题构造 vs 预定义模板”方法方向：Main 仍可提假设、选参数组/目标/模板，模板限制自由组合；程序保留全部合法性、物理约束与数值检查，五种 operation 继续可用。

证据层级必须分别写明：代码存在、Schema 暴露、Main 提交、程序执行、结果进入后续决策；任何一项均不自动推出其他项。具体原始 artifact ID、源码职责及审计限制见 [Core 审计](https://github.com/wran021004-gif/softrobot-agent-core/blob/codex/p3-intent-projection-revision-20261112/docs/scientific-question-v4-intent-projection-audit.md)。

## No-Pairwise-Interaction 的实际基础与范围

P3 Full 实际执行过两次 matched_two_parameter_four_point_v1：

- payout_offsets_m.tendon_1 × spans.0.radius_m。
- segments.3.physical_parameters.density_kg_m3 × segments.3.sections.0.parameters.radius_m（远段 density × section radius）。

两者 strict_derivative=false，结果为诊断比较，不能称严格混合偏导；完成四点计算也不保证存在有效标量交互增益。当前 Coupled Block 包装器调用相同 interact，因此被相同操作门禁拒绝；历史专用包装器是否实际使用仍为 UNKNOWN。实验不命名为 No-Coupling，不声称移除了所有联合参数搜索。

## 统一硬预算与停止规则

历史 P3 Full 实际消耗：Provider 150、数学评价 67、物理 episodes 98、steps 15,680,000；不重跑 Full。新组使用较大统一额度，不要求用满。

| 预算 | No-Math | No-Knowledge | No-Pairwise-Interaction | No-Intent（未创建） |
|---|---:|---:|---:|---|
| Provider requests（Main + Reporter） | 200 | 200 | 200 | 若将来实施，200 |
| Protected requests（包含于总额） | 4 | 4 | 4 | 4 |
| Mathematical evaluations | 0 | 100 | 100 | 100 |
| Physical launches | 150 | 150 | 150 | 150 |
| Public operations | 800 | 800 | 800 | 800 |

全部硬预算禁止自动扩展，request_budget_only=false；使用现有 model_calls/tool_calls/backend_solves 和数学计数，不新增预算框架或虚构字段。FamilySearch 的 max_proposals=24、max_evaluations=16 是每次请求的上限，不能写成 Study 累计额度。保留有限 Worker watchdog；注册动态数学请求与普通物理搜索均通过原 backend ledger 预留 episode，完整双方向普通响应消耗 2 launches（单独只做这类响应至多 75 次，且与其他请求共享额度），实际 episodes/steps 分别报告。

第 200 次 Provider 请求允许在原保护阶段规则下正常完成；第 201 次在发送前拒绝。200 包含末尾 4 次 closeout 保护请求，不能解释为 200+4，也不能为凑满次数突破物理/数学/公共操作上限。200 内完成且满足原任务阈值，报告成功并标明原证据等级；达到请求上限未找到满足阈值候选时报告 budget_exhausted；关键评价未完成时报告 incomplete_at_budget 并列缺失项。保存耗尽时的最佳候选、全部已完成证据与实际违反量，缺测为 UNKNOWN。若其他额度先耗尽，记录实际资源和停止原因。禁止新建 Study、重置 Store、追加预算、切换身份续跑；预算耗尽不代表设计空间无解。这些报告值不伪称新增了 Core 内部状态枚举。

## Knowledge 资产与使用证据

本轮已直接恢复历史准入快照：45 records / 17 entry IDs，9 个原始源文件及其原始索引元数据，正文未重写；一次核对全部 45 条内容与历史 manifest 一致。Core 原打包 4 条通用知识不足以代表历史范围，本轮无需采用 4→0 回退口径。两个 Knowledge ON 组固定相同的全部 ID/版本，实际解析 manifest 等于历史 manifest；No-Knowledge 为 0，并继续隔离双角色检索、缓存、预载和正文。原始来源为 Research 的 memory/ 和 [启动 manifest](../../docs/research/p3-autonomous-study-v1_2-launch-20261110/knowledge-manifest.json)，Core 随包资源和具体版本见审计文档。

| 角色 | 历史实际读取 |
|---|---|
| Main，7 次 | passive-structure-mechanics@1；mechanism-research-process@2；skill-parameter-model@4；skill-witness-replay@3；skill-matched-comparison@4；skill-finite-search@3；skill-continue-or-stop@3 |
| Reporter，9 次 | general-routing@1,@2；passive-structure-mechanics@2,@3；validation-qualification@1,@2；general-material-inertia@1,@2；skill-local-to-experiment@4 |

45 条是可检索版本记录，不能描述成读了 45 条；未见 p3-case@3 本体直接 read。检索、理解、采纳和最终独立增益不同；原始知识中已有历史经验，不能写成 Main 首次发现。恢复资产不等于复现历史 Full；新 Core 和硬预算等差异仍需报告，不能将全部结果差异归因于一个消融开关。

## Cross-Task Evidence 与论文展示

| 任务 | 研究内容 | 展示安排与证据边界 |
|---|---|---|
| M1 | 主动控制 | 正文主要定量案例：详细三条件指标、研究/控制修正过程、数学与物理成本；联合 SELECT 等证据等级按历史报告 |
| P3 | 被动渐进刚度结构设计 | 正文主要定量案例：双向位移/恢复/刚度、机制假设与研究过程、成本；已有数值可行设计，但无完整 fresh 独立验证及唯一机制因果证明 |
| PHS-2D | 九段四腱、十工况被动结构设计 | 补充案例：任务定义、保存的核心结果、证据等级，不要求本轮开展新研究 |
| 其他已有正式任务 | 按真实历史结果整理 | 附录任务表：任务定义、核心结果、证据等级及来源；缺失写 UNKNOWN，不补跑 |

各 Study 的指标、成本和有效性范围分别展示，不直接合并成跨任务总性能或效率排名。历史 [M1](../full_results/M1_full_results.md)、[P3](../full_results/P3_full_results.md) 与 [能力盘点](../full_results/analysis_capability_inventory.md) 是来源，不改写其原结果。

Reporter ON/OFF 继续采用历史快照小实验：冻结相同问题、工具证据和上下文，比较解释与可追溯性；不创建新的完整 P3 Study，也不据 Reporter 产物存在就声称改变 Main 决策。本轮不执行快照实验。

## 尚未纳入与执行边界

Fixed-Plan 仅定义，One-shot LLM Plan 留待后续；No-Intent 缺少独立可消融模块；No-Mechanism-Diagnostics 暂缓，避免连带改变任务响应评价；No-Inspect 不新增；tracking 数学迁移不作为本轮准备前置条件。Store/Trace 关闭不在本轮问题范围。

三组均保留独立 Study ID、evidence destination、空候选池、agent_choice，不导入历史成功候选或 Store，不改变 P3 TaskDefinition、FamilySpace、Runtime、物理模型、评分阈值或评价方式。具体协议与文件身份见 [P3 实验计划](P3_ablation_plan.md)。本轮只完成定义、配置、资产与离线验证，等待另行授权第一个 No-Math Pilot。
