# S142：Reach/Hold Cold-start 自主研究

**当前：原 orphan 阻塞已解除，等待明确 Provider 外发批准后继续同一 Study；尚无完整任务验收。**

以下原中断结论保留为历史阶段事实，最新恢复见文末。
真实 Provider 自主选择并启动了一次 NMPC/MuJoCo 实验，保存了 32/35 个控制更新。
随后原终端句柄失效，监督查询未发现原主进程或 worker，执行目录没有完成边界和结果。
原 `recover` 明确返回
`UNKNOWN_WORKER_TERMINATION_RETAINS_PENDING_RESERVATION; NO_RELAUNCH`。
没有重跑、第二个 Study、预算重置、人工通过或伪造 Agent STOP。
中断的具体原因未确定，不能把时间上相邻的状态询问归因为中断原因。

## 身份、冻结与授权

- Study：`s142-reach-hold-coldstart-20261023`。
- 基线：`origin/mainline/softarm-codesign@4de5d5d47`；独立分支
  `research/s142-reach-hold-autonomous`，worktree `.worktrees/s142-reach-hold-autonomous`。
- 配置：[study_reach_hold_coldstart.json](../../configs/research/study_reach_hold_coldstart.json)。
  原 robot/task/control/runtime 引用保持；默认 Study 和旧 Study 未修改。
- 冻结配置身份：`034d2cac74141856fbe4a8fe051c284d8b608f26e0f32c2e9386da34a0762a4f`。
- 正式批准为本次用户 2026-10-23 S142 完整指令，经既有 Store 的
  `formal_study_authorization` 真实记录，绑定本次 Study 和上述冻结身份；未复用旧 grant。
  批准引用、实施提交、候选与待结算执行见 [summary.json](../../evidence/s142_reach_hold_autonomous/summary.json)。
- 首次 bind 为 `3fd6ff03`；之后仅修复决策包，通过原 `migrate --reason` 迁移至
  `c3aeacbf4`，冻结配置、批准、Profile 和计数均保留。
- 实际主进程使用既有 `.s135-env`；物理 worker 按冻结 runtime 使用 `.mainline5-env`。
  三个数值线程环境变量均为 1，未安装或升级依赖。

Cold-start 使用全新 Store、会话和证据目的地。历史 observation、mathematics、control seeds
均为空，没有导入历史通过候选或轨迹。原两段六腱物理结构与控制默认是公开工程先验，
不是随机无先验初始化。S140/S141 未合并；只提供来源明确的
[S141 模型范围警告](../../configs/research/s142_model_scope.json)，不指定参数调整方向。
该警告被保存为 scoped context；不把配置中“提供”误称为 Agent 已完整阅读。

## 原任务与合法设计域

沿用 `tasks/reach_hold.json` 和原独立 evaluator/组合验收：目标为世界坐标
`[0.29, 0.035, 0.19] m`，零初态，0–8 N 理想张力，35 次控制更新，
时域 0.35 s、控制/采样周期 0.01 s、物理步长 0.0005 s。
终点误差 ≤10 mm，最后 0.05 s 保持误差 ≤10 mm、最大末端速度 ≤0.02 m/s。
未修改历史保持语义、张力顺序或组合验收，控制惩罚不改变验收条件。

复用 source-relative 两段六腱生成器；可变段长、Young 模量、已列截面尺寸及
两个已注册 NMPC 速度权重，具体范围由冻结配置的 `allowed_parameters` 唯一给定。
未额外要求总长固定，未扩大拓扑或腱数。可选控制为原注册 NMPC、Direct/兼容 Residual PPO；
没有新建 Agent、Store、工具注册、CLI 或恢复框架。

## 最小工程预检及修复

配置 resolve、生成器和控制器准入、独立任务条件、Provider 凭据读取和既有数学依赖通过。
实际发送前已核对目的地为 `https://api.deepseek.com/chat/completions`，模型 `deepseek-flash`；
决策包不含实际密钥值，不注入仓库源码或 `.env` 内容。最初真实启动被自动审批拒绝，
理由为目的地和可能敏感的请求内容未具体列明；在完成上述离线来源核对后，原命令获准启动。
首次拒绝发生在 CreateProcess 之前，没有发送请求或启动科学 worker。

只修改两处已有生产接口：

1. `working_set` 错把 family-space 的 `resolved_parameters.tendons` 视为所有候选必填，
   导致 prepare 已保存后打印状态失败。改为从实际 robot configuration 读取柔性段/腱数量。
   同一 Store 随后 status 成功；此时尚未 bind，也无科学执行。
2. 紧凑 `decision_packet` 无条件读取 `family_space`，离线复现会阻挡 source-relative Study。
   改为按既有 start_mode 显示 family-space 或原冻结 reference/allowed parameters/length constraint。
   未新增解析器或第二份任务视图；提交后明确迁移原 Study。

共 8 项不同的定向测试最终通过，包括 2 项新增回归；未跑全仓库测试或大型物理预检。
新增决策包测试的 fixture 初次缺少 Profile version 和 Registry，补全 fixture 后通过；
没有改变历史哈希、原证据或准入使测试表面通过。

## Agent 的真实决策

5 次真实 Provider 请求均返回 HTTP 200，原始请求、响应及处理记录完整保存，
没有未知 Provider 发送或未消费响应。8 项原生工具请求中，7 项有返回；最后一项科学工具
仍待原执行结算。公共操作账本为 9，按原账本记录，不能用请求条数替代。

Agent 先读取候选与方法视图，自行提出竞争假设并选择当前基准结构的闭环 NMPC：
默认控制可能满足任务；另一种解释是其估算的基座相对距离超过直链长度，
形成约 13 mm 的几何误差下界。它希望用真实终点、保持位置/速度和数值反馈区分两者。
这是 Agent 自主提出的物理诊断，不是 Codex 指定的实验顺序，也不是 T1 见证。
首个获准科学计划的原始引用：
`ab52e18345db9608254f71e8934c8af8f6fbe24b93c85811b25b7cfc7a944095`。

最初有两次 evidence 指针错误和一次缺失 selected_candidate 的计划错误；
既有错误反馈正常返回，Agent 自行更正后获准执行，没有科学预算绕过。
Codex 未给它下一结构方向或历史成功参数。

本轮没有调用 T1/T2、其他数学 worker、局部求解或 PPO。
方法授权/依赖/成本目录可读，T2 初始明确缺少匹配模型 stencil；
单/双步长从零准备示例分别需要 8–11 / 14–19 次数学内部评价，不能视作一次优化。
“已授权且能显示成本”不证明本轮数学工具被正确用于科学推断。

## 实际物理证据与验收边界

唯一执行 owner 为 `s142-reach-hold-coldstart-20261023-exec-ab2e3bebfda74387`，
simulation execution ID 为 `83167c03af65492e8b3c1b56758c7aa5`。
实际 MuJoCo XML、编译物理配置、控制配置及逐更新记录均已生成。
候选保持原结构，没有结构修改；NMPC 在当前候选实测状态上逐次重新求解。

保存了 32/35 个完整控制更新记录，最后记录为 0.31 s 的 pre-step 观测，已进入保持窗口。
32 份计划全部可用、solver exception 为 0；32 次 raw status 均为
`Maximum_Iterations_Exceeded`，上限 120，不能称为优化收敛。
已记录命令范围为 0.131801–7.726616 N；这不是完整独立实际张力验收。
这些完整更新的 wall-time 合计 4038.868 s，不包含未完成求解和全部执行开销。

| 冻结独立验收项 | 完整结果 |
| --- | --- |
| 终点误差 ≤10 mm | 未测得完整结果 |
| 保持最大位置误差 ≤10 mm | 未测得完整保持窗口 |
| 保持最大速度 ≤0.02 m/s | 未测得完整保持窗口 |
| 实际张力、数值完整性及组合验收 | 未生成完整独立评价 |

部分 0.31 s 实测位置距目标为 3.045 mm，已与 Agent 声称的约 13 mm 几何下界不符。
这说明其未验证的几何下界假设不成立；该点不是终点，也不能替代完整保持验收。
本轮没有 T1/T2 数值预测与真实任务结果可比较。
主 Agent 未收到这次完整物理工具返回，因此没有证据证明它根据物理反馈改变结构、控制或路线。
没有额外结构收益、全局最优、鲁棒性、重复性、实时或硬件结论。

## 中断、恢复与预算

监督初期曾确认原进程和 worker 存活、CPU 时间增长，并持续读取原目录更新记录；
没有因慢求解而重启。状态询问后的检查发现原终端 session 句柄失效，
提权 Win32_Process 查询未找到匹配 Study 的原进程，原目录也没有 `boundary.json` 或 `result.json`。
没有可靠证据确定中断原因或精确终止时刻；进程查询为空不能替代原 worker-tree 的持久终止确认。

同一 Study 的 status 成功；recover 按原安全门禁拒绝恢复，没有新请求或重放。
原研究操作和 `complete-simulation` 两条 receipt 未封存，pending 和预算均保留。
Store 正式 `research_status` 仍为 `ready` 且 pending 非空；监督结论记录为工程阻塞，
没有伪造 Agent STOP，也没有手工清空状态、伪造 boundary 或修改冻结身份。
剩余额度不代表当前可以继续调度；迁移/新执行仍受该未决边界阻挡。

| 资源 | 实际计数 / 上限 |
| --- | --- |
| Provider | 5/36，6 次收尾保留包含在总额内 |
| 公共操作 | 9/160，16 次收尾保留包含在总额内 |
| 物理启动 | 1/8；完整独立评价 0 |
| NMPC 执行启动 | 1/3；完整更新 32/35 |
| 数学内部评价 / 局部求解 | 0/40、0/8 |
| PPO 阶段 / actions | 0/2、0/8192；每阶段上限 4096 |
| RL 独立评价 / 成功后确认 | 0/1、0/0 |

公共账本已计 1 次 backend 启动，未释放或重置。simulation receipt 未封存，
因此账本已结算 wall_s 43.001 s 和 state numerical_s 不能代表真实全部计算耗时；
部分更新时间与未结算资源另行保留，不能宣称只消耗了约 43 秒。

## 证据、结论分离与交付

[可追溯摘要](../../evidence/s142_reach_hold_autonomous/summary.json) 保留身份、原始引用、
Provider 状态、两条未封存操作、预算及部分记录统计；没有完整 Provider 内容或轨迹数组。
原 Store 为 `runs/research/s142-reach-hold-coldstart-20261023`。
21 份现场文件的原始字节（约 66 MB）已通过原 Store.put 保存，manifest 为
`6c199a9c842c4a7d6c571a9219d52435b7e11d1b7a67aa2195616878cf24d9cc`。
使用原 `core.export` 的 destination 参数导出至该 Store 下的 `export/`，
保留 snapshot、调用、原始 artifact 及未结算状态；全部原始包位于 Git 忽略的 runs，
没有声称存在公开原始归档。

| 要评价的结论 | 本轮证据 |
| --- | --- |
| 工程链路正常 | 部分准备和真实执行正常；端到端收尾/恢复阻塞 |
| 主 Agent 自主决策 | 已观察真实多步读取、假设、更正与自主 NMPC 选择 |
| 数学工具正确科学使用 | 未使用，无法评价 |
| 物理任务成功 | 未建立；不完整执行，不属于已独立验收的科学失败或通过 |
| 根据完整物理反馈继续研究 | 未观察，工具返回前中断 |
| 结构修改带来额外收益 | 无结构修改，无收益证据 |

本轮自主研究的最终验收条件尚未满足：有真实 Provider 和真实部分 MuJoCo 执行，
但缺少完整独立反馈及其后的 Agent 决策。合法停止点是工程阻塞，不是科学任务不可行。
后续首先需要原终止边界/receipt 的可验证恢复依据；不能从零 prepare 或重跑完整实验填补证据。
本轮不扩大框架，也不追加第二项 Study 追求成功。

配置提交为 `b08d1724b`；实际必要修复为 `3fd6ff030`、`c3aeacbf4`，均普通 push 至指定 S142 分支。
最终文档/摘要由本报告所在提交交付。未修改 main、科研主线、S137–S141 或旧 Study，未 force push。

## 同一 Study 恢复修复（2026-10-23 20:32 后）

用户追加要求查清阻塞并恢复本次真实验证。进一步找到原 18:44:11 的监督工具输出，
包含原主进程 44716/49552、worker launcher 125484 及实际 worker 126044 与本次 request.json
的精确命令行；该原始输出已保存进原 Store，未凭记忆填写 PID。
Windows OpenProcess 对这四个原 PID 均返回 ERROR_INVALID_PARAMETER (87)，即当前不存在；
权限错误和 PID 仍存活/复用都不会被接受为退出。原 worker 在进入 complete-simulation 前
已经安装 kill-on-close Job，因此确认实际 worker 退出可确认其受控子树不再继续科学执行。

本地 Codex 日志显示原服务 PID 49904 的最后记录为 19:50:55，原物理更新最后写入为
19:50:56.785；19:52:16 会话在新服务 PID 784840 中恢复，Windows 没有在该时段重启。
这支持终端宿主链路更换/退出的解释；没有原退出码，不能进一步断言关闭来源。
缺口是原父进程退出后无法写完成边界，而不是 Provider 未确认发送或数学不可行。

最小修复保留原 recover/Store/receipt：增加仅可信 Operator SDK 可调用的 orphan 结算入口，
要求原 worker 命令与当前 pending request 绑定、原 simulation 确已启动且未封存、
原监督中所有进程经原生句柄核验已退出。缺身份、存活、PID 复用、权限不足仍保留阻塞。
新 `recovery_boundary.json` 明确为事后监督确认，原 `boundary.json` 保持缺失；退出码仍未知，
wall-time 按截至核验时的保守上界计入并明确标注，不伪造精确退出时刻。
后续 worker 启动在既有目录持久化已有 Job 名和启动 PID，未新增调度器或 ID 系统。

5 项新增定向回归通过，含完整 recover 封存路径、无重启、无计数重置和幂等核验。
原 synthetic-worker 集成测试在冻结 `.mainline5-env` 下通过；最初用 `.s135-env` 被原解释器
一致性检查拒绝，未放松该检查。旧执行只能恢复为 execution_incomplete；没有完整 MuJoCo
状态 checkpoint，不能从第 33 步原位续算。恢复后下一科学动作仍交由主 Agent 在原额度内选择。

恢复结果：原 32/35 实验现已合法封存为 `execution_incomplete`，引用
`364634c4cf1726a9854ddb13bd237482b6e1be337683fbbf59d5297a4b5d4794`。
原科学工具与 simulation receipt 均已结算，pending 清除，原始边界仍缺失且退出码未知；
事后核验依据保存在独立 recovery boundary，不冒充原 worker 的完成回执。
计数仍为 Provider 5、物理 1、NMPC 1，没有新科学启动。6592.760 s 是截至退出核验时的
保守耗时上界，非原进程精确存活时长。首次恢复返回中的旧展示字段误写
`additional_scientific_executions=1`；真实计数与账本没有增加，现修正为恢复路径返回 0，
新增回归断言通过；原首次返回记录保留，不能以该展示字段宣称又启动一次实验。


恢复交付状态：原 pending 和两条未封存 receipt 已合法结算，Provider 5/36、物理 1/8、NMPC 1/3
保持不变；实施已迁移至 `e8abaef72`。这不代表补齐了原物理轨迹或获得任务验收。
原 SDK 会话尚未消费恢复后的工具结果，下一模型请求尚未发送。

尝试恢复时，后台脱离终端启动被自动审批拒绝；重新核对约 43 KB 的待发送决策包，
确认不含密钥值或源码注入后，原前台 CLI（完整调用边界暂停）仍在 CreateProcess 前被拒绝。
审查认为用户未明确点名批准向 `https://api.deepseek.com/chat/completions` 发送这些冻结研究参数
和真实执行反馈。因此没有改用其他客户端或绕过审批，没有后台进程、新 Provider 请求或 worker。
当前剩余阻塞是外发批准，不再是原 worker 未知终止；待明确批准后可使用原 run-id 继续，
不需要 prepare 新 Study。新摘要和 `export_reconciled/` 保留已结算状态；旧导出不覆盖。
