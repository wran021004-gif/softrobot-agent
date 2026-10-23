# S136：任务条件到数学问题的逐项映射

本矩阵对应 S132 基线及 S136 的语义保留修复；所有数值是冻结 Reach 规则或明确标为
draft 的 Tracking 开发样例，不是新增科研结果。`T=duration_s`，`W=settling.window_s`，
`r=max_error_m`，`p` 为世界末端位置，`v` 为世界平移速度。

数学模型 M：候选身份绑定、指定工作点的连续局部仿射模型，按控制周期零阶保持离散，
使用声明的 position/velocity 输出、张力顺序与上下界；不能推广到全局非线性动力学。
Tracking 的 M 当前需要外部已保存且任务身份匹配的模型，生产 robot model builder 不支持；
合成测试模型不是机器人证据。

## A. Reach + Hold

| 条件/角色与来源 | 物理观测 | 数学表达/采样 | 模型与支持状态 | 可以证明什么/遗漏什么 |
| --- | --- | --- | --- | --- |
| 终点位置，硬条件：task evaluator tolerance_m=.01 m | p(T)，world/m，task 声明 phase | `terminal_error_m`: norm(p-target)≤.01，index 35 | M；endpoint 支持，trajectory/conic 可采样支持 | 仅局部模型的终点；独立 evaluate.reach 仍需完整保存采样与执行 |
| 保持位置，硬条件：frozen settling.position_limit_m=.01 m | [T-W,T] 的 p，world/m | `holding_max_error_m`: 每点 norm(p-target)≤.01；30…35 | M；endpoint 不覆盖，trajectory/conic 支持适用未来样本 | 含端点六样本；不能推导连续时间保持，saved-state 以前样本需另证据 |
| 保持速度，硬条件：frozen settling.speed_limit_m_s=.02 m/s | [T-W,T] 的 v，world/m/s；真实 profile 观测 | `holding_max_speed_m_s`: norm(v)≤.02；30…35 | M velocity 输出；braking 只覆盖终点，trajectory/conic 可覆盖窗口 | 绝对 tip 速度条件；不能由位置误差或曲率速度直接代替 |
| 保持覆盖，证据有效性：frozen window_s=.05、task timing | 原始时间戳及完整六样本 | 数学 requirements 有 grid，但不验证真实记录 | 独立 protocol/profile；数学不覆盖真实执行覆盖 | 缺失样本是缺证据，不是有效失败或成功 |
| 力界限，协议硬条件：候选 tendons.force_limit_n 与 protocol | 实际按腱顺序保存张力，N | mathematical physical_inputs [0,force_limit]，pre-step ZOH | M 与模型绑定一致时覆盖预测输入 | 可证序列在模型输入箱内，不能代替真实执行的力界限核验 |
| 完整执行、有效 evaluator、solver_errors，协议条件 | execution/source/receipt、solver 状态、评价结果 | 无相应动力学不等式 | 独立 assemble_acceptance；数学不覆盖 | 不能把数学 witness 当作执行成功 |
| position_error 最小化，偏好：task.objectives | 同终点误差 | T1 可用归一化超限，但不是 objective 权重转换 | 优化偏好与 pass 分开 | 改权重/方向不改变 tolerance |
| runtime/deadline_misses，诊断 | 更新墙钟时长 | 非任务约束 | 当前 offline protocol 不要求实时 | 仿真通过不等于实时部署通过 |

Reach 数学约束 provenance 指向 evaluator tolerance 或 controller settling，并包含 task
timing/goal/window；不是从 `objectives.weight` 导出。完整验收还由冻结 protocol 组合，
因此即使全部三类数学约束均覆盖，也不代表完整物理任务被数学证明。

## B. Untimed Geometric Tracking

当前 `r=.004 m`、`geometry_step_m=.001 m`；这些是 provisional 开发值。
真实 evaluator 忽略采集 duration 对成功的期限含义，但要求有效、严格递增的记录时间和至少两点。

| 条件/角色与来源 | 物理观测 | 数学表达/范围 | 模型与支持状态 | 可以证明什么/遗漏什么 |
| --- | --- | --- | --- | --- |
| 路径偏差，硬条件 tracking_max_error≤r | 保存折线的顶点及均匀弧长重采样点到参考折线的最近距离 | `path_bound` 用 norm(p_k-r(s_k))≤r 作为代理；整个数值 grid 0…N | M + free progress SOCP，参考限一/两段；独立 metric 留为 unsupported | 代理采样点接近指定进度；不等于对真实保存折线的同一评价 |
| 覆盖，硬条件 path_coverage≤r | 参考弧长采样点+参考顶点到测量折线距离 | 代理固定 s_0=0、s_N=1，单调且访问折点；不直接计算 coverage metric | M；本轮 retained unsupported row | 不能仅有低路径偏差就宣称走完整条路径；stationary/shortcut 仍由 evaluator 拒绝 |
| 起点，硬条件 path_start≤r | 第一条测量位置与首参考顶点 | proxy s_0=0，但数学 t=0，evaluator 首条 post-step 记录 | M；retained unsupported row | 初始状态约束不是第一条真实测量的自动证明 |
| 终点，硬条件 path_end≤r | 最后一条测量位置与末参考顶点 | proxy s_N=1；选择的有限数值时域终点 | M；retained unsupported row | 是有限见证的端点，不是无时间任务 deadline；真实记录需另评 |
| 顺序/回退，硬条件 path_progress_regression≤r | 原始顶点最近段投影的弧长进度；累计最大值减当前值 | proxy s_(k+1)≥s_k，使用优化辅助变量而非最近点投影 | M；retained unsupported row | 辅助进度单调与 evaluator 容许 r 回退不等价，不能直接替代 |
| RMS 最小化，偏好/诊断 | 测量折线均匀弧长重采样误差 | 未作为硬条件编入 math；T1 是最大超限不是 RMS | 无硬阈值 | RMS=0 仍可能是未完成路径；测试验证 stationary path 失败 |
| 记录完整性/信号合法性，证据条件 | solver completed、唯一 tip、world/m/post_step、递增时间 | grid 是数值需求，不是真实 recording 验证 | evaluator 独立执行；数学不覆盖 | 不从模型假设推导真实信号有效 |
| 输入界限，模型/候选条件 | 候选张力界限/实际控制 | physical_inputs [0,limit]，N、tendon order | M 可覆盖预测输入 | Tracking evaluator 本身不检查力；完整物理协议尚不支持，不能添加臆造的验收 |

本轮 analysis requirements 保留一个可求解的 `geometric_path` 和五个同名独立评价条件
的 unsupported payload。附带 goal/evaluator、阈值、单位、语义和来源。unsupported 行的
indices 只标数值 grid 占位范围，不是“把整个折线条件等价拆成每点约束”。

两段路径 SOCP 对可能的内部折点访问样本枚举多个凸子问题，未退化成凸包或终点 Reach。
它不覆盖任意曲线、任意段数、重叠返回路径、全部物理非线性运动或无限完成时间。

## C. Timed Tracking

| 条件/角色与来源 | 物理观测 | 数学表达/采样 | 模型与支持状态 | 可以证明什么/遗漏什么 |
| --- | --- | --- | --- | --- |
| tracking_max_error≤r，硬条件：evaluator + goal.times_s | 对每个 scored t 的 p(t)，world/m/post_step | `timed_tracking`: norm(p_k-r(t_k))≤r；sampling.window 内含端点；示例 1…20 | M、norm_bound，trajectory/conic 内核支持；robot/controller 仍 unsupported | 局部模型评分样本对齐；不保证真实系统/连续时间 |
| 参考时间，定义条件：times_s 从0严格递增，末时刻=T | 同一时间原点和任务时钟 | 分段线性插值，节点处速度用右段（末点用最后段） | TrackingGoal.at_time，adapter 复用 | 位置参考准确；没有自动添加速度跟踪硬条件 |
| 完整时间网格，证据条件 | .02… .4 每个 post-step 时间戳 | requirements 数值 grid 包含0，但 scored indices从1 | evaluator 校验实际数据；数学仅描述 | 缺样本 incomplete，错时间 invalid；不能用无时间几何相同替代 |
| RMS，偏好/诊断 | scored samples 的算术 RMS | 非硬阈值；不编成 norm_bound | 可用 evaluator metric | 不要求额外 RMS pass |
| terminal_position_error，诊断/可选偏好 | 完整记录末点与末参考位置 | 仅当评分窗含末点时，它也受最大误差硬条件约束 | evaluator 总是报告；math 按实际评分窗选择 | 评分窗若提前结束，不可偷偷增加末点硬阈值 |
| path_coverage_error | Timed evaluator 不输出此指标 | 不存在 | 本轮拒绝选择此 objective | 不能因同属 Tracking 就假设两个模式指标全集相同 |
| 输入与完整物理协议 | 候选输入、执行/force/solver 证据 | 数学输入箱同 Reach | 模型支持与物理验收分开 | 不支持 Tracking 的 composite acceptance，不能借注册 evaluator 绕过 |

## 四种“目标”的追溯关系

| 层 | 内容和身份 | 与其他层关系 |
| --- | --- | --- |
| 正式成功条件 | task/evaluator/协议与硬条件来源 | 唯一 pass/fail 依据；保持冻结 |
| T1/T2 task violation | requirement identity、模型/工作点/时域、归一化和 coverage | 对可表达条件的代理或模型内表达；遗漏条件必须保留 |
| NMPC objective/constraints | 控制 recipe、输出参考、权重、尺度、窗口、求解器/模型 | 可用于改善任务的控制设计；当前 Reach 特化，cost 不是 pass |
| RL Reward | reward/training/action/observation/reference identity | 训练偏好，可有平滑/失败惩罚；return 不是任务验收 |

未注册任务、未声明信号/物理、无法构造模型和无法执行的控制器必须保持明确拒绝。
后续具体接口与合并风险见 [主审计报告](s136_task_contract_audit.md)。
