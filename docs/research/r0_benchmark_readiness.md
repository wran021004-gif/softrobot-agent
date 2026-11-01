# R0 九任务准备度审计与 M1 V4 准备

基线：`codex/r3-b-c1-1-task-objective-semantics@0425cb6a3e3bf9d9afd9885e10eca7d387e4b7c1`。
准备分支：`codex/r0-nine-task-benchmark-preparation`，独立 worktree：`D:/softrobot-agent/.worktrees/r0-benchmark-preparation`。
日期：2026-11-01（Asia/Shanghai）。结论只覆盖源码、可读取历史证据和离线接口检查，不包含新物理结果。

## 结论及证据口径

M1 可以在现有接口下准备新的盲测 V4 Study；本轮只冻结待授权准备对象。M2、M3 的 Reach/Hold 接口可复用，但仍须分别准备，M3 还保留原开发协议级别。M4–M6 的原 Native direct sequence、独立 Replay 和验收路径存在；V4 `control_feasibility` 当前固定选择 T1，而这些任务明确不适用 T1/T2，不能标为完整 V4 决策适配。C1、PHS-2D、P3 都存在完整任务接入阻断，未在本轮实现。

证据等级按原始记录判断，不以 Trace 的 PASS 字样升级：

| 任务 | 原历史证据等级 | 实际读取来源 |
|---|---|---|
| M1 | 原冻结注册协议，三条件联合 SELECT | 原 private Store 中 selected 联合对象、3 个 Replay、候选配置、控制与原始采样、完成回执和 SELECT 事件 |
| M2 | 原冻结注册协议，三条件联合 SELECT | 同上，3 个真实 COM 外力条件 |
| M3 | **开发草案通过**，虽有 SELECT 记录，未获正式 Benchmark 协议批准 | 原 Store 的单项 SELECT、Replay、控制、配置和采样 |
| M4 | 原冻结注册协议 SELECT | 原 Store 的 timed tracking Replay、控制、配置和采样 |
| M5 | 原冻结注册协议 SELECT | 原 Store 的位置/有向工具轴 Replay、控制、配置和采样 |
| M6 | 原冻结注册协议 SELECT | 原 Store 的刚性工具、有向跟踪、逐物理步无接触验收和控制来源 |
| C1 | 原四个独立单项协议通过，操作者选择；**无统一异构联合 SELECT** | `runs/c1_20261029` 的四个 Store、配置、控制、物理采样、审计和 `selected.json`；该文件只有 label/reason |
| PHS-2D | 原十工况开发协议通过，含原独立/半步长/扰动检查；无正式 SELECT | 原 round3b Store、独立开发 evaluator、冻结协议、40 个结果引用和实际物理样本 |
| P3 | 原渐进刚度开发协议通过，含机制对照和原独立检查；无正式 SELECT | 原 P3 Store、冻结协议、原 evaluator、轨迹；空间验证证据在另一个 spatial Store |

本轮递归检查 9 份 Trace 中的 86 个文件路径，均可读取，已声明的文件哈希均一致。M1–M6 选中结果链实际读取了 62 个 Store artifact 并复核字节哈希；C1 的 8 个控制/原始采样 artifact 亦匹配。PHS 的 40 个引用全部存在，另解析一份 401 样本的真实动力学结果及 assembly/baseline/protocol 绑定。P3 的 28 个引用在其各自原 Store 中全部存在，另解析一份 2,000 样本动力学结果，并读取最终 8 份 CSV、核对全部 1,600,000 行及各自哈希；其中 6 个空间检查引用归属 spatial Store，不能在原 P3 Store 中误报缺失。未将原私有 Store、获胜结构或控制复制到新 Study。

原始索引与检查细节见：

- [source_inventory.json](../../evidence/r0_benchmark_preparation/source_inventory.json)
- [historical_evidence_audit.json](../../evidence/r0_benchmark_preparation/historical_evidence_audit.json)
- [development_evidence_audit.json](../../evidence/r0_benchmark_preparation/development_evidence_audit.json)

这些路径的可用性只代表本机本次检查；克隆 Git 并不包含外部原 Store。历史复现仍须携带这些精确来源与哈希，不能仅拿摘要重建控制。

## 九任务适配矩阵

“有”指源码/注册已存在；“部分”不等于端到端适配。本轮没有为其余八任务建新 Study，也没有重跑任何历史实验。

| 任务 | 原任务/结构域/载荷/初态/网格可恢复 | 原结构、控制或被动物理来源 | 当前 FamilySpace | 机制/数学观测 | 控制/物理执行注册 | 独立 evaluator / Replay / 联合 SELECT | V4 科研决策及阻断 |
|---|---|---|---|---|---|---|---|
| M1 | 完整，三个 BF7 原条件 | 可读，三组控制及采样 | 有；原 2 段/6 腱冻结子域一致 | 瞬时机制、短响应、Reach/Hold T1 和已有证据 T2；非完整动态结构梯度 | 有，原 Native 优化和显式控制 Replay | 有，原 Reach/Hold 联合验收 | 本轮 Schema/编译/Mock 通过；真实自主研究待授权 |
| M2 | 完整，BF2 零/正/负 COM 力 | 可读，三条件 Replay | 有，原文件与当前一致 | Native 实际外力可用；GVS/Conic 不支持完整 COM 外力任务，不能替换成无力问题 | 有，Native 和冻结世界 COM 力执行 | 有，原同协议三条件联合验收 | Reach/Hold 路径可复用；尚未独立准备，不能宣称数学全覆盖 |
| M3 | 完整，原 B3 0.50 s 开发草案 | 可读，原 SELECT/控制/Replay | 有，原文件一致 | Reach/Hold Native T1/T2、局部机制适用 | 有 | 有，**协议仍是开发草案** | 接口有；正式 Benchmark 批准是独立缺口 |
| M4 | 完整，BF4 定时折返参考 | 可读，完整时间参考和物理采样 | 有，原 tracking 家族文件一致 | Native direct 与定时位置约束可用；T1/T2 明确不适用 Tracking | 有，direct sequence 和注册后端 | 有，timed evaluator/Replay/单任务 SELECT | **部分**：V4 control_feasibility→T1 被拒绝；不能将终点误差冒充全程跟踪 |
| M5 | 完整，BF5 位置+有向轴 | 可读，真实工具轴采样和控制 | 有，原 tracking/工具原型一致 | 原 direct 同时观测位置与轴；瞬时 tip Jacobian 不能证明轴任务；Conic/T1/T2 不覆盖完整任务 | 有，backend 1.3 显式 Native sequence；GVS/NMPC 轴优化不适用 | 有，双谓词 evaluator/Replay/SELECT | **部分**：V4 T1 路径不适用，尚无完整有向轴机制决策映射 |
| M6 | 完整，BF6 刚性工具定时扫描 | 可读，原 rigid-tool 和逐步 contact 证据 | 有，原 sensor 家族文件一致 | 原 direct 是采样搜索代理；无接触门禁和工具载荷必须 Replay 核实；无完整接触结构导数 | 有，backend 1.4 显式 Native sequence | 有，原 oriented v2、刚性工具绑定和逐步无接触验收 | **部分**：V4 T1/T2 不适用；不能削弱为纯位置任务 |
| C1 | 完整，原 M1 三条件+M5 同一结构 | 可读，四组控制/采样，原同 XML 审计 | 基础生成器可表示原合法结构；不能继承 M1 固定 6 腱限制来代表 C1 的公共低腱数域 | Reach 与轴任务支持范围各异；无异构全任务标量验收 | 各单项有 | 各单项有；**原四条件联合链没有** | resolver 只接 2/3 条件，聚合拒绝异任务族/协议；本轮未修 |
| PHS-2D | 完整，原材料点十工况、无载基准与数值修订可追溯 | 可读，assembly、基准、加载、协议、样本均有来源 | 通用 V2 有材料分布/放绳字段；**当前被动示例仅 1 段/1 腱/2 单元，未冻结原 9 段/4 腱域** | 原被动 KKT、Jacobian、可行锥、重平衡观测有；完整十工况稳定性不等于这些观测 | 通用 no_active_control + passive backend 有 | 通用 passive_response 有；**原十工况完整 evaluator/Replay/SELECT 未接入** | 缺原域、基准资格、十工况及尾窗残差等完整映射；本轮未修 |
| P3 | 完整，原双向五阶段连续加载和机制对照 | 可读，原 Store/CSV 来源和空间检查存在 | 通用内核可表示被动结构/放绳；**当前示例不是原 3 段/2 腱合法域** | 静力/KKT 和张紧集合观测有；加载历史、刚度比、恢复和有效消融还需原时序证据 | 通用被动执行有；**当前 goal 只有每工况重置的单次 ramp/hold** | **原连续多阶段/刚度比/机制联合验收未接入** | 原开发见证不能按现通用 passive_response 宣称可 SELECT；本轮未修 |

## 原任务与最小后续改动位置

1. **M1**：权威文件为 `tasks/bf7_shared_reach_v1_{positive_high,negative_low,central_high}.json` 及 `reach_hold.json`。三目标分别为 `[.285,.035,.185]`、`[.275,-.040,.135]`、`[.295,0,.215]` m。世界重力 `[0,0,-9.81]`，无附加外力，原 10 g payload 原型、mount 和惯性均继承。seed=17，所有候选自由度位置/速度为零；0.6 s，物理步长 .001 s，控制/采样 .02 s。终点误差及末 .06 s 位置 ≤.01 m、速度 ≤.03 m/s，末窗 4 个含端点样本；solver_errors=0，力界容差 1e-8 N。三条件结构及离散必须相同，合法控制可不同。本轮无生产代码阻断，无需新增模块。
2. **M2**：`bf2_multidirectional_hold_frozen_v1_{zero,positive,negative}.json`。目标 `[.29,-.035,.19]` m；0.35 s，.0005 s 物理步长，.01 s 控制/采样，末 .05 s：位置 ≤.01 m、速度 ≤.02 m/s、6 个样本。正负条件在 .1–.35 s 对 payload 世界 COM 施加 `[0,±.02,-.03]` N。原始零初态、重力、来源都在冻结配置。最小准备工作仍是现有 Study 三条件配置；完整外力数学扩展不在本轮，不能把 GVS/Conic 的 unsupported 写成已支持。
3. **M3**：`reach_hold_b3_050.json`，目标同 M2，.50 s、.0005 s/.01 s，原末 .05 s 位置/速度阈值同 M2。源码接口无需因历史通过而修改；正式 Benchmark 之前必须冻结并批准原开发协议地位，不得事后重标旧证据。
4. **M4**：`bf4_tracking_direction_change_v1.json`；世界位置折线及 `[0,.3,.6]` s 参考完整保存，.6 s、.001/.02 s，全规定时间采样位置误差 ≤.012 m，无 Reach/Hold 速度门槛。后续最小接口工作在 `scientific_intent.py` / `task_constraints.py`：明确投影现有 direct-sequence 研究路径，并保留 T1/T2 的 not-applicable；不开发新优化器。
5. **M5**：`bf5_position_tool_axis_v1.json`；位置 `[.29,-.025,.12]` m、冻结有向单位轴及 tip-local 轴完整保存，.6 s、.001/.02 s；原采样窗位置 ≤.008 m，轴角 ≤π/60 rad。后续在上述原意图/发现接口暴露已注册 direct 选择，完整保持双谓词。姿态数学如尚无注册观测，应返回 unsupported，不能临时用位置 Jacobian 代替。
6. **M6**：`bf6_sensor_oriented_tracking_v1.json`；.6 s、.001/.02 s 的冻结位置/轴时间参考，20 g payload、COM `[.007,.001,-.002]` m、完整惯性与 tool site 均保留；位置 ≤.012 m，轴角 ≤π/18 rad；完整每物理步环境无接触和刚性工具绑定是额外硬门禁。后续只在原意图/目录中区分 direct 与不适用 T1；保留 `backends.py`、`physical_replay.py`、`research_tasks.py` 的原验收权威。
7. **C1**：原任务就是 M1 三 Reach/Hold 加 M5 轴任务，四条件同一实体结构、各自控制；`runs/c1_20261029/run_case.py`、`audit.py`、budget 和四个配置可恢复其原域、初态和原协议。最小后续工作是 `config.resolve` 的四条件/异构后端绑定、`conditions.configuration_for_condition` 的条件执行策略，以及 `research_tasks.aggregate_acceptance` 的明确异构组合协议；目前该函数直接抛出 `AGGREGATION_TASK_PROTOCOL_MISMATCH`。不能只删掉检查或扩大 list 长度。这些本轮均未实现。
8. **PHS-2D**：原 `phs2d_protocol_inverse_v2.json` / `family_space_phs2d_inverse_v2.json`、`phs2d.py` / `phs2d_evaluation.py` 是历史权威。总柔性长 .28 m、世界重力、基座、材料坐标定义、无载基准资格都要保留。搜索 s=.3/.5/.7、预留 s=.4/.6，各 ±.1 N；4 s 基准/4 s 受载时域、.5 s ramp、.25 s 尾窗，主步 .000125 s，原最终半步检查已存在。门槛：受力点 ≥.01 m、Tip ≤.005 m、比值 ≤.30、平面外 ≤.002 m，以及原速度、漂移、关节、残差、长度、接触检查。协议中的默认 cells=12 不能覆盖候选冻结的实际 8 cells；真实加载初态来源是各自合格无载基准，不是零姿态。最小后续方案是在原 FamilySpace、reference contracts/passive_response、passive_execution 和 TaskAdapter 中版本化映射原完整协议，包含 holdout 与基准来源；不复活历史独立编排器，不新建 Worker。
9. **P3**：原 `passive_progressive_stiffness_dev_v1.json`、`passive_load.py` / `passive_evaluation.py` 和 final_freeze 是权威。固定材料点 s=.7，±X，五阶段 `0/.05/.1/.2/0` N，每阶段 4 s，连续 20 s 不重置；相同合格无载平衡起步。主物理步 .000125 s，评分 .01 s，原逐步记录另保留。低载位移 ≥.006 m、高载 ≤.025 m、区间刚度比 ≥1.5、恢复残差 ≤.002 m，及分母精度、张紧/松弛转换、稳定性、路径、有效消融、半步/初态复核均不可丢。当前 `PassiveResponseGoal` 只支持单 ramp/hold 且每工况重置，`PassiveResponseBound` 无完整阶段刚度/静态残差/机制组合。最小后续修改仍放在这些原 contracts、passive_execution、passive_response、TaskAdapter 及组合验收中。原 1/2 cells 通过、4 cells INVALID 的空间敏感性限制继续保留；本轮未补跑或修复。

## 统一 Benchmark 配置约定

不增加 Benchmark Harness、第二个执行入口、Store 或 Reporter。仍使用 `python -m tools.research`、现有 Study resolver、`research_plan`、`research_analysis`、`scientific_question_v4`、短对象、Reporter、原 ledger/Worker 恢复。

两种模式用**独立 Study ID、authorization、supplied_evidence、knowledge 和 execution_instructions**明确区分，不增加新的 runtime 状态机：

- 历史协议复现：名称和授权明确为 reproduction_control。历史结构和控制必须以可读取的精确来源、原身份、网格、通道和哈希单独绑定；只能产生标注为复现对照的证据。历史源本身不是 fresh current-study 验收，仍走原候选绑定、Replay、evaluator 和选择规则。
- 独立自主研究：空科学候选池，`initial_structure_strategy=agent_choice`；不得提供历史候选、控制、result Store、task-specific success_case 或私有经验。至少冻结 `allow_benchmark_answers=false` 和明确 Knowledge 清单。M1 本草案进一步设 `mode=off`、`include_entry_ids=[]`，因此冻结清单为空。Reporter 只能读该 Study 已有来源，不获得另一条历史答案通道。

公共 FamilySpace 原型及其默认值仍是公开工程先验，不能宣称随机、无先验或完全信息隔离。正式研究通过已暴露工具得到的盲测可用范围，与执行本次审计的操作者能够查看历史文件是两回事。原框架不是任意文件访问的隔离沙箱；若未来另给 Main shell/文件工具，须重新冻结授权范围。本草案没有增加此类工具。

## M1 草案、准入与验证

草案：[study_r0_m1_v4_draft.json](../../configs/research/study_r0_m1_v4_draft.json)。
Study ID：`r0-m1-v4-offline-preparation-20261101`。这是本轮待授权准备对象，正式研究必须使用新的单次 Study ID；不修改或重置此对象预算。

实际 prepare/bind 均通过；绑定实现为 `36193aedd70fdf4755dc27e986931772682b0bd3`，resolved identity 为 `956c10cf70b31c111b1df0c74609c0160dc52bfa8fe1d66a0bb252dbff8e6ba0`。后续交付提交只补文档/检查记录，没有改写该绑定。绑定后兼容性通过，候选数、所有消耗和授权事件仍为 0，pending 为空，正式研究门禁仍拒绝未授权执行。

与原 M1 Store 比较：三个 `task_conditions`、解析后的 FamilySpace、backend、dynamics_model、discretization 完全相同。原 2 段/6 腱子域保留；Main 仍可在该原域内选择合法长度、材料、截面和腱路。增补的 `family_sensitivity_variables_v2` 仅冻结该域中现有参数的可选机制研究授权，不拓宽物理参数域。V4 公共请求保持真实结构/控制研究意图；内部复用旧请求编译器不改变对外版本。

本轮检查：

- 正式 resolver/prepare 成功，候选池为空，Knowledge 清单为空。原 pending 授权门禁能拒绝未经批准的科学执行。
- 三条件 TaskAdapter：注册任务、evaluator、信号、initializer、controller、backend 的技术兼容检查均 supported；不据此宣称任务成功。
- 一个 M1 集成测试通过：12 次真实 SDK/Mock HTTP 请求，按需工具 Schema、短引用、生成、机制 diagnose、条件绑定、普通 baseline 控制初始化、Native control diagnose；V4 结构和控制请求均编译到原 AnalysisRequest。没有获胜结构/控制注入。
- 6 项现有小范围回归通过：同结构不同控制/恢复/联合 SELECT、三条件身份与非法来源、V4 菜单、原机制编译门禁、T1 原契约与计费、按需 Schema。所有数值输出均为既有 fixture；没有新真实物理。
- Mock 里的授权和 continuation admission 明确是隔离 fixture 数据；真实准备 Study 没有授权事件。初次测试暴露的是 fixture 缺少 handoff/数学授权和固定 ID 的 single-use grant 冲突，已改为显式 fixture 准入及唯一测试 ID，未放松生产门禁、未删除 grant 或重置科学预算。

实际总成本：真实 Provider=0，真实数值 Worker=0，真实控制优化=0，真实物理 episodes/steps=0，新独立 Replay=0，PPO/NMPC=0。几何/Schema/Host 编译准入不属于新物理实验。prepare/bind 的身份和余量见 [preparation_validation.json](../../evidence/r0_benchmark_preparation/preparation_validation.json)；Mock 与测试结果见同目录。

## 最小修改与删除清单

- 新增 1 个 M1 待授权 Study JSON，1 个针对 M1 的无数值 SDK 集成测试，以及审计文档/结果索引。
- 生产 Python 修改：**0**。未发现本轮 M1 必须修复的通用执行接口阻断。
- 删除函数、模块、数据或历史证据：**0**。旧 C1.1、main 和其他 worktree 不改。
- 未开发结构优化器、控制器、数学工具、Worker、Store、Reporter 或预算系统；未实现 C1、PHS-2D、P3 的后续接入。

## 正式 M1 启动的冻结预算与授权边界

当前准备对象的真实 Provider 配额为 **0**，authorization 为 `PENDING_EXPLICIT_APPROVAL:`；它没有正式研究启动许可。以下为可审阅的**未来启动提案**，不是本轮授权，也不向既有 Study 追加预算：

| 项目 | 当前 R0 冻结值 | 新正式 Study 提案 |
|---|---:|---:|
| Provider 总请求（Main、Reporter、失败发送、closeout 合计） | 0 | 64，其中 8 保护收尾，待用户明确冻结 |
| public_operations / 保护收尾 | 500 / 8 | 保留 500 / 8 |
| mathematical_evaluations | 16 | 保留 16，机制与 T1/T2 共用 |
| physical_launches / 独立 Replay | 100 | 保留 100，共用原累计 ledger |
| 每次 Native 回调 / iterations / knots | 800 / 100 / 4 | 原上限保留；Main 可选更小值 |
| local_solves / offline_nlp / bdf_replays | 0 / 0 / 0 | 0 / 0 / 0 |
| NMPC / PPO / RL evaluation | 0 / 0 / 0 | 0 / 0 / 0 |
| 原 campaign 最大物理尝试步数 | 8,000,000 | 不得突破 |
| 额外成功确认次数 | 0 | 0；三条件完整联合验收后立即 SELECT |

原 8,000,000 步 campaign 上限并非当前通用 Store 中单独新增的步数预算字段。当前保留的预算通过原每条路径的计数守恒约束：最多 16×800 个完整 .6 s Native 回调，再加 100 个完整独立 Replay，各最多 600 次积分，合计上界 **7,740,000** 次。机制和短响应消耗同一个数学计数，原短响应时域上限 .05 s，原 T1 回调亦含其差分探测，因此不会另开 16×800 外的物理窗口。不得额外授权 NMPC、RL、未计费重试、另一条独立 rollout 途径或预算扩张；若未来改变任何路径或每回调成本，此推导需先重新审核，而不是声称已有独立全局步数限流器。

正式启动前需要明确授权：一个新的冻结 Study ID/解析身份、单一 Provider/runtime/model/线程/continuation 准入和 64/8 请求提案是否采用；授权 scope 包含 `registered mathematics`、原 Native 控制优化、三个原条件的独立 Replay 与联合 SELECT/STOP；同一原结构域/阈值/网格/来源、Knowledge 空范围、原累计预算、失败保留和 pending Worker 恢复均保持。提供给批准者的应是新 Study 完整 resolved configuration 及 scope_identity；现有门禁要求与确切 Study ID 和 resolved_identity 对应的授权事件。

Worker 未知结果必须先 recover/reconcile，不能通过新 request_id 或新 Study 复制预算；不恢复半段物理轨迹来冒充完整独立 Replay。三条件各自成功不触发单条件 SELECT，完整读出三个 acceptance_certificate 后才提交精确联合结果。失败或预算耗尽以有证据的 STOP 收尾，不自动替换 Study 或继续其他八任务。

本轮到离线准备、提交/绑定和证据交付为止；不启动 M1，不启动其余任务，不合并 main。
