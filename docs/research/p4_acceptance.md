# P4 验收记录（2026-10-29）

本轮在 `mainline/research-harness-v2` / `fca8966ce43fbf644a059202bd871ac2daebcb06`
继续。用户追加授权真实调用及显式 DeepSeek 备用路径；按更保守的口径，将
Provider 验证、Main、Reporter 全部计入一个 Study 的八次总账本，保护性收尾保留三次。
不创建第二个科研 Study 清零预算，不自动重试，不进行长期运行。

## P4-A 工程检查

- 删除 `require_english` 及配置、请求、Main、Plan、Reporter、经验读取中的全文扫描。
  英文提示与编写要求继续保留；经验入口仍检查英文原始来源或有引用和审阅者的派生来源。
  不自动翻译、不改写原始中文资料。
- Provider 参数映射仍只有 `request_settings` 一个所有者。静态能力检查集中于
  `validate_provider`（配置解析与模型构造边界），角色投影不再重复验证冻结角色。
  实际发送处保留请求与冻结配置的一致性、离线能力不可冒充账号验证、容量及账本检查。
  它们分别保护发送、恢复、预算边界，不是重复的模型目录查询。
- 复用 working set 已有的完整 action trace，避免同一请求再次扫描全部动作；候选排序和
  profile artifact 每次只读一次；小型证据读复用已计算结果，只补原有读取标记。
- 删除 plan_schema 从未使用的 family_space 入参及其重复传递；实际领域约束仍由
  原 FamilySpace/生成入口拥有，不通过一个无效入参假装已绑定。
- `smoke` 必须提供 `--model`，目录排序不再选择模型，显式发送
  `reasoning_effort=none`。不提供 medium 开关、自动重试或回退。
- 旧 `research_roles_v1/v2`、on-demand v1、handoff/snapshot 校验仍承担冻结 R2 与历史
  SDK 恢复职责，保留。未证明已退休的版本不删除；本轮只删除明确退役的字符串扫描及对应测试。

测试：Gateway 全套 107 项，106 通过、1 项上游 Unix 专用测试跳过；新增 smoke 和请求转换
定向 22 项通过。Python 定向矩阵 35 项中 34 项当次通过，1 项 Windows SDK
`os.replace` 出现 WinError 5；该项隔离复验通过，另三项配置验收同次通过。此前同组原有
32 项通过；没有为此加入重试或修改 SDK 存储行为。宿主解释器及冻结单线程环境预检 ready。
所有上述测试均离线，没有科学 Worker。

### Gateway 进程与来源

原监听 PID 29388，`node src/cli.mjs serve`，Windows PEB 工作目录明确为
`D:\softrobot-agent\local-chatgpt-gateway\`，不是 V2。仅停止该 PID，未停止其他 Node。
保留原锁，由 proper-lockfile 的 30 秒 stale 机制接管；首次接管前报 runtime_busy，
没有删锁、账号文件或 DPAPI 凭据。V2 当前 PID 68704，版本 0.1.0，命令
`node src/cli.mjs serve`，工作目录为本 worktree 的 `local-chatgpt-gateway`。

现有 ignored `.devkit` 与旧目录固定 vendor 快照核对：20 个文件在撤销两处既定回调补丁后
文本一致；两个原始文件 SHA256 与 prepare 脚本完全一致，对应固定上游 commit
`0a36fefeb913055c8c7a1a29b63d82b96b2e841a`。沿用已准备的依赖并完成构建测试。
认证状态路径仍为 `%LOCALAPPDATA%\LocalResearchChatGPTGateway`，Harness Gateway 凭据约定
仍为 `~/.softrobot-agent/chatgpt-api.json`；未覆盖、迁移或提交认证配置。

`/health`：connected，plan_usage=true。真实 `/v1/models` 返回 403 `api_error`，
retryable=false，提示策略、权限或服务地区限制；不能从这个错误唯一判断原因。
停止 ChatGPT 路径，不重试目录、不重新登录、未发出 ChatGPT 推理。
账号连接/plan usage 可见不等于目录/推理/模型工具能力可用。

### 同一 R2 边界的完整离线请求

只读打开原 Store，使用 handoff event 110 的 `source_state`，与原 request event 115
配对。科学状态、模型、系统指令、历史、预算及私有经验范围一致，只改变 V2 路由及投影。
原 Store 469 events、51 calls，未修改。完整请求仅在本地 ignored `runs/p4-context` 保存，
防止把 R2 私有经验随公共报告发布。可复现脚本为 `tests/research/p4_context_audit.py`。

| 部分 | V1 字节 / Token 估计 | V2 字节 / Token 估计 |
|---|---:|---:|
| 完整请求 | 16,376 / 4,284 | 32,392 / 8,919 |
| 系统指令 | 1,019 / 185 | 1,019 / 185 |
| 历史 | 535 / 116 | 535 / 116 |
| L0（排除独立反馈字段） | 9,275 / 2,306 | 14,785 / 4,150 |
| Schema | 2,757 / 635 | 12,687 / 3,085 |
| 反馈 | 1,585 / 446 | 1,585 / 446 |

分项是各自独立序列化的诊断大小，不能直接相加成为包含 framing 的总请求。
使用仓库固定 DeepSeek V4 tokenizer，属于离线估计，不冒充实际 API usage。
V2 更大：旧请求只有 evidence_read/route，已加载 generate 丢失；V2 保留 generate、
精确导航以及 selected/submitted 区分。反馈 tool ID 一致。Mock 已确认导航 query 可达、
检索不卸载 Plan、提交一次、handoff 后状态保持。大小不支持进一步压缩的收益结论，
本轮未删关键约束以压缩 Token。

### 历史脚本处理

- 保留：当前 `python -m tools.research` 路径、CLI/测试有调用的科研模块、数值内核、
  仍用于恢复/审计的 s8/s125 及 R2 fixture、历史证据生产脚本与其来源身份。
- 本轮删除：仅明确退役的全字符串扫描及其专用测试；不批量删除脚本。P0 已删除的无调用
  `build_sorosim_s55_packet` 不再恢复；原有数值 Runner 不在本轮合并范围。
- 可归档建议：一次性 build_/prepare_/audit_ 研究脚本可在逐项确认 CLI、测试、文档和归档
  provenance 引用后列入归档清单；仅凭命名或旧日期不能认定无调用。此项是建议，未执行移动。
- 已确认且已修复的重复见上文。Reporter 的预算/报告读取、完整 context 到 L0 的多步投影
  可能还有成本，但未证明可无损替换；不把推测当作删除理由。

## P4-B/C 实时验收准备

ChatGPT 目录失败后按用户明示授权改用 DeepSeek。真实目录确认 deepseek-flash
（DeepSeek-V4.1-Flash）和 deepseek-v4-pro。不凭目录顺序排名费用。
沿用当前正式运行配置的 deepseek-flash，Main/Reporter none。

唯一 Study：`p4-m5-none-20261029-a01`，配置 `configs/research/study_p4_m5_autonomy.json`。
任务、FamilySpace、独立 evaluator、两次数学/两次物理上限及每次 native control 限制与 pending
模板一致；无经验索引、无 PPO/NMPC、无额外 local solve/NLP/BDF。两次只读工具协议验证也
消耗这个 Study 的 Provider 总账本。验证通过后才运行自主科学决策。

GPT-5.6 Luna 的官方文档将其描述为面向成本敏感工作的模型，支持 none/medium；这不能证明
当前 ChatGPT 账号授权或实际 plan 额度。官方资料：
[Luna](https://developers.openai.com/api/docs/models/gpt-5.6-luna)、
[ChatGPT 价格与共享用量](https://learn.chatgpt.com/docs/pricing)。本轮不宣称它全局最便宜，
也不把 API 单价套用为 ChatGPT plan 的实际费用。

## P4-B/C 最终实测结果

**真实 DeepSeek function/result 闭环通过；首次自主科学行动未通过。**
ChatGPT Gateway 的账号目录路径仍受 403 阻塞，不能把 DeepSeek 成功写成 ChatGPT 成功。
本轮不再发送推理，不重开 Study，不启动完整长期科研。

运行实现为 `9c7d674803225cba7265f906b331e81159a11751`（同时记录于
`evidence/p4_provider_acceptance/manifest.json` 的 `execution_commit`）；前一个提交为 `f9b1f396994aec22167022fbcfd8c0e6c04a8d00`。
首个 Main 启动在发送前触发 `SDK_HISTORY_HAS_NO_TRUSTED_STORE_ANCHOR`：共享账本中的
只读验证被误认为 SDK 对话。修复仅在 SDK 历史为空时排除已知 Reporter/验证用途；
conversation、summarization、未知用途及非空无锚点历史仍拒绝。两项定向测试通过。
随后在同一个 Store 显式迁移实现，保留前两次请求；未重试已经发送的推理。

### 逐次请求

全部是实际 `https://api.deepseek.com/chat/completions`，模型 `deepseek-flash`，
`thinking.type=disabled`、`reasoning_effort=none`。请求 1–2 属只读协议验证，3–7 属 Main；
Reporter 实际调用为 0。所有 HTTP 200，finish_reason 均为 tool_calls 或 stop。

| 全局次数 | 实际可用 Schema | 模型实际选择和结果 | 实际 Token（输入/输出） |
|---|---|---|---:|
| 1 | p4_echo | 自主 function call，参数 token 正确；工程函数成功 | 325 / 48 |
| 2 | 无 tools | 原 ID 回传结果后，准确复述 token、success 和非科学证据属性 | 161 / 41 |
| 3 | research_plan(generate), research_route | 选择 route(evidence_read)，成功；未提交 Plan | 5,666 / 54 |
| 4 | 上述两项 + evidence_read | full 读取冻结 FamilySpace，成功；未提交 Plan | 6,827 / 135 |
| 5 | research_plan(stop), evidence_read, route | 读取 working_set 的空候选/方法/结果索引，成功 | 8,074 / 189 |
| 6 | 同 5 | full `/result` 指针错误，返回精确导航；同轮 working_set `/all_fresh_results` 成功返回空列表 | 5,808 / 274 |
| 7 | 同 5 | 再读根 working_set 与 summary，均成功，但无 Plan/STOP | 6,079 / 249 |

原始验证 call ID：`call_00_nZUNasPXj1VOaAKqQ8Xh1209`；原参数
`{"token":"p4-live-readonly-20261029"}`。第二次请求回传同一个 ID 和真实本地执行结果。
两次合计 575 Tokens，没有强制 tool_choice、Mock、上游重试或模型降级。

完整 Schema、每个真实 tool call ID/参数、结果、错误与反馈引用在公共新证据目录
`evidence/p4_provider_acceptance/`。每次请求/响应及反馈独立保存；manifest 汇总引用、
大小、usage、finish_reason 和共享账本。响应文件是原 HTTP body 的精确字节；请求文件是
Store 保存的原请求语义的 canonical JSON，不冒充原 HTTP 空格/键序。原始 Store 仍在
`runs/research/p4-m5-none-20261029-a01`，未覆盖旧证据。
导出后逐项复核七个请求的原 request_hash、七个原响应的 SHA256，以及七个已结算、
各扣一次 model_call 的 completed receipt，全部一致。最后 Provider 定向七项测试通过。

真实推理共 **7/8**，输入 **32,940**，输出 **990**，总 **33,930 Tokens**。
其中 Provider 报告缓存命中 6,784 输入 Tokens。所有七次均有 usage；实际 money/费用、
余额及额度折算保持 unknown。未报告的 reasoning_tokens 也保持 unknown，不由 none 推断为零。
最大实际 HTTP 请求 28,566 字节，小于 1 MiB，但这是 DeepSeek 请求，不能算作 ChatGPT
Gateway 的真实大上下文验收；Gateway 1 MiB 限制仅有离线 HTTP 测试证据。

ChatGPT 没有推理，因此未验证真实上游 `response.completed`、opaque reasoning 续接、
具体账号模型 function tools/none/medium。DeepSeek 按其原生 chat-completion
finish_reason 验证，没有伪造 Responses 事件。Main/Reporter 独立配置有定向 Mock 证据；
Reporter 在本轮没有科学结果可解释，不能宣称真实 Reporter 路径通过。

### 首窗口、保护边界与停止

累计四次时安全暂停：Main 两次分别是路由和必要的首次 domain 读取，没有反复刷同一输入，
没有候选或 Plan。generate Schema 持续可用，full FamilySpace 反馈完整交付，精确查询未丢失。
此时剩余四次，但原有 `next_request_will_protect = total - 1 <= reserve` 与扣账后
`protected(remaining <= reserve)` 的组合，已经将第 5 次限制为收尾。也就是说，原代码
在 8/3 配置下实际最多四次科学可行动请求；再扣除两次协议验证，只剩两次 Main 科学机会。
这是已观察到的预算边界与“约五次探索”预期差异，未在运行中更改冻结语义来争取成功。

请求 5–7 只能收尾；Main 确实读取了空候选/结果信息，但又继续浏览，没有自主 STOP。
第 7 次后已在工具全部结算、无 pending、无 unconsumed response 的安全边界，Supervisor
调用原有 engineering_closeout 停止；model_stop=false、selected=null、observed_pass=null。
最后一次额度保留未花，不再发送重复请求。不是成功 STOP，不是科学不可行性结论。

| 级别 | 本轮结果 | 证据与原因 |
|---|---|---|
| L1 合法科学 Plan | 未达到 | plans=0；路由和证据读取不是 Plan |
| L2 新科学证据 | 未达到 | candidates=0，数学评价=0，物理结果=0；协议 echo 不是科学证据 |
| L3 基于新科学反馈的下一决策 | 未达到 | 没有新科学反馈；只有工具/导航反馈被读取 |
| L4 任务通过和 SELECT/STOP | 未达到 | 未评价任务、未 SELECT、未模型 STOP；仅工程关闭 |

本轮证明真实模型会使用本地函数并利用函数结果生成文本；没有证明它在当前额度内提交科学
行动。不能把预算只允许两次科研决策的观测，推广成同一模型在八次纯科研请求内也会失败。
同样，未观察到科学行动并不说明 frozen M5/BF5 不可行。

### 实测后的额外最小修复

请求 5 选择的 working_set 字段原始结果仅 879 字节，但旧实现仍把根 working_set
无条件包装成导航，再交付摘要。这是已确认的重复组织。实测结束后改为所有 <=4096 字节
的既有视图直接返回已计算值，保留原读取标记；大型结果继续导航，完整 formal full read
继续精确交付。小型字段读、大型导航、完整读取接续三项定向测试通过。没有用剩余额度
重新跑该 Study；上表和原始证据仍反映修复前实际行为。

### 下一步建议与公平性

优先明确并测试请求预留的边界含义，以及能力验证费用如何占用短 Study 的科学决策机会。
先在同样有限预算下验证 none 的首次合法科学行动，再考虑 medium；当前没有可靠的
none/medium 行为对照，也没有理由立即启动完整自主 Study。

V2 的收益是检索时保持可执行 Plan、导航与动作状态的连续性，代价是这个配对请求明显更大；
真实 Main 仍只进行了读取，不能声称上下文重构已改善科研决策。R2 有私有 M5 短卡，
本轮没有经验索引；再加上此次严格共享校验费用，不能把行为差异全归因于 V1/V2。
严格配对必须固定模型、任务、预算、背景知识和经验交付；历史中文资料仅能通过有原始
引用且经审阅的英文派生来源进入模型，不在本轮暗中翻译。

未修复项区分：预算保护提前一个请求是已确认的运行语义；root working_set 小结果导航
重复已修复；完整 context 到 L0 的多层计算及 Reporter 重复查询仍只是优化候选，需要
独立证据。旧 frozen roles/handoff 仍有真实恢复职责，本轮没有将其归为无用兼容代码。
Store artifact hash 与 Provider request identity 使用的 JSON 编码不同，不能仅凭某些
英文请求的散列碰巧一致就合并，保留原身份语义；没有新增第二套 digest。

R2 最终复查仍为 469 events、51 calls、0 未结算。旧 Study、原封存证据、任务规则、Store、
Session 数值内核、Benchmark evaluator、FamilySpace、MATLAB 和扩展科学代码均未修改。
本轮唯一 Study 最终停止，账本 model_calls=7、tool_calls=7、backend_solves=0、
worker_calls=0、无占用资源、余 1 Provider 请求；没有科学 Worker、PPO 或长期运行。

代码提交：`f9b1f3969`（定向精简与冻结配置）、`9c7d67480`（真实发现的恢复归属修复），
本报告、精确新证据及小型 working_set 修复随最终提交交付；最终 HEAD 和 push 结果见交付消息。
