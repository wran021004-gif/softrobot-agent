# 研究起点与共同判读规范 v1

日期：2026-10-07。范围：研究主线一。核对基线：`79d72b78380c5b2a176ddb3703e1c8d3cb219648`。

本文件是当前研究起点的版本化增量规范。它统一任务状态、候选角色和证据解释，不替换封存活动报告、历史规格、配置、预算或 STOP，也不授权执行。后续起点改变应形成显式版本；下述运行入口的差异仍交给主线二／三处理，不能把本文视为运行时已经统一。

总目标是让主研究模型利用数学工具与可核验证据组织机器人设计和控制适配，完成明确规定的任务。物理表现与研究成本分别评价，不要求全局最优。当前优先研究问题是远段初态扰动下的保持速度失败；这不把所有未来任务永久限定为该问题。

## 1. 已完成证据与当前起点

### 1.1 精确配置、来源与角色

当前起点采用验证后按冻结规则晋升的 `batch-396bdbbae02626d3-0`。决定依据是[验证后冻结选择](../evidence/research_native_development_v3_20261007/structural_continuation_20261007/final_frozen_selection.json)的 `outcome=promote_frozen_candidate`，不是原科研 STOP 的 selected 字段，也不是最后一条执行。

| 角色 | 候选与源执行 | 权威配置 |
| --- | --- | --- |
| 当前晋升起点 | `batch-396bdbbae02626d3-0`；nominal 研究执行 `871e8b83c5d14f9ba813fb65dcb0cc29` | [配置 `3ae03b4e…`](../evidence/research_native_development_v3_20261007/store/artifacts/3ae03b4e4ddac2e5099ae5823fc0dd7dd9d338dfba6b7d435729d4e5ab41665b.json) |
| 前 incumbent／历史参考 | `batch-ebbeadbdaca10732-0`；源执行 `91c3ba1b01d6499fb26df8f95409401b` | [配置 `285236ab…`](../evidence/research_native_development_v3_20261007/store/artifacts/285236abf99bf36894fa08410ac82fefa177a80179c4ceba15d95f8d1bc8d978.json) |

完整配置 ID 分别为 `3ae03b4e4ddac2e5099ae5823fc0dd7dd9d338dfba6b7d435729d4e5ab41665b` 和 `285236abf99bf36894fa08410ac82fefa177a80179c4ceba15d95f8d1bc8d978`。这些 saved configuration 是使用配置的依据；以下数值只作阅读摘要，不能据此重建权威配置。

晋升配置 near/far 长度为 0.16/0.11 m，两段源相对截面比例均为 0.95，材料场景均为 `compliant`，Young 模量分别为 7.2/5.4 MPa。唯一选中变化是 `control/recipe/terminal_tip_speed_weight` 从 0.05 到 0.10；`holding_tip_speed_weight` 保持 0.05，实际物理字段不变。控制器为 `controller.gvs_nmpc@7.0.0`，后端为 `backend.family_mujoco@1.1.0`，执行模型为 `model.serial_bending_cells@1.0.0`，每段 12 个 bending cells。完整数值配方、绳路、刚体和初态均以源配置为准。

源 nominal 通过只是资格证据。二十次验证各自有独立配置与执行身份，不能把源执行冒充验证重复：[完整执行表](../evidence/research_native_development_v3_20261007/report_completion_20261007/all_execution_results.json)保存每槽配置、任务／结构／科学身份、事实 ID 和成本来源；[原验证记录](../evidence/research_native_development_v3_20261007/structural_continuation_20261007/verification.json)保存 simulation receipt、evaluation、profile 及联合 acceptance 引用。对应原件位于同目录 `store/artifacts/<artifact_id>.json`。

后续使用角色时，必须分别保留：研究的固定源基线、当前 incumbent、验证前冻结 challenger、验证后晋升交付、最新尝试、最新完成评价。角色依选择记录和 reservation/completion 事件确定，不按列表顺序、时间接近或“最近通过”推断。原 STOP 当时仍选择旧 incumbent；本文记录后续冻结验证的交付，不能改写原 STOP。前 incumbent 仍是可追溯历史参考；下一研究是否采用它作比较锚点，应在新协议中冻结。

### 1.2 完成轨迹、成功与失败

已完成三个研究批次、六次研究执行，随后二十次新鲜配对验证。研究批次分别考察 terminal 速度权重 0.10/0.025、near 截面比例 1.00/1.05、far 截面比例 1.00/1.05。near 批从已接受计划恢复执行；其真实反馈之后，主模型提出并执行 far 批。两份后续长度提案均被拒，没有长度实验。[独立结果审查](../evidence/research_native_development_v3_20261007/structural_continuation_20261007/independent_results_review.json)的 `scientific_observations` 保存六次配置、执行、修改和 acceptance。

terminal=0.10、near scale=1.00、far scale=1.00 和 1.05 均有新鲜 nominal 联合通过；terminal=0.025 和 near scale=1.05 因保持速度失败。near/far 批的 terminal/holding 权重均为 0.05/0.05。既有历史 passing configurations 也保留在[原研究规格](../configs/research/reach_hold_v1_1.json)的 `source.historical_outcomes` 中。当前晋升配置不是唯一通过配置，其他 nominal 通过也没有因此获得完整扰动套件验证。

五个固定开发案例，各用 seed17/18 的两个新鲜执行；每槽 incumbent 后 candidate。下表来自[逐案例结果](../evidence/research_native_development_v3_20261007/report_completion_20261007/per_case_results.json)及[聚合结果](../evidence/research_native_development_v3_20261007/report_completion_20261007/aggregate_results.json)。

| 案例 | 前 incumbent 联合通过 | 晋升配置联合通过 | 已知失败槽 |
| --- | ---: | ---: | --- |
| nominal | 2/2 | 2/2 | 无 |
| near_z_plus | 2/2 | 2/2 | 无 |
| near_z_minus | 1/2 | 2/2 | incumbent seed17 |
| far_y_plus | 0/2 | 0/2 | 两配置 seed17/18 |
| far_y_minus | 1/2 | 1/2 | 两配置 seed17 |
| 合计 | 6/10 | 7/10 | 七槽保持速度超限 |

二十次执行均有效、完整，官方终端位置评价全部通过，force-bound violation 均为 0 N，solver errors 均为 0；两配置都未完成整个联合套件。晋升配置仍有三个远段扰动保持失败，不能写成完成任务或一般鲁棒性已经成立。

| 套件最坏分量 | 前 incumbent | 晋升配置 |
| --- | ---: | ---: |
| 终端误差 m | 0.0031794922216638703 | 0.00401791580527543 |
| 保持最大误差 m | 0.0033040679451552747 | 0.004070644033629745 |
| 保持最大速度 m/s | 0.07026211095497123 | 0.06484873299977026 |

冻结规则首先比较联合通过数，只在计数相同时比较物理分量。因此 7/10 支持晋升，同时最坏位置误差升高、最坏速度降低。它不证明全指标改善或结构设计优越。“保留位置要求”指保持验收限值，不要求所有数值位置误差永不增大。

700/700 控制更新超期，执行均值范围为 7.927247994285842–14.490832028570418 s，控制周期 0.01 s；实时可行性未证明，且不是本次离线套件验收项。数值停止规则、初态和 warm-start 仍是执行上下文，不能因排除实时验收而忽略。不同 seed 标签不自动形成独立随机条件；这里是固定初态、独立新执行的观测比例，不是总体成功概率。

尚未建立的结论包括：远段失败的主导原因、未执行长度修改的效果、其他参数组合和任务／扰动分布的表现、连续时间保持保证、一般鲁棒性、硬件安全与部署实时性、全局最优、数学收敛或因果贡献、LLM 研究优于数学基线。终端权重、速度和位置的观测取舍可指导后续问题，不能单凭它认定必须修改结构。

### 1.3 历史版本与证据解释

历史隐式零初始化与后来明确写入各 cell 的零 qpos/qvel 有不同原始任务身份，即使 nominal 数值状态相同，也不能合并身份或宣称历史比较是匹配新实验。旧 `design/section_scale`、`design/material_scenario` 为共享选择器；新规划用分段选择器。投影用于参数解释，保留原配置字节、原哈希和科学执行边界，不把源相对倍率再次乘在已缩放结构上。源配置与各执行配置的构建注释差异也不等于实际物理结构差异。

| 记录类别 | 可以支持 | 不能据此支持 |
| --- | --- | --- |
| 封存配置、receipt、evaluation、profile/motion、冻结选择与完整验证表 | 指定执行的状态、物理结果、资格、晋升和已核对成本 | 未执行条件、全局最优或泛化 |
| 独立源审查、确定性投影与聚合 | 来源绑定、精确值、计数、对冻结规则的判读 | 自动采纳所有模型文字 |
| 模型观察、解释、诊断假说、STOP 理由、后续长度提案 | 可审查的研究决策及其证据引用 | 因果事实、资源耗尽或新执行授权 |
| 合成 receipt、离线 gate、恢复／输入尺寸检查 | 指定工程路径及夹具下行为 | 新机器人结果、真实随机重复或方法收益 |

已完成报告交付以[报告续作](research_v3_report_completion.md)及其确定性证据为准。[最终文字审查](../evidence/research_native_development_v3_20261007/report_completion_20261007/independent_review_attempt_2.json)记录 `quantitative_and_main_scientific_claims_supported=true`、`accepted_as_final=false`：主要科学计数得到支持，但两处解释错误仍保留。报告周期已关闭，不再调用模型重写解释。旧文档中“尚未执行”“最终报告受阻”等表述属于其当时版本；最新记录改变当前认识，不改变旧报告历史。

## 2. 共同判断规则

### 2.1 任务完成、晋升、研究终止分别判断

| 判断 | 依据与应报告内容 |
| --- | --- |
| 任务完成 | 满足某项研究执行前冻结的验收协议，包括覆盖范围、必需组件、有效性与完整性；局部通过不能代替未通过或未执行套件。 |
| 候选晋升 | 按预声明比较规则选择；可早于完整任务完成。注明源 incumbent、冻结 challenger、比较条件、全部分量取舍及未完成条件。 |
| 研究终止 | 可因任务完成、理由明确的自愿停止、继续工作价值有限、预算边界或真实工程阻塞；预算是上限，无需耗尽。记录实际状态、剩余工作与依据。 |

停止必须分别报告三件事：动作是否合法；解释是否有事实支持；是否证明最优停止。合法自愿 STOP 不验证其资源／因果解释；“价值有限”须有理由但不自动证明没有更好下一步；预算耗尽须以实际可执行额度与截止时间为依据。工程阻塞说明是哪条入口／依赖受阻，不把它改称科学不可行。当前实现的停止原因词汇不完全一致，见第 4 节，本文不暗中扩展历史运行合同。

### 2.2 当前 reach-and-hold 协议的限定适用范围

以下是[冻结 v1.1 规格](../configs/research/reach_hold_v1_1.json)及当前二十次验证采用的 `offline_reach_hold_v1` 上下文；[联合验收实现](../tools/research_tasks.py)的 `assemble_acceptance` 负责组合原评价与 profile/motion，不替换原评价。

| 项目 | 本次冻结条件 |
| --- | --- |
| 任务、坐标与时序 | `task.reach`；世界系 tip target `[0.29, 0.035, 0.19]` m；duration 0.35 s，control/sample period 0.01 s，physics step 0.0005 s |
| 终端位置 | 官方 `evaluate.reach@1.0.0` 成功，终端误差 ≤0.01 m |
| 保持位置／速度 | 最后闭区间 `[0.30, 0.35]` s，六个均匀采样点；最大位置误差 ≤0.01 m，最大世界平移 tip speed ≤0.02 m/s |
| 保持证据 | profile 的覆盖与冻结定义一致；本次另核对 motion 的全部窗口时间戳。速度沿用 Jacobian × recorded velocity，不改用位置有限差分；仅为采样保证。 |
| 输入 | 六路理想非负绳张力，各 ≤8 N；force-bound violation 的数值容差为 `1e-8 N`，不是放宽物理限值。 |
| 有效性与完整性 | 有效、完整执行，所需信号有限且有覆盖，solver errors=0；evaluation、simulation、profile 与配置／执行绑定一致。 |
| 案例与重复 | nominal、near_z_plus/minus、far_y_plus/minus；非 nominal 总主弯角 ±0.01 rad、角速度 ±0.02 rad/s，按归一化弧长均分至相应段各 cell；seed17/18，各角色十槽。 |
| 实时性 | 非验收项；deadline misses、更新耗时和总计算成本单列，历史实时失败不被重评分。 |

五案例和 10/10 只是这个冻结研究的完整通过要求，不自动成为任何新研究的验收要求。下一研究必须执行前冻结自己的任务、条件、覆盖／重复、完成标准、晋升规则、参数子集、数值上下文、预算和停止政策；不得看结果后改阈值、筛案例或替换候选。

### 2.3 状态、覆盖和比较

沿用 `research.task_acceptance@1.0.0`：`accepted` 为证据完整的通过，`valid_failure` 为有效完整执行的物理不通过；`invalid`、`incomplete`、`missing_evidence` 分别表示无效、不完整或所需证据缺失，`accepted=None` 表示未知。调度层的 unavailable／not_started 是能力或未开始状态，不能变成已测物理失败。某组件已知失败而其他组件缺失时，两者都保留，不能伪造完整联合结果。

所有预定槽位都留在验证分母及结果清单中，包括失败、无效、不完整、缺失、未开始和非新重复。新重复必须有唯一执行、正确绑定的 simulation receipt、`cache_hit=false`、一次 charged backend solve；缓存或重复 request 的原回执不是 fresh repetition。搜索 nominal 也不替代验证槽位。不重试求通过，不自动重放 unknown reservation。

改善判断先确认冻结条件及比较身份相容，并确认全部必需槽位为新鲜、完整、可判读结果，再按该研究的规则比较。当前规则是联合计数优先、计数相同才作分量支配判断；相反方向变化属于取舍，缺少必需证据时不作优越性结论。保留逐槽和逐案例信息，成本不混进物理标量分数；同一结果可晋升而未完成任务。

来源、单位、精确 JSON pointer、配置／执行／任务身份和比较方向必须检查。终端误差读官方 evaluation；保持最大值读 profile 的 sampled_settling。profile 与评价有极小浮点表示差异时，保留二者并明确权威投影／supersession，不能改原值或放松来源保护。`authoritative_metric_projection@1.0.0` 已修复本次投影，见[修正事实记录](../evidence/research_native_development_v3_20261007/report_completion_20261007/corrected_fact_projection.json)。有效引用只支持引用值，不保证周围模型解释成立。

## 3. 参数与决策权限

### 3.1 四类量及三层能力

| 类别 | 当前范围与权限 |
| --- | --- |
| 机器人设计 | 段长、源相对截面倍率、材料场景；结构变化需重建受影响物理、投影、控制器和初态绑定。 |
| 控制参数／控制器选择 | 本池连接 terminal/holding 速度权重；当前固定 v7。其他控制器是否允许取决于新研究及注册兼容性，不因目录中存在就可切换。 |
| 数值／模型设置 | mesh、basis、预测模型、solver 时限／迭代／early-return、warm-start、线程等；当前研究固定并计入上下文，不能假装设计或验收量。 |
| 外部任务条件／验收 | target、环境／gravity、初态分布、timing、阈值、日程等；由冻结任务协议定义，不能为候选过关而改写。 |

“底层模型可表达”“研究入口已连接”“执行已验证”是三层不同判断。[catalog](research_parameter_catalog.md)与[实际 catalog 实现](../tools/parameter_catalog.py)分别记录 `technical_support`、`study_permission`、`validation_evidence`。离线 mutation/compiler 检查只证明接线，不验证整个域或参数组合的闭环表现；当前六次研究和二十次验证只覆盖其记录的值及条件。

### 3.2 当前八变量池

下列域逐项取自 v1.1 的 `parameter_grants` 与 catalog；本轮不扩池、不修改实现或研究授权。

| 分类 | 稳定参数 ID | 已连接的研究域 |
| --- | --- | --- |
| 设计：near 长度 | `components/near/length_m` | `[0.15, 0.17]` m |
| 设计：far 长度 | `components/far/length_m` | `[0.11, 0.13]` m |
| 设计：near 截面 | `design/near_section_scale` | `[0.95, 1.05]`，无量纲，绝对源相对倍率 |
| 设计：far 截面 | `design/far_section_scale` | `[0.95, 1.05]`，无量纲，绝对源相对倍率 |
| 设计：near 材料 | `design/near_material_scenario` | `baseline`／`compliant`／`stiff` |
| 设计：far 材料 | `design/far_material_scenario` | `baseline`／`compliant`／`stiff` |
| 控制：终端速度目标 | `control/recipe/terminal_tip_speed_weight` | `[0.025, 0.10]` |
| 控制：保持速度目标 | `control/recipe/holding_tip_speed_weight` | `[0.025, 0.10]` |

截面倍率保留形状、aspect ratio、站位和方向；材料场景为原 Young 模量 ×1/0.9/1.1，保留原 density 和 bending viscosity，是模拟输入而非已验证商用材料。两权重作用于按冻结 speed scale 归一化的世界 tip speed 平方，不改验收速度阈值。段数、绳路、输入次序和每段 12 cells 在本研究固定。

未来模型可在新研究冻结的允许范围内自主选择任意子集，无需逐批人工解锁；参数可选不等于额外执行额度。当前活动仍已停止，本文不恢复执行。表示能力如 natural curvature、payload mass/COM/inertia 不等于已经连接的研究 mutation；拓扑／绳数、routing／shape、density／viscosity、离散化等更广覆盖仍是主线三工程工作。shear、stretch、torsion、tendon friction、rope elasticity 和 motor dynamics 在当前模型缺失。扩大公共能力无需先证明这八变量不能完成任务。

## 4. 入口差异与后续输入清单

下表来自定向源码和已保存记录检查。“未统一”表示当前边界或静态调用契约缺口；不宣称已运行新的回归或已修复。主线二负责证据、状态、解释和恢复；主线三负责公共能力、参数／任务接线及按需诊断。对于有意差异，后续应保留其版本／问题含义。

| 入口／函数 | 当前行为 | 差异或限制 | 支持来源 | 性质 | 后续 |
| --- | --- | --- | --- | --- | --- |
| `load_spec`／`ResearchSpecification.frozen_bindings` | 默认 v1.1，校验原 incumbent 配置与固定五案例／seed／分配，尚未采用验证后起点 | 文档新起点不自动重写运行规格；下一研究需显式新冻结，不覆盖旧 JSON | [research_spec.py](../tools/research_spec.py)，[v1.1](../configs/research/reach_hold_v1_1.json) | 有意版本区分；新研究连接待办 | 主线三 |
| `reach_facts` 与 `assemble_acceptance` | 前者的 `task_accepted` 取官方终端成功；后者组合 holding、输入、有效性和 solver errors | 同一记录可 official reach pass、joint failure；消费者必须带协议和组件判读 | [delivery_facts.py](../extensions/tendon_family/delivery_facts.py)，[research_tasks.py](../tools/research_tasks.py) | 有意协议区分，非 evaluator 缺陷 | 主线二 |
| `research_scheduler.capabilities`／`validate_decision` 对 `stop_interpretation` | 自主入口始终允许 voluntary stop，并核验观察引用；固定停止解释器只识别 budget_exhausted、completed_schedule、predeclared_policy | 自愿停止／价值有限／工程阻塞未在共享解释器统一映射；引用检查不验证自由 STOP 文字 | [research_scheduler.py](../tools/research_scheduler.py)，[stop_interpretation](../tools/research_tasks.py) | 未统一的停止判读契约 | 主线二 |
| `aggregate_acceptance`／`compare_acceptance` 与 `fixed_research.run_study` | 聚合保留全部日程，比较器可先按 fraction 返回 improved；fixed runner 另检查每槽 fresh、绑定和 accepted/valid_failure | 比较器自身没有 fixed runner 的完整可判读槽位 gate；其他调用者须保证此前置条件 | [research_tasks.py](../tools/research_tasks.py)，[fixed_research.py](../tools/fixed_research.py) | 未统一的比较前置条件；静态源码缺口 | 主线二 |
| `fixed_research.run_study`／`research_campaign_v3.verification_gate` | fixed 搜索时保留二十次完整资源；v3 保护 backend 数并在启动验证前核对全量时间／操作／交付资源 | 固定与反馈流程分配不同；prepared fixed study 未正式完成，不构成三组收益比较 | [fixed_research.py](../tools/fixed_research.py)，[v3 gate](../examples/research_campaign_v3.py)，[v3 协议](research_native_development_v3.md) | 有意版本／分配政策区分 | 主线三；主线六再冻结公平条件 |
| `project_planning_configuration`／`historical_parameter_projection` | 当前规划将旧共享 selector 投影到分段域，保留非默认值、原 bytes 和科学范围 | 历史 exact reuse 与规划解释不能混同；旧失败已保存，不能再描述为尚未修复的当前读参错误 | [candidate_parameters.py](../tools/candidate_parameters.py)，[结构续作](research_v3_structural_continuation.md) | 有意表示区分，已修复历史缺陷 | 主线三保留版本接线边界 |
| `current_research_authority.refresh`／`check_payload`／`dispatch_snapshot` 对 working-state 恢复 | 启用 role 刷新标志的 v3 请求绑定当前不可变菜单／账本，dispatch 再核对；恢复保持原 archive allowlist 与 STOP | 当前刷新是启用标志的路径行为；可读历史证据／恢复成功都不能授权旧活动或推导其他入口全已统一 | [current_research_authority.py](../tools/current_research_authority.py)，[context_assembly.py](../tools/context_assembly.py)，[恢复说明](research_state_recovery.md) | 当前 authority 接入覆盖限制，后续需按入口核对 | 主线二 |
| `research_authority`／`assemble_working_context` 与验证后冻结选择 | 上下文角色取 saved selected_deliverable/chronology；后验证晋升另存 final_frozen_selection | 原科学 STOP、最新完成执行和后验证交付分开保存；新起点的角色采纳须显式绑定后验证选择，不能覆盖原 STOP | [context_assembly.py](../tools/context_assembly.py)，[冻结选择](../evidence/research_native_development_v3_20261007/structural_continuation_20261007/final_frozen_selection.json) | 有意时间边界；跨入口交付角色衔接待办 | 主线二 |
| `report-completed`／`report_completion.frozen_results`／`authoritative_metrics` | 预取二十行，evaluation 提供 terminal 精确值、profile 提供 holding；独立报告 sink，不调度研究 | 后来报告替代失败报告调用，未重开科学轨迹；源指针修复已完成，但模型两处解释仍未通过审查 | [report_completion.py](../tools/report_completion.py)，[bound_reporting.py](../tools/bound_reporting.py)，[最终审查](../evidence/research_native_development_v3_20261007/report_completion_20261007/independent_review_attempt_2.json) | 报告版本区分＋残余解释缺口 | 主线二 |
| `effective_catalog`／`resolved_pool`／`task_adapter.check_compatibility` | catalog 区分能力、grant 和证据；scheduler 仅列已授权接线；adapter 检查实际 task/controller pairing | 八变量接线不是全域验证；例如 tracking 需其 v5 控制器，reach v7 技术支持不验证 tracking | [parameter_catalog.py](../tools/parameter_catalog.py)，[research_scheduler.py](../tools/research_scheduler.py)，[task adapters](research_task_adapters.md) | 有意能力／证据区分；更广接线待办 | 主线三 |

主线二下一轮的证据输入包括完整二十行及原 receipts、原 STOP、验证后选择、current authority 的请求／dispatch 绑定、claim 与 ledger 恢复、修正事实的 supersessions、两次模型响应和独立审查。上表是待审查的输入与缺口清单，不是完整主线二实施目标；本轮没有修改 runtime 或新增回归执行。

必须保留的两个具体主线二回归案例：

1. **计划预算短缺不等于实际资源不足。** model8 提案写 2000 s，完整需求为 2590 s，故 planned shortfall=590 s；actual available 相对完整需求的 shortfall=0 s。零是“不足量”，不是剩余容量为零。model9 voluntary STOP 合法，不因此证明预算耗尽、没有可行下一步或最优停止。[原结果审查](../evidence/research_native_development_v3_20261007/structural_continuation_20261007/independent_results_review.json)的 `independent_model_interpretation_corrections` 与最终文字审查保留来源。
2. **先前七次与后来第八次修复是两个授权边界。** [先前报告阻塞审查](../evidence/research_native_development_v3_20261007/structural_continuation_20261007/final_report_blocker_review.json)仅属于七次修复边界；[报告续作授权](../evidence/research_native_development_v3_20261007/report_completion_20261007/continuation_authorization.json)才允许第八次修复和有限报告请求。不能把 repair8 写进先前 repairs_used=7/ceiling=7 的受阻历史。保留原回答和独立纠正，旧报告周期不重开。

## 5. 不变的六主线路线

| 主线 | 已约定方向与衔接 |
| --- | --- |
| 1. 研究起点、范围与判断规则 | 本文的共同规范及有界差异清单；不承担全入口 runtime 修复。 |
| 2. 证据、运行事实、上下文管理与恢复 | 下一工程目标；以第 4 节已证实输入／缺口为起点，不捆绑新机器人搜索。先审阅本次交付再确定完整实现目标。 |
| 3. 可发现、可扩展的参数／工具／任务与按需诊断 | 连接公共能力与一层按需诊断。刻意安排的 handoff 测试必须明确标为工程 handoff 测试，不当作主模型自主发现或科研收益。 |
| 4. 模型组织、数学支持的设计与控制研究 | 可在一项研究中包含多个批次、反馈和诊断；允许研究选择保持现有结构，数学分析支持保留设计也是合法成果。 |
| 5. 证据驱动决策、诊断与可复用方法 | 可复用同一研究证据考察决策质量；报告诊断提供了什么信息、主模型如何处理、后续结果是否支持其判断、付出多少成本。 |
| 6. 识别收益来源的公平比较 | “诊断／方法复用比没有它更好”或“LLM 比数学基线更好”需要这里的比较，不能由单次轨迹、工程通过或解释质量替代。 |

不增主线，不扩其验收要求。来源、单位、身份、可比性等基本核验是所有路线及比较基线的共享基础设施，不能为了构造弱基线而移除。成本应区分请求／失败与重试、工具操作、backend/诊断计算、实际结算与在途预留、已知 tokens 和未知账单，不把预留当实际消耗；本文不更改既有成本或授权账本。

## 6. 本次交付核验边界

本轮仅以保存的权威配置、冻结选择、六次研究审查、二十次完整执行表、逐案例／聚合表及最终解释审查核对身份、参数、计数和结论；核对文内本地引用、改动范围及 whitespace。未新增机器可读 schema、账本或状态管理器。没有新增模型／provider 请求、仿真／controller solve、数学实验、诊断 worker、参数搜索、RL 或正式基线执行；不改封存证据、历史规格、活动状态、预算或保护分配。
