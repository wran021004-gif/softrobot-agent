# 阶段 B：MuJoCo-direct 离线控制优化

**MuJoCo-direct 控制优化已经可用，并已完整回放及独立验收。** S142 增刚结构的保持最大速度
从 **0.022849089711 降至 0.018846588184 m/s**，降低 **17.5171%**；原阈值始终为 0.02 m/s。
全部六个保持样本及其他冻结组合条件通过。这只支持同一 MuJoCo 模型、冻结离散采样条件下的
一次工程通过，不支持硬件、跨模型、鲁棒性、重复性或全局最优结论。

基线 `codex/mujoco-native-math-stage-a@904f4932a`；独立工作树
`.worktrees/mujoco-direct-control-stage-b`，分支 `codex/mujoco-direct-control-stage-b`。
已读取 AGENTS、阶段 A、S142–S148 报告和原数学、控制搜索、回放及证据实现。
主工作树现有未跟踪文件和历史研究 Store 保留不动。

工程范围：原 `research_analysis` 新方法 `mujoco_direct_control_v1`，使用原
`local_control_search.search` 和受限响应求解，仅替换为克隆 native checkpoint
的多区间回调。优化覆盖全部保持样本，内部裕量不改变冻结阈值。
输出原 `explicit_control_schedule_v1`，通过原 `physical_replay` 完整重放与独立验收。

远端 ls-remote 已核验基线为 904f4932afc46c58853f53156d1a87f460e1fa55。
主工作树原位于 feat/gvs-dynamics@d629a80d0，其环境和未跟踪文件均未修改。

## 公共接口与求解语义

继续使用原 research_analysis，operation=mujoco_direct_control_v1，model_source=mujoco，
operating_point=saved_state，以及原 candidate 和冻结 protocol。
数学模型来源独立于控制器；本例只把历史 NMPC 实际张力作为初始化，不准备 GVS/SoRoSim
动力学图，不运行 NMPC。原生力学、短时输入响应和固定输入结构分析仍可独立调用。

状态来源支持 saved_state，或 execution + update_id。前者必须是候选/配置绑定的完整 native
integration checkpoint，控制优化额外核对其已验证张力前缀；后者支持当前 Store 拥有的
NMPC 执行或完整 physical_replay。在原数学 worker 内只重放并核验所需前缀，之后克隆准确状态。
这也使新结构可从自身完整回放重新进入原生分析，无需先运行一次 NMPC。

新增 control_optimization={source,settings}。source 复用原可执行数学序列或
explicit_control_schedule_v1；settings 直接使用原 LocalControlSearchSettings，要求 v2
及明确 correction_window_s。窗口从 checkpoint 起点至任务终点，必须覆盖全部相关任务样本。
当前 v1 明确支持原 Reach/Hold 三组 norm 约束；不支持的任务/约束、物理或采样网格明确拒绝。
不指定新方法时，旧请求序列化、GVS/SoRoSim、Conic/KKT 和敏感性含义保持不变。

NativeModel.rollout_sequence 每次克隆同一个完整状态，施加实际合法绝对张力，返回起点和
各区间末端的世界位置、速度、时间和实际输入。一次试探不能修改下一次初态；优化期间不保存
每个物理步的全部 96 维状态。完整回放仍使用原后端，并保存原始状态样本。

没有第二个优化器：复用原 search、corrected_tensions、correction_basis、constraint_vectors、
constrained_response_step 和信赖域规则。search 只增加可选求值类型、停止条件及排序回调。
旧完整物理搜索默认行为不变；native 以最大有符号归一化违反量排序，进入可行区域后仍区分裕量。
原生回调始终 accepted=false、independent_evaluation_executed=false；其 valid_complete
仅表示该预测窗口数组完整，不能解释为完整物理任务通过。

优化通过原 Store 保存完整合法 schedule，返回 control_schedule_reference；主 Agent 可直接
调用原 research_plan action=physical_replay，指定同一候选和该 source。
schedule 本身保持 task_acceptance=unmeasured，只有原完整独立评价可建立实际通过结论。
正式新 Study 需冻结 analysis、physical_replay、control_correction 能力和相应共享预算。

## 实际有界工程验证

使用 S142 原增刚执行 3c78b551965f443abd966bfb68b969dd。世界目标 [0.29,0.035,0.19] m；
终点/保持位置限值 10 mm；保持窗口 [0.30,0.35] s 的六个含端点样本速度限值 0.02 m/s。
六路顺序 near_t0、near_t1、near_t2、far_t0、far_t1、far_t2，均为绝对张力 0–8 N。
控制/采样周期 0.01 s、物理步长 0.0005 s、原 implicitfast。

新 engineering_numerical Store 为 runs/mujoco-direct-stage-b/store，配置为
runs/mujoco-direct-stage-b/study.json，从原冻结输入构建，候选参数与增刚结构相同。
独立上限：数学求值 4、完整物理启动 2、public operations 40，Provider/NMPC/PPO 为 0。
没有重启 S142、启动 Provider 自主 Study、重置或借用阶段 A/S142 预算。

原 0–0.30 s 前缀只核验一次：30 个样本、600 个物理步。
原控制预测对历史六个保持样本的最大位置逐分量差为 **0**，速度差 **1.56e-17 m/s**，
时间差 **2.22e-16 s**。优化输入只含截至起点的历史运动状态、初始化控制和冻结任务；
没有把未来实际位置/速度作为优化输入。

参数化为 [0.30,0.32,0.34] s 三个结点 × 六腱，共 18 个系数，映射至完整 35×6 时间表。
前 30 区间逐项不变。系数上限 0.5 N、初始信赖半径 0.1 N、差分 0.005 N、
最小半径 0.0001 N；最多 80 次尾段求值、4 次迭代，内部目标为原阈值内 5% 裕量。
实际最大张力改动仅 **0.007747295 N**，完整控制合法，最大一路约 7.920831217 N。
没有向前扩展窗口或继续扫描参数化。

实际开始两次局部响应迭代：第一组完成 18 列响应及一个 SLSQP 提案；第二组第 3 个差分点
满足内部裕量，立即停止。合计 **1 基线 + 21 差分点 + 1 响应提案 = 23 次尾段积分**。
所有合法实际探针参与排名；最佳点为 native-rollout-22，是差分探针，具有实际非线性响应。

| 层次 | 结果 |
| --- | --- |
| 线性局部提案 | 最大有符号归一化违反约 −0.0500000000 |
| SLSQP 状态 | success=true，7 次内部迭代，无全局最优证明 |
| 该提案的 native 非线性验证 | −0.0498710073；最大速度约 0.019002579853 m/s，已过原界但略未达内部裕量 |
| 最佳 native 实际预测 | −0.0576705908；最大速度 0.018846588184 m/s |
| 原完整回放及独立评价 | accepted；没有用局部求解成功替代实际验收 |

## 全部样本与原冻结验收

以下来自原/最佳输入的**两次新完整回放**，均从冻结初始化状态执行 0–0.35 s。
两条回放的保持位置/速度与对应 native 预测逐分量差均为 **0**；
canonical 时间与 engine 时间差最大 2.22e-16 s。

| t/s | 原位置误差/mm | 优化位置误差/mm | 原速率/(m/s) | 优化速率/(m/s) |
| --- | ---: | ---: | ---: | ---: |
| 0.30 | 2.948836 | 2.948836 | 0.009087739 | 0.009087739 |
| 0.31 | 3.037133 | 3.032813 | 0.010172697 | 0.009367858 |
| 0.32 | 3.110052 | 3.093595 | 0.004896022 | 0.003398892 |
| 0.33 | 3.122254 | 3.086128 | 0.003691849 | 0.006103668 |
| 0.34 | 3.091917 | 3.027744 | 0.009927944 | 0.012674149 |
| 0.35 | 3.136442 | 3.034395 | 0.022849090 | 0.018846588 |

最大违反量和保持窗口整体条件改善，**不是每个时刻速度都降低**：0.33、0.34 s 的速度有所增加。

| 原完整冻结指标 | 原控制 | 优化控制 |
| --- | ---: | ---: |
| 终点位置误差/mm | 3.136442 | 3.034395 |
| 保持最大位置误差/mm | 3.136442 | 3.093595 |
| 保持最大速率/(m/s) | 0.022849089711 | 0.018846588184 |
| 最大正归一化违反量 | 0.142454485532 | 0 |
| 保持速度裕量/(m/s) | −0.002849089711 | +0.001153411816 |
| 保持覆盖 | 6/6 | 6/6 |
| 实际张力违反/N | 0 | 0 |
| solver exception | 0 | 0 |
| 完整控制更新 / 物理步 | 35 / 700 | 35 / 700 |
| 原组合评价 | valid_failure：保持速度 | accepted |

位置、task evaluator、实际输入边界、完整性、覆盖、数值有效性及 solver 条件全部重新评价，
没有继承历史前缀验收状态。相比阶段 A 单区间修正的 0.020000528285 m/s，
阶段 B 整个保持最大速度再低约 5.7695%；阶段 A 覆盖范围较小，不能当作完整任务评价。

## 计算成本、持久化及保留结论

| 计算 | MuJoCo 模型加载 | 显式 forward | 物理步 | wall/s |
| --- | ---: | ---: | ---: | ---: |
| native：一次前缀 + 23 尾段 | 1 | 313 | 2900 = 600 + 23×100 | 0.198384 内核；1.265690 worker |
| 原控制完整回放 | 1 | 原后端范围 | 700 | 1.191098 worker |
| 最佳控制完整回放 | 1 | 原后端范围 | 700 | 1.096355 worker |
| 合计 | 3 | 不混同内部调用 | **4300** | **3.553143 worker** |

本次原生 mechanics 读出为 0；313 次是显式零步进 forward，不把 mj_step 内部运算另计。
工程入口 elapsed 11.844707 s，Store numerical_s 4.202150 s 含候选构建等原范围，
与 worker wall 有包含关系，不能相加冒充总 CPU。实际数学额度 **1/4**、物理 **2/2**、
public operations **4/40**；Provider、自主 Study、PPO、闭环 NMPC、额外确认均为 **0**。
单次本机 wall 不证明实时性。

每个已完成尾段通过原 checkpoint 回调保存可序列化进度及累计成本，返回前严格检查 JSON。
原 Store/worker/receipt 继续负责恢复与计费，没有新增 checkpoint 框架。
重复原 analysis operation key：0 新计算、0 新数学额度、Store 状态不变。

实验冻结在提交 3bdae230。审计提交 0431305d 修复裕量排序、迭代计数、回放状态入口和保护读取。
用**同一组已记录响应**核对最终搜索的逐次系数，仍选同一 23 点及最佳完整控制，没有追加仿真。
原不可变结果的 optimization_iterations=1 实际指完成响应步；最终代码分别记录开始迭代 2、
完成响应 1，不改写历史 artifact。

本阶段没有失败的数值 worker 或未决执行。初次检查曾使用错误 unittest 类名，以及未指定
调查 question 的双结果 Reporter 调用，原接口正常拒绝；改正调用后通过，未放宽 Schema 或增加科学计算。
阶段 A 原序列化失败、S142 失败与历史成本均保留。
S142 Store 全程只读 immutable/query_only；前后大小/mtime 和 events/artifacts/calls
478/532/73 不变，原状态 stopped、pending=null。阶段 B 工程 Store 也已按原 STOP 封存，
pending=null、occupied={}，没有自动进入阶段 C。

## 调用链审计与代码量

| 环节 | 实际接通与边界 |
| --- | --- |
| 候选 → 原生动力学 | 原 construct/编译链及具名状态；不同结构不能借用基准 checkpoint |
| 数学模型来源 | 独立选择 native；阶段 A 力学、输入与固定输入结构分析独立保留 |
| GVS/SoRoSim 数学 | 旧序列化、模型含义、Conic/KKT/敏感性保持原义 |
| 原生轨迹 → 优化 | 同起点克隆、全部保持样本、少量系数、原搜索及受限响应求解 |
| 优化 → 执行 | 原 explicit schedule、候选/任务/模型/时间网格/张力绑定、原 physical_replay |
| 完整执行 → 数学 | 补齐 owned physical_replay 的实际前缀入口，不要求先运行 NMPC |
| 完整独立评价 | 原 evaluator/assemble_acceptance，35 区间和实际输入重新评价 |
| L0/L1 | 原方法目录、compact_result、ResultCard、Reporter、Decision Brief；本项数学视图 8036 bytes |
| L2 | 原 same_structure_controls 可比关系；数学结果增加到最佳 schedule 的一个关联字段 |
| L3 | 原 JSON Pointer/range；补齐通过后对该回放关联 source/raw/evaluation 的读取，未关联证据仍受阻 |
| Agent 后续决策 | 可发现方法，摘要含最差约束时刻、原/新数值、求解/验证状态、成本、引用和下一步动作 |

完整 L0 约 49.7 KB，包含既有目录及上下文；本项数学视图约 8.0 KB。
默认视图没有完整张力序列、integration state、96 维状态、Jacobians 或迭代数组。
主 Agent 自主科研，原 Reporter/子 Agent 按需解释，F0–F2、L0–L3 和正式读证据义务均保留。
没有强制新 LLM 汇总步骤；agent.py、reporter.py 不变，research_context.py 仅增加 1 行。

相对阶段 A，11 个生产文件 **增加 295 行、删除 72 行、净增 223 行**（含原设置类移动）：

| 文件 | 增/删 | 职责 |
| --- | ---: | --- |
| extensions/tendon_family/mujoco_analysis.py | +22/−0 | 多区间克隆积分，checkpoint 保留核验前缀 |
| tools/research/native_control.py | +131/−0 | 原搜索的原生求值适配、任务/窗口语义和解释；不另写优化器 |
| tools/research/native_analysis.py | +10/−2 | 新方法分派、适用性和统一简洁摘要 |
| tools/research/local_control_search.py | +15/−11 | 可选停止/排序/求值类型，及时保留求解状态及迭代成本 |
| tools/research/analysis.py | +19/−1 | 原预算/worker、source 准入、Store schedule 交接和进度 |
| tools/research/contracts.py | +62/−43 | 复用 v2 设置，明确 native-control 请求，保留旧序列化 |
| tools/research/numerics.py | +18/−5 | owned 完整回放实际前缀作为 native 状态来源 |
| tools/research/task_constraints.py | +11/−8 | 原数学目录、前提及适用性 |
| tools/research/evidence_views.py | +3/−2 | 重优化性质、控制来源和证据链接 |
| tools/research/research_context.py | +1/−0 | 原 L2 数学结果 → 控制源 |
| tools/research/state.py | +3/−0 | 通过后读取该回放已关联原始证据 |

physical_replay.py、control_correction.py、research_tasks.py 无需修改。
新增定向测试文件 97 行、一个显式工程案例入口 148 行。
没有第二套 Store、预算、长期状态、Reporter、Agent、求解器、schedule Schema，
没有新增 SHA/digest 算法、manifest 系统、复杂恢复协议或兼容层；导出复用 core.export。

## 验证及证据入口

**12 项不同定向单测通过**：4 项新原生控制边界/已记录响应复核/回放再接入/保护读取；
3 项旧搜索；2 项旧 native 身份/owned 前缀；真实 GVS 初态线性化 1 项；
原证据读取模式 1 项；原候选数学目录 1 项。没有重跑阶段 A 全部 23 项或全仓库测试。
另一次真实工程案例覆盖原数值复现、受限 native 优化、合法完整序列交接、两次独立验收、
原 worker/Store receipt、Reporter/L0、L2 可比关系和 L3 原始采样读取。git diff --check 通过。

证据在 [evidence/mujoco_direct_stage_b](../../evidence/mujoco_direct_stage_b/)：

- [summary.json](../../evidence/mujoco_direct_stage_b/summary.json)：可比指标、结果/控制/回放引用、原预算及摘要；
- [delivery_checks.json](../../evidence/mujoco_direct_stage_b/delivery_checks.json)：最终代码零新仿真审计、L0–L3、保护读取和迭代字段说明；
- [study/](../../evidence/mujoco_direct_stage_b/study/)：原 Store 导出，含不可变原始数学结果、完整输入、原始回放、独立评价、调用和账本。

数学结果 2215b856… 的 /native_dynamics 含原/最佳输入、六样本预测、试探与成本；
控制引用 daf7c908…，原/优化完整回放 c6945454… / 0b940626…。
完整引用及 JSON Pointer 在 summary，未用手写身份替代原 Store 身份。
案例入口 [tests/research/mujoco_direct_stage_b.py](../../tests/research/mujoco_direct_stage_b.py)
针对已封存 Store 再运行会退出，不能当成新实验。

## 瓶颈与下一项科研条件

本例没有证据要求增加自由度或提前窗口：18 系数及很小张力修正已过原任务。
短时计算成本低，不能外推为长时域、高维或接触任务同样容易。
首组响应秩为 18，但子空间条件数约 **7.08×10⁴**，存在弱方向；单侧 0.005 N 差分
和有限信赖域不提供区域导数可靠性界。应保留线性预测/非线性验证和有界停止，而非无限增加迭代。

未建立优化后结构能力排名、结构梯度、全局最优、控制鲁棒性或跨模型泛化。
本阶段未做结构变体配对；新结构应通过原构建和 schedule 初始化绑定，独立产生其合法实际前缀，
再在相同任务、参数化、预算和停止规则下优化。新增回放状态入口支持复用同一流程；
不能移植基准结构 0.30 s 状态或继承其通过结论。

**已经具备为新自主结构—控制 Study 提供数学、执行、评价和证据接口的工程条件。**
正式 Study 仍需自己的冻结任务/设计域、方法授权、共享预算及 Provider 授权，
由主 Agent 自主选择科学动作。最有价值的下一项研究是公平预算下对合法结构分别生成真实前缀、
重新优化控制并独立评价；本阶段没有启动它，也没有证明结构最优能力。

提交：3bdae230 为已执行工程实现；0431305d 为调用链/裕量/读取审计修复；
本报告和原 Store 导出随后单独提交，均普通推送到阶段 B 分支。
