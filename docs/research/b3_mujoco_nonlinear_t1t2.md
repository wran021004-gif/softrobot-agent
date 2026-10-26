# B3 MuJoCo 非线性 T1/T2：有限预算能力与科研决策检验

2026-10-26，Asia/Shanghai。结论为 **C：可信结构修改的证据不足**。
非线性工具在本次固定控制和有限搜索条件下有辨别力，但本轮没有证明它比维持基准结构更能提高找到可行解的效率。

三个结构的 MuJoCo 最佳已找到 J 依次为 2.0857141424384675、1.7468672625906523、1.4174875824815398。
增大远段 Young 模量的左右响应割线同为负，独立完整回放复现了这些数值。
然而三次搜索均达到 3 次更新上限，三个结果仍不满足任务；不能把这个观察升级为可信最优结构方向。
冻结规则因此让 GVS、MuJoCo 和不改结构三种策略均保留 d0。真实决策增益为 0，实际节省的候选物理评价为 0。

原始数值和来源见 [证据索引](../../evidence/b3_mujoco_nonlinear_t1t2/evidence_index.json)、
[独立确认](../../evidence/b3_mujoco_nonlinear_t1t2/verification.json)。
另有独立的 [Agent 可消费决策摘要](../../evidence/b3_mujoco_nonlinear_t1t2/agent_decision_summary.json)，未注入任何 Agent Study。

## 1. 边界、工作树与冻结实验

使用独立工作树 `.worktrees/b3-mujoco-nonlinear-t1t2`、分支 `research/b3-mujoco-nonlinear-t1t2`，
精确基线 `78ca687fd893bfc805cfcaf1370ea62dd14dbf65`。
已读取基线 `AGENTS.md`。主工作树原有环境和 runs 未跟踪文件未处理；R1 工作树的原有修改未处理。
只读核对时，R1 为 ready、pending=null、selected=null、数学计费 0，绑定实现
`69a82930f0f5f58017d6f621d4a04d57b82d2081`；这只是核对时状态，不是本轮对 R1 的冻结或续研。
未写入 R1、M2、G2、S130–S145 的配置、Store 或封存证据。

本轮为 `engineering_numerical`，复用原 prepare/bind、候选验证、分析 Worker、完整回放、独立 evaluator 和 Store。
没有启动 Agent、Provider、正式自主 Study、NMPC、PPO 或 MATLAB。
唯一新 Store 为忽略目录 `runs/b3-mujoco-nonlinear-t1t2/store`，是原 Store 实现的本轮实例，没有第二套科研 Store 或账本。

[实验计划](../../evidence/b3_mujoco_nonlinear_t1t2/frozen_plan.json) 在所有科学计算前保存并提交。
任务为 `tasks/reach_hold_b3_050.json`：目标 `[0.29,-0.035,0.19] m`，独立生成候选各自的冻结零初态，
时长 0.50 s，保持窗 `[0.45,0.50] s`，终点/保持位置限 0.010 m、保持速度限 0.020 m/s，
四路张力各 `[0,8] N`，控制/采样间隔 0.01 s，积分步长 0.0005 s，最终保真度每段 12 cells。
两段四腱结构只改变 `segments.1.young_pa`：d−=4.86 MPa、d0=5.40 MPa、d+=5.94 MPa。
候选全部由原 `generate_candidate` 和 FamilySpace 生成，没有修改保存的 XML。

共同 U0 为 M2 C 完整控制源
`30994c15d28a3b1b434d1f4cdc252199773e3eb4c9888a4b47b3870ac8d004ea`，
原独立回放为 `0f87cf01869d1892043a8c52f3893c9b0b433ff305f769d2fbb3ad28a991baca`。
通过原 `archived` 验证封存来源，在原候选下检查 binding，再用原 `initialize_schedule` 为每个新候选合法重绑定。
逐值核对 task、tendon_order、50 个真实张力区间、51 个时间边界、输入界及各自初态。
所有新控制的 task_acceptance 都从 unmeasured 开始，没有继承 M2 验收。
这不是旧六腱 0.35 s 实验。

搜索配置在运行前固定：原 response 搜索、knots=`[0,.38,.45,.5] s`、活动系数 `[9,10,13,14]`，
系数界 2 N、FD 步长 .01 N、初始半径 .1 N、最小半径 .0001 N、安全余量 0，
每结构至多 24 callbacks、3 次更新。活动子空间来自 M2 C 已保存经验，未根据本轮结果调整。
它限定本次控制空间，不代表所有可能控制器。

## 2. 实现与数学语义

MuJoCo-T1 方法为 `mujoco-nonlinear-task-capability-v1`，请求 operation 为
`mujoco_nonlinear_task_capability_v1`。它沿用 `control_optimization={source,settings}`、原协议和冻结初态，
由 `native_analysis` 调用原 `native_control.calculate`，继续使用 `NativeModel.rollout_sequence`、
`LocalControlSearchSettings`、原 `local_control_search.search`、控制修正及 `task_measure`。
没有开发新优化器、评分、样条、裁剪、积分循环或后端。

其输出是 `Vhat_MJ(d; algorithm, initialization, budget)`，含最佳合法序列及来源、初始和最佳硬指标、改善量、
真实 callbacks/rollouts/physics_steps、停止原因、完成更新数、瓶颈时间、边界状态和适用限制。
最佳控制由原 recover 保存为 `control_schedule_reference`。
原 `mujoco_direct_control_v1` 保留原义，新增能力主要是版本化任务解释和结果组织。

全程用原有有符号量：

`J = max(e_terminal/0.010, e_holding/0.010, v_holding/0.020) - 1`。

normalized_gap 继续保存，但没有用它给已达约束的候选排名；测试明确覆盖两个负 J 均被截为零的情形。
T1 不授予正式独立任务验收信用，也不声称全局最优、非线性 KKT 或包络梯度。

MuJoCo-T2 方法为 `mujoco-reoptimized-structure-response-v1`，operation 为
`mujoco_reoptimized_structure_response_v1`。唯一新增请求载荷为：

`nonlinear_response={variable,unit,t1_results:[baseline,minus,plus]}`。

它只接受当前 Store 已完成、候选绑定、同实现/协议的三个 T1，复用原候选和 FamilySpace 参数检查，
要求同任务/场景、控制通道和约束、时间网格、共同合法初始控制及相同搜索设置，且只有指定参数变化。
缺少真实控制搜索、数值无效、非对称 stencil 或身份不匹配时返回 not_comparable。
已有控制搜索但更新不足、方向矛盾、实际机会不等或停止于上限时返回 unresolved。
T2 不生成候选、不构建模型、不运行三套 T1，只计本次聚合的一次原分析费用。

新适配模块 `nonlinear_capability.py` 同时保留固定控制与各自重优化后的左、右、中央割线。
practical_J_tolerance 是显式的实用辨别阈值，**不是**误差界；本次差异超过它，但优化误差仍没有界。
目录仅在新方法被本 Study 显式授权时增加两个版本化项目，并标记为有限预算诊断。
旧 R1 不获得新方法授权；未修改 Agent system prompt 或每轮 L0 代码。
结果通过原 candidate-bound L1、compact/decision 视图和 Store 按需读取。

原 GVS-CONIC 与 `controlled-capability-sensitivity-v1` 内核未修改，原 CONIC 的数值最优性、对偶检查、
条件包络和适用范围保留。没有把原对偶乘子带入 MuJoCo 搜索，也没有重载原 capability_method 字段。

## 3. A：GVS 预测与共同平台

使用冻结原 `controller_start_input` 工作点，在各结构自身重建 B3 局部模型；没有改变工作点追求结构方向。
三个 T1 与单尺度 h=540,000 Pa 的 T2 先完成并保存，再开始 MuJoCo。
完整简表见 [GVS 原数值摘要](../../evidence/b3_mujoco_nonlinear_t1t2/gvs_prediction.json)。

| 候选 | 重优化模型 signed J | 浮点 support 下估计 | 数值 gap | CONIC 状态 |
|---|---:|---:|---:|---|
| d− | -0.19999999999984042 | -0.2000000000597092 | 5.98688e-11 | optimal |
| d0 | -0.1999999999901171 | -0.2000000000509465 | 6.08294e-11 | optimal |
| d+ | -0.19999999999997867 | -0.20000000003115692 | 3.11783e-11 | optimal |

主导为终点与保持位置约束。三份保存模型的 x 输出 C/D 行均为零，y0_x≈0.298 m。
因此在这些仿射模型内，目标 x=0.29 m 留下固定约 0.008 m 的轴向残差，可解释共同约 -0.2 的模型内几何平台。
这是对保存局部模型的解释，不是 MuJoCo/硬件下界，也没有改变原核仅标为浮点数值检查的证据强度。
原求解器的通用严格解析下界仍为 -1，最优值和 rigorous upper bound 仍标 unavailable。

GVS-T2 重优化割线，按 J/MPa：左 `1.8006121285e-11`，右 `-1.8262140771e-11`，
中央 `-1.2800974272e-13`，实质为平台；preferred_parameter_direction=unresolved，
direction_status=`directional_comparisons_only`。
条件 envelope≈`3.2673710150e-13 J/MPa`；两个 dual-face 极值求解均 optimal_inaccurate，面范围 unresolved，
LICQ/可微性没有证明、finite_difference_checks_passed=false，未强行转为梯度。

固定 **GVS 基准最优控制** 时，d−/d0/d+ 的模型 J 为
`0.2874257119639364 / -0.1999999999901171 / 0.6162296400347157`。
该固定控制的左/右割线方向相反；重优化后重新落到共同平台。
这里的固定控制不是 M2 U0，不能与下一节不同输入的 MuJoCo 结果直接计算跨模型误差或声称方向预测错误。
本轮也没有回放 GVS 最优控制，不能用不同控制的 MuJoCo 失败反证 GVS 自身控制的物理结果。

## 4. B、C：固定 U0 与 MuJoCo 控制重优化

| 控制条件 | 候选 | terminal error / m | holding error / m | holding speed / m/s | signed J |
|---|---|---:|---:|---:|---:|
| 固定 U0 | d− | .007625441972488307 | .010880792884357223 | .11109869171375548 | 4.554934585687774 |
| 固定 U0 | d0 | .004515550349894086 | .006675937086453473 | .08788779126447174 | 3.394389563223587 |
| 固定 U0 | d+ | .0031176446578404906 | .00406130880362835 | .06934348057937524 | 2.467174028968762 |
| 各自重优化 | d− | .012294834022459667 | .012741179465874584 | .06171428284876935 | 2.0857141424384675 |
| 各自重优化 | d0 | .0074401918597937515 | .008068170854003237 | .05493734525181305 | 1.7468672625906523 |
| 各自重优化 | d+ | .0038424944304132533 | .004842188681213695 | .0483497516496308 | 1.4174875824815398 |

固定 U0 的位置峰均在 .45 s，速度峰均在 .48 s；固定控制结果只是结构非线性响应，不替代 T2。
重优化后速度峰 d−/d0 在 .50 s、d+ 在 .48 s，位置峰仍在 .45 s。
每个结构都有自己从零执行的结果，d0 固定回放与 M2 C 保存数值一致，但这是新执行和新费用。

| 候选 | J 改善 | callbacks / 完整 native rollouts | FD probes | 完成 response 更新 | 停止原因 |
|---|---:|---:|---:|---:|---|
| d− | 2.4692204432493066 | 16 / 16 | 12 | 3 | iteration_limit |
| d0 | 1.647522300632935 | 16 / 16 | 12 | 3 | iteration_limit |
| d+ | 1.0496864464872222 | 16 / 16 | 12 | 3 | iteration_limit |

每次为 1 baseline + 3×(4 FD + 1 proposal)，所以没有为用满 24 callbacks 额外运行。
所有最优点均为实际执行过的 local_response_proposal，九个局部 SLSQP 子问题均成功；
各结构的三个控制响应矩阵均为 resolved_local_response。子问题成功不等于非线性控制搜索收敛。
所有输入合法，真实张力全局范围 0–7.9999451984617505 N，存在下界饱和并接近 8 N 上界。
最佳修正没有达到 2 N 系数界，但有限子空间、局部半径和输入投影仍可能限制搜索质量，不能推断物理制动力极限。

## 5. D：MuJoCo-T2 与方向判断

T2 只消费三份上述 T1；来源、task/model/input/grid、单参数变化、预算与初始化检查通过。
三者都为 16 callbacks、3 个完成更新，没有提前达标引起的实际计算机会不等。

| 控制处理 | 左割线 J/MPa | 右割线 J/MPa | 中央割线 J/MPa |
|---|---:|---:|---:|
| 共同固定 U0 | -2.1491574490077535 | -1.717065804175602 | -1.9331116265916777 |
| 各自控制重优化 | -.6274942219403987 | -.6099623705724304 | -.6187282962564145 |

观察为单调，无左右矛盾；重优化明显压缩了结构间差异。
本次 practical J tolerance≈0.0002085714，相邻 J 差约 .339 和 .329，足以区分保存的浮点结果。
这不约束积分截断误差、模型误差或控制优化误差。
由于三次都达到更新上限、仍未过关、且没有独立初始化/收敛误差证据，direction_status=`unresolved`，
原因为 `CONTROL_SEARCH_QUALITY_UNRESOLVED_AT_LIMIT_OR_FAILURE`。中央负割线没有直接触发增大模量建议。
该保守门槛已随实现预先提交；它不把有限预算的数值比较判为无效，而是拒绝把它直接推广为可信结构修改方向。
在 3 次更新的设置下，这个门槛使自动修改很难成立，因此本轮 C 也不能证明更宽松但明确限定为有限预算的决策规则无用。

GVS 与 MuJoCo 在“当前不足以支持可信修改”上相同；其原因不同：前者是平台和对偶/局部模型限制，
后者有条件性的数值趋势，但控制求解质量未决。不能写成两种方法已经验证同一结构梯度。

## 6. 预定决策、E 阶段揭示与决策价值

规则在第一份科学结果前已写入冻结计划：方向明确、可比且质量足够才选择对应端点；否则维持 d0 或追加诊断；
不使用新加权分数。GVS 还要求没有未决的非线性任务失配风险。

[真实决策记录](../../evidence/b3_mujoco_nonlinear_t1t2/decision.json) 保存时，已有最佳控制独立回放数为 0。
原 Store 阶段事件顺序为：计划 #14 → GVS #32 → 固定 U0 #60 → T1 #76 → 决策 #81 → 独立确认 #109 → 停止 #110。
对应本地时间为 14:17:17、14:19:02、14:19:42、14:20:02、14:20:11、14:20:31。
不依据最后回放改变 GVS 预测、控制配置或建议。

| 策略 | 揭示前选择 | 保存的理由 | 揭示后 J | 相对 d0 改善 |
|---|---|---|---:|---:|
| 仅 GVS-T1/T2 | d0，保留并诊断 | 单尺度局部模型没有已验证的非线性任务误差界；原方向未解决 | 1.7468672625906523 | 0 |
| MuJoCo-T1/T2 | d0，保留并诊断 | 三次控制搜索均达到更新上限 | 1.7468672625906523 | 0 |
| 不改结构 | d0 | 固定参考规则 | 1.7468672625906523 | 0 |

随后三个最佳序列都经原完整 MuJoCo 回放和独立 evaluator 确认：51 个样本、6 个保持窗样本、每次 1,000 步，
完整性、数值有效性、张力、solver_errors 均通过；三个 composite acceptance 均为 **valid_failure**。
d− 三项硬指标均失败；d0/d+ 位置通过、速度失败。不能把仅终点 evaluator 的通过当作完整 Reach/Hold 成功。
与 T1 轨迹的最大位置/速度差均为 0，时间表示差为 3.885780586188048e-16 s。

d+ 确实是本次三个已找到控制结果中 J 最低者，比 d0 低 .3293796801091125；
它不是预先规则正式推荐的结构，不能事后改写为“数学推荐正确”。
三种策略都没有错误推荐新的结构，但都没有获得优于 d0 的已实现收益。
合理 abstention 避免了无依据的结构必然改善断言，也可能错过本次 d+ 的有限收益；本实验无法量化这项权衡。
全部三个候选仍按验证协议评价，没有实际节省物理候选，也没有对照 Study 证明找到可行解更快。

因此，新增工具有 **诊断辨别价值**：它揭示 GVS 平台没有呈现的非线性差异，
区分固定控制变化与控制重新优化后的变化，并量化控制优化本身的改善。
但对于本轮核心“自动选择更值得投入的结构并提高可行解搜索效率”，结论仍是 C，不能宣称 A。

## 7. 费用、数值时间与停止状态

| 项目 | 实际用量 |
|---|---:|
| Agent / Provider / NMPC / PPO / MATLAB | 全部 0 |
| 候选结构 | 3 |
| GVS 模型构建，已返回边界 | 3 |
| GVS 能力 CONIC | 6（T1 3 + T2 重优化 3） |
| GVS dual-face 求解 | 2，两次 optimal_inaccurate 保留 |
| GVS 数学计费 | 11 / 22 |
| 新 native T1 分析 / T2 聚合计费 | 3 / 1 |
| 全部原数学计费 | 15 / 22 |
| native 模型构建 | 3 |
| native callbacks / rollouts / FD probes | 48 / 48 / 36 |
| native 完成更新 / 局部 SLSQP | 9 / 9 |
| native forward_evaluations | 4,851 |
| native 内部积分 | 48,000 步 |
| 固定 U0 完整回放 | 3，3,000 步 |
| 最佳控制独立完整回放 | 3，3,000 步 |
| 总 MuJoCo 积分 | **54,000 / 90,000 步** |
| T2 聚合新增模型 / 搜索 / 积分 | 0 / 0 / 0 |

六次完整回放各走原 backend 的一次模型编译；它们由完整执行收据记录，没有另设模型构建账本或额外收取数学构建费。
候选准备不执行轨迹。实际步数来自原 native.cost 和完整回放 raw.physics_steps，没有用预算估算代替实际费用。

原 Worker 收据的数值时间（含进程启动、导入和工作）：GVS 28.1499661 s，native T1 6.3809670 s，
T2 聚合 .9079203 s，固定回放 3.4875542 s，独立最佳回放 3.7170005 s；合计 42.6434081 s。
原 state.numerical_s 为 43.6113645 s，包含原准备/候选等额外数值工作，未把两者重计。
三个 native kernel_wall_s 合计 3.5062579 s；T2 聚合 kernel_wall_s=.0000272 s，
不能把 .9079203 s 的真实 Worker 开销说成零。未统计的单独构建时间不另行猜测。
实验阶段之间的人工查看和交付整理时间不冒充数值求解时间。

原共享账本 used 为 model_calls=0、backend_solves=6、tool_calls=14、wall_s=42.6434081，occupied={}。
原工程 closeout 已设置 research_status=stopped、pending=null；没有 SELECT、重启或追加实验。
剩余预算不是继续搜索授权。

## 8. 测试、源码与交付

五个独立定向用例通过（首次 0.402 s）：四个新增离线测试覆盖原 signed J/成本、
上限与反向/机会不等/无搜索、单参数/任务/搜索绑定、显式授权和原 GVS Schema；
另复用原保存 callback 的 native 搜索回归，不新增积分。
实验后收紧了“已有探测但未完成更新返回 unresolved”、所有 not_comparable 成本记录、
授权 capability 和 T2 目录信息，四项受影响用例再通过（.086 s）。
这些离线整理不改变本次三结构的数值或决策；原科学结果保持绑定
`cb25654e2fe3095c4ceafbe10fecea129d3745dc`，没有为交付版本重跑实验或重写 Store 结果。
原 L1 方法目录读检通过，停止后的两个方法都正确显示 blocked。
没有全仓测试、额外真实仿真或与本任务无关的修复。

生产修改集中于 contracts/config 的最小版本化字段和授权、analysis 的原 Worker/Store 路由、
native_analysis/native_control 的薄适配、capability/task_constraints 的摘要和目录，以及新增
`tools/research/nonlinear_capability.py`。
独立实验入口为 `tools/research/experiments/b3_mujoco_nonlinear_t1t2.py`，
显式阶段为 prepare → gvs → fixed → t1 → decision → verify，已完成阶段不自动重算，
重复操作仍使用原收据身份；运行前保存预算，逐次按原 Store 费用检查 90,000 步边界。
没有修改 local_control_search、control_correction、MuJoCo 后端、GVS-T1/T2 内核或任务评价阈值。

Git 只保留源码、小配置、定向测试、本报告、阶段关键数值和证据索引。
完整轨迹、回调、矩阵和 Worker 原始收据保留于忽略的 runs/Store，没有重复 tar 或新 SHA manifest。
初始接口和实验冻结提交为 `cb25654e2`；最终数值、报告和离线边界收紧另行提交。
交付分支为 `research/b3-mujoco-nonlinear-t1t2`，推送目的地为用户指定的
`wran021004-gif/softrobot-agent`；最终提交、普通 push 回执和清洁状态在交付时复核。
未强推、合并 main 或清理其他工作树。

## 9. 可开放的信息与不可越过的限制

可供未来 Agent 按需读取：本任务/结构/控制条件、最佳已找到 J 与原硬指标、费用、
固定与重优化响应的区别、GVS 平台、搜索上限、同模型轨迹复现及 unresolved 原因。
新 Study 仍需显式授权昂贵方法；现有 R1 不开放，也不自动注入摘要。

必须保持 unresolved：完整非线性最优值/梯度、与控制器或初始化无关的结构排名、
非线性搜索收敛、硬件转移、鲁棒性、统计泛化和自主科研效率改善。
同一个 MuJoCo 动力学用于优化与独立执行，回放一致性主要验证执行复现，不能称为跨模型独立预测精度或真实世界验证。
只运行三结构各一次，未做独立控制初始化或不同控制器对照；不可推广到其他控制策略。

最值得下一次**另行授权**的实验是：对 d0 与 d+ 使用独立的合法控制初始化，保持同预算/同子空间进行搜索和完整确认，
检验观察到的 d+ 优势是否依赖共同 U0。它仍不能单独证明全局结构最优。
本轮没有执行该实验，也没有为了消除限制扩大搜索、结构数量或启动下一次 Study。
