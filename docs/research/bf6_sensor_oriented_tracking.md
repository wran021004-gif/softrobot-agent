# BF6：携带刚性工具的定向轨迹扫描

## 范围与冻结

用户补充指令授权将下一任务扩展为有真实物理语义的、无环境接触的携带工具定向 Tracking，并允许分阶段提交、普通推送及有限独立可行性执行。BF4 S2 已在 `4a5ddea86` 完成并推送，原六组冻结、结果、失败和成本均保持封存；已有 BF5 可行解的[只读工具审计](bf5_witness_tool_audit.md)未新增积分，也不作为本新任务的通过证据。

新候选是轻型传感器接近工作面附近后作定向横向扫描，不要求真实传感成像或接触。以[独立冻结协议](../../configs/research/bf6_sensor_oriented_tracking_freeze.json)、[任务](../../tasks/bf6_sensor_oriented_tracking_v1.json)、[Study](../../configs/research/study_bf6_sensor_oriented_tracking.json)和[刚性工具家族配置](../../configs/research/family_space_bf6_sensor_tool.json)为权威；所有条件在 BF6 科学搜索前固定。

| 条件 | 冻结值 |
|---|---|
| 世界系 | 原 `world_base_x_forward_yz_cross_section`，长度 m，方向无量纲，角度 rad |
| 位置路径 | 0 s `(0.298, 0, 0.150)`；0.3 s `(0.290, -0.025, 0.120)`；0.6 s `(0.290, 0.015, 0.120)` m；按时间线性插值 |
| 工具轴 | `tip_site` 局部 +x；世界目标节点分别为 +x、单位化 `(1,-0.18,-0.20)`、单位化 `(1,0.12,-0.20)`，同节点时间作 normalized-linear 插值 |
| 工具中心评分点 | `payload` body 局部 `(0.014,0,0)` m 的 `tip_site`，局部安装旋转为单位姿态 |
| 全程位置验收 | 0.02 至 0.60 s 共 30 个 post-step 时刻，最大 `||p_k-r(t_k)|| ≤0.012 m` |
| 全程方向验收 | 同 30 个时刻，最大 `acos(clamp(a_k dot a_ref(t_k),-1,1)) ≤π/18 rad`（10°） |
| 积分与输入 | 0.6 s；1 ms 物理步；20 ms 控制/采样；六独立理想张力，原 `0..8 N` 物理界 |
| 初态与起点 | 同一个预先选定的合法 P1，全部命名 qpos/qvel 为零，常量 0.2 N 控制；不导入 BF4/BF5 成功控制 |

角度容限代表轻型传感扫描的允许指向锥，是该新任务首次冻结的条件，不是放宽旧 BF5 的 3°。扫描阶段横向位移 40 mm；评分角点与终点相隔 40 mm，大于两倍 12 mm，排除只停在一个位置的成功。这里按全部时刻验收，不能以最终位置或最终方向代理整个任务。

## 外力、真实负载与安装审计

`external_forces` 的 `TimedForce` 当前只支持世界系恒定力、命名 body 的质心作用点、控制网格上的起止时间。`scene.assemble_physical` 绑定实体，`_bind_mujoco_forces` / `_apply_mujoco_forces` 在每次积分前更新 `xfrc_applied`，在力窗外归零。它可改变广义力，但不会增加 body mass、质心惯量或质量矩阵；也不表示偏离质心的工具端力、接触摩擦或法向力。故恒定 `m*g` 不等价于携带质量 m 的动态运输。

现有 `family.design` 的 `Rigid(kind=payload)` 已有正质量、局部质心、完整质心惯量张量及刚性安装连接。编译器 `compiler.resolve` 校验对称正定/三角不等式的物理惯量，并将 payload 作为无自由度刚性子 body 保留；`mjcf.compile_xml` 写出明确的 `<inertial mass pos fullinertia>`，已有铰链动力学直接包含其重力、平移/转动惯量和惯性耦合，不需要新负载求解器。

BF6 复用原 10 g payload/安装体，增加一个与其质心和主安装方向同址的 10 g 理想刚性传感器，将二者精确合并为一个 20 g body。相同质心下质量与完整质心惯量直接相加，无平行轴偏移项；这是明确的建模假设，不是某款硬件的 CAD 或测量辨识结果。

- 总质量 `0.020 kg`；质心为 body 局部 `(0.007,0.001,-0.002) m`。
- 完整质心惯量 `kg*m²`：`[[1.2e-6,2e-7,0],[2e-7,1.6e-6,2e-7],[0,2e-7,1.8e-6]]`，包含非对角项。
- 原安装体/额外传感器各占总质量和惯量的一半；20 g 总 body 仅有现有刚性连接，不新增铰链、工具运动或接触。
- `external_forces=[]`。本任务不是外力近似，不能通过加一个质心力来满足其负载验收。
- 现有 `tip_site` 方向继承父 body。本轮冻结单位局部安装姿态，未宣称支持任意 tip attachment quaternion；已有 body 安装旋转仍由原物理编译器处理。

新 `check_rigid_tool_definition` 在 admission 校验任务所要求的 mass/COM/tensor/site 与候选真实组件一致；Native 和独立 playback 各自对自己编译的 MuJoCo model 核查 mass、COM、主惯量及其 quaternion 还原的完整张量、body 无自由度和实际 site 安装。独立协议增加 `rigid_tool_binding`，缺失或不一致不能通过。

## 接口与已有链路复用

新增 `reference.oriented_tracking_goal/evaluation`、`task.oriented_tracking`、`evaluate.oriented_tracking`，经原 TaskDefinition、Registry、TaskAdapter 工厂进入研究链路。位置条件直接投影到未改动的原 `evaluate.tracking@1.0.0` timed 分支，保留相同逐时刻误差和 RMS/终点诊断；其位置 task 投影只用于该 evaluator 的复用，不移交任何旧通过身份。

工具轴 Native 与 playback 均取真实 `R_tip_site @ axis_local`。独立 evaluator 单独检查方向信号完整性、单位长度、网格和逐时刻真实 arccos 误差；方向绕自身的 roll 不受约束，不把工具轴当完整六维姿态。

原 Native response 同时使用全部 30 个位置 norm 条件和 30 个等价轴锥：单位轴有 `||a-b||=2*sin(angle/2)`。排名和验收仍保留真实位置/弧度两项误差和归一化违反量。affine/GVS 对新任务方向不支持时仍为 `not_applicable`，没有新姿态求导、STL 或通用优化器。

新 backend 注册 `backend.family_mujoco@1.4.0` 复用同一物理编译、积分和固定序列回放，只声明这个新任务的显式 Native 序列路线。普通 NMPC solve 明确不支持方向任务，不能静默只优化位置；不启动 Provider/NMPC/RL。

## 计算前声明的有限执行与恢复

只运行一个 P1 构型、一个 fresh 起点，原 `local_control_search_v2` response、四结点 `[0,0.2,0.4,0.58] s`、差分 0.02 N、初始信赖域 0.2 N、修正界 ±2 N。上限为 **151 次完整 Native 回调、6 次迭代、一次完整独立回放、91,200 步**。原工具已有的 0.5% 内部规划裕量只用于局部目标，物理验收仍是冻结的 12 mm / 10°。

[监督入口](../../tests/research/bf6_oriented_tracking.py)只调用原 generate、initialize_control、`research_analysis:mujoco_direct_control_v1`、evidence read、physical_replay、SELECT/STOP。Native 达到声明目标或有限上限后将完整 best 序列独立回放一次；首次完整独立通过立即 SELECT 并封存。没有私有 warm-start、参数扫描、任务/容限调整、通过后追分或额外鲁棒性实验。若失败，保留 finite-search failure 和下一步最小缺口，不宣称结构不可行。

使用原 Store 稳定 operation key、pending reservation 与 receipt 恢复，不清空 Store，不重发未知结果。六阶段历史 BF4/BF5 费用不转移为新任务余额。

## 定向检查与当前状态

20 项定向检查已通过，覆盖 timed 方向插值、全 30 时刻覆盖、原 Tracking 位置评价等价、中途位置/方向失败、缺失信号/错网格/缺失负载绑定、实际编译质量和完整张量、质心外力不可代替负载、Native 两项真实约束，以及原 BF4/BF5 回归。只有一个工程 fixture 的模型编译，0 forward/积分；它不是候选科学证据。

科学搜索将在上述协议的提交绑定后执行。真实结果与费用随后追加；本次只读旧 BF5 审计仍为零新增科学计算。

## 科学与应用边界

软臂仍为两主弯曲轴 cell 模型，不包含独立扭转、剪切、伸长、硬件驱动动态、真实传感图像质量或实际表面接触。原模型的地面碰撞边界保留，但本任务不授权工具接触环境，不实现接触/摩擦/法向力控制、笔尖—纸面接触、完整写字或书写质量评价。这些只列为未来接口与评价缺口，不阻塞本轮无接触扫描。
