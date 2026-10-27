# BF7：三目标共享结构探索

基底为 2026-10-27 核对并 fetch 后一致的本地与远端 `integration/research-next`：`a1566b91a387316405bdb2fc79eb8a087ea20e8a`。独立分支 `research/bf7-shared-structure-benchmark`，独立 worktree `.worktrees/bf7-shared-structure-benchmark`。不修改基底，不从 B 历史研究分支派生，不读取或导入 BF4/BF5/BF6 成功设计、控制或私有 Store。

Codex 组织有限研究，所有科学工作交给原 Study 工具；LLM Research Agent、Provider、PPO、NMPC、私有物理/数学搜索均为零。新增运行入口只编排原工具、保存与汇总现有结果。

## 接口审计与范围

- `tools/research_tasks.py` 将每个 Reach 自身的终端位置、保持窗位置和保持窗速度转换为带各自容差的 norm constraints；独立 `evaluate.reach` 和原 Reach/Hold 组合验收分别检查终点、完整执行、保持窗及张力/求解有效性。
- `tools/research/task_constraints.py` 的分析适用性针对一个候选的实际任务和采样点；`analysis.py` 验证该候选、初态、物理输入、任务要求、完整覆盖、方法授权与预算，数学输出不能成为物理验收。
- `search.py` 的 `family_mixed_search_v1 / task_violation` 只在 `base_configuration` 的单任务上构建模型、求 CONIC 和排名，**不遍历 `task_conditions`**。因此本实验的搜索只负责在第一个任务上提出至多三个合法结构，不宣称它实现了原生三目标优化。
- `optimal_capability.py` 保留原 GVS/CONIC 方法准入和模型/内部求解计数。每个单任务模型构建加一次 norm CONIC 为两单位；预计三结构 × 三任务 = 18 单位，总授权上限 24，不要求耗满。没有新优化器或新隐藏评分。
- `config.py` 已冻结支持两或三个 `task_conditions`；`initialize_control(condition_id=...)` 调用 `conditions.py` 在同一物理结构上产生任务绑定候选。每个条件均可独立初始化和优化控制。
- `conditions.py` 的联合 SELECT 检查全部冻结条件、实际完成且非替代来源的物理回放收据、原验收及其评价/profile/raw 绑定、相同物理结构和离散化。`core.py` 已支持把三条独立证据列表传给 select；少一个目标、结构不同或未读取证据都不能 SELECT。

现有接口足够执行本轮，不新增 Registry、数学框架、物理执行器或任务评价器。

## 计算前冻结的 BF7 v1

用途是同一条软臂上的原 10 g 末端刚体，分别定位到三个传感器测点；不要求方向、真实接触或实际硬件能力。

| 条件 | 世界坐标目标（m） |
| --- | --- |
| positive_high | (0.285, 0.035, 0.185) |
| negative_low | (0.275, −0.040, 0.135) |
| central_high | (0.295, 0, 0.215) |

三次分别从相同 seed17、全部候选关节位置/速度为零开始，时长 0.6 s、步长 1 ms、控制/采样周期 20 ms。终点误差 ≤10 mm；最后 `[0.54,0.60] s` 的四个 inclusive 样点同时满足误差 ≤10 mm、实际世界系速度 ≤30 mm/s。完整 600 步、采样覆盖、原 evaluator、张力硬界和求解有效性均需通过。有限采样不构成连续时间或重复性证明。

沿用 `reach_hold.json` 的世界系、安装、重力、无外力和非接触地面配置，沿用族域的 10 g 刚体、质心与完整惯量。两段、六条独立理想张力腱，0..8 N，原材料和截面；`distributed_consecutive` 路由规则固定，12 cells/segment，原 MuJoCo 1.2 接口和 serial bending cells 1.0 模型。实际科学结构全部由本分支原 `family_space_v2` 生成。

预筛只改变段长，两个长度均在原合法子域 `[0.10,0.16] m`；原工具从公开默认值启动。它们改变长度分配、总长、弯曲柔度与几何可达范围。材料、近远段模量及腱路在本轮固定，不能据此声称已经识别其敏感性。先验证有限长度结构效应，后续扩大变量域需要独立冻结。

对每个提出结构，分别调用原 CONIC 对三个实际任务重新优化合法控制，读取各自完整 constraint/sample coverage 和 affine replay。仅三个求解均有受支持的有限结果时，确定性汇总 `V_BF7(d)=max_j trajectory.replayed_violation_j`；否则共享分数为未决。符号值是原各任务的最大归一化超限，越小越好，负值仅代表局部模型样点有余量。局部 GVS 物理一致性未验证时明确保留限制。

物理候选先选完整共享分数最小的结构，平分按提案顺序；比较结构固定为第 0 行（若它已是最优，则选下一完整排名结构）。两种结构都使用相同新鲜 0.2 N 初始化与充分的独立控制搜索，不把固定控制响应或未充分调控制的弱基线冒充结构能力。

## 预算、续算与停止

权威配置为 [v1 协议](../../configs/research/bf7_protocol_v1.json)、[预筛 Study](../../configs/research/study_bf7_v1_prescreen.json) 和两个独立多条件 Study `study_bf7_v1_best.json / study_bf7_v1_peer.json`。原共同族域默认值和输入文件由 Study 解析器一次冻结，不借用历史余额。

每结构每目标首轮至多 101 Native 回调、4 轮 response、1 次完整独立回放。4 knots 为 `[0,0.2,0.4,0.58]`，24 系数，原 v2 response；差分 0.02 N、初始半径 0.2 N、系数域 8 N、内部余量 0.02，实际输入仍被 0..8 N 限制。全时域张力控制不是只修补终点；独立验收阈值保持原值。

初始 Study 同时封顶一次可选续算的总额度，但未授权自动耗用：仅完整可靠的真实失败、相对新鲜起点最大归一化超限至少下降 5%，且末段反馈仍持续改善时，才可在读取结果后**另行提交续算配置**，至多增加 100 回调和一次独立回放。保留同一个 Study 累计账本，不修改预算、不转移旧余额。已通过条件不再优化；原工具联合验收可组合该 Study 内此前通过与续算后通过的条件。

单目标累计硬上限 201 回调、2 独立回放、121,800 积分尝试；两个结构三个目标合计至多 1,206 回调、12 独立回放、730,800 积分尝试。原 Store Native 分析入口单位与内部回调分别列账。先阶段独立通过即联合 SELECT；不值得续算或续算结束仍失败则 STOP。另一结构是独立授权的能力比较，不在已通过 Study 内继续搜索。

有限失败不证明结构不可行。不通过时不更改 v1 任务、容差或成功定义。若另立候选版本，须保存 v1 失败、成本与科学原因并先冻结新版本；本轮不会自动开展正式三策略对照或合入主线。

运行入口：`python -m tests.research.bf7_shared_structure prescreen`，随后 `physical best`、`physical peer`；只有另行提交续算配置后才能运行 `physical <role> continuation`。所有科学调用都来自该入口内部原 `core.dispatch / analysis.dispatch`；审计只读取原 Store。

结果、真实成本和最终 Benchmark 状态将在计算完成后追加。
