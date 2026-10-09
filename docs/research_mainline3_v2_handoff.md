# Research Mainline 3 V2 interface handoff — conditional, 2026-10-09

V2 is prepared as the next separately scoped development goal, but V1 has not passed. A remains accepted; B has one valid new timing report, no valid new reach report, no two-report synthesis or completed final dispositions, and a failed material audit. C was not executed. See the [current V1 delivery](research_mainline3_v1_completion.md) and [facts](../evidence/research_mainline3_v1_complete_20261009/delivery_facts.json). Historical missing responses and unresolved reservations remain sealed; their recovery is not a prerequisite for fresh authorized work.

The next development order remains limited tendon counts and actuator layouts, then segment-count changes, then finite necessary combinations. No topology combinations were implemented or validated here. The existing concrete interfaces and comparison requirements below remain the handoff; no architecture or scheduler redesign is proposed.

The subsequent offline correction-policy repair enables the new activity's two planned and at most four actionable corrections per stable report/disposition target. It preserves counts across report versions, session restoration and redispatch in the existing project ledger, with task allocations 12/4/6/18 and the common 40-request ceiling. Historical limits and STOP states remain sealed. See the [focused additions to the existing offline gate](../evidence/research_mainline3_v1_correction_policy_20261009/offline_gate.json). No new B report, disposition or C execution is claimed by this repair; V2 readiness remains conditional on the missing V1 evidence.

Changed or exposed gaps: the model-response content gates were removed throughout the affected paths; full original responses now persist before business processing. Request purposes are enforced separately with actual dispatch counts and original role deadlines. Explicit restoration must retain the immutable catalog supplied to the model; the local repair verifies unchanged contents/owners before binding it. Large principal correction histories can still exceed full-input capacity. New reports must correctly distinguish an available failed recomputation from an absent result, and must satisfy original-evidence inspection and per-source applicability requirements. These are material closeout gaps, not evidence of reasoning-token exhaustion.

The [timing report](../evidence/research_mainline3_v1_complete_20261009/timing_report.json) and [audits](../evidence/research_mainline3_v1_complete_20261009/principal_material_audit.json) preserve useful partial work. Completing the missing new reach report under appropriately scoped authority, then two-report synthesis/dispositions/audit and the fixed C case, remains necessary before declaring V1 closed. No unused ordinary or recovery quota can be transferred to bypass the exhausted reach correction allowance.

## 现有代码与需补齐的边界

以下路径都指向现有实现。集合可表示与单独构建不等于公共 NMPC 兼容，也不等于实际闭环验证。V1 `candidate.family@1.2.0` 与 `controller.gvs_nmpc@9.0.0` 只覆盖固定近／远段结构和已声明变量。

| 接口／现有位置 | 已有表示或实现 | V2 所需小范围实现与验证 |
| --- | --- | --- |
| [contracts.py](../extensions/tendon_family/contracts.py)：`Design`、`Segment`、`Tendon`、`Actuator`、`Transmission`、`Discretization` | 组件、绳、执行器集合及命名连接；绳起点、导引、终点；离散网格 | 冻结少量具名模板，显式组件／绳／执行器 ID、顺序、传动与限值；不以任意 JSON 编辑冒充受支持公共设计。 |
| [candidate.py](../extensions/tendon_family/candidate.py)：`build`、`apply`；[design_decisions.py](../extensions/tendon_family/design_decisions.py)；[parameter_capabilities.py](../extensions/tendon_family/parameter_capabilities.py) | 模板结构和离散选择先编译；当前公共语义变量仍是近／远段 | 增加有限模板的版本化选择声明、授权和可发现兼容域；保留源相对修改及候选事实；旧版本继续拒绝新增拓扑。 |
| [compiler.py](../extensions/tendon_family/compiler.py)：`resolve`；[routing_radius.py](../extensions/tendon_family/routing_radius.py)：`locations` | 拓扑生成 parts、DOFs、entity_map；每根绳合法通路；传动矩阵为绳数 × 执行器数 | 对新增／删除组件检查引用、导引孔、绳直径、间隔、跨段路由；保留物理所在段归属，远绳过近段孔仍归近段，共享孔仅修改一次。固定点／刚性附件的祖先归属随新拓扑核对。 |
| `compiler.resolve`；[gvs.py](../extensions/tendon_family/gvs.py)、[gvs_casadi.py](../extensions/tendon_family/gvs_casadi.py) | 当前规则要求每根绳唯一传动并被驱动；约化输入依实际绳顺序 | 显式区分绳张力与执行器命令空间。布局改变须检查传动比／符号、共驱映射、执行器限值如何约束各绳和输入雅可比；不假定新执行器布局仍是六个独立理想张力。 |
| [gvs_structure.py](../extensions/tendon_family/gvs_structure.py)、[gvs_basis.py](../extensions/tendon_family/gvs_basis.py)：`resolve_basis` | 基函数／节点由组件与附件结构生成；保留结构 ID 与分段积分 | 新段数／网格重建约化维度、坐标顺序与结构节点；不复用旧 12 维约化／48 维后端向量的数值位置。保持局部单位、弯曲轴和积分约定。 |
| [scene.py](../extensions/tendon_family/scene.py)：`assemble`；`contracts.Initial` | 命名 `qpos_rad`／`qvel_rad_s` 映射编译 DOFs，未知关节拒绝，未指定零 | 新版本显式语义初态映射，见下节；零默认不能隐式替代总远段弯曲条件。记录新旧状态身份、映射误差及初始化规则。 |
| [gvs_profile.py](../extensions/tendon_family/gvs_profile.py)：`checked_reach`、`reach_numerical`、`candidate_numerical` | 当前固定拓扑兼容；小命名初态；历史张力仅数值猜测，当前测量状态重新生成 | 新拓扑要独立版本化兼容检查、输入／力界顺序、初态约束、数值猜测与不可兼容原因。历史状态、平衡、计划与评价不能重绑定；维度不匹配的张力猜测也不可照搬。 |
| [gvs_nmpc.py](../extensions/tendon_family/gvs_nmpc.py)：`workspace_key`、`resolve_gvs_nmpc_control` | 基于任务、机器人、参数构建控制工作区和动力学图 | 重建 shooting 状态／输入维度、权重尺度、限值、约束和图；新布局不通过只改一个缓存键获得支持。既有 V7 停止配方与 V8 实验行为继续分开。 |
| [gvs_projection.py](../extensions/tendon_family/gvs_projection.py)：`description`、`project`、`discretize`；[backends.py](../extensions/tendon_family/backends.py)、[mjcf.py](../extensions/tendon_family/mjcf.py) | 两主轴铰链／单元，按实际长度积分基函数与曲率投影；后端物理模型生成 | 新段／网格重建 qpos/qvel 映射、cell lengths、惯量与控制 entity_map；核对投影／反投影残差、单位、轴、绳导数和实际 MuJoCo 模型。构建成功不等于完成动力学运行。 |
| [research_execution.py](../tools/research_execution.py)：`prepare_candidate_tool`、`linearize_configuration` | 候选原始所有权、完整 content identity、分析协议与工作点绑定 | 新配置必须贯穿编译、数学工作点、控制器、执行和评价；旧线性化／指标／端点结果不得贴到新拓扑。新的科学计算必须单独授权。 |
| [research_tasks.py](../tools/research_tasks.py)：`task_adapter`、`assemble_acceptance`；[research_joint_evaluation.py](../tools/research_joint_evaluation.py)：`evaluate` | 到达与跟踪分别适配；评价绑定任务、配置、执行 ID 与报告 | 冻结世界坐标目标、mount、重力、时间网格、初态、seed 与阈值；新尺寸导致可达域变化须显式比较。物理失败、工程无效、缺材料分开；不得反套新判据到历史结果。 |
| [platform_host.py](../tools/platform_host.py)、[platform_registry.py](../tools/platform_registry.py)、[platform_store.py](../tools/platform_store.py) | 输入／依赖内容身份、版本封存、缓存与原执行来源 | 结构、路由、绳／执行器顺序、离散、初态、任务或控制器变更均核对缓存失效；版本升级显式新快照，旧记录保持原身份。读取旧评价不是新执行。 |

## 初态映射的具体要求

以语义总弯曲为约束，例如 `theta_far = integral kappa_far(s) ds`（离散后为 far 段各单元主轴角之和），不能把旧状态数组复制到新长度或新维度。首先保留 world mount、局部弯曲轴与符号，声明远段弯曲方向／总角及对应语义速度；按新长度、结构节点和基函数分配曲率，再通过新投影得到后端命名关节状态。速度同样由新映射导出，不用索引拷贝。

新增段初始曲率和速度、删除段后弯曲如何保留必须预先明确；不能用事后调节初态优化结果。记录每段积分、末端姿态和投影残差，并检查当前兼容入口的小关节条件（当前 reach envelope 的角度绝对值不超过 0.05 rad、角速度不超过 0.5 rad/s）。若新语义初态不能在原限制中表示，需新的显式版本和任务初始化声明，不能放宽历史阈值。本任务未实现该映射算法。

## 后续有限案例与比较约束

先冻结四个具名槽位：基线 `T0`；仅改变有限绳数／布局的 `T1`；仅改变段数的 `T2`；一个必要的代表组合 `T3`。每个槽位提交完整组件／绳／执行器清单和实际数目、路由及网格，检查支持后才定最终身份；本文件不虚构尚未审查的具体数目，也不授权全部笛卡尔组合或通用优化器。不能把“可由 schema 表示”当作进入有限比较清单的证明。

每个案例的资源表至少记录总长、各段截面／材料、质量／惯量、绳数、执行器数、每路张力限值、传动／力臂与总驱动能力。执行器共驱时不能简单把各绳上限相加宣称总能力；理想张力模型与真实电机能力分开。任务目标、重力、mount、初态语义与运行时间相同的比较须注明改变尺寸后的可达性；资源变化与控制改进不能混称。

验证分三层：离线具名模板编译／路由／维度／初始化／投影／缓存与来源检查；生产公共发现→准备→分析绑定→执行请求的无科学替代检查；最后在另行授权的有限预算下执行真实数学准备和闭环评价。每一步保留构建、数值准备、控制器构建、完整有效执行与物理验收的独立状态，不以一次 isolated construction 跳过其余步骤。

仍未实现的工程缺口：有限拓扑公共选择与版本域、新输入／执行器限值映射、语义初态映射、拓扑控制兼容、后端投影跨维度验证、任务适配与资源公平比较、新身份缓存／评价全链检查及真实有限案例。缺少 shear、stretch、torsion、摩擦与电机动力学的原模型限制继续显式保留。V1 最后持久化修复仅有离线验证，B/C 的缺失也仍是交接限制。

## 前一交接草案（历史记录，不是当前前提）

2026-10-08 新活动 `mainline3-v1-finish-dcf23687722e` 的阶段 A 正式处置与独立审查通过。阶段 B 已开展新的协调者和两名调查者执行，但到达调查耗尽冻结分配的 8 次请求、计时调查第 8 次响应保存失败且原请求未确认，未形成两份有效报告。阶段 C 未启动。**版本一尚未整体完成，本文件不是版本二开工许可。** 当前事实与账目见[版本一交付](research_mainline3_v1_completion.md)。

旧原件逐字节保存在 `evidence/research_mainline3_v1_finish_20261008/previous_research_mainline3_v2_handoff.md`。旧科学审查理由的不足有追加修订说明，旧 STOP、结论、费用和未知请求均未覆盖或释放。

进入版本二前，需解决计时原请求未确认状态，明确原冻结节点分配与后续授权关系，补齐 B 的有效报告、协调综合、最终主模型处置及独立审查，然后执行 C 唯一固定半径配置的数学与完整闭环验证。完整有效的物理失败可交付；不能为争取通过而调参。

继承事实目录、精确句柄展开、显式对象投影、报告支持与主模型新增依据及范围分离、公共读取记录、具体反馈、版本绑定分项指标和官方结果分离、独立审查及完整档案。第四次安全诊断和第五次身份字段反馈修复仅离线覆盖，不能暗算为新的真实验证。工程交接还需预留调查最终报告的交互机会、提示剩余查询预算，并在不发布被拒绝正文的前提下保留可核对的接收、token 和持久化安全元数据。未知请求先核对，不盲重发。

满足版本一条件后，版本二按“**有限绳数与布局 → 段数 → 必要组合**”安排另行冻结的有限比较清单、身份、任务、控制、判据和预算。局部代理或单步预测不证明闭环、实机或全局最优。本轮没有开发这些结构。

## 历史交接原文（旧活动记录，非本轮状态）

2026-10-08，活动 `mainline3-v1-facts-5b50c31fc0f0`。见[本轮版本一报告](research_mainline3_v1_completion.md)。事实选择接口、确定性展开、公共来源／读取校验及两份真实正式处置已覆盖；科学解释门禁失败。新协调调查和固定半径科学执行均未发生，因此版本二不能进入。

阻塞是到达处置仍将已记录的 free_reach 官方 task_accepted=false 解释为 reach success unknown rather than measured-failed。缺少独立标准只限制复算，不能覆盖官方失败。原决定和正式记录保留，没有人工改报告或额外模型裁判。主模型专用纠正 2/2 已耗尽，不得借用协调预算、重命名节点或重置计时。本轮模型请求 4、项目工具 12、实现修复 3/4、付费纠正 2/6、数学及后端 0。

后续首先需要在明确权限与预算关系下处理该科学解释，区分官方结果与未提供的独立判据，不能重开旧停止活动、释放旧未知预留或改写原失败。结构通过不等于科学解释通过。最后模型响应 `85762c243ff0526de3328825f99f9b9ffbd8eb6edc3e385d72a9a20857cdc8b7`、选择与展开见本轮 `stages/reuse_bundle.json`。真实最终处置是在 `622a5a0` 本地重验，`7816a2d` 的纠正上下文收尾增补只有离线覆盖。

处置门禁通过后，才能真实执行协调者提出的两个不同子调查：必须有两名新调查者自主按需读取、后续真实请求、有效报告使用和主模型正式决定，不能拿旧报告代替。协调门禁通过后再执行唯一固定案例：近段半径比例 1.01、远段 0.99，起点 `evidence/research_native_development_v3_20261007/store/artifacts/3ae03b4e4ddac2e5099ae5823fc0dd7dd9d338dfba6b7d435729d4e5ab41665b.json`，`candidate.family@1.2.0`、`controller.gvs_nmpc@9.0.0`，其余结构、权重、任务和继承 v7 的规则保持。完整有效但物理任务失败必须如实交付，不能调参或第二次后端尝试争取通过。

版本二未来范围仅准备为另行有界授权的绳数、绳路布局、段数及必要组合。本轮没有实施这些开发、扩大搜索或升级实验控制器 v8，没有实时部署或收益结论。
