# S12.8 Cold-start 正式研究冻结协议

2026-10-21，分支 `feat/sorosim-matlab-nmpc`，工作树
`D:\softrobot-agent\.worktrees\sorosim-matlab-nmpc`。
起点和重新 fetch 后远端：`096488569644d8bdd9b2907486585adec563b41e`。

当前只授权准备、离线验证、工程 readiness、冻结和普通 commit/push。
**首次真实 Provider 请求或正式科学 worker 之前，必须另获本 Study 的明确批准。**
本协议不是批准记录，也不沿用 S12.7.6 A/B 的余额或许可。

## 冻结对象

- Study：`s128-cold-live-20261021`，配置 `configs/research/study_s128_cold.json`。
- Runtime：`configs/research/runtime_s128.json`。
- 原任务：`tasks/reach_hold_mirror_v1.json`，继承原 `reach_hold.json`。
- 原 FamilySpace、defaults 和 `control_sorosim_s56_braking.json` 作为声明的设计先验。
- Store：`runs/research/s128-cold-live-20261021`，SDK session ID 同 Study ID。
- `evidence/s128_preflight/freeze.json` 记录实际代码 SHA、冻结时远端 SHA、配置身份、
  science/core hashes，以及全部受跟踪 tools/extensions/schemas/tasks/matlab/configs/tests 源文件 hash。

保留目标 `[0.29,-0.035,0.19] m`、原零初始化语义、0.35 s 时域、0.01 s 控制周期、
0.0005 s 物理步长、终点和保持位置误差均不超过 0.01 m、保持速度不超过 0.02 m/s。
原输入张力、数值有效性、覆盖、完整执行和独立评价器要求全部保留。
数学结果、PPO reward、checkpoint 存在或优化器收敛均不建立任务通过。

`history`、`mathematics`、`control_seeds`、`supplied_evidence` 均为空。
正式 Store 启动前不含候选、实验、控制种子、历史数学或旧聊天。
工程构造/合成测试全部在不同 ID 的独立 Store，不导入正式研究。

## 固定资源上限

| 资源 | 总上限 | 总量内部保护 |
|---|---:|---:|
| Provider 请求 | 128 | 12 |
| 公共操作 | 400 | 24 |
| 共享物理启动 | 80 | PPO 阶段评价另在其中预留 |
| 数学分析 | 8 | — |
| 离线 NLP / BDF / NMPC | 各 4 | — |
| PPO 阶段 | 8 | start 与 continuation 共用 |
| PPO 总动作 | 4,194,304 | — |
| 单阶段 PPO 动作 | 1,048,576 | — |
| RL 独立评价 episode | 12 | 包含阶段预留评价 |

所有数值是上限，不要求耗尽或使用任何指定方法。保留 count-mode，无科学时间上限，
无静默逐步时间停止。动作按 `n_steps` 对齐，默认 256，每阶段至少两个完整 rollout。
Agent 可以自主申请更小额度。训练、续训和独立评价共用 80 次物理启动；
每个新阶段在同一事务预留一次独立评价机会，不能把训练动作误计成物理启动次数。
4,194,304 个完整控制动作对应最多约 83,886,080 个训练积分步，未包含独立评价。
已分配额度、真实 attempted/completed actions、未结 reservation、未知消耗分别报告。
续训必须绑定正确父 run、已发布 checkpoint、配置/策略 hash 和兼容性；恢复原阶段不新增阶段额度。

## Provider、上下文与资料范围

端点 `https://api.deepseek.com`；`deepseek-flash`，thinking enabled，reasoning effort high，
单次输出最多 131072 tokens，128 次请求总上限。没有重试或额外辅助模型调用额度。

2026-10-21 核对 [Chat Completions API](https://api-docs.deepseek.com/api/create-chat-completion/)、
[模型资料](https://api-docs.deepseek.com/quick_start/pricing/)及
[thinking 文档](https://api-docs.deepseek.com/guides/thinking_mode/)；文档支持这些参数。
账户模型权限、余额和本次实际响应尚未访问，须在正式批准后、首发前确认。
账户检查不增加 128 次 chat-completion 上限；不以账户检查代替科研请求。

可传输新 Study 的任务、FamilySpace、生成结构、控制、工具 Schema、合法科学证据，
以及此后真实工具历史和完整 reasoning/tool IDs/results。不得传输凭据、无关私人文件、
旧 Study 聊天或已测实验答案。
准确机器可读范围和身份见 `evidence/s128_preflight/provider_scope.json`。

保留 1,000,000 token context guard。每个实际发送的序列化 UTF-8 输入字节数，加
131072 最大输出与 8192 framing headroom，不得超过该上限。这是保守容量估计，
不是 tokenizer 测量；实际 tokens 只取 Provider usage。
保留完整原始 HTTP、reasoning、工具配对和 receipt，保留分层工作集、按需读取和工具结果 Offload。
不删除 reasoning、截断旧历史、清空 Store 或创建新 Study 绕过容量限制。

## 会话准入

新研究从独立、零消息 Strands session 开始。P0 最小一致性修复已完成：首次恢复核对
Store 的 initial_messages、已提交快照文件信息、会话/交接指针、Schema 和证据引用；
已有完整科研回合后，改用同 session 最新 `model_original_turn.sdk_message_identity`
核对完整消息，正常增长不再要求等于初始消息或文件 hash。
未完成工具回合和已保存待消费响应继续走原 receipt/feedback 恢复，不当作干净轮换边界。
启动时先做恢复一致性检查，再恢复工具反馈及写入 live_started；不一致拒绝不修改 Store 或消耗预算。
没有签名、第二套数据库、逐条验签或新 SessionManager。

回归覆盖正常增长、可解析 JSON 的内容不一致、未提交完整回合、两次 handoff 后重启，
以及原 14 个进程中断场景和真实科学 receipt 的离线反馈恢复。
S12.7.6 真实旧/新 SDK 也在新进程只读重开，7/4 段原 reasoning、工具配对、Store 和 SDK 文件均保持一致。
详见 `evidence/s128_preflight/p0_consistency.json` 与 `p0_live_reopen.json`。

生产轮换准入与最小一致性检查分开：本轮未验证完整生产工具组合下所有中断后继续研究的路径，
不手工置 production opt-in。此前发现的内容不一致问题已修复，门禁关闭不代替本修复。

因此不手工设置 `session_handoff_live_admitted`，不启用 `--session-handoff`。
使用原连续 Strands 路径，逐请求执行容量保护。容量不足必须保留状态并准确报告，
不能热改冻结源码或静默清除历史。辅助会话功能不阻塞本轮核心科研。

## 实施范围与验证

沿用 Plan、ResearchDecision、ControlSeedRequest、GenerationRequestV2、AnalysisRequest、
EvidenceQuery、动态 Schema、严格引用及原 `error_feedback()`。
新 Study 指令明确必填顶层 hypothesis、decision.hypothesis_id、generation 归属、
raw_reference 样本指针、大 PPO 动作额度和逐项约束反馈。
测试证明漏字段、额外字段、错误包装指针均被拒绝并可修复，不需要放宽生产合同。

生产代码增加最小 SDK 恢复一致性修复，以及 opt-in 正式授权门禁：`PENDING_EXPLICIT_APPROVAL:` 配置必须有本地 Store
中绑定同一 resolved identity/Study 的独立批准记录；在读取凭据、Provider 调用及科学准入前拒绝。
旧 Study 的授权语义不变。没有新增 Agent、Planner、Store 或求解器。

预检仅进行依赖检查、MATLAB 工程探针、RL 环境构造、真实高额度启动准入至 worker
调用边界拦截、checkpoint/续训/评价入口及既有 fixture 回归。没有真实 PPO 训练或机器人 rollout。
MATLAB sandbox 启动的编码失败保存在本地；获准在 host 环境重新探针后 ready。
工程 gateway 的小型 fmincon 自测不是机器人科研结果。

## 执行、异常和公开交付

准备和冻结入口：

```powershell
python -m tests.research.s128_preflight --environment
python -m tests.research.s128_preflight --prepare
# commit、普通 push 并核对 SHA 后，仅执行一次：
python -m tests.research.s128_audit --freeze
python -m tests.research.s128_audit
```

实际用户批准后，本地批准 JSON 需包含 stage=`S12.8`、study_id、scope_identity、
freeze_source_commit 和准确 user_approval；用 `s128_audit --record-approval <local-file>` 入账。
然后复用 `python -m tools.research run --run-id s128-cold-live-20261021`。
不在未获批准时创建虚构批准记录或运行该命令。

研究方法、结构和控制变量由 DeepSeek Research Agent 自主选择，Codex 只监督运行、
账本、worker、恢复及证据。首个完整原任务通过后停止探索，读准确验收证据并由 Agent SELECT。
STOP 必须引用全部新实验结果，不虚构不可行性，不强迫耗尽预算。
异常按原恢复流程处理，不重发已确认请求，不重复启动未结 worker，不热修复冻结实现。

所有原始 HTTP、SDK、Store、checkpoint 和科学数组留在忽略的 `runs/`。
默认完整 export 也在该本地目录；GitHub 只提交代码、配置、派生统计、必要证据引用和公开报告。
`s128_audit` 只输出派生审计；已有验收重建工具在实际结果产生后复用，
当前零实验状态不能称为 SELECT、STOP 或科学成功。本轮不自动进入 S12.9/S13。
