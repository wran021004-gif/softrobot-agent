# A4 MuJoCo 原生力学与任务敏感性

基线 `feat/mujoco-task-capability-parameters@938d7d21137f9b4aafbd8b24984c30abbfeb55c2`。
独立分支 `research/mujoco-native-task-sensitivity`。遵循根 AGENTS.md。

## 数值执行前冻结的有限试验

2026-10-26，Asia/Shanghai。新增物理积分硬上限 **20,000 步**，失败、重试、
前缀重建、控制探针全部计入；达到预算立即停止，不启动下一阶段。
首先审计 R1 design_package 的原结构和已保存绝对张力序列（0.50 s，dt=0.0005 s），
接触则保留首次原生检测时间区间、几何体和消耗，停止该原生分析，不更改碰撞。
合法替代使用 A3 已保存的单段 S7 工程候选（8 个具名 hinge、3 腱、4 cells），
沿用其完整冻结任务（0.35 s，dt=0.002 s，控制/评价采样 0.01 s）和 1 N 绝对张力序列。
这是工程候选的任务，不冒充 R1 B3 的通过能力或硬件结论。

三个连续独立方向沿用 `nonlinear_response_v2` 的 dp/ds=1：

| 路径 | 基值 | h 与 h/2 | 独立留出点 |
|---|---:|---:|---:|
| segments.0.young_pa | 7,200,000 Pa | 10,000 / 5,000 Pa | +7,500 Pa |
| spans.0.radius_m | 0.018 m | 0.000010 / 0.000005 m | +0.0000075 m |
| segments.0.sections.0.parameters.semi_y_m | 0.0095 m | 0.000010 / 0.000005 m | +0.0000075 m |

原 FamilySpace 无固定总长等式，本轮不额外增加长度交换方向。授权目录仍完整保留。
每个结构使用同一零态约定、输入序列、原 local_control_search：两 knot [0,0.34] s，
窗口 [0,0.35] s，active_coefficients=[0]（第一 knot 第一张力通道），
evaluation_requests=3，iterations=1，difference_step_n=0.01 N；其余设置沿用原默认。
共 16 个候选最多 48 rollouts、8,400 步。固定控制与有限预算重优化分别分析。
控制方向复用基线 T1 的 0.01 N 探针，再用同算法分别请求 0.005 N 和
0.0075 N（后者仅作留出检验），至多另 1,050 步。没有新搜索器。

从替代候选固定控制的保持速度峰值选择原生 checkpoint；所有结构在相同具名
qpos/qvel 和绝对输入下做原生力学对照，与各自零态完整任务响应严格分开。
固定状态对照通过原 fixed_input_structure_v1 路由，保留其短端点作用域。
原任务 adapter 提供阈值；不修改积分器、控制含义、独立 evaluator 或任何原 Store。

预测模型只用 ±h、±h/2；留出 +0.75h 不参与建模。判读保留逐保持采样、
两尺度差异、活跃约束/时刻切换、相对阈值及实际变化的误差。差异容限仅是
工程辨别标准，不是严格误差界。优化触及预算始终保留 best-found/unresolved。
使用原 research_analysis、Worker、Store、费用账本、ResultCard 和 L1/L2 查询。
不启动 Provider、Agent Study、NMPC、PPO、独立物理验收或大规模扫描。

## A4.1 审计与补充

A3 已有 mj_fullM、mj_solveM、mj_jacSite、mj_jacDot、bias/passive/actuator、
零速度重力偏置分离、腱长/力臂、驱动力映射、末端加速度输入映射、质量条件数与
力平衡残差。新增原生 qpos/qvel、坐标/通道/输入符号、瞬时有效域、引擎质量分解
逆对角、张力边界与逐通道饱和、驱动力映射一致性残差，以及逐物理步接触限制诊断。
原矩阵留在 `/native_dynamics/mechanics`；简要解释通过原 native_analysis 交付。
内部一致性不证明硬件准确性或未来轨迹预测正确。

## A4.2 实现

原 T1 保留基线保持速度峰值的完整 native checkpoint，未为此增加积分。
原控制搜索的已有 FD callbacks 产生逐采样约束对控制系数的响应，不新增搜索器。
T2 继续仅聚合已拥有的 T1，增加逐采样约束割线、合法区间无量纲化、活跃时刻切换、
两尺度对照和独立留出预测。V2 direction 的可选 validation_coordinates /
validation_t1_results 是唯一请求扩展；未使用时原请求序列化不变。
所有固定控制与重优化结果分别报告；有限优化上限不建立 V_tau(d) 或最优梯度。
fixed_input_structure_v1 额外保留广义力、qacc、末端与腱 Jacobian 的原单位差分数组。
原生瞬时速度导数张力盒范围只描述当前工作点，不替代完整任务响应。

## A4.3 真实结果及适用范围

**原生物理信息可以建立任务相关局部敏感性；本轮验证支持冻结候选、输入参数化和
小扰动内的固定控制预测，不支持最优任务能力梯度、全局下降或硬件保证。**

### R1 真实工作点

R1 原始 0.50 s 控制序列新增回放 1,000 个物理步，逐步未检测到 contact / 约束限制。
因此没有把 R1 宣布为不适用，也未删除碰撞。A3 历史两段结构的接触拒绝事实仍保留；
不能把该事实推广到另一条 R1 结构/轨迹。完整任务多参数检验采用前述已经冻结的
8-DOF 工程基准，R1 的 48-DOF 原生工作点另做三方向两尺度力学对照；两者不混用。

R1 原始保持峰值在 **0.49 s**，速率 **0.01993431973 m/s**。
以原始 qpos/qvel、前一已执行区间的四路实际张力
`[0.771471,4.739797,1.811438,0.540130] N` 比较，所有模型重置 solver history。
这是同坐标/输入的瞬时比较，不是重建完整积分历史或相同平衡态。
四路均未饱和；质量条件数约 **1.3340e6**；质量方程与驱动映射残差分别为
**1.2490e-16 / 2.7756e-17 N·m**。这些只诊断 MuJoCo 模型内部一致性。
末端加速度输入映射奇异值为 **212.4064 / 177.2261 / 5.42158 m/(s²·N)**。
当前速率导数为 −0.27859 m/s²；固定此状态的合法张力盒可产生约
[−631.939,1692.530] m/s² 的瞬时速率导数。该范围不构成可执行的整段刹停策略。

| R1 同状态正向扰动 | 质量矩阵相对变化 | 驱动力映射相对变化 | 末端加速度向量相对变化 |
|---|---:|---:|---:|
| distal Young +10,000 Pa（基值 5.4 MPa） | 0 | 0 | 2.97102 |
| spans.0.radius +0.000010 m | 0 | 0.000277311 | 0.142048 |
| distal 截面 0 的圆半径 +0.000010 m | 0.000494819 | ≈4.86e-16 | 0.280808 |

表中是完整数组范数相对差，不是任务改善率。±h 与 ±h/2 全部保留；Young 的
质量/驱动映射不变而被动力/加速度改变，腱半径改变 moment arm，截面同时改变质量、
惯量与刚度。R1 变体未做完整任务 rollout，因此不发布其整段任务方向或预测误差。

### 同一合法基准的完整任务矩阵

工程基准的原始终点/保持位置峰值为 **0.137489893 m**，保持速度峰值为
**0.0747813383 m/s**，J=**12.74898925**，任务尚未通过。
保留 [0.30,0.35] s 的六个位置和六个速度样本以及终点约束，共 **13 行**。
固定控制的最坏 J 一直是 0.35 s 终点位置；保持速度峰值一直是 0.34 s。
本次数值样本未发生活跃约束/时刻切换；切换和符号不一致的人工单元夹具会保持 unresolved。

下表是 h/2 中心差分；位置列同时适用于本次终点和保持位置峰值，速度列是保持峰值。
原始矩阵还保存每个采样点、左/右割线、物理单位、合法区间与原结果指针。

| 参数（单位） | 固定控制位置响应 m/参数单位 | 固定控制速度响应 (m/s)/参数单位 | 固定控制 J 响应 1/参数单位 |
|---|---:|---:|---:|
| Young（Pa） | −9.87688484e-10 | +1.27822401e-9 | −9.87688484e-8 |
| 腱路半径（m） | +1.52380386e-5 | +2.50482368e-4 | +0.00152380384 |
| 椭圆 semi_y（m） | −0.700686781 | +9.46808541 | −70.0686781 |

增加 Young 或 semi_y 在本局部减小位置误差，却增大保持速度；一个 J 改善不能代表所有
约束同时改善。腱路半径固定控制效应极小，其 +7.5 µm 留出点实际位置变化只有
**+1.14308e-10 m**，速度变化 **+1.87899e-9 m/s**，不构成实用设计改进依据。
原生力臂变化确实存在，但不能把它解释为等比例任务贡献。

### 未参与建模的新 rollout 检验

每个留出点都独立重建、真实积分，未进入 ±h / ±h/2 模型。下表采用 h/2 模型，
“相对阈值误差”是所有 13 行中 max(|预测−实际|/各自行冻结阈值)，
“相对实际变化误差”是逐行比值的最大值，不能把两列的最大值当作同一采样点。

| 留出扰动 | 最大相对阈值误差 | 最大相对实际变化误差 | 方向 |
|---|---:|---:|---|
| Young +7,500 Pa | 3.40253e-5 | 7.5052% | 所有有辨别意义的采样方向一致 |
| 腱路半径 +0.0000075 m | 1.98434e-10 | 0.020392% | 数值一致，但效应微小 |
| semi_y +0.0000075 m | 4.43291e-6 | 0.216861% | 一致 |
| 控制第一 knot / 第一通道 +0.0075 N | 6.50808e-6 | 6.56464% | 一致 |

Young / 腱路半径 / semi_y 两尺度完整逐采样导数的相对差约
**4.8341e-6 / 1.1151e-8 / 9.1832e-6**，没有方向矛盾。
Young 留出点最大的保持速度预测误差为 **6.80505e-7 m/s**，
semi_y 为 **8.86583e-8 m/s**；其终点位置误差分别约 **6.82071e-9 / 1.72107e-9 m**。
控制 0.01 / 0.005 N 既有探针导数相对差为 **1.26947%**，留出检验的最坏速度误差约
**1.30162e-7 m/s**；J 预测误差为 **−8.20855e-9**。

所有 18 次 T1 都在 iteration_limit 停止，各 3 callbacks、1 次响应更新，机会可比。
baseline best-found J=**12.74636206**。重优化 Young / radius / semi_y 的 J 割线分别约
**−9.60991e-8 / −0.127176 / −67.1178** 每参数单位；尤其 radius 的符号和固定控制相反。
这些结果始终 **unresolved**，不冒充 V_tau(d) 或其梯度，也不继承固定控制的验证可信度。

Python 绑定存在 mjd_transitionFD；本次为 implicitfast、Newton，每个控制区间含 5 个
物理步。选择复用完整区间/完整任务的输出探针，没有计算全状态稠密 Jacobian，
没有把单物理步导数当作控制区间导数，也没有改求解器设置。
原生函数的单步定义与 RK4 限制见 [MuJoCo 官方函数说明](https://mujoco.readthedocs.io/en/stable/APIreference/APIfunctions.html#mjd-transitionfd)。

## 后处理修复、费用与测试

数值计算均成功；第一次交付断言误把 engineering 模式的正式授权门槛当成错误。
修正断言后按原 operation receipt 复用全部 29 个结果，新增积分 **0**；未放宽真实就绪条件。
后处理审计又发现 FamilySpace 返回 `bounds`，代码误读 minimum/maximum，使初次 T2 的
无量纲列为空。已改用原授权边界，并零积分重读原样本生成补充矩阵。合法参数跨度为
13,000,000 Pa、0.009 m、0.009 m；该归一化仅比较尺度，整个区间并非已验证预测域。
原 T2 artifact 未改写；补充结果见 summary 的 final_saved_sample_review 精确查询。

最终工程判读要求预测误差 < 实际变化的 25%，材料辨别尺度为归一化 1e-8，
两尺度相对差阈值为 5%。这是把最初“误差小于变化”收紧后的经验辨别标准，
不是数学误差界或任务验收阈值。原样本零积分复核后，三结构固定控制与控制留出结果仍通过；
所有重优化方向仍 unresolved。未修改任何真实 rollout、原阈值或历史结果。

累计新增积分 **10,570 / 20,000 步**：R1 1,000，18 次 T1 共 9,450，
固定状态短端点对照 120。共 **79 rollouts、58 次 NativeModel 构建、47 次力学读出、
4,145 次显式 forward**；模型/原生操作费用同时包含直接 R1 审计和准备验证。
原分析账本计 **44 个模型求值、29 个 contained workers**，29 次操作调用已封存收据；
postflight 不产生新的模型/rollout。具体 wall 与累计 numerical_s 以
[`summary.json`](../../evidence/mujoco_native_task_sensitivity/summary.json) 为准，避免相加有包含关系的时间。
Provider、NMPC、PPO、独立物理评价全部 **0**。未启动新 Study 或下一阶段扫描。

**67 项不同定向测试通过，另 1 项门控烟测跳过**（本轮真实试验另行执行）。范围为
native_task_sensitivity、mujoco_analysis、native_control、nonlinear_capability、
family_nonlinear_parameters、task_analysis_contract 和 f3_family_sensitivity。
新增测试用明确人工夹具验证非光滑/方向相反/误差与改善同量级/裁剪/重复留出拒绝、
区间归一化及三路径 L0 展示；真实试验验证引擎数组、合法重建、留出 rollout 和精确读证据。
原回归的一个测试依赖 discovery 路径导入 test_mainline；补齐测试搜索路径后仅重跑该项通过。
一个新增测试曾出现代码移动造成的 NameError，修正后仅重跑两项受影响测试通过。
保留原 CLARABEL accuracy warning，不据此推断更强数学结论。未重复全仓测试或实际积分。

## Agent 查询与交付

继续使用 `research_analysis(AnalysisRequest)`、`mathematical_capabilities`、ResultCard、
`mathematical_decision_view`、原 `evidence_read`。L0 把两个差分尺度归为同一物理路径，
因此三个参数均可见；原始 6 个 stencil、13×参数矩阵、完整控制和轨迹按需读取。
完整参数目录未压入 L0。engineering 目录仍如实显示正式 Study 未授权，未自动开放旧 Study。

本地原 Store：`runs/mujoco-native-task-sensitivity/store`；没有新增 Store 镜像/归档。
小型交付索引 summary.json 包含所有候选、结果、成本和以下精确查询：

- T2：`d444dbfc760330bfe1e6643b5315762d4dc8e15b18b7cc6aaf4762179215c0e2`。
  L1：`view=working_set, pointer=/mathematical_decision_view/nonlinear_response`。
  原逐采样矩阵：`/nonlinear_response/directions/{0..5}/task_sensitivity/{fixed_control|reoptimized_control}`。
  原生控制矩阵：各 T1 的 `/native_dynamics/control_task_sensitivity`；留出控制验证：
  `/nonlinear_response/control_prediction_validation`。
- 原生工程基准 mechanics：`7a1ff14a7281328a5ead1af4f819aa76ac28719c3265189b942dece83f4ab8a9`，
  `view=full, pointer=/native_dynamics/mechanics`；包括原生状态、矩阵、力和输入含义。
- R1 原始状态与三方向两尺度原生矩阵：
  `74d5d1e70123b095862aa5f6b3ea64eee877bd396bfa188e929f2e9cf0c990dd`，
  `view=full, pointer=/mechanics` 或 `/directions`。
- 完整无量纲矩阵和收紧判读复核：summary 的 `final_saved_sample_review.reference`，
  `view=full, pointer=/normalized_sensitivities`；每行仍指向原 T2 的物理单位矩阵和采样行。

下一次有信息价值的实验是：在 R1 原冻结任务上，先针对其 0.49 s 工作点选择一个小方向，
用同控制的留出 rollout 检验瞬时敏感性是否传递到全部保持样本；需要新的有限预算与冻结，
本次没有执行。工程基准上优先研究位置与速度的权衡，不能只沿减小 J 的方向选结构。

提交：A4.1 `770d7cc6d`，A4.2 `f84bd4eaf`，A4.3 执行冻结 `02cb086b5`，
最后报告提交另见分支 HEAD。前三次均普通 push 至用户指定 research 分支。
原生数值源冻结为 `02cb086b55cff535fd173f074965dfaddd74dd44`；最终补充解释保留独立来源，
没有把报告提交冒充已执行 worker 的版本。没有 force push、合并 main 或修改其他工作树。
