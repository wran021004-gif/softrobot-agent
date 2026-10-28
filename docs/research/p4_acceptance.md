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

实时请求与 L1–L4 结果将在完成后追加；当前尚未声称自主科研通过。
