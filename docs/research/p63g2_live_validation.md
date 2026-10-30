# P6.3-G2：短窗口真实验证

**本次未通过最终真实验收：Main 提出了结构—控制联合研究假设，但未选择 search action，也未启动 Main 的 Search Worker。** 离线接口和真实小型 Worker 接入测试通过，不能用它们或 Operator 准备计算替代这个缺失的自主执行证据。

实现基线、字段和离线验收详见 `p63g2_mixed_search_intent.md`。运行代码冻结于 `e86097d`，独立 Study `p63g2-m3-mixed-search-sol-20261030`；整个真实窗口没有换代码、模型或提示，没有重开 Study 或追加预算。Main/Reporter 均保留 G1 的 `gpt-5.6-sol / none`。

## 验收结论

| 项目 | 实际判定 |
|---|---|
| B1 科研意图 | 已观察。Main 根据有效失败提出改变几何、路由或段参数并逐结构重优化控制的可反驳假设，明确位置—速度权衡和独立验收要求。 |
| B2 合法联合搜索请求 | 未证明。没有 research_route(search) 或 research_plan(search)，没有新接口编译绑定。新精简 search Schema 的加载和编译仅由实际 SDK/Mock wire 验证，未在此真实 Main 窗口加载。 |
| B3 Main 真实 Search Worker | 未通过。Main 新数学评价、物理评价、结构搜索与 Worker 均为 0。准备 Worker 和隔离测试 Worker 均明确排除。 |
| B4 数值语义 | 无 Main search 结果可验收。真实准备数据、控制设置、实际迭代/回调、费用和范围已独立保存；没有数学改善→物理通过或 SELECT 的升级。 |

## 准备数据与所有权

新 Store 从空状态开始，用原生成工具重建 G1 第 4 次合法生成请求的失败候选，重新初始化 baseline，再做新数学优化和新独立 Replay。没有复制旧科学结果引用、控制轨迹或 Store。新 `canonical_task`、FamilySpace、analysis_protocol、control 与 G1 解析后相等：0.50 s、最后 0.05 s 保持、0.01 m 位置阈值、0.02 m/s 速度阈值，积分 0.0005 s、控制/采样 0.01 s；原初态、物理模型和最终保真度保持。

以下均为 **Operator 准备**：

- 候选 `8469268c84c063f6b2e355919119f5c68044f3362d10efd1c552b3415e275f6c`；两段六腱、原长度/材料/截面，基座三根全长 + 三根近端的合法分组。
- baseline `7b8217285bde1525e84f961e3b42ccf97188baa9e835687f1aa8d3d2bc9561ed`，候选原预张力来源。
- Native 结果 `345ce1d4e46f328ff4bcb64f0814a75b5f54a990a2e59ecc2bf2ac2f94d0b7e6`，pattern，四 knot `[0,1/6,1/3,0.5] s`，80 iterations / 120 callbacks。实际 29 次优化迭代、120 callbacks，以 `evaluation_request_budget` 结束，不是隐藏的 16 次限制。
- 优化 source `e2336ba090ee92fde8715cbf8a748632b3bf33330686ec4bc753aaf4805beb3c`；独立结果 `d51b5c9249fd8eca03c2a474b6a4c8736f64b87bec9aaf1e88e245991f09325a`。两份 Reporter 解释均 available，且在首个 Main 实际 wire 中可见。

| 准备结果 | 数值与范围 |
|---|---|
| 初始 J → best-found J | 20.4267857531 → 11.8164398768；无收敛、全局最优或不可行证明 |
| 独立终点误差 | 0.1264496051 m，失败（限 0.01 m） |
| 独立保持最大误差 | 0.1281643988 m，失败（限 0.01 m） |
| 独立保持最大速度 | 0.2536984073 m/s，失败（限 0.02 m/s） |
| 原验收 | valid_failure；完整执行、保持覆盖、张力边界和 solver errors 检查有效；全部三项性能指标失败 |

初始化时无 Main Plan，准备记录 `decision_owner=Operator`；不能把上述优化或失败后的结构选择算作 Main 自主研究。执行指令明确说明该所有权。当前对象投影的 origin 显示 unknown，是既有 provenance 投影未识别此准备来源的展示限制；原候选 provenance、分析 origin 和准备记录保留 Operator 来源，不按 unknown 反推 Main 所有权。

## 真实请求轨迹

| 总序号（含 Reporter） | 行动与反馈 |
|---|---|
| 1–2 | Operator 准备结果的两个真实 Reporter 请求，均 HTTP 200、available，计入 12 总量。 |
| 3 | Main 精确过滤 Knowledge 时填写自然语言 structure/failure_type，得到空结果。实际反馈包含本次新增合法过滤值和读取进度；没有历史 trace 正文读取或重复读取两条程序经验。 |
| 4 | Main 提出有意义的 mixed structure/control 假设，但用 diagnose，并误放额外顶层 selected_candidate。Schema 拒绝，反馈明确要求移至 decision.selected_candidate。无科学费用。 |
| 5 | Main 自行修正，合法 diagnose；它只记录假设，未启动计算。没有由 Operator 补参数。 |
| 6 | Main 选择 ScientificQuestion v2 的 structure_parameter_effect/reoptimized_task_capability，填 `/parameters/geometry`、四 knot、4 iterations、120 callbacks；因路径不在原有效参数目录返回 unsupported。 |
| 7–8 | 查询候选 `/parameters` summary，然后填 `/parameters/spans/0/anchor_angle_offset_rad`；仍非注册数学参数，未执行。 |
| 9–10 | 读取 `/parameters` full，改填 `/spans/0/guide_angle_offset_rad`；仍被同一注册路径准入拒绝。 |
| 11–12 | 进入原保护收尾。首次索引请求把 64 位 artifact id 抄错，原 Schema 拒绝；第 12 次修正并本地取得两项新结果引用索引。没有后续 Provider 请求确认这份索引正文，未形成 Main STOP。 |

约第 8 次只读检查时，无未封口 calls、pending Worker 或执行环境故障，按授权继续剩余窗口。三次 unsupported 均未消耗正式数学评价。Main 的四次迭代是其显式选择，未编译到 Worker；不能将它与 Operator 的 80/120 准备执行混记。

## 实际 Schema 与未解决问题

原能力目录在探索阶段明确提供 Design/search 为 available，也提供 `research_route` 的工具/行动切换入口；但当前加载的精确 Plan 始终为 diagnose（请求 3–10），收尾为 stop（11–12）。诊断完成后实际加载 ScientificQuestion **v2**，包含 control_search_effort、没有旧 search_strategy/requested_budget。实际 Schema 和 wire 引用保存在 `p63g2_live_audit.json`，不是仅检查 Python 编译返回值。

因此本轮没有观察到“新 Mixed Search 请求再次因内部 MATHEMATICAL_ANALYSIS、FamilySpace identity 或 Native operating_point 出错”，因为 Main 根本未提交该请求；也不能由此宣称这些缺陷已经在真实 Main 搜索中被验证消除。它们目前有离线原请求、原准入、Mock wire 和真实隔离 Worker 的证据。

新增/遗留限制：

- diagnose 的局部 execution_entry.interface 仍硬编码 `scientific_question_v1`，而同一后续实际 Schema 和上层 analysis_handoff 已为 v2。Main 第 8 次实际使用 v2，未观察到该标签使合法 search 执行被拒，但标签不一致必须记录。
- 默认加载 diagnose 并指引其进入单候选问题，可能影响后续行动选择；本次不能把未进入 search 全部归因于模型，也没有因果对照。
- 对未注册结构路径，现有 C2 返回 unsupported，但 Main 连续猜测三个路径，没有转向注册参数目录或合法 search。新 Mixed Search 能力与单参数 T2 比较的发现/交接边界，仍未获得有效的真实自主恢复证据。

按任务对范围和冻结运行的限制，只记录这些未影响原 mixed-search 合同合法执行的新观察，没有在真实运行中调提示、代提交 Plan 或顺手扩建路由器，也未为了获得成功而再开 Study。

窗口关闭后的代码复核另外修正了新代理分支的一处语义：CONIC task_violation 会在仿射模型内求解控制，不能与静力/保持输入代理一并标为 not_optimized。最终接口要求显式 proxy_optimized，保留原 CONIC 准入且不换成 Native；未授权仍拒绝。该修正仅作离线合同/Mock 回归，没有重开真实 Study；上述真实轨迹仍对应 e86097d，Main 未触及该代理分支。

## 成本、停止与保存

| 项目 | 实际记录 |
|---|---:|
| Provider Main / 准备 Reporter / 总数 | 10 / 2 / 12（上限 12） |
| HTTP 失败实际发送 / 自动重试 | 0 / 0 |
| prompt / completion / total tokens | 185992 / 3310 / 189302 |
| reasoning_tokens / 金额 | 0 / 未提供，未知 |
| Provider elapsed / ledger.wall_s | 194.8610000 / 209.4646393 s |
| 最大真实请求体积 | 79957 bytes，低于原 1 MiB |
| public operations / backend launches | 10 / 1 |
| Operator Native build / rollouts / steps | 1 / 120 / 120000 |
| Operator Native forward / kernel / charged Worker | 12121 / 11.9498414 s / 13.3113950 s |
| Operator 独立 Replay build / rollout / steps | 1 / 1 / 1000 |
| Replay forward / kernel / charged Worker | 101 / 0.2754555 s / 1.2922443 s |
| 准备合计 build / rollouts / steps | 2 / 121 / 121000；attempted steps 相同 |
| 原 numerical_s / construction_numerical_s | 15.1385352 / 0.3890162 s |
| Main 数学 / 物理 / mixed search / NMPC / RL / T2 | 全部 0 |

Kernel 已包含于对应 Worker 费用，不再次相加。ledger.worker_calls=0 是原账本分类，不表示没有准备子进程。隔离测试期间两次小型真实接入合计 2 builds、4 rollouts、2400 steps，属于开发测试，另列于实现报告，不计入当前 Study 或 Main 成果；其他模型测试为 Mock。

12 次后 pending、unconsumed response、未封口 calls 均为空；两准备 Worker 均 returncode=0、termination_confirmed=true。最后监督边界状态为 ready，随后仅调用原 `engineering_count_budget_closure` 记账关闭，状态 stopped，`model_stop=false`，Provider 仍为 12。该关闭不是 Main 科学 STOP，没有 SELECT 或完整任务通过。

原 Store 和原模型/序列/数组保留在本 worktree 的 `runs/research/p63g2-m3-mixed-search-sol-20261030/`。公开精简审计保留每次 Main 请求、原反馈与实际 Schema、编译/Worker 记录、来源和费用；不包含密钥或模型不透明推理。至此停止，不延长窗口、不重新启动验证或继续 80 次可行解研究、不合并其他分支。
