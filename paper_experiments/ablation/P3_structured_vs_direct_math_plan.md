# P3 Structured vs Direct Mathematical Research

2026-11-12。本轮只准备两个独立配置，不创建或启动 Study，不调用 Provider，不启动 Main/Reporter、数学 Worker 或 MuJoCo。两个仓库分支均为 `codex/p3-structured-direct-math-20261112`；Core 从 `16d72fe82263a44a83ca8dc6f8111b4b0e6c1858`、Research 从 `fa863e1de0ac41664c62dd1f582604db0d4e1c14` 开始，保留原有准备文档和历史配置。最终配置的 `base_commit` 绑定本轮已提交 Core，配置不是执行授权。

已提交并推送的共同 Core：`4e5a25dd6a418b71892df29e9fd61a477de37790`。两份配置均绑定此完整 SHA，独立身份如下。

配置解析和未来获授权后的执行必须从这个 Core checkout 使用其 `tools.research`；Research 基线仍含历史同名目录，不能让 Research 当前目录抢先解析旧模块。将运行数据 home 指向 Research 工作树、配置使用其绝对路径，代码工作目录保留在指定 Core。此处只说明运行绑定，不执行启动命令。

## 科研问题及共同输入

**C2: Composable Mathematical Research** 的主张是，将现有底层数学能力组织成能处理显式科研意图、构造数学问题、选择并组合数学操作的结构化研究层。比较这一组织层，而非有无数学、是否允许任意表达式、或是否保留必需物理验证。

| 项目 | Full-Selective | Direct-Math-Tools |
|---|---|---|
| Study ID | `p3-full-selective-20261112` | `p3-direct-math-tools-20261112` |
| 配置 | [study_p3_full_selective_v2.json](../../configs/research/study_p3_full_selective_v2.json) | [study_p3_direct_math_tools_v1.json](../../configs/research/study_p3_direct_math_tools_v1.json) |
| Main 高层接口 | 现有 ScientificQuestion V4 → mechanism_structure_v1 | research_math_api；不暴露 research_analysis 或高层机制操作 |
| 研究组织 | Main 做科研选择，由结构化层构造/组合合法数学问题 | Main 显式选参数、观测、条件、底层函数、调用组合与结果解释 |
| 底层数值函数和检查 | 同一实现 | 同一实现 |
| 普通 FamilySearch | 直接 passive Replay adapter | 完全相同 |
| Knowledge / Main 决策 Skill / Reporter | 相同冻结内容、版本与角色设置 | 完全相同 |
| 初始化 | 空 Store、空候选池、agent_choice | 相同规则，独立 Store；不强制两个自主模型给出相同首次结构 |

TaskDefinition、FamilySpace、物理模型、设计域、两方向、五阶段20 s、dt=0.000125 s、采样与资格阈值、最终两 cells/segment、Runtime、gpt-5.6-sol/medium、account3:8789 和 Reporter 设置均沿用实际 No-Math 运行基线。不更改任务或评价器。

不导入历史 Full/No-Math Store、成功候选、候选参数、控制方案或历史成功初始答案。两个默认 Store 路径为 `runs/research/<study_id>/`，evidence destination 分别为其 `private-evidence`，配置的空 history/mathematics/control_seeds/background 保持；当前这些 Store 均未创建。

## 高层操作与底层 API 映射

底层函数是从实际调用链定位的，未重写算法。Core 文档包含完整函数和权限映射：[p3-structured-vs-direct-math-20261112.md](https://github.com/wran021004-gif/softrobot-agent-core/blob/codex/p3-structured-direct-math-20261112/docs/p3-structured-vs-direct-math-20261112.md)。

| Full 高层操作 | 原底层函数 | Direct 如何组织 |
|---|---|---|
| inspect | 共享 model_evaluator → PassiveModel / passive_equilibrium.mechanics / solve / tangent，或 passive_execution.execute/execute_pair；原 metrics、observe | model_evaluate；对保存的记录调用 observe；显式给候选、观测、参数值和物理条件 |
| differentiate | differentiation_router.stencil / differentiate；适用时 re_equilibrated / task_design_sensitivity；同一有效性检查 | stencil、finite_difference；Main 决定研究参数及观测，自己决定是否继续其他调用 |
| optimize | 共享模型 callback、归一化坐标、SciPy minimize/Powell 和原 task-improvement projection | minimize；Main 选择变量、局部范围和预算，按需先做差分，自己解释有效性和候选修改 |
| compare | 原数值求值、NumPy 差值、min/max、observed_task_improvement | 分别求值或选择已有精确记录，调用 subtract/minimum/maximum/observed_task_improvement，自行解释匹配和取舍 |
| interact | matched_points、同一模型求值与 interaction_evidence | Main 先设计四点，再独立调用求值、显式复用已有点，最后对四点来源调用 interaction_evidence；没有高层研究操作代办整条链 |

Direct 白名单有 11 个函数：`model_evaluate`、`stencil`、`matched_points`、`finite_difference`、`minimize`、`interaction_evidence`、`observe`、`observed_task_improvement`、`subtract`、`minimum`、`maximum`。结果保留数值、单位、参数域、条件、有效性、原始记录指针与成本；`sources`/`source_record_indices` 只能选择当前 Study 自己保存的 Direct 数值记录，不能提交任意代码、表达式或外部结果。

Full 五操作全部开启；Direct 高层 grant 为 null，实际分析入口同时拒绝高层绕过。Direct 不经过 compile_question、MechanismStudy 或高层结构数学 calculate，而使用提取出的共享模型求值函数和原数值 API。必要的模型/任务绑定、类型/单位、约束、适用性、KKT/活动集、数值一致性和 Worker 预算检查始终保留。

本对照覆盖 P3 被动模型的既有数学研究能力，不声称 Direct 具备任意符号公式或其他主动控制任务的全部 API。局部有效性不自动成为全局下降、最优性、任务验收或硬件结论；not_defined、not_comparable、缺失成对机制均按原义保留。

## 普通物理路径与计数

两份配置共同将普通 FamilySearch 限定为 v1 mixed / passive_task_response，`physical_launches=150`，因此沿用已验证的 `passive_search.physical_response_search → evaluate_physical → passive Replay` 路径。普通 FamilySearch 不使用静态数学模式或 Coupled Block 包装；Full 的显式 interact 和 Direct 四点 API 仍可在数学入口中执行。

该路径只根据 v1、mode 与有限物理预算选择，不根据数学 grant 开关；开启 Full 数学不会回退旧 inspect/analysis 搜索适配。普通响应 math=0，episode/step 按原执行记账。数学 API 的内部动态执行仍记录为数学来源，不写成普通 Replay；其真实积分同时占用既有共享物理硬额度，不能借区分类别获得额外150次。

数学计数复用现有机制：单点模型评价计1；有限差分按原 baseline+stencil 点预留；Powell 按显式 cap 预留；stencil/四点设计及已保存数值的观测/算术归约不产生新的模型评价，但仍记录真实 API 与公共操作。报告保留预留/收费与实际模型调用、复用、episodes、steps，不能将语义操作数、低层调用数和积分次数混为一谈。

## 共同研究动作选择指导

新 Knowledge Skill `research-action-selection-and-stopping@1` 在两个配置中完全相同：历史45条/17ID，加同一Skill后为46条/18ID。通过既有 catalogue/manifest 解析；`knowledge.main_context_entries` 将其完整冻结正文自动放入 Main 的 `FROZEN_MAIN_RESEARCH_GUIDANCE` system prompt，而非只展示目录或等待检索。

内容来自一次 Pilot 的抽象经验，明确标注泛化未验证，不含成功候选 ID、具体获胜参数或可重建答案。两组都获得：

1. 先分离任务违反量、非法结构/路由、资格失败与证据缺失。
2. 数学前明确竞争解释、不同结果将改变的行动、直接物理替代和预计成本。
3. 仅选择最小必要、适用的计算，禁止把无效导数当有效方向。
4. 查重、复用并区分失败工具回执与已经完成保存的科学结果。
5. 根据已测权衡考虑合法中间试验，不固定历史参数答案。
6. 研究后判断新增证据、假设/参数/路线改变或仅确认原判断。
7. 按冻结数值与物理资格、强制证据及硬预算停止，不忽略资格，也不无限追加可选分析。

离线检查证明两组会构造相同正文；当前无 Main 运行，不能称 Main 已阅读或采纳。未来获授权运行后，由已有 Provider 原始 wire 核实实际可见的条目、revision 和内容身份；阅读、理解、采用与决策收益分别报告。

## 统一硬预算与停止

| 资源 | 两组相同 |
|---|---:|
| Provider（Main+Reporter） | 200，内含保护4，不是200+4 |
| Mathematical evaluations | 100 |
| Physical launches（共享硬额度） | 150 |
| Public operations | 800 |
| FamilySearch proposals / evaluations | 每次24 / 16 |

不自动追加、重置、换身份或创建新 Study 续跑。请求200允许按原保护规则结束，201发送前禁止。保留原 No-Math 数值停止合同：必要物理资格和最终完整双方向响应齐全、原阈值满足即可按证据等级报告数值成功；不单独要求 Full 取得成对因果、额外 Replay、半步长、初态扰动或正式 SELECT。数值成功不等于正式认证，未取得的 M3/因果证据仍 UNKNOWN。

达到请求上限仍无阈值通过候选，报告 budget_exhausted；关键评价未完成报告 incomplete_at_budget，并保存最佳已完成候选、实际违反量与缺测。其他硬资源先耗尽时报告实际原因，不推断设计空间无解。

## 实验解释与验证状态

本轮不是 No-Math，也不是把不可独立关闭的意图投影再包装成一个权限开关。主要差异为整个语义化数学组织层 ON/OFF；底层计算能力、普通物理响应、Main 决策指导、Knowledge 与 Reporter 共同保留。原 No-Math 及 Full-Historical 结果保持；本轮不增加第三组，也不启动 Fixed-Plan、No-Knowledge、No-Pairwise、M1 或其他任务。

正式比较应报告首次核心数值通过、首次严格物理资格通过、完整评价/正式验收边界、结果影响下一决策的证据、实际模型与物理成本及失败来源。单次匹配实验仅是探索性证据，稳定定量结论需要独立重复，不能用两次总请求数直接归因结构化层。

定向离线验证使用 Core 的新 Direct 测试与现有 P3/M1 权限回归。阻断网络、subprocess/Worker 与 MuJoCo；只用配置解析、Mock 和纯数值函数，没有 Host、Store、Study、Main/Reporter。原配置和历史结果不修改。最终结果：Direct 18项、原P3 11项、原M1 9项全部通过，共38项；未执行全量测试。

PREPARATION COMPLETE — NO STUDY STARTED
