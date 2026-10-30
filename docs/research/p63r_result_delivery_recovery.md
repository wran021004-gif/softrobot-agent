# P6.3 R0/R1/R2：结果交付、原恢复与同 Study 接续

基线为 `32cab42a011750138504b9d63b8f218f2df3a486`，独立分支
`codex/p6-3v-result-delivery-recovery`。唯一 V1 为
`p63v1-m3-autonomous-feasibility-sol-20261030`。经隔离恢复验收后从原 24/80 接续到
32/80，数学结果由 94 增至 155（137 computed、18 incomplete），完成一轮新搜索。
没有新建 Study 或重放旧两轮搜索。实际 Main 已收到原两轮最佳结果；独立 Replay、
正式物理通过、SELECT 均为 0。运行最终因第 32 次 Reporter 响应未能入库而受原恢复
门槛阻断，属于工程中断，不是 Main STOP 或科学不可行结论。

## 缺口定位

`core.packet()` 的 search_feedback 不在研究版 `agent.decision_packet()` 调用路径中。
`research_context.context().decision_feedback.recent_searches` 只取 control_search_results，
没有纳入 search_results。agent_decision_brief 主要保留最后两份 Reporter 和最近几项
数学结果，随后 compact_scientific_delivery 将 recent_searches 压为查询；
research_decision_brief_v3 / information_flow_brief 也没有聚合搜索事实字段。
session_handoff 可保留原工具反馈，但不是自动读取搜索最优指标的程序。
因此最终实际 wire 只有“搜索完成”及搜索引用，没有对应最佳 C/M/U/J。

原实际请求 19、22 的缺失证据保留在 V1 暂停报告及 p63v1_pause_trace_audit.json。
新固定事实沿原 search_feedback → agent_decision_brief → compact_scientific_delivery
→ research_decision_brief_v3 → information_flow_brief 进入现有 Provider 尾部 packet。
没有新增 Reporter、工具或科研状态机；Reporter 解释保留其非权威角色。

## 固定结果视图

现有 L0 新增 scientific_results：latest_search、按原 task/profile/method/discretization
可比条件分组的 study_best_mathematical、latest_evaluation、best_independent_physical。
最新搜索较差或最后结果 incomplete 时，前一轮最佳 computed 不消失。
同组最佳若已在最新搜索卡内，用 facts_at 指向同一事实，避免重复数值。

搜索卡含原搜索及 Plan、方法和范围、实际 proposal/evaluation/status 数量、终止原因、
最佳候选/数学结果/控制 source、J、原任务三项指标和阈值/有符号超额、控制设置、
实际归属成本、独立验收状态及 comparison_summary 原索引。只读取原搜索汇总、
最佳结果和必要的独立数学结果；不把全部轨迹塞入 L0，不依据 Reporter 文本排名。

卡片明确 scientific_observation_available、executable_under_current_profile 和
current_profile_requires_new_construction。复用 final_materialization 原生成配方，
新 Plan 的 supporting_evidence 指向已注册的候选和底层数学结果；搜索引用保留为
source_search 导航，不新增其正式科学证据资格。旧控制仍只属于原候选，不能
自动移交给新候选。所有候选生成、控制初始化、独立 Replay 和 SELECT 仍由原准入判断。

## 大状态性能

对原 94 项数学结果 Store 做只读 cProfile：原单次 decision_packet 为 604.159 s；
其中 action_feedback 415.959 s，warm_start 342.099 s，JSON decode 533.530 s。
按 warm_start 既有类型规则提前筛选来源后为 270.527 s；一次中间 SQL 投影写法
导致重复解析，实测 272.311 s，已替换为一次多路径 json_extract。
复用同一次同步投影的 budget 和 method view、减少重复 citation state 读取后，
最终观测为 88.764 s。上述为实际本机含 profiler 的观测，不是无条件性能保证。

Store.artifact 的可选 paths 读取仍先核对完整原始 blob 的哈希和媒体类型，再从
同一原始字节提取少数字段，保留 JSON 类型/显式 null/缺失区别；不新增缓存数据库。
科学执行继续使用完整原结果，数值内核、原任务、模型、求解器和评价器未改。
去掉新增 scientific_results 后，优化前后原 packet 的全部字段逐值相同。

## 离线验证与边界

小型合成协议夹具验证了指标/source/成本/索引、最新与最佳分离、incomplete 排除、
跨 Profile 不混排、旧候选只读/执行拒绝、合法生成入口、不增加证据资格、
Reporter available/unavailable/skipped 时实际 SDK/Mock wire 的固定事实及旧字段保留。
已有 G3/G2、bounded evidence、evidence policy、request-boundary 和 C1/C2/information
flow 直接相关测试已运行，详见离线审计及原日志。

一次旧快照 Schema 测试暴露 evidence_query_schema 对共享返回值原地 remove 的缺陷；
增加 deepcopy 后复测通过，没有改变正式 Schema 或准入。另一项 Knowledge 测试
缺失旧 Git 对象，通过 GitHub 原 commit/tree/blob 哈希补齐三个公开历史 summary
的本地 Git 对象后通过；没有改工作树历史文件、Knowledge 目录或 V1 冻结输入。

对原 Store/SDK 的隔离副本，通过原 converse(restore_only=True) 恢复，随后仅发
一次 Mock Main 请求。原最近工具反馈得以恢复；副本计数从 24 到 25，原 Store
保持 24。94 数学、两轮搜索、候选/控制和数值费用保持，科学 Worker 为 0，
旧 Provider 请求重复发送为 0。实际 Mock wire 为 102953 bytes，第一轮最佳
J=-0.014355323230259676、第二轮最佳 J=-0.0069635885347172355 及两组三指标、
source、Profile 限制直接可见；旧 task/trace/tool_continuation/Knowledge/budget/
method/Plan 机制保留。此初次副本测试使用了明确的 fixture root/guard 隔离和 Mock
凭据/传输，不授予真实执行权限，R2 不使用这些 patch。

原 v1/v2 Profile 和全部旧证据保留，不手工修改 Profile identity 或候选身份。
本轮共享 Store/上下文源码属于既有保守依赖闭包，不能以排除整个源码文件的方式
承诺后续任意修改都不影响科学行为；保持原 Profile 分类规则。提交后必须使用原
bind/migrate 路径，在隔离副本先审计新版本、全部科学哈希和原费用/来源保持。
只有完整离线恢复/交付/迁移验收通过，才在原 Store 原 80 总额度内接续 R2。

## R2 状态

实际过程、科研结果和工程阻断见下文。原始 Store 保持 ready 和一项 unknown Provider
回执，不以人工封口伪装成合法 STOP；原 80 次总额度及所有历史科学身份保持。

## R1 提交后迁移与恢复验收

修复冻结为 `b0f0faad1fc20e7adbabe60846f0ac4fa8c52c81`。隔离副本使用原 bind，
Profile v2 → v3，完整保留 v1/v2、94 项数学结果、两轮搜索、候选、控制和费用，
科学源码哈希相同。SDK restore-only 14.673 s；原 handoff 从 before_prepare 到
committed 12.680 s，其中写快照约 0.012 s、独立验证约 11.827 s；一次 Mock converse
总计 200.051 s（含两次决策构造及交接），正文 103406 bytes。fixture patch 不授予
源码、任务或来源真实执行资格。完整原结果见 `p63r_recovery_validation.json`。

原 Store 的原 bind 也完成相同 v3 迁移，全部逐项保持检查通过。启动驱动在迁移
提交后因未写入的 physical_replay_launches 零次字段使用下标触发 KeyError，尚未
启动 converse 或发送 Provider；保留错误日志后，从只读迁移前副本核对全部科学/
费用身份，用 get 审计缺省字段并接续已提交迁移，没有重复 bind 或手改身份。
驱动错误不计为 Main 决策或 Provider 故障。见 `p63r_live_migration.json`。

R2 已按用户新授权在原 Store 通过原 converse 接续，起始仍为 24/80，总新增上限
56，模型和科学提示词沿原冻结配置。后续实际 wire、Main 科研及结论另行补入。

## R2 首次实际交付与字段回归

第 25 次请求的实际 HTTP 200 wire 为 102250 bytes。两轮最佳 C/M/U/J、三项指标、
阈值和旧 Profile 不可直接执行的状态已直接进入 Main。Main 提出新 Profile 下的
联合结构与控制搜索，并明确不把旧候选当作当前可执行候选；但其支持证据包含
未注册的两轮搜索汇总，原准入以 UNREGISTERED_RESEARCH_EVIDENCE 拒绝，未启动科学计算。

第 26 次 Main 自行清空全部 supporting_evidence，提交 64 proposal / 64 evaluation
的有界搜索后获原准入接受。清空也移除了本来可引用的底层已注册数学结果，故不能
将这次恢复描述为完全正确地理解引用资格。其假设为新 Profile 上的结构控制协同
搜索；搜索组仍为 lengths/materials/sections/routing，使用 response 控制优化、
4 个 knot、100 iterations、1000 callbacks、initial_tension_n=0，未指定旧候选作
previous_candidate。以上是 Main 的实际选择，Operator 未替其选择结构或物理复验。

对真实 wire 的进一步核对发现，搜索范围投影使用了旧的单数字段名，而实际编译
查询使用 variable_groups/segment_counts/tendon_counts/span_strategies 等名称。
因此最佳数值已交付，但直接范围字段尚不完整，不能将 R0 声称为完全通过。新增
小型合成回归 test_compiled_search_scope_and_registered_math_are_direct_facts 在当前
冻结上以 KeyError variable_groups 如实失败，日志 p63r_scope_regression_before.log。
本轮正在运行的 Native 批次保持原冻结；待其及对应 Reporter 封口后，在无 pending、
无未消费响应、无未封口调用的边界记录工程暂停，再修正这一个投影并按原版本和
隔离恢复验证接续。暂停不属于 Main STOP，不重置原 Study 或任何预算。

## 第三轮结果与真实工程阻断

第三轮因 proposal_budget_exhausted 封口：64 proposals、61 legally_constructed、
61 actual_mathematical_evaluations，53 computed、8 execution_incomplete；外层耗时
4087.543 s。重复或裁剪后无变化的提案由原搜索机制跳过。当前 Profile v3 的最佳
数学 J 为 -0.011897791151900927，terminal/hold-position 为 0.009881022088480991 m，
hold-speed 为 0.01955035395638464 m/s，阈值分别为 0.01 m、0.01 m、0.02 m/s。
完整 C/M/U 和指标指针见 p63r_blocked_scope_projection.json。不同 Profile 分组展示，
不与 v1 的最佳 -0.014355323230259676 混排。这些都没有独立任务验收资格。

Reporter 依原优先级解释关键结果、跳过常规重复结果，累计 Provider 达 32
（Main 16、Reporter 16；本轮新增 Main 2、Reporter 6）。第 32 次请求
`r3-request-001b8413ac4740c2b57234712c4525cf` 的原响应在归档首个事务提交时发生
database is locked，事务回滚，Store 中没有响应原始字节。原边界保留 unknown 请求，
运行驱动退出。故障由 Operator 的只读监控脚本引入：runpy 嵌入原 p63v1_audit 后，
未显式关闭其 BEGIN 读事务，随后另开连接读 wire；遗留读锁妨碍真实响应归档。
这是本轮执行失误，不归因于 Main 科研选择。监控现已在新连接前显式关闭原连接。

在生产代码仍为 b0f0faa 时，实际调用原 core.recover 得到
UNKNOWN_PROVIDER_SEND_INSPECT_BEFORE_REPEAT；原 converse(restore_only=True) 得到
UNKNOWN_PROVIDER_OUTCOME_RECOVER_BEFORE_SEND。两者没有发送新请求或改动科学状态。
原 bind 也要求 UNSEALED_RESERVATION_BLOCKS_BIND，故没有对原 Store 强行迁移。
没有手工 settle、填补响应、修改 Profile 或重发未知请求。请求结果的不确定性不能
由本地安全推断消除，本轮按用户允许的真实工程阻断条件结束；不自动续发余下 48 次。

实际 Store 仍冻结于 b0f0faa、Profile v3，保留 v1/v2/v3 全部身份；后续交付字段修复
仅在已结束的运行之外实施。35 项针对性回归通过，连同先前测试共 89 项不同测试；
输入、断言、结果和红灯日志见 p63r_scope_validation.json。对当前第三轮结果的修正
投影已只读核对全部范围、resolved_domains 和已注册底层数学引用，未改 Store；
但不能声称此修正已到达真实 Main，或声称真实 Main 已收到第三轮结果后作出决策。
后续隔离 Mock 验收使用完整保留的接续前 24/94 Store/SDK 检查点，不把副本作为新 Study。

约新增 5 次 Provider 的只读检查点实际记录于总数 32；锁竞争造成监控晚于阈值 29。
新增 15/30 次检查点未到达，不伪造。所有 Native Worker 均确认终止，数学 pending 和
未消费响应均为空；唯一未封口调用是上述 unknown Reporter 请求。原 G3 数据库、
原 94 数学结果/费用、原两轮 Search、旧候选/控制、任务和预算均逐项保持。

## 费用与研究限制

已保存响应合计 279098 tokens（prompt 265649、completion 13449）；缺失第 32 次
响应的 tokens 和收费未知，不当作零。原请求计数保留 32/80，未知调用占用保留。
Provider 货币费用未提供。保存的 mathematical numerical_s 为 7132.6343315000995 s，
construction 为 76.89217760012252 s，control-initialization 为 43.13034969998989 s。
已报告 Native kernel wall 为 6689.246085399936 s、rollouts 69464、physics steps
69464000；18 项 incomplete 缺少详细 Native 成本，缺项保持未知。外层搜索时间、
Worker 和 kernel 时间存在重叠，不能再次相加为总费用。完整账本见 p63r_live_audit.json。

本轮证明旧最佳关键数字可进入真实 Main 并保留原科研上下文，也暴露了引用理解错误、
直接范围字段遗漏和监控连接生命周期缺陷。没有验证出自主独立复验、正式通过或合法
Main 收尾。未来只有获得未知请求的外部确证并走原恢复/绑定机制后才能继续；当前
保留冻结代码与完整证据供审计，不擅自扩展预算或开展第二轮任务。
