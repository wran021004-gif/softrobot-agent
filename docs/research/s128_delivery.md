# S12.8 准备与冻结交付状态

2026-10-21。**已准备新的 Cold-start 配置与高 PPO 上限，正式科研等待本 Study 独立授权。**
尚未发送真实 Provider 请求、启动正式数学/NMPC/PPO/物理实验或取得任务通过结果。
这是一份准备阶段交付，不是科研完成报告。

P0 已提交：`3848db8eb992a207dffe8c93ad8c8f6f00755013`。
正式源码冻结：`988acfe3339dc4a55b6a46df7349ed98783ae4ee`，冻结时本地和远端完全一致。
324 个源文件 hash 已封存。后继提交只归档冻结证据和本文，不更改冻结源码。
新 Store 与持久化后独立重开的 SDK 均无科研历史/消息；0 候选、0 实验、0 Provider、0 PPO 动作、
0 未结 receipt、0 pending。原任务尚未验收。

具体冻结条件、资源、资料范围、会话准入和运行规则见 [S12.8 协议](s128_protocol.md)。
起点为 `096488569644d8bdd9b2907486585adec563b41e`，目标分支和工作树不变；
未更改原任务、科学评价器、历史 Study 配置或 sealed archives。

新 Study `s128-cold-live-20261021` 使用空初始科研状态和新的本地 Store/SDK/Provider 账本。
预算为 128 请求（内含 12 protected）、400 公共操作（内含 24 protected）、80 共享物理启动、
8 数学、各 4 NLP/BDF/NMPC、8 PPO 阶段、4,194,304 总动作、1,048,576 单阶段上限、
12 RL 独立评价 episodes。全部是上限，不规定方法顺序或最低使用量。
新 runtime 为 deepseek-flash / thinking high / max_tokens 131072，保留原 count-mode 与 1M 容量保护。

MATLAB R2024a/SoRoSim 工程 readiness 已通过；Direct PPO 环境在独立 RL Python 中构造成功：
48 DOF、4 张力动作、107 维观测、35 控制区间、0.0005 s 物理步长。
checkpoint 发布/验证、continuation 和独立评价入口可导入；没有训练或 rollout。
磁盘构造检查时约 800 GB 可用，实际版本及容量保存在 `evidence/s128_preflight/rl_environment.json`。
大训练实际耗时、磁盘增长及任务通过率尚未测量。

高额度测试经过真实 dispatch、候选/任务/实现准入、动作配置、共享物理与独立评价事务预留，
只在 worker 调用边界拦截：4 个 1,048,576 动作阶段全部准入，第五阶段因总动作上限被拒绝。
另测 8 个 524,288 动作阶段、阶段超限、单次超限、评价预留和预算保护。
合成 fixture 的预留不是实际训练消耗，正式 Store 不包含这些阶段。

原生连续 Strands 启动请求的真实序列化路径经合成 HTTP 验证可容纳 131072 输出；
每次真实请求仍须重新检查增长后的输入。精确字节、framing 和限制见
`evidence/s128_preflight/startup_capacity.json`，不能将这些字节或合成 usage 当作实际 tokens。

P0 最小恢复一致性修复完成：首次核对交接初始消息和提交信息；已有完整回合时核对 Store
保存的最新完整消息身份，允许正常增长；未完成工具回合保留原恢复机制。
启动时验证在 recover_feedback 和 live_started 写入之前，不一致拒绝不改 Store、不新增消耗。
不新增签名、数据库或逐条验签。正常增长、JSON 内容不一致及原崩溃恢复回归通过。
S12.7.6 真实旧/新 SDK 已在新进程只读重开，原 7/4 段 reasoning、工具 ID 和反馈保持一致。
结果见 `p0_consistency.json` 和 `p0_live_reopen.json`；所有旧封存文件保持原样。
完整生产轮换尚未单独准入，按已验证的连续 session 路径推进 S12.8，不扩展新的大规模 Harness 实验。

生产修改净增 59 行，其中独立授权保护 18 行、P0 恢复一致性与启动顺序修复净增 41 行；
工具字段和指针反馈无需改动既有合同，本轮以新指令和回归验证准确拒绝。
54 个不同测试通过，包含既有 14 个进程中断子场景；一个旧 hook fixture
更新后单独复测通过，原失败日志保留。没有扩大科研框架。
回归结果见 `evidence/s128_preflight/regression.json`。

冻结提交、冻结时远端 SHA、全部科学/核心及配置源文件 hash、环境和预算见
`evidence/s128_preflight/freeze.json`。本地空状态见 `cold_start.json`，
只读审计见 `evidence/s128_acceptance/status.json`，实际成本见 `evidence/s128_costs/counts.json`。
完整原始 Store/SDK/Provider 文件与 export 留在本地 `runs/`，不上传 GitHub。

独立授权的完整机器可读范围见 `evidence/s128_preflight/provider_scope.json`。
人工审阅范围见 [S12.8 独立授权范围](s128_authorization_scope.md)。
目前没有 S12.8 正式批准记录；账户可用模型/余额检查、正式运行、原始 MuJoCo 验收重建、
SELECT/STOP 与最终科研结论均待批准后进行。未找到解与尚未运行是不同状态；本轮当前是后者。
