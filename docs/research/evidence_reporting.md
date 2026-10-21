# F0：统一证据与科研报告契约

2026-10-21。分支 `feat/s129-evidence-contract`，开发前 HEAD 为
`67c8fd9c6e79d5479a0c7ba2def00a44ffe74e70`，工作树干净。仅完成共享类型、
结果卡投影和内部读取记账开关；没有运行新的正式科研 Study。

## 审计与复用

| 现有能力 | F0 的处理 |
|---|---|
| `core.packet()`、科学 dispatch、Store 与预算准入 | 保留；不增加执行路径或成本计算器 |
| `analysis.decision_result()` / `compact_result()` | 数学结果卡直接复用前者；后者及其旧调用行为保持不变 |
| `research_context.compact_evidence()` | 复用物理约束、原任务 gap、搜索摘要；不复制完整 preview |
| `physical_diagnostic()` | 复用实测极值选择与原始样本定位，不重新计算验收或解释失败原因 |
| `context()` / `decision_brief()` / `working_set()` | 保留 L0/L2 的状态、候选、控制关系、预算及比较视图 |
| `tool_feedback()` / `read_coverage()` | 保留正式交付/阅读覆盖语义；内部结果卡不伪造交付记录 |
| `evidence_policy.summarize_evidence()`、引用库存和准入 | 原样复用可信工具结果的证据分类；不注册报告 |
| `EvidenceQuery`、`TaskAnalysisRequirement`、`ScopedMathematicalClaim` | 保留原契约和任务所有权，不定义第二套任务规范 |
| `feedback.result_view()` / `eligibility()` | 保留独立验收、身份和显式阅读要求，不把数值成功当作物理验收 |
| `session_handoff.safe_boundary()` / `trusted_history()` | 仅审计；仍由完整回合、工具反馈、pending/worker 和持久化历史约束接续 |

同时查阅 `analysis/s128-math` 的 `s128_diagnostics_math.md`、
`analysis/s128-budget` 的 `s128_diagnostics_budget.md`，以及本基线的
`s128_delivery.md`、`s128_acceptance/status.json` 和封存结果。
已有代码已经具备数学摘要、候选工作集、预算、身份与来源机制；实际缺口是统一报告类型
和内部读取关闭正式阅读记账的接口。跨证据诊断计算、报告送达与子 Agent 生命周期属于后续阶段。

## 文件与公共入口

本次修改仅涉及以下五个文件：

- `schemas/research_reporting.py`：新增 `ScientificReport`、`ResultCard` 及必要嵌套类型。
- `tools/research/evidence_views.py`：新增 `result_card(host, reference) -> ResultCard`。
- `tools/research/core.py`：`read_evidence(host, query, *, record_read=True)` 的兼容扩展。
- `tests/research/test_research_reporting.py`：8 项离线专项测试。
- 本文档。

依赖为 `evidence_views → core / analysis / research_context / evidence_policy / reporting schema`。
新 schema 继续使用 `schemas.common.Contract`、`EvidenceRef` 和
`ScopedMathematicalClaim`，并直接复用原位置 `tools.research.contracts.EvidenceSummary`；
未为目录分层移动、复制该既有类型，也没有改变旧契约的 import 路径。
`core` 不导入新投影；现有 Provider 工具 Schema 和 `EvidenceQuery` 均不增加字段。

## 契约语义

`ScientificReport.version="scientific_report_v1"`：

- `result_summary` 恰好包含一张结果卡；`investigation` 包含问题和至少一张结果卡。
- `ResultIdentity` 保留原结果、Study、实际任务与已知 canonical task、候选、控制源、
  operation、模型、评价 profile 及执行身份；未知值保持 `null`。不猜测缺失的 operation。
- `RecordedField` 只表达已记录的目的、配置、相对基线变化等信息，并附原始来源。
  投影提供候选的冻结 configuration/parameters/provenance 链接；未记录的目的或 delta 留空。
  raw measurement 中已知模型、backend、通道顺序和步长可作为有来源的工况字段。
- `ReportedMetric` 保留值、单位、阈值、是否通过、时间/窗口和证据位置。
  物理值来自原验收组件，数学样本来自原 `decision_result.margins`；两者 scope 不同。
  数学默认只展示已有决定性样本，其余覆盖、界和验证状态保留在原 scoped claim 与精确引用中。
- 搜索卡保留各起点 baseline、最近三个 proposal/coordinate、best、预测/实测改善、
  原任务指标及停止原因；全部探针/提案通过 `all_steps` 下钻。
  best 可能是差分探针；数值改善和有限搜索都不构成结构能力结论。
- `MathematicalEvidence` 直接嵌入原 `ScopedMathematicalClaim`，引用现有任务要求；
  `MathematicalQuantity` 为后续最优违反量、上下界和敏感性等保留输出槽。
  `verified`、`unverified_estimate`、`unavailable` 明确区分；不可用值必须为 `null`，
  有值时必须有 source。结构参数、控制重优化条件和问题定义都可显式保留。
- `EvidenceRelation` 冻结左右身份、比较种类、可比性、变化因素与来源。
  不可比或未知必须说明原因；多因素变化不能填入单因素归因字段。
  这些声明不替代受控比较或因果验证；F0 不计算 `diagnostic_relations`。
- `ResourceUse` 保存原记录和单位，不计算或重置预算。未知成本为 `null`，包括不可归属到
  此结果的 Provider 成本、父动作历时及 CPU 时间。worker wall、parent action wall、CPU
  及未明确计时边界的历史 elapsed 分开标记。同一 elapsed 可能在原记账与 worker 字段重复出现，
  不得把资源列表逐项相加。物理步与优化/训练步也不能混加。
- `ReporterInterpretation` 仅容纳新增信息、解释、假设、未决问题和进一步调查的文字，
  固定为 `reporter_interpretation`，没有行动命令或证据注册效果。
  `ScientificReport` 和 `ResultCard` 的 `authoritative_scientific_evidence` 固定为 `False`。

JSON Pointer 使用 RFC 6901 的空根或绝对路径，转义 `/ → ~1`、`~ → ~0`。
每个位置都指向 `reference` 中的原始内容；展示字段如 `deterministic_summary` 不是 Store 路径前缀。
类型验证不证明文字或用户填写的数值为真；生产调用方仍必须解析可信工具产物，复用既有证据策略。
`inconclusive`、见证、必要条件排除、局部诊断和数值失败均沿用原始结论，不相互升级。
静态敏感性仍不能解释为控制重新优化后的结构能力梯度。

## 分层访问与 A 线示例

四层共用现有 Store、查询和入口，无新数据库或读取工具：

```python
from schemas.research_reporting import ScientificReport
from tools.research.core import read_evidence
from tools.research.evidence_views import result_card
from tools.research.research_context import context, decision_brief

brief = decision_brief(context(host))                         # L0
card = result_card(host, original_result_reference)           # L1，内部读取
report = ScientificReport(mode="result_summary", results=[card])

# 原 registered anchor；原工作集的关系、比较和引用库存保持其现有范围。
query = {k: v for k, v in brief["evidence_access"].items() if k != "scope"}
relations = read_evidence(host, query, record_read=False)      # L2
metric = card.metrics[0]                                     # 选已有指标的结果卡
raw_value = read_evidence(host, metric.source.model_dump(),
                          record_read=False)                 # L3
investigation = ScientificReport(mode="investigation",
    question="这些已有结果支持哪些有范围的解释？", results=[card])
```

L3 的 `view="summary"`、`fields`、`range`、pointer 和分页保持原含义。
`result_card()` 的根读取经过原 protected-result 准入，随后仅组合既有只读结果投影。
默认报告不带完整矩阵、原始轨迹或重复日志；通过 detail_sources 精确下钻。

`record_read=False` 是 Python 内部关键字，不是模型可填写的 `EvidenceQuery` 字段。
它只在原查询、准入、pointer、视图与分页成功之后跳过 `guidance_reads`、
`evaluation_reads`、`rl_evidence_reads` 更新。默认 `True` 的旧行为保持不变，
包括哪些 pointer/view 可以满足正式阅读；工作集原本不记账的行为也不变。
内部结果卡不会满足 SELECT、STOP 或 RL 的显式阅读要求。
报告是否可满足某种正式阅读义务，留给 A 线在送达语义明确后处理。

## B 线输出槽示例

```python
from schemas.research_reporting import MathematicalEvidence, MathematicalQuantity

# card 来自已有数学结果；不在 F0 中重新求解。
math = MathematicalEvidence.model_validate({
    **card.mathematics.model_dump(),
    "quantities": [MathematicalQuantity(
        name="optimal_task_violation", status="unavailable",
        structural_parameters=["segments.0.length_m"],
        control_reoptimization="required").model_dump(),
        MathematicalQuantity(name="structural_sensitivity",
            status="unavailable", control_reoptimization="required").model_dump()]
})
```

B 线日后只能用真正已生成并验证的数值与来源填写相应字段；继续使用原任务规范、
coverage、模型范围及求解/验证状态。F0 不计算最优值、乘子、包络梯度、误差界、曲率、
下降保证或 STL，不增加数学求解器。也不实现子 Agent、Provider hook、自动报告触发、
Session 接续、新预算、证据注册或自然语言真实性判别器。

## 离线验收

使用原 `.mainline5-env`，从本 worktree 运行：

```powershell
$researchPython='D:/softrobot-agent/.mainline5-env/Scripts/python.exe'
# 仅供既有 capability discovery 查找本机已安装源码，不导入或启动 Engine。
$env:PYTHONPATH='C:\Program Files\MATLAB\R2024a\extern\engines\python\dist'
& $researchPython -m unittest discover -s tests/research -p test_research_reporting.py -v
& $researchPython -m unittest discover -s tests/research -p test_s127_layered_context.py -v
& $researchPython -m unittest discover -s tests/research -p test_s127_working_set.py -v
& $researchPython -m unittest discover -s tests/research -p test_evidence_policy.py -v
& $researchPython -m unittest discover -s tests/research -p test_task_analysis_contract.py -v
git diff --check
```

结果：新增 **8/8**，原四组分别 **9/9、3/3、14/14、14/14**，合计 **48/48**。
分层/工作集测试首次因 Engine discovery 缺少路径而失败；补上述现有路径后通过，无安装或求解。
既有测试依赖本地保存的 Store；通过只读 SQLite backup 复制
`../sorosim-matlab-nmpc/runs/research/s126-cold-live-20261020/platform.sqlite` 和
`../sorosim-matlab-nmpc/runs/s127-4a-decision-20261021/platform.sqlite` 到本 worktree 的同名
`runs/` 路径。`s127_decision_probe/manifest.json` 中的绝对原 Store 也必须可读。
仅有公开仓库而缺少这些本地原始数据时，不能宣称已复现对应历史回归。
新专项测试仅用合成夹具和隔离的工程测试 Store；旧测试中的 GVS 线性化及合成小核检查沿用原测试范围。

另对封存 S12.8 Store 的 **79 个物理结果和 2 个搜索结果**只读构造结果卡，均成功，
并逐项定位 **435 组指标/阈值**到原 artifact，完成报告 JSON 往返和 JSON Schema 检查。
状态、ledger、events 及数据库 SHA256 均未改变，数据库仍为
`24df37fc6afd4e489cfe957ec01aadac5f6366e63614dd19cdbef3e271522cc6`；未重新评估物理结果。
本地派生核对统计在忽略目录 `runs/f0_reporting_saved_check.json`，不复制原始科研数据。
专项测试核对数值/阈值/单位/身份/源指针、
原结果及摘要不变、各查询方式、全部三种记账、SELECT 不被内部读取解锁、报告不能作为注册证据、
不可用数学值和比较边界。没有真实 Provider 请求、MuJoCo 步进、MATLAB 会话、NMPC 或 PPO；
没有验证未来报告送达、真实子 Agent、数学新算法或完整运行生命周期，也未跑无关大规模 Harness。
