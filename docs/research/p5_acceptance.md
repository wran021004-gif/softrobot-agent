# P5 验收记录（2026-10-29）

工程修复与离线准备已完成。ChatGPT 准入尚未通过；真实 Main 决策测试未运行，不能宣称达到 D1–D4。
本轮没有新的推理请求、科学 Worker 或正式 Study。原 P4 已停止的 7/8 账本未恢复。

## 1. ChatGPT 准入及代理

基线分支 `mainline/research-harness-v2`，起点 `c56bae83e86ec78451f0acd68c9f78f91f5c503c`。
已阅读官方 [Models and Inference](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference)、
[Errors and Recovery](https://developers.openai.com/siwc/token-sharing-open-source/errors-and-recovery)、
[Preview Limitations](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations)。
固定 DevKit 使用官方 `https://api.openai.com/v1/models`，推理使用官方 Responses 端点；没有非公开 backend-api。

只读诊断直接在内存中解密现有 DPAPI 状态，不创建 SDK client、不调用可能迁移状态的 Store、不续期、不登录、不联网。
文件检查前后字节一致。已确认：选中 profile 存在、保存状态 connected、六个必需 scope 存在、
动态注册 client 已保存、ID token subject 与 profile 一致、audience 与 client 一致、issuer 符合预期、
access token client 与注册一致、Host ID 格式有效。没有输出账号、client、host、token 的实际值。
这些是已保存 claims 的一致性检查，没有重新验证签名，也不证明上游准入。

当前 access token 在检查时已过期；不能据此认定它导致了 P4 的 403。
固定 DevKit 没有独立保存可核对的 Workspace 绑定，不能排除 Workspace 或其他外部策略。
P4 的 `/health` connected 与 plan_usage=true 只证明当时本地保存的连接/授权状态。

P4 的目录请求已到达上游，标准化结果为 HTTP 403、`api_error`、retryable=false、
responseShape=`undefined`，没有 request ID。源码说明：非 JSON 错误被 DevKit 标准化时不会保留原正文；
上游未提供或 SDK 未保留的信息现在不能恢复。新增离线 Gateway 测试确认：当 SDK 确实提供 code、
upstream status、request ID 和 param 时，现有转换会保留这些字段。没有仅为补日志重发原 403。
现有证据不能唯一判定是账号、地区、Workspace 还是其他服务策略，状态记为 `blocked_external_admission`。

用户明确要求使用本机 7890 代理后，仅停止本轮之前启动的 V2 PID 68704，保留锁及 OAuth/DPAPI 文件，
等待原锁自然过期，再从 V2 运行 `npm run start:proxy`。记录时 PID 379820 监听 `127.0.0.1:8787`，
绝对启动命令为 V2 `node --use-env-proxy .../local-chatgpt-gateway/src/cli.mjs serve`；
代理 PID 26412 监听 `127.0.0.1:7890`。Node 为 v24.19.0，Gateway 包版本 0.1.0。
代理仅通过该启动进程的 HTTP_PROXY/HTTPS_PROXY 设置，NO_PROXY 保持 loopback 直连。
本地 fake proxy 测试验证 Node 原生代理路由，不访问外部网络。
该开关见 [Node 官方文档](https://nodejs.org/download/release/v24.20.0/docs/api/cli.html#--use-env-proxy)。

代理启动后尚未复验真实目录；一次目录验证的明确授权正在等待用户回复。
没有把代理作为绕过地区或服务策略限制的方案，没有换身份、重复登录或猜测模型 slug。
GPT-5.6 Luna 是否存在于当前账号目录、支持本地工具、可以实际推理，均未验证；不声称它最便宜。
用户现在无需另开 Gateway，重复启动仍会遇到 runtime_busy。

脱敏支持材料见 `p5_admission_diagnostics.json`。它包含端点、错误边界、版本和一致性布尔值；
没有账号或 OAuth 私有信息。若官方需要原始 request ID，本轮证据无法提供，应明确说明缺失。

## 2. 预算提前保护的原因及修复

旧实现同时使用发送前 `remaining - 1 <= reserve` 与扣账后 `remaining <= reserve`。
当余额为 4、预留为 3，第五次请求先扣至 3，当前调用的工具也被保护；实际探索只有前四次。
P4 前两次用于已通过的协议验证，因此 Main 只有两次正常研究请求，不能据此判定模型在充分窗口下不能生成。

新配置显式选择 `budgets.provider_reserve_policy=last_requests_v2`。
单一 `provider_allowance` 在原有发送前原子预算检查中确定当前已购买请求的阶段，
阶段随现有 r3_request metadata 保存；同步工具执行与准入钩子使用该阶段，保存响应恢复时取回原阶段。
没有新账本、Supervisor 预算系统或持久状态机。成功、公共操作、科学资源等原保护仍生效。

| 总上限 / 收尾预留 | 可探索请求 | 只收尾请求 | Reporter |
|---|---|---|---|
| 旧冻结 8 / 3 | 第 1–4 次 | 第 5–8 次 | 共享同一总账本 |
| 新语义 8 / 3 | 第 1–5 次 | 第 6–8 次 | 共享同一总账本，消耗探索机会 |
| P5 待授权提案 9 / 3 | 最多前 6 次 | 最后 3 次 | 若调用会减少 Main 可用次数 |

没有版本字段的旧 Study 保持旧行为，不改写旧计费、授权或恢复语义。
待授权提案的 9 次来自 P5 文本建议的六次探索加三次收尾，**不是已授予的新额度**。
没有创建该提案的正式 Store；不把待授权文件当执行许可。

实际 SDK + MockTransport 覆盖初始余额、新旧版本、第五次提交 generate、后三次拒绝探索、
Handoff 持续加载 Plan、选定未提交状态、Reporter 共同扣账、最后一次响应恢复不重发、第九次拒绝。
测试中的候选是明确标注的工程夹具，不算科研证据。

## 3. 上下文与 Schema

新配置选择 `on_demand_tools_v3`；旧 v1/v2 仍服务冻结恢复，不批量删除。
比较使用相同 R2 边界（handoff 110 / request 115）及 P4 第四次反馈后边界（56 / 60）。
旧 Store SHA256 检查前后相同。完整输入留在 ignored `runs/p5-offline`，公共 Git 仅存指标。
全部 Token 是固定 DeepSeek tokenizer 对序列化请求的离线估计，不是 API usage。

| 边界 / 投影 | 完整字节 | 完整 Token 估计 | L0 Token（排除独立反馈） | Schema Token | 反馈 Token |
|---|---:|---:|---:|---:|---:|
| R2 / P4 V2 基线 | 32,392 | 8,919 | 4,150 | 3,085 | 446 |
| R2 / 修正预算、未去重 | 32,392 | 8,919 | 4,150 | 3,085 | 446 |
| R2 / 修正预算并去重 | 29,350 | 8,120 | 3,782 | 2,715 | 446 |
| P4 / 旧保护，仅 STOP | 27,932 | 8,650 | 2,064 | 1,843 | 3,285 |
| P4 / 修正预算、恢复 generate | 34,904 | 10,442 | 2,415 | 3,207 | 3,285 |
| P4 / 同一合法 generate 并去重 | 31,876 | 9,633 | 2,039 | 2,837 | 3,285 |

分项是独立序列化诊断，不直接相加为完整 framing。P4 旧值为本次离线重投影，不冒充当时网络请求原字节。
R2 相同合法性下减少约 9% Token；P4 相同 generate 合法性下减少约 7.7%。
P4 修复后比旧 STOP 更大，是因为恢复了原来被保护逻辑移除的科学工具及域约束，不能把它算成压缩失败或隐瞒。
P4 保留完整 FamilySpace 原反馈 8,768 字节，不为了比例削减。R2 系统/历史/反馈及私有经验交付范围不变，
R2/V2 科研行为没有进行严格配对，不将历史私有经验差异归因于上下文。
完整分项字节和输入 digest 见 `p5_offline_metrics.json`。

| 重复项 | 处理及保留价值 | L1 / 原来源 |
|---|---|---|
| action_menu 与目录动作名 | 原状态/原因行移动到唯一 research_plan.actions；其他分析要求单独保留 | 原 registry/准入；没有移除合法动作 |
| loaded_tool 与 continuation | loaded 移入 continuation，plan_selection 仍区分 selected_not_submitted | 原路由及 Handoff 记录 |
| continuation.recent 与 pending_feedback | 同 tool ID 已交付的 recent 行省去；原反馈逐字保留 | 原工具反馈及精确 ID/导航 |
| 当前意图与历史相同 hypothesis | 历史保留 outcome，以 intent_at 指向相同当前意图；不同内容不合并 | full_trace_query 仍可读完整 trace |
| generation_contract 与 Schema | 已加载 generate 时 identity/version 由 Schema const 拥有；domain_query/scope 保留 | 冻结 FamilySpace full read |
| 空控制/报告/历史 | 未生成且无来源的控制空壳省去；空报告留 status；空 trace 留 total 和查询 | 候选状态、完整 trace 与原报告来源 |
| Plan 无关分支和 title | 删除选定动作不可能命中的分支与注释；不删除实际字段名、科研记录或定义依赖 | 原 Plan/Pydantic 继续执行准入 |

Schema 同时绑定实际冻结 family_space_identity、可执行 segment enum、tendon bounds，
没有替 Main 选择参数。科研假设、预期观察、削弱观察、固定条件、停止条件、解释和 decision 全部仍必需。
任务、候选状态、预算、未完成意图和 pending_feedback 在去重前后逐项相同；
generate 保持加载、小型 working_set 直接交付、原 evidence reference/view/pointer、来源限制和已提交回执继续保留。
未对所有已读事实做激进摘要或删除：没有证据证明进一步压缩不损失决策价值。

## 4. 决策输入与 D1–D4

已从 P4 第四次请求完成 FamilySpace full read 后的真实状态构造独立决策输入，
状态 identity 为 `4090243c87d7cf8c66a48caea0b858f324cb70e037ae8eb30a7e548cf4bc5fbb`。
只使用该边界及之前的事件；若当时目录已被旧保护投影覆盖，只从此前保存请求恢复目录，不读取未来成功信息。
输入保留真实任务、完整域反馈、Schema、未完成意图及来源，没有填入生成参数或指定科研路线。

`study_p5_m5_decision_pending.json` 与 none/medium 本地输入仅作待授权准备。
它们的任务、工具、来源、预算相同，只有显式 reasoning 配置不同；DeepSeek 的 medium 沿用
现有 enabled/high 映射，不冒充其原生支持 medium 枚举。未来执行复用现有决策探针与正式 Harness。

D1（合法科学 Plan）、D2（真实新结果）、D3（消费反馈并决定下一步）、D4（正式通过及 SELECT/STOP）
全部为 **未运行**。P5 要求新的明确授权与冻结额度，目前没有收到，不复制 P4 授权、不恢复原 Study。
本轮新增真实 Provider 推理请求 0、实际 Token 0；没有新增推理费用或 usage 估计。
P4 的既有 7 次请求、33,930 Token 和未知费用原样保留。

目前有依据先做 none 决策边界测试，没有依据直接启动 medium 或完整长期科研。
none 若达到 D1，不强制消耗 medium；none 充分信息下仍不行动，才值得做同条件推理强度对照。

## 5. 回归、隐私和剩余问题

- 新预算/上下文加 Harness 验收：8 项通过。原保护语义专测：1 项通过。
- Harness/Provider/S11 扩展组：24 项中 22 项通过；两个旧 S11 夹具因 Mock.lookup 未提供 receipt 而报错。
  用基线 c56 的原 research_context 加载复现相同错误；没有改弱生产恢复检查来让夹具通过。
- Gateway 定向 server/diagnostic/proxy：19 项通过；无外部请求。
- 原 recent-round 工具及恢复回归：9 项通过。检查使用现有研究环境解释器；未安装新依赖。
- Python 编译与 git diff 检查通过。没有科学 Worker、PPO、数学优化或物理评价。

已检查 P4 公共证据 24 个文件：与本机保存 OAuth 私有值及当前 DeepSeek credential 的精确匹配为零；
请求顶层字段不包含认证 headers。此检查不是通用秘密识别器，不把“未命中”夸大为任意私有信息都已排除。
没有改写公开历史，没有修改旧 P4 原始请求/响应；后续完整输入优先留 ignored 本地 Store。
不恢复全量英文字符串扫描，也没有新语言识别器。

已确认的工程问题是预算 off-by-one、重复上下文所有者和动作无关 Schema 分支。
尚未确认的是模型是否在正确窗口下无法形成 Plan，以及外部 403 的具体政策原因。
旧 roles/on-demand 版本仍有冻结恢复调用者，应保留；session_handoff、Reporter 和数值内核不重写。
依然较大的证据 working_set、类型契约和恢复校验未证明可安全删除，不为行数继续重构。
历史脚本沿用 P4 已记录的保留/归档建议，本轮没有批量删除。

## 6. 提交与停止边界

修改覆盖 budget/provider/agent/config/research_context、两个 pending 配置、Gateway 代理启动及只读诊断、
原审计脚本的参数化复用和少量定向测试。session_handoff.py、reporter.py、evidence_policy.py、
Store、任务、FamilySpace 与独立 evaluator 没有生产修改。
工程提交 `344caed2c2ebef16b31b8ad56218f8198e070446` 已成功 push 至
`origin/mainline/research-harness-v2`（远端由 c56bae83e 前进至 344caed2c）。
本文的后续结算提交只补充该发布结果；最终 HEAD 见交付消息及 Git 记录。
不自动启动长期科研或创建实际 P5 Study。
