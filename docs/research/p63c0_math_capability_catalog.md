# P6.3-C0：通用数学能力分类与只读目录

基线 `codex/p6-3b6-gateway-repair-retest@85b01a37e97ebe264b4fb060e1d0f80b126ec481`；
独立分支 `codex/p6-3c-math-capability-catalog`。本轮只做源码/历史证据审计、只读发现和定向离线测试。
没有科学 Worker、真实 Provider/Reporter、MuJoCo 积分、MATLAB、GVS 数值计算、NMPC、PPO、NLP 或新梯度实验。
测试中的合成结果不属于科学证据。旧 Study、Store、冻结协议、阈值和历史结果均保持原样。

已读根 AGENTS.md、[模块职责](modules.md)、[P6.2-K 数学审计](p62k_information_and_p63_audit.md)、
[P6.3-A](p63a_math_decision_interface.md) 及[最新 B6 记录](p63b6_gateway_retest.md)。B6 已有一次 Main 自主提交的 Native computed 请求；
结果后自主决策 M3 未通过。这与下文历史案例中的任务 M3 是不同概念。本轮不修复行动循环，也不运行新的 Study。

## 目录职责与查询

`math_capability_catalog.py` 仅拥有五类标签、源码位置、物理输入/输出、前提和跨分支能力说明。
正式方法身份及含义仍取自 `METHOD_MEANINGS`、`registered_analysis_method_names()` 和原非线性模块的 `LIMITATIONS`；
正式模板、授权、适用性、预算、来源和可执行状态全部由原 `mathematical_method_view()` 计算。
没有第二份 `AnalysisRequest.operation` 注册表、执行分派或准入程序。

沿用 `evidence_read(view="mathematical_capabilities", reference=<当前自有候选>)`：

| pointer | 内容与边界 |
|---|---|
| `/operation_categories` | 唯一五类：inspect、solve、analyze、differentiate_optimize、compare |
| `/capability_statuses` | 实现/来源状态的解释，包括未确认来源；不人为编造未知方法 |
| `/capability_inventory` | 27 项已审计能力：原 18 项正式方法，加 9 项未接入的跨分支内核/历史 helper |
| `/capability_inventory/<method_id>` | 标签、输入、观测量、模型、前提、限制、实现位置、实际来源与接口状态；未接入项没有请求模板 |
| `/methods/<原方法名>` | 原候选绑定详情、模板、Schema 查询和动态状态；新增 generic_operations 标签 |
| `/research_opportunities/parameters` | 原参数域、授权、有效性和 method_links，附加 sensitivity_scope 分类 |

现有 `mathematical_catalog()` 保留 v1、原 methods 内容与语义，仅增加标签、分类和 inventory 查询指针。
`listed_methods_implemented=true` 仍只说明其原 methods；不涵盖只读 inventory 中的跨分支条目。
大目录继续用原分页/导航；不会把全部历史能力塞进 L0，也不会给未接入项生成可执行模板。
静态目录既不选择候选/控制源，也不把方法存在解释成 `ready`。

每条能力分开给出：

- `implementation_status`：当前源码、未适配源码、历史 helper 或未确认来源。
- `interface_status` / `has_formal_execution_entry`：是否有当前正式入口。
- `current_execution`：仅复制原候选方法的 planning/execution/executable/missing 字段；未查询候选时 assessed=false，不猜可执行性。
- `source`：当前 checkout 或已核对的分支/提交及本地/远端可用性。源码存在不意味着任务、授权、状态源和预算已满足。

## 九项 Trace：实际工具、结果与决策

[机器可读只读审计](p63c0_trace_audit.json) 记录每项 Trace、原路径/pointer、当前文件可读性、
39 个原 Store artifact 的可读性，以及实际跨分支函数和源码行。
读取使用 SQLite `mode=ro`/`query_only`，没有打开可写历史 Store。
85 个被引用文件和 39 个被引用 artifact 均可读；没有缺失项需要补造。
没有重复计算原 SHA，也没有新增 SHA 准入。私有经验卡只核对路径存在，没有复制正文到 Git。

M1–M6 原计算 artifact 的 `operation=mujoco_direct_control_v1`、`status=computed`、
`implementation=668d2c251608de7ecaacd7c8ae39183777e09962` 均实际读取。
原输入在 candidate/configuration、protocol 和 `/native_dynamics/original_schedule`；
原输出在 `/native_dynamics/optimization`、`optimized_schedule`，独立接受在原 replay/SELECT。
这些历史搜索不是后来具名的非线性 T1/T2 实验，也没有证据表明它们用过 GVS/conic；不能倒填方法使用史。

| Trace / 原来源 | 实际数学、输入/输出及用途 | 真正影响的选择；诊断边界 |
|---|---|---|
| `memory/cases/m1_research_v1`；原六路 Native、三目标 | 结构/零初态/有界张力序列 → 完整 Reach/Hold 样本和最佳已见 J；`native_control.calculate` → 独立 replay | 原结构 central_high 失败及有限续算停滞后，operator 记录分组锚点假设，再为新结构分别适配控制。三条件接受推动 SELECT；停滞不证明不可行。原 SELECT 候选配置为 positive_high，不能标成 central_high。 |
| `m2_research_v1`；原 COM 外力三条件 | 同一 Native 控制核，保留真实载荷、任务时间和严格保持速度谓词 | negative 的未舍入超限仍判失败；原记录约超 8.96e-16 m/s。内部搜索 margin 后的新控制须新独立重放；margin 不改接受阈值。 |
| `m3_research_v1`；0.50 s draft | 原任务/候选绑定的全窗控制优化和 50 ms holding 检查 | 原结构失败后 operator 引用 M1/M2 历史提出结构假设；新控制/重放得到 development draft 接受，未获正式 benchmark 批准。 |
| `m4_research_v1`；timed Tracking | 全时变参考和整段样本 → Native 序列搜索、独立轨迹接受 | 首次重放接受，未记录中途结构改变或额外数学诊断；不能推断结构优越、稳健性或只用 endpoint 代替 tracking。 |
| `m5_research_v1`；位置+有向工具轴 | 实际工具坐标、原采样窗口、六路控制 → 位置与轴联合残差 | 54 callbacks 后首次重放两个谓词通过推动 SELECT；没有额外机制研究记录，不是完整 6D 姿态证明。 |
| `m6_research_v1`；刚性载荷 oriented Tracking | 实际质量/外力/环境、位置/轴/无接触条件 → Native 全窗搜索和完整 replay | 不完整接触/数值失败、变硬后完整但不接受，再分组锚点和新控制，最终独立接受。完整性不等于成功，联合改动不能隔离唯一因果。 |
| `c1_multicondition_research_v1`；`runs/c1_20261029/run_case.py` | `NativeModel.mechanics` 初始 Jacobian/rank；原 `native_control.calculate` 按四条件适配；同 XML 独立 replay | 局部 rank 仅筛选诊断；四腱结构及 2.5 mm 缩短后的四条件接受支撑最终选择。四是已测试最小成功数量，非全局最小。M1_B 采样间速度峰值超限仍记录，无连续时间保证。batch/shorten/export 是编排，不是新数学核。 |
| `phs2d_passive_research_v1`；PHS 分支 | 固定放绳/无主动输入/材料点加载 → 原平衡 KKT、单侧切线 QP、Jacobian/nullspace/modal、腱路行匹配、有效性优先多工况、固定拓扑敏感性；源码见只读目录 | P0 无合格基准即停；Round2 有效但未成功；Round3 局部行匹配优秀仍因松弛/有限力失败，促成真实导向孔/几何/材料对照。六搜索+四首次 holdout 的独立动态、半步长和扰动通过是开发性数值见证，无正式 TaskAdapter/SELECT。局部匹配与静态梯度本身不决定接受。 |
| `p3_passive_progressive_stiffness_v1`；本地 P3 两分支 | 被动 KKT 静力筛选；`passive_response.run_schedule` 连续加载/逐步约束观测；`passive_evaluation.response_metrics/evaluate/mechanism` 算刚度、张紧切换和有效配对消融 | c16 静力良好后动态长度超限；c17/c18 UNKNOWN 保留，只读复算 INVALID；c25 无效消融不算机制证据。c26 冻结后双向动态与有效消融支撑开发见证；1/2 cells PASS，4 cells INVALID，四单元机制 UNKNOWN，空间收敛未证实。 |

以上九项的假设选择、结构改动与停止/SELECT 均属 **Codex/operator 或固定 supervisor 编排**，不是 Main 自主发现。
物理重放和独立 evaluator 属验证层；数学分数、Jacobian、秩、KKT、模态、导数属不同强度的证据，不能互相替代。
历史脚本中的批处理、画图、导出和预算 orchestration 不列入正式数学执行注册。

## 当前入口与未接入能力

原正式接口仍是 18 项方法，具体机器清单以目录函数为准：
GVS/SoRoSim 的 linearization、controllability、equilibrium、input/design sensitivity；
Native mechanics、短响应、固定输入结构响应、完整序列控制；
affine endpoint、braking、instantaneous braking、trajectory feasibility、task capability；
conic minimax/受控敏感性；Native Reach 的非线性 T1/T2。

Reach/Hold 可使用原适配方法；timed Tracking 有原 affine sampled/conic 和 Native direct 序列路径；
工具轴/loaded oriented Tracking 仍需适配完整约束的 Native 路径，不能用原 affine/GVS 或 Reach T1/T2 丢掉轴条件。
C1 是子任务集合，没有单一 C1 T1/T2 或数学 TaskAdapter。范围与动态授权仍由原程序决定。

未接入的九项见 `/capability_inventory`：七项 PHS 平衡/顺应性/模态/Jacobian 匹配/几何/敏感性/多工况能力，
以及两项 P3 load metrics 和配对机制 helper。模态项同时暴露腱长、末端和材料点 Jacobian，及约束零空间/单侧锥；
敏感性项同时包括重新求平衡 FD 核对；不另复制相同计算注册成多个“求解器”。
`passive_multicase_design_v1` 明示 `screen` 是编排，只有 `multicase_metrics` 算术可独立复用。
P3 连续动力学 runner 与 evaluator 保留在历史分支，不移植、不伪装成主动控制 schedule。

本轮 `git ls-remote` 核对 PHS 远端为 `9d6d160e050c836b87d0563a497fc0ec1c3761a8`，本地同提交且目标源码无未提交修改。
P3 本地 `codex/passive-progressive-stiffness@83d9b8f35b4015a924e0f8c32d073607247f92b9`、
`codex/p3-spatial-fidelity@f0379f8508025f350b6ddfaeaf92c8b8401f0c97` 可读，目标分支远端查询没有返回 refs，
故不声称远端发布或验证了 P3 求解实现。knowledge-integration 分支的 Trace 不等于求解源码。
现有 GVS 核保留；历史九项未使用它，不构成删除理由。

## 参数类别—物理问题—可用数学方法

权威域和真实路径来自 `family_space.parameter_capabilities()`；Study 授权和方法链接来自
`optimal_capability.family_analysis_parameters()`。本轮未增加参数域，也未给任何参数新增敏感性授权。
`sensitivity_scope` 仅由原 data_type/category/effectiveness/continuous 字段分类，完整保留原 analysis_reason、单位和 domain_source。
`derivative_validated=not_established_by_catalog` 表示目录没有做导数验证，不否认下列已有历史证据。

| 参数类别 / 权威模型或实际路径 | 影响、连续性与可用方法 | 必须重做的计算、限制及已有验证 |
|---|---|---|
| 段长 `segments.i.length_m` | 固定拓扑内连续；影响质量/刚度/几何/材料点。原 Native fixed-input/T2，或匹配 affine 模型 conic sensitivity；PHS 可提供 ± 模型给隐式核 | 重建合法候选与路线，静力需重新求平衡，动态能力需重优化同条件控制。材料点跨 body 绑定、路由合法性或活跃集改变会破坏普通梯度。S130 保存模型已有长度双步长 FD；P6.3-A 两段长 Native T2 是合成接口验证，不能当真实验证。 |
| 杨氏模量 `segments.i.young_pa` | 连续且确实改变弹性；原模型实际使用 E。静态 IFT/KKT、Native finite-budget secants、affine conic sensitivity 各有不同目标 | 重建刚度并重平衡/重优化。PHS 六受载分支实际验证 `u=(E-2MPa)/13MPa` 的基准相对位移隐式梯度，最大相对误差 0.1191%；只覆盖该变量/模型/分支。原 Native 刚度三点重优化验证 derivative_valid=false、方向 unknown；不能称“增刚必改善”。 |
| 截面尺寸、几何分布 `segments.i.sections.j.parameters.*` | 尺寸可连续；截面 kind 是离散比较。尺寸影响惯性、质量和 clearance；分布并非任意自由场 | 重新生成结构/编译/几何检查，重建模型并求平衡或重优化。截面旋转对圆/各向同性截面无力学效应；非均匀 station angle 缺显式耦合路径时不可分析。原研究比较过截面方案，不等于已验证所有尺寸导数。 |
| 腱路半径/相位/guide_s/anchor_s、route overrides | 实际具名 span/index 可连续；模板 `spans.*`、完整 RoutePoint/拓扑对象不能当连续轴。影响长度 Jacobian、力臂和实体合法性 | Native 原通用候选对照可在原授权下使用；PHS 提供实际 ± 几何模型可做固定拓扑 KKT/重平衡 FD。需要保持孔/导向/锚点所有权，拒绝碰撞、绑定/拓扑切换。覆盖所有 route 的自动微分未实现，几何匹配优秀不保证有限力激发。 |
| 固定放绳长度 / 松弛量 / 预紧 | 被动 `native.payout` 真实存在且连续；当前主动 FamilySpace 的 pretension_n 是初始化选择，两者不是同一问题 | 被动 KKT 可以接收提供的 ± payout 模型，但须重平衡并检查张紧/松弛、LICQ、互补和 KKT 条件。现有 PHS 敏感性核不按参数名硬编码，但本轮证据仅验证 E。固定主动全绝对张力 schedule 会覆盖初始化 pretension，不得假定它改变当前任务轨迹。主线没有被动 payout AnalysisRequest。 |
| 材料黏性/阻尼、密度/质量分布 | v2 physical_domains 中声明时有实际路径；prototype 的实际值也存在，未声明域不能擅自变更。阻尼影响动态；密度影响惯性，也可能通过重力影响静力 | 需重建质量/阻尼并做匹配动态响应/控制重优化。静态零速度不含黏性效应，不能套静态梯度解释停稳性能。PHS/P3 的黏性比较是实际有限设计对照，非黏性梯度验证；未验证全部质量分布导数。 |
| 驱动张力上限、腱物理参数 | force_limit_n 改变输入集合，必须含边界效应；ideal-tension length_servo_gain 无效；diameter 仅 clearance/visual，不引入原模型没有的摩擦/惯性 | 原目录保留各参数的 effectiveness/reason。不能把绳直径的几何有效性等同力学敏感性，也不能把输入盒变动漏掉。PHS/P3 张力由单侧约束产生，无主动控制输入可替代。 |
| 控制器权重、控制设置 | 是动态闭环/搜索性能参数；原 parameter_capabilities 将控制权重排除在固定结构合法输入能力之外 | 需另外定义匹配控制器性能问题并重优化/执行；不是静力梯度。原受限序列搜索的系数响应不等于任意控制器参数梯度。当前目录不把它们变为结构敏感性方法。 |
| 段/腱数量、连接/腱路拓扑、cells | 数量/拓扑是离散结构比较；cells 是数值分辨率。两者均无普通连续导数 | 维度/通道/绑定变化需重新生成并评估。固定拓扑 KKT 拒绝维度或 material-point binding 变化。P3 的 1/2/4-cell 实测正说明分辨率/单侧约束耦合限制，不能把 cells 当物理梯度或把 4-cell INVALID 平均成收敛值。 |

PHS `design_sensitivity(native, equilibrium, minus, plus, parameter, step, s, force)` 接受外部提供的扰动模型和归一化坐标，
参数名称仅作标签；它不是任意参数解析器、AD 框架或参数合法性检查器。先对 KKT 残差做模型中心差分，再解隐式线性系统；
总 Lagrangian Hessian 包含材料、腱几何和外载几何项。`task_design_sensitivity` 同时微分受载状态和随设计变化的无载基准，
并以实际重新求平衡的差分检查。活跃集、点绑定或正则性失败时没有普通梯度；最大平面外范数仅有方向差分。
当前隐式核的可扩展输入形式不代表长度、payout、任意导向孔或质量分布导数已经验证。

历史敏感性依据另见 [S130 保存模型对照](s130_optimal_capability.md)、
[Native 重优化结构响应](mujoco_reoptimized_structure_sensitivity.md) 和 PHS 原 `phs2d_round3_results_20261028.md`；
这些是既有结果的阅读归纳，本轮未复算。主线当前原 T2 可聚合授权连续路径的保存结果，但 Reach 之外的任务仍按原规则 unsupported。

## 实现与验证

生产修改只有两个文件：新增只读分类模块；`task_constraints.py` 将它附加到已有候选方法/参数视图。
新增一个定向测试模块及本文、历史来源审计 JSON。没有删除现有内核；没有修改 Contract、执行器、TaskAdapter、
FamilySpace、Provider、Reporter、Store、预算、网关或现有 research_plan/research_analysis/physical_replay 执行语义。
正式方法含义直接复用原 `METHOD_MEANINGS` / 非线性 `LIMITATIONS`，参数域直接复用原行，避免维护平行含义/单位/域。

验证使用已安装的 `D:/softrobot-agent/.f3-prestudy-env/Scripts/python.exe`，没有安装依赖。
只运行本次目录与直接受影响的 P6.3-A 接口、B5 原 source/admission 边界测试；
科学 Worker、NativeModel、mj_step 在新增测试的读取阶段设为拒绝，原 P6.3-A 数值结果为明确标记的合成 fixture。
准确命令、结果与差异检查见 [验证记录](p63c0_validation.json)。

## 下一轮缺口

目录已经提供统一的物理对象、方法类别、原始前提和查询；它没有新增执行能力。
PHS/P3 后续仍需要正式被动 TaskAdapter、版本化固定放绳请求、独立 evaluator 与合法执行输入，
以及新授权 Study 中的候选、源、预算和数学适配，不能借 Reach scaffold 执行。
通用参数敏感性仍需逐问题验证静态/动态目标、基准、模型绑定、活跃集和搜索质量。
M0–M3 路由、科研意图适配、被动框架迁移、通用求导器和 Main M3 决策修复均未实现；本轮交付后停止。
