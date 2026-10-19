# P0–P2 证据驱动控制搜索交付（2026-10-19）

P0/P1/P2 的基础链路、有限实验和回归验证已完成。**本轮没有找到通过原任务全部验收条件的解。** 最优完整物理评价的终点误差为 5.193064 mm，保持最大误差为 5.193910 mm，保持最大速度为 0.021090041 m/s；速度仍超出 0.020 m/s 上限约 5.45%。这是有效失败，不能解释为结构不可行。

工作位置为 `.worktrees/sorosim-matlab-nmpc`，分支 `feat/sorosim-matlab-nmpc`；基线为 `5cd0531094f22e42facde77d7baaa6d70e870e85`。IDE 中其他 worktree 的文件没有参与本轮修改。

## A. 真实完成情况与数据流

| 阶段 | 已实现及验证 | 未完成的科学结论 |
|---|---|---|
| P0 | 11 个历史记录的身份、原始有效性、指标、来源和成本资产化；精确恢复实际施加控制；任务/指标分组、有效性优先排名、位置速度 Pareto；4 次独立完整回放及历史配对 | 没有把历史无效 NMPC 执行改写为成功；仅新开环回放取得新的有效性 |
| P1 | 纯回调局部搜索、有限差分响应约束 SLSQP、确定性坐标搜索；同起点/基函数/边界/评价器/Store；24 次真实评价；已完成结果的恢复和缓存核验 | 原任务通过解、区域模型误差界、全局可行性和方法总体优越性均未建立 |
| P2 | 七类证据摘要、身份及范围检查、禁止推论、五类待检验假设；6 个旧分析和 24 个新物理结果的只读证据视图；细化失败降级 | 诊断根因、校准故障概率、总体统计结论、完整 Agent 执行前审查未建立 |

数据流：既有 `numerics.archived`/`holding_diagnostic.historical` → `candidate_portfolio.record/portfolio` → 已绑定的 `explicit_control_schedule_v1` → 既有 candidate、Store、`core.dispatch` 和 `physical_replay` → 原独立验收 → 既有 `task_gap` 排名 → Evidence Policy 附加视图。原始归档和 scoped claim 保留原样。

`compatible_schedule` 对比机器人、设计、模型、任务、时序、通道顺序及物理 seed/backend/discretization/dynamics_model；不以相同控制数组推定相同物理实验。恢复使用实际施加控制，检查 35×4、输入界、采样相位、时间网格和 engine time；密集子步必须逐点覆盖且区间内保持恒定，不做平均。

`local_control_search.search(starts, evaluate, settings)` 只拥有有限搜索逻辑。调用方使用 `physical_replay.evaluate_schedule` 扫描既有 Store 的已结算结果、恢复引用，缺失时才经既有预算和调度执行。没有新增缓存数据库、预算账本、物理求解器或生命周期。恢复是确定性重走搜索并复用完成结果，不是恢复 SLSQP 内部状态；pending 执行仍须走既有 `core.recover`。

默认修正为 3 个时间结点 `[0, 0.18, 0.30] s` × 4 根腱，共 12 维；契约最多支持 4 结点/16 维。有限差分探测也计入请求预算并参与最优排名。SLSQP 使用归一化终点及保持位置/速度向量约束、力边界、信赖半径和系数边界；坐标搜索优先晚期结点，完整扫掠仍涵盖早期控制。本轮有限预算没有完成所有结点的扫掠。

明确 `NOT_RUN`：真实任务成功后的停止路径（只做合成测试）、故意中断活动 native worker 的恢复实验、硬件/鲁棒性/重复性实验、等预算方法优越性研究、总体统计验证、P3 Agent 接入、P4、完整数学 NLP、新 NMPC rollout、PPO 训练和 provider 请求。后四项科学运行没有发生；已完成结果恢复有实际只读审计。

## B. 逐文件改动表

以下统计相对基线；A=新增，M=修改，无删除文件。生产代码合计 **+650/-1 行**；测试、驱动、配置、归档及本文单列。JSON 行数是可追溯证据体积，不是生产代码。二进制文件按字节列出。表中“作用/必要性”同时解释修改原因，“复用”说明事实或执行机制的权威来源。

| 文件 | 操作 | + / − 行 | 作用 / 必要性 | 复用 |
|---|---|---:|---|---|
| [configs/research/study_control_search_p0.json](../../configs/research/study_control_search_p0.json) | A | +17/-0 | 声明独立冻结研究与有限预算 | 原配置格式/预算系统 |
| [configs/research/study_control_search_p1.json](../../configs/research/study_control_search_p1.json) | A | +21/-0 | 声明独立冻结研究与有限预算 | 原配置格式/预算系统 |
| [evidence/control_search_p0/portfolio.json](../../evidence/control_search_p0/portfolio.json) | A | +4731/-0 | 保存 11 项历史候选及精确控制来源，供复核 | candidate_portfolio 导出 |
| [evidence/control_search_p0/progress.json](../../evidence/control_search_p0/progress.json) | A | +2632/-0 | 保留 P0 四次完整配对过程 | 原结果与接受组件 |
| [evidence/control_search_p0/source_audit.json](../../evidence/control_search_p0/source_audit.json) | A | +321/-0 | 证明历史源前后 hash 相同 | 既有归档文件内容 |
| [evidence/control_search_p0/study/archive_manifest.json](../../evidence/control_search_p0/study/archive_manifest.json) | A | +329/-0 | 保存归档成员与摘要便于完整性复核 | 原 core.export |
| [evidence/control_search_p0/study/calls.json](../../evidence/control_search_p0/study/calls.json) | A | +170/-0 | 保留真实调度调用和成本 | 原 Store/core.export |
| [evidence/control_search_p0/study/configuration.json](../../evidence/control_search_p0/study/configuration.json) | A | +2996/-0 | 保留每个 study 完整冻结配置和绑定 | 原 core.export |
| [evidence/control_search_p0/study/disposition.json](../../evidence/control_search_p0/study/disposition.json) | A | +127/-0 | 保留停止、选择和执行状态 | 原 core.export |
| [evidence/control_search_p0/study/immutable_artifacts.tar.gz](../../evidence/control_search_p0/study/immutable_artifacts.tar.gz) | A | binary 334012 bytes | 保存不可变 artifact 原件，支持独立复核 | 原 Store/core.export |
| [evidence/control_search_p0/study/ledger.json](../../evidence/control_search_p0/study/ledger.json) | A | +24/-0 | 保留已用、剩余和占用预算 | 原统一预算/core.export |
| [evidence/control_search_p0/summary.json](../../evidence/control_search_p0/summary.json) | A | +2664/-0 | 保存全量指标、验收和方法结果 | 原结果与搜索导出 |
| [evidence/control_search_p0/validation.json](../../evidence/control_search_p0/validation.json) | A | +30/-0 | 记录配对/恢复/预算检查及局限 | 保存结果只读审计 |
| [evidence/control_search_p1/audit_saved_results.py](../../evidence/control_search_p1/audit_saved_results.py) | A | +48/-0 | 证明 26 次重走请求无新计费且最优结果一致 | 同一 search 和既有 Store |
| [evidence/control_search_p1/best_control.json](../../evidence/control_search_p1/best_control.json) | A | +406/-0 | 独立保存最优失败控制和引用便于继承 | P1 summary 原始序列 |
| [evidence/control_search_p1/portfolio.json](../../evidence/control_search_p1/portfolio.json) | A | +4731/-0 | 保存 11 项历史候选及精确控制来源，供复核 | candidate_portfolio 导出 |
| [evidence/control_search_p1/prelaunch_boundary.json](../../evidence/control_search_p1/prelaunch_boundary.json) | A | +8/-0 | 保留首次绑定拒绝及零物理成本 | 既有绑定错误和账本 |
| [evidence/control_search_p1/search_progress.json](../../evidence/control_search_p1/search_progress.json) | A | +17198/-0 | 保留 P1 请求、探测、预测和最优轨迹 | search 回调与 Store 结果 |
| [evidence/control_search_p1/source_audit.json](../../evidence/control_search_p1/source_audit.json) | A | +321/-0 | 证明历史源前后 hash 相同 | 既有归档文件内容 |
| [evidence/control_search_p1/study/archive_manifest.json](../../evidence/control_search_p1/study/archive_manifest.json) | A | +1271/-0 | 保存归档成员与摘要便于完整性复核 | 原 core.export |
| [evidence/control_search_p1/study/calls.json](../../evidence/control_search_p1/study/calls.json) | A | +716/-0 | 保留真实调度调用和成本 | 原 Store/core.export |
| [evidence/control_search_p1/study/configuration.json](../../evidence/control_search_p1/study/configuration.json) | A | +3026/-0 | 保留每个 study 完整冻结配置和绑定 | 原 core.export |
| [evidence/control_search_p1/study/disposition.json](../../evidence/control_search_p1/study/disposition.json) | A | +207/-0 | 保留停止、选择和执行状态 | 原 core.export |
| [evidence/control_search_p1/study/immutable_artifacts.tar.gz](../../evidence/control_search_p1/study/immutable_artifacts.tar.gz) | A | binary 1410546 bytes | 保存不可变 artifact 原件，支持独立复核 | 原 Store/core.export |
| [evidence/control_search_p1/study/ledger.json](../../evidence/control_search_p1/study/ledger.json) | A | +24/-0 | 保留已用、剩余和占用预算 | 原统一预算/core.export |
| [evidence/control_search_p1/summary.json](../../evidence/control_search_p1/summary.json) | A | +17852/-0 | 保存全量指标、验收和方法结果 | 原结果与搜索导出 |
| [evidence/control_search_p1/validation.json](../../evidence/control_search_p1/validation.json) | A | +45/-0 | 记录配对/恢复/预算检查及局限 | 保存结果只读审计 |
| [evidence/control_search_p2/audit_saved_evidence.py](../../evidence/control_search_p2/audit_saved_evidence.py) | A | +54/-0 | 对保存结果生成视图并核查细化边界 | Evidence Policy/历史归档读取 |
| [evidence/control_search_p2/saved_evidence_views.json](../../evidence/control_search_p2/saved_evidence_views.json) | A | +5067/-0 | 保留 30 个视图及旧细化失败复核 | 保存证据和 Evidence Policy |
| [evidence/control_search_p2/verification.json](../../evidence/control_search_p2/verification.json) | A | +37/-0 | 记录 100 项回归、归档摘要及边界检查 | 真实测试及只读核验 |
| [tests/research/control_search_pilot.py](../../tests/research/control_search_pilot.py) | A | +132/-0 | 显式 P0/P1 驱动，冻结、执行、导出独立 study | core.prepare/bind/generate/dispatch/export/stop |
| [tests/research/test_candidate_portfolio.py](../../tests/research/test_candidate_portfolio.py) | A | +89/-0 | 验证对应新契约和失败边界，防止科学语义回归 | unittest/既有夹具与结果契约 |
| [tests/research/test_evidence_policy.py](../../tests/research/test_evidence_policy.py) | A | +127/-0 | 验证对应新契约和失败边界，防止科学语义回归 | unittest/既有夹具与结果契约 |
| [tests/research/test_local_control_search.py](../../tests/research/test_local_control_search.py) | A | +130/-0 | 验证对应新契约和失败边界，防止科学语义回归 | unittest/既有夹具与结果契约 |
| [tools/research/analysis.py](../../tools/research/analysis.py) | M | +4/-0 | 在既有结果视图附加证据摘要，供后续机器检查 | 原 scoped_claim/decision_result |
| [tools/research/candidate_portfolio.py](../../tools/research/candidate_portfolio.py) | A | +134/-0 | 历史资产、身份绑定、恢复控制、分组排名及 Pareto | archived/historical/task_gap |
| [tools/research/config.py](../../tools/research/config.py) | M | +10/-0 | 加入可选局部搜索配置，保持旧配置可读 | 原配置加载及冻结机制 |
| [tools/research/contracts.py](../../tools/research/contracts.py) | M | +40/-0 | 强类型搜索设置和 evidence_policy_v1 摘要 | 原 Pydantic 契约 |
| [tools/research/control_correction.py](../../tools/research/control_correction.py) | M | +40/-0 | 局部向量约束和响应子问题，供纯搜索调用 | 原控制基函数和 SciPy SLSQP |
| [tools/research/evidence_policy.py](../../tools/research/evidence_policy.py) | A | +141/-0 | 范围检查、七类证据和五种假设，限制越界推论 | 原 scoped claim/task_gap/契约 |
| [tools/research/holding_diagnostic.py](../../tools/research/holding_diagnostic.py) | M | +43/-1 | 保留施加控制/时间相位并拒绝截断或错位数据 | 原历史读取与 CSV 解析 |
| [tools/research/local_control_search.py](../../tools/research/local_control_search.py) | A | +108/-0 | 可复用有限响应/坐标搜索，保留每个探测结果 | control_correction/ranking_key/回调 |
| [tools/research/physical_replay.py](../../tools/research/physical_replay.py) | M | +30/-0 | 精确 schedule 身份与 Store 完成结果恢复 | 原 Store/core.dispatch/预算/回放 |
| [本文](control_search_p0_p2_delivery.md) | A | +218/-0 | 集中交付范围、逐文件变更和证据限制 | 引用既有报告/归档，不复制实现 |

## C. 科学运行结果

冻结任务保持 35 次控制更新、0.01 s 控制间隔、0.30–0.35 s 保持窗口、位置上限 10 mm、速度上限 0.020 m/s、四腱各 `[0,8] N`。下表 G 为既有 `task_gap` 的最大归一化违反量；无效历史执行的 G 记为 null，不能据低误差进入有效解排名。位置展示为 mm，完整未舍入 SI 指标、完整接受组件和成本见对应 JSON。

### 历史候选（只读）

| 历史结果前缀 | 来源 | 历史状态 | 终点 mm | 保持位置 mm | 保持速度 m/s | G |
|---|---|---|---:|---:|---:|---:|
| a323c9375b46 | evidence/sorosim_s58/study | valid_task_failure | 5.917143774 | 6.618027540 | 0.069612810 | 2.480640498 |
| 8e7ee1afd56c | evidence/sorosim_s510/study | valid_task_failure | 34.742183428 | 35.818994387 | 0.104178985 | 4.208949237 |
| 15cce2112131 | evidence/sorosim_s58/study | valid_task_failure | 5.726664823 | 6.938187305 | 0.104976667 | 4.248833326 |
| 88a9368baf27 | evidence/sorosim_s58/study | valid_task_failure | 6.589359770 | 7.297399673 | 0.109578213 | 4.478910630 |
| d9f90ae212e2 | evidence/sorosim_s59/study | valid_task_failure | 16.677320051 | 16.753886037 | 0.129669292 | 5.483464584 |
| ec6b9563a756 | evidence/sorosim_s56/rl/study | valid_task_failure | 133.171574350 | 135.178638360 | 0.052934973 | 12.517863836 |
| 6525abb1b05c | evidence/sorosim_s56/rl/study | valid_task_failure | 21.601973615 | 25.760594592 | 0.312143126 | 14.607156309 |
| ad716d412cb2 | evidence/sorosim_s58/study | valid_task_failure | 5.483582238 | 7.462180617 | 0.336118609 | 15.805930456 |
| 1099c6f4e978 | evidence/sorosim_s59/study | valid_task_failure | 5.869246498 | 12.939257955 | 0.339659836 | 15.982991807 |
| c0da16dc3c57 | evidence/sorosim_s56/physics/study | valid_task_failure | 16.856707818 | 16.856707818 | 0.498798459 | 23.939922971 |
| 96615db5434b | evidence/sorosim_s56/physics/study | invalid_or_incomplete_execution | 6.120971961 | 6.926833645 | 0.041814094 | null |

历史身份、原验收、replay pending/unavailable 和拒绝原因保存在 [P0 portfolio](../../evidence/control_search_p0/portfolio.json)。恢复后的控制本身仍是 acceptance unmeasured，必须独立评价才能获得新任务结论。

### P0 四次配对回放

| 历史来源前缀 | 新结果前缀 | 终点 mm | 保持位置 mm | 保持速度 m/s | G | 计费 s |
|---|---|---:|---:|---:|---:|---:|
| 96615db5434b | e9e602c40d5b | 6.120971961 | 6.926833645 | 0.041814094 | 1.090704702 | 1.111012900 |
| a323c9375b46 | c96d2157ea3c | 5.917143774 | 6.618027540 | 0.069612810 | 2.480640498 | 1.093815300 |
| 15cce2112131 | a45bc1e271f4 | 5.726664823 | 6.938187305 | 0.104976667 | 4.248833326 | 1.104772000 |
| 8e7ee1afd56c | a6826c839240 | 34.742183428 | 35.818994387 | 0.104178985 | 4.208949237 | 1.092246400 |

四次新执行均完整、有效，均为 `valid_failure`。三个物理指标与对应保存轨迹完全一致。尤其 S5.6 NMPC 的历史 solver failure 仍然无效；本轮只是将其实际施加序列作为新开环实验独立评价，不能反向洗白历史执行。停止原因为 `bounded_replay_complete`。详见 [P0 summary](../../evidence/control_search_p0/summary.json) 和 [validation](../../evidence/control_search_p0/validation.json)。

### P1 全部 24 个唯一新评价

两个起点为 P0 已独立验证的 S5.6 NMPC 实际控制和 S5.8 PPO 实际控制。P1 在自己的 study 内重新评价起点；pattern 的两次基线请求复用 P1 response 的完成结果，不从封存 study 借用额度。所有下列行均为完整有效执行、原验收 `valid_failure`，无失败执行被剔除。每次 700 个物理步，共 16,800 步。

| 方法 / 请求类型 | 新结果前缀 | 终点 mm | 保持位置 mm | 保持速度 m/s | G | 计费 s |
|---|---|---:|---:|---:|---:|---:|
| response / baseline | 441a6a3f8a40 | 6.120971961 | 6.926833645 | 0.041814094 | 1.090704702 | 1.129696000 |
| response / baseline | 278dfebed8ce | 5.917143774 | 6.618027540 | 0.069612810 | 2.480640498 | 1.079982900 |
| response / finite_difference | 0e6608329290 | 6.194626988 | 7.018238021 | 0.042665985 | 1.133299267 | 1.096831900 |
| response / finite_difference | 98b814b5bfe4 | 5.980072943 | 6.715365975 | 0.039374444 | 0.968722216 | 1.095115300 |
| response / finite_difference | 7742aa420e1e | 6.132626908 | 6.944505052 | 0.041391250 | 1.069562507 | 1.084297700 |
| response / finite_difference | 463b1a4b900d | 6.318762150 | 7.193998388 | 0.043966763 | 1.198338132 | 1.076646300 |
| response / finite_difference | fdd279b11f43 | 6.251038307 | 7.024938720 | 0.041987083 | 1.099354137 | 1.115085100 |
| response / finite_difference | 2b73b667ba11 | 5.792662792 | 6.557420298 | 0.040370222 | 1.018511098 | 1.101310400 |
| response / finite_difference | 972aca608996 | 6.262943170 | 7.111363535 | 0.041276185 | 1.063809241 | 1.106123500 |
| response / finite_difference | 42dd63f0f30a | 6.733629433 | 7.584264209 | 0.042709439 | 1.135471965 | 1.157519000 |
| response / finite_difference | 5a3000c1af5a | 6.134524394 | 6.937064795 | 0.040667089 | 1.033354439 | 1.140264900 |
| response / finite_difference | 407c84d44d74 | 5.911611410 | 6.808591398 | 0.044831075 | 1.241553757 | 1.092035800 |
| response / finite_difference | 9dce6f00e5e2 | 6.299873259 | 7.024374837 | 0.041610423 | 1.080521139 | 1.103693200 |
| response / finite_difference | 523014923cce | 6.518938009 | 7.166239863 | 0.037454712 | 0.872735578 | 1.077536800 |
| response / local_response_proposal | df28c38f5972 | 5.193064009 | 5.193909968 | 0.021090041 | 0.054502039 | 1.128206200 |
| response / finite_difference | 9ad8c033864c | 6.014304303 | 6.704637254 | 0.070460231 | 2.523011534 | 1.109806400 |
| pattern / coordinate | 2d46a0336953 | 10.200439517 | 10.200439517 | 0.057725207 | 1.886260340 | 1.112380400 |
| pattern / coordinate | 92911d85dc13 | 2.630586372 | 4.988603914 | 0.091600432 | 3.580021604 | 1.135113000 |
| pattern / coordinate | 22c805bee8d8 | 8.108973168 | 8.151054616 | 0.047537409 | 1.376870473 | 1.080995800 |
| pattern / coordinate | 6f67f726573d | 4.757258241 | 6.075298214 | 0.053308203 | 1.665410130 | 1.067986700 |
| pattern / coordinate | 3f218fb2c3c8 | 4.229057818 | 5.852510140 | 0.073053528 | 2.652676422 | 1.082275600 |
| pattern / coordinate | 58df4992fe72 | 8.332377620 | 8.376590065 | 0.040965039 | 1.048251942 | 1.091834300 |
| pattern / coordinate | c708275b81e5 | 8.219121752 | 8.219121752 | 0.107317299 | 4.365864956 | 1.073660400 |
| pattern / coordinate | 2488e2f0ec08 | 7.510239751 | 7.510239751 | 0.088110055 | 3.405502768 | 1.090772300 |

表中引用是 evaluation artifact ID 前 12 位，完整 ID、候选/来源引用、控制系数、序列 hash、全部轨迹、逐项验收及预测记录在 [P1 summary](../../evidence/control_search_p1/summary.json)。另外两条请求为 pattern 的缓存基线，新增成本均为 0；没有第 25 次新物理评价。

最优结果引用为 `df28c38f59726d06bc59573eb93fc22294d38089a13565774c77a2801c2ff352`，可继承的精确序列已独立保存在 [best_control.json](../../evidence/control_search_p1/best_control.json)。其 G=0.05450203924159114，绝对速度违反量为 0.001090040784831825 m/s。局部响应提议预测 G 降低 1.0907047020975185，实际降低 1.0362026628559327，方向一致；预测终值约 5.33e-15，实际仍为正。SLSQP 19 次迭代的 success 只说明本次局部子问题求解状态，不是原任务通过；信赖半径由 0.1 N 增为 0.15 N，不构成未知候选下降保证。

| 阶段/方法 | 新物理评价 | 缓存基线请求 | 账本计入的后端数值时间 s | 停止原因 |
|---|---:|---:|---:|---|
| P0 | 4 | 0 | 4.401846600 | 四次有限回放完成 |
| P1 response | 16 | 0 | 17.694151400 | evaluation_request_budget |
| P1 pattern | 8 | 2 | 8.735018500 | evaluation_request_budget |
| P1 总计 | 24 | 2 | 26.429169900 | 有限搜索完成，物理额度耗尽 |

P0/P1 独立 study ID 分别为 `control-search-p0-20261019` / `control-search-p1-20261019`；source freeze 为 `fb9362ba6efab747c85ea679830f1db9c45b2d5e` / `79ef5e80bb0fe6b27774e157aead72da5455caee`。最终 tool_calls 为 8/27，backend_solves 为 4/24，model_calls 和 worker_calls 均为 0；occupied 为空。这里的 worker_calls 是既有账本类别，物理计算已由 backend_solves 计费，不能解读为没有执行物理计算。

既有 state 数值累计（含构建）分别为 5.323114600 s / 27.070329700 s。上表是后端计费时间，不是整个程序 CPU 或端到端时长；进程内局部 SLSQP 的额外耗时没有单独计时。response 和 pattern 的请求上限分别为 16/10，共用 P1 的 24 次物理预算；这是机制验证，不是等预算的性能比较，不能据此宣布算法优越。

P1 首次启动曾因绑定前写入派生 portfolio 导致 dirty source，被 `COMMIT_BEFORE_BIND_OR_MIGRATION` 拒绝，物理执行数为 0。修复将派生导出移到绑定之后，保留 prepared study 和账本；记录见 [prelaunch_boundary.json](../../evidence/control_search_p1/prelaunch_boundary.json)。没有把工程启动失败当作科学候选失败或重置预算。

## D. 测试、审计和运行方式

最终相关九模块回归：**100 passed，0 failed，0 skipped，39.050 s**。测试包括不合法/错位控制、身份不匹配、有效性优先、两种搜索的预算及失败路径、首次成功停止的合成夹具、缓存恢复、旧 scoped claim 兼容及禁止推论。结果记录在 [verification.json](../../evidence/control_search_p2/verification.json)。

在本 worktree 的 PowerShell 中使用现有环境（未安装/升级依赖）：

```powershell
$env:PYTHONPATH='.;tests/research;C:/Program Files/MATLAB/R2024a/extern/engines/python/build/lib'
$env:SOROSIM_ROOT="$env:TEMP/softrobot-sorosim-24d573a3"
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
& D:/softrobot-agent/.mainline5-env/Scripts/python.exe -m unittest tests.research.test_candidate_portfolio tests.research.test_local_control_search tests.research.test_evidence_policy tests.research.test_control_correction tests.research.test_task_analysis_contract tests.research.test_agent_feedback tests.research.test_s58_agent tests.research.test_s59_guidance tests.research.test_s55_refinement -v
& D:/softrobot-agent/.mainline5-env/Scripts/python.exe evidence/control_search_p1/audit_saved_results.py
& D:/softrobot-agent/.mainline5-env/Scripts/python.exe evidence/control_search_p2/audit_saved_evidence.py
git diff --check
```

两份 audit 脚本不新增科学计算，核验/更新的是独立审计摘要，不改写历史归档。P1 恢复审计重新产生 26 个请求，全部命中 Store，最优结果一致、state/ledger 未变；24 个唯一结果全部有效。P2 产生 30 个保存证据视图，并检查 S5.10 粗细积分失败边界；11 个历史序列通过更严格的 engine time/有限值/模型身份复查且控制值不变。

真实 pilot 使用 `python -m tests.research.control_search_pilot --stage p0` 和 `--stage p1` 显式启动；默认 unittest 不发现或运行该驱动。`--audit-only` 仅导出历史 portfolio/来源摘要。当前 study 已停止封存，原 ID 再次启动会报告 sealed，不会重新开展科学实验；后续新研究应使用新配置和独立预算。MATLAB Engine 路径用于现有准备/绑定接口，本轮没有 MATLAB 数学积分计算。

归档核验：P0 54 个成员，SHA256 `a8728e83a1884535c9c1d924d1c2112ec68ed9c04b0543577f2ef999cf62e4cb`；P1 211 个成员，SHA256 `34bd056a5e6f614d77ddf6b5e0574c1af918ff79e929147848c5736838fc2562`。保存的 source_audit 前后 hash 相同。验证覆盖相关模块，未宣称运行整个仓库所有测试。Windows 的临时文件夹权限限制通过经自动审批的本地提权运行相关夹具解决，没有更换科学依赖。

## E. 代码与科学边界

`tasks/`、`extensions/`、`matlab/`、`mujoco/`、`tools/research_tasks.py`、`tools/research/agent.py` 和 S5.6/S5.8/S5.9/S5.10 原 evidence 相对基线均无修改。旧 task-gap、归档读取、配置加载、独立接受规则、预算、Store 和调度继续复用原实现。新增生产模块分别只负责历史候选视图、局部搜索或证据推论；没有新通用框架。测试和审计夹具不作为科学证据。

P2 的七类为 MODEL_WITNESS、MODEL_EXCLUSION、NUMERICAL_DIAGNOSTIC、PHYSICAL_OBSERVATION、EMPIRICAL_COMPARISON、STATISTICAL_EVIDENCE、UNVERIFIED_HYPOTHESIS。分类不构成统一可信度排序。模型见证/排除只在已声明模型和样本范围成立；粗网格见证遇细化失败降为诊断。物理观察只支持该次完整独立执行。统计对象仅记录方法、样本及不确定度，状态为 reported_not_independently_verified。

五个诊断假设为 CONTROL_SEARCH_INCOMPLETE、MODEL_PREDICTION_UNRELIABLE、CONTROL_PARAMETERIZATION_LIMITED、DESIGN_LIMITATION_POSSIBLE、SOLVER_OR_NUMERICAL_ISSUE；目录列明可用证据、区分实验、适用范围及禁用结论，概率为 null。失败优化/KKT、不可靠局部响应、瞬时制动或静态敏感性均不支持结构不可行、全时域成功、适配后动态改善或未知候选仿真下降保证。`prospective_guarantee` 固定为 false。缺模型证书仍允许合法经验搜索，但不能越过既有 Plan/预算授权。

## F. 本地提交与工作树

本轮按 P0 → P1 → P2 分阶段实现并保留必要修复。实现先冻结再运行相应实验，证据随后单独提交，以保持 source freeze 可追溯。

| SHA | 提交说明 |
|---|---|
| fb9362ba6efab747c85ea679830f1db9c45b2d5e | P0: recover bound historical applied controls and candidate portfolios |
| 64b9ebd599912db3d797da5a430c65919c6ae99a | P0: archive four independent replays and exact historical pairing |
| 16d3bfb9a0848086a347c6aa3154adbc749b13b2 | P1: add bounded response and pattern control search with Store recovery |
| 79ef5e80bb0fe6b27774e157aead72da5455caee | Keep derived audit exports after source binding and retain prelaunch failure |
| d653fb756e18dba7840899da18ddf7086e521d95 | P1: archive 24 bounded evaluations and restart-without-replay audit |
| 9927d4f2051d424ecc5e6c6e6bd041fcb5ef8eea | P2: add scoped evidence policy and diagnostic hypotheses with saved-evidence audit |

本文作为最后一个文档提交单独提交。交付时目标 worktree 应为 clean，所有本轮相关文件均已提交；根目录其他用户未跟踪文件不属于本轮清理范围。**没有执行 git push、reset --hard、强推、改写封存历史或清除用户工作。** 本地领先远端的最终提交数和本文提交 SHA 在交付消息中给出；该状态只描述交付检查时刻。

## G. P3 接入接口与尚缺工作

P3 可在 `agent.py` 接收提议后，先从 Store 解析真实工具 artifact，再用 `summarize_evidence(value, reference, refinement=...)` 生成视图；对拟议推论调用 `check_inference(summary, inference, target=...)`。target 应给出 task/candidate/model/design/operating_point/covered_samples 全部身份及范围，任何缺失或不匹配都拒绝移交结论。对于合法的新经验搜索，使用 `inference='empirical_search', legal_candidate=...`；合法性必须来自现有确定性候选校验。

```python
# P3 调用示意：value/reference/target 均来自已解析的可信 Store 对象。
summary = summarize_evidence(value, reference, refinement=refinement)
decision = check_inference(summary, proposed_inference, target=target)
if not decision['allowed']:
    # 返回明确拒绝原因供 Agent 重新提议；不得提升结论强度。
    ...
# allowed 后仍走既有 Plan 校验、授权、资源预留、dispatch 和独立接受规则。
```

目前缺少 Agent 提议字段与 inference/target 的确定性映射、可信 artifact 解析接线、拒绝/修订交互、审查记录持久化和端到端执行前回归测试。P2 的纯函数以已解析可信工具结果为前提，不能直接信任 LLM 自报的 verification_status 或身份；它也不替代证书原有验证器。本轮未修改 agent.py、未创建多智能体流程、未请求 provider，P3 仍为 `NOT_RUN`。
