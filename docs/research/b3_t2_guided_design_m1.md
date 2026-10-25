# M1：B3 T2 数学指导与 Study Readiness

2026-10-25，Asia/Shanghai。基线 `feat/b3-benchmark-readiness@43b64f7e8fd1de5b5cfda3d75980e94c74a8080d`，
独立分支 `feat/b3-t2-guided-design`，工作树 `D:/softrobot-agent/.worktrees/b3-t2-guided-design`。
开始时远端基线精确一致，目标分支不存在；基线树干净。主树仍为 `feat/gvs-dynamics@d629a80d`，
它是该基线的祖先，其既存未跟踪环境和 runs 文件没有清理、覆盖或提交。

**结论：conditional。M1 的配置、方法发现、模型组准入、原 dispatch/Worker 请求边界、
L1/L0 交接及原 generate 提案接口已完成离线验证；0.50 s B3 的实际 T2 数值方向、
局部模型可信范围和物理效果仍未验证。没有启动 M2。**
本轮真实数学计费 **0/14**，模型构建、CONIC、对偶面、Provider、独立物理、NMPC、PPO、新正式 Agent Study 均为 **0**。
保存的 F2 已实际走过真实 GVS/CONIC/T2/Store 链，因此本轮没有重复计算来证明已存在的数值内核。

## 审计结论与数学范围

已读取目标树 `AGENTS.md`、[B3 Readiness](b3_benchmark_readiness.md)、
[S130 T1/T2/T3](s130_optimal_capability.md)、[S138](s138_task_conditioned_research.md)、
[C3 A/B](c3_ab_live_comparison.md)、[F1/F2](c3_f1_f2_decision_continuity.md)、
[G1/G2](c3_g1_g2_decision_validation.md)、[最终 G2](c3_g2_scientific_decision_loop.md)。
S140/S141 不在指定基线文档树中，分别从封存提交 `2913fbb1122374ca16136b123c79c070a80f65b5`
的 `docs/research/s140_structure_effect_prescreen.md`、`f2223c24b2806076b2fc9c670cbaaf56c4deec4d`
的 `docs/research/s141_model_validity.md` 用 Git 只读审阅，没有合并、复制或修改其档案。

现有 `capability_sensitivity.py`、`conic_capability.py`、`OptimalCapabilitySensitivity`、
`candidate_methods/sensitivity_context/calculate_sensitivity` 均已存在并可复用。
**数学内核、优化器、乘子、有限差分公式和 search.py 都没有修改。**

模型为选定 GVS 基的连续局部仿射状态模型，包含 A/B/C/D、drift、初态投影和各结构自己的名义张力。
T2 v1 仅接收相同冻结任务、固定拓扑、单个合法连续参数的 3 或 5 个独立模型，
工作点为 `controller_start_input` 或 `standardized_initial_pretension`；本 B3 使用零初态及合法预张力，
不把其称为目标静力平衡。每个结构都使用其自己的 GVS 线性化模型重新求解控制。

数学问题仍是 `V_task(d) = min_U max_i g_task,i(d,U)`，正尺度范数约束为
`||r_i||/rho_i-1`，区间为原物理尺度下的两侧有符号违反量。
g 来自冻结 TaskAdapter，未添加能耗、速度软权重或任意新评分。
B3 0.50 s 的目标为 `[0.29,-0.035,0.19] m`，张力各路 `[0,8] N`，
控制/验收网格 0.01 s；终点 0.50 s，保持 `[0.45,0.50] s` 的六个 inclusive 样本，
位置限 0.010 m、速度限 0.020 m/s，共 13 个任务行。物理步长配置为 0.0005 s，本轮没有推进。
工作点张力 0.2 N 不会把实际物理盒改成 `[0.2,7.8] N`。

T1 包含独立重放、输入合法性、原始/对偶/KKT、支撑下界估计和 gap 检查。
T2 在绝对张力坐标下比较固定基准控制的响应与各结构控制重优化后的最优值，
保留左右差分、采样活跃集、步长稳定性、条件包络及近最优对偶面诊断。
数值支撑区间不是严格误差界；活跃 minimax 瓶颈也不等于该任务约束已被违反。

至少两个尺度及相应稳定性检查才可能得到 `numerically_stable_local_direction`。
双尺度 FD 通过但乘子稳健性未决时保留 `stable_reoptimized_direction_envelope_unresolved`；
平坦分别保留 `numerically_flat_at_resolution` 或 `numerically_flat_fd_envelope_unresolved`；
只有一次中心割线或其他检查不足时为 `directional_comparisons_only`，方向仍 unresolved；
数值最优性不足为 unresolved，不能从求解失败推出不可行。
这些状态均不提供严格下降、全局非线性 GVS 梯度、闭环 NMPC 梯度或 MuJoCo 改善保证。

## 新草案、参数目录和公平预算

新增 [B 草案](../../configs/research/study_b3_t2_pilot_b_draft.json) 与
[C 草案](../../configs/research/study_b3_t2_pilot_c_draft.json)，最终 ID 为
`b3-t2-050-b-v2-draft`、`b3-t2-050-c-v2-draft`。
原 A/B/C JSON、已绑定 Store、封存 C3/G2 和 A 的基准控制均不变。
两组保留相同授权背景，是 **history-assisted** 草案；不能改称 cold-start。
历史只能帮助选择问题，不能给新时限授予数学执行、物理执行或 SELECT 身份。

C 显式声明原 `mathematical_methods` 的 CONIC 和 T2，以及原 `family_sensitivity_variables`：

| 冻结参数 | 单位 | 两段参考结构中的值 | 范围来源 |
|---|---|---:|---|
| segments.0.length_m | m | 0.160 | FamilySpace segment_domains.0：0.08–0.24 |
| segments.1.length_m | m | 0.110 | segment_domains.1：0.06–0.20 |
| segments.0.young_pa | Pa | 10,450,000 | 对应材料域：2,000,000–15,000,000 |
| segments.1.young_pa | Pa | 5,400,000 | 对应材料域：2,000,000–15,000,000 |
| spans.0.radius_m | m | 0.018 | routing_domains.radius_m：0.014–0.023；还须通过真实生成几何检查 |

索引按当前候选重新解析。单段候选的 segments.1 返回不适用；spans.0 只影响其实际覆盖腱路，
不自动修改其他 span。不一次分析全部参数，不授权离散拓扑导数、截面尺寸、任意路由角、阻尼或密度。
未来仅在具体任务证据表明有必要时再扩展，M1 没有发现必须扩展这些参数的接口缺口。

B 不获得 T2 参数 grant，仍由原 `fixed_structure_reference/same_robot_structure` 拒绝任何结构变化，
可合法改变控制。C 的 T2 是可选研究动作；可以继续优化控制、做有理由的对照、诊断或停止。
C 最多两种**独立物理评价结构**，包括共同参考；数学扰动候选只用于准备模型，不新增物理机会。

| 每组限制 | B | C |
|---|---:|---:|
| Provider（含 Reporter）/公开操作 | 32 / 80，保护额度 4 / 6 包含在内 | 相同 |
| 数学评价总计费上限 | 22 | 22 |
| 共享独立物理启动 / NMPC / 完整回放 | 4 / 2 / 2 | 相同；每结构至多 1 NMPC + 1 回放 |
| native 回调 / 更新 / knots | 8 / 2 / 4 | 相同 |
| PPO | 0 | 0 |

NMPC 仍为 horizon=10、substeps=1、replan_period_s=0.1、每次最多 120 迭代、tolerance=1e-6；
最终 12 cells/段、8 N/路，冻结监督协议和独立验收保留。没有把内部 native 积分当作免费物理。
B/C 的最优“已找到结果”比较不构成固定结构理论无解或 C 的额外结构收益证明。

原账本中一次 linearization 准备计 1，T1 计 `1+B`，其中 B 是每模型实际 CONIC 子问题数。
B3 的 B=1；T2 k 档中心差分需要 M=1+2k 个**已登记**模型，预占 `M*B+2k`，模型准备另计：

| 工作集 | 模型数 | T2 内部 CONIC / dual-face 预占 | linearization 准备 + T2 | 全部用 T1 准备 + T2 |
|---|---:|---:|---:|---:|
| 单尺度 | 3 | 3 / 2 | 8 | 11 |
| 双尺度 | 5 | 5 / 4 | 14 | 19 |

新结构自己的 T1 再计 2：双尺度完整链分别为 16 或 21，因此冻结 **22**，
可以容纳较贵的准备方式和一次额外诊断，而不是忽略内部求解而照抄 20。
若只完成单尺度且方向未决，不要求自动追加半步长。计划预留的失败、早退、未用尝试不退回；
实际次数以原 result/checkpoint/receipt 为准。相同 operation ID 的完成收据复用额外计费 0，
没有新增跨 ID 模型缓存或预算账本。本轮上限 14 与未来每组 22 是不同范围，本轮实际使用 0。

## 方法发现、执行与证据读取示例

Agent 先指定当前 owned candidate，使用原入口：

```text
evidence_read(reference=C0, view="mathematical_capabilities",
              pointer="/methods/controlled-capability-sensitivity-v1")
```

现有方法目录派生 `registered / authorized / applicable / executable`，没有第二套状态机。
`registered` 表示现有方法已实现；`study_authorized` 表示冻结方法/参数 grant，
`authorized` 还要求真实的正式 scope 授权；`applicable` 来自原 Task/模型准入与当前参数；
`executable` 还要求原 sensitivity_context 验证的完整组、依赖、剩余数学预算及非收尾/停止状态。
未授权但参数/任务适用时不会误报可执行，配置文本中的方法名称不能代替模型工作集。

目录保留参数值/单位/边界/来源、最大对称扰动步长、完整 ready_stencils、
缺模型的参数值以及仍未验证的部分组、准备请求模板、全新准备成本、剩余预算与拒绝理由。
尚未选择 h 时给符号工作集，不伪造精确缺项或复用数量。
只有 ready_stencils 已通过原身份验证；部分组不承诺复用成功。
模型准备仍用原 generate + research_analysis(linearization)，也可选择已授权的 T1 准备。

```text
# 需要后续正式授权；C0/Cmh/Cph/Cmh2/Cph2 均为本 Study 原 generate 产生的候选。
research_analysis(candidate=C0, operation="linearization",
    operating_point="controller_start_input", scoring_window_s=0.05, protocol=P)
# 其余候选按相同工作点规则准备，取得登记结果 M0/Mmh/Mph/Mmh2/Mph2。
research_analysis(candidate=C0, operation="task_capability",
    operating_point="controller_start_input", protocol=P,
    capability_method="sampled-affine-conic-minimax-v1",
    optimal_sensitivity={variable:"spans.0.radius_m", steps:[0.0005,0.00025],
        model_results:[M0,Mmh,Mph,Mmh2,Mph2]})
```

P 必须读取冻结的完整 analysis_protocol；这些占位符不能替代 EvidenceRef。
完整合法组的可复制请求也直接在 `readiness.variables[].ready_stencils[].request` 返回。
缺少模型、越界、变更其他参数、拓扑、任务、网格、工作点、模型身份、预算或依赖时，
原 gate 在新增求解前拒绝。旧模型不能改名为 0.50 s 新模型。

```text
evidence_read(reference=T2, view="working_set", pointer="/mathematical_decision_view/optimal_sensitivity")
evidence_read(reference=T2, view="full", pointer="/optimal_sensitivity")
```

第一条是现有 working_set 上新增的按需派生路由，复用 ResultCard/mathematical_decision_view，
不是新 evidence_read view。此前不存在名为 result_card 的可调用 view，测试已核对真实 Schema。
L1 提供原任务/候选/模型绑定、参数及实际采样值、固定控制和重优化差异、原 direction_status、
数值最优性/包络限制、活跃约束与实际采样时刻/违反量、观察的精确原始 pointer、费用和原始来源。
`sampled_parameter_values` 只表示已采样点，不建立有效邻域、信赖域或下降半径。
当前完整任务约束/半径/输入盒还可读 T2 的原 `/task_analysis`、`/binding`、`/operating_point`、`/protocol`。

L0 只保留参数名、direction_status、preferred_parameter_direction、物理未测和 L1 查询。
移除了全参数清单的重复注入，不携带差分表、矩阵、模型组、张力序列或乘子。
L2 仍为原模型、优化解、控制、乘子、Plan、Worker、Store 和收据，未建新数据库。
原历史结论索引和跨任务背景隔离的两项回归通过；没有把历史最优结构/控制答案注入 cold-start。

## 最小结构提案与后续控制重优化

原 generate 已支持复制当前 GenerationRequest 后修改一个参数，因此不需要改 design.py 或 search.py，
也不新增梯度步、线搜索或自动多轮 Agent。Agent 自己决定动作和步长。
例如读完 T2 后，若方向仍 unresolved，可以明确选择一个小范围对照；以下只是接口例子，**没有 B3 收益结论**：

```text
research_plan({action:"generate", generation:<复制 C0 的完整 parameters，仅 spans[0].radius_m 改为 0.0181>,
  supporting_evidence:[T2],
  decision:{hypothesis_id:"radius-contrast", research_intent:"DESIGN_MODIFICATION",
    selected_candidate:C0, selected_method:"generate", claimed_inference:"empirical_search"},
  hypothesis:"方向未决；检验小幅半径对照，不称梯度步骤。",
  expected_observation:"新候选自己的 T1 控制重优化后可能显示可分辨变化。",
  weakening_observation:"数值平分、未收敛或模型失配。",
  fixed_conditions:"冻结 B3 任务、拓扑、其余结构、控制机会、输入盒和网格。",
  stopping_condition:"原预算内一次对照；无证据时不追加。",
  interpretation:"局部数学提案，须独立物理验证。"})
research_analysis(candidate=Cnew, operation="task_capability", operating_point="controller_start_input",
  protocol=P, capability_method="sampled-affine-conic-minimax-v1")
```

原 Plan 保存 T2 支持引用和生成来源；新候选不会自动取得旧结构的优化控制、分数或物理成功身份。
T1 对新候选重新准备模型并重优化控制后，才可比较同任务数学证据。
M1 测试实际经过原 core.dispatch(generate)，核对 Plan 来源、新候选没有旧数学结果，以及其新 T1 请求计 2。
该测试的 T2/Worker 是明确的离线 stub，不声称执行了新的 T1 或对照获得收益。
控制优化、另一参数、模型诊断、对照、停止均仍是合法选项，T2 不强制改结构。

## 本轮证据与未决科学问题

旧 S130 两尺度长度 FD 为约 100 score/m，状态为
`stable_reoptimized_direction_envelope_unresolved`；远段模量为
`numerically_flat_fd_envelope_unresolved`，不能发布硬化/软化方向。
这是旧 0.35 s、不同参考/结构模型的结论，不能转移成当前 B3 的设计建议。
S140 的同总长变体受直臂轴向一阶退化下界支配；S141 弯曲点局部几何更准确，
但完整任务动力学/结构排序仍不可信，没有形成可直接复用的可靠区域下降方向。

原 F2 Study `c3-f2-radius-20261025` 实际有三模型和完整 T2，
来源 [原归档](../../evidence/c3_f1_f2/math/immutable_artifacts.tar.gz)。
半径 17.5/18/18.5 mm 的固定控制响应不同，重优化后均约 -0.2；
单尺度结果为 `directional_comparisons_only`、方向 unresolved，对偶面未决。
本轮只读取该档案的原始结果和精确数值，没有重做其 3 次模型准备 + 3 CONIC + 2 对偶面求解。
保存的双尺度 S130 结果亦原样读取自
[t2_final_comparison.json](../../evidence/s130_optimal_capability/t2_final_comparison.json)。

因此本轮**没有发现新的、有数值依据的 0.50 s B3 结构修改方向**。
准确原因是没有执行此任务的 T2，而旧证据既有任务身份差异，又有平坦、对偶未决和局部模型失配限制。
这不是结构没有物理作用、固定结构不可行或 C 必然优于 B 的结论。

## 工程验证、资源与交付

使用已有 s135 独立运行环境，在本工作树的隔离进程内预检，没有安装或修改共享依赖。
Python 3.11.16、NumPy 2.4.6、SciPy 1.17.1、Pydantic 2.14.0、CasADi 3.7.2、MuJoCo 3.13.0、
CVXPY 1.9.3、Clarabel 0.11.1、Strands 1.59.0，三个 BLAS/OMP 线程值均为 1。
目录检查使用的就是现有 Worker 的 sys.executable，不声称默认 Python 同样具备这些依赖。

最终 **6 项定向测试通过，23.455 s**，见
[offline_verification.json](../../evidence/b3_t2_guided_design_m1/offline_verification.json)：
新四项验证解析、公平预算、固定 B、正式门禁、缺失/完整模型组、原 dispatch/9 次预占/零收费收据复用、
原 generate、L1 实读、完整 agent_decision_brief 的紧凑 L0、stable/flat/unresolved 不混淆；
另复用两项 B3 历史完整 wire 与 L1/L2/身份隔离回归。没有运行全仓测试或新增数值求解。
真实 Worker 全局禁止；单个明确标注的测试替换 Worker 和数值核，借用 F2 数组作合成身份夹具，
不将重绑定数组当作新 B3 模型或科研证据。夹具中的 9 次账本预占是故障/收据接线检查，不能算真实数学费用。

尝试复用的另两项 S130 测试在旧 AgentReporting fixture 初始化时因重复传入 exclusive_resources 报错，
未进入被测逻辑，未计为通过；相应夹具源文件在指定基线上即如此，本轮没有修补无关旧测试。
新夹具初次运行暴露的读取 view、背景导入、浮点精确相等、guard 参数及 grant 冲突均已修正；
所有失败均发生在真实求解/Provider/物理派发之前，记录保留在验证摘要。

早期测试曾以 v1 草案 ID 在两个 fixture Store 完成零使用 prepare，原机器 grant 锚点因此保留。
没有删锚点、清账或复用目录冒充新预算；最终可交付配置使用新的 v2 ID。
后续所有夹具改用既有测试方式的唯一 fixture project/grant；其合成数据与正式待授权 Store 分开。
v1 原目录分别为 runs/b3-t2-b-fixture-e209bb4c 与 runs/b3-t2-fixture-e8fa0c5e，
均没有正式授权、Provider、数学费用或物理执行，保留且不作为后续运行入口。

生产修改五个既有文件 **+62/−16，净增 46 行**：
optimal_capability.py +24/−8、task_constraints.py +9/−1、capability.py +14/−0、
research_context.py +11/−7、core.py +4/−0。测试/配置/本文/精简验证产物另计。
config.py、design.py、search.py、数学内核和旧封存文件不变；没有第二 Worker、搜索器、Store、记忆系统或预算账本。

本轮模型准备、内部 CONIC、对偶面、数学计费及其真实数值时间均为 0；
几何构形、协议解析、依赖导入、离线测试耗时不冒充能力计算，也没有将它们说成耗时为零。
最终 prepare/bind、冻结身份、原账本零使用和无授权状态见
[frozen_drafts.json](../../evidence/b3_t2_guided_design_m1/frozen_drafts.json)。

实现提交为 `dc773ea20aad9146a4f2080ec64b2d65b6b7d99f`，两份正式待授权草案已实际 prepare/bind 到该实现。
B resolved_identity 为 `4a623b709812f4787383e4386a7d0deaec9ed76cb370f11312951d323423f554`；
C 为 `4de5e88479238e3e5f478d8251aaf2a6951ec7fa7d6d06f379aba15f93a03093`。
两个正式待授权 Store 位于 `runs/research/<上述 v2 study_id>`，候选、模型、分析结果、数学费用、
Provider、物理、NMPC、PPO 和 pending reservation 均为零；只导入三个明确授权背景锚点，
没有将其计为当前结果。Handoff live 标志仍为 false，真实 expensive guard 均按原授权错误拒绝。
随后提交仅补报告与零使用冻结收据，不修改已绑定的科学实现或冻结 spec。
最终交付提交的完整 SHA、普通 push 后远端 HEAD 和树状态在交付消息核实，避免自引用 SHA。

## 后续运行入口与停止边界

新 v2 待授权 Store 仅 prepare/bind，不写 formal_study_authorization，
不登记 session_handoff_live_admitted，不激活 Provider，不调用 run。
其他机器使用同一提交及配置从原 CLI prepare/bind；已有 Store 用原 recover/restore-only，不重建或清账。
后续显式授权必须按原 resolved_identity/scope_identity 绑定各组预算及执行范围，
并引用已有真实 Handoff/request-feedback 准入来源，不能无来源切布尔值。

新机器在干净提交下可复用这些仅准备的命令（本机已完成，无须重复创建）：

```powershell
& $researchPython -m tools.research prepare --spec configs/research/study_b3_t2_pilot_b_draft.json
& $researchPython -m tools.research bind --run-id b3-t2-050-b-v2-draft
& $researchPython -m tools.research prepare --spec configs/research/study_b3_t2_pilot_c_draft.json
& $researchPython -m tools.research bind --run-id b3-t2-050-c-v2-draft
```

```powershell
$researchPython='D:/softrobot-agent/.worktrees/s135-task-conditioned-control/.s135-env/Scripts/python.exe'
$env:OPENBLAS_NUM_THREADS='1'; $env:OMP_NUM_THREADS='1'; $env:MKL_NUM_THREADS='1'
# 下列仅为后续正式授权及原 Handoff 准入均完成后的入口；M1 未执行：
& $researchPython -m tools.research run --run-id b3-t2-050-b-v2-draft --session-handoff --handoff-request-bytes 160000 --pause-exploration-remaining 4
& $researchPython -m tools.research run --run-id b3-t2-050-c-v2-draft --session-handoff --handoff-request-bytes 160000 --pause-exploration-remaining 4
```

共同参考按 [b3_reference_generation.json](../../configs/research/b3_reference_generation.json) 在各组内合法生成；
完整流程和明确参数/Plan 示例见上文。不要把两个组的命令并发执行或把 B 研究结果注入 C。
A 继续原方案；如果要把 A/B/C 组成新的总额度比较，需后续授权明确新的 B/C 上限，不能沿用旧总预算。

解析/生成/证据读取/授权拒绝：**ready（已实际离线执行）**。
已有数值 T2 内核：**ready（旧真实证据复用，本轮未重算）**。
当前 B3 0.50 s T2 控制重优化方向、模型有效范围及物理收益：**conditional（未测）**。
草案正式 Provider/科学执行：**blocked（刻意保留的显式授权与准入门禁）**。
没有新的必需优化器或搜索接口缺口。M1 到此停止，不自动启动 M2，不为获得 ready 增加数学或物理实验。
