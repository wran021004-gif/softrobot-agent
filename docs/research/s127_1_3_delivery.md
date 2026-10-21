# S12.7.1–S12.7.3 交付记录

2026-10-21。分支 `feat/sorosim-matlab-nmpc`；基线 `bd31326296afb6daace6db5afb1205daa8e01841`；冻结生产源码 `b8e48c7fdfecd14054f210c68d09bd7adb8fc932`。开始时已重新 fetch 并确认本地/远端基线一致，目标工作树干净；未修改其他工作树。本文和派生统计作为后继文档提交，最终远端 SHA 见交付回复。

## 验收状态

| 项目 | 已验证 | 尚未验证/阻断 |
|---|---|---|
| S12.7.1 | 三层展示、默认去重、完整科学索引、精确详情与正式资格字段 | 真实 Provider token 和决策配对效果：缺本轮独立传输及额度授权 |
| S12.7.2 | 两份真实 NMPC 输入预检、3/6 腱绑定、v2 搜索、独立工程物理评价 | 本次局部试验未通过原任务；不推断全局可控性或方法优势 |
| S12.7.3 | `offline_protocol_passed=true`；先持久化/重开验证再提交，崩溃及旧反馈恢复 | `production_recovery_validated=false`；`live_provider_continuation_unverified=true`；生产未准入 |

## 分层上下文

[同状态字节审计](../../evidence/s127_layered_context/audit.json)使用同一封存 S12.6 Store、任务、候选及预算。原始回归输入留在 `runs/s127_1_baseline.json`；状态身份为 `d366a9a2791a6d35d881ca5c11bf82c182e03c38b912536ce8b900dfb071b5f3`，审计前后状态、账本和事件均不变。

| 序列化 UTF-8 JSON | 原版 | 当前 |
|---|---:|---:|
| decision_brief | 107,041 B | 34,837 B |
| 默认工作集 | 55,315 B | 12,204 B |
| 默认请求 envelope（相同工具 Schema） | 165,962 B | 87,322 B |
| 工具 Schema | 34,008 B | 34,008 B |

默认 brief 减少约 67.45%。这是实际构造并序列化的默认请求 envelope，排除累积聊天历史，没有发送 HTTP；**字节不是 Provider tokens**。完整当前请求还包含既有 family space、控制器与分析协议。

默认只保留一次预算与方法条件，保留全部九项新科学结果的 STOP 索引、全部原任务约束的测量值/失败分量、主要候选及不同控制状态。`prerequisites_only` 保持原义，不等于科学准入。PPO 剩余 stage/actions/单次上限/评价 episodes 集中在 `budget.training`；共享物理、数学、NMPC 等额度仍由原预算函数/账本提供。

`evidence_read(reference=brief.evidence_access.reference, view="working_set", pointer="...")` 返回 `evidence_working_set_v2` 的确定性当前投影；根查询附状态身份和非科学证据标记。可读 `/candidate_index`、`/control_result_links`、`/eligible_methods`、`/method_requirements`、`/read_coverage`、`/source_references`、`/control_search_domain`。空候选状态以现有 family-space artifact 为锚点。原始 artifact 的 full/fields/range 查询继续可用。

详情为 58,771 B：通用条件去重，同时补齐原先截断的完整读取覆盖，以及完整 warm-source、数学和 PPO 参考/资格字段，因此没有以缩小详情为由舍弃这些数据。派生视图的实际交付单独审计，不计为原始 artifact 的完整阅读，也不能满足成功证据读取/SELECT。`context()` 不创建大型 artifact；所有原始验收、轨迹、控制器日志、Provider 原始数据和历史失败均保留。

## NMPC 实测输入和独立工程试验

[零物理预检](../../evidence/s127_control_handoff/preflight.json)使用 S12.6 的两个原执行引用，分别为 35×3 和 35×6。PPO 与显式控制共用 `measured_nmpc_trajectory` 和原 `ControlEvidence`，不解析第二套轨迹。要求当前 Study 注册来源、原 execution/receipt 对应、完整执行、准确配置、pre-step 实测输入、完整有序有限网格、实际腱序和逐腱力限；预测张力不能替代实测值。

`initialize_control(source=NMPC结果引用, parent=candidate, candidate=candidate)` 保存显式开环 ZOH 序列和测量来源。结构/任务重新绑定，`task_acceptance="unmeasured"`、`inherited_acceptance=false`；新控制源引用作为其身份。直接跨 Study NMPC 来源被拒绝；本试验通过原有 `research_decisions.control_seeds` 正式导入已验证的历史设计/显式序列，保留原 Study/执行/测量引用，不导入历史物理成功。

[独立工程结果](../../evidence/s127_control_handoff/experiment.json)冻结于 `8992f8fd837dece0d4939b9601b70398c325039e`。先独立开环回放，再做六腱 v2 的单系数 response 搜索，原 Reach 任务、阈值、评价器及初始化不变。最多 6 次新物理启动；实际 2 次，余量 4；原 Study 账本和状态不变。

| 执行 | 总体违反量 | holding 最大位置误差 m | holding 最大速度 m/s | 结果 |
|---|---:|---:|---:|---|
| 原六腱闭环 NMPC | 6.491882 | 0.074918816 | 0.141219774 | 失败 |
| 新开环基线 | 6.491882 | 0.074918816 | 0.141219774 | 完整、原任务失败 |
| 单系数实测探测 | 6.492278 | 0.074922782 | 0.141105185 | 完整、原任务失败 |

搜索 3 次 callback：1 次新物理、2 次 Store 复用，最佳仍为基线。探测张力相对原测量的最大变化 0.009428571 N；worker 实测计费共 2.317693 s，完整累计数值时间见验证清单。没有重跑 NMPC、Provider 调用或 PPO 训练。观测到本次开环基线与原闭环指标相同；其他任务或初始化下的轨迹一致性没有保证。

原始驱动把搜索 knot 误设为 3.5 s，正式入口在启动新物理前拒绝；[修正记录](../../evidence/s127_control_handoff/settings_repair.json)将其改为真实 0.35 s。随后零修正使 `-0.0` 变成 `+0.0`，暴露原缓存身份的问题：仅将 signed zero 规范化用于身份比较，原测量数据不改写。两次拒绝和已有基线均保留，未重置账本或扩大额度。

## 崩溃安全会话

[准入记录](../../evidence/s127_session_recovery/admission.json)、[14 场景矩阵](../../evidence/s127_session_recovery/crash_matrix.json)、[真实保存结果恢复](../../evidence/s127_session_recovery/saved_worker_recovery.json)记录边界。

准备记录保留旧/新 session、冻结源码/完整状态身份、累计预算、科学索引和原工具边界，正式指针仍指旧会话。新会话只装入权威默认工作集；通过安装的 `SnapshotSessionManager`/`LocalFileStorage` 保存并刷新文件，再由独立重建的 SDK 重开，校验会话、交接身份、工具 Schema、证据引用和 Windows 路径。Store 事务重新检查状态/账本及文件身份后才提交指针。同一准备记录从旧调用方或重启后重复提交幂等；后续完整回合可以再次交接。

真实子进程 `os._exit` 覆盖准备前/后、真实 Storage 写入中、写后验证前、验证后提交前、提交后请求前、未知首发、保存未消费响应、数学/物理待反馈、RL 活动、pass-before-SELECT、STOP 和重复恢复。最大 SDK 路径 214 字符，另预留 38 字符给临时文件；损坏/缺失快照和 Schema 不匹配均阻断，未提交的孤立快照不会自动切换。

隔离 grant 复制了实际 S12.6 保存的数学/物理 receipt 及累计账本，子进程从原工具 ID 配对并持久化反馈后退出；重开旧 SDK 消费反馈，再创建新会话，全部九项科学引用仍可读。无新科学 worker 或预算重置。旧 invocation 前缀及 HTTP 是明确的协议 fixtures，不能据此宣称原 live SDK 完整历史/真实 Provider 科研接续已经验证。

默认仍走连续 Strands 会话；`--session-handoff` 还要求独立 live admission，当前在凭证读取/发送前拒绝。已验证的未提交 checkpoint 失败可重开原 SDK 继续安全会话；指针已提交但快照损坏/丢失、未知 Provider 发送或未完成 worker 按原保护阻断，不伪造替代会话。

## 配对请求和外部授权

复用 `tests/research/s126_decision_probe.py --prepare-s127` 和既有 cutoff snapshot/interceptor，已封存[六对/12 个请求](../../evidence/s127_decision_probe/manifest.json)，[离线一致性检查](../../evidence/s127_decision_probe/offline_checks.json)通过。同一对的任务、科学索引、动作、预算和工具 Schema 相同，原始 wires 仅在本地 Store。第六对单独标为独立 HTTP 会话条件，与第五对使用同一科学快照；SDK 恢复证据另由上面的矩阵提供，不将历史差异归因于压缩。

请求上限 12、无自动重试、`https://api.deepseek.com`、`deepseek-flash`、每次最多 8192 输出 tokens。冻结 manifest 身份 `330d4b06ec479abcf97a08996430ed601de6cf751bd6c4cd1eee609571929c6a`。**尚无本轮独立授权，因此未运行**；现有 `--authorization` 仍属于旧 S12.6 runner，不能用旧授权代替本轮授权。prompt/completion/cache hit/cache miss/总 tokens、合法科学提案、首次真正科学准入顺序、有效证据交付、无必要详情读取和决策退化均为未测量；full scientific admission 为 `not_tested`。未将合成 HTTP usage 当成真实测量，未启动新的完整 Cold-start Study。[全部指标状态](../../evidence/s127_decision_probe/metrics.json)明确记录未测量项。

## 验证和 Git

[验证清单](../../evidence/s127_layered_context/verification.json)覆盖 94 个不同通过的测试 ID：90 项广泛回归，随后最终投影/覆盖/门禁/幂等/二次交接的针对性检查；各运行重叠，不累加为唯一测试数。14 个 killed-process 子场景另列。`git diff --check` 通过。依赖保持 `strands-agents==1.59.0`、`strands-harness==0.2.0`，三个数值线程变量均为 1，未升级依赖。

生产 8 文件 **+386 / -38，净 +348**；测试/审计脚本 11 文件 **+687 / -22，净 +665**。逐文件统计在验证清单。原 Agent/Store/优化器/评价器/训练器复用，未另建科研框架。

源码提交链：

```text
ad9bd418 refactor(research): layer evidence working set and remove duplicated decision context
ceff0e8e feat(research): admit measured NMPC schedules as local search starts
b2e3567f test(research): freeze valid independent control handoff grant
c66ee233 test(research): correct prelaunch search grid without resetting costs
8992f8fd fix(research): reuse measured schedules across signed-zero corrections
95587140 test(research): validate NMPC-to-open-loop control search handoff
55e7f81d feat(research): validate crash-safe session handoff protocol
b8e48c7f fix(research): keep session commit retries idempotent across restarts
```

[上传范围](../../evidence/s127_layered_context/data_scope.json)限定代码、fixtures、派生统计、精确引用和有限数值；新原始 Provider 请求/响应/推理/feedback、完整 Store/SDK、私密环境与凭证均不上传。封存 S7–S12.7 科学证据未改写；旧 S12.7 checkpoint 回归输出改到忽略的 runs，避免覆盖历史准入结论。只向指定分支普通 push，不使用 force push。

