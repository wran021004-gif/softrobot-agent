# P3 系统消融实验计划（最终准备修订）

仅为权限实现、配置和离线验证交付。历史 Full 已完成，直接复用，不重新创建或运行 Full。本轮没有新的候选、响应曲线或消融实验结果。

Research 从指定基线 f6089b293318df187f72ed21d664b981b086d798 创建 codex/p3-ablation-design-revision-20261112；Core 从 9a8a1fd3feee5d966a5981dd965c2a2ec5c681d5 创建 codex/p3-intent-projection-revision-20261112。Core 先提交和 Push，随后三配置绑定其新 SHA。完整论文贡献、C2 四层职责及跨任务展示冻结在 [Contribution–Mechanism–Ablation Map](Contribution_Mechanism_Ablation_Map.md)。复用既有数学方法和 operation 门禁、No-Knowledge 双角色隔离、No-Math 普通物理搜索路径，不重复开发。

## 论文问题与对照

C1 为 Mechanism-Guided Autonomous Research，C2 为 Composable Mathematical Research，C3 为 Evidence-Grounded Iterative Research；已有推理/数学理论是依据，系统创新在于科研决策、问题组合与证据迭代，不宣称提出新的 KKT、敏感性或双因素交互理论。

| 实验 | 数学能力 | 科研规划 |
|---|---|---|
| Full | ON | 自主、根据证据动态调整 |
| No-Math | OFF | 仍然自主、根据物理反馈动态调整 |
| Fixed-Plan | ON | 预先固定研究路线，不根据中途证据重新规划 |

No-Math 关闭 C2 的数学研究，不关闭 C1 的自主规划。Fixed-Plan 保留所有数学操作，在开始前固定路线、参数组、操作顺序和停止规则；本轮只定义，不开发执行框架或配置。两者不能替代；One-shot LLM Plan 留待未来。

C2 包含 Research Intent Projection、Parameter / Observable Composition、Composable Mathematical Operations、Differentiation / Numerical Validation 四层，而不是五种 operation 的别名。Main 选择假设、研究目标、参数/观测和固定输入/重新优化语义；程序承担冻结结构/任务解析、注册检查、模型/约束绑定、方法适用性、确定性问题生成、求导/数值路由与证据检查。P3 无主动控制，不将 payout 当作主动控制输入。

## 独立实验定义

| 能力 | No-Math | No-Knowledge | No-Pairwise-Interaction（配置 no_interact） |
|---|---|---|---|
| 可选 mechanism_structure_v1 | OFF，五种 operation 均拒绝 | ON | ON |
| inspect / differentiate / optimize / compare | OFF | ON | ON |
| interact 四点交互 | OFF | ON | OFF |
| Main 和 Reporter Knowledge/Skill | 沿用 Full policy | OFF，含缓存/预载检索入口 | 沿用 Full policy |
| 普通生成、FamilySearch | ON | ON | ON |
| 完整被动物理响应及原指标评价 | ON | ON | ON |
| 原 Task / FamilySpace / Runtime / System Prompt | 保留 | 保留 | 保留 |

No-Math 与 No-Pairwise-Interaction 存在包含关系，不能解释为独立加性贡献。No-Interact 仅作为既有配置简称；论文实验名为 No-Pairwise-Interaction，不使用 No-Coupling。

No-Math 用 `mathematical_methods.mechanism_structure_v1=null`；No-Knowledge 仅将原 Knowledge policy 的 `mode` 设为 `off`；No-Interact 增加 `mechanism_operations=[inspect,differentiate,optimize,compare]`。没有同时关闭三项能力。其他组不改变数学 operation 或 Knowledge 权限。

当前 FamilySearch 的 Coupled Block 包装器实质上调用 `MechanismStudy.operation=interact`，不能绕过相同门禁；不是已查明的另一种独立耦合优化能力。保留 `family_search.coupled_block_enabled=true`，No-Interact 仍可做普通坐标搜索、联合参数修改和非 interact 分析。没有把标志关闭当成本次消融。

## No-Intent-Projection 审计与实际四点交互

**Not independently ablatable in current implementation**

Core 有真实的 V4 确定性科学问题编译器。只读原 P3 Trace 找到 25 份 scientific_intent_compilation_v1 收据，证明 Main 选择目标/参数，程序生成实际请求；首个 inspect 与两次 interact 有完成结果，payout/radius 结果被后续长度重分配 Plan 引用。代码存在、Schema 暴露、Main 提交、程序执行和影响后续决策均分别核实，不自动等同。

现有实现没有可独立关闭的自适应投影模块：结构化问题选择属于 Main，编译器承担所有数学请求必须的语义绑定和检查。仅关闭字段补全不等于关闭科研问题构造，关闭编译器又会损及其他数学入口。本轮不造开关、不建 No-Intent 配置或专门测试；未来可另行建立固定模板对照，保留假设、目标和参数组选择及五种 operation，只限制自定义问题组合。详见 [Core 审计](https://github.com/wran021004-gif/softrobot-agent-core/blob/codex/p3-intent-projection-revision-20261112/docs/scientific-question-v4-intent-projection-audit.md)。

P3 Full 的两次四点交互是 payout_offsets_m.tendon_1 × spans.0.radius_m，以及远段 segments.3.physical_parameters.density_kg_m3 × segments.3.sections.0.parameters.radius_m。均为有限尺度 matched_two_parameter_four_point_v1、strict_derivative=false，不是严格混合偏导。操作级消融仅禁止 interact，不禁止其他四种数学操作、普通坐标搜索或联合参数修改；Coupled Block 包装器调用相同 operation，因此同样受限，不据此声称历史专用包装器已被使用。

## 三配置、身份和 Store 隔离

| 文件（相对 configs/research/） | Study ID |
|---|---|
| [study_p3_ablation_no_math_v1.json](../../configs/research/study_p3_ablation_no_math_v1.json) | `p3-ablation-no-math-20261112` |
| [study_p3_ablation_no_knowledge_v1.json](../../configs/research/study_p3_ablation_no_knowledge_v1.json) | `p3-ablation-no-knowledge-20261112` |
| [study_p3_ablation_no_interact_v1.json](../../configs/research/study_p3_ablation_no_interact_v1.json) | `p3-ablation-no-interact-20261112` |

文件与原 Full 同目录，继续解析原 defaults、`family_space_p3_passive_v2.json`、`runtime_phs2d_topology_successor_20261106.json` 及原 TaskDefinition。三份配置的 `base_commit` 均绑定本次先提交的新 Core SHA `ac4065f27edb357876c18c290ae3983a5bae5793`，不使用字符串 HEAD。

每份 `evidence_destination` 为 `runs/research/<该 Study ID>/private-evidence`。将来启动时使用既有默认独立 Store 路径 `DATA_HOME/runs/research/<该 Study ID>/platform.sqlite`，或在单独授权中明确同样分离的目录；不增加不存在的 Store JSON 字段。本轮不调用 prepare，未创建这些 Store 或任何 Study。

所有新组均从空科学候选池、`agent_choice`、零自由度初始化规则开始。没有 fixed_structure_reference、历史候选、控制或 Store 导入；不向 Main 提供历史成功结构。以下历史基准只用于论文比较，本计划和结果报告不作为 supplied_evidence 或 Knowledge 注入 Main。

## 共同物理范围和数值交付

保留 `passive_progressive_stiffness_dev_v1_2` 的 +X/−X、20 s 五阶段：无载、0.05 N、0.10 N、0.20 N、卸载恢复，各 4 s。步长 0.000125 s、记录周期 0.01 s、阶段末 0.25 s 评分窗、材料观察位置 s=0.7、原低/高位移、恢复、刚度比、接触和同腱约束定义均不修改。

低载位移 ≥6 mm、高载位移 ≤25 mm、恢复残差 ≤2 mm、渐进刚度比 ≥1.5；Middle 为原机制记录点。最终最佳候选必须报告双方向完整数值和实际违反量；缺测为 UNKNOWN。违反原阈值不能称为数值可行，更不能将有限预算未通过说成设计域无解。

最终最佳响应使用原 `final_evaluation` 的每段 2 cells；可选筛选精度不替代这个数值模型口径，不追加其他网格或收敛要求。

本次是数值研究比较，不追加 fresh validation_source Replay、半步长、初态扰动、成功后重复检查、成对腱因果证明或正式 SELECT 认证。TaskDefinition 和 Evaluator 自身仍保持原语义，不把未取得正式认证改写成 certified pass。

为避免 No-Math 连带关闭搜索，有限物理预算下的普通 FamilySearch `passive_task_response` 复用现有物理响应执行入口，三个组采用同一路径；完整两方向、五阶段，不接受 execution_profile 覆盖。该路径按原诊断约束的违反量排序，保留接触和腱检查，排除本轮未要求的 paired mechanism proof，明确不授予正式 acceptance。它不调用可选机制数学 Worker。静态 equilibrium 诊断仍属于 No-Math 禁用范围。

## 历史 Full 比较基准

Study：`p3-passive-progressive-stiffness-autonomous-20261110-v1_2`，最佳候选 `candidate_2915`。只复用 [P3 Full 整理](../full_results/P3_full_results.md)，不重跑、也不作为新组初始候选。

| 指标 | 历史 +X | 历史 −X |
|---|---:|---:|
| Low displacement | 6.01794 mm | 6.01794 mm |
| Middle displacement | 11.11727 mm | 11.11727 mm |
| High displacement | 17.75103 mm | 17.75103 mm |
| Recovery residual | 0.001246 mm | 0.001246 mm |
| Progressive stiffness ratio | 1.537391 | 1.537391 |
| Contact | 0 | 0 |

历史成本：Provider 150、数学评价 67、物理 episodes 98、物理 steps 15,680,000。完整 Token/美元费用 UNKNOWN，不作估算。已有可行数值设计、同腱 slack-to-taut 关联与尚未证明唯一因果的边界沿用原报告。

新组除最终指标/违反量，还应报告 Provider、实际数学评价、物理 episodes/steps、提案与有效候选数、失败与 UNKNOWN、停止原因及实际 Token（如原收据可得）。新组硬预算和 Core 版本与历史 Full 有差异（本轮已恢复历史知识准入快照），不能把差异自动归因于单个被消融能力，也不做跨任务效率排名。

## 统一预算、硬上限与停止合同

| 额度 | No-Math | No-Knowledge | No-Pairwise-Interaction |
|---|---:|---:|---:|
| Provider requests（Main + Reporter） | 200 | 200 | 200 |
| Protected Provider requests（含在 200 内） | 4 | 4 | 4 |
| Mathematical evaluations | 0 | 100 | 100 |
| Physical launches | 150 | 150 | 150 |
| Public operations | 800 | 800 | 800 |
| 每次 FamilySearch proposals / evaluations | 24 / 16 | 24 / 16 | 24 / 16 |

历史 Full 用量为 Provider 150、数学评价 67、物理 episodes 98、steps 15,680,000；本轮选择较大统一硬预算，不要求用满。200 是共享总额，包含 4 个 closeout 保护请求，不是 200+4。预算不会自动增加，request_budget_only=false；禁用的 local/offline/BDF/NMPC/RL 计数继续为 0。

现有 config.resolve 将三项计数映射到平台 model_calls/tool_calls/backend_solves，数学额度通过原数学准入及事务计数限制；public operations=800 使用真实 tool_calls。FamilySearch 24/16 是每次请求上限，不是 Study 累计额度。physical_launches=150 限制原 ledger 登记的 backend episodes，数学动态分析也已有 dynamic_cost_bound.episodes 预留；完整双方向普通响应占 2，因此仅做这种响应至多 75 次，且与其他物理调用共享额度。分别报告实际 episodes/steps，不将次数混成求解器内部迭代步数。未设置的累计时间字段保持 null，单 Worker 的有限 watchdog 保留，不增加时间预算体系。

第 200 次 Provider 请求允许按原保护阶段规则正常完成；第 201 次不发送。若 200 次内完成且满足原任务阈值，报告成功，并保留原数值支持/正式验收的证据等级区别。达到 200 次仍无满足阈值候选，报告 budget_exhausted；尚有关键评价未完成，报告 incomplete_at_budget，列出缺失证据。这是实验报告合同，不新增虚构配置字段或 Core 状态枚举。

预算耗尽时保存最佳候选、全部完成证据和实际违反量；没有候选或缺测均明确写 UNKNOWN。若其他硬上限先耗尽或原停止规则先触发，及时停止并记录实际原因，不为了凑满 200 而扩大额度。禁止重新创建 Study、重置 Store、追加预算或切换身份续跑；有限预算失败不能写成设计空间无解。

## Knowledge 快照对齐与实验口径

本轮可直接复用原始资产，无需重构：Research 历史 manifest 的 45 records、17 个 ID 对应 9 个现有源文件（253081 bytes），原文和准确版本已恢复为 Core 打包资源。对历史内容只做一次一致性核对，全部相符。三配置按历史 manifest 固定所有条目的准确 revision；两个 Knowledge ON 组解析出的完整 manifest 与历史快照一致，No-Knowledge 为 0。因此本轮已解决原 Core 4 条通用知识的资产差异，不采用 4→0 Pilot 回退口径。快照恢复没有导入候选、控制或历史 Full Store。

Main 历史实际读取 7 次：passive-structure-mechanics@1、mechanism-research-process@2、skill-parameter-model@4、skill-witness-replay@3、skill-matched-comparison@4、skill-finite-search@3、skill-continue-or-stop@3。Reporter 读取 9 次：general-routing@1,@2；passive-structure-mechanics@2,@3；validation-qualification@1,@2；general-material-inertia@1,@2；skill-local-to-experiment@4。已核对原 retrieval，不能把全部 45 条准入版本写成实际阅读。

No-Knowledge 继续仅关闭原 Knowledge policy 的 mode；Main/Reporter 检索、缓存、预载和正文输入均关闭，System Prompt、TaskDefinition、工具 Schema、必要物理说明保留。未见 p3-case@3 的本体 read，不声称使用。所有原知识中的历史经验仍标明来源，不写成本 Study 新发现。资产对齐不消除新旧 Core 和预算差异，论文仍需将历史 Full 视为带版本限制的比较基准。

## 验证、Pilot 顺序与未纳入实验

三配置已真实解析；11 项 P3 定向离线 Mock 测试通过，另有 9 项既有 M1 门禁回归通过。验证了方法/operation 的原始入口拒绝、Schema/发现列表、No-Knowledge 双角色及缓存隔离、No-Math 的 Main 搜索入口和物理准入、Coupled 包装器、共同任务/模型一致性和 Full 文件未改。测试阻止网络、子进程和 MuJoCo；没有新科学结果。

后续建议顺序：

1. 用户授权后先做 **No-Math**，检验必要物理搜索链路和有限预算研究行为；只报告该组实际结果，不创建新 Full。
2. 单独授权 **No-Interact**，保持其他机制操作和普通搜索，检查移除实际四点交互后的路径变化。
3. 按上述已对齐 Knowledge 快照口径，单独授权 **No-Knowledge**；不将其与其他两开关同时关闭。

每组启动前绑定精确 Core SHA、新 Study 身份及独立 Store，并确认无历史候选注入。配置的 OFFLINE_PREPARATION_ONLY 说明不是执行授权；本轮不进入步骤 1。

No-Mechanism-Diagnostics 暂缓，No-Inspect 不新增，tracking 数学迁移不要求本轮完成；不扩大执行框架。Reporter ON/OFF 使用历史快照实验，冻结相同工具证据与问题，比较解释/追溯，不能新建完整 P3 Study；本轮也不执行快照实验。No-Knowledge 不能代替 No-Reporter。

正文以 M1 主动控制和 P3 被动渐进刚度为主要定量案例，分别展示详细指标、研究过程和成本。PHS-2D（九段四腱、十工况）作为补充案例；其他已有正式任务按真实结果整理附录任务表，展示定义、核心结果与证据等级。不同 Study 的成本与指标不直接合并。具体证据分工见 Map。

本轮提交顺序为 Core 提交/Push → 三配置绑定新 Core SHA → Research 提交/Push。两个新分支均来自指定基线，不合并 main、不 force-push；历史 Full、TaskDefinition、FamilySpace、Runtime 和物理阈值不改。交付只代表准备完成，停止等待首个 P3 No-Math Pilot 的单独授权。

**PREPARATION COMPLETE — NO STUDY STARTED**
