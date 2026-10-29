# P6.3-B4-Live：M0 computed；M 达到 M1，未达到 M2/M3

两项已各执行一次并结束。M0 的原 Native 内核计算成功，形成五类机制中心割线；
独立 M 自主完成正式 diagnose，但两次数学请求均在 Worker 前被原准入拒绝。
没有追加预算、切换模型、豁免失败、代交科学选择、重试 M0 或开展物理验证。

沿用原 B4 worktree 和两个 Store，在原目录切换交付分支
`codex/p6-3b4-live-validation`。源码基线 `fa25cb4c9b23ed88c5db1381f127869b3c900f97`，
原执行绑定 `ae315c3565e220b18bbbf4aef02d8685eb3a24ba` 兼容，无重新创建 Store 或修改科学配置。
此次未修改生产代码，也没有启动额外回归/Mock 测试。原候选、失败、授权、Store 与证据均保留。

## M0：实际机制响应

[M0 非敏感结果与原始来源](p63b4_m0_live_results.json)。Study
`p63b4-m0-mechanism-20261029`，resolved identity 沿用准备时的
`ebc11388e95f860c0144ae3521d22cf7b7655148f9c9c91d6b8a7ef4c1d77c66`。
独立 formal_study_authorization 引用为
`073c89d15b02533ab1b7c20b49cc1ea3235b496358fd1fbc5d0f2fc24920bdd2`。

从原 Store 读取未修改的 `m0_analysis_request.json`，通过 AnalysisRequest、原 state.guard 和
analysis.dispatch(origin=engineering_preflight) 一次执行，操作键 `p63b4-m0-fixed-input`。
返回 **computed**，真实数学结果引用：
`6a8dc5fa66a43114455b9a7836e3644fbad41d781012e8533dd7acd609f055b0`。
Worker 已退出、termination_confirmed=true、returncode=0、pending=null。

冻结比较为 segments.0.length_m：0.160 m 基线，0.159/0.161 m 左右对照；两段、四腱、每段 12 cells。
Native 命名 qpos/qvel 同为零，t=0，standardized_initial_pretension，四通道绝对张力各 0.2 N，
短响应 0.01 s。坐标为 Native 48 个命名 hinge、world tip，通道顺序 tendon_0…tendon_3；
完整次序保留于 JSON。比较中所有模型按原内核统一重置 solver history；不是相同平衡/能量条件。

下面是实际数组的 Frobenius/Euclidean 范数，**不是各分量的符号或优化方向**。
左/右列为原 mechanism_changes 中的单侧割线范数；中心列直接使用实际
`(F_plus-F_minus)/(p_plus-p_minus)`，分母 `0.0020000000000000018 m`。

| 机制量（形状） | 基线范数 | 左割线范数 | 中心割线范数 | 右割线范数 | 割线单位 |
| --- | ---: | ---: | ---: | ---: | --- |
| 质量矩阵（48×48） | 0.0173837 | 0.128270 | 0.128630 | 0.128990 | (kg·m²)/m |
| 末端 Jacobian（3×48） | 1.19005 | 3.00463 | 3.00463 | 3.00463 | (m/rad)/m |
| 腱长 Jacobian（4×48） | 0.176363 | 2.72e-14 | 1.66e-14 | 2.26e-14 | (m/rad)/m |
| 末端加速度输入映射（3×4） | 286.079 | 1.76e-8 | 5.58e-9 | 2.66e-8 | (m/(s²·N))/m |
| 被动力加速度贡献（3） | 0 | 0 | 0 | 0 | (m/s²)/m |

基线量本身的单位分别是 kg·m²、m/rad、m/rad、m/(s²·N)、m/s²。
完整有符号数组、中心值、两侧原值/割线和精确原始 pointer 均保存于原 M0 Store 的
`m0_mechanism_central_secants.json`，Store 派生引用：
`467dda548089bbaf898c248a2483d46773bda050048f5bc63b3d84f878fcb8b1`。
它是确定性后处理，不是第二个数学 Worker 或新的独立科学评价。

原始路径为 `/native_dynamics/structure_baseline/mechanics/<field>`、
`/native_dynamics/structure_responses/{0,1}/mechanics/<field>` 及
`.../mechanism_changes/<field>/finite_difference_per_parameter`；候选和单位映射见 JSON。
原数学结果不可变，没有用派生结果覆盖它。五项中心计算与按实际 delta 加权的原单侧割线重构一致；
这只是代数一致性，不是独立数值精度验证。

质量矩阵的最大相对扰动为 0.742%，左右割线相对差约 0.571%；末端 Jacobian 的最大相对扰动为
0.252%，左右割线差接近浮点精度。这提供了此工作点下可解释的惯性与几何响应证据。
腱长 Jacobian 和加速度输入映射的最大相对原量变化仅约 1.54e-16 和 9.29e-14，
割线差相对小割线可达 137%/164%，但绝对变化极小，不能据此认定存在可靠敏感方向。

被动力贡献为原 `J M^-1 qfrc_passive`，在零位移/速度下为零；这不等于全部漂移为零。
同次记录 gravity_bias 的范数约 0.215311 N·m，实际 tip acceleration 约
`[0, -7.33e-14, -9.81] m/s²`。质量平衡残差约 5.97e-16 N·m，仅表明引擎内部一致，
不能证明跨模型或硬件准确性。不能把被动项、重力 bias 与总加速度混为一项。
三组质量矩阵条件数约 3.17e6–3.22e6；涉及逆质量映射时须注意误差放大。
小质量平衡残差不能替代敏感性误差界，也不能使近零驱动割线自动变得可信。

0.01 s 末端速率的左右变化为 +0.000135440 / -0.000134724 m/s；该时刻没有匹配的冻结任务样本，
原 short_endpoint_tasks 的 constraints 为空。不是 holding window 指标改善或 Reach/Hold 通过证据。
一次 h 的中心割线不构成严格梯度、步长收敛、全局方向或控制再优化结论。

| M0 实际成本 | 数值 |
| --- | ---: |
| Provider / Public operations | 0 / 1（上限 0 / 8） |
| 数学 evaluation | 3/3 |
| 真实数学 Worker 调用 | 1 |
| Native model_builds / rollouts | 3 / 3 |
| mechanics / forward evaluations | 4 / 18 |
| physics_steps / attempts | 30 / 30 |
| kernel_wall_s | 0.1360242 |
| charged_numerical_s | 1.1539686 |
| 独立物理 / NMPC / RL / NLP / BDF | 全 0 |

原 ledger.worker_calls=0 是原账本分类，不代表没有数学 Worker；真实 Worker 数由原执行回执给出。
已调用原 scientific_feedback 生成确定性报告 `2a3a9161e0037bcba7e5df4325d8fd446d70a68670ce11a7e3faccce4849f7ac`，
interpretation_status=deferred，没有调用 Reporter Provider。该报告和 M0 结果均未注入 M。
M0 已有进一步研究局部机制响应的证据；本轮到此停止，不运行第二步长或优化。

## M：自主决策真实窗口

[逐请求、原始 Plan、绑定与实际 L0/Schema 审查](p63b4_m_live_audit.json)。Study
`p63b4-m-sol-20261029`，resolved identity
`2e0cf5935c3de1a7ae98427ce7e30dd3590b697f2ae66deaea4173555f214b84`。
独立授权引用 `102c7a162920d1a2b1d25dafa6e2b59ef2ecaf32d2e8c9964a2a259e2a11cbd6`，
request-feedback live_handoff_admission 引用
`98ba2839eef08d51a57b90c85c99ba79462c30ae42a1eb0a53718e3cd233ba72`。

启动前为原 Operator 未评价候选一份、数学/控制初始化/物理结果均空、九项 Success Case 可读。
一次非推理 models GET 成功确认准确 sol 可用，无 smoke 推理；所有正式发送使用原入口、
gpt-5.6-sol、reasoning=none，无切换或人为科学输入。

12 次 Provider 请求均 HTTP 200，每次原账本扣 1 次 model_call；没有 Reporter 发送。
表内 token 为该请求返回的 total_tokens，秒为原 elapsed_s；不推断货币账单。

| 次数 | 实际工具行为及推进 | tokens | 秒 |
| --- | --- | ---: | ---: |
| 1 | 搜索经验；读候选 parameters 和 methods 目录。发现信息，无科学执行 | 8102 | 10.125 |
| 2 | 搜索；首次读 T1 单方法行动视图、opportunities、provenance | 9797 | 88.984 |
| 3 | 正确读 procedure；精确读 T1 request_template；再读 parameters | 10516 | 11.141 |
| 4 | route(research_plan, diagnose)，只加载工具 | 10784 | 7.547 |
| 5 | 提交 diagnose；research_intent=MATHEMATICAL_ANALYSIS 被原 const 拒绝 | 9199 | 15.625 |
| 6 | Main 自行改为 DIAGNOSE，正式 Plan 完成，达到 M1 | 9653 | 13.203 |
| 7 | 再读候选 parameters，无新 Plan 或计算 | 10985 | 9.062 |
| 8 | 再读 provenance，无新 Plan 或计算 | 10979 | 9.578 |
| 9 | research_analysis：pattern + safety_margin_fraction=0.05 被拒；Worker 未启动 | 11047 | 9.344 |
| 10 | Main 自行改 response，但 source 仍是候选 artifact，被原来源准入拒绝；Worker 未启动 | 11652 | 9.593 |
| 11 | 搜索 success_case 元数据，没有读取正文或初始化 source | 11451 | 11.141 |
| 12 | 收尾读 /all_fresh_results 用了 full 而非 working_set；被拒，额度耗尽 | 7342 | 16.844 |

Main 选中的正式原始假设为：

> For the frozen reach-and-hold task, bounded nonlinear control optimization of the owned Operator-generated structure can find a four-knot control schedule whose simulated terminal error, final-window maximum position error, and final-window maximum tip speed satisfy the task thresholds.

完整原 Plan 的预期观测、弱化条件、固定条件和解释保留于 JSON。Main 自选
`mujoco-nonlinear-task-capability-v1`，研究控制输入，而非本轮 M0 的结构长度；关注 terminal_error_m、
holding_max_error_m、holding_max_speed_m_s。它提出有限预算搜索与阈值比较，明确区分模型结果与
独立接受，也明确失败不证明不可行。它没有真正选择或构造一个合法控制 source。

两次实际 analysis 输入均由 Main 提交，程序绑定 candidate、protocol、operation、唯一 MuJoCo model_source
和唯一初始工作点。第一次完整合同验证失败于 SAFETY_MARGIN_REQUIRES_RESPONSE_METHOD；
第二次完整合同验证通过，原后台随后拒绝 BOUND_EXECUTABLE_CONTROL_SOURCE_REQUIRED。
两次 source 都误用候选 `d2f4fb613c510d3af866cd5fc0d4550ef7c2084f3612256666e0dc20c9bcecd1`，
从未调用 initialize_control。绑定审计保留 raw_main_input、full_request、field_sources 和验证状态，
没有程序替换 source 或自动修复科学变量。

实际 L0 清楚显示 control_initialized=false、no_complete_bound_sequence_recorded、所选方法仍
requires_parameters、需要 initialized/rebound control_optimization.source；analysis Schema 已加载，
顶层 required 只有 control_optimization。没有观察到 L0 声称 source 已齐备或候选就是 schedule 的矛盾。
当前证据支持将失败定位在 Main 对来源/设置前提的选择和预算使用，不能归因为数学 Worker 失败或数值无解。
仍可将本次记录作为未来研究源前提表达是否足够易用的依据；本轮不扩建框架。

最终 L0 的 stop_index.query 为原 FamilySpace anchor + working_set，且引用属于**同次实际 Schema**
允许集合。Main 使用了正确 anchor 却把 view 改为 full，导致 EVIDENCE_VIEW_MISMATCH；
反馈给出准确 corrected_query，但已无后续 Provider。此处不同于 B2 的真实广告/枚举矛盾。
没有原生 STOP/SELECT；原 research_status=ready，最终为 supervisor_pause，不伪写科学 STOP。

M 总计 Provider 12/12、Public 19/32、数学 0/4；所有拒绝均保留并计入原 Provider/Public 账本。
prompt/completion/total tokens 为 119158/2349/121507，reasoning_tokens=0，原 ledger.wall_s=212.187。
金额未知。原 numerical_s=0.3968756 包含已有准备/准入开销，不能抹为零；数学 Worker、Native 模型构建/
rollout、独立物理、NMPC、RL、NLP/BDF 均未执行。Reporter Provider 和科学报告均为 0。
实际只精确阅读 research-bounded-continuation@2；九项 Success Case 权限仍在，但正文读取数为 0。

**M1 通过；M2/M3 未通过。** 正式科研假设与 Plan 是实质推进；两次数学工具提交不是 computed。
因为没有数值结果，无法观察 Main 对数学证据可靠性、结果后科研判断或下一行动的能力。
没有 pending Provider 或 Worker，Provider 余额为 0，公共操作余额 13 不构成续窗授权。

## 与 B2 M 的观察性比较

| 指标 | B2 M | B4 M |
| --- | ---: | ---: |
| 单方法详情读取 | 4（同一 fixed-input 方法） | 1（T1） |
| 重复单方法详情额外读取 | 3 | 0 |
| 错误 view/pointer | 2 | 1（最后收尾） |
| 保护期 anchor 枚举拒绝 | 1 | 0 |
| diagnose route | 1 | 1 |
| diagnose Plan 提交 / 正式完成 | 0 / 0 | 2 / 1 |
| research_analysis 提交 / computed | 0 / 0 | 2 / 0 |
| 数学结果后的决策 | 未观察到 | 未观察到 |

本次首次方法读取确实交付了目的、缺参和模板入口，Main 第 3 次就沿精确模板查询前进，
第 6 次完成 Plan；没有反复读单方法导航第一页。仍重复读候选参数/来源，并犯设置、source 和收尾 view 错误。
不能称为“更早进入数学计算”：只更早进入实际请求阶段，尚未跨过准入。
这是两个独立窗口的观察性比较，不是严格因果消融，也不证明全部接口或自主科研问题已解决。

## 交付与停止

保留两个 Store、两份授权、M0 完整矩阵和中心派生引用、M 原始 wire/response/失败回执；
仓库只提交本说明和非敏感结果投影，不提交凭据、完整 Store、Knowledge 正文或 Provider opaque output。
本轮没有发现必须修改生产代码才能继续已授权测试的工程阻断，因此没有代码修复或额外测试。
M0 不再重跑，M 不续窗；不自动进入梯度优化、独立物理验证或跨任务研究。
