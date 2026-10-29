# P6.2-K 交付记录

目标分支：`codex/p6-2k-knowledge-consolidation`。接口基线：`9d2ca3e288b41cfe425e34eac2555f3465d9f0d0`。本轮不合并、不改写主线；所有真实 Provider、数学 Worker、物理 Worker、NMPC、RL 新执行均为 **0**。

## 九项 Research Trace

全部复用 `project_research_success_case_v1`，未建立平行 Case Schema。M1–M6 复用六张原卡及已核验的 review，选择实际改变路线的事件；C1/PHS 提炼原日志；P3 原文件与原提交内容相同。

| Case | 里程碑 | 验证状态与边界 | Trace |
|---|---:|---|---|
| M1 | 7 | 三个 Reach/Hold 目标均由原评价器接受；首轮中心高目标失败，分组假设后重新优化并独立回放。 | [原 Trace](../../memory/cases/m1_research_v1/success_trace.json) |
| M2 | 7 | 三种外力工况接受；保留严格阈值约 8.96e-16 的超限及同候选、同控制的有限续算。 | [原 Trace](../../memory/cases/m2_research_v1/success_trace.json) |
| M3 | 6 | development draft 协议通过，有原 SELECT 记录；不是正式 Benchmark approval。 | [原 Trace](../../memory/cases/m3_research_v1/success_trace.json) |
| M4 | 6 | 0.6 s 定时反转 Tracking 通过；没有虚构失败、诊断或结构修改。 | [原 Trace](../../memory/cases/m4_research_v1/success_trace.json) |
| M5 | 6 | 0.6 s 位置与有向轴联合约束通过；没有虚构失败路线。 | [原 Trace](../../memory/cases/m5_research_v1/success_trace.json) |
| M6 | 7 | 20 g 工具定向扫描及逐步无接触检查通过；保留不完整数值失败、材料与分组修改，因果未隔离。 | [原 Trace](../../memory/cases/m6_research_v1/success_trace.json) |
| C1 | 7 | 同一 XML 四工况独立 PASS；四腱仅为已测成功的最少数量。M1_B 采样间速度超出采样阈值，不能宣称连续时间通过。 | [原 Trace](../../memory/cases/c1_multicondition_research_v1/success_trace.json) |
| PHS-2D | 9 | 十工况开发性见证，独立、半步长及扰动核查；无注册 SELECT，无一般稳定性或硬件证明。 | [原 Trace](../../memory/cases/phs2d_passive_research_v1/success_trace.json) |
| P3 | 12 | 原冻结任务通过，2 单元通过，原步长下 4 单元 INVALID；保留原 Trace，未声称空间收敛。 | [原 Trace](../../memory/cases/p3_passive_progressive_stiffness_v1/success_trace.json) |

所有案例均是 Codex/operator 编排与既有固定数学/物理程序的历史研究，未发现可据此声明 LLM 自主研究的依据。各节点注明选择来源；固定优化器的数值搜索不等于自主选择路线。P3 的所有权与分开成本补在索引元数据，未重写其原 Trace。

原 Store、注册评价器和历史成本继续拥有科学事实；Trace/Knowledge 只作 context_only。M3 保留 draft；PHS 保留开发等级；P3 保留四单元 INVALID。M4/M5 的成功首尝试没有被补写成失败—诊断故事。

## 历史成本

| Case | 原数学调用 | 原独立物理回放启动 | 已记录 numerical_s | 范围 |
|---|---:|---:|---:|---|
| M1 | 7 | 6 | 157.159067800 | 原 Store 累计，失败包含在内，构建时间另列在 Trace |
| M2 | 6 | 5 | 135.375841400 | 原 Store 累计，失败包含在内，构建时间另列在 Trace |
| M3 | 3 | 2 | 119.137913700 | 原 Store 累计，失败包含在内，构建时间另列在 Trace |
| M4 | 1 | 1 | 9.112563900 | 原 Store 累计，失败包含在内，构建时间另列在 Trace |
| M5 | 1 | 1 | 5.842203100 | 原 Store 累计，失败包含在内，构建时间另列在 Trace |
| M6 | 4 | 3 | 47.509098800 | 原 Store 累计，失败包含在内，构建时间另列在 Trace |

C1：2,118,788 个物理步尝试、2,118,787 个确认步；两次误设载荷共 452 步仍计费但排除性能比较。已知 native kernel 194.450232300 s、已完成 case 214.830294900 s 是重叠口径，不能相加；一次失败回放时长未知。四个最终独立验证各 600 步。

PHS-2D：Round 3 累计 303 次数学调用、3,456,000 步、3429.037302200 numerical_s，含 Round 3 v1 继承的 928,000 步；不是 P0/Round 2 全部历史累计。P0 未获得合格基线且 100,000 步用尽；Round 2 没有六工况见证；额外授权的新 campaign 没有抹除旧失败。

P3：原任务数学 161 次、物理步尝试 3,619,532；空间检查是另一 campaign，数学 2 次、物理步尝试 960,000。两者没有冒充一次原任务成本。货币费用缺乏发票，不从秒数推算；所有本轮新增成本为零。

## 唯一索引和版本处理

完整入口是 [memory/diagnostic_index.json](../../memory/diagnostic_index.json)。原主线 8 项、P6-F 15 项、P3 10 项按 `entry_id@revision` 的并集为 **17**，不是 33；16 个重复精确键内容相同，无冲突。本轮增加 8 个派生 Case 和 8 个方法版本后为 **33** 项：9 个 success_case、1 个旧 draft case、23 个 procedure。

主线八项及六个 BF @1 原内容保留；P6 英文 strict-near-tolerance@2 保留，新补来源的英文版本为 @3。P3 方法 @1 原样保留，@2 合并 PHS 的有限形变/松弛/平衡/KKT、有效配对及空间失效边界。新 model-physics-comparison 是跨案例独立方法，其余复用同主题身份升 revision。BF4/5/6 没有被错标为 M1–M6 成功案例。

| 精确键 | 用途 | 来源案例/档案 | 处理 | 文件 |
|---|---|---|---|---|
| `nmpc-feasibility-case@draft` | 历史 draft Case | 既有 NMPC/RL 诊断档案，原引用保留 | 保留原版及原验证等级 | [内容](../../memory/nmpc_feasibility_case_draft.json) |
| `nmpc-feasibility-procedure@draft` | Knowledge | 既有 NMPC/RL 诊断档案，原引用保留 | 保留原版及原验证等级 | [内容](../../docs/nmpc_feasibility_procedure.md) |
| `nmpc-stopping-selection@1` | Knowledge | 既有 NMPC/RL 诊断档案，原引用保留 | 保留原版及原验证等级 | [内容](../../memory/diagnostics/nmpc-stopping-selection_v1.json) |
| `offline-verification-gates@1` | Knowledge | 既有 NMPC/RL 诊断档案，原引用保留 | 保留原版及原验证等级 | [内容](../../memory/diagnostics/offline-verification-gates_v1.json) |
| `nmpc-whole-window-speed@1` | Knowledge | 既有 NMPC/RL 诊断档案，原引用保留 | 保留原版及原验证等级 | [内容](../../memory/diagnostics/nmpc-whole-window-speed_v1.json) |
| `rl-pre-failure-state@1` | Knowledge | 既有 NMPC/RL 诊断档案，原引用保留 | 保留原版及原验证等级 | [内容](../../memory/diagnostics/rl-pre-failure-state_v1.json) |
| `rl-surrogate-boundary@1` | Knowledge | 既有 NMPC/RL 诊断档案，原引用保留 | 保留原版及原验证等级 | [内容](../../memory/diagnostics/rl-surrogate-boundary_v1.json) |
| `rl-spent-vs-inherited@1` | Knowledge | 既有 NMPC/RL 诊断档案，原引用保留 | 保留原版及原验证等级 | [内容](../../memory/diagnostics/rl-spent-vs-inherited_v1.json) |
| `research-contact-causality@1` | Knowledge | BF6 | 保留 BF 通用方法旧版 | [内容](../../memory/diagnostics/research-contact-causality_v1.json) |
| `research-stable-start@1` | Knowledge | BF6 | 保留 BF 通用方法旧版 | [内容](../../memory/diagnostics/research-stable-start_v1.json) |
| `research-bounded-continuation@1` | Knowledge | BF6 | 保留 BF 通用方法旧版 | [内容](../../memory/diagnostics/research-bounded-continuation_v1.json) |
| `research-strict-near-tolerance@1` | Knowledge | BF5, BF6 | 保留 BF 通用方法旧版 | [内容](../../memory/diagnostics/research-strict-near-tolerance_v1.json) |
| `research-timed-tracking@1` | Knowledge | BF4 | 保留 BF 通用方法旧版 | [内容](../../memory/diagnostics/research-timed-tracking_v1.json) |
| `research-witness-and-cost@1` | Knowledge | BF5, BF6 | 保留 BF 通用方法旧版 | [内容](../../memory/diagnostics/research-witness-and-cost_v1.json) |
| `research-strict-near-tolerance@2` | Knowledge | BF5, BF6 | 保留 P6 英文版 | [内容](../../memory/diagnostics/research-strict-near-tolerance_v2.json) |
| `p3-passive-progressive-stiffness-success@1` | Research Trace | P3 | P3 本地增量原内容复用 | [内容](../../memory/cases/p3_passive_progressive_stiffness_v1/success_trace.json) |
| `passive-force-response-research@1` | Knowledge | P3 | P3 本地增量原内容复用 | [内容](../../memory/diagnostics/passive-force-response-research_v1.json) |
| `owner-m1-research-trace@1` | Research Trace | M1 | 新增派生 Trace | [内容](../../memory/cases/m1_research_v1/success_trace.json) |
| `owner-m2-research-trace@1` | Research Trace | M2 | 新增派生 Trace | [内容](../../memory/cases/m2_research_v1/success_trace.json) |
| `owner-m3-research-trace@1` | Research Trace | M3 | 新增派生 Trace | [内容](../../memory/cases/m3_research_v1/success_trace.json) |
| `owner-m4-research-trace@1` | Research Trace | M4 | 新增派生 Trace | [内容](../../memory/cases/m4_research_v1/success_trace.json) |
| `owner-m5-research-trace@1` | Research Trace | M5 | 新增派生 Trace | [内容](../../memory/cases/m5_research_v1/success_trace.json) |
| `owner-m6-research-trace@1` | Research Trace | M6 | 新增派生 Trace | [内容](../../memory/cases/m6_research_v1/success_trace.json) |
| `c1-multicondition-research@1` | Research Trace | C1 | 新增派生 Trace | [内容](../../memory/cases/c1_multicondition_research_v1/success_trace.json) |
| `phs2d-passive-research@1` | Research Trace | PHS2D | 新增派生 Trace | [内容](../../memory/cases/phs2d_passive_research_v1/success_trace.json) |
| `research-timed-tracking@2` | Knowledge | BF4, M4, C1 | 合并来源并新增版本 | [内容](../../memory/diagnostics/research-timed-tracking_v2.json) |
| `research-strict-near-tolerance@3` | Knowledge | BF5, BF6, M2 | 合并来源并新增版本 | [内容](../../memory/diagnostics/research-strict-near-tolerance_v3.json) |
| `research-stable-start@2` | Knowledge | BF6, M6, C1 | 合并来源并新增版本 | [内容](../../memory/diagnostics/research-stable-start_v2.json) |
| `research-contact-causality@2` | Knowledge | BF6, M6, PHS-2D | 合并来源并新增版本 | [内容](../../memory/diagnostics/research-contact-causality_v2.json) |
| `research-bounded-continuation@2` | Knowledge | BF4, BF6, M1, M2, M3 | 合并来源并新增版本 | [内容](../../memory/diagnostics/research-bounded-continuation_v2.json) |
| `research-witness-and-cost@2` | Knowledge | BF5, BF6, M1, M2, M3, M4, M5, M6, C1, PHS-2D, P3 | 合并来源并新增版本 | [内容](../../memory/diagnostics/research-witness-and-cost_v2.json) |
| `passive-force-response-research@2` | Knowledge | P3, PHS-2D | 合并来源并新增版本 | [内容](../../memory/diagnostics/passive-force-response-research_v2.json) |
| `model-physics-comparison@1` | Knowledge | C1, PHS-2D, P3 | 新增独立方法 | [内容](../../memory/diagnostics/model-physics-comparison_v1.json) |

## 来源审计和可复核性

[来源清单](p62k_source_audit.json) 记录实际本地路径、原提交、原 Store/结果 ID、原始文件 SHA-256、可用状态、去重对照。开始时独立核对 Git：P3 本地 HEAD `6b982c7b45a334ef2dcabb491aa5d41e8afa3039`，没有把它假装为已存在远程分支。

[只读复核结果](p62k_source_recheck.json)：111 份文件全部匹配，变更 0、缺失 0，包含 13 个原 Store。M1–M6 原 SELECT、accepted 与导出引用对应；C1 同模型 XML SHA 与独立核查对应；PHS 最终结果 refs 与原 Store 对应。复核脚本为 `python -m tests.research.p62k_source_audit`，仅读取文件，不启动计算。其他机器若无本地私有资料，会明确返回 unavailable_local_source，不冒充远程可复核。

内容中的 repo 来源链按 UTF-8/LF 规范化哈希；原本地资料清单使用原始字节哈希，二者没有混用。审计哈希仅是历史溯源资料。未提交原私有 Store、原私有卡正文、完整成功控制、成功结构配置、凭据、无关导出或大型 experiment_journal。

## 正式检索、权限和上下文

新 Study 默认启用公共方法发现。在原 `resolve` 中一次解析既有 P3 KnowledgePolicy，冻结获准目录元数据；不冻结正文。`off`、include/exclude、allowed_kinds、benchmark-answer 授权在准备时确定；独立盲测/排除集必须在准备前声明原冻结策略。旧封存 Study 不补写配置，不因目录统一获得新增案例或新方法版本；其原私有卡仍只属于原 Study。

九项 success_case 均为 benchmark_sensitive，需冻结的 `allow_benchmark_answers=true` 才进入授权目录。默认启用的方法知识没有完整成功参数或控制配方。旧八项非公共状态仅保留档案，没有借本轮升级为公共或正式接受。

L0 固定程序按任务元数据选最多两个方法，优先任务直接匹配及最新 revision；只含标识、一句方法、适用任务、边界和 read_query，无正文、自动回执或采用声明。无直接匹配仍给 search。`experience_retrieve` 沿用 search/read；search 返回获准元数据、不读正文，默认不截断；可选 limit 仅用于调用者主动限量，不设 20 条硬上限。read 直接读取当前获准文件。

用户在本轮明确要求取消过度防御：已删除新增的正文冻结哈希、运行时一致性哈希检查、检索时重复索引冲突检查、每次读取重做配置验证和已冻结目录权限筛选，以及默认 1 条/最多 20 条搜索限制。解析器直接重建目录，不因外部传入内部 manifest 另设错误；原只读 diagnose 可选状态保留。没有新增校验 Worker、审查 Agent 或批准步骤。既有精确读取回执的 content_sha256 保留兼容，仅标识实际已读内容，不比较、不阻断读取。

Reporter 继续用 experience_queries 读取获准上下文，记录 reader=reporter，排除于科学 source_catalog，不授予 Main 阅读进度或 SELECT/STOP 信用。Main 的实际读取和正文交付状态继续通过现有 Store/Handoff 恢复，不把发送成功当作理解或采用。

P3 原 Trace 是原中文内容，不伪造英文来源或人工翻译审核；非英文限制的授权 Study 可精确读取，english_sources Study 仍遵守原来源语言政策，可使用新增英文 passive-force-response-research@2。其余八项派生 Trace 和八个新方法版本为新写英文，无人工审阅声明。

## P6-F 最小接口收尾

资源比较按同名、单位、time_basis 和来源 JSON pointer 配对，保留 current/baseline、带符号 delta、numeric_change 和双方证据位置。3210 < 3316 明确为 decrease，不能反说 increase；未知偏好仍是 preference=unknown、direction=unknown，不能由资源减少推导效率提升。资源差值单列 comparisons.resources，不混入原科学指标。Reporter wire 和紧凑 findings 继承这些事实。

工具说明区分 research_investigate 对已有资料的只读解释、旧只读 diagnose、候选绑定 diagnose 方法选择及 research_analysis 的独立执行。无候选不把绑定数学执行标为 ready；不收紧旧只读 diagnose。普通调查优先紧凑事实、interpretation_query 和精确 JSON pointer；保留 evidence_read(full) 及 SELECT/STOP 正式读取要求。admit_decision、Plan/AnalysisRequest/EvidenceQuery 的科学契约和任务成功判定 AST 与 P6-F 相同。没有迁移 P3 Harness、Provider 或科学实现。

## 离线验证

最终测试及尺寸数据见 [验证记录](p62k_validation.json)。14 个相关 unittest 模块覆盖新目录/九案例、旧八项与版本并集、来源链、英文发现、授权/私有/关闭、直接读取修改后的文件、搜索无正文 IO、Reporter 非科学角色、真实 SDK Mock HTTP 的正文交付/Handoff、原 Provider Schema、SELECT/STOP、预算及 F1。所有 SDK 请求由 MockTransport 返回，异常/中断日志属于恢复测试 fixture；没有真实 Provider 或科学 Worker。

## 提交与主线同步

纯内容提交：`887a8593b`、`a920639b9`。接口与离线测试、交付文档分别提交；最终 SHA/远程状态由交付回复及 Git 分支标识。主线 `mainline/softarm-codesign` 内容基准仍是 `4de5d5d475755578653e9cca8febe395adeb8764`，本次没有部署到其 worktree。

后续在基于主线的临时集成分支，按本次最终索引白名单同步相对旧八项新增的 25 个内容文件和完整索引，保持八个原文件不改。仅 cherry-pick 两个内容提交不能假定已包含 P6 基线的七个既有文件：六条 BF @1 和 strict-near-tolerance@2 必须从本次最终树一并同步；索引冲突必须按精确键审阅。纯内容提交可单独比对和选择。较早主线不应整支合并 P6 开发历史；只在需要检索行为时审阅本轮接口提交的局部改动，并先满足既有 P6 接口依赖。新的 Study 从该 checkout 准备后才获得新目录；旧封存 Study 不重解析。文档与本地审计可单独同步。

P6.3 可复用现有候选身份、注册数学方法目录、候选绑定 research_analysis、原始 evidence_read/full/fields/range、working_set、Reporter 委托和 Handoff。知识不增加计算授权或验证等级；本轮未实施 P6.3、未重跑完整自主科研。

## 本轮追加的信息收尾与只读数学接口审计

按用户后续确认，梯度部分仅只读审计，不实现梯度系统。[专项报告](p62k_information_and_p63_audit.md) 给出原 P6-F 事件 53 的工具构造问题、事件 99 大报告的 full/summary 尺寸对比、资源 wall/CPU-time 语义及 M1 两连续参数最小问题。原大报告 summary 复用 Reporter 投影，保留全部 13 项指标和 4 项失败。唯一额外读取边界修改是 core.py 中科学报告的既有 summary 分支。

额外试跑 test_c1_method_context 的三项失败（旧 Mock lookup 缺省、旧 wire 大小断言、旧方法状态断言）已在未改动的 P6-F 基线 9d2ca3e 原 worktree 逐项复现，错误相同；未借本轮改写科学适用性或历史 wire。测试记录中单列，未当作新增回归通过。

接口提交：4d4f6200e5d0bacfdc3929db4cf811bcd35c9954。最终追加修复后，10 个相关模块的 100 项离线回归通过（133.580 s）；此前 14 模块的 127 项兼容回归通过。所有真实执行预算使用为 0。
