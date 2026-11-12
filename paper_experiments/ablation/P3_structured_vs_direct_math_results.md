# P3 C2：Full-Selective 与 Direct-Math-Tools 实际结果

**状态：Direct 已完成并封存；Full 于用户明确要求下人工停止。该配对实验未完整完成。** 本报告记录截至停止时的全部已观测结果，不能把 Full 的人工中止解释为预算耗尽、正常 Main STOP、设计空间无解或架构劣势。

## 1. 版本、执行条件与停止状态

| 项目 | Direct-Math-Tools | Full-Selective |
|---|---|---|
| Study ID | p3-direct-math-tools-20261112 | p3-full-selective-20261112 |
| 配置 | configs/research/study_p3_direct_math_tools_v1.json | configs/research/study_p3_full_selective_v2.json |
| 首次真实 Provider 请求 | 2026-11-12T14:39:42.735+08:00 | 2026-11-12T17:21:40.155+08:00 |
| 结束时间 | 2026-11-12T17:09:05.931+08:00 | 2026-11-12T20:27:26.489+08:00（人工终止进程） |
| 实际处置 | 本轮 numerical_success；Main STOP | stopped_by_user；没有执行 Main STOP |
| Store 原始状态 | stopped | ready；保留 prepared handoff，不改写为正常完成 |
| 预算耗尽 | 否 | 否；停止时 Provider 41/200 |
| 最终认证 | UNKNOWN / 未 SELECT | UNKNOWN / 未 SELECT |

运行使用固定 Core 4e5a25dd6a418b71892df29e9fd61a477de37790，固定 Research 3b652ef0fb3e6e6237848e815b3244b6f28abc37。Core checkout 提供实际 tools.research；Research checkout 提供配置与 evidence home。报告提交发生在实验停止之后，不改变实际运行版本。未修改 Core、研究配置、Knowledge、TaskDefinition、FamilySpace、物理模型或数学算法。

两个 Study 由同一监督进程串行运行。Direct 在 Full 创建前已停止、导出并核实无相关进程；Full 从空 Store、空候选池开始，未向其 Main 注入 Direct 的结果。原配置比对见 [匹配条件记录](../../evidence/p3-c2-supervision-20261112/matched-conditions-pre-full.json)。

两组冻结条件相同：GPT-5.6 Sol、medium、account3 Gateway；相同 46 条/18 ID Knowledge；相同研究动作选择指导；相同普通物理搜索通路 v1 mixed search → passive_task_response → evaluate_physical → passive Replay adapter。普通响应不计主动数学评价；数学内部积分计入共享物理硬预算。

独立硬预算均为 Provider 200（含 protected 4）、数学评价 100、物理预留/启动上限 150、公共操作 800；每次 FamilySearch proposals≤24、evaluations≤16，无预算转移或扩展。

任务为原始双方向、五阶段，每方向 20 s，dt=0.000125 s，最终 2 cells/segment。每个完整双方向响应有 320,000 个积分步。Low≥0.006 m、High≤0.025 m、恢复残差≤0.002 m、刚度比≥1.5；Middle 保留原定义。位移评价点为材料坐标 s=0.7；Low/High/Recovery 表中使用冻结评价器的窗口聚合值，Middle 为保存的机制观测量，不用平均双方向替代原始值。

**实际网格差异：** Direct 的 12 个已完成响应均为最终 2 cells/segment。Full 前 3 个显式候选实际为 12 cells/segment，其资格通过只对该执行网格成立；后 4 个 FamilySearch 响应为 2 cells/segment。Full 数学内部模型亦核实为每段 2 cells（8 个弯曲关节）。这项执行轨迹差异必须保留，前三个探索不能充作最终网格成功证据。

Full 停止时最后动作是第 41 次 Provider 请求加载 stop 路由，并非执行 STOP 计划；在 session_handoff prepared 状态收到用户“停止”，随后终止 PID 35016/9984。无待处理 Provider、无未封收据、无待完成科学计算，且两组均无 Main/Reporter/Worker 残留。原 Store 状态及历史事件未改写；见 [人工停止记录](../../evidence/p3-c2-supervision-20261112/full-user-stop.json)。

## 2. 最终设计与原始双方向指标

Direct 的最佳候选为 Main 最终选择的 candidate_890，完整候选 artifact fab6d270725293b6a8399a519b13fda3f107f5b7d7f08d0beb44dcd6d4b0b0e0，结果 d24723d8d5fbc571d9b956b51a7355c462fe67190e3e8e345abd089d65f545f9。

Full 没有 Main 最终选择，也没有满足本轮条件的候选。下表仅采用最后完成 FamilySearch 自己保留的最终网格 incumbent（候选 dc537fe1a3e51b7cc764bdb1ae2d02300a8c3b9e30c1eaedc08bf23c1e001349，结果 1d6a1392ed0fdb6b33fe25fc912d5fb2a69eafd0fe08d92c76aee818e87bd9e1），作为可追溯的暂定比较对象；不是监督者新选的成功设计。

| 指标 | Full +x（暂定） | Full −x（暂定） | Direct +x | Direct −x | 阈值 |
|---|---|---|---|---|---|
| Low / m | 0.005211374882916884 | 0.005211374882916923 | 0.006434294529517387 | 0.006434294529517423 | ≥0.006 |
| Middle / m | 0.010414313335040925 | 0.010414313335041258 | 0.011514265064608445 | 0.011514265064608228 | 记录原值 |
| High / m | 0.02069610779973922 | 0.020696107799738413 | 0.018006507015642586 | 0.018006507015642433 | ≤0.025 |
| Recovery residual / m | 1.0743638504848492e-11 | 3.0214836911443973e-12 | 2.5987215043059833e-06 | 2.5987215042644503e-06 | ≤0.002 |
| Progressive stiffness ratio | 1.012068169615294 | 1.0120681696154796 | 1.5649356796636293 | 1.564935679663559 | ≥1.5 |
| Slack-to-taut | 0.0 | 0.0 | 1.0 | 1.0 | 1 |

| 项目 | Full 暂定最终网格对象 | Direct 最佳 |
|---|---|---|
| Contact 最大数量 | 0.0 | 0.0 |
| 实际 constraints / initial qualification / execution / solver / sampling / stages | 均 PASS | 均 PASS |
| 双方向 10 个阶段资格窗口 | 10/10 PASS | 10/10 PASS |
| 核心四指标 | FAIL | PASS |
| 本轮完整数值成功 | 未观测到 | PASS |
| 原始 evaluator validity | incomplete | incomplete |
| 原始 acceptance | UNKNOWN | UNKNOWN |
| 正式 SELECT / 独立证书 | 未获得 | 未获得 |

设计摘要：Direct 为 2×0.12 m，圆截面半径 0.008 m，Young 4.6 MPa，密度 1000 kg/m³，双轴物理黏性 0.0007 N·m²·s，四根 whole-chain 腱，路由半径 0.018 m，四个 payout offset 均为 0.0012 m。Full 暂定对象为 2×0.1 m，圆半径 0.0056 m，Young 7 MPa，密度 1100 kg/m³，黏性 0.0004 N·m²·s，四根 whole-chain 腱，路由半径 0.018 m，payout offset 均为 0。完整生成参数与配置来源 hash 保存在公开汇总及本地 Store。

### 物理资格窗口

下表保留双方向全部五阶段。每窗口 2001 个样本、采样周期 0.000125 s；静力平衡绝对阈值 1e−5 N·m、tip/monitor speed 阈值 0.001 m/s、长度超限阈值 5e−5 m。原绝对资格阈值是判定依据；归一化静力平衡仅为诊断，校准仍标为 incomplete。

| 对象 | 方向 | 阶段 | 窗口 / s | Static balance / N·m | Tip speed / m/s | Monitor speed / m/s | Length excess / m | 资格 |
|---|---|---|---|---|---|---|---|---|
| Full 暂定 | plus_x | unloaded | [3.75, 4.0] | 5.971343648636171e-18 | 3.2688410545519735e-19 | 3.5380360285915163e-19 | 0.0 | PASS |
| Full 暂定 | plus_x | low | [7.75, 8.0] | 1.0099126396267977e-14 | 5.97661697141465e-14 | 8.624181855648011e-14 | 1.0041523812454045e-07 | PASS |
| Full 暂定 | plus_x | middle | [11.75, 12.0] | 1.0839419639641079e-14 | 1.8005242115952523e-13 | 1.49862140451835e-13 | 2.0012881765674173e-07 | PASS |
| Full 暂定 | plus_x | high | [15.75, 16.0] | 3.4991107233928176e-14 | 1.2884854507764237e-13 | 1.035087054232525e-13 | 3.9681223851228964e-07 | PASS |
| Full 暂定 | plus_x | recovery | [19.75, 20.0] | 1.2161605044906401e-09 | 6.698774270868054e-08 | 9.798143082873364e-08 | 4.1843695175458606e-11 | PASS |
| Full 暂定 | minus_x | unloaded | [3.75, 4.0] | 5.971343648636171e-18 | 3.2688410545519735e-19 | 3.5380360285915163e-19 | 0.0 | PASS |
| Full 暂定 | minus_x | low | [7.75, 8.0] | 8.629381931246627e-15 | 3.749158335276968e-14 | 5.703703478101416e-14 | 1.004152380690293e-07 | PASS |
| Full 暂定 | minus_x | middle | [11.75, 12.0] | 7.81232717406155e-15 | 6.13412375230344e-14 | 8.641756011337873e-14 | 2.0012881765674173e-07 | PASS |
| Full 暂定 | minus_x | high | [15.75, 16.0] | 9.270362255620057e-15 | 6.00119226676469e-14 | 7.69434674142933e-14 | 3.96812238095956e-07 | PASS |
| Full 暂定 | minus_x | recovery | [19.75, 20.0] | 6.286514251294549e-10 | 3.473363039623204e-08 | 4.6444355773590174e-08 | 2.2446988712232496e-11 | PASS |
| Direct | plus_x | unloaded | [3.75, 4.0] | 1.8330547271891132e-17 | 1.5791996515555092e-19 | 1.8429480557822387e-19 | 0.0 | PASS |
| Direct | plus_x | low | [7.75, 8.0] | 2.9593653780783484e-06 | 5.33134697720673e-05 | 4.982638823961161e-05 | 0.0 | PASS |
| Direct | plus_x | middle | [11.75, 12.0] | 1.9064177320116116e-14 | 1.1230204079888205e-13 | 1.1275719364955435e-13 | 2.3798311210576628e-08 | PASS |
| Direct | plus_x | high | [15.75, 16.0] | 6.7465130704214e-14 | 2.8935995175296037e-13 | 3.0567267741981245e-13 | 1.3602465315232237e-07 | PASS |
| Direct | plus_x | recovery | [19.75, 20.0] | 8.736009556481822e-06 | 0.00016213383181067756 | 0.00015152598423902485 | 0.0 | PASS |
| Direct | minus_x | unloaded | [3.75, 4.0] | 1.8330547271891132e-17 | 1.5791996515555092e-19 | 1.8429480557822387e-19 | 0.0 | PASS |
| Direct | minus_x | low | [7.75, 8.0] | 2.9593653780961293e-06 | 5.331346977204602e-05 | 4.982638823959162e-05 | 0.0 | PASS |
| Direct | minus_x | middle | [11.75, 12.0] | 1.837050477015989e-14 | 8.816893799040854e-14 | 1.1483941863591058e-13 | 2.379831126608778e-08 | PASS |
| Direct | minus_x | high | [15.75, 16.0] | 7.113233613242897e-14 | 3.3056570764976895e-13 | 3.0913502208926057e-13 | 1.3602465315232237e-07 | PASS |
| Direct | minus_x | recovery | [19.75, 20.0] | 8.736009556492605e-06 | 0.00016213383181069225 | 0.0001515259842390388 | 0.0 | PASS |

Direct 最终恢复阶段静力平衡最大约 8.73601e−6 N·m，仍低于原阈值；因此不能把先前核心通过但恢复资格失败的候选当作成功。腱的其他方向性通道允许保持松弛；所需 slack-to-taut 判定由冻结评价器的实际张力、活动集与长度残差联合给出，不能把“所有腱均张紧”作为替代条件。

### 实际任务违反量

| 对象 | 原约束 | 观测值 | 界限 | Signed violation（正为违反） | 状态 |
|---|---|---|---|---|---|
| Full 暂定 | plus_x_low_minimum | 0.005211374882916884 | 0.006 | 0.000788625117083116 | FAIL |
| Full 暂定 | plus_x_high_maximum | 0.02069610779973922 | 0.025 | -0.00430389220026078 | PASS |
| Full 暂定 | plus_x_residual_maximum | 1.0743638504848492e-11 | 0.002 | -0.0019999999892563614 | PASS |
| Full 暂定 | minus_x_low_minimum | 0.005211374882916923 | 0.006 | 0.000788625117083077 | FAIL |
| Full 暂定 | minus_x_high_maximum | 0.020696107799738413 | 0.025 | -0.004303892200261589 | PASS |
| Full 暂定 | minus_x_residual_maximum | 3.0214836911443973e-12 | 0.002 | -0.0019999999969785164 | PASS |
| Full 暂定 | plus_x_stiffness_ratio | 1.012068169615294 | 1.5 | 0.487931830384706 | FAIL |
| Full 暂定 | plus_x_slack_to_taut | 0.0 | 1 | 1.0 | FAIL |
| Full 暂定 | plus_x_paired_mechanism | UNKNOWN | 1 | UNKNOWN | UNKNOWN |
| Full 暂定 | minus_x_stiffness_ratio | 1.0120681696154796 | 1.5 | 0.48793183038452037 | FAIL |
| Full 暂定 | minus_x_slack_to_taut | 0.0 | 1 | 1.0 | FAIL |
| Full 暂定 | minus_x_paired_mechanism | UNKNOWN | 1 | UNKNOWN | UNKNOWN |
| Full 暂定 | no_contact | 0.0 | 0 | 0.0 | PASS |
| Direct | plus_x_low_minimum | 0.006434294529517387 | 0.006 | -0.00043429452951738653 | PASS |
| Direct | plus_x_high_maximum | 0.018006507015642586 | 0.025 | -0.0069934929843574155 | PASS |
| Direct | plus_x_residual_maximum | 2.5987215043059833e-06 | 0.002 | -0.001997401278495694 | PASS |
| Direct | minus_x_low_minimum | 0.006434294529517423 | 0.006 | -0.00043429452951742296 | PASS |
| Direct | minus_x_high_maximum | 0.018006507015642433 | 0.025 | -0.006993492984357568 | PASS |
| Direct | minus_x_residual_maximum | 2.5987215042644503e-06 | 0.002 | -0.001997401278495736 | PASS |
| Direct | plus_x_stiffness_ratio | 1.5649356796636293 | 1.5 | -0.06493567966362934 | PASS |
| Direct | plus_x_slack_to_taut | 1.0 | 1 | 0.0 | PASS |
| Direct | plus_x_paired_mechanism | UNKNOWN | 1 | UNKNOWN | UNKNOWN |
| Direct | minus_x_stiffness_ratio | 1.564935679663559 | 1.5 | -0.06493567966355895 | PASS |
| Direct | minus_x_slack_to_taut | 1.0 | 1 | 0.0 | PASS |
| Direct | minus_x_paired_mechanism | UNKNOWN | 1 | UNKNOWN | UNKNOWN |
| Direct | no_contact | 0.0 | 0 | 0.0 | PASS |

paired mechanism 与独立 numerical confirmation 在原评价器中仍缺失，因此原始 accepted 为 null、validity 为 incomplete。用户本轮明确豁免这两项及半步长、扰动、成功后重复、独立 Replay 证书和正式 SELECT；Direct 的本轮数值成功依据完整双方向物理资格、最终网格、核心阈值、实际腱约束、招募转变及无接触，不改写原评价器的 UNKNOWN，也不等同正式任务认证。

## 3. 实际科研成本

| 指标 | Full（截至人工停止） | Direct（完成） |
|---|---|---|
| Provider requests | 41 | 47 |
| Main / Reporter | 33 / 8 | 35 / 12 |
| Input tokens 总量 | UNKNOWN（40/41 收据已知部分 2,269,168） | 2,324,609 |
| Output tokens 总量 | UNKNOWN（已知部分 31,741） | 39,845 |
| Reasoning tokens（包含在 output 内） | UNKNOWN（已知部分 12,573） | 14,578 |
| Cached input（input 的子集） | UNKNOWN（已知部分 63,232） | 147,456 |
| Provider cost | UNKNOWN | UNKNOWN |
| 数学评价：账本扣记 | 9 | 0 |
| 数学评价：实际 attempts | 8 | 0 |
| 结构化数学接口调用 | 2（一次规模不足，一次执行） | 0 |
| Direct API 调用 | 0 | 0 |
| 物理预留/扣记 | 32 | 24 |
| 普通物理 Episode started / completed | 14 / 14 | 24 / 24 |
| 数学内部 Episode started / completed | 16 / 16 | 0 / 0 |
| 实际总 Episode started / completed | 30 / 30 | 24 / 24 |
| 普通 physics steps | 2,240,000 | 3,840,000 |
| 数学内部 physics steps | 2,560,000 | 0 |
| 实际总 physics steps | 4,800,000 | 3,840,000 |
| 公共操作 | 39 | 39 |
| 收据 cache-hit | 0 | 0 |
| Wall-clock：首次 Provider→结束 | 3:05:46 | 2:29:23 |
| Ledger wall_s（不同口径） | 7233.812936400005 | 5212.603187700013 |

Full 一次 Reporter 请求 HTTP 502，receipt 的 usage/money 缺失，故总 token 与费用为 UNKNOWN，不以零补齐或估算；其余 40 次收据的 token 仅列已知部分。Direct 47 次均有用量，费用仍无来源。Full 9 次数学评价预算扣记对应 8 次实际取点；18 个数学物理预留对应 16 个实际 Episode。未人工退还、补算或重置预算。普通物理求解器内部的 KKT、QP、雅可比或平衡计算不等于主动数学 API 调用。

## 4. 收敛与候选生成路径

| 里程碑 | Full | Direct |
|---|---|---|
| 首次核心四指标通过 | 未出现 | 响应 #10 / 2fc5f602644c5b1f；2026-11-12T16:34:12.731+08:00；Provider/public/physical=38/32/20 |
| 首次最终网格完整物理资格通过 | 响应 #4 / dc537fe1a3e51b7c；2026-11-12T18:31:24.156+08:00；Provider/public/physical=27/26/8 | 响应 #1 / 119d49e404b2f75d；2026-11-12T14:49:07.862+08:00；Provider/public/physical=8/9/2 |
| 首次最终网格资格＋本轮数值成功 | 未出现 | 响应 #12 / fab6d270725293b6；2026-11-12T16:57:27.915+08:00；Provider/public/physical=44/36/24 |
| Main 最终 STOP | 未执行；#41 仅加载 stop 路由，随后用户停止 | #47 |
| 终止原因 | 用户停止，右删失 | Main 正常数值停止 |

Full 首个执行网格上的阶段资格通过发生于响应 #1（Provider 10、public 9、physical 2），但该候选为 12 cells/segment；最终网格资格里程碑必须采用 #4，不能把两者混同。

下表轨迹使用双方向最差值：Low 最小、High 最大、Residual 最大、ratio 最小；完整双方向未经舍弃地保存在公开汇总。P/O/L 为当时 Provider、公共操作、物理账本扣记。

| Study | 响应 # | 候选 artifact 前缀 | 每段 cells | Low / mm | High / mm | Residual / mm | Ratio | 执行网格资格 | 本轮成功 | P/O/L |
|---|---|---|---|---|---|---|---|---|---|---|
| Full | 1 | 480df1f146f59fbb | 12/12 | 3.55193145 | 14.3336807 | 1.39521934e-10 | 0.9938352791 | PASS | FAIL | 10/9/2 |
| Full | 2 | 0eaf8e4eef999abe | 12/12 | 6.88024529 | 24.3868842 | 8.43832425e-06 | 1.006557345 | PASS | FAIL | 16/17/4 |
| Full | 3 | ff09f5cdae4a2f3f | 12/12 | 6.8833483 | 24.3897653 | 8.46588053e-06 | 1.006560923 | PASS | FAIL | 21/20/6 |
| Full | 4 | dc537fe1a3e51b7c | 2/2 | 5.21137488 | 20.6961078 | 1.07436385e-08 | 1.01206817 | PASS | FAIL | 27/26/8 |
| Full | 5 | 32543fb6a94004bf | 2/2 | 5.21137488 | 20.6961078 | 8.88576812e-09 | 1.01206817 | PASS | FAIL | 27/26/10 |
| Full | 6 | 75bfcdce738d8bb4 | 2/2 | 5.21137488 | 20.6961078 | 4.14204049e-12 | 1.01206817 | PASS | FAIL | 27/26/12 |
| Full | 7 | e5bbd8d7452ac885 | 2/2 | 5.31101801 | 22.2783982 | 1.07785869e-08 | 0.9602010026 | PASS | FAIL | 27/26/14 |
| Direct | 1 | 119d49e404b2f75d | 2/2 | 1.42451728 | 5.70182982 | 8.89703993e-09 | 0.999709406 | PASS | FAIL | 8/9/2 |
| Direct | 2 | 8e79181f93e18577 | 2/2/2 | 4.07402094 | 16.3172973 | 0.00416455222 | 0.9996551157 | FAIL | FAIL | 8/9/4 |
| Direct | 3 | 56278fd58272d41c | 2/2 | 1.42526062 | 5.71169516 | 3.18764366e-09 | 0.9984834267 | PASS | FAIL | 8/9/6 |
| Direct | 4 | 7011733f7190ce7b | 2/2 | 1.424517 | 5.70182958 | 8.12676192e-09 | 0.9997094059 | FAIL | FAIL | 8/9/8 |
| Direct | 5 | ceffd833ceeb2f0d | 2/2 | 8.45086856 | 23.5405826 | 0.0384319235 | 1.010835387 | FAIL | FAIL | 17/17/10 |
| Direct | 6 | 6e8dfe2d0ba0cd35 | 2/2 | 7.6659225 | 21.361651 | 0.0243868996 | 1.217179387 | FAIL | FAIL | 21/20/12 |
| Direct | 7 | dd39ec614ca8f52e | 2/2 | 6.94647469 | 19.2696531 | 0.0183332436 | 1.328706716 | FAIL | FAIL | 24/22/14 |
| Direct | 8 | bdfcdc080df40f5f | 2/2 | 7.21999434 | 20.4067065 | 0.107788814 | 1.37760839 | FAIL | FAIL | 28/25/16 |
| Direct | 9 | 31406ca956c000e4 | 2/2 | 6.65818847 | 18.7313514 | 0.054175365 | 1.493238615 | FAIL | FAIL | 33/28/18 |
| Direct | 10 | 2fc5f602644c5b1f | 2/2 | 6.55471976 | 18.4888423 | 0.00543518462 | 1.519116432 | FAIL | FAIL | 38/32/20 |
| Direct | 11 | e8cc9fb3d5b7140b | 2/2 | 6.61624182 | 18.4610368 | 0.000141146659 | 1.517629196 | FAIL | FAIL | 41/34/22 |
| Direct | 12 | fab6d270725293b6 | 2/2 | 6.43429453 | 18.006507 | 0.0025987215 | 1.56493568 | PASS | PASS | 44/36/24 |

Direct：初始过大搜索被合同拒绝，四段默认结构又因完整装配长度不合法失败；随后共同的直接物理搜索评价 4 个拓扑/路由方案。Main 根据真实响应转为显式父候选参数变更与普通 Replay，调整长度、模量、payout，再处理密度/黏性与恢复资格。#9 ratio≈1.4932386，严格不四舍五入为通过；#10/#11 核心通过但恢复静力资格失败，仍继续至 #12 完整通过后 STOP。12 个完整响应保留，未在核心刚通过时提前跳过资格。

Full：前三个显式生成候选采用 12-cell 网格；从默认结构改为较小截面与较大路由半径，再把 payout 从 0.0005 m 增至 0.0005015 m。响应几乎不变，仍无 slack-to-taut。之后 Main 自主选择 final_evaluation FamilySearch，约束 section/routing/payout 的边界，6 次提案中 2 次因重复/裁剪跳过，4 个结构完成直接物理响应。没有核心通过。该搜索摘要 evaluated_designs 字段为 0，原始字段保留；实际完成数依据四份响应和 Episode 收据，不用该字段替代实际成本。

数学结果不可比较后，Main 转回搜索，但后续申请 24、20 次评价等超出每次 16 次上限，未获准启动 Worker。之后读取当前任务与 working_set；一项视图不匹配的读取失败。最后加载 stop 路由，用户随即要求停止。监督者未替 Main 指定参数、修改候选、给出临时提示或改写 Reporter 结论。

| 原始工具错误/拒绝代码 | Full 次数 | Direct 次数 |
|---|---|---|
| EVIDENCE_VIEW_MISMATCH | 1 | 0 |
| MECHANISM_QUESTION_BUDGET_CANNOT_FIT | 1 | 0 |
| SEARCH_OUTSIDE_FROZEN_NUMERICAL_SCOPE_OR_COUNT_CAP | 6 | 4 |
| TOOL_SCHEMA_ADDITIONALPROPERTIES | 1 | 0 |
| TOOL_SCHEMA_REQUIRED | 0 | 1 |

上述计数按实际工具反馈中的 error_code 或不足预算 reason 统计；Reporter HTTP 502 单列为 Provider 失败。计划 Schema 错误、导航错误、数学预算拒绝和数值有效性不足是不同类别，不能全部称作“数学计算错误”。

## 5. 数学研究组织与证据质量

| 结构化操作 | Full 实际接口尝试 | 数值执行 |
|---|---|---|
| inspect | 0 | 0 |
| differentiate | 0 | 0 |
| optimize | 2 | 1 次运行，8 个取点 |
| compare | 0 | 0 |
| interact | 0 | 0 |

Full 先以 diagnose 计划提出“低载荷已张紧，是否存在可用招募边界”的机制判别问题，后实际提交 scientific_question_v4 的有限时间 task_violation optimize：两条路径 payout_offsets_m.tendon_1、tendon_3，界限各 [0.0005015,0.0015] m，两方向、原冻结任务、最终网格、无主动控制。第一次 cap=8，小于编译所需最少 9，被返回 MECHANISM_QUESTION_BUDGET_CANNOT_FIT，未开始科学执行；Main 随后明确改为 cap=9。

该运行 8 个取点全部 MEASUREMENTS_MISSING，Low/High/Recovery 的数学目标观测为 UNKNOWN；因此 derivative_status=not_defined、candidate_improvement_status=not_comparable，best_valid_record_index=null、observed_reduction=null，sensitivities 为空。顶层 computed、工具传输 success 和 scoped diagnostic 声明不等于有效导数或候选改善。积分确实完成，成本确实发生，但不能据其推出可行方向、有效双参数交互、局部不可行或机制因果结论。具体测量缺失的根因本轮未修改代码排查修复。

数学结果与候选、模型、任务、执行条件及原始 records 有绑定；结果 artifact 0cf77fe5d7c91deca30e921cde1d843234c5061be334a8cc752e85381b4a5e2c。模型按 final_evaluation 执行，但源候选最初来自 12-cell 探索；既有 12-cell 性能不能直接移作最终网格基线。Main 收到不可比较结果后转向 search，表明结果影响了路径选择；没有证据显示获得了有效数学方向并据此改善参数。未重复执行同一已完成数学问题。

| Direct 底层 API | 实际调用次数 |
|---|---|
| model_evaluate | 0 |
| stencil | 0 |
| matched_points | 0 |
| finite_difference | 0 |
| minimize | 0 |
| interaction_evidence | 0 |
| observe | 0 |
| observed_task_improvement | 0 |
| subtract | 0 |
| minimum | 0 |
| maximum | 0 |

Direct 未调用 research_math_api。因而本次没有实际自行组装数值数学问题、双参数交互或 API 调用顺序可供评价；参数/观测组合错误、调用顺序正确性、重复数学计算及结果解释能力均为未测试，而非“零错误所以能力已证实”。Direct 的数值成功来自 Main 组织普通物理实验，不能归因于底层数学 API。两组共享的物理数值内核本身也不代表两组都实际使用了主动数学能力。

### Knowledge 与工具暴露：许可、收到、阅读、采用分开

| 证据层级 | Direct | Full |
|---|---|---|
| 配置许可 | Direct APIs 开启；高层关闭 | 五种高层操作开启；Direct API 关闭 |
| 初始工具暴露 | research_route 目录允许 research_math_api；按需完整 Schema 未被选择 | 初始按需；完成 diagnose 后 Provider #24 实际收到 research_analysis Schema |
| 动作选择指导 | 实际 Main 系统提示收到 @1 全文 | 实际 Main 系统提示收到相同 @1 全文 |
| Main 主动 Knowledge 检索 | 0 | 0 |
| Reporter 主动 Knowledge 检索 | 8 | 6 |
| 采用与因果影响 | 观察到响应驱动的实验调整，不能仅凭注入证明 Knowledge 因果作用 | 有诊断计划、数学失败后转路等行为；不能仅凭注入/检索证明因果作用 |

两组注入的 FROZEN_MAIN_RESEARCH_GUIDANCE 解析后 JSON 完全相同（3378 字符），共同条目 research-action-selection-and-stopping@1 body SHA-256 为 3246c581c536d53b18ae6f44aee6a3d2349234c7ce085f6e60c4fd71f6454b98。Direct 另有与实验能力条件对应的附加指令，不把这段附加说明误当共同指导不一致。

截至停止，Full 的 6 次 Knowledge 读取全部属于 Reporter，涉及 validation-replay@1/@2、validation-qualification@1/@2 及 passive-structure-mechanics@2/@3；准确 query 见公开汇总。Main 获得系统提示中的共同指导，但没有主动条目检索收据。Reporter 阅读、Main 收到报告、Main 主动读取原 Knowledge、理解并采用、影响决策不是同一件事。

## 6. C2 可以与不能回答的结论

本次已观测到 Direct 在本轮豁免合同下完成数值成功；Full 在用户停止前未取得合格候选，实际数学优化因观测缺失而不可比较。**Full 为人工停止的右删失运行，不能把其 41 次请求与 Direct 的完成成本 47 次直接解释为谁更高效，也不能将未观测成功解释为预算内失败。**

最终设计质量：只可确认 Direct 有满足本轮门槛的设计，Full 暂定对象未达到 Low、ratio 和招募转变门槛。数学问题构造：Full 有明确的绑定与问题，但一次 cap 不足，运行后完整目标不可用；Direct 未实际使用 API，组合能力未测试。证据组织：两组都有可追溯原始物理记录，Full 额外产生条件明确但无有效完整目标的数学记录。科研决策影响：Full 在收到不足结果后改路径，尚无数学带来设计改善的证据。

因此，问题“底层数学能力相同时，结构化数学层是否优于直接工具暴露”在这次运行中**未得到可归因的优劣证据**。除人工停止外，还有 Direct 数学能力未被实际调用、按需工具暴露差异、Full 网格轨迹差异与数学观测不完整等限制。仅涉及单次 P3 被动结构设计，不能声称统计显著性、通用架构优越性、设计空间无解、鲁棒性或硬件可迁移性。

## 7. 历史上下文（非匹配对照）

| Study | Provider | Math 账本 | 物理账本 | Low / mm（+x / −x） | Middle / mm | High / mm | Residual / mm | Ratio | 证据结论 |
|---|---|---|---|---|---|---|---|---|---|
| Full-Historical | 150 | 67 | 138 | 6.0179372 / 6.0179372 | 11.1172741 / 11.1172741 | 17.7510278 / 17.7510278 | 0.00124591 / 0.00124591 | 1.5373910 / 1.5373910 | 历史核心通过；探索性采样，未建立本轮逐步资格网格 |
| No-Optional-Math | 42 | 0 | 10 | 7.928066911447334 / 7.928066911447379 | 14.179043125448779 / 14.179043125448772 | 22.22665119511545 / 22.22665119511617 | 0.0006816136535264351 / 0.0006816136534904558 | 1.5534991664325057 / 1.5534991664323694 | 原数值合同成功；最终 2 cells、完整资格 |
| 本次 Full-Selective | 41 | 9 | 32 | 见双方向原始表 | 见原始表 | 见原始表 | 见原始表 | 见原始表 | 用户中止；无成功候选 |
| 本次 Direct | 47 | 0 | 24 | 见双方向原始表 | 见原始表 | 见原始表 | 见原始表 | 见原始表 | 本轮原数值合同成功 |

历史 Full 使用旧数学适配搜索路径，不能当成本轮共同直接物理搜索路径的匹配对照。其最佳 candidate_2915 为 4×0.058 m、圆半径 0.0065 m、Young 10.10 MPa；记录支持探索性数值核心通过，不能移作本轮完整资格或独立证书。历史 No-Optional-Math 的最佳候选为 45fc1cb8ba0f67db663c0ace6283eee803014c9a3f54b509e4d927fdb1549b03，结果 08a16882e03bb15a708ba95109c296b1fa510dffc2575101eef214ecd289b877。历史 token/费用为 UNKNOWN，本轮未重跑历史 Study。

Full-Historical 的 150 次与 No-Optional-Math 的 42 次请求差异不构成本轮 C2 结论。历史原始来源分别为 worktrees/passive-research-capabilities-20261107/runs/research/p3-passive-progressive-stiffness-autonomous-20261110-v1_2 与 worktrees/p3-no-math-account3-restart-20261112/runs/research/p3-ablation-no-math-20261112-account3-restart1。

## 8. 证据与交付映射

可提交的原始精度指标、完整候选参数、每方向全部阶段资格、任务违反量、收据计数、查询归属及 source artifact identity 均见 [public_summary.json](../../evidence/p3-c2-supervision-20261112/public_summary.json)。该文件是公开派生汇总，不替代原始 Store。

本地证据 home：D:/softrobot-agent/.worktrees/p3-structured-direct-math-20261112。每个 Study 的 runs/research/<Study ID>/platform.sqlite 保留 Store、Trace、ledger 和原始候选；物理与 analyses 子目录保留积分 CSV、模型、请求、返回值与生命周期文件。private-evidence/archive_manifest.json 与 immutable_artifacts.tar.gz 由既有 export 离线生成。Direct 已封存，Full 按人工停止时的原始 ready/prepared 状态封存，不伪造正式终止。大型原始归档和原始 Provider 内容保留本地，未纳入 Git。

监督证据目录为 evidence/p3-c2-supervision-20261112；本地还保留 actual Main prompt、两个 final-summary、budget checkpoints、数学缺失观测摘要和停止记录。全过程无第三个 Study、无重跑历史组、无扩大预算、无 source/config/Knowledge 修改；停止后只做离线整理、封存与用户请求的提交推送。

半步长、初态扰动、独立确认/证书、paired mechanism 因果证明、正式 SELECT、一般稳定性、重复性、硬件性能、全局最优与全局可行性均为 UNKNOWN 或未评估，不因本轮豁免而改记为 PASS。

两组离线导出均已完成；归档体积、既有 export SHA-256、成员数与本地 Store 映射见 [publication_mapping.json](../../evidence/p3-c2-supervision-20261112/publication_mapping.json)，完整 artifact 索引见 [Direct manifest](../../evidence/p3-c2-supervision-20261112/direct-archive-manifest.json) 与 [Full manifest](../../evidence/p3-c2-supervision-20261112/full-archive-manifest.json)。
