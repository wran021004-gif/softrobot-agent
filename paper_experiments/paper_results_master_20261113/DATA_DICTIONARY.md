# 数据字典与取数规则

## 基本格式

CSV为UTF-8 BOM；数值用SI单位，列名后缀明确m、s、N、rad等。结构化对象以JSON字段保存；建议优先读取`SOURCE_DATA/FULL_CASES.json`以免手工解析单元格。空白缺失字段统一为`unavailable`；未执行、不适用、未暴露不能写成0。布尔passed保留原值。TASK_CASE_RESULTS中的source_reference指向Store artifact或原始评价器记录。

## 任务、结构与工况

`system=Full`；一项任务一行。`required_conditions`与`control_conditions`分列；T10两frozen工况不进入required分母。`candidate_id`是原候选身份，不能把不同候选的最佳工况拼为一个通过结构。T07必须同硬件，T10必须同共同控制器配方。task_version/source_classification保留原分类。

`CANDIDATE_EVOLUTION.csv`每行是某run内唯一物理结构，候选artifact别名全部保留。排序仅依据该Store首次保存顺序，不推定跨run时间或父子关系；`exact_changes_vs_previous_stored_structure`是描述性字段差异，不是因果对照。完整candidate保存在SOURCE_DATA/CANDIDATES；确切研究意图、先前证据与决策见KEY_RESEARCH_NODES和SELECTED_RESEARCH_EVENTS。

## 性能语义

每项task metrics必须同时携带工况、时间窗、采样/聚合方式及原阈值。ALL_TASK_RESULTS中的primary_metrics是原结果字段，不是跨任务统一分数。带单位的同义字段保留原名以便查证。约束上界/下界方向来自原constraint_thresholds和原task定义；不要从正负号猜方向。

T01/T02/T03/T07保持窗或终端误差不是同一指标；T04完整3D RMSE/最大误差不能由y–z图替代。T05/T06有向轴误差单位rad，不能当作位置误差。T09深度、接触力、按钮位移和保持时长含义不同。T10完整验收是密集步检查，10 ms信号曲线只供展示。

PHS-2D：point_x_abs_m为原受力材料点x位移幅值；tip_projected_m为Tip投影位移；评分末窗[7.99,8.0] s，阈值分别≥10 mm、≤5 mm，ratio≤0.30。max_plane_y_m≤2 mm。尾窗是无载[3.75,4]及加载[7.75,8]，漂移≤0.5 mm，Tip/监测点速度≤0.001 m/s，关节速度≤0.01 rad/s，静力残差≤1e-5 N m。几何为被检查保存姿态合法，不是连续时间碰撞证明。半步长独立标识。PHS候选进展的evaluation_kind、scope、case_count不可丢弃；局部QP、2/6/10工况不能直接连成“收敛曲线”。

P3/T08：材料点s=.7，不是Tip；双方向、20 s分段载荷与恢复；低载≥6 mm，高载≤25 mm，残余≤2 mm，刚度比≥1.5，成对机制与其它资格各自检查。当前两段二腱最终任务与历史四腱消融分开。

## 时间序列与动画

`*_SAMPLES.json`为原始存储采样点，并非所有积分步；`*_SIGNALS.json`按spec记录实体、单位、时间与值。SOURCE_DATA/TASK_TIME_SERIES是可用的原始逐步数组，T09包括按钮实际环境关节，不能仅用机器人qpos重放一个不动的按钮。PHS完整CSV较大，保留原始绝对路径和执行manifest，不复制数GB文件。MOTION_INDEX及ANIMATION_INPUTS仅为已有轨迹的抽样视图，不包含新物理解。

动画只将已有qpos写入对应真实关节并做正向位置更新；不积分、不插值优化、不重算任务指标。目标/路径/力箭头来自原task、原参考或实际记录，为视觉提示，不添加物理载荷。慢放或抽样需看动画manifest和屏幕时间；不能按GIF播放时长估算物理速度。

## 资源口径

RESOURCE_COSTS按run_id分列。五项完成任务的Full系列包含其失败/准备studies；另五项使用归档最终研究，避免叠加旧批次重复研究。PHS主搜索+名义、半步长和诊断分支分别记录。

`math_evaluations`是数学评价计费；`math_internal_optimizer_calls`为已保存local_solver调用记录数，旧`math_internal_optimizations`来自对应原成本报告的内部优化调用；两者不能再次相加。`math_objective_evaluations`是内部目标/rollout评价数，不是优化调用数；`math_optimizer_iterations`与`local_optimizer_iterations`分别保留原层级，不能混用。平衡组明确89次构造优化保存在explicit_reference_bank_optimizer_calls及原NATIVE_REFERENCE_BANK文件；失败构造不具备完整内部调用总数，不能用收费数推算实际求解数。

`physical_episodes`为原记录的独立物理/注册控制器启动回合，含失败启动；不等于数学内部rollout数。`physical_steps`和`math_internal_physics_steps`不同；integration_steps在可覆盖时为两者的已记录总和。若某失败Profile没有步数，总计unavailable；部分已知总和不能当作完整总数。

`candidate_count`为同run唯一物理robot.structure；artifact数量另列，控制/协议变体不等于新结构。跨run简单相加会重复同硬件。tool_calls有Core ledger units与top-level public operations两种basis，不直接跨口径合计。cpu_time_s可能仅为监控到的worker寿命，coverage列必须保留。wall_time_s有elapsed和PHS charged wall两种口径；charged_numerical_wall_s是嵌套数值时间，不能与elapsed相加。未闭合study历时unavailable。

## 后续绘图建议

先按task_id、candidate/controller身份、condition_role、protocol版本和评价范围分组，再选指标。原值、单位、上下界、原证据列一起导出。任何归一化裕量写明公式及方向。跨任务只比较可解释的资源或能力覆盖，不平均不同单位的任务误差。暂存统计图只供草稿核对，后续论文图应重新设计。
