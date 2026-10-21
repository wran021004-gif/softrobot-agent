# F1-A：科研报告与独立会话

2026-10-21。工作树 `s129-agent-reporting`，分支 `feat/s129-agent-reporting`，
共同祖先为 F0 `6e5c0e4c7f3af62cc345d44461369d795af4da4b`。
只完成 A 线工程实现和离线验证，不开展 F2 集成、F3 科研或真实付费请求。

## 边界与复用

F0 是唯一共享边界。本次没有修改 `schemas/research_reporting.py`、
`evidence_views.py`、`core.py`、`contracts.py`、证据准入或数学计算方法。
复用 F0 的 `ScientificReport`、`ResultCard`、指标、关系和非权威解释类型，
`result_card()`、原 `read_evidence(record_read=False)`、Store 和 Provider 账本。
继续使用原 prepare → snapshot → restore → verify → commit、原工具 ID 和 receipt 恢复。
没有新的数据库、预算系统、通用 Session Manager 或科学证据注册路径。

## 文件和入口

| 文件 | 入口与职责 |
|---|---|
| `tools/research/reporter.py` | `assemble(host, references, *, question=None) -> ScientificReport`：结果摘要或调查，原始指标和有条件的历史比较 |
| 同上 | `InvestigationRequest(question, references, focus=[], constraints=[...], reads=[])`：A 线本地类型，`reads` 复用 `EvidenceQuery` |
| 同上 | `investigate(host, request) -> dict`：保存问题、确定性报告，内部验证精确读取，不发模型请求 |
| 同上 | `scientific_feedback(host, value, before) -> dict \| None`：已保存科学结果的自动报告反馈；失败保留旧反馈 |
| 同上 | `complete_reports(host, transport, *, recover_only=False)`：外层回合结束后独立解释，原响应恢复和明确降级 |
| 同上 | `provider_usage(host) -> dict`：从原 Provider 事件按 purpose 汇总真实 usage、缺失状态和请求字节 |
| `tools/research/agent.py` | `converse(host, *, session_handoff=False)`：原生调查工具、自动反馈、外层 Reporter、重复轮换、动态 Schema 恢复 |
| `tools/research/research_context.py` | `research_intent(host)`：从原 Plan/ResearchDecision 和 receipt 重建假设、目的、方法、反驳条件与实际结果引用 |
| 同上 | `agent_decision_brief(host)`：主 Agent 专用投影，最新两份报告摘要、科研意图、预算、合法动作和精确清单入口 |
| `tools/research/session_handoff.py` | `handoff()` 的快照仍验证完整结果清单；`recover_feedback()` 支持新调查工具的原始 receipt，不重跑调查 |
| `tests/research/test_s129_agent_reporting.py` | 13 项离线边界测试，真实 Store/SDK，模拟 HTTP |
| `tests/research/s129_saved_reporting_audit.py` | 封存结果只读报告与指标指针核对；输出派生统计 |
| `evidence/s129_reporting/offline_validation.json` | 本轮离线测量和只读核对统计；不是科学证据或生产准入 |

## 调用链和失败语义

主 Agent 原生执行 → 科学工具保存原始结果/receipt → F0 结果卡 →
`research_report` 检索产物及立即工具反馈 → 完整主 invocation 结束并保存 →
独立 Reporter 请求 → 下一次主决策或新 Session。
控制搜索默认交付主搜索卡，子评估保留在原正式清单，不逐项发几十次模型请求。

`research_investigate` 示例：

```json
{
  "question": "保持速度的差异能否归因于控制条件？",
  "references": [{"artifact_id": "<原结果 SHA256>", "media_type": "application/json"}],
  "focus": ["holding_speed", "comparison conditions"],
  "constraints": ["Only existing saved evidence"],
  "reads": []
}
```

可以在 `reads` 中指定原 fields、range、working_set 或 JSON Pointer 查询。
Reporter 每次仅收到报告、问题和这些已选读取，没有主 Agent 对话历史，也没有科学工具。
模型只能返回 `InterpretationResponse.interpretations`；额外事实字段导致整份解释拒绝。
每条解释必须带范围内可解析来源。程序验证形状和来源，不保证自然语言推理为真。
复杂调查缺少信息时，应提出进一步调查，再由主 Agent 选择补充读取或下一项科学动作。

权威数值、阈值、成本、身份、关系和来源由确定性代码填充，模型不参与生成。
比较展示原值、基线值、差值和双方来源；不可比时明确保留 `comparable=false` 和原因，
差值仅为描述性算术。结构、控制等多因素变化不产生单因素归因。
旧 mechanics 的 `mathematical_facts` 通过 A 线适配搬运原状态、目标、迭代等字段；
不伪造 scoped claim，不改变原 `verified_conclusions`，不创建数学证书。

Reporter 使用原 LiveBoundary 的配置检查、真实发送预留、原响应保存和结算。
`purpose=reporter` 与 `conversation` 可区分；未知 usage 保持未知，不估算美元费用。
主响应未消费、未结账或 worker 活动时不嵌套发送。保护 closeout 和下一次主请求容量。
已知坏输出、截断或 HTTP 失败保存后降级为确定性报告，状态 `unavailable`。
未知发送保留 reservation 并阻止继续发送，不能以降级为由掩盖未知 Provider 结果。
已保存 Reporter 响应按原请求本地重放；启动先验证主 SDK 历史，再处理 Reporter 恢复。
每份报告至多一次解释尝试，无后台队列或自动模型重试。

报告不注册为证据，所有内部读取均为 `record_read=False`。
SELECT/STOP/RL 仍要求原正式阅读和引用；`stop_result_index.query` 精确返回
原工作集 `/all_fresh_results`。主输入不每轮展开完整库存，快照仍保存并核对完整引用。

## 会话与上下文

`session_handoff=False` 保留连续运行方式；启用后在每个合法完整 invocation 边界考虑轮换。
删除一次性 `rotated` 限制，并在重建时恢复已验证的动态工具 Schema 和删除状态。
保留 `session_handoff_live_admitted` 生产保护，不修改其默认值。
pending、未知结果、未消费反馈、活动 worker、未结账、待 SELECT 均保持原阻断。
失败保留旧 Session 和科学状态；不会重执行科学操作或清空历史。

新 Session 保留上轮 Agent 假设和 hypothesis_id、方法、预期/反驳观察、固定条件、
原结果引用与完成状态。假设明确标为 Agent 意图；报告解释继续标为非权威。
默认不复制旧消息或所有候选；完整旧 SDK/Store 留存，允许主动下钻。

## 离线验收

```powershell
$researchPython='D:/softrobot-agent/.mainline5-env/Scripts/python.exe'
$env:PYTHONPATH='C:\Program Files\MATLAB\R2024a\extern\engines\python\dist;'+(Join-Path (Get-Location) 'tests/research')
& $researchPython -m unittest tests.research.test_s129_agent_reporting tests.research.test_research_reporting tests.research.test_s127_layered_context tests.research.test_s127_working_set tests.research.test_evidence_policy tests.research.test_task_analysis_contract tests.research.test_s127_provider_output tests.research.test_s127_session_recovery -v
& $researchPython -m tests.research.s129_saved_reporting_audit ../sorosim-matlab-nmpc/runs/research/s128-cold-live-20261021 s128-cold-live-20261021 --output runs/s129_saved_reporting_check.json
git diff --check
```

73 个不同测试通过：新专项 13、F0 8、分层 9、工作集 3、证据策略 14、
任务分析 14、Provider 输出 5、会话恢复 7（含原 14 个进程中断子场景）。
先前一次组合运行因旧测试 `from test_mainline import ...` 缺少路径失败；
补上述 `tests/research` 路径后 72 项组合通过，最后新增的调查 receipt 恢复随 13 项专项通过。
旧测试使用的两个历史 SQLite 只读 backup 到本工作树 runs；无新物理搜索、NMPC、PPO。
原小型线性化/合成核测试沿用已有测试范围。旧回归生成的 scope 文件已恢复到原版本。

自动摘要覆盖物理、数学、控制搜索和独立 RL episode；非法解释/截断不改原结果或重跑科学。
真实格式原生调查完成工具 ID/反馈/receipt 配对，独立解释进入下一 Session；
缺少 AfterTool 事件时也能仅凭原调查 receipt 恢复。内部阅读不增加正式记录。
真实 SDK 连续 3 个 Session、两次轮换，另验证原工具反馈恢复后两次轮换，账本一致。

同样三轮离线输入，对照请求 UTF-8 字节为 **63344 / 123556 / 183768**；
轮换为 **63344 / 81194 / 81194**。两次新 Session 初始消息各 **17837 bytes**，
对应旧完成上下文 **60442 / 78331 bytes**，旧长历史未复制。
该合成负载仅验证体积增长控制，不代表真实科研 token 节约率。
原生调查联测：主请求 3 次，mock usage 为 prompt/completion **30/6**；
Reporter 1 次，mock usage **17/3**，请求 5996 bytes；原账本共 4 次 Provider，科学执行 0。
这些 token 是模拟响应的计量夹具，不是真实 Provider 消耗测量。

封存 S12.8 的 **82** 份报告（77 重放、2 NMPC、1 NLP、2 搜索）全部构造和 JSON 往返通过；
440 组顶层/搜索步骤指标和阈值从原 Pointer 核对，详见派生统计。原数据库 SHA256 保持
`24df37fc6afd4e489cfe957ec01aadac5f6366e63614dd19cdbef3e271522cc6`，状态/账本/事件不变。
两段 NMPC 原值保持 25.0757759705 mm、28.3798672637 mm、0.0856416282 m/s，
三项均未通过；结构/控制变化与不可比限定仍在报告中。

真实 Provider 的 Reporter 输出质量、完整科学工具组合的生产接续、实际 token/费用收益，
仍需 F2 独立验证和授权。本次不启用生产 handoff，不合并 B 线或正式科研分支。
