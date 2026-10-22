# S130 第三轮真实验证与最终验收意见（2026-10-22）

**本轮已完成授权的 3 次真实请求；2/3 形成合法草稿，Reach 没有走通到配置预览。**
斜坡接球与全身避障都被 N2 正确识别为不支持，没有伪装成普通 Reach。
核心意图均被理解，但完整缺失定义检查、结构设计范围保留和 Reach 输出契约仍有问题。
因此不建议把 S130 判定为目标已达成，也不建议现在以验收通过状态融合主线。
本轮执行已停止，不增加阶段、不补发请求、不修改生产代码。

逐项机器可读结果、原文、错误位置、覆盖缺口、完整 usage 与哈希见
[第三轮摘要](s130_final_validation.json)。本报告是助手逐项审查原始回答的可复核判断，
不是 LLM 自评。前两轮 [真实记录](s130_live_validation.md) 与
[协议修复/离线重放记录](s130_protocol_repair.md) 均原样保留。

## 执行与证据

- 开始时 worktree `.worktrees/s130-task-intake` 干净，分支 `research/s130-task-intake`，
  HEAD `f7d7d6f542e4319332c1a7c3d75e1979c059b6c9`。
- 已读 AGENTS.md 和指定报告/源码；64 个历史证据文件与已保存哈希一致。
  第三轮运行前后再次验证历史、源文件、原参考配置不变。
- 三例共用上述提交的提示词/schema/parser/compiler，系统消息哈希一致；每例请求消息另行保存。
  测试期间没有调整提示词，也没有修改、删除或规范化真实输出中的问题及关系。
- 请求模型 `deepseek-flash`，显式 `https://api.deepseek.com`、thinking=disabled、
  max_tokens=8192、timeout_s=60、max_retries=0，无工具调用，逐例串行。
  沿用户授权从 `$HOME/.codex/.env` 只提取 DEEPSEEK_API_KEY，在调用进程内映射
  TASK_INTAKE_API_KEY；没有修改文件、输出密钥或继承科研服务配置。
- 复用现有 request_draft 和 compile_draft。测试驱动只做请求占用、文件保存与串行检查；
  每次发送前独占创建 started.json，后续案例要求上例已知完成，无重试。
- 只给 Reach 发送与第二轮完全相同的 AcceptanceView；编译使用原完整
  `runs/s130-n2/reference.json`，identity 为
  `31af3e097ad29fef1ffd74c5178a6267fc5ffe35889c63e98f531dd42c0df69e`。

忽略目录 `runs/s130-live-round3-20261022/` 独立保存第三轮：每例有 task.txt、
request_config.json、request_messages.json、started.json、response.txt、result.json、completed.json；
Reach 另有 context.json，后两例另有 compilation.json。
response.txt 是 Provider 最终回答 content；result.json 保留 finish_reason、usage、耗时及解析结果。
preflight.json、completed.json 和摘要记录源码/输入/响应/结果哈希。
离线审计在 SDK 与网络连接被 mock 禁止的条件下重放原响应，结果与真实保存的解析结果一致，
没有增加真实请求或产生替代性“成功输出”。

## A/B：Provider 与 N1 结果

| 案例 | Provider / JSON | input / output / total tokens | 耗时 | Pydantic / 来源准入 / 草稿 |
| --- | --- | --- | --- | --- |
| Reach + Hold | 已完成，stop，完整 JSON | 2209 / 797 / 3006 | 6.110 s | 失败 / 未进入后续来源检查 / 无草稿 |
| 斜坡滚落接球 | 已完成，stop，完整 JSON | 1180 / 444 / 1624 | 4.453 s | 通过 / 通过 / needs_confirmation |
| 全身避障 Reach | 已完成，stop，完整 JSON | 1207 / 483 / 1690 | 3.203 s | 通过 / 通过 / needs_confirmation |

无截断、超时或 Provider 错误；Reach 存在模型输出 schema 错误。
三例独立检查均未发现来源字段混用或伪造引句，但此只读检查不能替代 Reach 未完成的 N1 准入。
未观察到新增正式验收阈值或强加物理条件；Reach 问题里的 0.3 来自参考窗口，见下述来源限制。

实际 unquoted_spans：

| 案例 | 实际草稿中的未引用原文 |
| --- | --- |
| Reach | 无草稿，字段不存在；另行只读检查发现八条用户原句均被引用 |
| 斜坡 | `[22,24)`：`，并`；`[41,65)`：`。斜坡倾角、球的初始位置和滚动摩擦条件尚未指定。` |
| 避障 | `[0,7)`：`设计一条软臂，`；`[96,113)`：`。障碍物的具体位置和半径尚未指定。` |

偏移为 Python 字符索引、左闭右开。缺失句转成提问可形成草稿，完整原文仍在；
“设计一条软臂”则是实际语义遗漏，覆盖诊断使它可见，不意味着模型已经正确提取。

## C/D：科学语义与编译逐项对照

| 案例 | 保留的科学要求 | 遗漏、误判或额外疑问 | 实际 N2 结果 |
| --- | --- | --- | --- |
| Reach + Hold | 八条用户要求全部逐字保留：目标/world、终点 0.01 m、0.35 s、最终 0.05 s、窗口位置 0.01 m、速度 0.02 m/s、采用其余参考设置；解释正确区分终点与窗口 | 六个问题使用非法 kind=undefined；窗口边界、采样等已在参考中仍被列为未知，还提出接触/扰动问题；参考采纳不充分 | N1 失败，未调用 compile_draft；无 candidate_task、配置预览或真实端到端成功证据 |
| 斜坡滚落接球 | catch_ball 保留“从斜坡滚下”和 0.05 kg；hold_after_catch 保留捕获后稳定保持至少 0.20 s；before 边表达捕获先于保持，未变成自由落体或接近即捕获 | 三个问题准确覆盖坡角、球初始位置和滚动摩擦；未主动识别接触测量、捕获/保持判据和评价器定义缺失 | 实际进入 N2；unsupported catch_and_hold，缺 contact/object-state signals、capture/retention definition、contact/capture evaluator；无配置预览 |
| 全身避障 Reach | R1 保留目标/world/0.35 s；R2 保留 0.01 m；R3 完整保留“整个运动过程中，软臂任何部位”不碰撞；Q1 询问球障碍位置/半径 | 未提取“设计一条软臂”，goal 与解释也未保留设计范围；未主动询问碰撞/距离信号和 evaluator；Q2 对末端参考点的澄清保留待审核 | 实际进入 N2；unsupported obstacle_reach，缺 collision/distance signals、obstacle semantics、collision-aware evaluator；原始设计范围在全文诊断中保留；无配置预览 |

核心意图/物理机制识别 **3/3**；用户明确要求在模型提取中完整保留 **2/3**；
按“还必须正确识别缺失定义、合理采纳参考且无上述遗漏”的完整审查口径，**0/3 完全通过**。
斜坡任务的用户显式语义保留是成功项，其未发现的评价定义由确定性编译器补充诊断。
两个合法草稿均保留原 intent、要求和时序，没有改写成 Reach；Registry 实际只有
task.reach / evaluate.reach，缺少对应任务注册。

后两例 capabilities 均为 semantic=incomplete、evaluation=unsupported、physical=not_assessed、
mathematics=not_applicable、authorization=not_authorized，executable=false。
physical.reference_check=supported 仅指传入的原 Reach 参考配置，不能解释成接球或避障可执行。
N2 的附加诊断含参考设置未采纳及复杂时序待审核；采纳 Reach 参考也不能消除不支持的物理要求。

### Reach 失败的具体归因

实际首错在 `tools/task_intake.py:135` 的 IntakeProposal 校验：
requirements[8..13].kind 均为 `undefined`。`schemas/task_intake.py:16` 允许的 kind 只有
behavior/constraint/observable/environment/acceptance；undefined 是 source 值。
这是 **模型输出格式错误**，不是当前 N2 拒绝了一份已准入的合法 Reach。

以下为原回答和源码的静态后续问题诊断，本轮没有修正输出去试编译：

- req-hold-window-boundary 问题包含 `[0.3, 0.35] s`。0.3 明确来自已发送的
  context.holding_interval_s，是正确参考信息，没有捏造新阈值；但它不在原用户数字词元中，
  仍会与 `tools/task_intake.py:155` 的问题数值规则冲突。这是当前来源表达的边界。
- 窗口边界 `[0.3,0.35]`、sample_period_s=0.01、含端点采样说明已经提供。
  再把它们列为 undefined 属于多余缺失声明；观测/度量细节需结合实际参考审核，不能笼统宣称全部问题错误。
- 唯一时序边是 hold-window during task-duration，语义上合理；位置/速度与窗口的关系保留在原句及解释中。
  但 `_holding_relations`（`:290`）只映射 hold-position/speed during/throughout hold-window。
  即使来源格式问题被另行解决，这条边仍超出当前固定映射，`:442` 会要求审核。
- 模型输出的六个 undefined 问题按现有缺失项门禁也会阻止预览。没有删除它们以制造真实成功。

## 回归与三轮记账

沿用既有回归命令运行 N1/N2、原数学/验收 3 项、证据政策 14 项、主线 12 项：
**59 tests 全通过，18.124 s**。日志 `runs/s130-live-round3-20261022/regression.txt`。
生产源码、测试源码、冻结任务及配置均与 f7d7d6f5 一致，git diff --check 通过。
原独立验收组合、adapter 数学约束、Registry 和 draft 执行门禁的离线回归继续有效；
本轮没有真实 Reach 预览，不能把这些离线回归称为真实端到端成功。

| 证据类别 | 真实请求 | input / output tokens | total tokens | 完整 N1 草稿 |
| --- | --- | --- | --- | --- |
| 第一轮真实，thinking 未指定 | 6 | 7847 / 24576 | 32423 | 0/6，全 length |
| 第二轮真实，disabled | 6 | 7697 / 5617 | 13314 | 0/6，原契约 |
| 协议修复后离线重放第二轮 | 0 | 无新增 Provider tokens | 0 新增 | 3/6，旧输出的新规则评估 |
| 本次第三轮真实，固定 f7d7d6f5 | 3 | 4596 / 1724 | 6320 | 2/3，新请求原始回答 |
| 三轮真实累计 | **15** | **20140 / 31917** | **52057** | 不将不同任务/契约混成单一可靠率 |

第三轮 Provider 耗时合计 13.766 s；prompt cache hit=1792、miss=2804 tokens。
usage 未给 reasoning_tokens 字段，记为未知，不伪造计量零；请求的 disabled 有证据。
没有核实账单或价格，货币成本仍为 unknown/null，不是零费用。

## 最终验收与最小后续建议

当前已真实证明：普通独立 LLM 可以产生可审核草稿；来源字段省略和覆盖诊断可用；
未注册任务能保留原文并由 N2 报告能力缺失，且不能伪装为普通 Reach。
当前未证明：完整 Reach 能直接走通真实解析到预览；所有关键语义和缺失定义能可靠提取。
三例小样本也不能证明跨任务普遍可靠性。

**本轮结束并提交证据；S130 的成功验收条件尚未全部满足。**
不自动追加开发阶段，以下仅是阻碍消除和主线接入前的最小建议，未实施：

1. 在现有提示词中明确 kind 与 source 的枚举区别，针对已观察到的混用做离线验证；
   不直接把错误 kind 改成合法值，也不引入重试 Agent。
2. 对已采用参考的定义、仅在问题中引用的参考数值及固定窗口包含关系，明确最小表达契约。
   若需代码调整，另行审核其范围；不能增加正式数值来源或偷偷放宽验收。
3. 强调结构设计范围与接触/碰撞评价缺失的提取；审核界面必须并列展示完整原文、
   unquoted_spans、LLM 问题和 Registry 诊断，不能只展示 intent 标签或自动确认缺口。
4. 主线只需薄入口调用现有独立解析和 compile_draft，展示参考身份与待审核预览，
   审批、任务身份与执行准入继续由原流程负责；先解决并获准验证上述 Reach 阻碍再考虑融合。

无需新 Agent 框架。本轮不改生产解析器、不合并主线、不启动正式科研、不再请求 Provider。
