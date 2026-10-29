# P6.1 — Research Information Flow V1

基线：`44667616bf1a6b98876e48889b2782f0a353d7d8`。开发分支：`codex/p6-1-research-information-flow`。
开始时通过远端 `ls-remote` 确认目标主线未前进；开发在独立工作树进行。没有修改封存 Study、原始证据或主线分支。

## 启用与兼容

仅在**新 Study** 的既有配置位置设置：

```json
{"research_decisions":{"tool_schema_policy":{"version":"research_information_flow_v1"}}}
```

这是唯一新增版本选项，继续要求已有 English architecture 和 `recent_round_trace_v1`。英文来源准入复用已有 `english_sources_v1`，没有第二个信息流开关。旧 `on_demand_tools_v1/v2/v3` 的 L0 结构保留；旧 Study 不自动升级。固定系统提示词保持冻结，动态投影仍置于请求末尾 `CURRENT_RESEARCH_PACKET`。

`Plan` / `ResearchDecision` 原始科学契约与 Host 准入没有改变。STOP/SELECT 的原字段仍校验，但 Schema 明确要求既有主张、证据或收尾理由，不要求新设计假设，也不自动填入虚构假设。`ResearchRecallQuery` 只新增可选的 `trace=actions|milestones`，默认仍为原动作历史。

## 信息所有权与实现位置

| 模块 | 本轮职责 |
|---|---|
| `tools/research/research_context.py` | 在既有 brief 上作最终 L0 投影；从 Store/Plan/结果恢复 research_focus；将同一 Action Trace 投影为 Milestone Trace；保留尚无反馈的正式工具提交；提供稳定事件步骤分页。 |
| `tools/research/agent.py` | 保留已选 Plan，并直接暴露当前合法的读取/调查工具；新 L0 接入现有请求尾部；引用拒绝显示角色、原因和合法修正。 |
| `tools/research/evidence_policy.py` | 注册清单增加来源角色与可支持推论标记；FamilySpace 是 domain_reference，读取不会将其注册成结果。无科学结果时明确展示空清单与合法探索的 `supporting_evidence=[]`。 |
| `tools/research/provider.py` | 集中进行 Provider Schema 投影；恢复时只使用与原 wire 匹配的投影，继续执行原完整 wire 校验。 |
| `tools/research/reporter.py` | 问题与结果引用即可发起委托；复用结果卡、有限结构发现、diagnostic_relations 和精确 reads；保存 selected_reads；保留差值、成本、缺失项和原始恢复入口。 |
| `tools/research/experience.py` | 英文搜索只返回来源声明合格的条目；精确读取、内容哈希、阅读回执沿用现有 Store。 |
| `tools/research/session_handoff.py` | 统一定位旧/新 packet 的反馈；显式读取的短英文 JSON 经验正文可原样经过轮换，并由确认的 wire 证明送达。 |
| `tools/research/config.py`、`contracts.py` | 校验上述单一版本和历史分页参数。 |

没有新增生产模块、状态数据库、Evidence Store、Reporter 工具或长期记忆。`evidence_views.result_card` 及原数学/物理投影继续提供数值权威。

L0 的十项所有权：study_goal 来自冻结任务；research_focus 来自已有 Plan 与候选；verified_facts 来自固定程序的有来源数值；research_trace 来自原事件/回执；capabilities 展示 Design、Control、Mathematical Research、Physical Validation、Evidence & Knowledge 五类；tool_continuation 管理已选、已加载、待反馈状态；knowledge 仅展示入口与阅读进度；reporter_findings 保存解释及引用；evidence_access 给出原始恢复、科学强度与正式读取规则；budget 来自既有账本。

旧 L0 的 `current_intent`、`history_trace`、`research_state`、`recent_round`、`tool_directory` 不再作为重复顶层字段输出。Reporter 数值统一进入 verified_facts，解释仍标识为非权威内容。未决问题只能来自原 Plan 的削弱观察或有引用的 Reporter 问题，不由固定程序创作。

完整 Action Trace 包含提交、待反馈、拒绝、回执和科学结果引用。Milestone 使用固定规则：已有科学结果、失败/拒绝/待定、各候选首次完成生成或控制初始化、正式 SELECT/STOP。L0 保留最近四个节点及至多两个较早未决失败；所有原节点可通过 `research_recall` 按事件步骤、offset/limit 恢复。Reporter 不维护 Trace。

## 委托读取与 Schema

Main 调用现有 `research_investigate(question, references, reads?)`。固定程序组装结果卡与合法比较，未给 reads 时提供有限的结构发现；精确读取返回实际值、单位和来源，缺失路径记录 unavailable 与导航建议。Reporter 只接收这些卡片、选中读取及 source_catalog，不接收 Main 全部对话或完整 Study。handoff summary 保留实际指标、比较差值、可比性、成本、限制和完整报告引用。解释失败、共享预算或当前调用上限不足时，确定性报告仍保留且状态为 unavailable。重复的显式调查绑定各自的 Store 事件步骤，完全相同的问题与引用也按正常预算处理；原回执恢复则复用已保存报告，不重复发送。

Reporter 读取与报告均不注册新科学结果，不获得 SELECT/STOP 的正式读取资格；Main 的原始整结果直接读取路径保留。知识引用独立于科学 source_catalog。

Schema 链路为：Canonical Pydantic → focused action/method Schema → `provider_schema` → 原 Host/Pydantic/选定 Schema 校验。顶层 allOf/anyOf/oneOf/not 放入恒真条件的 then 中，保留完整约束和根 `$defs` 引用；没有删除 saved_state 与 execution/update_id 的互斥条件。包括 selected_analysis 的真实 SDK 格式化路径在离线测试中验证。此处仅验证已知的顶层组合限制及 JSON Schema 等价性；官方 API 的真实接纳与模型表现留给 P6.2。

## 英文 Knowledge

新增 `research-strict-near-tolerance@2`，从三个历史 Git 原始摘要重新撰写英文指导，逐一核对原始 blob 的 SHA-256。保留 BF5 成功与 BF6 R7 严格失败的适用范围、未舍入数值、历史成本、原来源和版本。历史数值以 evidence_index + JSON Pointer 绑定来源，测试逐值复核。旧第 1 版正文不变，英文 Study 仍拒绝其未审阅中文来源。

新条目明确 `authored_english`、`human_review=not_claimed`，不伪造翻译审阅。正文仅在显式 read 后交付，确认的 Provider mock wire 与已读回执均可跨会话恢复。正文不预加载到 L0。

## 离线验证

环境：既有 `.mainline5-env`，MATLAB 已安装源码目录仅用于依赖发现，**没有启动 Engine**。缺少的 `tokenizers==0.22.2` 仅安装到工作树忽略目录 `runs/p61-deps`，使用仓库固定哈希的 tokenizer。

回归命令（PowerShell，仓库根目录）：

```powershell
$env:PYTHONPATH='<worktree>\runs\p61-deps;C:\Program Files\MATLAB\R2024a\extern\engines\python\dist'
D:\softrobot-agent\.mainline5-env\Scripts\python.exe -m unittest tests.research.test_information_flow tests.research.test_recent_round_tools tests.research.test_harness_v2 tests.research.test_openai_api tests.research.test_provider_v2 tests.research.test_f1_integration tests.research.test_research_knowledge tests.research.test_research_reporting tests.research.test_evidence_policy tests.research.test_s129_agent_reporting
```

整组 **88/88** 通过；最后引用规范化与重复调查修正后的相关边界 **55/55** 通过；去掉重复资源投影后的 Reporter 复验 **16/16** 通过（这些集合重叠，不累加为独立测试数）。无剩余失败。结果和最终源文件哈希记录于 `p61_validation.json`。覆盖无候选、已生成候选、数学结果、独立物理失败、保护收尾；Action/Milestone 分页及 pending submission；Reporter 精确值、比较差值、缺失路径、来源、只读和预算边界；FamilySpace/科学结果分离；空引用探索与正式推论限制；全部 AnalysisRequest operation 的 bound/unbound Schema；真实 SDK 的 Mock HTTP、旧 Study、正式读取、恢复与 Handoff；英文条目真实读取、原文哈希和已读进度。

修复的旧测试夹具问题：Knowledge wire 补齐 adapter；已有只读 probe 补齐现行预算字段；三会话测试改从 original_plan_query 核对已被 L0 压缩移出的 decision。最后一项也在未修改基线单独复现，属于既有测试漂移，未放宽生产规则。

所有新增数值均为明确的合成测试夹具或已封存来源的只读投影。资源边界：**0 次真实 Provider 请求、0 次新数学 Worker、0 次物理 Worker、0 次 RL 训练**。Mock HTTP 会按测试账本记账，不属于真实请求。

## 同状态大小对比

`p61_context_audit.py` 在实际基线 checkout 执行旧 `on_demand_tools_v3` 投影，再用同一封存状态、原事件前缀和同一预算作新投影。两份 Store 的数据库哈希在审计前后相同。详情：`p61_r2_metrics.json`、`p61_closeout_metrics.json`；均逐项断言任务、身份、候选、验收状态、预算、原样反馈、已加载 Plan 和系统提示词保留。

| 边界 | L0 字节（旧→新，不含原样反馈） | L0 本地估计 tokens | 工具 Schema 字节（旧→新） |
|---|---:|---:|---:|
| R2 请求 115 / handoff 110 | 13,549 → 8,438（-37.7%） | 3,782 → 2,313 | 10,985 → 16,761 |
| P4 收尾请求 60 / handoff 56 | 6,452 → 5,615（-13.0%） | 1,759 → 1,539 | 7,136 → 7,040 |

R2 的 Schema 增长用于直接开放 experience_retrieve、research_recall、research_investigate；不声称所有请求字节都下降，也不将本地 token 估计当成 API 实际用量。原样反馈分别为 1,585 与 8,768 字节，前后完全一致。

复核示例：

```powershell
python -m tests.research.p61_context_audit --baseline-repo <baseline-checkout> --source <sealed-r2-store> --study m5-main-off-experience-r2-20261028 --handoff-event 110 --request-event 115 --output runs/p61-r2-repeat.json
```

P6.2 仍需在另行授权的真实预算下测试 Reporter/Handoff 与官方 Provider 接纳、模型是否实际采用证据和选择合法动作。P6.3 的参数化数学研究、求导和优化器本轮未实现。
