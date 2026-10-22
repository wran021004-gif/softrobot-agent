# S130 最小协议修复与离线联调（2026-10-22）

本轮 **零 Provider 请求、零新增 Provider tokens、无物理研究**。起点为干净的
`research/s130-task-intake` / `c5bba8ff`，worktree 为 `.worktrees/s130-task-intake`。
未引入 N3、Agent、重试循环、依赖、Registry 或第二套配置编译器。

历史 [真实验证报告](s130_live_validation.md) 和 [原摘要](s130_live_validation.json) 未修改。
前两轮共 12 次请求、45,737 tokens；货币成本仍未知。
本次 [离线重放摘要](s130_protocol_repair.json) 单独记账，包含原始文件哈希、旧结果、
新结果、逐例诊断和派生测试样例的全部修改说明。第二轮 response/result/request 哈希逐一
匹配已提交的原摘要；两轮案例文件及两份历史报告在重放前后逐一核对，均未改变。

## 最小契约变化

| 边界 | 旧规则 | 本次规则 |
| --- | --- | --- |
| 来源字段 | 三字段必须出现，无关字段为 null | 不适用的 quote/config_pointer/question 可省略；实际来源字段仍必填且互斥 |
| 引句覆盖 | 未覆盖字母、数字、中文导致整份拒绝 | user_text 完整保留；unquoted_spans 给出原文和起止偏移，草稿仍 needs_confirmation |
| 数字提问 | 问题中任何数字都拒绝 | 允许重复原文数字词元；新数字仍拒绝；问题 value 始终为 null |
| 保持时序 | 任意 temporal_relations 阻止预览 | 仅位置/速度要求 during/throughout 既有最终保持窗口可映射；其他关系待审核 |
| DeepSeek | 可省略 thinking | 对 api.deepseek.com，未显式指定 disabled 在请求前拒绝 |

`schemas/task_intake.py::RequirementProposal.source_shape` 仍验证来源互斥。
`tools/task_intake.py::parse_response` 仍拒绝不真实引句、伪造配置指针、模型自填数值、
重复 JSON 键、非 stop 响应。省略实际需要的来源字段也不能通过。
数字重复只是提问文本容许规则，不验证其单位或物理含义，不能成为数学事实；
undefined 和 llm_candidate 仍分别形成缺失项或待确认映射，阻止配置预览。

`compile_draft` 重新验证来源、重新计算覆盖，逐句检查 **全部 user_text**，不信任
序列化覆盖注释。未知原文、冲突数值、未解决问题继续阻止预览。
即使模型只引用合法 Reach 子集、漏掉全身避障，或人为清空 unquoted_spans，也无法绕过。
如果未引用原文恰是既有语法可独立验证的保持限值，则允许 draft 预览，覆盖缺口仍可见；
未映射约束从未被当作已满足。标点空隙不单独形成缺口，但仍保留在原文并经全文编译。

提示词去掉无关 null、重复原文及复制配置字段的要求，保留逐条件提取、连续原文引句、
任务不可降级、缺失定义和来源约束。**新提示词尚未真实测试。**

## 六份完整真实输出的离线重放

旧结果直接引用保存的 result.json，不重写为本轮真实结果。
第一轮六份 length 响应在新规则下仍全部拒绝，语义仍无法评估。
第二轮原始输出逐字不改，新旧 JSON/Pydantic 格式通过数均为 **4/6**；
完整解析准入从旧记录 **0/6** 变成本次离线 **3/6**。

| 原始案例 | 旧首错 | 新规则离线结果 | 语义审查与编译边界 |
| --- | --- | --- | --- |
| Reach + Hold | 假时序引句 | 仍拒绝 USER_QUOTE_NOT_FOUND | 目标、终点、窗口位置/速度均保留；拼接引句非法；重复参考问题待确认 |
| 全身避障 Reach | 来源冲突及缺无关字段 | 仍拒绝 SOURCE_CONTENT_CONFLICT | 无关字段已可省略，R4 同时带 quote/question 仍非法；“设计一条软臂”的遗漏未被修复 |
| 自由落体接球 | 未逐字覆盖缺失句 | 接受待审核草稿 | 保留自由落体、0.05 kg、捕获后至少 0.20 s、禁反弹/落地；缺失句可见，Q4 重复 0.20 不再拒绝；无接触/捕获 evaluator，编译阻止 |
| 斜坡滚落接球 | 未覆盖“并”和缺失句 | 接受待审核草稿 | 保留从斜坡滚下、质量、捕获后稳定保持；坡角/初始位置/摩擦缺失可见；未替换为自由落体；编译阻止 |
| 扰动平台稳定 | 来源冲突 | 仍拒绝 SOURCE_CONTENT_CONFLICT | 对 world frame 的错误缺失声明、未单列扰动前阶段仍需复核；不因格式简化自动修正 |
| 圆周 Tracking | 未覆盖缺失句 | 接受待审核草稿 | 保留半径、3 周期、2 s、最大误差；圆心/平面/相位原文及问题可见；时序边待复核；缺注册 Tracking evaluator，编译阻止 |

自由落体、斜坡、Tracking 的 semantic_spec 保留原始需求和时序；evaluation=unsupported、
physical=not_assessed、mathematics=not_applicable、authorization=not_authorized；
均无 candidate_task/configuration_preview。这是本次原始输出实际离线进入 N2 的结果。
障碍/扰动仍在 N1 拒绝，不能宣称它们的真实输出已进入 N2。

本次没有新增真实语义得分。历史人工可审核对照仍为两个完整语义确认、四个待复核；
格式修复没有消除语义遗漏、错误缺失声明或模糊时序。确定性解析器不冒称能判定所有解释真伪。

## Reach 保持时序与科学边界

`_holding_relations` 只识别既有固定语法中的位置/速度限制作用于最终保持窗口。
区间由可信完整配置经原 ResearchTaskAdapter 得到，当前为含端点采样 `[0.30, 0.35] s`，
无新增连续时间保证。before/after/then/until、反向关系、将终点误差作为窗口限制均待审核。
尤其“到达 before 保持窗口”可能意味着更早截止时间，不能默默视为既有验收。

另保存 **派生审核测试样例，不是 Provider 结果或审批**，检验真实输出字段结构的衔接：

1. 仅将 Reach 第三条时序关系的拼接引句换为包含中间位置句的连续原文。
   此版本能解析，但仍因 R1 before R5 与 R19–R22 候选问题阻止配置预览。
2. 再显式移除该推断时序边及四个候选问题，用于检验“这些项目经审核消解以后”的接口。
   user_text 不变，保留全部用户约束、来源指针和两条 during 关系；生成 status=draft 配置预览。

全部删除项与引句修改前后内容见摘要 reach_integration_fixture.edits。
没有自动清洗真实回答；真正采用此回答时这些决定仍需审核。
产物为 `reach_quote_only.json`、`reach_review_fixture.json`；**不计作原始 Reach 解析成功**。

预览仍深拷贝可信完整 SessionInput、复用 check_definition，不从 AcceptanceView 反建。
原 assemble_acceptance 的终点 evaluator、execution_complete、evaluation_validity、solver_errors、
force_bounds、holding_coverage、holding_position、holding_speed 与组合协议不变。
数学要求仍由原 adapter 生成，其适用性结果不是物理验收证明。
新合法时序预览也被原 compile_input 因 draft 状态拒绝，未改 development_valid 或审批门禁。

## 离线验证

```powershell
$taskIntakePython = 'D:/softrobot-agent/.mainline5-env/Scripts/python.exe'
& $taskIntakePython -m tests.research.replay_task_intake --output runs/s130-protocol-replay-another
& $taskIntakePython -m unittest tests.research.test_task_intake tests.research.test_task_intake_compile tests.research.test_task_analysis_contract.TaskAnalysisTests.test_frozen_translation_and_distinct_holding tests.research.test_task_analysis_contract.TaskAnalysisTests.test_old_contracts_and_acceptance_unchanged tests.research.test_task_analysis_contract.TaskAnalysisTests.test_signal_semantics_and_unsupported_requirements tests.research.test_evidence_policy tests.research.test_mainline -v
```

重放只读历史证据，要求全新输出目录；SDK 构造与 socket.connect 均 mock 为禁止。
本次产物在忽略目录 `runs/s130-protocol-replay-20261022/`，原始回答未复制进 Git。
回归 **59 tests 全通过，17.495 s**，日志为该目录 regression.txt；git diff --check 通过。
覆盖漏引障碍/捕获约束、错误限值、伪造配置数值/identity/指针、“接近即捕获”错误解释及
伪造引句、冲突时序、伪造覆盖、遗漏字段、截断与数字来源。
原数学/验收 3 项、证据政策 14 项、主线 12 项全部通过；基础平台、评价器、冻结配置、
Agent/Reporter/Store/预算均未修改。

## 新授权后三例真实复测方案（本轮未执行）

原 Reach + Hold、斜坡滚落接球、全身避障 Reach，各一次、串行、最多三次、无重试。
使用原 task.txt，只有 Reach 发送相同参考上下文；后两例只在确定性编译阶段对照参考。
分别检查保持时序与参考采纳、斜坡物理机制与缺失定义、全身避障及设计范围。
仅完整兼容 Reach 可能有 draft 配置；后两例应形成审查草稿但不能执行。

新授权后，独立 TASK_INTAKE_API_KEY 必须已在当前进程显式配置；不得回退科研服务或 OPENAI_*。
本轮没有读取 `.codex/.env`。以下准备函数调用现有 CLI，不创建新 Provider 客户端：

```powershell
$taskIntakePython = 'D:/softrobot-agent/.mainline5-env/Scripts/python.exe'
$taskIntakeOutput = 'runs/s130-three-authorized-retest'
New-Item -ItemType Directory -Path $taskIntakeOutput -ErrorAction Stop | Out-Null
function Invoke-S130Case([string]$Case, [switch]$Reach) {
    if (-not $env:TASK_INTAKE_API_KEY) { throw 'Independent TASK_INTAKE_API_KEY required' }
    $caseDir = Join-Path $taskIntakeOutput $Case
    New-Item -ItemType Directory -Path $caseDir -ErrorAction Stop | Out-Null
    $marker = [IO.File]::Open((Join-Path $caseDir 'started.json'), [IO.FileMode]::CreateNew)
    $marker.Dispose()
    Set-Content -LiteralPath (Join-Path $caseDir 'started.json') -Encoding UTF8 -Value '{"request_limit":1,"retry_forbidden":true}'
    $argsForCase = @('-m','tools.task_intake','--file',"runs/s130-live-nonthinking-20261022/$Case/task.txt",
        '--enable-provider','--model','deepseek-flash','--base-url','https://api.deepseek.com',
        '--thinking','disabled','--max-tokens','8192','--timeout-s','60',
        '--compile-reference','runs/s130-n2/reference.json')
    if ($Reach) { $argsForCase += @('--context','runs/s130-n2/reference.json') }
    & $taskIntakePython @argsForCase > (Join-Path $caseDir 'result.json')
}
```

然后逐条执行，不作为自动批次；每次审查 receipt、finish_reason、usage 与解析/编译结果，
确认结果已知才执行下一条。超时或未知结果停止，保留 started.json，不重复提交。
退出码 2 也可能是合法草稿不受编译器支持，不能自动视为 Provider 失败而重试。

```powershell
Invoke-S130Case '01_reach_hold' -Reach
```

```powershell
Invoke-S130Case '04_slope_catch'
```

```powershell
Invoke-S130Case '02_obstacle'
```

CLI result.json 保留 response_text、finish_reason、usage、wall_s、解析及编译结果；
原始响应仅留在忽略运行目录，Git 只提交非敏感摘要。逐条件审查语义，不能只看 intent 标签。

本轮代码和离线验证完成，停止扩张并交阶段验收；真实遵从性仍需另行授权复测。
后续主线接入仍只需在已有任务入口前调用 request_draft/parse_response/compile_draft，
展示原文、覆盖缺口、映射及参考身份，再走原审核门禁；本轮不合并、不启动科研。
