# 官方 API 目录与 GPT-5.4-mini 实测（2026-10-29）

目录及真实调用权限已经验证。用户列出的两组 17 个型号全部出现在该 Key 返回的目录中。
本次 GPT-5.4-mini 的有限科研测试**未达到 D4，也未达到 D1–D3**：没有产生经准入的科学 Plan 或新候选。
这不是“模型没有调用权限”，也不能据此证明模型不具备完成 D4 的能力。

## 目录、额度及原验证尝试

官方 `/v1/models` 首次直连在建立连接阶段发生 ConnectError，没有 HTTP 响应。
沿用用户之前指定的 `http://127.0.0.1:7890` 代理后，一次目录请求返回 HTTP 200，列出 130 个模型。
完整型号及日期见 [目录审计](openai_api_models.json)，未发布凭据、账号身份或 organization 信息。
目录只确认可见性，不能证明每个型号都已通过推理、工具、端点或免费额度验证。

| 用户提供的每日共享池 | 目录中确认可见的型号 |
|---|---|
| 250,000 Tokens | gpt-5.4、gpt-5.2、gpt-5.1、gpt-5、gpt-4.1、gpt-4o、o1、o3 |
| 2,500,000 Tokens | gpt-5.4-mini、gpt-5.4-nano、gpt-5-mini、gpt-5-nano、gpt-4.1-mini、gpt-4.1-nano、gpt-4o-mini、o3-mini、o4-mini |

共享池数额来自用户，接口未独立返回适用资格、当前余额、有效期或重置时区。
没有把池总额当作每个模型各自额度，也没有把目录中额外可见的 Luna/GPT-6 等型号声称为适用这个赠送池。
本轮只有 mini 的推理和原生工具调用被实际验证；其他 16 个型号没有逐一发送请求。

用户指定 mini 前，曾尝试一次 gpt-5.6-luna 短文本调用验证。独立验证脚本把
本地 SDK 的同步 LegacyAPIResponse.text 属性当作异步方法调用，发生本地 TypeError，未封存原响应正文。
该尝试、原请求和错误元数据保存在 ignored runs；响应内容、usage、费用保持 unknown，不声称成功或零消耗。
没有补发 Luna 请求，没有将其列入已验证官方 API 型号。后续执行仅使用用户明确指定的 mini。
这条独立验证尝试不隐藏在 mini Study 的九次账本中，须单独保留。

目录/短文本检查阶段没有创建 Study。之后用户明确提出使用 mini 做“上述真实测试”，才创建下述独立有限 Study。

## 冻结范围与权限证据

- Study：`p5-m5-openai-mini-none-20261029-a01`。
- Provider：官方 `https://api.openai.com/v1/chat/completions`，所选独立 Key，经 7890 HTTP 代理；不经过 ChatGPT Gateway。
- 请求型号：gpt-5.4-mini；实际成功响应型号：gpt-5.4-mini-2026-03-17。
- Main/Reporter 均为 none、store=false；实际 Reporter 请求为 0。
- 沿用前两组的相同 M5/BF5、FamilySpace、完整域起始资料、科研指令及资源数量；没有旧 R2 私有经验。
- 原上限 9 次共享 Provider 尝试，前 6 次可探索、最后 3 次只收尾；数学 2、物理 2 和原 native caps 不扩大。
- 不做 Echo；不自动重试、回退、PPO、隐式补预算或创建替代 Study。
- 与前两组一样使用持久 SDK 会话，关闭自动 Handoff；模型自主决定参数及动作。

官方文档确认 [GPT-5.4-mini 支持 none 和 function calling](https://developers.openai.com/api/docs/models/gpt-5.4-mini)。
真实成功响应进一步证明本 Key 在当时具备该模型的 Chat Completions 推理和本地函数工具请求权限。
官方 Key 凭据文件未修改，仍在仓库外；没有借用 Gateway OAuth 或 DeepSeek Key。

## 逐轮结果

| 账本次数 | 结果 |
|---|---|
| 1 | 官方 HTTP 400：research_plan 顶层 allOf 不被工具 Schema 接口接受，模型没有生成响应。失败保留并计数。 |
| 2 | 修复并核验首请求错误恢复后，HTTP 200，自主 route 到 generate。 |
| 3 | HTTP 200，提交具体生成 Plan，含结构、材料和 routing 参数；引用 FamilySpace 作为 supporting_evidence，受到 UNREGISTERED_RESEARCH_EVIDENCE 拒绝，未执行生成。 |
| 4 | HTTP 200，针对错误自主 route 到 evidence_read。首窗口检查后确认有具体提案和纠错进展，允许在原额度继续。 |
| 5 | 官方 HTTP 400：evidence_read 也有顶层 allOf。此前修复遗漏该工具，失败由工程负责，保留扣账。 |
| 6 | 修复后 HTTP 200，读取正确 FamilySpace reference 的 /citation_eligibility，返回空列表。最后一个探索请求耗尽。 |
| 7 | 保护期 HTTP 200，提出 STOP，但仍引用未注册 FamilySpace，被同一证据准入拒绝。 |
| 8 | HTTP 200，再次提出 STOP，仍保留错误引用，重复被拒绝。 |
| 9 | HTTP 200，只 route 到 evidence_read，没有余量再读取或提交 STOP。随后工程封存。 |

第 6 次的空列表是实际有效工具输出，没有替换或伪造。它表示没有注册科学结论证据，不意味着读取本身失败，
也不证明原结构或任务不可行。模型第 7 次解释中把先前生成提案的引用拒绝说成“prior read was rejected”，表述不准确。
第 7–8 次重复引用已明确拒绝的来源是模型反馈利用失败，不能全部归因为工程问题。

逐轮 Schema identity、原始 call ID、模型参数、反馈及原始回执引用见
[脱敏执行审计](p5_openai_mini_results.json)。完整请求、响应和 SDK 文件只保存在 ignored 本地 Store。

## 实际成本与停止状态

| 项目 | 结果 |
|---|---:|
| 账本尝试 | 9/9 |
| 官方 HTTP 200 模型响应 | 7 |
| 官方 Schema HTTP 400 | 2 |
| 正常探索的实际模型响应 | 4 |
| 收尾模型响应 | 3 |
| 已知 prompt Tokens | 62,553 |
| 已知 completion Tokens | 1,358 |
| 已知 total Tokens 小计 | 63,911 |
| 全账本 usage / 费用 / 免费池剩余额度 | unknown |
| 候选 / 数学评价 / 独立物理评价 / Reporter | 0 / 0 / 0 / 0 |

两条 400 没有 usage，不能把缺失项默认为零。63,911 是七条成功响应的小计，不是含所有缺失项的精确总账。
在这个小计之外还要保留前述 Luna 独立验证的未知消耗。没有将用户给出的免费池当成实际已核验计费。

本轮最大完整请求 46,780 字节；现有上下文容量检查通过，没有截断恢复或科学 Worker。
回执审计确认 request digest、原始 HTTP 响应 SHA256、结算均可恢复，所有已回传工具结果文本与保存反馈逐字相同。
最终状态 stopped；pending Provider、pending science、unconsumed response 均为空。
收尾为工程额度封存，不是模型成功 STOP。原 P4、DeepSeek 与 Gateway Luna Study 保持封存，没有额外请求。

## 本轮最小工程修改与验证

1. 在 ModelConfig 增加可选 proxy_url；未配置时不序列化，旧 R2 模型身份保持不变。
   官方目录和 LiveBoundary 都使用所选代理，不自动切换网络或身份。
2. 新 V3 的固定动作 Plan 将条件约束放在原属性内，避免官方拒绝顶层组合。
   保留 hypothesis、expected/weakening observation、固定条件、停止条件、interpretation、decision、候选及 generation 约束。
3. EvidenceQuery 的单个 allOf 条件等价展开为原 if/then；正常/保护期复用同一 Schema 入口，fields 视图仍必须有非空 fields。
   最初只修 Plan 而遗漏读取工具，确实额外消耗一次尝试，没有掩盖该工程失误。
4. 首次工具 Schema 400 没有模型对话锚，原恢复检查拒绝接续。现在仅在新 V3、唯一首请求、明确已结算的对应 400、
   精确相同初始 SDK 消息和原请求、且已显式绑定修复时，恢复该原始初始消息；无自动重发、会话删除或预算重置。
   其他未知、无锚或旧版本恢复要求不放宽。
5. 只读审计原先假设反馈 JSON 是对象，已补充实际空列表输出的记录；不改变工具行为。

离线验证：代理/旧身份/Provider 12 项；固定动作 Schema 和预算 7 项；首次拒绝恢复及 Provider 11 项；
读取 Schema 与上下文 8 项；旧 recent-round 路由/恢复 9 项，均分别通过。组间有重复用例，不相加冒充唯一用例数。
对本轮 13 个待发布文件核对当前官方 API Key，精确匹配为 0；原始流量和凭据未纳入提交。
没有修改 Store、科学内核、任务接受标准或自动替模型修 Plan。

提交及 push：`d66653b4b`（目录/代理/mini 冻结）、`3127bace3`（Plan Schema）、
`2dfd90e1f`（首错误恢复）、`4f9e44aba`（读取 Schema），均在正式 `mainline/research-harness-v2`。
最终中文报告与脱敏审计由结算提交记录，最终 HEAD 见交付消息。

## D4 判断

D1 没有通过：唯一生成 Plan 因证据引用未通过准入。D2 没有候选或新科学结果，D3 没有可消费的新科学结果，
D4 更没有独立物理通过和规定的读取、SELECT/STOP。

本次实际只提供了四个无工程拒绝的探索响应，不能作为与前两组严格相等的模型决策机会试验；
也不能以“没达到 D4”否定先前 DeepSeek 已观察到的 D1–D3 或 Gateway Luna 的 D1–D2。
可以确认 mini API 权限及工具闭环可用，但现在没有依据承诺它能在九次内完成完整科研链。
如继续，应先明确背景约束与注册结论证据的区别，并在同一 Study 保留原账本、按新明确授权增加有限决策机会；
不重开同模型 Study 清零，不以扩大数学/物理预算或放宽原准入制造 D4。本轮到此停止。
