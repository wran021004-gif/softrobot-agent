# Softrobot-Agent 阶段 A 交付报告

日期：2026-11-04（Asia/Shanghai）。仓库 `wran021004-gif/softrobot-agent`。

本地开发分支：`codex/stage-a-math-handoff-20261104`。独立 worktree，未改目标分支，未合并 main。
开始时通过 GitHub 接口核对远端 `codex/m1-knowledge-physics-reasoning`：HEAD 正好为指定基线 `52f8663a6642e35232286e403bb0731334c825ab`，没有后续提交被覆盖。原工作树当时干净。
报告生成前代码 HEAD：`f9f71994d43da410e5e2d8c91226010230372ca7`。最终文档提交和完整 SHA 列表见 `stage-a-commits.json`。

已完成核心接口修复、主动/被动 SDK Mock 分段交接验证、真实被动参数—模型—观测闭环，以及既有 INVALID 证据的只读诊断。**没有调用真实 Main Provider，没有启动正式 Benchmark/训练/阶段 B。回归并非全绿，失败及验证边界完整列在下文。**

## 1. 接口审计矩阵

| 环节 / 权威 | 主动基线 | 被动基线缺口 | 本次处理与边界 |
|---|---|---|---|
| TaskDefinition / 注册 evaluator | Reach/Hold 的冻结采样、位置、速度及实际张力输入 | `constraint_observations` 有动态事实，通用 `analysis_requirements` 仍为空约束、静态语义 | 保留空约束保护；从同一 TaskAdapter 增加发现用动态事实，附冻结来源、窗口、完整 bound 定义及资格规则。没有向 GVS/Conic 填入不支持的动态问题 |
| 物理 / 参数能力 | 理想绝对张力、合法输入集；控制权重与结构区分 | FamilySpace 展示写死 ideal_tension，并列出主动初始化作用 | 被动明确无主动控制、固定 payout、单侧限长、容量资格与实际张紧/松弛需观测；主动语义保持 |
| mathematical_method_view → L0/L1 | 原 T1/Direct、Conic 与机制入口 | 动态失败指标无法关联机制方法，静态说明过时 | 加入动态约束映射和 finite_time_response；保留 planning_status、预算/来源/授权及独立验收边界 |
| V4 / Provider Schema → 编译 | 显式结构/控制科学选择 | 动态分支允许不匹配载荷，配对干预限制不够明确 | 完整任务固定为 finite_time_task_violation、所有冻结工况及冻结初态；合法 tendon 名、两臂选择和成本明确；不替 Main 选参数、步长或路线 |
| AnalysisRequest → Worker | 原请求、预留和执行器 | 底层已支持动态积分，发现说明未跟上 | 复用原 Worker 与 shared budget；同一 dynamic_cost 用于发现和预检，真实 episode/model/step 成本保留 |
| Evidence / Reporter → 下一轮 Main | 已有方向、来源及解释 | 最终 L0 白名单会丢弃新增动态与 INVALID 事实 | 修复原最终投影白名单；Reporter 实际 Mock HTTP 输出及结果事实均进入下一轮 wire；解释不构成证书 |
| Main → generate → Replay | 原生成 / 验收链 | 被动完整方向建议含公开 Schema 删除的 control_weights | 新生成建议去掉无效被动控制字段；公开 parent + changes 路径验证不改其他物理参数；重新建模、不继承成功 |

真正缺陷是上述展示、Schema、成本与最终投影脱节。接触/混合主动被动物理不支持、授权缺失、预算不足、非光滑或不合格动态样本，仍保持拒绝或条件状态，不当成待绕过的 Bug。

## 2. 修改文件、函数与兼容性

| 文件 | 主要函数 / 变化 | 兼容性 |
|---|---|---|
| `tools/research_tasks.py` | structure_task_view；新增 dynamic_constraint_view、qualification_diagnosis；只投影冻结定义和已有记录 | 不改 evaluator、acceptance 或通用主动求解输入 |
| `extensions/tendon_family/family_space.py` | decision_summary、parameter_capabilities；被动物理作用、无效控制参数、payout 对应腱数 | 保留严格 payout 键等式；主动分支保持 |
| `tools/research/optimal_capability.py` | family_analysis_parameters；被动链接现有机制方法，纠正主动输入解释 | 不增加参数注册表或授权 |
| `tools/research/task_constraints.py` | mathematical_method_view、mathematical_research_view；动态发现事实、方法相关性 | 不把动态条件伪装成 affine kernel 约束 |
| `tools/research/scientific_intent.py` | scientific_actions、question_schema；动态目标、工况与配对干预条件 | 兼容已注册被动 v1；只有唯一确定的执行字段由原编译器补齐 |
| `tools/research/structure_research.py` | dynamic_cost、finite_time_discovery、prepare_context、discovery、dynamic_summary；保留诊断和真实成本，过滤无效生成字段 | 不更换数值算法、资格检查或差分可靠性规则 |
| `tools/research/research_context.py` | mechanism_direction_view、information_flow_brief；最近资格诊断和最终 L0 白名单 | 主动 parameter_domains 保留兼容；被动域详情按需查询 |
| `tests/research/test_stage_a_handoff.py` | 8 项合同、非法输入、SDK 路由和真实参数重建检查 | Mock 不作为科学结果 |
| `tests/research/test_passive_program_v2.py` | 原准备夹具可在创建前指定隔离验证预算 | 默认行为不变；不改任务阈值 |
| `tests/research/stage_a_validation.py` | 一次性、先记上界的工程验证脚本，调用原 SDK / Worker / generate / evaluator | 不是第二套正式 Runner；发现既有 journal 即停止，不重跑积分 |

没有修改 mechanism_registry / DifferentiationRouter 的物理含义或算法；复用其已有目标、方法和资格保护。没有改冻结任务文件、正式 Study、原 M1 Store 或任何历史结果。

## 3. 数学能力矩阵

`I/D/O/C` 分别为 inspect / differentiate / optimize / compare；支持表示可准备研究请求，仍需原始逐请求准入。

| 能力 | 适用物理 | 操作 | 关键前提 / 不可推断 |
|---|---|---|---|
| Jacobian、惯性、编译刚度/阻尼、主动方向驱动力及有界瞬时加速度 | 各量在原 registry 标明的主动或共享几何范围 | I/D/O/C；方向/离散量例外 | 注册连续有效参数、状态/绝对输入明确、合法重建和两尺度信号；不是完整控制或动态通过 |
| 腱长残差、payout、张力拟合、KKT、约束活跃集合 | 被动固定 payout 硬静力模型 | 连续标量 I/D/O/C；活跃/边界/松弛集合 I/C | 几何事实可读；不合格平衡、活动集变化或非光滑时不生成可信普通梯度 |
| 切线刚度/柔顺、重平衡位移 | 被动静力 | I/D/O/C，标量化及条件检查 | 合格平衡、所需 LICQ/严格互补/数值一致性；硬静力不代表软限长有限时间任务 |
| 单侧方向材料响应 / 局部可行锥 | 被动约束边界 | I/C | 保留单侧不等式和 QP 状态，不当成普通光滑导数 |
| finite_time_task_response / finite_time_task_violation | 原注册被动动态任务 | I/D/O/C | 所有冻结 load episodes、完整时间网格、全部资格与约束；有机制配对要求时 Main 显式选合法消融、支付两臂成本 |
| Native T1 / Direct 与保存的 T2 | 主动 Reach/Hold 等各自支持范围 | 原控制优化与保存对比入口 | 合法控制来源、冻结输入/时间/候选；T2 不启动隐含控制搜索；独立 Replay 才提供验收 |
| affine Conic / 敏感性 | 原支持的主动采样问题 | 原优化/敏感性入口 | 浮点数值证据，不是被动动态后端、全局物理证明或严格下降证书 |
| 拓扑 / 腱数 / 网格 / 控制权重 | 冻结授权范围 | 生成或合法离散比较 | 不当作普通连续纯结构导数；数值离散参数与控制参数保持区分 |

## 4. INVALID 的真实只读示例

来源：已有工程 Study `C:\Users\gugugaga\Documents\Codex\2026-11-03\files-pasted-by-the-user-codex-2\work\softrobot-agent\runs\u3-p3-cells2-40b313b7\platform.sqlite`；结果 `afcce1532499c19e76cf67c5fb002103a022ac132868ef10bfda8ee041cd897e`，原始观测 `d8d7e2d02a444157fb066f85eb2d63e86fead696495c2410050dc2cede4d4bd8`。

原 evaluator 返回 `DYNAMIC_STAGE_NOT_QUALIFIED:low`；诊断类别为 `dynamic_stage_qualification`。无载阶段已合格，低/中载阶段的 static_balance 未合格；高载与恢复还存在 tip_speed、monitor_speed 不合格。基准/消融两臂、正反工况共保留 **16 条阶段资格失败**，每条有原始 pointer、冻结 rule 和已测 checks。L0 只取前三条并给出总数，完整事实留在 L1/L2。

Main 可读保存阶段对照，或自行选择有前提的静力残差、张力、KKT/切线研究，也可重新设计、生成或停止。旧冻结实现/范围不满足时显示 blocked，不能把它说成已经可执行。静力梯度还须另行通过静力平衡和光滑性检查。

没有生成完整任务 signed_task_gap、普通动态任务梯度、下降保证或合格机制证书。没有新积分。原工程数据库审计前后 SHA-256 相同：`ea54dc7dcb1cea473583da7d8758f02b8595cd91295e686c66b44006a1cb8109`。这份历史失败仅作诊断，未作为获胜结构或新任务通过注入。

## 5. 被动拓扑与 payout

| 冻结对象 | 声明腱数域 | 实际授权执行腱数 | payout / 实际 tendon / MuJoCo tendon / 主动输入 |
|---|---|---|---|
| 本轮轻量 v2 工程夹具 | 1–12 | 1 | 1 / 1 / 1 / 0，编译通过 |
| 已存 PHS 工程 Study | 1–12 | 2 | 2 / 2 / 2 / 0，编译通过 |
| 已存 P3 cells=2 工程 Study | 1–12 | 2 | 2 / 2 / 2 / 0，编译通过 |
| 已存 P3 cells=4 工程 Study | 1–12 | 2 | 2 / 2 / 2 / 0，编译通过 |

这些**真实冻结 Study 都是固定腱数**，所以没有放宽 payout 键集合，也未臆造其他腱数的放绳长度。声明域大于执行域不等于科学不可行。源目录某个未冻结 FamilySpace 的 2–4 腱声明不能代替冻结 Study 的授权；未来若真正冻结跨腱数执行域，必须先提供对应条件 payout 域。四项构建检查均无积分，详见 `stage-a-topology.json`。

## 6. 实际 SDK Mock wire、Schema 与结果交付

所有 Main 动作均预写；使用真实 Strands SDK 请求组装、Mock HTTP、原工具 Schema 和原 Store。Reporter 也走真实请求/响应处理，并使用其 source_catalog 返回带来源的非权威解释。

- 主动：`stage-a-active-wire.json` 证明机制发现、合法 T1/Direct 可发现、diagnose → V4 → 数学固定事实 + Reporter → 下一次 Main；`stage-a-active-adopt-wire.json` 证明 Main 显式 parent/changes → 原 generate 新候选。此组数学值明确为 synthetic，只证明接口。
- 被动：`stage-a-initial-wire.json`、`stage-a-difference-wire.json` 包含真实 Worker 数学结果，下一次 Main 实际请求得到方向、可信度和 Reporter 解释。`test_stage_a_handoff` 独立验证被动 SDK parent edit 不改变其余物理字段。
- 同一差分请求经公开 Schema 校验、唯一字段展开、MechanismStudy/AnalysisRequest 和预算预检，成本为 5 次数学评价 / 5 次构建 / 5 个 episodes / 2,500 步。可选单腱配对 inspect 的成本为 2 构建 / 2 episodes / 1,000 步。
- 非法参数路径、错误模式、错误工况/目标、过小预算、非法消融名及外来比较候选均在预留/Worker 之前拒绝。

**如实保留中断：** 第一次被动采纳 Mock 把旧方向中的完整请求原样返回，含被动公开 Schema 不接收的 control_weights，Mock 响应前本地校验失败。之后 SDK 保守地拒绝恢复该快照。原 Mock 失败记账保留，未伪造 HTTP 响应、未重写 SDK 快照或重置科学成本。数值验证复用已有差分，通过原 Plan/compile/Worker API 完成生成与复算；没有重跑差分。后续代码过滤无效字段，并以已验证的显式 parent/changes 表达采纳。

因此，本轮证据是**分段完整交接 + 真实数值闭环**，不宣称已重跑一条全程无中断的被动 SDK 科研会话。最终一次性脚本已去掉临时恢复分支；未为漂亮演示追加积分。

### 上下文和字节数

- 对完全相同 Store/state 的只读核心 L0 投影，状态身份 `6005e4d6bcbb610bf69ad24be01c6fad4d92e7f3a61a6982cf2957cec679a116` 相同：UTF-8 紧凑 JSON 从 **19,988 B → 21,688 B**。
- 两个分别绑定原实现身份、但冻结 task / 参数 / 物理设计完全相同的实际 SDK Mock 请求：**58,211 B → 59,679 B**；不是拿移植后的 Store 绕过 root/authority 绑定。严格同状态对比来自上面的只读 L0，wire 对比来自等价冻结输入。
- 新增信息是完整动态目标、配对干预/每评价成本、实际约束关联和资格诊断入口。大于 120 字符的重复对象计数为 7 → 7。
- 被动参数域详情改为已有证据查询；没有新增完整 trajectory、状态向量、Jacobian/KKT 数值矩阵或完整有限差分记录到 L0。实际 raw 数据仍在原 L2/L3。未宣称 token 节省，也未外推到大型 M1 Store 性能。

## 7. 最小真实数值闭环与全部成本

冻结任务来自原 `configuration_v2` 工程夹具：0.5 s、1 ms 步长、一个工况、无载/低/中/高载/恢复程序；同一 task/阈值贯穿。改变一个已授权连续结构参数 `segments.0.young_pa`：**7,200,000 → 7,330,000 Pa**。其他设计参数经 resolved_request 对照保持相同；重新构建后的 model identity 确实变化。

| 阶段 | 数学评价 | 模型构建 / episodes | 实际积分 |
|---|---:|---:|---:|
| 初始真实 inspect | 1 | 1 / 1 | 500 |
| 一个参数的两尺度差分（公共基准 + 四个探针） | 5 | 5 / 5 | 2,500 |
| 原 generate 后新模型真实 inspect | 1 | 1 / 1 | 500 |
| 独立原 evaluator Replay | 单独物理调用 | 1 / 1 | 500 |
| 数值闭环合计 | **7** | **8 / 8** | **4,000** |
| 原 v1/v2 相关回归 | 另 1 次配对数学 inspect；其余为执行夹具 | 4 个积分模型 | 2,300 |
| 本轮所有新增持久化积分记录去重合计 | **8 次真实数学评价（含原回归）** | 不把配对父记录重复计入 | **6,300** |

发现/编译/SDK 合同测试及四项拓扑构建没有积分。原 FamilySpace 模型编译测试另有无积分模型构建。没有训练、完整 PHS/P3 运行或隐藏控制优化。

两尺度相对差异约 0.0002536，方向一致，观测信号大于原信号地板；这不是严格误差界。完整任务 signed gap 从 `-0.999083396789234` 变为 `-0.999099281404189`（越小越好）；相应已测位移约 **9.16603210766e-05 → 9.00718595811e-05 m**，下降约 **1.7330%**。两次数学观察的正违反量都为 0；因此不能说实现了“失败转成功”。新候选独立 Replay 被原 evaluator 接受，但仅对这份宽松轻量工程任务成立；初始结构没有另做独立 Replay。

数值 Study `u3-wire-d2b4c89d1b` 的原台账 backend_solves=8，数学 charged evaluations 为 1+5+1，所有内部积分均计入原预算；legacy worker_calls=0 不代表没有子进程，实际有三个 analysis Worker 和一个独立 Replay Worker，见原 boundary/日志。详细 forward、状态保存、episode 和实际 wall 成本均保存在 `stage-a-numerical.json` 与工程 Store。

实现身份边界：初始/差分运行于 `195f41f`；补丁 `0c25bca` 仅修正生成展示后完成生成及复算。该工程会话的原 freeze 标记仍保留 `195f41f`，没有改写历史收据；后段实际文件树差异及执行命令保存在提交与日志中，数值求解/任务/物理模型未改。它不被包装成单一代码身份下的无中断认证实验。

## 8. 回归结果与基线问题

主回归：**87 项用例，72 项通过，8 项断言失败，7 个用例报错（12 条错误记录，含子用例）**；未标记跳过。原始完整结果见 `stage-a-tests.json/.log`。后续定向补测保留原记录，不覆盖主结果。

- Stage A 最终合同测试：8/8，覆盖动态事实与 affine 隔离、真实参数作用、Schema/编译/成本一致、非法路径/模式/工况/预算、配对干预、外来候选拒绝、实际被动 SDK 生成及 wire 保留。
- 主动与被动 V4、机制两尺度、方向归属与 generate、Reporter 非证书边界、科学结果绑定恢复等相关主路径通过；v1/v2 真实执行与现有配对执行器回归通过。
- 在指定 `52f8663` 独立基线逐项复现了八项原断言失败：旧 L0 禁词/大小限制，旧控制 Schema/拒绝状态预期，FamilySpace 压缩比例、能力目录计数 27/28、缺失本地经验技能等。没有为让它们变绿改测试或放松生产门槛。
- 原 Reporter 测试替身 `artifact=lambda ...` 不接受已有 paths 参数，导致两个测试/七条子错误，基线相同。
- 两个旧冷启动/交接夹具先缺稀疏 checkout 中的 MATLAB 源文件；补齐原跟踪路径和原 readiness 文件后，继续被正式数学授权门槛拦截，基线相同。没有关闭该门槛。
- 临时目录权限问题的资格冻结测试在无沙箱补测通过；空 Store 的 read_snapshot 测试随后暴露基线已有“只读打开不存在数据库”错误。没有重构 Store。

原封存 M1 Store 未打开修改；INVALID 审计只读另一个工程 Store，并验证哈希未变。没有为了任何旧失败修改冻结物理模型、目标、阈值或评价权威。

## 9. 未完成事项、交付与下一阶段建议（不执行）

当前没有真实 Main 自主科研能力证据；Mock 决策和 synthetic 主动数值均不能支持这种结论。没有新的 PHS/P3 正式通过结构、配对机制认证或硬件/鲁棒性结论。大型 M1 Store 性能和一条修复后全程无中断的被动 SDK 数值会话也未追加验证。

本地代码和证据可审查。发布最初被自动审批拒绝，随后用户明确授权发布本阶段独立分支。直接 Git 连接被重置或无法连接，因此改用已连接的 GitHub 接口发布最终代码树；本地提交历史与远端发布提交分别记录于 `stage-a-commits.json`，未合并 main。可离线审查 `stage-a.patch` 和 `stage-a.bundle`，完整日志及工程 Store 在证据包内。

下一阶段最小建议：另建一份隔离的轻量被动 v2 Study，冻结当前代码/同一夹具后，明确授权 **Main 最多 8 次、Reporter 最多 2 次真实 Provider 请求**；数学评价最多 6 次（一个参数差分 5 + 新结构 inspect 1），加可选独立 Replay，总物理积分上界 4,000 步。Main 自选参数/研究/采纳或拒绝，遇到 INVALID 保留合法诊断及停止自由；达到任一预算即停，不追加。先观察一次自主决策质量，再另行决定是否授权主动 T1/Direct 小窗口或 PHS/P3。需要单独授权真实 Provider、模型与凭据来源及此窗口预算；本轮没有执行，也没有估算或承诺货币价格。

### 本地提交记录

```text
f9f7199 Document Stage A interface audit, real numerical evidence and regression limits
e1f4549 Check foreign finite-time comparison sources before budget reservation
f972777 Keep bounded validation single-use after retaining the interrupted Mock audit
f371838 Verify actual passive SDK parent edits preserve unchanged physical choices
0c25bca Align passive direction generation with public Schema and retain failed Mock evidence
f13f96b Retain original charges when settling local Mock validation failures
f754fc7 Use explicit parent-relative generate input and resume saved numerical evidence
195f41f Add bounded journaled real Worker and SDK Mock structure validation
58e104d Preserve finite-time and INVALID facts through final Main wire projection
a7f3106 Verify passive discovery, dynamic schema costs and SDK request delivery
5418d5c Retain registered legacy passive finite-time schema compatibility
82bb6ca Align passive mechanism discovery, dynamic schema and qualification diagnostics
```

所有运行失败、中断、预算和原始观测均保留；最终 SHA 与包哈希见 `stage-a-commits.json`、`stage-a-manifest.json`。
