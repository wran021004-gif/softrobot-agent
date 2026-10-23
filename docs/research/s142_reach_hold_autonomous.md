# S142：Reach/Hold Cold-start 自主结构—控制研究

**同一 Study 已恢复并完成，主 Agent 自主 STOP；本次没有找到完整通过方案。**
真实 Provider 多步研究、两个数学 worker 与两次完整 MuJoCo 反馈已发生。
两次完整执行的位置条件均通过，保持速度均超限；没有追加 Study 或放松验收。

## 身份、冻结与授权

- Study：`s142-reach-hold-coldstart-20261023`。
- 基线：`origin/mainline/softarm-codesign@4de5d5d47`；独立分支
  `research/s142-reach-hold-autonomous`，worktree `.worktrees/s142-reach-hold-autonomous`。
- 配置：[study_reach_hold_coldstart.json](../../configs/research/study_reach_hold_coldstart.json)，
  保留原 robot/task/control/runtime 引用；默认配置、旧 Study、S137–S141 分支未修改。
- 冻结身份：`034d2cac74141856fbe4a8fe051c284d8b608f26e0f32c2e9386da34a0762a4f`。
- 本轮完整用户指令通过原 Store 的 `formal_study_authorization` 记录并绑定新 Study/冻结身份；
  未修改授权检查、伪造审批或复用旧 grant。恢复阶段用户另行明确批准向
  `https://api.deepseek.com/chat/completions` 发送冻结研究参数和真实执行反馈，
  记录为 `provider_egress_authorization`。实际模型为原配置的 `deepseek-flash`。
- 初次 bind 为 `3fd6ff030`，必要修复后使用原 `migrate --reason`，当前科学实施为 `e8abaef72`；
  每次迁移保留冻结配置、旧 Profile、结果、批准及消耗。
- 主进程沿用 `.s135-env`，worker 按冻结 runtime 使用 `.mainline5-env`；
  OPENBLAS/OMP/MKL 线程数均为 1，没有安装或升级依赖。

全新 Store、session 和证据目的地；历史 observation、mathematics、control seeds 均为空。
没有导入历史成功候选、控制参数或轨迹。当前基准结构与原控制默认属于公开工程先验。
S140/S141 未合并，只提供来源核对后的
[S141 模型范围警告](../../configs/research/s142_model_scope.json)，没有给出结构调整方向。
Codex 负责工程与恢复，没有编排 Agent 的科学动作顺序或传入历史成功答案。

## 原任务与合法设计域

沿用 `tasks/reach_hold.json` 和 `offline_reach_hold_v1` 独立组合验收：世界坐标目标
`[0.29, 0.035, 0.19] m`，基座 `[0,0,0.15] m`，零初态，六路理想张力 0–8 N，
35 次控制更新，时域 0.35 s，控制/采样周期 0.01 s，物理步长 0.0005 s。
终点误差 ≤10 mm；保持窗口 [0.30,0.35] s 的 6 个含端点样本要求位置误差 ≤10 mm、
最大末端速度 ≤0.02 m/s。原实际张力、覆盖、完整性与 solver exception 等组合条件全部保留。
控制惩罚与独立验收各自沿用原冻结兼容语义，没有任务迁移或阈值调整。

使用原 source-relative 两段六腱生成器；段长 ±5%、Young 模量 ±15%、列明截面尺寸 ±5%，
两个已注册 NMPC 速度权重 [0.025,0.1]。具体参数和耦合约束以冻结配置为准，
没有新加总长约束、拓扑、腱数或任务接口。控制目录保留 NMPC、Direct PPO 和兼容 Residual PPO。

## 预检与必要工程修复

resolve、源结构生成、初态/张力顺序、控制器准入、真实 GVS/CasADi/MuJoCo、evaluator、
Provider 凭据路径、T1/T2 授权/成本目录、Store/SDK session handoff 通过必要检查。
没有大型物理预检、第二项 Study 或全仓库测试。密钥值和 `.env` 内容未输出、未提交。

仅修复原模块中的实际阻碍：

1. `working_set` 原假定所有候选均有 family-space `resolved_parameters.tendons`；
   改从实际 robot configuration 读取段/腱数，恢复 source-relative prepare/status。
2. 紧凑 `decision_packet` 原无条件读取 `family_space`；按原 start_mode 显示冻结
   reference、allowed parameters 和 length constraint，恢复 source-relative Agent 入口。
3. 中断后原父进程不能发布完成边界：在已有 worker 目录持久化既有 Job 名/启动身份；
   仅可信 Operator SDK 可依据原监督进程清单、精确 pending request 绑定、原 simulation 启动记录和
   原生进程退出核验，提交独立 `recovery_boundary.json`，再由原 recover/receipt 封存不完整结果。
   未增加 Agent/public tool、CLI、调度器、请求体系或第二个 Store。
4. 修正恢复返回的展示字段 `additional_scientific_executions` 为 0；真实账本从未重复计数。

8 项初始定向测试（含 2 项 source-relative 回归）、5 项恢复回归和原 synthetic-worker 集成检查最终通过。
恢复测试覆盖缺证据保持阻塞、错误身份、进程仍存活/权限错误、幂等计数和完整无重启结算。
集成检查最初使用非冻结解释器被原准入拒绝，改用 `.mainline5-env` 后通过，没有放松检查。
没有为历史失败修改哈希或原证据。

## Agent 实际研究与反馈适应

第一项科学决策为基准结构的真实闭环 NMPC，自主竞争假设是“默认控制已足够”与
“直链长度不足，约有 13 mm 几何误差下界”。原计划引用
`ab52e18345db9608254f71e8934c8af8f6fbe24b93c85811b25b7cfc7a944095`。
Agent 将长度算为 0.282 m，遗漏刚性部分；工具模型实际直臂末端为 `[0.298,0,0.15] m`。
原中断执行在 0.31 s 的已保存 pre-step 误差仅 3.045 mm，反驳该下界；这不是完整验收。
这项假设是真实自主提出，但其几何论证错误，不能当成可信数学结果。

同一会话恢复后，Agent 读取已封存的 execution_incomplete 反馈，尝试数学诊断并更改材料。
它先请求 halfway_waypoint 的 T1 task_capability；因缺少已知分析起点时间，原工具返回
`KNOWN_ANALYSIS_START_TIME_REQUIRED / not_applicable`，没有启动数学 worker 或消耗优化额度。
随后自行改用标准初态/预张力，对基准与增刚候选分别执行 trajectory_feasibility。
原等价实验门禁拒绝基准重复；错误 evidence 指针、缺字段、saved-state 和 RLReference 请求均通过
现有反馈交回，由 Agent 更正或放弃，没有 Codex 替它构造控制答案。

Agent 提出两段材料增刚至近 8.280/6.210 MPa（接近 +15%，实际为 8,279,999/6,209,999 Pa），
依据是提高恢复刚度可能改善保持尾段。增刚 MuJoCo 完整执行后，位置通过而保持速度失败。
Agent 实际读取该结果和控制反馈后，转向两段材料下限 6.120/4.590 MPa（−15%），
假设降低达到同一弯曲姿态的张力需求可以改善保持；同时承认变软可能降低稳定频率而恶化速度。
两次改变均保留段长 0.16/0.11 m、截面、腱路和两个速度权重 0.1。
每一结构重新生成实际模型，NMPC 在该结构的实测状态上逐次重新求解，未移植旧通过张力序列。

需独立纠正 Agent 的解释：增刚执行 near_t1 达到 7.922288 N，接近 8 N，尚不能证明饱和致因。
它声称 NMPC 存在 7.8 N planning ceiling，但实际绝对输入约束为 0–8 N；
不能把仿射增量输入余量当成 NMPC 绝对上限。它声称降刚度是“唯一非等价候选”也不成立。
一次失败的 Residual PPO 参数请求不证明所有控制路径不可用，Direct PPO 仍在合法目录内。
这些是 Agent 的科学推断/工具使用局限，没有因此更改生产工具来保证成功。
最终 soft 执行 near_t1 最大值约 6.029 N，保持速度反而升至 0.0520305 m/s，
削弱了其特定“该路接近上限导致失败”的解释；这仍不能将原因唯一归结为控制器。

## 数学证据的实际范围

真正启动 2 个数学 worker；各准备一个当前结构的 GVS 局部仿射模型并执行一次 SLSQP
sampled_trajectory 求解，按原账本各计 1 次数学评价。每次均为 status 9、100/100 次迭代、
success=false、certificate=null、trajectory inconclusive；内部目标/约束评价记录保留。
局部求解预算 local_solves=0 指独立已注册局部控制优化，不表示内部优化器没有运行。

| 候选 | 代理最差保持速度 (m/s) | 最大归一化违反 | 数值结论 |
| --- | --- | --- | --- |
| 基准 | 0.020009547485 | 0.000477374242 | inconclusive |
| 增刚 | 0.020004890885 | 0.000244544260 | inconclusive |

两模型均在直臂标准初态/预张力处构建，不是静态平衡；覆盖 0.35 s 的局部仿射采样约束，
不提供非线性、连续时间或 MuJoCo 保持保证。T1 请求未通过适用性准入，没有 T1 数值见证；
未运行 T2，也没有可靠的结构敏感度/排名证书。SLSQP 未收敛不能推断结构不可行。
代理极小违反不能支持增刚收益；代理张力轨迹也未在 MuJoCo 回放，不能把其速度与独立 NMPC
速度之差直接解释为同一控制的模型误差。

增刚 NMPC 自身的 35 组一阶预测与下一实际采样对齐，最大位置差 4.047 mm、
最大速度向量差 0.119145 m/s；该证据仅覆盖已执行的一步预测，不验证整段未来计划。
没有把 Gramian、静态残差、近似求解或代理改善替代实际验收。

## 真实物理执行与独立验收

| 执行 | 更新 | 终点误差 mm | 保持最大误差 mm | 保持最大速度 m/s | 组合验收 |
| --- | --- | --- | --- | --- | --- |
| 基准，原中断 | 32/35 | 未完成 | 未完成 | 未完成 | execution_incomplete |
| 增刚 | 35/35 | 3.136442 | 3.136442 | 0.022849090 | valid_failure：速度超限 |
| 降刚度 | 35/35 | 2.780838 | 3.031025 | 0.052030494 | valid_failure：速度超限 |

增刚完整执行的其他组合条件通过：实际张力违反 0 N，保持覆盖 6 样本，solver exception 0，
35 个计划可用、0 个优化收敛更新。原 IPOPT Maximum_Iterations_Exceeded 上限 120，
不等于物理不可执行或已经收敛。实际六路张力范围及逐步求解记录完整保留。
增刚均值每更新 94.376 s、仿真 wall 3316.391 s；降刚度为 91.478 s、3210.219 s。
降刚度也通过实际张力、6 样本覆盖和完整性条件，实际张力违反 0 N；34 个计划可用，
0 个优化收敛更新，34 次 Maximum_Iterations_Exceeded，末次 Error_In_Step_Computation，
1 次沿用上一张力响应。注册 solver exception 计数为 0 不表示原优化器没有异常状态。
两次完整执行均为 700 个实际 MuJoCo 物理步，控制更新 35 次；离线执行，实时性不属于本轮验收。
降刚度 34 组可匹配的一步预测最大位置差 3.977 mm、最大速度向量差 0.103636 m/s，
末次缺少已接受预测，未将其补成第 35 组。

## 中断、合法恢复与预算

原进程保存 32 个更新后，终端 session 句柄失效且缺少 worker 完成边界。
最初 recover 正确返回 `UNKNOWN_WORKER_TERMINATION_RETAINS_PENDING_RESERVATION; NO_RELAUNCH`。
后找到原 18:44:11 监督输出，精确绑定主进程 44716/49552 和 worker 125484/126044；
Windows OpenProcess 核验四个原 PID 均已不存在。存活/PID复用/权限不明仍阻塞，不接受为退出。
原 worker 已在 simulation 前安装 kill-on-close Job；事后核验独立封存，不冒充原完成回执。

本地宿主日志显示原服务 19:50:55 后停止记录、物理文件最后写入为 19:50:56.785，
19:52:16 会话在新服务 PID 恢复，Windows 没有重启。这支持宿主退出/更换导致链路中断，
没有原退出码或精确终止时刻，不能断言关闭来源，更不能归因于后来的用户状态询问。
原始 partial、缺失 boundary 与未知退出码保持原样，没有精确 MuJoCo checkpoint，不能从第 33 步续算。

原执行经原 recover 封存为 execution_incomplete，pending/两条 receipt 结算，
Provider 5、物理 1、NMPC 1 保留不变，没有重放任何已计费或未知科学执行。
6592.760 s 为截至退出核验的保守耗时上界，非原进程精确存活时长；计入账本的该值不能
被表述为精确计算时间。原恢复展示字段曾误写新增执行 1，但真实计数未增加，修复后为 0，原输出保留。

恢复启动曾在 CreateProcess 前被自动审批拒绝，没有发送请求/创建进程；
用户随后明确批准目的地和数据范围，经 Store 记录后才恢复原前台 CLI、原 Study 和 SDK 会话。
没有代理客户端、盲目重试、新 request_id 绕过未知请求、后台监控系统或第二个研究。
后续 worker 生命周期及原监督身份清单已持久化，监督按 CPU、原日志与更新进度判断，
没有因为求解较慢停止或重启 worker。

最终原 CLI 正常退出（exit 0），Store 为 `stopped`、pending=null、selected=null，
没有成功 gate 或成功候选。主 Agent 通过原 evidence_read 的紧凑 `/all_fresh_results` 集合读取
并在 STOP 引用全部 5 项新数值结果；原 admission 的 resolved_evidence 精确含 3 个物理结果
和 2 个数学结果。第一次 STOP 缺少证据引用被拒绝，随后自行补齐，未伪造读取标记。
正式停止引用：`3823d4b3d8958008291e9333c7d33794e6984e34425e80f9f3c66665f2b5d5dc`。

| 资源 | 最终消耗 / 上限 |
| --- | --- |
| Provider | 28/36；全部 HTTP 200、完整响应、已结算，未知 0 |
| public operations | 43/160 |
| 物理启动 | 3/8；1 个不完整、2 个完整独立评价 |
| NMPC | 3/3；原中断也占额度 |
| 数学评价 / 独立 local_solves | 2/40、0/8 |
| PPO 阶段 / actions | 0/2、0/8192；每阶段上限 4096 |
| RL 独立评价 / 成功后确认 | 0/1、0/0 |

Provider 6 次、public operations 16 次收尾保留均包含在总上限中；剩余不是新授权。
所有 Provider reservation 与科学 receipt 均已封存，occupied={}，没有未决 worker/请求。
账本 wall_s=13835.482415 包含原 orphan 的 6592.760 s 保守上界，不能解读为精确总计算时间。
两次完成的 simulation 分别按原 receipt 实耗结算；Store numerical_s 与总账本范围不同，保留原值。

停止依据是两次真实保持速度失败、NMPC 额度耗尽、代理模型不足和 Agent 对剩余 PPO 路径的
成本/工具使用判断；不是所有资源耗尽。剩余物理 5、数学 38、Provider 8、PPO 全额未用。
Agent 声称“剩余方法不能再取得验收”超过证据：Direct PPO 仍获授权，Residual PPO 的
reference 构造也没有证明不可解决。它从两个材料样本推断“刚度方向单调”亦非普遍规律。
合法结论是该 Agent 选择停止、本轮未找到解；不能宣称任务/设计域/所有控制方法不可行。
尚未解决保持速度超限的来源、迭代受限求解与模型/物理误差的贡献，以及控制优化的改进空间。
没有据此追加预算、再跑一项 Study 或替 Agent 实施下一科学动作。

## 证据与结论分离

完整原始记录保留在 Git 忽略的 `runs/research/s142-reach-hold-coldstart-20261023`。
原中断 21 份文件约 66 MB 的字节归档 manifest 为
`6c199a9c842c4a7d6c571a9219d52435b7e11d1b7a67aa2195616878cf24d9cc`。
原 `export/`、恢复后的 `export_reconciled/` 均保留，不覆盖旧快照；
最终用原 core.export 导出至同 Store 下 `export_final/`，完整 artifact、calls 和 snapshot 在本地可追溯。
没有声称存在公开原始归档。
Git 只保存本报告、配置、必要修复/少量测试与
[可追溯小摘要](../../evidence/s142_reach_hold_autonomous/summary.json)，没有凭据、完整响应、轨迹或大矩阵。
摘要在原 Store 另存最终监督结论引用，历史摘要和原失败全部保留。

| 结论 | 当前证据 |
| --- | --- |
| 工程链路 | 曾有真实宿主中断，最小修复后同 Study 恢复、完成反馈及正式收尾；不是全程无故障 |
| 主 Agent 自主决策 | 真实多步 Provider 决策、假设、工具自纠及从增刚转降刚度已观察 |
| 数学工具 | 适用性门禁正确；两个真实但未收敛的局部诊断，无 T1/T2 证书或可靠排名 |
| 物理任务成功 | 未建立；两次完整执行均只在保持速度上失败 |
| 结构修改额外收益 | 尚未建立；没有完整基准对照，不能隔离纯结构因果效应 |

没有鲁棒性、重复性、连续时间、实时性、硬件或全局最优结论。
本轮最终最佳完整候选为增刚方案，速度仍超限约 14.245%；未选为成功解。
降刚度终点误差略低，但保持速度约为增刚的 2.277 倍，不能当成总体收益。
没有运行第二个 Study、额外确认或修改验收条件。
配置提交 `b08d1724b`，source-relative 修复 `3fd6ff030` / `c3aeacbf4`，恢复修复
`19066a785` / `e8abaef72`，均普通 push 至指定 S142 分支。最终报告/摘要由本报告所在提交交付并普通 push；
收尾只改这两份文件，不再改变科学实施绑定。最终工作树状态与远端一致，main/科研主线未修改。
