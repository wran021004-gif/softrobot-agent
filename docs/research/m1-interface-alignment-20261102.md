# M1 接口审计与执行报告

原 Study：`m1-low-tendon-speed004-20261102-campaign3`。分支：`codex/m1-knowledge-physics-reasoning`。

本报告把原正式科学证据、隔离工程验证、待继续的正式研究分开记录。原 Store 的 92 个 Provider 请求均有回执，其中 conversation 完成 86、失败 2，Reporter 完成 4；失败请求没有退款或重做。没有 pending、未封口 reservation 或占用资源。实际 SDK 暴露过的工具为 research_plan、research_analysis、research_route、evidence_read、research_investigate、experience_retrieve、research_recall，未暴露 research_rl。

## 端到端矩阵

“真实验证”指已有正式 Worker 或本次隔离真实 Worker；后者不计入 M1 科学进展。Schema/Mock 通过单独注明。

| 工具/方法 | 对 Main 的展示 | Schema | 编译 | 准入 | Worker | 反馈 | 结论 |
|---|---|---|---|---|---|---|---|
| research_route | 按目录加载单一工具/动作 | 原 SDK 实际记录 | 只选择，不运行实验 | 当前动作、冻结权限 | 无科研 Worker | 下次请求加载 Schema | 原 Study 17 次路由，真实验证 |
| plan generate | 冻结 FamilySpace 的实际结构参数 | 动态生成契约 | 短引用还原、原 Plan | 原结构/物理域 | 原构造器 | 候选、失败原因和 provenance | 原 Store 6 个候选，真实验证；非法设计拒绝保留 |
| plan diagnose | 候选、假设、下一研究动作 | 真实 SDK 投影 | 冻结候选与科学意图绑定 | 所有权、证据推断范围 | 无数学求解 | 动态 analysis 入口 | 原 Store 15 次，真实验证 |
| initialize_control | baseline / 来源转换 / capability_sequence | 原动态 Schema | 候选与源严格绑定 | 通道、完整 SI 网格、张力边界 | 不继承任务成功 | 返回控制源，不冒充候选或状态 | 17 条正式控制源；Conic 转换本次真实验证 |
| Native Direct | 有限预算完整任务控制搜索 | 实际选定 Schema | 原 control_optimization | exact source、模型、时域、资源 | 本次 2 callbacks / 1200 physics steps | computed；任务仍 unmeasured | 已真实验证 |
| Native T1 | 有限搜索最好观察值，不是严格最优值 | 同上，保留独立方法身份 | 原 nonlinear task capability | 原冻结初态及完整任务 | 本次 Conic seed 后 2 callbacks / 1200 steps | 原非线性摘要及账目 | 已真实验证 |
| structure inspect | 机制目标对象、明确工作点 | 类型、目标适用性、来源互斥 | 原 mechanism_study | 原模型/来源/预算 | 本次真实恢复完整状态并计算 | 诊断，不继承任务通过 | 已真实验证 |
| structure differentiate / optimize / compare | 已注册连续参数、目标、方向、范围 | 当前 Schema→编译与拒绝路径回归 | 原机制内核 | 保留两尺度、预算、可表达性等约束 | 本次未逐项真实求解 | 缺前提、诊断强度明确 | 编译/集成验证；未声称各操作均已真实运行 |
| T2 已保存结构响应 | 保存且匹配的 T1 baseline/minus/plus | 任务目标字符串 | 原 T2 聚合，不生成扰动或优化控制 | 匹配工况、初态、源、设置、预算及结果版本 | 当前 Study 无合格 stencil | 指出所缺 stencil、所选证据类型及准备入口 | 需要明确前提；原非法梯度拒绝保留 |
| Conic/SOCP | structure inspect + reoptimized_task_capability + optimal_task_violation | 明确完整 V4 入口 | 原 task_capability / GVS / Conic | 原依赖、模型、任务、参数和权限 | CVXPY/CLARABEL 真实求解 | 数值验证与 Native/物理验收区分 | 本次真实验证，随后成功导入完整控制序列并由 Native 评价 |
| qualified sensitivity | 合格已保存模型 stencil | 原能力目录与结构 M2 | 原 optimal_sensitivity | 基线/扰动模型、正则性、数值检查 | 本次未补造模型或执行 | 仍按缺失证据拒绝/准备 | 需要明确前提；未声称严格梯度 |
| plan search | 结构组、起点、控制努力与冻结域 | 原 scientific_structure_search | 原 mixed search | 不能丢弃截面旋转等参数 | 本次无大规模搜索 | 不可无损种子给出具体 generate 路径 | h31 有意拒绝保留，反馈已修复；完整搜索未新增实测 |
| plan control_search | 独立回放驱动的控制搜索 | 原 Plan/local search 契约 | 原有限搜索 | 必须有合法源和真实回放预算 | 本次未新增回放搜索 | 独立后端费用与 Native callbacks 分开 | 代码/契约审计；本次尚未真实执行 |
| plan execute | NMPC 真实执行 | 原 Plan/候选绑定 | 原执行接口 | nmpc、前提及后端资源 | 本次未启动长 NMPC | 保留失败/不完整来源规则 | 尚未真实验证，本次不替 Main 选择 |
| physical_replay / SELECT | 同结构三工况独立验收 | 原结果短引用与严格证书 | 原 Replay / joint_assessment | 必须三工况完整通过、公开证据读取与真实收据 | 本次工程阶段未新增正式 Replay | 数学预测不等于物理验收 | 需要正式有希望的控制；严格门槛保留 |
| STOP | 科学解释、证据与资源收尾 | 原冻结关闭规则 | 原 STOP 记录 | 完整结果索引、真实账目 | 无实验 | 已封存非成功 STOP | 原正式 STOP 真实存在并保留 |
| evidence_read | 完整引用/短引用、视图及 JSON Pointer | 原 SDK 与短引用投影 | 恢复完整 EvidenceRef | 所有权、视图、正式读取信用 | 无科研 Worker | 精确事实、导航、错误分类 | 原 Study 真实调用；短引用/错误回归通过 |
| investigate / experience / recall | 解释、程序性经验、原始历史导航 | 原 SDK 工具列表与现有测试 | 原只读工具/Reporter | 不授予科学证据信用；Reporter 单独收费 | 不启动科研 Worker | 解释与事实分开 | 经验与 SDK 回归通过；本次未新增真实远程解释对照 |
| research_rl | 当前无正式 capability | 原 SDK 未暴露 | 不执行训练 | 未获训练/stage/evaluation 授权 | 仅隔离无训练环境预检 | 不伪装可正式执行 | 有意未授权，保留 |

## h27–h31 的证据与修复

- **h27**：前两次目标对象不符合原实际 SDK Schema，不属于“合法请求却无法执行”的缺陷。第三次 Schema 合法，但 `optimal_task_violation` 与 Native T1 来源混用，正确拒绝。修复目标说明与针对性反馈，区分机制对象、Native 有限最好值和 Conic 数值最优值；不替 Main 改指标。保存的 result_12 实际是 Direct，不可自动冒充 T1 stencil。
- **h28/h29**：原 SDK Schema 允许同时传 saved_state 与 execution，编译器正确拒绝；缺少互斥展示和可用状态发现是接口问题。现 Schema 提前排除混合来源，反馈给出两种合法方案。
- **h26 状态核验**：result_12 的 `/native_dynamics/baseline_peak_speed_state` 保存了完整 `mjSTATE_INTEGRATION`，不是末端采样数组。已按原候选、配置、物理身份、完整 baseline 控制源和网格核验，并真实 restore，零物理积分步。它表示 **baseline 保持期速度峰值**，时间约为 0.6 s，不代表优化后最好轨迹的任意时刻。Main 必须明确选择这个来源，工具不推断制动时间点。
- **新增真实贯通缺陷**：完整状态的记录时间为 `0.6000000000000004`；旧准入严格比较会拒绝 0.6 s 末端。现复用冻结协议既有 `horizon_alignment_atol_s`，不修改原记录，不放宽物理任务界限。
- **h30**：原 Plan 文字描述 Conic，但结构化请求明确选择 Native T1/pattern。实际 Worker 与结构化请求一致，**原 Conic 假设未检验**，不能算 Conic 失败。V4 的 Conic 入口本来存在于结构 M2 inspect，却未从 Native control 入口清楚交付。已展示现有入口、编译/Worker 对照与未测试状态。当前 Conic 是冻结初始预张力下的 sampled affine 模型，**不支持围绕任意 Native schedule 重新线性化**。
- **h31**：混合搜索无法无损保留原截面旋转，拒绝是必要准入。保留拒绝并提供拷贝完整原参数、只修改所选坐标的 generate 路径；没有静默清零旋转或更改原结构。

## 工程验证

定向回归 22 项通过。另一个历史 V2 展示测试在原始基线函数也复现失败：旧断言禁止 L0 出现 `mass_matrix` 等名称，而基线已显示这些机制目录/参数说明；未为该旧断言扩大修改范围。最终补充方法反馈断言的 6 项测试也全部通过。

四个隔离真实 Worker 均 computed，原 Store 数据库校验和保持不变：Native Direct → 完整状态机制 inspect；Conic → 数值验证 → capability_sequence → Native T1。每个 Native 搜索只用 2 callbacks。完整 request/result/boundary/runtime/log 已保留在工程证据包。工程结果不导入正式 Study，不用于 SELECT，也不作为新候选科学表现汇报。

## 原账目、候选与正式续研

原 STOP：`2f4ec3dbe0e484ad1368bbfe64061607e3940a38c28451792b1009a1750f0b61`。

| 资源 | 原累计上限 | 已用 | 原剩余 | 本次追加 | 新累计上限 | 续研开始时剩余 |
|---|---:|---:|---:|---:|---:|---:|
| Provider | 100 | 92 | 8 | 52 | 152 | 60 |
| 公共操作 | 569 | 85 | 484 | 0 | 569 | 484 |
| 独立 Replay | 18 | 0 | 18 | 0 | 18 | 18 |
| 数学评估 | 无累计次数配额 | 13 | — | 0 | 无累计次数配额 | — |

用户已在本 chat 明确授权真实测试、后续自主监督与及时修复。按原 B3 原子预算追加、实现迁移和 nonpass STOP continuation 执行；不创建替代 Study、不清空历史或费用。精确 committed implementation、新 resolved identity、批准 scope identity 和激活回执由后续冻结记录列出。

`candidate_1210` 精确引用：`3634c476a5d0092d185d425c99318c150a9a4b6238fb9b9621b335462ac8f2a5`。物理设计身份：`29a4395896937d9b5a5d9116559574e99945ae06091f4119071663efb8143e44`。三段、两腱；段长 0.11/0.09/0.10 m，Young 模量 3.5/3.0/3.2 MPa，圆截面半径 0.0062/0.0057/0.0057 m；整链两腱 polar span 半径 0.022 m，相位 π/4。baseline 引用 `4ea81e316a2c2ecf2e916f89cc063165f9f029b4b676ceeeca9c46d899bb6f5b`，两通道顺序 tendon_0/tendon_1，0–0.6 s、0.02 s 网格，恒定 0.2 N，合法且未测任务表现。不会重新生成或重复初始化。

原最佳 result_13 仍未通过 positive_high：终点误差 0.023961 m、保持期最大误差 0.024520 m、最大速度 0.098079 m/s；阈值为 0.01 m、0.01 m、0.04 m/s。原 Study 没有独立 Replay 或联合通过证据。新正式决策与评价结果将追加记录，不能从有限失败推断两腱不可行，也不能把同时改变的截面和腱路单独归因给半径。

## RL 预检

candidate_1210 的 positive_high 可用现有 prepare_input 和 PPO 环境：72 个 hinge DOF、153 维观测、2 维动作、ideal_tension、0–8 N、physics dt 0.001 s、control dt 0.02 s、30 个控制区间，holding samples 27–30。两次相同种子的三步无训练 rollout 完全一致。训练 stages/actions 均为 0。

Native→Residual 原入口只接受 verified mathematical trajectory，不能自动接受 Native explicit schedule。最小适配现只接纳当前 Store 已完成 Native T1/Direct 的准确 control_schedule_reference，检查其 optimized_schedule 完全一致并复用原完整 candidate/task/order/grid/bounds 验证；普通 baseline、未完成或不匹配来源仍拒绝，不重采样、不裁剪。隔离真实 Native 结果已成功导入并生成合法 reference。

negative_low 与 central_high 仍被现有单一 `rl_task` 绑定拒绝。未来最小适配是从冻结 task_conditions 选择精确任务绑定并保持每个 stage、checkpoint、reference、evaluation 的工况身份。普通 RL evaluation 没有 joint_assessment 要求的 source_reference、独立 Replay 收据、profile/evaluation 来源和正式证书；不能用三个普通 evaluation 替代联合 SELECT。后续若 Main 选择 RL，必须另行明确 capability、rl_limits 的训练 actions/stages/evaluation/worker 并接通上述证据路径；本次授权不启动训练。
