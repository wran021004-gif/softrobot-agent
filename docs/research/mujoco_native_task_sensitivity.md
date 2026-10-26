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
