# BF7：三目标共享结构探索

基底为 2026-10-27 核对并 fetch 后一致的本地与远端 `integration/research-next`：`a1566b91a387316405bdb2fc79eb8a087ea20e8a`。独立分支 `research/bf7-shared-structure-benchmark`，独立 worktree `.worktrees/bf7-shared-structure-benchmark`。不修改基底，不从 B 历史研究分支派生，不读取或导入 BF4/BF5/BF6 成功设计、控制或私有 Store。

Codex 组织有限研究，所有科学工作交给原 Study 工具；LLM Research Agent、Provider、PPO、NMPC、私有物理/数学搜索均为零。新增运行入口只编排原工具、保存与汇总现有结果。

## 接口审计与范围

- `tools/research_tasks.py` 将每个 Reach 自身的终端位置、保持窗位置和保持窗速度转换为带各自容差的 norm constraints；独立 `evaluate.reach` 和原 Reach/Hold 组合验收分别检查终点、完整执行、保持窗及张力/求解有效性。
- `tools/research/task_constraints.py` 的分析适用性针对一个候选的实际任务和采样点；`analysis.py` 验证该候选、初态、物理输入、任务要求、完整覆盖、方法授权与预算，数学输出不能成为物理验收。
- `search.py` 的 `family_mixed_search_v1 / task_violation` 只在 `base_configuration` 的单任务上构建模型、求 CONIC 和排名，**不遍历 `task_conditions`**。因此本实验的搜索只负责在第一个任务上提出至多三个合法结构，不宣称它实现了原生三目标优化。
- `optimal_capability.py` 保留原 GVS/CONIC 方法准入和模型/内部求解计数。每个单任务模型构建加一次 norm CONIC 为两单位；预计三结构 × 三任务 = 18 单位，总授权上限 24，不要求耗满。没有新优化器或新隐藏评分。
- `config.py` 已冻结支持两或三个 `task_conditions`；`initialize_control(condition_id=...)` 调用 `conditions.py` 在同一物理结构上产生任务绑定候选。每个条件均可独立初始化和优化控制。
- `conditions.py` 的联合 SELECT 检查全部冻结条件、实际完成且非替代来源的物理回放收据、原验收及其评价/profile/raw 绑定、相同物理结构和离散化。`core.py` 已支持把三条独立证据列表传给 select；少一个目标、结构不同或未读取证据都不能 SELECT。

现有接口足够执行本轮，不新增 Registry、数学框架、物理执行器或任务评价器。

## 计算前冻结的 BF7 v1

用途是同一条软臂上的原 10 g 末端刚体，分别定位到三个传感器测点；不要求方向、真实接触或实际硬件能力。

| 条件 | 世界坐标目标（m） |
| --- | --- |
| positive_high | (0.285, 0.035, 0.185) |
| negative_low | (0.275, −0.040, 0.135) |
| central_high | (0.295, 0, 0.215) |

三次分别从相同 seed17、全部候选关节位置/速度为零开始，时长 0.6 s、步长 1 ms、控制/采样周期 20 ms。终点误差 ≤10 mm；最后 `[0.54,0.60] s` 的四个 inclusive 样点同时满足误差 ≤10 mm、实际世界系速度 ≤30 mm/s。完整 600 步、采样覆盖、原 evaluator、张力硬界和求解有效性均需通过。有限采样不构成连续时间或重复性证明。

沿用 `reach_hold.json` 的世界系、安装、重力、无外力和非接触地面配置，沿用族域的 10 g 刚体、质心与完整惯量。两段、六条独立理想张力腱，0..8 N，原材料和截面；`distributed_consecutive` 路由规则固定，12 cells/segment，原 MuJoCo 1.2 接口和 serial bending cells 1.0 模型。实际科学结构全部由本分支原 `family_space_v2` 生成。

预筛只改变段长，两个长度均在原合法子域 `[0.10,0.16] m`；原工具从公开默认值启动。它们改变长度分配、总长、弯曲柔度与几何可达范围。材料、近远段模量及腱路在本轮固定，不能据此声称已经识别其敏感性。先验证有限长度结构效应，后续扩大变量域需要独立冻结。

对每个提出结构，分别调用原 CONIC 对三个实际任务重新优化合法控制，读取各自完整 constraint/sample coverage 和 affine replay。仅三个求解均有受支持的有限结果时，确定性汇总 `V_BF7(d)=max_j trajectory.replayed_violation_j`；否则共享分数为未决。符号值是原各任务的最大归一化超限，越小越好，负值仅代表局部模型样点有余量。局部 GVS 物理一致性未验证时明确保留限制。

物理候选先选完整共享分数最小的结构，平分按提案顺序；比较结构固定为第 0 行（若它已是最优，则选下一完整排名结构）。两种结构都使用相同新鲜 0.2 N 初始化与充分的独立控制搜索，不把固定控制响应或未充分调控制的弱基线冒充结构能力。

## 预算、续算与停止

权威配置为 [v1 协议](../../configs/research/bf7_protocol_v1.json)、[预筛 Study](../../configs/research/study_bf7_v1_prescreen.json) 和两个独立多条件 Study `study_bf7_v1_best.json / study_bf7_v1_peer.json`。原共同族域默认值和输入文件由 Study 解析器一次冻结，不借用历史余额。

每结构每目标首轮至多 101 Native 回调、4 轮 response、1 次完整独立回放。4 knots 为 `[0,0.2,0.4,0.58]`，24 系数，原 v2 response；差分 0.02 N、初始半径 0.2 N、系数域 8 N、内部余量 0.02，实际输入仍被 0..8 N 限制。全时域张力控制不是只修补终点；独立验收阈值保持原值。

初始 Study 同时封顶一次可选续算的总额度，但未授权自动耗用：仅完整可靠的真实失败、相对新鲜起点最大归一化超限至少下降 5%，且末段反馈仍持续改善时，才可在读取结果后**另行提交续算配置**，至多增加 100 回调和一次独立回放。保留同一个 Study 累计账本，不修改预算、不转移旧余额。已通过条件不再优化；原工具联合验收可组合该 Study 内此前通过与续算后通过的条件。

单目标累计硬上限 201 回调、2 独立回放、121,800 积分尝试；两个结构三个目标合计至多 1,206 回调、12 独立回放、730,800 积分尝试。原 Store Native 分析入口单位与内部回调分别列账。先阶段独立通过即联合 SELECT；不值得续算或续算结束仍失败则 STOP。另一结构是独立授权的能力比较，不在已通过 Study 内继续搜索。

有限失败不证明结构不可行。不通过时不更改 v1 任务、容差或成功定义。若另立候选版本，须保存 v1 失败、成本与科学原因并先冻结新版本；本轮不会自动开展正式三策略对照或合入主线。

运行入口：`python -m tests.research.bf7_shared_structure prescreen`，随后 `physical best`、`physical peer`；只有另行提交续算配置后才能运行 `physical <role> continuation`。所有科学调用都来自该入口内部原 `core.dispatch / analysis.dispatch`；审计只读取原 Store。

## 首轮证据与一次有限 R1 修订

冻结实现 `7cacc71d5` 的 9 个单任务 CONIC 均 computed/optimal，完整覆盖每任务的终点、四个保持位置点和四个保持速度点；实际 18 数学单位，86.007370100 s Store 数值、95.648562200 s driver。三结构共享分数分别为 1.30、2.80、0.20，均不是局部模型全部可行见证。按规则选择第 2 行和第 0 行，未人工覆盖排序。

首轮五个完整 Native 搜索各 101 回调，独立回放均为 valid_failure，但归一化超限相对初始状态明显下降，最后阶段仍改善，满足原续算规则。其中短臂的 negative_low 已达到 9.786186 mm 位置误差，保持速度 30.001167 mm/s，仍按真实超限失败保留，未改容差。

第 0 行结构的 central_high 在第 37 次 Native 回调、0.272 s 遇到 `floor/payload_shape` 接触，穿透距离 −8.025506 μm，触发原 `NATIVE_V1_REQUIRES_FINITE_CONTACT_FREE_UNCONSTRAINED_STATE`。已记录 36 次完整和 1 次部分回调，累计 21,872 个积分步；不是完整控制搜索或独立验收，未执行该项回放。原 Native 中断输出没有可执行的 best schedule，不重构隐藏控制或假装取得完整反馈。

原任务文件保留 floor 的 `contype=0, conaffinity=1`，与 payload 的碰撞掩码仍可能配对。原协议文本中的“non-contact floor”是对应用意图的描述，**不是碰撞被禁用的事实**；以上真实接触揭示了该表述的局限。模型、碰撞掩码和任务未改变，接触未被忽略，也不推测数值发散先于接触。

[一次 R1 阶段配置](../../configs/research/bf7_v1_continuation.json)在续算前另行提交。五个完整失败从各自本轮最好控制出发，至多再 100 次回调。中断项明确不符合原普通续算条件，使用用户允许“一次有限修订”的权限单独标记初始化修复：将本轮短臂、同一个 central_high 任务的 **valid_failure** 控制逐行不变地传给原 initialize_control，再把初始搜索半径减为 0.1 N。没有导入 B 历史答案，也未传递接受结论；源与目标结构不同，第一条 Native 反馈是固定控制转移后的物理观察，后续才是重新优化的控制表现。

原五个完整失败和一个中断记录见[修订前原始摘要](../../evidence/bf7_v1/initial_before_revision.json)。每个正常续算项累计最多 201 回调；中断修复项最多 37+100=137 次尝试，未使用的 64 次不追加。所有新操作仍在原独立 Study 的既定总预算内，不清空或改写账本；任务、结构和物理限制保持 v1 身份。

工程上同时补齐监督入口续算请求原 API 所要求的 `source + parent` 配对；这是编排参数修正，未改任何科学工具、方法或内核。结果与最终冻结状态将在 R1 完成后追加。

## R1 已 STOP 与用户追加授权的 R2

R1 未找到完整共享可行见证。短臂只有 negative_low 独立通过；第 0 行结构三项均失败。两个物理 Study 和预筛 Study 全部 STOP，未联合 SELECT。短臂最终保持位置/速度为 positive_high 18.054180 mm /54.216819 mm/s、negative_low 9.799966 mm /29.400000 mm/s、central_high 35.128080 mm /105.260936 mm/s；第 0 行分别为 12.204899/35.369749、9.165506/36.522954、30.008270/87.566706。

第 0 行的 negative_low 续算 25 回调后以 `numerical_failure: Positive directional derivative for linesearch` 停止，不是耗完预算或结构不可行。完整输出的多组 24 列 response 条件估计约 10^9–10^11，说明该局部数值参数化值得诊断，单个条件数不证明病态造成全部误差。最终张力峰值约 1.31–2.25 N，未达到 8 N 上界；不能把失败简单归因为张力饱和。

用户随后明确允许重新优化结构、使用现有工具并增加预算寻找可行解。旧实验仍封存，见[追加前累计账本](../../evidence/bf7_v1/sealed_costs_before_r2.json)：**1,067 次 Native 尝试（1,066 完整）、11 次独立回放、646,472 个已记录积分步、175.873905300 s 数值 /220.932142300 s driver**。原 Store 数学入口共 30 单位：18 模型/CONIC 单位加 12 Native 分析入口。

新的 [R2 协议](../../configs/research/bf7_r2_protocol.json)和独立 `study_bf7_r2_*` 账本继续同一组任务 v1，不修改目标、10 mm/30 mm_s、0.6 s、初态、10 g 负载或原物理模型。新[结构族域](../../configs/research/family_space_bf7_r2.json)保留原物理 prototypes，仅明确选择有物理依据的域默认值：近/远段长度 0.16/0.12 m、Young 模量 12/10 MPa。假设是增加少量几何余量并减少重力变形，仍需实际工具检验，不是已有成功设计。

原 mixed search 只提出两个结构，在长度 `[0.10,0.16] m`、模量 `[8,15] MPa` 内实际评价；每个结构仍分别求解三个任务的 GVS/CONIC，新增数学上限 12 单位。前轮 GVS 排名没有得到可靠物理排序支持，因此 R2 预先规定按原提案顺序实际检验，不根据浮点级 proxy 差异挑物理赢家，也不声称数学预筛已验证非线性覆盖能力。

三个初始控制逐行来自本轮 BF7 v1 第 0 行结构的三个完整 **valid_failure**，原 initialize_control 在新结构上绑定，实际起点仍是零状态，不继承接受结论。v1 历史的成功 B 分支和 BF4/BF5/BF6 输入均不导入。R2 控制沿用原 response，3 knots `[0,0.4,0.58]`，仅后两个 knot 的 12 个系数可变，第一组偏置为零；原失败序列保留为基线，每次从零执行完整 0.6 s。这减少了对保持窗影响很弱的早期自由度，并避免首瞬间大幅改变控制，效果仍由真实反馈判断。

每结构每目标最多 **401 次 Native、32 response、1 次独立回放**；至多两个结构新增 2,406 回调、6 回放、1,447,200 步。两个新 Study 各独立授权，不转移旧余额。首先检验第一个新结构，首次三个目标完整独立通过即原联合 SELECT 并停止 R2 科学执行；否则才执行第二结构，无自动续算。不为凑成功更改原任务阈值。

追加入口为 `python -m tests.research.bf7_shared_structure r2 prescreen` 和 `r2 physical best/peer`；入口仍只编排原 Study 工具，没有新增优化器、物理执行器或评分方法。
