# S130 真实 LLM 跨任务验证（2026-10-22）

**结论：普通调用已能保留多类任务的主要语义，但尚未可靠满足来源契约，不能宣布 S130 最终验收通过。**
第二轮六例全部返回完整 JSON，Pydantic 契约通过 4/6，包含引句/覆盖/来源检查的 N1 完整准入通过 **0/6**。
逐项人工可审查对照后，完整科学语义确认 2/6（自由落体接球、斜坡滚落接球），其余 4 例部分正确、需要复核。
这不等于其余任务被完全误解，也不等于两个语义正确的原始回答能进入编译器。

机器可读字段、每项证据、原文、缺失引句、成本及原始文件 SHA-256 见
[验证摘要](s130_live_validation.json)。语义判断由本次助手逐项检查原始回答作出，供用户复核；不是 Provider 自评或标签匹配评分。

## 执行范围和记录

开始时 worktree `.worktrees/s130-task-intake` 干净，分支 `research/s130-task-intake`，提交 `dde3e9cb`。
用户随后指定 `$HOME/.codex/.env` 与 `deepseek-flash`；文件内的 `DEEPSEEK_API_KEY`
按此次明确授权，仅在测试进程中映射到 `TASK_INTAKE_API_KEY`，未修改环境文件，也未读取科研 Agent 配置。
显式地址为 `https://api.deepseek.com`，与 [DeepSeek 官方接口说明](https://api-docs.deepseek.com/) 一致。

两轮逐例串行执行，各六次、每例一次，无自动重试、无探索请求、无物理执行。
每次请求前独占创建 `started.json`，已有记录禁止再次提交该案例；第二轮新授权单独记账，没有清除第一轮历史。
使用原 `request_draft()`，JSON 模式、`max_retries=0`、单请求超时上限 60 s。
六个输入与用户给定原文一致；仅 Reach + Hold 发送明确指定的 reach_free 参考视图。
参考来自上轮保留的完整 `runs/s130-n2/reference.json`，不从 AcceptanceView 拼装配置。

| 轮次 | 配置 | 请求 | 完整 JSON | JSON + Pydantic | 完整 N1 准入 |
| --- | --- | --- | --- | --- | --- |
| 第一轮 | 未指定 thinking；max_tokens=4096 | 6 | 0 | 0 | 0 |
| 第二轮，用户重新授权 | thinking=disabled；max_tokens=8192 | 6 | 6 | 4 | 0 |

两轮六例均先完整收集，未中途修改提示词。第二轮使用原 N1 提示词；新增模式参数和提高上限不改变提示内容。
第二轮结束后才补充提示词要求，之后没有真实重测。

## 第一轮：调用模式与上限不匹配

六例均为 `finish_reason=length`，每例 completion_tokens=4096。五例最终答案为空；
自由落体接球输出 1185 字节截断 JSON，时序关系处中断，不能进入 JSON/Pydantic 验证或任务编译。
这一轮的语义正确性全部为待评估，不能记作六个语义错误。

官方说明 [thinking 默认开启且默认 effort 为 high](https://api-docs.deepseek.com/guides/thinking_mode/)。
实际 usage 显示共 24,262 个 reasoning tokens，占 24,576 个 completion tokens；
截断来自调用模式与给定上限的组合，不是已经证明模型不理解任务。
原入口 `request_draft()` 未提供 thinking 参数；`parse_response()` 第 95 行按设计拒绝非 stop 响应。

## 第二轮：逐项语义对照

六例 finish_reason 均为 `stop`。以下 R/U/Q 编号是原回答中的 requirement ID；
JSON 字符串与解释一起检查，不能仅凭 intent 名称宣告正确。

| 案例 | 原始回答保留的依据 | 缺失定义与语义问题 | 完整语义结论 |
| --- | --- | --- | --- |
| 1 Reach + Hold | R1/R3–R7 保留目标、world、终点 0.01 m、0.35 s、最终 0.05 s 窗口、窗口位置 0.01 m 和速度 0.02 m/s；终点与窗口验收分开；R9–R17 引用参考配置 | R21 又询问参考已明确的含端点窗口边界；对信号/评估器提出重复疑问；解释声称可能不一致但未给依据 | 主要任务正确，参考采纳与缺失声明需复核 |
| 2 障碍 Reach | R3 原样保留“整个运动过程中，软臂任何部位都不能与球形障碍物发生碰撞”；目标、0.35 s、world、0.01 m 都在；未缩为末端避障 | 几何、碰撞规则、信号和评价方式问题合理；但“设计一条软臂”未进入提取要求，设计范围丢失 | 全身避障正确，整体要求不完整 |
| 3 自由落体接球 | R1 明确“从上方自由落下”、0.05 kg；R3 接住后至少 0.20 s；R4 禁止反弹脱离或落地；then/throughout 保留捕获先于保持及全保持期约束 | Q1–Q4 提问接触测量、释放高度/初始条件、捕获判据和评价器；没有把接近小球当作捕获 | 科学语义完整；来源编码仍失败 |
| 4 斜坡滚落接球 | R1/R4 明确“从斜坡滚下”，解释也写 rolling down a ramp；0.05 kg、捕获后稳定保持至少 0.20 s、then 顺序均保留 | R5–R10 覆盖坡角、初始位置、滚动摩擦、捕获与稳定保持测量、判据和 evaluator；未替换成自由落体 | 科学语义完整；来源编码仍失败 |
| 5 扰动稳定 | R1–R6 保留平台水平扰动、1.0 s 起始、固定 world 目标、扰动后 0.5 s 内恢复、0.01 m、再保持至少 0.10 s；没有降为 Reach | 扰动→恢复→保持关系保留，扰动前阶段未单独描述；解释错误声称坐标系未给出；波形、目标坐标、信号和 evaluator 确属未定 | 主要恢复任务正确，阶段及缺失声明需复核 |
| 6 Tracking | R1/R3–R6 保留 world 圆轨迹、半径 0.10 m、3 周期、每周期 2 s、最大误差 0.015 m；无固定目标替换 | 圆心/平面/相位及误差测量/evaluator 均被询问；时序边指向“周期值”和“误差阈值”行，未形成清楚的评分时段关系；未声称已可执行 | 时变轨迹正确，关系表示需复核 |

所有案例 intent_correct=true，依据不仅是标签，还包括上述物理机制和约束内容。
第二轮未观察到新增数值阈值、硬性验收条件或捏造物理机制；**仍有错误的缺失声明和遗漏，不能称为无语义错误**。
问题中的可选姿态/接触力询问没有被当作用户要求。自由落体 Q4 中的 0.20 s 来自用户，
不是新编数字，但违反当前“问题不能带数字”的严格规则。

字段级判断见 JSON：`semantic_correct=null` 表示待复核，不能计入通过数；
`temporal_semantics_correct=null` 用于扰动和 Tracking 的尚未充分确认关系。
缺失原句的语义有时已在问题中保留，但不等于保留了原句来源。

## 解析失败与源码归因

`format_pass` 严格按 JSON + IntakeProposal/Pydantic 定义；额外设置 `intake_pass`
表示原 N1 全部引句、覆盖、数值和配置来源检查通过。两者分开统计。

| 案例 | format_pass | 实际首个拒绝原因 | 可审查细节与源码 |
| --- | --- | --- | --- |
| Reach + Hold | true | USER_QUOTE_NOT_FOUND | temporal_relations[2] 把最终窗口和速度句拼接，省略中间位置句，不是原文连续子串；`tools/task_intake.py:113` |
| 障碍 Reach | false | SOURCE_CONTENT_CONFLICT / Field required | R4 同时为 llm_candidate 并携带 quote；R7 缺 config_pointer（必须显式 null）；`schemas/task_intake.py:14`、`:32` |
| 自由落体接球 | true | UNRETAINED_USER_REQUIREMENT_TEXT | 最后“尚未指定”句被问题替代而未引用；另有 Q4 重复数字的潜在后续拒绝；`tools/task_intake.py:124`、`:138` |
| 斜坡接球 | true | UNRETAINED_USER_REQUIREMENT_TEXT | 未覆盖“并”和整句“斜坡倾角、球的初始位置和滚动摩擦条件尚未指定”；`:124` |
| 扰动稳定 | false | SOURCE_CONTENT_CONFLICT | R7 为 undefined，同时带原句 quote 与 question；`schemas/task_intake.py:32` |
| Tracking | true | UNRETAINED_USER_REQUIREMENT_TEXT | “圆心、轨迹平面和起始相位尚未指定”只进入问题，未保留原句引文；`tools/task_intake.py:124` |

障碍例还遗漏了设计开头和缺失几何原句；上述表按真实首错记录，完整离线枚举在摘要中。
没有修补原始 JSON 后冒充真实通过结果，也没有将带来源错误的猜测构造成合法草稿。

**真实模型结果均未形成 TaskIntakeDraft，所以 compile_draft 没有运行于任何真实输出，
compilation_status=not_run_parse_failed。** 不能把这些首错归因于 N2 窄语法，
也不能声称本轮真实证明了“不支持任务被编译器正确拒绝”。

现有离线回归仍验证：完整支持 Reach 可生成 draft，Tracking/避障/接球/扰动不可冒充普通 Reach，
原 Registry 只有 task.reach/evaluate.reach。Tracking evaluator 未注册是代码事实，不是 LLM 的声明。
Reach 原回答还包含候选问题与时序关系；即使纠正引句，按 `compile_draft()` 的现有
`TEMPORAL_RELATIONS_REQUIRE_REVIEW`、`UNRESOLVED_REQUIREMENT_MAPPINGS` 分支也需要人工确认，
不能自动取得执行授权。此为源码分析，不冒充实际成功编译。

## 请求量、成本与证据位置

| 案例 | 第一轮 input / output / 秒 | 第二轮 input / output / 秒 |
| --- | --- | --- |
| Reach + Hold | 2153 / 4096 / 22.672 | 2128 / 1646 / 7.437 |
| 障碍 Reach | 1151 / 4096 / 23.437 | 1126 / 734 / 4.094 |
| 自由落体接球 | 1132 / 4096 / 21.407 | 1107 / 681 / 4.187 |
| 斜坡接球 | 1124 / 4096 / 24.672 | 1099 / 838 / 4.344 |
| 扰动稳定 | 1152 / 4096 / 23.703 | 1127 / 900 / 5.453 |
| Tracking | 1135 / 4096 / 23.188 | 1110 / 818 / 4.203 |
| 合计 | 7847 / 24576 / 139.079 | 7697 / 5617 / 29.718 |

第一轮 32,423 tokens；第二轮 13,314 tokens；两轮 **12 次请求、45,737 tokens**。
每轮输入缓存命中均为 4480 tokens；未命中分别为 3367、3217。
第二轮 usage 没有 reasoning_tokens 字段，记录为 null，不伪造为计量零；请求中的 disabled 已有记录。
无已核实价格或账单，货币费用仍为 unknown/null，不报告零费用。

原始响应和认证信息严格分开：密钥未输出、未持久化到运行记录、未提交。
忽略目录 `runs/s130-live-final-20261022/` 保留第一轮；
`runs/s130-live-nonthinking-20261022/` 保留第二轮。
每例目录有 task.txt、request_messages.json、started.json、response.txt、result.json；
Reach 另有 context.json。response.txt 是 Provider 的最终 content，第一轮未保存 reasoning_content。
Git 只提交本报告、非敏感摘要及必要代码/测试；原始响应保持在忽略目录。

## 最小修复与阶段建议

第一次观察后增加可选 `thinking` 参数，并记录显式值或 provider_default；默认请求保持兼容。
用户第二次授权后把输出上限允许范围提高至 8192，并显式使用 disabled，六次都正常 stop。
测试入口仍只调用同一个 request_draft，无新 Harness、Agent、循环或依赖。

第二轮完成后仅加强 `request_messages()` 提示：

- 引句必须是连续原文，不能把间隔句子拼接；不省略标点或中间内容。
- 用户声明“未指定”的句子也必须保留为 user_explicit，再另加 undefined 问题。
- 所有字段必须出现，不用的字段显式 null；来源字段形状互斥。
- 问题不含数字，包括已给数字的重复；已有数值留在原文引句。
- 不将用户或明确采用的参考已定义的量重新宣布为缺失。

没有放宽 schema、引句校验、验收语义或 N2 固定 Reach 语法。
新增离线测试复现上述失败，并确认 explicit thinking 传递、8192 上限、单次请求和截断失败关闭。
修改后原始六个回答的离线重放仍然拒绝，这是预期的来源保护，不代表提示词修复无效或已有效。
提示词修改的真实效果尚未测试；当前两轮授权均已用尽。

回归 **53 tests 全部通过，14.217 s**；日志位于
`runs/s130-live-nonthinking-20261022/regression.txt`。范围为 N1/N2、Provider 边界、
原数学/验收 3 项、证据政策及主线回归；六份第二轮原始回答已离线重放，拒绝结果未变。
`git diff --check` 通过。此次没有修改 schema、平台模块、正式评价器或冻结任务。
不建议以“真实 LLM 验证已通过”结束 S130 或融合主线；可停止开发并交付当前证据，
后续若用户批准少量真实重测，再验证提示词遵从性。当前不合并、不启动科研、不新增开发阶段。
