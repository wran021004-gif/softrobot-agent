# P6.3 R3：短连接监控与受控 Reporter 恢复

基线为 `d8a9c8a48a7f89169f57c1d335222736fe4d0c27`，独立分支
`codex/p6-3r3-safe-monitor-recovery`。已从 GitHub Git-data 原始元数据重建并验证
准确提交对象与父链，未用相同 tree 的其他提交冒充基线。

唯一原 Study 为 p63v1-m3-autonomous-feasibility-sol-20261030。准备时保持 32/80、
155 数学评价、3 轮搜索、Profile v3、独立 Replay/SELECT 0，原 unknown 请求和
科学冻结 b0f0faa 不变。用户本轮明确授权研究 Reporter-only 的本地工程放弃路径；
原响应仍不能恢复，不将本地处置描述成 Provider 取消或执行失败。

## 监控连接生命周期

原 p63r_live_audit 入口改为短观察，不再 runpy 嵌套全文审计。新 p63r3_monitor
每个 SELECT 使用 mode=ro、query_only=ON 和 contextlib.closing；fetchall 返回后
立即关闭连接，Python JSON 解析、分组、输出和等待均发生在关闭之后。没有显式
长事务，没有在运行期复制全文审计或 ZIP。观察是多个短读取，不冒充原子科学证书。
历史 p63v1_audit 的每次取数也显式关闭连接，去掉模块级 db/BEGIN；重审计仍只在
隔离副本或运行结束后使用。没有改 Store 数据库类型、数值算法或科研准入。

隔离并发回归使用独立监控进程，重复 5 轮 Reporter 与 Main Mock Provider 归档
（10 次虚构 Provider）、确定性 Reporter 保存和下一次 decision_packet 读取。
原响应 bytes 逐字核对、回执全部封口、无 database is locked；监控退出后可获得
BEGIN EXCLUSIVE；监控参数错误单独退出，不影响科研写入。2 项定向测试通过，
真实 Provider 和科学 Worker 均为 0，详见 p63r3_monitor_validation.json。

## 受控恢复进度

原计划先完成整个 Store/SDK 隔离链路。用户随后明确要求“现在不需要测试了直接接续原来study，我需要快速验证”，因此中断该全链探针，直接接续原 Study。17 项定向测试已经通过；不将中断的全链探针描述为通过，也不声称取得了它尚未发出的 Mock Main wire。

已实现 operator-only 的 abandon_unrecoverable_reporter_attempt，不注册为 Main 工具，
不自动调用。要求精确 Study/请求的本次用户授权、唯一 unknown Reporter、原响应缺失、
确定性基础报告、已封口科学结果、无活 Worker、无未消费响应、匹配原 science_delivery
边界的已配对 SDK 快照，且该未知调用是最后一次发送。事务中再次核对状态和唯一未封口
调用，通过原 Store.complete 以 cancelled 终结本地 reservation，保留 model_calls=1。
不创建 r3_response、HTTP 状态或解释文本；provider_outcome 仍 unknown，tokens/money
为未知。本地放弃事件和 receipt 输出精确保留授权、原 wire/base report 和范围声明。
重复执行只返回已存在的处置；Main 或其他 unknown 仍由原 pending 机制阻断。

17 项不同的相关离线测试已通过，覆盖并发监控、8 类恢复准入/反例、原 5 项证据门槛
以及两种 Mock 终局；后者明确检查 SELECT 写入 selected_solution 后自动 stopped，
失败 SELECT 被拒绝后由 Mock Main 使用完整索引合法 STOP。没有修改正式阈值或准入。
完整输入、关键断言、日志和结果见 p63r3_targeted_validation.json。

真实操作前备份已保存为 P63-R3-before-recovery.zip；逐字节核对当前 SQLite 与原归档
一致、全部 30 个 SDK 文件一致，freeze/profile/spec 一致。SHA-256、原 DB SHA 和原始
路径见 p63r3_pre_recovery_backup.json。这项备份在真实写入前完成。后续真实操作依据用户明确的新指令执行，实际逐项保持检查见 p63r3_final_checks.json。

## 同一原 Study 的真实接续与终局

原 Study ID 仍为 `p63v1-m3-autonomous-feasibility-sol-20261030`；原数据库路径不变，没有从归档另建 Study。科研运行冻结为 `70d7ca8f53e062ed084d5bbd9db4d58808ca5120`。
原请求32的响应没有恢复；通过显式授权函数终结本地 reservation，upstream outcome 继续 unknown。原一次 model_calls 计账保留，未退款、未重发、未补造 response/HTTP/interpretation。未知 tokens、金额和上游耗时仍为未知。
真实接续新增 10 次 Provider 请求，从32增至42/80；新增数学结果 0 项。终态 `stopped`；独立 physical_replay 2 项，其中原评价器通过 1 项；selected 为 `True`；最终原计划动作 `select`。
最终原计划和 selected_solution 以原 Store 为准。只有实际独立评价及原准入可建立正式通过；Mock SELECT/STOP 只证明接口能力，不能计作真实成果。

恢复时逐项核对任务、预算、155项原数学结果、费用、候选、控制、三轮搜索、Profile v3和科学代码哈希均保持。之后科研选择完全由 Main 提交，没有 Operator 提交 Replay、SELECT 或 STOP。
恢复后33、34两次实际调用均来自既有 complete_reports 的未完成报告队列，priority 为 new_numerically_incomplete_result，非 Main 主动调查，且非请求32的重试；两次响应均已归档。
本地上下文准备存在先遍历全部数学结果再裁剪、后续关系构建再次读取的开销。此阶段没有新科研 Worker，不是模型推理时间。随后用户明确要求提前选取最佳结果、关键失败和引用再按需加载。修复已提交3d2e71d，并通过原bind接续，完整历史保留；首次真实新决策包104.047s，对照此前749.993s约快7.2倍。未修改科学算法、评价器或准入。三个定向检查通过，一个旧B3检查因缺少C3归档未能建立fixture；完整修复后性能探针按用户快速继续指令中断，没有冒充通过。

### 简单选择接口与用户要求的重新决策

用户随后明确要求回到参数错误前让 Main 重新选择，并将 Replay、SELECT/CONFIRM、诊断、执行及控制相关 Plan 的对象引用改成简单选项。源码70d7ca8已实现：原始模型输入与确定性展开计划分别归档；Replay 的候选/控制/数学结果来自同一保存结果，SELECT/CONFIRM 的候选/证据来自同一评估结果。原验收、正式读取、身份和预算门槛不变。7项定向检查通过，含真实SDK/MockSELECT；没有重新开展完整科研探针。
这次重新决策是用户显式干预，不是完全无人工干预的连续自主科研。只重开原Main已选的Replay工具入口；原失败复验、全部历史和费用保留，不回滚科学状态或计数。实际请求40在真实wire中收到result_151达标、result_155未达标两个绑定选项，直接选择result_151，没有填任何哈希。
原先的失败来自Main37把未达标候选35e470及其控制531e1d与另一个候选的证据b73818混配；结果视图已有数学未达标提示。Reporter38在复验之后明确报告了有效执行但任务失败。Main36最初正确的4f813/d2e5e/d2c908配对只因额外顶层字段被拒绝，当时Worker未启动；不能把后续失败误记成这条正确配对的物理失败。
修复后原Main40独立选择result_151，物理复验e605a25d通过原评价器：terminal/holding_position=0.009881022088480991m，holding_speed=0.01955035395638464m/s，force_bound_violation=0，solver_errors=0；不是Operator代提交的Replay。正式SELECT是否完成仍以终局原Store为准。

### Main 的实际新动作

- `physical_replay`：The current-profile executable candidate, replayed with its candidate-bound optimized schedule from the stronger saved native result, will satisfy every frozen M3 Reach/Hold constraint in an independent full-task physical evaluation.；原始计划引用 `0ba644948fe5bb91aaeefd52c3dc8b289b1bdc8fcf574fff610e78bc65e5e104`。
- `physical_replay`：The current-profile executable candidate-control pair bound to saved result_151 will satisfy every frozen M3 Reach/Hold constraint in an independent full-task physical replay. This is preferred over result_155 because result_151 is a complete native finite-budget pass on all three constraints, whereas result_155 already failed the same independent protocol.；原始计划引用 `5d56305771ad8787640f2caf60bcfe9cc6d9ae60dc1d618caea12eb2996b808b`。
- `select`：The exact candidate-control pair represented by evaluation_2911 is a legal executable solution satisfying every frozen M3 Reach/Hold constraint in independent full-task physical evaluation.；原始计划引用 `5b037aa5b840f03f168653775aaea5ec1f336437c0fc7ee702ccf59b4561742d`。

### 真实请求与工具轨迹

| 请求 | 角色 | HTTP | 工具调用 |
| --- | --- | --- | --- |
| 33 | reporter | 200 |  |
| 34 | reporter | 200 |  |
| 35 | conversation | 200 | research_route:physical_replay(success) |
| 36 | conversation | 200 | research_plan:physical_replay(error) |
| 37 | conversation | 200 | research_plan:physical_replay(success) |
| 38 | reporter | 200 |  |
| 39 | conversation | 200 | research_route:search(success) |
| 40 | conversation | 200 | research_plan:physical_replay(success) |
| 41 | conversation | 200 | evidence_read(success) |
| 42 | conversation | 200 | research_plan:select(success) |

### 原始结果交付与费用边界

实际新 Main 请求 7 次；完整事实卡片、Profile兼容性、控制source、三项指标阈值、搜索scope、引用资格及工具轨迹逐条保存在 P63-R3-audit.json。实际最大Provider输入 203406 bytes，原限制为1MiB。
全部已保存响应报告的 usage 合计：`{"prompt_tokens": 580053, "completion_tokens": 17437, "total_tokens": 597490, "reasoning_tokens": 0}`。这只覆盖已报告的token；请求32缺失量未知，不能将其视为0。金额未提供，因此金额未知。
原Store数值费用累计 numerical_s=7135.322584300127，construction_numerical_s=76.89217760012252，control_initialization_s=43.13034969998989。Worker/kernel等费用口径可能重叠，不再次相加。
数学结果状态：`{"computed": 137, "execution_incomplete": 18}`；详细费用缺失条数 18，缺失仍记未知。

一致性审计所有断言通过，包含原155项及费用前缀、候选/控制/搜索/任务/预算/科学哈希、Provider总数与账本一致、32仅一次计账且无响应伪造、输入限制、Worker终止证据。其完整结果见 p63r3_final_checks.json。
