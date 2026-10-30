# P6.3 R0/R1：结果交付与同 Study 恢复准备

基线为 `32cab42a011750138504b9d63b8f218f2df3a486`，独立分支
`codex/p6-3v-result-delivery-recovery`。V1 原 Store 保持
`p63v1-m3-autonomous-feasibility-sol-20261030`，准备期间真实 Provider 仍为 24/80，
数学结果 94、两轮 Mixed Search、独立 Replay 0。没有新建或重跑科学 Study。

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

本节在原 Study 接续后补入实际 Provider wire、Main 科研决策、物理结果、SELECT/STOP
与累计费用。当前仅记录工程准备，不冒充完成自主研究。
