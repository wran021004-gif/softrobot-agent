# P6.3-G3：科研行动交接验证

本轮接口目标通过。Main 自主提出联合研究假设，显式选择
`structure_control_codesign`，下一次真实 wire 加载了
`ScientificStructureSearch`，随后自行修正一次非法截面类型并提交合法请求，
启动原 Mixed Search 和 Native Worker。未要求或宣称独立任务验收通过。

仅运行一个新 Study：`p63g3-m3-action-handoff-sol-20261030`。
模型保持 `gpt-5.6-sol / none`，科研提示、任务、FamilySpace、模型、协议和
控制配置与 G2 一致。未开启 Thinking、替换模型、追加额度或启动第二个 Study。

## 验收与真实请求

| 验收项 | 结果与证据 |
|---|---|
| Main 联合假设 | 请求 3：改变合法几何、路由和结构参数，逐结构重新优化控制，检验终端位置、保持位置和速度；明确有限失败不证明结构不可行。 |
| 显式行动 | 请求 3 的 diagnose 包含 `next_research_action=structure_control_codesign`。不是从 selected_method 或假设文字推断。 |
| 下一次实际 wire | 请求 4 只有 `research_plan(search)` 的 ScientificStructureSearch；无 research_analysis。L0 direct_plan 同为 search，无过时 ScientificQuestion 提交指引。 |
| 合法科研请求 | 请求 4 的 section_types 不合法，原校验拒绝、无 Worker；Main 在请求 5 自行修正，原 FamilyMixedSearch 准入 12 次评价上限。 |
| 原 Worker 启动 | 请求 5 启动原 search.run_search、analysis.dispatch、隔离 Native Worker。11 个 Main Worker 均记录 worker_started=true。 |
| 完成与真实费用 | 11 个 Worker 均 returncode=0、termination_confirmed=true；科学状态另行区分：6 次 computed、5 次 execution_incomplete。原费用、失败原因和结果引用保留。 |

完整实际 Schema、原输入/反馈引用、逐请求角色、已交付 L0、Worker 边界和费用
见 `p63g3_live_audit.json`。这些证据来自实际 Store/wire，不是 Python 函数返回值
或脚本编造的模型行为。

| Provider 次数 | 行为 |
|---|---|
| 1–2 | Operator 准备数学与独立失败 Replay 的 Reporter，均 available。 |
| 3 | Main 首次 diagnose：自主联合假设、合法候选、明确 codesign 行动。 |
| 4 | 已加载新 search Schema；非法 section_types 被拒绝。 |
| 5 | Main 修正后提交合法结构/控制搜索，原 Worker 执行。 |
| 6–10 | 原 Reporter 对搜索结果进行解释，全部 available。 |
| 11 | Main 收到结果后再次提交 diagnose，但重复附加根级 selected_candidate；原 Schema 拒绝，无新科研执行。保留此模型字段使用限制，未替它补交。 |

请求 11 不影响已经完成的行动交接验证。它也说明单窗口成功不代表模型今后不会
犯字段错误。本轮没有追加提示、修正运行中代码或再开验证窗口追求更理想轨迹。

## 科学结果与限制

Main 自选 lengths、sections、routing、spans；12 次提案、12 次评价上限；
Native response、四个均匀 knot、12 次迭代上限、每条件 180 次回调。
这些是 Main 的选择，不是 Operator 准备时的 pattern / 80 / 120。

原搜索实际构建并评价 11 个设计；第 9 次提案因重复或裁剪后无变化而跳过，
没有新增评价费用。原终止原因为 `proposal_budget_exhausted`，状态为
`best_finite_budget_native_candidate`，搜索耗时约 141.652 s。

五个不完整结果的原因为
`NATIVE_V1_REQUIRES_FINITE_CONTACT_FREE_UNCONSTRAINED_STATE`。
子进程正常返回不等于数学计算成功；这些失败没有改写、弱化或计为 computed。
它们的 Worker 时间和正式评价费用保留，但未返回详细 Native 计数，不能将缺失计数
当成零。没有修改物理内核以使这些候选通过。

六个 computed 结果的有限搜索 J 依次约为：0.0009427063、12.46994032、
0.000005939609、0.000002492609、0.0000000009851919、
0.00000000003149969。最佳候选为
`da1c14850fcd93aa33705f1caae54ceafd5366e9225d77d2737168fd459f2dac`，
数学结果为 `536e97dd81f7f1df4e564f6c44b90f75261197137817d25f7df728fa364dcfe6`。

最佳结果的终端/保持位置误差约 0.009999999999944607 m，保持速度为
0.020000000000629993 m/s，仍略高于冻结的 0.02 m/s 阈值。不能通过四舍五入
宣称通过。Main 没有进行新的独立 physical_replay、SELECT 或正式 STOP；
数学结果仍为模型范围内的有限预算诊断，无全局可行性或最优性证明。

## 准备归属、费用与停止

Operator 在新 Store 内重新生成合法候选和 baseline，执行一次真实 Native
pattern 优化（四 knot、80 iterations、120 callbacks），再执行一次独立失败
Replay。没有复制旧结果、控制轨迹、费用或 Store，没有预填 Main search 或 Plan。
准备时的终端误差 0.1264496051 m、保持误差 0.1281643988 m、保持速度
0.2536984073 m/s 均为新执行的有效失败；两份 Reporter 解释均 available。
授权先按原 formal_study_authorization 机制登记，总上限 16。

| 项目 | 实际记录 |
|---|---:|
| Provider 总数 / 上限 | 11 / 16 |
| Main / 准备 Reporter / 搜索 Reporter | 4 / 2 / 5 |
| HTTP 失败实际发送 | 0；11 次均 HTTP 200 |
| prompt / completion / total tokens | 93,550 / 6,208 / 99,758 |
| reasoning tokens | 0 |
| Provider elapsed | 226.969 s |
| 最大实际请求 | 76,616 bytes |
| Main 正式数学评价 / computed / incomplete | 11 / 6 / 5 |
| Main 搜索 / 独立物理评价 | 1 / 0 |
| Main 已结算 Worker wall | 120.6806198 s，包含不完整 Worker |
| 六个 computed Main 结果的已报告计数 | 6 builds、1080 rollouts、1,080,000 physics steps |
| 准备 Native 的已报告计数 | 1 build、120 rollouts、120,000 physics steps |
| 全 Study 已报告 Native 计数之和 | 8 builds、1201 rollouts、1,201,000 steps；缺失的五个失败计数未知 |
| Study numerical_s / construction_numerical_s | 144.4603245 / 5.6989111 s |
| 已报告 kernel wall | 119.0420125 s，已包含于对应 Worker 范围，不再次相加 |
| 原共享账本 model_calls / tool_calls / backend_solves / worker_calls | 11 / 4 / 1 / 0 |
| 货币成本 | Provider 未提供，未知 |

账本 worker_calls=0 是原分类，不表示没有 Native 子进程。原始 Worker 文件和
boundary 明确记录了启动、返回码、终止与费用。

验证完成后，Operator 在没有 pending Worker、未知 Provider、未消费响应或
未结算 receipt 的边界，调用原 engineering_closeout 关闭本次短窗口。
状态 stopped、model_stop=false、selected=null、success_gate=null；额度没有用尽，
没有要求 Main 继续研究或 SELECT。随后 SDK 的继续发送被原
`SEALED_STOP_OR_PENDING_WORK_BLOCKS_SEND` 在创建 r3_request 前拒绝；外层
APIConnectionError 是该本地 guard 的包装，不是第 12 次实际请求或网络重试。
Runner 已退出，pending 和未结算调用均为零。没有重新启动。

首次启动 Main 前，原环境检查发现新进程未设置冻结的三个单线程环境变量；设置
原配置值后才发送 Main。该 preflight 不涉及实际 Provider 请求或新科学结果。

## 离线检查与交付

46 项相关 C0/C1/C2/G0/G2/G3 测试通过；最终 11 项实际 SDK/Mock wire 回归通过。
G3 包含原 G2 请求 5/6/8/10 回放、显式/中立选择、原 search 准入、参数组、非法
Pointer、原有效性和 saved-T1-only T2 检查。另一个旧 C1 历史归档测试类因缺少
本地 immutable_artifacts.tar.gz 无法启动，不计入通过数。详细范围见
`p63g3_offline_validation.json`。

仅一次极小真实 Native 搜索用于离线接入检查：1 build、2 rollouts、1200 steps，
returncode=0。它不属于本 Study，也不计作 Main 科研。git diff --check 通过。
G2 原 Store 通过 SQLite mode=ro/query_only 检查，文件大小和 mtime 与前记录一致；
其历史与预算未改写。

实现冻结在本地 `e082a4ae2525cc4d12806fdce11a53a265a997f3`。直接 git 传输不可达，
使用已连接的 GitHub Git-data 工具发布为
`e06603b1e1f3c2b186535ee2f7df9815cdf19afb`；两者源树均为
`933b8b4c5a7a6c8e0d14e0947a5b1c6f2c05cfd7`，差别仅为提交元数据。
原本地提交和审计提交保存在增量 Git bundle 中，供精确恢复实验冻结版本。
审计与报告另行提交到同一 G3 分支，未合并。

固定职责和兼容边界见 `p63g3_scientific_action_handoff.md`。
复核命令：`python -m tests.research.p63g3_audit`，仅只读原 Store 并生成审计，
不会调用 Provider 或科学 Worker。准备脚本为一次性入口，已有 Study 时明确拒绝重建。
