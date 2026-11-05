# PHS-2D 完整协议准入与差异矩阵（2026-11-05）

本报告区分历史冻结协议、当前统一 v2 执行语义、显式新建的 continuous-v1 工程合同。不得把新合同的通过追认成原协议逐状态等价，也不得把原 1 nm 夹具阈值带入 PHS。

原始依据为 `research/phs2d-inverse-passive-design@9d6d160e050c836b87d0563a497fc0ec1c3761a8` 的完整交付 design.protocol、原 evaluator、round3 results/integration 和只读不可变归档。38 个归档分片、1591 个成员及原 XML 内容哈希已验证；具体计数/哈希以本地完整校验清单为准，摘要不发布历史设计和固定 payout。

## 科学任务

| 项目 | 原冻结协议事实 | 新统一工程合同 | 准入结论 |
|---|---|---|---|
| 材料 s | 累计柔性材料长度，剔除刚性间隔；0.3/0.4/0.5/0.6/0.7 | 同一定义，真实 material_point 绑定 | 已实现，代表工况真实验证 |
| 外力 | 每处世界-x ±0.1 N，十工况 | 全部十个具名 load，真实 mj_applyFT/JᵀF | 已实现，完整运行单独列结果 |
| 受力点 | 最后样本相对无载最后样本的 abs(delta-x) ≥10 mm | material_projection_world=[[1,0,0]]，aggregation=last | 可执行，未改门槛 |
| Tip | 最后样本世界 xy 范数 ≤5 mm | tip_projection_world 为 x/y 两行 | 可执行 |
| 比例 | Tip-xy / max(point-x,1e-15) ≤0.30 | 同一真实位移比；不是差值替代验收 | 可执行 |
| 平面外 | 21 个监测材料点及 Tip 的最后样本 delta-y 最大值 ≤2 mm | 所有 21 点和 Tip 均有独立 y 投影上限 | 可执行；逐点上限等价于该最大值上限 |
| 重力与安装 | [0,0,-9.81]，Base z=0.5 m，局部轴转为向下 | 使用原 gravity/mount/payload 原型 | 数值结构比对、真实验证 |
| 准备/加载 | 4 s 无载，独立 4 s 载荷，0.5 s smoothstep | 每个 episode 4+4 s，同样 ramp | 时长相同，基准复用方式不同 |
| 评分 | 0.125 ms 积分，80 步/10 ms 保存；任务位移取最后样本 | 同 dt/10 ms；显式 interval_start；最后样本 | 网格/取值相同，原生刷新相位有差异 |
| 尾窗 | 最后 0.25 s，10 ms 网格；Tip/monitor 速度 ≤1e-3 m/s，qvel∞ ≤0.01 rad/s，漂移 ≤0.5 mm，静力残差 ≤1e-5 N·m，长度超限 ≤50 μm | 无载和加载分别冻结同一尾窗门槛 | 可执行，无载失败阻断加载；加载资格影响独立有效性 |
| 张力/方向/接触 | 单侧正乘子、上限行方向、容量、无接触/无告警 | 原 evaluator 独立检查，并在每物理步记录/累计张力、长度、方向、接触 | 实际执行；不以位置好看掩盖 invalid |
| 路线几何 | 真板孔与 payload 实体内锚点；保存姿态做带绳半径实体相交检查 | 当前冻结 route_check=score_grid，801 poses/episode | 代表路线真实通过；非每步或连续扫掠证明 |

## 状态和数值差异

| 状态/过程 | 原 runner | 当前 v2 / continuous-v1 | 是否严格等价 |
|---|---|---|---|
| 无载初态 | 重新求硬绳静力，取 qpos；零 qvel 建新 MjData 后积分 4 s | 候选生成器强制全部命名坐标和速度为零，再积分 4 s 并资格检查 | 否 |
| 每次加载初态 | 同一个合法无载基准的末 qpos；新 MjData，qvel/warm-start/time 重置 | 每个独立 episode 从相同零完整状态开始；无载末完整积分状态连续进入加载 | 否 |
| 每次加载独立性 | 加载间不继承受载状态 | 不同 episode 重建 MjData；彼此独立，无载准备也重复 | 是：独立性；不是共享基准身份 |
| 加载时钟 | 加载 0–4 s | 总时钟 4–8 s，力程序减去 stage 起点 | 时间偏移可对齐，warm-start/速度语义不同 |
| force phase | interval-start 力；逐步前向刷新，10 ms snapshot 重映射外力 | interval-start 力，逐步 post-step 还按更新几何重新映射外力 | 存在真实原生状态/约束求值相位差异 |
| static balance | 拷贝原积分状态，qvel=0，再映射力并 forward | 使用 copied_integration_zero_velocity | 语义一致；cold 版本作为另一显式选项存在 |
| 积分器/求解 | implicitfast、100 iterations、1e-10 tolerance、冻结 tendon solref/solimp | 使用相同实际选项 | 相同，实际原始记录保存 |
| 地面位置 | 原实际 XML 为 z=0 m | 新 bridge 从通用 task scaffold 继承 z=-0.02 m；碰撞掩码相同 | 否；本次参考无接触不能证明全域等价 |
| Windows 编译栈 | 被动历史模型专用 32 MiB 编译线程 | 通用 loader 使用 8 MiB 编译线程 | 工程实现不同；本次实际已编译 144 维模型，无原生崩溃 |

实际 XML 核对还发现一个本次准备的来源差异：历史候选 configuration 的通用 task scaffold 地面为 -0.02 m，而历史 PHS runner 明确覆盖为 0 m。新 bridge 继承了前者。原生 XML SHA 分别为旧新鲜执行 75de64d1… 与统一名义 26de8786…，未宣称同一模型身份。该差异已记入本报告，必须在未来继任合同中明确修正到原 PHS 地面或作为单独科学版本批准，不能静默改动本次已运行 task/Store。原地面与新地面都不构成本次参考载荷的已观测接触，仍不能据此宣称全域等价。

这些区别通过新 task_id/task_version、不可变 protocol_source 和独立 Study 身份公开冻结。旧任务、旧评价结果及旧账本均不变。配对数字接近也只证明本次有限结构/工况下的一致程度，不能证明两种协议在整个 FamilySpace 上等价。

## 结构、数学和独立验收

原轻量域只授权一段、一根腱、每段两个单元；不能代表完整 PHS。新 `family_space_phs2d_admission_20261105_v1.json` 授权九段、四腱、每段八单元，四个独立固定 payout，Base-only 路由、实体孔覆写及真实 payload 包络内终端锚点。它是独立实例版本，未扩写原冻结域。未选择的旧域仍拒绝这些拓扑/特殊路由。

最小公共移植是默认关闭且旧序列化不输出的 terminal_payload_anchor、默认空且旧序列化不输出的 guide_hole_positions_m；复用原生成器、实体孔包络/清隙检查、候选身份、编译器、TaskAdapter、Worker、Store、PhysicalReplay 和 evaluate.passive_response@2.0.0，没有第二套机器人、Registry 或 Benchmark runner。7 项定向回归通过，覆盖旧配置序列化、显式授权、未使用/未知孔、板包络和 payload 实体锚点。

新参考装配的 parts（JSON 归一化后）、tendons、dofs、tip、discretization、section_quantities 与历史实体结构逐项相同；parts 的 Python tuple/list 类型差异未被误报成物理变化。原质量、惯量、截面、材料和刚性间隔保留；总质量 0.058356636458548904 kg。主动 actuator=0；模型 XML SHA 与任务/设计/协议 SHA 分开保存。

注册数学 Worker 已实际处理 144 坐标、4 根腱的加载平衡：1 次评价、1 次模型构建、2 次平衡求解、288 个 Hessian 列、0 物理积分。正张力 2 根、松弛 2 根，LICQ/严格互补和局部正定资格通过；驻点残差 6.44e-9 N·m，最大长度原始违反 6.43e-13 m，Tip-x 正张力行空间相对残差约 0.0214275。原优化器 success=false，原资格器返回 nonconverged_numerically_qualified，两个事实都保留；未把它写成成功终止或全局稳定性证明。硬绳静力与实际 MuJoCo 软约束反力并不相同，正式通过只由独立动态评价建立。

数学注册能提供 J_tip/J_length、张紧集合、单侧锥/零空间、KKT、柔顺性及条件导数；数值求导路由区分固定活动集、切换和无效探针。完整十工况的 affine 数学可行性求解尚不适用；现有有限时域响应可通过真实 MuJoCo 比较/优化，成本随完整协议显著增长。新增实体孔坐标尚未接入连续参数 catalogue 和其求导授权；全 generation 请求已可表达，selected-parent 的 `changes` 数学/生成短接口不能假称已经覆盖所有腱路坐标。需要另行完成通用参数声明及原方法/工作点准入。

完整统一 Replay 的资格包括同一候选身份、相同完整初态、所有十个 load、完整采样/积分、基准/加载尾窗、张力/长度/方向/容量、实体腱路、无接触、评价器全部约束和独立证书。原始 L2 每步 CSV 在新私有 Store 中；未只返回位置。旧实现对照仍只取得 development_pass，不是统一 SELECT。工程参考结构绝不能成为自主 Main 的候选或初始化。

## 成本与当前准入边界

十工况 continuous-v1 为 10×(4+4)/0.000125=640000 步，1 个 MuJoCo 模型、10 episodes；基准不复用，独立评价本身 0 积分。现有 Worker 按 10 episodes 预约 backend 资源并保存实际 attempts/completed、模型构建、原生 forward、几何检查、收据与结束边界。原协议旧实现为 (1 baseline+10 loads)×32000=352000 步，模型按原 runner 每次独立构建；两种成本不得混算。

新工程预算及未知执行规则见 preflight；没有无限物理或 Provider 预算。一次完整名义执行不能建立时间步收敛、扰动稳健性或整个设计域可靠性。若要对 continuous-v1 完整十工况执行半步与初态扰动，单独需要 1280000+640000=1920000 个积分步（每次仍含重复基准），以及相应独立预算/任务身份。每物理步几何检查会从每 episode 801 poses 增至 64001 或 128001 poses，必须另算几何检查与墙钟成本。

当前生成器仅允许 all_candidate_dofs_zero_v1；不能通过普通正式生成接口冻结非零初态扰动或原始 KKT 初始化。saved-state 输入只接受当前匹配结果的完整原始状态，不能伪造一个扰动状态或把历史轨迹重新评分充作新物理。因此原协议严格复现、初态扰动准入和新增孔坐标的连续研究授权是明确的剩余接口/科学版本工作，不以本轮接口热修掩盖。


本次完整统一执行的 Worker 墙钟为 2432.98 s（约40.55 min），实际成本还包括2576040次原生forward和25664040次绳段/实体检查。完整有限时域单参数两尺度求导至少5次评价，即50 episodes/3200000步；按本次运行线性估算约200 min，估算不是墙钟上界。原轻量Study的180 s单Worker保护不能直接继承来执行它。现有有限count模式可用明确评价/episode上限配置新的独立执行合同；无限数学配额模式的固定watchdog及其适用范围也要重新审查。不能以“底层已注册”声称原轻量Worker预算足够完整PHS研究。

旧protocol.cells_per_segment=12是继承缺省，不是获胜结构的实际网格；恢复依据为不可变generation及compiled physics中每段8单元、共144坐标。模型仍是原弯曲单元、无摩擦直线腱、单侧软长度限位模型；轴向/剪切/扭转、绳弹性、连续绳自接触和真实材料标定未由本次实验覆盖。

保存的注册零空间为144×142：Tip-x在该空间的相对行范数为0.021427，受力材料点-x为0.492142；真实+0.1 N外力的广义方向在该空间中仍保留约49.21%的欧氏范数。原内核给出的该点x向切线柔顺性约0.235821 m/N。这些是对已存注册矩阵的乘法提取，未新求解或积分，说明局部模型能区分‘Tip受约束’与‘受力点仍可变形’，不能作为完整动态成功的替代。


静力求解默认也分别保留：历史protocol为max_iterations=400、ftol=1e-13、stationarity_tolerance=1e-6 N·m、minimum_reduced_eigenvalue=1e-7；当前注册PassiveModel默认为150、1e-12、1e-7 N·m、1e-8。两者Hessian差分步均为1e-5 rad。旧实现复现使用其原值；本轮当前注册静力诊断使用当前冻结值。统一continuous-v1动态并不以该硬绳解初始化，因此不能把静力协议差异隐去后宣称完整旧协议同一身份。
