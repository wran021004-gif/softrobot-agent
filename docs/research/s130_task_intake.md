# S130-N1：独立自然语言任务解析与验收草稿

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

真实调用必须显式 `--enable-provider --model <name>`，可传 `--base-url`，凭据使用
OpenAI SDK 标准环境变量。独立客户端只发送一条 JSON 模式请求，max_retries=0，
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
