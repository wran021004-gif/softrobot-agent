# PHS-2D 功能开放性与冻结边界审查

本次审查针对已启动的 `phs2d-topology-successor-20261106`，不重新准备 Study，
不更改其冻结 Knowledge、FamilySpace、任务、物理模型或资格标准。
原始身份 `560ac79e6f82f9367359fa941ea47cb29e3a35125b916f2eff15a319f8fe5111`，
实现冻结 `f76a85282368458f01884579842876d317cc2134`。
正式授权和 Handoff 已通过现有接口记录。已用 Provider 10/64（余 54），Main 自主发起
`research_investigate`，要求解释十工况加载资格失败及有信息价值的下一步变量。

机器可读结果见 [audit.json](../../evidence/phs2d_openness_audit_20261106/audit.json)，
可重复的只读检查见 [phs2d_openness_audit.py](../../tests/research/phs2d_openness_audit.py)。
这些是工程检查和派生观察，不是正式科学结果。原始 Store 是唯一账本与证据源。

## Knowledge 的实际状态

冻结清单实际开放六个 `skill-* @1`（finite-search、parameter-model、matched-comparison、
local-to-experiment、continue-or-stop、witness-replay）和 `phs2d-research-process@1`。
首轮真实 gateway 请求确实包含专家过程六步及七条经验、精确 read_query、历史所有权说明；
后续请求没有再次注入整份专家过程。完整案例按需经 `experience_retrieve` 读取。
Mock SDK 测试验证首次实际 wire 交付、后续不重复提示、精确读取及无科学证据信用。

`passive-force-response-research@2` 的正文已存在且 Registry 默认程序性条目规则支持它，
但当前冻结 include_entry_ids 没有它；applicable_tasks 也没有 `passive_response`。
因此不能宣称当前 Main 已能读取该条目。这是确认缺口。运行中不能通过修改磁盘文件或
重载 manifest 修补冻结范围。后继版本可把该 id 加入准入名单，补 task tag，并在 PHS
过程旁提供精确读取提示；保留 `allow_benchmark_answers=false`，不引入 P3/PHS 获胜答案。
本次没有静默注入、创建重复 Study 或申请无必要的同身份授权。

## 当前设计域及物理作用

所有数值边界和具体候选参数路径完整保存在 audit.json 的 frozen_design_domains 和
parameter_catalog；下面按物理意义列出，不能把目录字段都当成有效驱动力。

| 范围 | 当前可调内容／边界 |
| --- | --- |
| 拓扑 | 实际生成 1～9 段、1～12 腱；离散生成和比较，非连续梯度 |
| 段 | 长度 0.015～0.28 m；Young 模量 2～15 MPa；逐段和逐截面分布 |
| 截面 | circle、tube、ellipse、rectangle；各自注册尺寸；既定 station 上的截面选择 |
| 材料／方向 | y/z 黏性及截面转角；逐段具体黏性域不同，以冻结目录为准；各向同性截面旋转无机械作用 |
| 腱与路径 | 实际每腱独立 payout 0.3～0.5 m；span 半径、相位、角度偏移、guide_s、anchor_s；合法 typed route overrides |
| 装配位置 | 真实导孔中心局部 YZ、base/payload 的注册局部 YZ 附着坐标；仍须实体包络及 clearance 检查 |
| 几何属性 | 腱直径 0.5～1.2 mm 主要影响 clearance；没有腱惯性、摩擦或直径相关张力定律 |
| 容量／无效项 | force_limit_n 是容量资格边界（1～8 N 的声明域，不允许增加原 8 N 上限），不是主动驱动力；pretension 和 length_servo_gain 在本被动模式无主动作用；control weights 非被动结构梯度 |

环境、载荷、payload、边界条件、任务评价以及 KKT/稳定性标准冻结。
导向件／连接件的质量、COM、惯量由原型提供，不能任意独立修改。

## 尚未开放字段及已有实现能力

| 字段／能力 | 查证结果与限制 |
| --- | --- |
| density | resolver、generator、compiler 支持；历史 passive engineering FamilySpace 有 500～2500 kg/m³ 的范围。当前未注册；后继版本可沿用有出处范围，质量按面积与长度联动 |
| natural curvature | generator 支持 curvature_y/z，compiler 使用原有本构参考曲率；历史范围 ±10 rad/m。当前未注册；不是新增物理内核 |
| polygon | Section、properties、生成及编译已支持。隔离副本上的有界方形轮廓成功生成；当前 FamilySpace 未授权。通用开放需要明确顶点／孔轮廓合法域，不能仅加入 polygon 空参数字典后容许无限轮廓 |
| hole radius | 孔净空、包络和实体几何有原实现；当前质量惯量是 supplied inertia，并不随钻孔半径重算。未找到当前注册的可信孔径变化域和物性联动规则，因此不能直接开放为自由物理变量 |
| section stations | 当前 generator 明确要求原型 station 数量和顺序；Section choice 不含 station s。底层编译可读取 station，但当前生成协议未注册 station 位置与数量及其范围 |
| guide／connector 几何与质量 | 固定原型。修改实体尺寸应提供可信材料／几何与质量惯量关系；不能开放几个无关联质量数字 |

上述后继能力检查均只用内存副本，没有写入当前 Study。density+curvature、polygon、
非 base 起点、4/16 cells 五个小型生成／编译检查均成功，没有动态执行或验收信用。

## payout、路由与离散精度

18 个实际生成路径检查覆盖 (1,1)、(1,12)、(5,6)、(9,4)、(9,12)、
(9,1 且近端 anchor)，分别取注册段长最小、默认、最大值。
所有布局成功生成，所检查路径长度均落在 0.3～0.5 m 外；例如单段为
0.015/0.16/0.28 m，九段全长为 0.247/1.362/2.632 m。
这证明当前 payout 域没有覆盖这些合法布局的零位实际路径长度，不能据此判整个拓扑不可行。
这也不是“所有候选都不匹配”：当前 C4 的实际 0.472 m 路径／payout 在域内。
未在冻结任务中找到统一 0.3～0.5 m 硬件来源；这是需在后继版本重新界定的范围，
不能把 2.632 m 当作所有角度、路线、锚点和形变的已证明全局最大值。

`base_only_consecutive_spans_v1` 是本 FamilySpace 的生成约束；原始任务未单独要求
所有腱必须从 base 开始。既有 `selected_segments_and_consecutive_spans_v1` 可从 guide_1
开始，隔离生成与编译成功，说明不是整个被动物理模型不支持。
仍需路线顺序、真实导孔、锚点和 clearance；不能等同于任意交叉网络已获支持。
当前规则冻结，额外路径留给后继版本。

8 cells/段是统一正式数值协议，不是结构变量。现有编译器可比较其他精度；
两段 4/8/16 cells 对应 16/32/64 DOF。隔离检查只证明生成编译能力，
不证明收敛。当前没有授权独立空间稳健性操作，不能混入主线结构排名。

## 工具及上下文

真实 Main 请求可发现 research_plan、experience_retrieve、evidence_read、research_recall、
research_route、research_investigate；完成 diagnose 后 research_analysis 实际出现并已执行。
捕获的全部实际 function Schema 通过 JSON Schema 结构检查。inspect、compare、
differentiate、optimize 在 mechanism_structure_v1 下可选，实际请求与结果沿原绑定链存储。
具体连续参数目录覆盖冻结注册的有效物理变量，离散和无效参数附有语义限制。
目录“可发现”不代表任意输入都免除原 Plan、预算、工作点或科学前置条件。

FamilyMixedSearch 的 task_violation mathematical_proxy 指向 CONIC；Native 分支要求
主动控制授权和 Reach/Hold 窗口，没有调用当前被动硬单侧机制平衡方法。
故不增加 search 授权，也不将它宣传成被动可行性工具。NMPC、RL、Offline NLP、BDF
继续未授权，没有为了工具数量增加平行接口。

实际 wire 每次只有一个 CURRENT_RESEARCH_PACKET，未每轮发送完整 FamilySpace assembly，
Knowledge 正文也未整份重复注入。最近检查的 packet 约 140 KB；study_goal 中完整十工况
定义约 73 KB，是主要体积来源，带各自加载条件，并非完全相同的重复对象。
检查该 packet 未找到超过 1200 字符的完全相同重复子树。
候选／结果引用在 Plan、证据作用域和 Reporter 来源中重复有不同语义，不能全部删除。
decision_packet 的旧协议顶层字段还有实际审查／恢复和测试消费者（例如 implementation、
evaluation_profile、candidate_profile_bindings），因此保留原导出接口。
最小修补为正式 Provider 和续接调用显式使用 `research_only=True`，直接返回 research、
family_space、study_id，跳过多余 controller 查询、候选 profile 逐项读取及导出字段构造。
不改 research 或 FamilySpace 摘要内容，不改最终 Provider 科研上下文的语义。
没有重写 compact_tool_delivery、research_decision_brief_v3 或 information_flow_brief。

## 预算、验证和继续执行

Provider 初始 64，收尾保护 6；其余累计数量只记账，可在明确有限 addendum 后追加请求。
worker_calls=0 是通用平台计数字段；实际已运行数学 Worker、完成十个数学动态 episode，
未消耗该字段，也没有阻止授权的数学／物理执行。物理 Replay 数仍为 0。
max_turns/max_no_progress 未作为累计 Study 配额进入研究准入账本；当前 harness 的
build_harness 也没有把它们注册成新的累计限制。Worker watchdog 仍为单次数学 7200 s、
物理 1800 s，保留原请求结算保护。

本轮定向验证：SDK 专家过程交付／读取、通用拓扑 Schema／独立 payout 展开、精简构造与原导出
内容一致性，3 个不同测试通过；另做 18 个纯几何域检查及 5 个隔离能力检查。
初始两项通过耗时 22.353 s；修补后 SDK 回归通过。新测试初次漏设 fixture freeze，
修正测试 fixture 后单测通过（2.283 s）；没有修改正式 Store 来使测试通过。
未重跑先前全部 29 项，未进行 Provider 预演，未以工程测试再跑完整十工况。
Knowledge／FamilySpace 未更改，因此 resolved identity 与科学授权保持不变。
清理前在 Store 写锁下确认全部 receipt 结算、无 pending，保存的 SDK 消息摘要精确匹配
science_delivery_boundary，才中断已知监督进程；未终止任何科学 Worker。
实现变更使用现有 `core.bind` 记录最小迁移，保留原 profile、所有计数和历史，
再由正常 `converse`／`reconcile` 恢复同一个 Study；不手动修改 Handoff 字段。
任何未来范围扩展必须使用独立后继版本及其明确身份授权，当前 Store、成本与失败全部保留。
