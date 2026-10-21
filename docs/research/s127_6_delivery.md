# S12.7.5–S12.7.6：可靠输出与真实 SDK 科研接续

2026-10-21。**用户独立批准 A+B 后，完成 18 次真实多回合决策请求和 11 次真实 Strands 请求，
合计 29/30 次、1,106,209 actual tokens。旧会话合法生成结构，新会话实际初始化控制并消费反馈；
全新进程恢复两个实际 SDK 快照通过。无长度截断、重复发送、未知结果或未结 Provider receipt。**
83 项相关回归通过，包含原 14 个崩溃子场景；本轮没有新增物理/数学/NMPC/PPO worker。
生产 handoff 门禁仍关闭，S12.8 没有启动；可准备以原连续 Strands 路径开展独立授权的有限 Cold-start。
分支 `feat/sorosim-matlab-nmpc`，指定工作树；已重新 fetch，起点与远端均为
`f351104d75bd598ee14446589b50795bb9d1f129`，起点干净。其他工作树未改。

## A. 工程修复

`LiveBoundary` 原截断异常被本机 OpenAI `_base_client.AsyncAPIClient.request()` 的普通
`Exception` 分支包装为 `APIConnectionError`。原 Strands 连续路径还显式开启了截断放行；
默认重放路径也没有再次执行相同输出检查。

现在 SDK adapter 在输出交付前读取已持久化原字节，区分确认收到 HTTP、模型结束原因、
未验证工具字段和科学准入。HTTP 200 的 length/content_filter/aborted/资源中断/缺失完整结束
均不能作为 native 工具输出；SDK 包装异常会被还原成携带事实诊断的 `IncompleteModelOutput`。
CLI 输出结构化 `confirmed_incomplete`，以退出码 2 停止。
真正网络未知结果仍保持未知 reservation 并阻止重试，不被重新分类为模型截断。

首次收取、相同请求重放、SDK 重开和 `consumed()` 均保护不完整响应；
即使诊断调用显式允许读取原字节，SDK 仍不会交付任何部分工具字段，`consumed()` 也不能清除它。
未结清但已保存的完整响应在相同请求重放时使用原 receipt 结清，已结清响应不会再次计费。
原 body/reasoning 不改写，不创建 assistant 内容或工具调用，不修改第三方安装包。
本轮没有增加解除 incomplete 阻断的终态捷径；需要新请求时必须使用独立合法 Study。

[原 S12.7.4B 只读诊断](../../evidence/s127_5_provider/classification.json)仍为 HTTP 200、
length、8192 上限、1 次已计费请求、无工具调用、保存未消费响应、零未知发送。
原配置、字节、reasoning、账本和安全阻断保留；没有重发、迁移或使用其剩余 5 次额度。

科学引用增加按需 `/citation_eligibility` 视图：由唯一 `registered_references()` 清单派生
候选、任务、claim kind 与 supported inferences；默认摘要只展示简短规则、计数和最后一个登记条目。
可读 FamilySpace 或未登记运动样本不会自动获得支持证据资格，读取也不登记。
资格错误反馈给出被拒引用、原因、合法清单查询和缺少的验证。
原 `admit_decision()` 规则没有放宽；两次真实历史错误原样重放仍拒绝，合法数学/物理引用仍通过。
原默认摘要 <36,000 UTF-8 B 的限制仍通过；**字节不作为实际 tokens 报告**。

新发送增加输入 UTF-8 字节保守估计 + 最大输出 + framing 的容量门禁，超过冻结 context guard
时在 reserve/发送/计费前拒绝。该估计明确标记，不伪称 tokenizer 测量。

## B. 真实多回合决策

[冻结 manifest](../../evidence/s127_6_decision/manifest.json)、
[独立范围](../../evidence/s127_6_decision/scope.json)、
[实际逐请求结果](../../evidence/s127_6_decision/results.json)、
[真实用量与反馈审计](../../evidence/s127_6_decision/metrics.json)。
用户回复“批准 A+B”，[A 授权记录](../../evidence/s127_6_decision/authorization.json)绑定原范围 hash，
本地原始授权在首发前已存在，授权内容也已保存到原 A Store；没有借用 S12.7.4 许可。

三个真实截止状态：合法候选无性能结果、同候选已有完整物理失败、NMPC 完整但原任务失败。
完整/分层两组具有完全相同的任务、工具 Schema、初始科学证据和预算；每组至多三次连续请求，
总上限 18，实际 18/18。初始均没有旧聊天，后续只传递该组自己的完整 reasoning、原工具 ID 和实际反馈。
12 个后续请求均有真实工具反馈；原 assistant reasoning 与工具 ID 在下一次 wire 中原样保留。
15 个读取提案中 14 个本地读取成功，其中 **11 个成功读取结果确实交付了后续模型请求**，
另 3 个在各组三轮的最后一轮返回，不能把它们计为已经交付模型。没有完全相同的重复读取。
之前的 18 响应合成检查单独保留，不混入真实 Provider 用量。

`evidence_read` 复用正式 Store 及派生视图。科学提案在一次性本地副本内经过正式 dispatch、
契约、证据和实际前置检查；只给副本重新绑定当前代码，原科学状态和预算不变。
正式分析的启动边界已用 fixture 验证可拦截，没有启动数值 worker。
`passed`、`prelaunch_passed`、`not_tested` 和 `rejected` 分开报告；RL worker 内部检查未运行，
不能据此宣称其完整训练准入。副本输出不导入冻结状态，不伪造物理观测。

| 三轮状态 | 完整工作集 | 分层工作集 |
|---|---|---|
| 合法候选无性能结果 | 真实读取 → 离线 NLP 启动前通过 → 基线控制初始化完整准入通过 | 真实读取 → 继续读取 → 初始化提案漏填 hypothesis，被拒绝 |
| 同候选已有完整物理失败 | 读取真实诊断/样本 → NMPC 启动前通过 → 继续读取 | 一次结果包装对象上的 /samples 指针错误 → 改读正确原始引用成功 → 自主结构生成提案含额外字段，被拒绝 |
| 完整 NMPC、原任务失败 | 离线 NLP 启动前通过 → 读取结果 → 继续读取 | 读取两个候选参数 → 离线 NLP 启动前通过 → 引用全部七项新结果的合法 STOP |

完整准入通过的是隔离副本中的一项控制初始化与一次 STOP；另四项数值提案只证明启动前检查通过，
worker 均拦截。没有伪造新计算、验收或全局不可行结论。
三项拒绝都是分层侧：一个必需字段遗漏、一个错误读取指针、一个额外字段错误。
**未注册 supporting_evidence 错误为 0**，但这不证明无退化：每状态每组只有一个样本，
最后一轮错误没有第四轮修正机会。不得声称三个分层状态都产生了合法科研动作。
本次没有实际 PPO 提案；Direct/Residual PPO 的入口和不同资格由既有回归保留，不能当作 live 方法选择已验证。

| 实际 Provider usage | 完整组，9 请求 | 分层组，9 请求 |
|---|---:|---:|
| prompt tokens | 470,078 | 299,721 |
| completion tokens | 38,688 | 106,988 |
| total tokens | 508,766 | 406,709 |
| cache hit tokens | 429,952 | 199,040 |
| cache miss tokens | 40,126 | 100,681 |
| reasoning tokens，包含于 completion | 32,413 | 99,890 |

配对三轮链输入减少 **36.2402%**，总 tokens 减少 **20.0597%**；输出增加 68,300。
其中一次完整响应用了 64,434 completion / 62,452 reasoning tokens 后才给出工具调用，没有被截断；
它随后仍因额外字段被原 Schema 拒绝。输出空间与科学合法性是两个独立问题。
完整组有更多暖缓存，分层组实际 cache miss 和输出均更高；不能把总 token 下降解释成账单下降。
没有实际金额字段，不推算美元费用。未证明关键事实无遗漏、模型理解或方法优越性。
这是真实 HTTP 决策链，反馈没有 SDK Offload；不能直接等同于连续 Strands 的全程成本。

## C. 新 Strands 会话

[新 Study](../../configs/research/study_s127_6_handoff.json)、
[SDK 范围](../../evidence/s127_6_handoff/scope.json)、
[真实 SDK 结果](../../evidence/s127_6_handoff/live.json)、
[逐请求与真实工具审计](../../evidence/s127_6_handoff/live_audit.json)、
[全新进程恢复](../../evidence/s127_6_handoff/live_reopen.json)。
复用原 `build_harness()`、Store、Plan 和 `session_handoff.py`，没有复制 Agent 运行器。
新验证 Study 无旧候选/实验/数学/控制导入，Provider 上限 12，公共操作 60，固定输入物理最多 2，
数学/NMPC/PPO 为零；它是接续准入实验，不是完整科研成功试验。
[B 独立批准](../../evidence/s127_6_handoff/authorization.json)与 A 分开绑定，原授权保存在该 Store。

首个 invocation 发出 3 次真实请求，只读材料并结束，未产生科学动作，
[原始只读阶段报告](../../evidence/s127_6_handoff/read_only_prefix.json)保留，未宣称通过。
驱动补上仅允许安全只读前缀的接续入口：先核对原授权、原预算、完整旧 SDK、receipt 和所有 pending，
再向同一 session 发起新 invocation，绝不重发旧请求或重建 grant。对未知发送、保存未消费、
已有科学状态、已提交/准备中的 handoff、缺失 receipt 或不匹配预算继续拒绝。
一次本地预检发现可选控制清单尚未初始化，修正为原空状态语义；该失败没有发送 Provider 请求。
模型另有一次 SDK Schema 拒绝，随后在原会话内修正。驱动允许必要读取，并避免重复挂载 hooks。

实际旧会话累计 **7** 次请求后合法生成候选，接收真实反馈并结束 invocation；
按原协议持久化、独立重开验证和原子提交指针。新会话再用 **4** 次请求读取证据、
通过正式 Plan 初始化同一候选的控制、消费反馈并结束 invocation。合计 **11/12** 次，
6/60 次公共操作，零物理启动，剩余 1 次请求和 2 次物理容量未消耗。
源/目标都是同一 Study，候选身份连续，控制源是新生成的引用，没有重复执行旧动作。
旧生成工具结果的 7,062 字符按已配置 Offload 交付了精确 2,122 字符预览与 stash 引用，
完整结果仍保存；新初始化结果 950 字符完整交付。没有把预览当作完整结果阅读。

运行结束后用全新 Python 进程、禁止 HTTP 和工具执行的 transport 重开实际旧/新 SDK。
两个消息 hash、Store 指针与原工具配对全部一致，7 段旧与 4 段新 reasoning 均与原始响应逐段一致，
状态、账本、事件均不变；该检查没有读取凭据、增加 Provider 请求或执行工具。

合成 HTTP 下实际 SDK 经过四次响应：旧会话通过正式 Plan 生成结构、收到反馈并完成 invocation；
持久化旧 history，准备交接，保存新快照，独立恢复验证，原子提交 Store 指针；
新会话再实际初始化控制并消费反馈。新 SDK 没有复制旧工具历史，原候选和账本连续，
原工具 ID/结果配对，无 pending 或未结 receipt，零物理启动。

| 准入项 | 当前状态 |
|---|---|
| offline_protocol_passed | true，真实 SDK + 明确合成 HTTP |
| live_old_tool_round_passed | true，真实 DeepSeek 生成结构并消费反馈 |
| live_sdk_continuation_passed | true，新 SDK 实际发出 4 次请求 |
| live_scientific_action_passed | true，同候选合法控制初始化并消费反馈 |
| production_recovery_validated | false |
| production_handoff_admitted | false |

没有手工修改任何生产准入标志。本次验证的是隔离干净边界、生成/初始化和真实快照恢复；
没有发布面向完整生产工具组合和运行中 worker 的新配置准入入口，生产 opt-in 门禁保持关闭。
这不阻止原连续 Strands 主线。新 SDK 工具成功也不代表原 MuJoCo 任务通过：控制源仍未测量。

## D. 验证、成本及后续科研

[最终验证清单](../../evidence/s127_6_handoff/live_verification.json)记录 **83 个不同通过测试 ID**：
53 项聚焦、10 项会话恢复、5 项新驱动、13 项旧契约/预算选择、2 项旧 Provider 恢复检查。
包含原 14 个进程终止子场景，不重复计为 14 个额外测试。
另有完整新版 SDK 四响应合成集成试验、A 组 18 响应合成试验，以及真实 29 请求和零发送的新进程恢复。
一次旧 wire 捕获 fixture 补齐了新的输出检查边界接口；它从未接收或执行模型响应。
`git diff --check` 通过。测试使用原 Windows Python 和已有本地 MATLAB Python 依赖副本，
三个数值线程变量均为 1，没有启动 MATLAB/NMPC/PPO 或安装/升级依赖。
实际版本为 `openai==2.54.0`、`strands-agents==1.59.0`、`strands-harness==0.2.0`。

| 本轮真实用量 | A | B | 合计 |
|---|---:|---:|---:|
| 请求 | 18/18 | 11/12 | **29/30** |
| prompt tokens | 769,799 | 176,608 | **946,407** |
| completion tokens | 145,676 | 14,126 | **159,802** |
| total tokens | 915,475 | 190,734 | **1,106,209** |
| cache hit / miss tokens | 628,992 / 140,807 | 22,144 / 154,464 | **651,136 / 295,271** |
| reasoning tokens | 132,303 | 7,170 | **139,473** |
| 新物理/数学/NMPC/PPO worker | 0 | 0 | **0** |

29 次均为确认完成并结清的响应；无长度截断、重复发送、未知发送、未消费响应或未结 receipt。
本地接续与审计预检失败均没有发新请求，不能把它们算入 Provider 请求数。
生产 `tools/` 和 `extensions/` **+92/-11，净 +81 行**，没有新生产模块。
测试/探针/审计 9 文件 **+1047/-31，净 +1016 行**，其中 344 行是可复现的只读实际 Store/SDK 审计。
这些代码覆盖真实 SDK 异常包装、重复重放、隔离准入和实际响应对照，没有新增科研运行框架。
原任务、评价器、科学模块、正式 runtime 和封存证据无改动。
S12.6 原状态身份仍为 `d366a9a2791a6d35d881ca5c11bf82c182e03c38b912536ce8b900dfb071b5f3`。
原始 Provider、SDK 和 Store 文件只在忽略的本地 `runs/`；Git 只有代码、配置、派生统计和引用。

[容量与 S12.8 预检](../../evidence/s127_8_preflight/preflight.json)区分正式 32768 与新验证 65536。
本日核对 [官方 API](https://api-docs.deepseek.com/api/create-chat-completion/) 和
[模型资料](https://api-docs.deepseek.com/quick_start/pricing/)：1M 上下文，思考模式默认 64K 输出，
文档最大输出 393216；本轮只准备明确的 65536，不静默升至更高。
所有六个初始 wire 的保守输入+输出+8192 framing 均在冻结的 1,000,000 限制内。
Offload 仍只处理工具结果（500 preview / 1500 threshold），没有辅助模型调用或历史 reasoning 删除。

S12.6 实际消耗 43/48 Provider、8/64 物理（其中 2 NMPC）、1 次数学；首先短缺的是决策空间，
不是增加同一失败候选的零散物理扰动。因此提出讨论预算：96 Provider/8 protected、
300 公共操作/20 protected、64 共享物理、8 数学、4 NLP、4 BDF、4 NMPC、
2 PPO stages/131072 aggregate actions/每次最多 65536、2 独立 RL evaluation episodes，输出 65536。
这些只是新 Study 前需要独立批准和冻结的建议，绝不在运行中临时追加。

[S12.8 准入结论](../../evidence/s127_8_preflight/admission.json)：**原连续 Strands 路径具备准备独立授权的
有限 Cold-start 工程条件；不是科学成功保证，也不是分层决策无退化认证。**
保持分层证据、正式拒绝/修复、65536 新输出预算和逐请求容量审计；保留充分模型收尾额度。
三个分层状态并非全部得到合法动作，但错误在正式准入前被拦截，不需要通过放宽科学门槛恢复主线。
接续是辅助优化，生产 gate 继续关闭不作为下一轮主科研的硬前置条件。
观察到的最大 prompt 为 82,316，连同 65,536 输出和 8,192 framing 为 156,044，低于 1M；
不保证未来 96 次累计历史都能容纳，仍须保留真实用量审计和有界收尾。**S12.8 尚未启动。**
新研究必须使用原任务、全新 Store/SDK/Study、空实验/数学/控制种子/外部科学证据。
结构生成/修改、数学、NLP、NMPC、固定/时变控制、局部/模式搜索、Direct/Residual PPO 全部仍可选；
数学预测不替代原 MuJoCo 独立验收，不规定方法顺序。

## 提交与范围

已普通 push 并核对远端：

- `75f38de2ed50b29cb1248dd17b3d4aeec552b42f`：截断分类、拒绝与引用说明。
- `2843dcddf85a1b0b2cf9daa8a92bdc9002d6c0e4`：独立验证驱动、范围、配置与预检。
- `b6284333bedcc914cba3766b025ae1792ca491ae`：原离线交付与 82 项检查。
- `655b4df93de6bb39205892e61ea547c6ff3cf254`：18 次真实多回合及 A/B 独立批准记录。
- `99abf740432500131cc9dbf60224e5c4e320dd11`：只读 SDK 前缀的原 grant 接续及原失败阶段报告。
- `d0ac790002140b1e64983c54aac08c22baf2471d`：空控制清单边界与驱动回归。
- `1c4837df1cf33b70067222026b97e7fb15e39b4c`：真实新会话科研动作、响应对照与新进程恢复。

最终真实 SDK 审计及本文作为后继提交，完整最终 SHA 见交付回复。未 force push 或重写历史。
[A/B 完整范围](s127_6_authorization_scope.md)已获本轮独立批准并完成；
**S12.8 的具体预算、Provider 数据范围与新 Study 仍需独立授权并冻结**，不能沿用本轮余额或历史候选。

只读重算入口（需要本机原 Store，均不会请求 Provider）：

```powershell
python -m tests.research.s127_6_live_audit --delivery
python -m tests.research.s127_6_live_audit --reopen-b
```
