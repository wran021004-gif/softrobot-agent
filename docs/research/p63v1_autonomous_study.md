# P6.3 V1：空白 Study 自主结构—控制研究

**交付状态：用户要求临时暂停，非 Main STOP，也非预算耗尽。**

2026-10-30 22:13（北京时间）记录暂停：24/80 Provider（Main 14、Reporter 10），
94 个数学结果（84 computed、10 incomplete），独立物理 Replay=0，SELECT=0。
运行器和只读监视器均已停止。原 Store 保持 ready，预算与 SDK 快照完整保留，
不把暂停伪装成研究终结或正式成功；只有用户要求恢复时才继续同一个 Study。
本报告为暂停时的完整阶段报告，V1 科学目标尚未完成。

## 实验边界与归属

基线为 `4817d34cc32acad5b14ada43e88209cc97604951`，分支为
`codex/p6-3v-autonomous-feasibility`。V1 唯一 Store 为
`runs/research/p63v1-m3-autonomous-feasibility-sol-20261030`；初始冻结实现为
`0e5bad6af6f8273c6a2efce3c104ee39c961abc0`。

启动时候选、Main Plan、数学结果、物理 Replay 和 Provider 使用数均为 0。
没有导入 G3/V0 的候选、控制序列、结果或历史解。V0 是 Operator 对旧 G3 解的
一次独立验证；以下 V1 结果属于本轮 Main 的新 Study，不能反向记作 G3 成果。

任务、FamilySpace、分析协议、控制配置、保真度和 runtime 均与 G3 科学配置一致。
目标为 `[0.29, -0.035, 0.19]` m，时长 0.5 s，最后 0.05 s 保持；原终点和保持位置
限值均为 0.01 m，保持速度限值为 0.02 m/s。保留 12 cells/segment、原 MuJoCo
模型和独立完整任务 evaluator。算法、阈值、容差、提示词和 Reporter 策略保持原配置。
第二轮封存后的真实 SQLite 交接故障需要一次最小事务读取修复，详见工程恢复节。
模型始终为 `gpt-5.6-sol`，reasoning 为 `none`，计算线程环境为 1。

Provider 总上限 80，包含 Reporter、失败请求和收尾；原 protected reserve 为 4。
其他科学次数维持原宽裕额度，Native 上限为 4 knots / 100 iterations / 1000 callbacks。
任务执行说明复用原 G1 空白完整 Study 说明，未沿用 G3 短窗口结束指令；启动后
不改变提示词、模型、预算或科研规则。只读检查点不建议实验、不代替 Main 决策。

准备阶段一次 clean-commit guard 在任何 Provider 请求和冻结之前阻止 bind；提交
V0 审计后，在原 Store、同一授权下完成原准备，没有重置预算或创建第二个 Study。
启动前证据见 `p63v1_preflight.json`。

## Main 的初始假设与自我修正

Main 首先提出两段、六拉索的独立近端/远端控制权假设：三根全长拉索加三根仅远端
拉索。三次生成均被原 `BASE_ONLY_REQUIRES_FIRST_SEGMENT_ZERO` 校验拒绝，未形成
合法候选。Main 随后自行检索、读取 FamilySpace/工具契约并修正研究方法；没有
Operator 替它选择结构或调整参数。

搜索请求先后遇到 `consecutive` 不属于合法 span strategy、`distal` 不适用于冻结
base-only 规则的反馈。实际被接受的是请求 10 的 H3_legal_native_codesign_search：
在合法 family 中搜索 routing、lengths、materials、sections，对每个候选重新进行
Native 控制优化；有限失败不能证明结构不可行。

该实际 Plan 为
`9ba211a1feef882ef51025f8ec5e60c0be076aa2f0c6926ee46355076d094521`：
32 proposals / 32 evaluations，2 segments、6 tendons、whole_chain、standard fidelity、
0 N 初始张力、无 previous_candidate_ref。控制选择原 response 方法，4 个均匀 knots
`[0, 1/6, 1/3, 0.5]` s、60 iterations、600 callbacks、coefficient limit 2 N、
correction window `[0, 0.5]` s。此前被拒绝请求中的 24/300 不属于实际执行设置。

## 第一轮有限联合搜索

搜索引用为 `a9aefb737296f7419f0e0aa22de7dd2df8e8c8b8fb20ebe0e8b3420dbae8686a`。
32 个 proposal 中 31 个合法构建并实际评估；proposal 10 的 routing.anchor_s 为
duplicate_or_clipped_no_change，未增加评估。原终止原因是 proposal_budget_exhausted，
状态 best_finite_budget_native_candidate。Worker wall 为 1122.5986371040344 s。

24 个结果 computed，7 个 execution_incomplete，后者原因均为
`NATIVE_V1_REQUIRES_FINITE_CONTACT_FREE_UNCONSTRAINED_STATE`，不进入有效 J 排名。
构建合法性不等于数值计算完整性；3 次初始生成失败也不能混计为数学 computed。

主要观察到的改进链如下，各候选都重新优化控制，因此不作单因素因果归因：

| 候选前缀 | 本步结构变化 | 有限模型 J |
|---|---|---:|
| b10bb2b33fa7 | family defaults | 0.24046985119633235 |
| c3496b1e057a | segment 0 Young modulus | 0.07916153786128355 |
| 950be6649bde | segment 0 semi_y | 0.06974862656727865 |
| 874b04c7d35e | segment 1 length | 6.888711823194171e-11 |
| f419dd73d9ad | tendon 0 angular offset | -7.005650779490225e-7 |
| d0d2a0f80afc | tendon 0 radius | -0.007361335244673861 |
| 304f7f3d9874 | tendon 3 radius | -0.01303662252475446 |
| 37eec2e59674 | tendon 4 radius | -0.014355323230259676 |

最优候选完整引用为
`37eec2e5967481d61cd78c00c1e0b723212171e310afe200e72c2957766a2734`；数学结果为
`e85b6c553a54d4ba11b49ae30210b44f7f918638dd7f7d266bab4772bbb764e1`；优化控制 source 为
`384aecee7e91edda92ee13afde19948baa315a92189abbb22e821811d0bfd208`。

该结构两段长度为 0.16 / 0.14500000000000002 m，Young modulus 为
10450000 / 5400000 Pa；第一段椭圆 semi_y/semi_z 为 0.01175 / 0.0076 m，第二段矩形
width/height 为 0.0133 / 0.0095 m。六根拉索均从 segment 0 到 1，半径依次为
0.020249999999999997、0.018、0.018、0.020249999999999997、0.020249999999999997、
0.018 m。完整参数、截面方向、拉索角度和逐步 lineage 保存在紧凑审计与 Store。

最优有限模型的终点误差为 0.009810678200353168 m，最大保持位置误差为
0.009856446767697404 m，最大保持速度为 0.019375487972897596 m/s；J 为
-0.014355323230259676。该候选自身从初始 J=23.854683350026622 改善到上述 J；
实际使用 188 callbacks、8 次 started iterations，原终止为 local_target_reached。
这是保存的模型计算改进，不是全局最优证明，也不能替代独立验收。

## 搜索后继续 Main 与第二轮假设

第一轮 Worker、Reporter 和原会话交接完成后，Main 在请求 19 自主提出
H4_fresh_native_codesign_bounded，未由 Operator 关闭 Study。实际 Plan 为
`f13dd1b44b22ed4ac80038e56d37202054d0e213a6ba74a46a3facb42af826dd`。
它引用最后两个不完整数学结果，选择第二轮 64 proposals / 64 evaluations，仍搜索
lengths、materials、sections、routing，2 段、6 拉索、whole_chain；初始张力改为
1 N，原 response 控制预算提高到 4 knots / 100 iterations / 1000 callbacks。
previous_candidate_ref 是 V1 内最后一个不完整候选 `7073a14196f1…`，不是 G3/V0 解。
Main 明确区分模型筛选见证与独立物理验收，表示表观通过仍需 Replay。

只读 wire 审计发现：请求 19 含第一轮完整搜索结果引用，但不直接包含该轮最佳
候选引用 `37eec2e59674…` 或最佳分数；紧凑当前候选与两份可见 Reporter 解释聚焦
于最后的不完整结果。实际 wire 为
`f7cd183326eeb374268443bbe0a46091d1189469d7b785107d82a284df16b527`。
因此不能声称 Main 已直接审阅最佳候选后决定放弃它；完整不可变搜索结果仍可
通过 evidence_read 读取。这是本次观察到的信息交付限制，未在研究中途修补或
由 Operator 把最佳候选提示给 Main。逐轮检查保存在紧凑审计 search_delivery_checks。

该轮搜索保存到下一次 Main 请求的观测间隔为 658.926365 s；最后一份 Reporter
完成到 Main 请求的间隔为 467.092967 s。这是实际框架交接/上下文阶段的 wall 间隔，
不作为额外的 Provider 调用或物理计算计数，也不与已含其中的耗时重复相加。

## 第二轮有限搜索的封存结果

搜索引用为 `61251b64d479c7f9994fac52510f2800ebc6a78a6f8b9d9e4ebcb7e4499d43c5`。
64 个 proposal 中 63 个合法构建并实际评估；proposal 11 的 routing.anchor_s 为
duplicate_or_clipped_no_change，未新增评估。60 个 computed、3 个 execution_incomplete，
仍因原数值有效性条件未满足；原终止原因为 proposal_budget_exhausted。
Worker wall 为 2512.8935039043427 s。

该轮关键的更优模型观察链为：

| 候选前缀 | 本步结构变化 | 有限模型 J |
|---|---|---:|
| c3496b1e057a | segment 0 Young modulus | 0.06696641754969246 |
| 950be6649bde | segment 0 semi_y | 0.04778226673617336 |
| 7985d5f1a32c | routing phase | 0.047782253267584895 |
| ba499fcaa847 | segment 1 Young modulus | 1.0891287871572786e-12 |
| 120b93710bba | segment 0 semi_z | -0.0005369787848732432 |
| 0848ec0e4d44 | routing guide | -0.004766162067843971 |
| 4e7e8944af46 | tendon 0 radius | -0.006097842761171535 |
| 511cfea7bd77 | tendon 1 radius | -0.006333794955055927 |
| 75b62217056b | routing anchor | -0.006545624700332375 |
| 93be32b1e92a | segment 0 semi_y | -0.006742070337740325 |
| 1e0adb9d3f7c | tendon 0 radius | -0.0069635885347172355 |

最佳候选为 `1e0adb9d3f7cf4f5886d83fbbc1d4777d4190915d45fae1780a8e3b6ab8e891c`，
数学结果为 `79e1d1fbc2f0b9cda262a291342209f2740e9daa93da35415773e65c4d104706`，
控制 source 为 `7b56a050d0d9aa04269618bef29db9e8d72baae5912bf82ecf329a79a874d243`。
该候选两段长度为 0.16 / 0.11 m，Young modulus 为 10450000 / 8650000 Pa；
第一段椭圆 semi_y/semi_z 为 0.012 / 0.009850000000000001 m。六根全长拉索的
guide_s=0.65、anchor_s=0.95，前两根半径为 0.021374999999999998 /
0.020249999999999997 m，其余为 0.018 m；完整旋转和截面参数见审计。

最优模型的终点误差为 0.009919327922016292 m，最大保持位置误差为
0.009930364114652828 m，最大保持速度为 0.01939479800742005 m/s；该候选自身
从初始 J=9.497107205283758 改善到 -0.0069635885347172355。实际使用
150 callbacks、6 次 started iterations，正常 local_target_reached，未强行凑满预算。

第一轮保存的最优 J 更低；两轮结构路径与初始张力不同，不能将差异单独归因于
控制预算，也不能据此推出结构因果结论或全局排名。两轮合计 94 次数学结果、
84 computed、10 incomplete，91 个候选记录；不同轮次可能再次评估同一结构。

## 真实交接故障与同一 Study 恢复

第二轮 Worker 与 Reporter 后，原进程在 request-feedback handoff 内因
`sqlite3.OperationalError: database is locked` 退出，未发送下一次 Main 请求。
当时 Provider=21、数学结果=94、独立 Replay=0、pending/unconsumed response 为空，
所有科学调用已有回执。交接准备事务回滚，未提交新 handoff pointer。

原因已用冻结前代码的离线测试复现：在默认 rollback journal 下，向写事务插入
大于默认 SQLite cache 的状态会触发 cache spill；handoff 随后另开只读连接取
events/artifacts/feedback，因自己的写锁而失败。实际状态 JSON 为 1853018 bytes。
离线 3 MiB 状态 padding 测试在原 `0e5bad6…` 代码上稳定得到相同 database lock；
fixture 的 100 ms busy timeout 只用于快速复现，没有改变真实 Store 设置。
这一机制与 [SQLite 官方 cache_spill 说明](https://www.sqlite.org/pragma.html#pragma_cache_spill)
一致：事务中溢写脏页会取得 EXCLUSIVE lock；本 Store 实测 cache_size=-2000，
即默认建议缓存 2000 KiB。该判断同时有原代码失败复现和修复后真实交接成功支持。

最小修复让 Store.events 可复用已有连接，并把 handoff 的事件、artifact 和反馈
读取绑定到原写事务；没有改 journal 模式、预算、科学内核、评价器、模型、提示词、
工具 Schema 或科研规则。直接运行大状态交接测试和原交接/反馈保持测试，2 项通过，
均使用 Mock HTTP，真实 Provider/物理运行均为 0。没有重跑 C0–G3 全套回归。

修复按原 commit/migrate 恢复机制绑定到同一 Store，保留所有原结果与成本；不重跑
两轮搜索、不重置配额、不创建第二个 V1 Study。修复前后 profile、科学配置与资源
余额的比较及新 implementation freeze 以 `p63v1_lock_repair_audit.json` 为准。

原 migrate 绑定到 `c9a2280c39f9462d55c1aded145070cfbc9897a0`。冻结科学配置、
SCIENCE_FILES 源码指纹、全部候选/数学/搜索引用、Provider 计数和数值费用的保留
检查均通过。原迁移对共享 Store 的传递依赖指纹变化作保守处理，新增 evaluation
profile v2，并记录 material_behavior_change=true；因此 **profile identity 并未保持
不变**。原 profile v1 与两轮结果留在历史中，没有回写版本或绕过兼容性门槛。
此后正式验收必须满足原流程对当前 profile、来源和新鲜性的要求。

迁移事务已正式提交；随后 CLI 仅为打印大型 packet 构造上下文，停止的是这个
展示进程。实际接续通过原 converse API 自动校验 SDK/Store 并恢复同一 Study，
剩余请求限额为 59，使全程总上限仍为 80；没有再次发送旧搜索请求。

## 两轮已封存阶段的费用

截至暂停时第 24 次 Provider 请求，数学结果仍为上述 94 个。原数值账本可核对为：

| 原计账口径 | 秒 |
|---|---:|
| 数学结果 charged_numerical_s 合计 | 3310.083096699993 |
| 候选构建 construction_numerical_s | 41.77920159994392 |
| 控制初始化 control_initialization_s | 20.810358899907442 |
| 数值总账 numerical_s | 3372.6726571998443 |

两轮搜索外层 wall 合计 3635.492141008377 s；它包含内部工作和协调开销，不与上表
再相加。已返回详细成本的 84 个 computed 结果记录 84 builds、32410 rollouts、
32410000 physics steps、3273494 forward evaluations，kernel wall 3129.9906393000274 s
属于数学工作内部，也不重复相加。10 个 incomplete 的内部 rollout/step 计数缺失，
不是零；其原 charged Worker 耗时已经保留。控制源登记既包含初始化输入，也包含
优化后序列，登记条目数不代表额外独立 Replay 次数。

暂停时 Provider 为 24/80（Main 14、Reporter 10），实际 prompt/completion/total
tokens 为 198250 / 9694 / 207944；Reporter 使用 39979 tokens。原 Provider elapsed
合计 416.2170000000333 s，并非 Study 全程 wall。美元费用未回传，记为未知。
总额度剩余 56 次，包含原 protected reserve，不能解释为 56 次纯科研请求。
未达到建议的 35/60 检查点，因此不补造这些检查点。15 次原检查点完整保留。

## 知识访问与科研证据的区别

最初两次带结构/失败类型过滤的经验目录检索未命中。第 22 次请求中 Main 自主
改为 task=reach_and_hold 的检索，返回 8 条目录元数据，含 owner-M1/M2/M3 的简短
历史 Trace 入口及通用程序条目。这不是读取其正文，更不是导入历史实验或控制。

第 23 次 Main 自主读取 `research-bounded-continuation@2`，原工具成功返回通用
程序正文，回执为 `921a41d1fbde9f800d6eefbd1ebd2a0af78857bb950a9fc44734e9aca4492075`。
`model-physics-comparison@1` 与该条目均曾作为自动目录提示出现；不能把提示出现
当作正文阅读或方法采用。完整正文何时进入实际 Main 请求，以最终审计
`knowledge_main_delivered_bodies` 的精确 wire 核对为准，服务端读取成功不单独证明
交付、理解或采用。目录返回、Main/Reporter 正文读取及实际交付分别记录。

Knowledge 保持原冻结目录，新写的 V0/V1 Operator 报告没有自动加入知识输入。
所有历史经验均为 procedural guidance / research trace，scientific_evidence=false；
既不授予当前执行权限，也不构成当前 M3 任务通过证据。


## 恢复后的实际动作与用户暂停

请求 22 检索经验目录；请求 23 读取通用 procedure。请求 24 的 Main 自主提出
H5_independent_pass_from_native_margin，并选择新一轮结构—控制搜索：24 proposals /
24 evaluations、response 4 knots / 30 iterations / 240 callbacks、初始张力 0 N。
它仍引用 V1 旧候选 `7073a14196f167a79202509e4ad71df6b48148167ad2cff391efc2383abacb55`，
在原当前-profile准入中被拒绝：
`OLD_EVALUATION_PROFILE_CANDIDATE_REQUIRES_NEW_CONSTRUCTION`。
反馈明确 scientific_execution_started=false，因此没有第三轮数学计算或物理 Replay，
也没有新增 accepted Plan。完整原输入与错误回执在暂停审计和 Store 中保留。

第 24 次实际 wire 为
`d0667a99a5e00ccf021595bf295949e60089abfcb26457c240421f9d83d1bca8`；
错误工具反馈为 `6b85f6481e7aaa72896eb10e86645280f7f3285189d54013337106d3ec0251e4`。
用户随后明确要求暂时停止并整理 push；两个统一执行 session 收到 Ctrl-C 并结束。
暂停时 pending、unconsumed_response、未封存调用均为空，94 个 Native Worker 的
终止证据都已确认；G3 原 Store 的大小和 mtime 与 V0 前记录一致。

通过原 record 接口仅追加 supervisor_pause 事件，引用为
`2991a53a792802cd069c8ab94dcb6d9fe88db7b313cb2d5033e361562e0b83a1`。
这没有修改科研状态、配额、候选或物理判定。暂停不冒充 SDK invocation 完成，也未
为暂停额外执行一次 handoff。原 SDK 快照、最近实际响应和工具反馈一起保留；
以后恢复必须先由原 SDK/Store 恢复机制校验/补齐边界，不能直接假定新 handoff 已完成。

## 简短 Trace 与 Main 实际看到的内容

只读检查了请求 19、22、23、24 的真实 CURRENT_RESEARCH_PACKET，而不是重新生成
一个事后 packet。恢复后的简短 research_trace 仍包括 #180 和 #818 两轮 search 的
completed / scientific_result_recorded，另外包括生成及参数拒绝里程碑；第 24 次
wire 的 action_total=8、milestone total=6，recent 展示 4 项，另有 unresolved 项。
所以中断前动作没有在 Store 或简短 Trace 中消失，但这是有界里程碑摘要，未直接
携带两轮最佳 C/M/U、最佳 J 或完整搜索参数。完整历史仍有 research_recall 导航。
精确字段见 `p63v1_pause_trace_audit.json`，完整事实见不可变原搜索结果与 Store。

两轮结果引用交回 Main，不等于最佳结果及其含义完整交付。第一轮下一次 Main
请求 19 和第二轮下一次 Main 请求 22 均没有直接出现对应最佳候选及最佳 J；Main
可按结果引用读取完整信息，但不能据此声称它已看过最佳后主动放弃。
第二轮搜索保存至请求 22 的 3174.798065 s 包含工程故障、修复、迁移和恢复，
不能全部归为上下文构造的纯开销。

请求 23 的经验正文 read 在服务端完成，但到请求 24 为止，精确完整回执检测没有
确认其正文进入实际 HTTP200 Main wire；该 wire 的 read_progress.body_delivered=false。
因此本次只确认 1 次 Main procedure 正文工具读取，确认完整正文交付数为 0；
历史 owner-M1/M2/M3 Trace 正文读取数为 0。自动目录提示、目录命中、服务端正文
读取、实际完整正文交付应分别记录，不能相互替代。Main 的经验选择是它的真实
工具调用，不是框架强制；模型为何这样选择，没有足够证据作心理或单一因果解释。

## 暂停时分层结论与剩余事项

| 层级 | 暂停时判定 |
|---|---|
| 有效科研行动 | 已有两轮合法自主联合搜索 |
| 有效数学改进 | 已有，第一轮最优 J=-0.014355323230259676 |
| 模型近可行/满足采样指标 | 有保存的有限模型见证，不替代物理验收 |
| 独立物理通过 | 未验证；V1 Replay=0 |
| 正式自主成功 | 未完成；无 acceptance certificate / SELECT |
| 预算内研究最终失败或 Main STOP | 未判定；用户在 24/80 时临时暂停 |

以后若用户恢复：必须使用同一 Store，保留已用 24 次和总上限 80，先按原机制
恢复 SDK/反馈，遵守 profile v2 对新构建候选的原约束，由 Main 自主决定后续研究。
Operator 不克隆旧候选、不指派 Replay、不注入最佳解，也不重跑两轮已封存搜索。
主要待处理的工程观察是最佳搜索结果的紧凑交付、知识正文的实际交付与昂贵交接；
本次未为这些观察临时改动研究提示词或接口。研究结论仍需独立物理验证支持。

## 归档与验证

原始 G3/V0/V1 Store、数学/物理轨迹和回执留在各自 runs 目录；outputs 同时提供
原 export 证据包及 V0/V1 完整运行目录备份。原 export 不修改科研状态；完整备份
含原 SQLite、SDK context/session、Worker 生命周期和输出，不向 GitHub 提交大型
运行数据。GitHub 分支提交报告、配置、审计与必要的两文件事务读取修复。
本地 Git bundle 保留原精确冻结提交链；发布记录说明远端提交与本地树的对应关系。
直接检查见 `p63v_final_checks.json`：身份、预算、调用回执、Worker 终止、G3
只读保全与生产改动范围均通过；没有因整理再发送 Provider 或启动新的科学计算。
