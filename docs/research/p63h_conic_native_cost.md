# P6.3-H：Conic → Native 成本对照

本例没有证据支持 Conic 减少成功求解成本或改善最终任务。Conic 控制源通过现有接口准入，但其首次 Native rollout 因接触而中止；短耗时不能解释为加速。Direct Native 有完整的有限预算结果，独立 Replay 仍然失败。

这是 Operator 所有的受控数值研究，不是 Main 自主发现或正式 Benchmark。独立分支 `codex/p6-3h-conic-native-study` 基于已发布 `e980f2d`，继承 C0/C1/C2/F1 和 G0；未重复实现 G0。实验实现冻结在 `3f6de4bec8a55edc03ac969617b3f7f368041674`。后续 H3 是接口修改，未重算或重新解释历史结果。

## 对照条件与 H0 审计

使用原 M3 `reach_hold_b3_050.json`、原 Base-only FamilySpace、原模型和 evaluator。原生成器产生两段、六腱的默认合法候选：段长 0.16/0.11 m；未导入历史成功结构或控制。使用原 pretension baseline、全 DOF 零初态、0–0.5 s 全时域、0.01 s 控制/采样间隔和 0.0005 s physics step。任务保留末端误差 ≤0.01 m、0.45–0.5 s 保持误差 ≤0.01 m、保持速度 ≤0.02 m/s。

A/B 使用同一 Native Response、同一四 knot `[0, 1/6, 1/3, 0.5] s`、24 个有效修正系数、2 N 系数幅度上限、0.01 N 差分、0.1 N 初始半径、0.0001 N 最小半径、最多 200 callback/60 迭代、安全余量 0。仅初始控制来源不同。

现有 `initialize_control(method="capability_sequence")` 已足够：其校验当前 Study/候选/实现/任务/模型/协议绑定、N 单位、六腱顺序、0–8 N 物理边界、零初始增量、完整 50 区间 ZOH 网格、有限值和独立离散重放。生成的 source 是 `explicit_control_schedule_v1`，接受状态仍为 unmeasured。现有回归也验证局部任务失败但数值合法的起点可以保留为诊断控制。

原 GVS/CasADi 构建及 CVXPY 1.9.3 / Clarabel 0.11.1 在实际 Worker 环境可用；实际运行采用既有 `.f3-prestudy-env`，NumPy 2.4.6、SciPy 1.17.1、MuJoCo 3.13.0，三个数值线程设置均为 1。此前曾在本任务 work 目录安装依赖，未用于最终实验。没有修改模型、任务、evaluator、Store 或预算实现。

## 实际结果及费用

| 指标 | A：Direct Native | B：Conic + Native |
|---|---:|---:|
| Native 初始 J | 20.451755 | 不可用：首次 rollout 未完成 |
| 最佳 Native J | 0.539774 | 不可用 |
| 完整 callback / rollout 尝试 | 200 / 200 | 0 / 1 |
| Native model builds | 1 | 1 |
| MuJoCo physics steps | 200,000 | 372 |
| Native kernel wall time | 21.202869 s | 0.086930 s（失败前观测） |
| Native Worker 完整执行时间 | 22.780929 s | 1.236419 s |
| 外层迭代/完成响应步 | 8 / 8 | 未开始有效搜索 |
| 终止 | callback 预算耗尽 | 原无接触适用性检查失败 |
| 独立最终 Replay | 1.292103 s，失败 | 无优化后控制源，未启动 |

Conic 首次 Worker 共 **9.644163 s**，包括首次 GVS 构建、导入、计算及序列化，未漏计模型构建；现有回执没有单独隔离 GVS 构建时间，故该分项为 unknown，不能将总时间减去 kernel 后全部称为构建时间。Conic kernel **0.620006 s**，CVXPY solve wall **0.030858 s**，Clarabel solve **0.006199 s**，12 次迭代、1 次内部 Conic solve。局部 J≈−0.20，全部 13 个声明的采样约束重放通过，最大预测/重放差约 1.46e−15；这只属于局部模型。

A 的 Worker+最终 Replay 小计 **24.073031 s**；B 的首次 GVS/Conic+失败 Native Worker 小计 **10.880582 s**，两者不构成达到相同性能的成本比较。共享生成/准备及控制初始化分开列示。C 的 Conic 原始控制独立 Replay **1.330682 s**，没有计入 B。

Native 在 `[0.1855,0.1860] s` 检测到 `floor` 与 `payload_shape` 接触，距离约 −3.31e−5 m，故保留 `NATIVE_V1_REQUIRES_FINITE_CONTACT_FREE_UNCONSTRAINED_STATE`，不删除约束或换问题。Conic 输入距物理 box 边界至少约 3.02 N，故不能归因为输入饱和。独立完整 Replay C 实际获得端点误差 **0.165863 m**、保持误差 **0.184986 m**、保持速度 **0.717856 m/s**，任务失败。Replay 与 Native 的接触处理适用范围不同，不能借完整 Replay 绕过 Native 的方法准入。

A 的独立 Replay 端点/保持误差 **0.015398 m**、保持速度 **0.030755 m/s**，均仍超标。其控制下界饱和、无上界饱和，系数未触及幅度上限；局部响应虽有数值满秩记录，部分条件数很大，且预算耗尽，不能宣称收敛到最优。

`best_found_J.csv` 从保存历史导出 callback 与已确认 physics-step 曲线，未重跑物理仿真。B 没有完整 callback，曲线为空，未补造 J 或 time-to-success。原 Native history 的 `cost_s=0` 不代表零耗时；缺少完整逐 callback wall 计时，故同 wall-time 成本下的完整曲线为 unknown。`numerical_summary.json` 保留全部指标、原引用和限制。

## 账本、恢复与范围

整个受控 H1/H2 Study：23 次原 mathematical evaluation charges、6 次独立 Replay、0 Provider 请求；5 次完整 Native 搜索合计 1,000 callback，另有上述 1 次失败尝试。总测量 numerical time **173.356088 s**：分析回执 160.675719 s、Replay 回执 7.978330 s、控制初始化累计 0.957683 s、生成及其他准备 3.744356 s。内部求解次数和账本 evaluation 单位不同，未混算或重复收费。T2 只聚合，额外 Native builds/rollouts/steps 均为 0。

补取旧回归 fixture 时，Git sparse-checkout 清理了部分 ignored runtime 侧文件。原 Store SQLite 的内容寻址结果、费用和身份仍存；备份后按其原 meta 恢复完全相同的本地授权索引行，使用原 recover 结算已完成的 pending Worker，未重跑、重置或追加额度。侧索引由 Store 重建；分源初始化 wrapper timer 和部分逐 callback 进度文件无法恢复，明确为 unknown，累计初始化和全部原执行回执费用完整。详见 `runtime_recovery.json`。这一缺口限制精细分项成本归因。

研究已经通过原 engineering closeout 停止；余量不再使用。完整结果经原 `core.export` 保存至 `evidence/p63h_conic_native/immutable_artifacts.tar.gz`，配套 archive manifest 可逐内容哈希复核。未自动合并或开启下一 Study。

Main 接口新增独立问题 `question_type="bounded_control_initialization"`，确定性编译到原 `task_capability + sampled-affine-conic-minimax-v1`，固定使用当前初始 GVS 模型和完整冻结任务。它不执行初始化或 Native；Main 后续可显式选择 capability_sequence。原 `control_feasibility` 仍为 Native T1；新入口保留原授权、依赖、预算和适用性检查。

定向验证最终覆盖 82 个不同测试：80 项主回归、5 项末次入口/成本检查（4 项复测）及 1 项新增 Conic Main Mock wire 检查，最终均通过。逐日志及初次 fixture 修正保留在证据目录；Mock 计费不属于本研究科学账本。归档 91 个成员逐哈希核验通过，A/B 完整请求仅 source 不同，成本总和核对通过。
