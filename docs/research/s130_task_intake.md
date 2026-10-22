# S130：独立任务解析与确定性编译预览

本文前半保留 N1 交付记录；后半 **S130-N2 交付** 描述当前接口和调用限制。
后续真实调用的两轮结果、最小修复与未通过事项见 [S130 真实 LLM 验证](s130_live_validation.md)。
当前最小契约修复、新旧行为对照与零请求重放见 [S130 协议修复](s130_protocol_repair.md)；
下文 N1/N2 交付记录中的强制 null、逐字覆盖拒绝和全部时序拒绝由该修复说明更新。

本次仅新增四个文件：`schemas/task_intake.py`、`tools/task_intake.py`、
`tests/research/test_task_intake.py` 和本文。没有接入科研 Agent，也没有实施 N2。

## 分支与审查

2026-10-22 开始时，已有 worktree `.worktrees/s130-task-intake` 干净，分支为
`research/s130-task-intake`，HEAD 为 `40a1a3409209565b1036c4f6fc2aaad33d3cbfa7`。
用户指定的基线 `13ddf460f9cb792cfb8e809a4e4f225c0bfd22f0` 存在，但不是该 HEAD 的祖先。
保留当前分支继续实现；未创建 worktree、reset、补合并或覆盖已有工作。
两者之间既有的 S129 代码/文档差异不属于本次修改。

已阅读 `AGENTS.md` 和请求列出的平台、Registry、研究适配器、数学约束、
Agent、manifest 接口及真实 reach_free 配置。真实关系如下：

- `TaskDefinition` 持有 goal/environment/evaluator/observations/timing/sampling，
  不含 controller settling；审批状态与 N1 草稿状态完全不同。
- `SessionInput` 将 task、robot、policy 组合。`check_definition` 通过现有 Registry
  校验 task 与绑定；`compile_input` 进一步准备执行。N1 只使用前者，不调用后者。
- `tools/research/config.py:resolve` 从任务源文件读取 `/settling`，复制到
  `/policy/controller/parameters/data/settling`。N1 不调用此 Study 解析器；测试仅用它构造快照夹具。
- `ResearchTaskAdapter.ranking_limits/holding_start_s` 读取有效快照中的终点、保持限制。
  `analysis_requirements` 生成带来源的采样约束，
  `tools/research/task_constraints.py` 再检查数学工具适用性。
  `schemas/platform_analysis.py` 的数学需求/结果不构成物理成功证明。
- `extensions/reference/implementation.py:evaluate_reach` 判定终点位置误差；
  `tools/research_tasks.py:assemble_acceptance` 组合独立评价与 profile 的保持判据，
  同时保留执行完整性、有效性、solver errors、force bounds、holding coverage 等条件。
- 当前 manifest 仅注册 `task.reach`；适配器代码虽列出 `task.tracking`，也不能据此声称
  Tracking 已有注册和执行支持。捕球、障碍物和平台扰动也不能自动替换成自由 Reach。
- `tools/research/agent.py` 的 Strands harness、Provider transport、持久化历史和预算
  是原科研执行链路。N1 不导入该模块，不访问 Session/Study/Store 或会话历史。

## reach_free 核对

`tasks/reach_hold.json` 的环境 ID 是 `reach_free`。下表均为程序读取已有值，
不是模型建议；文件名和 task 名称不能代替实际验收来源。

| 内容 | 任务源位置 | 有效 SessionInput 位置 | 读取值 |
| --- | --- | --- | --- |
| 终点容差 | `/task/evaluator/parameters/data/tolerance_m` | 同左 | 0.01 m |
| 保持窗口 | `/settling/window_s` | `/policy/controller/parameters/data/settling/window_s` | 0.05 s |
| 保持位置限制 | `/settling/position_limit_m` | `/policy/controller/parameters/data/settling/position_limit_m` | 0.01 m |
| 保持速度限制 | `/settling/speed_limit_m_s` | `/policy/controller/parameters/data/settling/speed_limit_m_s` | 0.02 m/s |
| 任务时长/采样周期 | `/task/timing` | 同左 | 0.35 s / 0.01 s |

保持区间为 `[0.30, 0.35] s`，包含端点，对应数学需求的采样索引 30…35；
终点索引为 35。它是采样判据，不是连续时间保证。单独传入 TaskDefinition 时，
视图明确缺少 settling，不填入 `SampledSettling` schema 的默认值。

`acceptance_view` 是按需只读投影：接受显式传入的 TaskDefinition、任务源 bundle
或 SessionInput，并返回原始字段路径、内容 identity、局限说明和派生保持区间。
SessionInput 分支复用 Registry controller 校验和 ResearchTaskAdapter。
bundle 分支保留原始 `/settling` 路径，不自行重建 SessionInput。
不创建第二份权威配置，不从现有 Study 重新加载可变源文件。

## N1 接口与来源边界

`IntakeProposal` 是模型响应契约；`TaskIntakeDraft` 是待确认输出。
Pydantic strict + extra=forbid 拒绝类型转换、额外字段和非法结构。
草稿包含原始任务、目标与对象引句、意图、行为/约束/观测量/环境/验收候选、
阶段关系、缺失定义和未验证的 LLM 解释。所有要求的 confirmation 均为 required。

四类来源的规则：

- `user_explicit`：仅允许原文引句，程序核对引句存在，值保留原文和单位。
- `verified_configuration`：模型只能返回视图中已有字段的指针，不能提交 value；
  程序解引用并附加 source identity。这里只验证配置来源，不宣称物理验证成功。
- `llm_candidate`：只能给待确认的问题，值为 null；禁止提出带数字的候选默认值。
- `undefined`：缺失定义问题，值为 null，同时列入 missing_definitions。

要求引句必须覆盖全部原文的字母/数字/汉字，避免静默漏掉参数或额外约束。
阶段关系引用已有、不同的 requirement ID，并附原文引句。
这些检查不证明 LLM 分类或时间关系理解正确：解释、问题和意图都是未验证建议，
还需人工审阅；没有把自由文本解释变成物理信号、阈值或可执行声明的代码。
N1 不做单位换算、STL 编译或完整任务本体。未注册意图照原样保留，
execution_support 始终为 not_assessed，executable 始终为 false。

最小复用入口是 `acceptance_view(value)`、`parse_response(text, content, ...)`、
`request_draft(text, enable_provider=False, ...)` 及 `TaskIntakeDraft`。
后续 N2 可以读取草稿逐项确认，再通过原有接口处理；本轮没有草稿到
TaskDefinition/SessionInput 的转换器，没有自动审批、注册 evaluator 或执行路径。

## 离线 CLI

在目标 worktree 中运行。以下生成的是合成响应夹具，不是科研证据：

```powershell
$py = 'D:/softrobot-agent/.mainline5-env/Scripts/python.exe'
& $py -c "from pathlib import Path; import json; from tests.research.test_task_intake import CASES; p=Path('runs/intake-demo'); p.mkdir(parents=True,exist_ok=True); text,response=CASES['catch']; (p/'task.txt').write_text(text,encoding='utf-8'); (p/'response.json').write_text(json.dumps(response,ensure_ascii=False),encoding='utf-8')"
& $py -m tools.task_intake --file runs/intake-demo/task.txt --response-file runs/intake-demo/response.json
& $py -m tools.task_intake --text '让末端到达目标；然后保持 2 s；全程不能超过 5 N'
```

第二条解析夹具并输出 JSON 草稿。最后一条演示默认关闭 Provider：返回
`PROVIDER_DISABLED_USE_OFFLINE_FIXTURE`、draft=null、退出码 2。
直接文本也可搭配匹配的 `--response-file`。可选 `--context tasks/reach_hold.json`
添加配置视图；上下文不会自动成为新任务的要求。`--finish-reason length` 测试截断。
成功退出码 0；输入/解析失败退出码 2，不修复 JSON，不输出部分草稿。

N1 当时真实调用使用 `--enable-provider --model <name>`、可选 `--base-url` 和
OpenAI SDK 标准环境变量；**N2 已取消该凭据/地址回退**，见下方独立 Provider 约定。
独立客户端只发送一条 JSON 模式请求，max_retries=0，
无 tools、无调用循环、无历史、无自动重试。本轮没有真实调用，Provider 分支仅用 mock 验证。

## 验证

```powershell
& $py -m unittest tests.research.test_task_intake tests.research.test_task_analysis_contract.TaskAnalysisTests.test_frozen_translation_and_distinct_holding tests.research.test_task_analysis_contract.TaskAnalysisTests.test_old_contracts_and_acceptance_unchanged tests.research.test_task_analysis_contract.TaskAnalysisTests.test_signal_semantics_and_unsupported_requirements tests.research.test_evidence_policy -v
```

结果：27 tests，全部通过（其中 N1 10 个测试方法，内部含多案例）。
覆盖 Reach/Reach-and-hold、Tracking、障碍物 Reach、捕获保持下落球、扰动平台下末端稳定；
参数、附加约束、阶段关系、四类来源、配置值确定性读取和不支持任务保留。
反例覆盖伪造/遗漏引句、假配置路径、模型自填数值、类型错误、重复字段/ID、
非法时序引用、空/非法/截断响应、拒绝和异常工具调用、Provider 异常及默认关闭。
CLI 已通过 UTF-8 文件、直接文本和实际 `python -m` 子进程测试。
现有数学约束、验收及证据边界回归通过，冻结 task/config/evaluator 无文件修改。

测试是合成模型响应的契约与集成验证，不是实际模型的自然语言理解准确率评估。
没有启动 MuJoCo/MATLAB/NMPC/PPO，没有调用真实 Provider，没有改动原科研 Agent、
Store、Registry、冻结任务、验收标准或科研证据，也没有合并主线。

## S130-N2 交付（2026-10-22）

工作目录 `D:/softrobot-agent/.worktrees/s130-task-intake`，分支
`research/s130-task-intake`，开始时干净，N1 HEAD 为 `78e69d51`。
已读 AGENTS.md、N1 文档及四个新增文件。基线仍为 `40a1a340`；未 reset、重建分支或补合并。
`40a1a340..13ddf460` 的四个 F2.1 提交为 `ea637c1f`、`8a1640c6`、
`c8dd71de`、`13ddf460`。逐文件比较后，本任务依赖的 `schemas/platform.py`、
`tools/platform_tasks.py`、`tools/platform_registry.py`、`tools/research_tasks.py`、
`tools/research/task_constraints.py` 无差异。Agent、Reporter、研究上下文等差异保持原状。

本次只扩展 N1 四个文件并新增 `tests/research/test_task_intake_compile.py`；
没有平台基础模块重构、第二套注册/评价/配置契约、依赖安装或 Agent 框架。

### 独立 Provider 入口与真实调用准备

检查发现 N1 的 `OpenAI(base_url=None)` 会继承标准 SDK 服务设置，存在连接到其他服务的风险。
N2 明确要求：

| 设置 | 当前规则 |
| --- | --- |
| API Key | 仅 `TASK_INTAKE_API_KEY`，不读 `OPENAI_API_KEY`、`DEEPSEEK_API_KEY` 或科研配置 |
| Provider 地址 | 显式 `--base-url`，否则仅 `TASK_INTAKE_BASE_URL`；两者都无则拒绝 |
| 模型 | 显式 `--model`，不自动选模型 |
| 地址校验 | HTTPS，禁止内嵌用户名/密码、query 和 fragment |
| 请求上限 | 一次调用最多一条请求，`max_retries=0`，无工具和对话循环 |
| 响应/时间上限 | 默认 2000 tokens、30 s；N2 原范围 1–4096 tokens，后续用户授权提高为 1–8192；时间仍为 (0,60] s |
| 思考模式 | 后续真实验证新增可选 `--thinking disabled/enabled`；省略时记录 provider_default，不改变原 SDK 默认请求 |

检查时仅发现另一服务的 `DEEPSEEK_API_KEY` 环境变量名；没有读取或输出密钥值。
独立的 `TASK_INTAKE_API_KEY` 和 `TASK_INTAKE_BASE_URL` 尚未配置，因此实际独立服务地址尚未确定。
本轮真实请求 **0 次**。不借用另一服务凭据，也不将配置缺失解释为授权。

N1 的 JSON、引句和来源边界保持不变：拒绝非 JSON、重复 key、额外字段、伪造引句、
未覆盖的原文字母/数字/汉字、不合法配置指针、模型填写的 value、含数字的候选问题。
`finish_reason` 仅接受 `stop`，截断、过滤、拒绝、tool calls 均失败关闭。
引句覆盖只证明文本保留，不证明语义理解；解释仍属 LLM 推测，不进入配置或数学约束。
没有因为尚未执行的真实测试修改提示词或增加重试。

`IntakeResult.provider_receipt` 保留实际请求的模型、显式地址、响应文本、finish_reason、
token usage、耗时和上限；Provider 异常只保存异常类名，不输出异常中的敏感内容。
没有供应商价格时 `monetary_cost=null`、`cost_status=unknown...`，不会把未知价格记为零。
token usage 缺失同样为 null。单次 output token 上限不是货币预算或输入 token 上限。

五类入口直接复用 N1 的 Reach、Tracking、障碍 Reach、接球、扰动稳定语料：

```powershell
$py = 'D:/softrobot-agent/.mainline5-env/Scripts/python.exe'
& $py -m tests.research.test_task_intake_compile --validate --output runs/s130-n2/offline-parser-audit.json
```

离线运行记录 `synthetic_fixture`；五例格式和预期分类均通过。
报告单独记录 `format_pass`、`intent_match`、`failure_reason`、响应成本，
`semantic_correct=null`、`semantic_review_status=human_review_required`，附五项人工语义检查清单。
这些结果不是实际 LLM 准确率。成本和格式通过不能替代人工核对全部验收条件及缺失定义。

获得额外真实调用授权并安全设置独立环境变量后，才运行以下模板（本轮未执行）：

```powershell
& $py -m tests.research.test_task_intake_compile --validate --enable-provider --case reach --model <已确认模型> --base-url <已确认独立服务HTTPS地址> --max-tokens 2000 --timeout-s 30 --output runs/s130-n2/live-reach.json
```

`--case` 可选 `reach/tracking/obstacle/catch/disturbance`；真实模式禁止 `all`，
每次 invocation 最多一条请求。后续只运行获授权的 case 数量，逐条检查记录，不自动扩大调用范围。

### TaskIntakeDraft → 编译预览

```python
from tools.task_intake import compile_draft

preview = compile_draft(
    draft,
    trusted_reference=validated_session_input_snapshot,
    reference_label="用户明确指定的完整参考快照",
    analysis_protocol=existing_analysis_protocol,  # 可省略
)
```

返回 `CompilationPreview`：

| 字段 | 意义 |
| --- | --- |
| `semantic_spec` | 保留原 TaskIntakeDraft，含未知任务、全部要求、缺失问题和时序关系 |
| `requirement_mappings` | 每条 requirement 的原文/配置指针/值/来源 identity、细分映射和状态 |
| `diagnostics` | 缺失、冲突、无法映射、不支持、未采纳参考等具体原因 |
| `capabilities` | 分别报告语义、评价、物理、数学、授权及实际 Registry 清单 |
| `acceptance_spec` | 既有配置、适配器、验收组合的只读投影；不完整/不支持任务为 null |
| `candidate_task` | 现有 `TaskDefinition(status=draft)`，未能编译则 null |
| `configuration_preview` | 原完整 `SessionInput` 的副本；只改变 task.status 和来源说明 |
| `reference_identity` | 经过原 schema 校验、规范化的完整参考快照 digest |

参考参数必须是完整 SessionInput；不能使用 AcceptanceView 或单独 TaskDefinition 反向拼配置。
`trusted_reference` 是调用方明确选择的来源边界，不是 LLM 可写的字段，也不是物理成功证明。
编译器不加载 Study/Store。仅测试和样例驱动使用现有 resolver 产生参考快照。
序列化草稿再次通过 N1 来源检查；配置值、identity 与当前明确参考重新核对。
原 `acceptance_context` 不能自行充当可信配置。

**N2 有意只支持固定 Reach 的窄语法及参考一致性预览。** 不做自由语言第二次猜测、单位换算、
任意参数修改或多阶段时序编译。句子以分号、句号或换行分隔；数值用 SI。
目标和世界坐标系必须显式给出；其余验收/执行设置需要原文中的明确采纳句。
数值与参考冲突时要求人工解决，不自动覆盖任何一边。
未知句子即使被 LLM 标成 behavior/observable 也会阻止预览；整段塞进一个引句也不能绕过全文检查。

可编译的完整样例：

```text
让末端到达目标 (0.29, 0.035, 0.19) m；世界坐标系；
终点误差不超过 0.01 m；任务时长 0.35 s；最终保持窗口 0.05 s；
保持窗口位置误差不超过 0.01 m；保持窗口速度不超过 0.02 m/s；
采用参考配置的其余验收与执行设置
```

所有明确数值与现有 reference 对比；缺失的容差/时长只有在明确采纳参考设置时才能来自该参考。
`undefined`、`llm_candidate`、未采纳的配置事实及未支持时序关系仍需要审阅，不能静默忽略。
任意自然语言都可以进入 N1 草稿；不符合上述窄语法时保留原文并返回诊断。

### 五种能力状态与 reach_free 的原验收

- A 语义：`complete/incomplete/needs_review`；不会将配置可校验等同于用户语义完整。
- B 评价：当前实际 Registry 只有 `task.reach` 和 `evaluate.reach`；`registered` 指实现存在，
  不表示已完成正式评价。其他四类任务报告各自缺少的信号、定义和 evaluator。
- C 物理：调用原 `ResearchTaskAdapter.check_compatibility()` 检查**原始**参考，保留
  `physical.reference_check`；仅当新任务语义全部一致时才将新任务标为 `supported`。
  原接口复用 `compile_input`，覆盖 task、evaluator、signals、timing、backend、controller、模型和 route。
  未复制这些检查。原参考若也是 draft，保持拒绝，不提升为 development_valid。
- D 数学：只对有效候选调用 `describe_analysis_requirements` 和可选 `analysis_capabilities`。
  无 protocol 为 `not_assessed`；不支持任务为 `not_applicable`；未执行数值求解。
- E 授权：始终 `not_authorized`、`executable=false`。新预览经原 `compile_input` 被拒绝，
  不创建 Session，不启动科研，原审批与执行门禁保留。

`acceptance_spec` 复用 `ResearchTaskAdapter.describe/ranking_limits`，并调用
`assemble_acceptance(preview, None, None)` 得到 `missing_evidence` 投影，不构造通过的执行证据。
包含终点 evaluator 绑定、最终窗口位置/速度、六个含端点样本覆盖、执行完整性、
evaluation validity、solver errors、force bounds，以及原组合协议与证据来源要求。
每个组合条件标明原 owner 和参考 identity；阈值/路径来自配置、adapter 或原组合器。
终点评价器仍负责 `evaluator:task_bound`：缺少 evaluator 结果时不伪造该结果行。
新增条件不会重写原 `offline_reach_hold_v1`，也不会只留下 `evaluate.reach`。

实际样例的数学约束仍是半径 `[0.01, 0.01, 0.02]`、终点索引 35、保持索引 30–35，
物理输入来自已验证机器人 tendon 次序与 force limits。原适用性结果：

| 操作 | 结果与范围 |
| --- | --- |
| equilibrium / linearization / controllability | applicable，局部诊断，不覆盖整任务 |
| endpoint | applicable，只覆盖终点位置 |
| braking | applicable，保持速度仅终点部分覆盖 |
| trajectory_feasibility / task_capability | applicable，覆盖当前三类采样数学约束 |
| instantaneous_braking_v1 | not_applicable，缺少 exact saved state |
| input_sensitivity / design_sensitivity | not_applicable，当前参考不满足 SoRoSim static IFT 条件 |

沿用原接口 `full_task_supported` 的范围仅是 adapter 生成的数学要求，
不是 solver errors、执行完整性、独立 evaluator 与整个物理验收协议通过。

### 可复现样例与诊断

```powershell
& $py -m tests.research.test_task_intake_compile --write-demo runs/s130-n2
& $py -m tools.task_intake --file runs/s130-n2/task.txt --response-file runs/s130-n2/response.json --compile-reference runs/s130-n2/reference.json --analysis-protocol runs/s130-n2/analysis_protocol.json
```

CLI 编译模式输出 `{intake, compilation}`，保留解析请求成本；成功预览退出码 0，
无法编译/解析失败退出码 2。上述为离线夹具，非真实 LLM 或物理证据。
样例驱动生成完整 `complete_reach.json` 以及以下诊断文件，均位于忽略的 `runs/s130-n2/`，
可从已提交测试代码重新生成：

| 样例文件 | 实际结果 |
| --- | --- |
| complete_reach.json | draft 配置预览，语义完整、参考兼容、数学已只读评估、无执行授权 |
| missing_reach.json | 缺 target、frame、tolerance、duration；无配置预览 |
| conflicting_reach.json | 用户 0.001 m 与参考 0.01 m 冲突；不覆盖 |
| extra_constraint.json | “全程不能超过 5 N” 未定义力的对象/信号，明确 unmapped 并阻止预览 |
| tracking.json | 缺注册 Tracking 任务、timed reference、tracking evaluator |
| obstacle.json | 缺距离/碰撞信号及 evaluator，不降级 Reach |
| catch.json | 缺接触、物体状态、捕获/保持定义及 evaluator |
| disturbance.json | 缺扰动定义、平台/扰动信号及稳定性 evaluator |

### 测试、交付边界与后续主线接入

最终回归命令：

```powershell
& $py -m unittest tests.research.test_task_intake tests.research.test_task_intake_compile tests.research.test_task_analysis_contract.TaskAnalysisTests.test_frozen_translation_and_distinct_holding tests.research.test_task_analysis_contract.TaskAnalysisTests.test_old_contracts_and_acceptance_unchanged tests.research.test_task_analysis_contract.TaskAnalysisTests.test_signal_semantics_and_unsupported_requirements tests.research.test_evidence_policy tests.research.test_mainline -v
```

最终结果：**51 tests 全部通过，14.099 s**，日志 `runs/s130-n2/regression.txt`。
其中 N1 10 项、N2 12 项、原数学/验收 3 项、证据政策 14 项、主线 12 项。
五类离线解析审计也通过，8 个编译/诊断样例已生成；`git diff --check` 通过。
测试覆盖完整 Reach、缺失容差/时间、额外约束、四类不支持任务、
参考冲突、来源伪造、draft 执行拒绝、真实 Registry/backend/controller/signal/timing 检查、
独立 Provider 无回退、单次上限与成本记录、CLI 和原验收/数学/主线回归。
中间一次 CLI 测试因全局 mock `Path.read_text` 干扰 Registry 源码检查而失败，
已改成真实临时 JSON 文件后通过；没有为测试改变生产平台逻辑。

后续接入主线的最小改动是：在已有任务入口前调用独立解析和 `compile_draft`，
把原文、逐项映射、完整参考 identity 与预览交给现有人工审核流程。
通过审核后再由现有配置拥有者处理任务身份、批准修改和原执行准入；不能直接把本预览送入科研。
不支持任务先实现既有扩展目录中的 contract/manifest/evaluator/backend signal，不能扩大 Reach 含义。
本阶段停止扩张编译器，提交供 N2 阶段验收；不合并主线，不启动正式科研。
