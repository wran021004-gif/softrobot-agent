# Base-only 跨任务 Benchmark 可行性探索（2026-10-28）

六项均找到新 Base-only 空间下的独立可行见证，全部已 SELECT / STOP。M1/M2 由原联合选择规则关闭；其余由各自注册评价器关闭。M3 仍是本轮冻结的 development draft，不宣称已经批准为正式 Benchmark。

本轮是 Codex 组织的开发性探索；未启动仓库 LLM Research Agent、DeepSeek Provider、NMPC 或 PPO。未改变冻结目标、容差、时间、重力、外力、负载或验收算法。每根实际构建腱路均复核为 `fixed_base/start`，所有结构均为两段、六腱、每段 12 cells。完整结构、控制及搜索过程仅保存在研究所有者本地私有 Store。

**Benchmark 状态表。** 下表任务均在 `tasks/`；版本均为原继承的 `1.0.0`。结构空间标记 R/T/L 的完整身份见后表。私有复核编号 W1–W6 的映射与内容身份在后表；公开类别不发布完整见证设计。

| ID | 冻结 TaskDefinition | Base-only 空间 | 已验证结构 / 私有索引 | 实际控制方法 | 独立结果及原指标 | 科研成本：提案 / 数学请求 / Native 回调 / 回放 / 积分尝试 | 最终判断及后续 |
|---|---|---|---|---|---|---|---|
| M1 | `bf7_shared_reach_v1_{positive_high,negative_low,central_high}.json` | R | 两段六腱，Base-only 分布锚点；W1 | `initialize_control` 0.2 N 常值起点；`mujoco_direct_control_v1` / v2 response | accepted；保持位置约 9.899983 mm；速度约 29.700000000 mm/s | 2 / 7 / 2410 / 6 / 1449600 | 完整可行见证；优先联合设计候选；须另冻等机会对照 |
| M2 | `bf2_multidirectional_hold_frozen_v1_{zero,positive,negative}.json` | R | 两段六腱，Base-only 分布锚点；W2 | `initialize_control` 0.2 N 常值起点；`mujoco_direct_control_v1` / v2 response | accepted；保持位置约 9.909576 mm；速度约 19.999948823 mm/s | 2 / 6 / 1778 / 5 / 1248100 | 完整可行见证；优先联合设计候选；外力及保持标准有辨别潜力 |
| M3 | `reach_hold_b3_050.json`（draft） | R | 两段六腱，Base-only 分布锚点；W3 | `initialize_control` 0.2 N 常值起点；`mujoco_direct_control_v1` / v2 response | accepted；保持位置约 9.948406 mm；速度约 19.887343774 mm/s | 2 / 3 / 1176 / 2 / 1178000 | 完整可行见证；开发性联合设计候选；先批准正式协议 |
| M4 | `bf4_tracking_direction_change_v1.json` | T | 两段六腱，公开 full-span 类别；W4 | `initialize_control` 0.2 N 常值起点；`mujoco_direct_control_v1` / v2 response | accepted；全程最大误差 11.987763 mm | 1 / 1 / 105 / 1 / 63600 | 完整可行见证；优先作为控制能力校准；尚无结构优势证据 |
| M5 | `bf5_position_tool_axis_v1.json` | T | 两段六腱，公开 full-span 类别；W5 | `initialize_control` 0.2 N 常值起点；`mujoco_direct_control_v1` / v2 response | accepted；位置 7.923372 mm；轴角 2.972778° | 1 / 1 / 54 / 1 / 33000 | 完整可行见证；本轮最易；适合作位置/方向控制校准 |
| M6 | `bf6_sensor_oriented_tracking_v1.json` | L | 两段六腱，Base-only 分布锚点及材料调整，真实 20 g 刚性工具；W6 | `initialize_control` 0.2 N 常值起点；`mujoco_direct_control_v1` / v2 response | accepted；位置 11.937423 mm；轴角 9.949874°；600 步无环境接触 | 3 / 4 / 628 / 3 / 377851 | 完整可行见证；安全初始化与结构/控制联合设计候选 |

**原验收与边际。**

| ID | 冻结物理与验收 | 最紧独立裕量 |
|---|---|---|
| M1 | 0.6 s；10 mm / 30 mm/s；三目标同结构 | 位置 0.100017437 mm；速度 0.300000000 mm/s |
| M2 | 0.35 s；10 mm / 20 mm/s；三外力条件同结构 | 位置 0.090424037 mm；速度 0.000051177 mm/s |
| M3 | 0.50 s；10 mm / 20 mm/s；末 50 ms 停稳 | 位置 0.051593831 mm；速度 0.112656226 mm/s |
| M4 | 0.6 s 全程，12 mm | 位置 0.012237276 mm |
| M5 | 0.6 s，8 mm + 3° 有向工具轴 | 位置 0.076628080 mm；角度 0.027222478° |
| M6 | 0.6 s，12 mm + 10°，20 g，逐步无环境接触 | 位置 0.062576751 mm；角度 0.050125968° |

M1 三目标的保持位置 / 速度分别为：positive_high 9.677934 mm / 29.699997158 mm/s，negative_low 8.726240 mm / 29.120119884 mm/s，central_high 9.899983 mm / 29.700000000 mm/s。M2 zero 为 8.966762 mm / 19.812257395 mm/s，positive 为 9.909576 mm / 19.999948823 mm/s，negative 为 9.799928 mm / 19.600000000 mm/s。标量原精度及 terminal/holding 分项见 `evidence/base_only_benchmark_feasibility_20261028/summary.json`。

部分首次通过裕量很小，尤其 M2 positive 的速度。按照首次完整通过即停止的授权，没有继续为通过组增加优化。这里证明规定样本和本次独立执行通过，不声称扰动鲁棒性、重复性、连续时间位置/方向保证、全局最优或较弱结构物理无解。BF6 的无环境接触则确实逐独立物理步检查。

**冻结身份。** 实际运行配置为 `configs/research/study_base_only_m{1..6}_v3.json`。协议及额度为 `base_only_campaign_budget_v2.json`。R 复用 Stage 0 Base-only 文件；T/L 使用既有单层组合方式保留原控制域和原 20 g 物理配置，只增加 Base-only 规则及新的 FamilySpace 身份。

| 空间 | 文件 | 实际冻结的 scoped FamilySpace identity |
|---|---|---|
| R | `configs/research/family_space_stage0_base_only_v1.json` | `946326b03ecd16c21dd1c1b6580c1ef3c34402bce1dc7e4e2a914307ef290271` |
| T | `configs/research/family_space_base_only_tracking_v1.json` | `034e32256d365bb589e5c2b3016e26e4cd54d041d66a5d2fb2948fe62bb215d2` |
| L | `configs/research/family_space_base_only_sensor_v1.json` | `59981dc09cf265117924b9dfa4fa05d9134efb1867cdada15dbf17045be6cbd3` |

三空间均为 `conditional_rules=base_only_consecutive_spans_v1`；执行范围固定两段六腱。公共域允许近段 0.08–0.24 m、远段 0.06–0.20 m，Young 模量各为 2–15 MPa，腱路半径 14–23 mm，终止站点 0.8–1.0；具体截面/角度/导向点合法性仍由原生成器、几何和编译器判定。本轮没有扩大段数、腱数、截面类别或离散网格。BF4/BF5 的保持/末端速度权重及其专用 recipe 的零速度权重均保留；BF6 保留原零权重域和 0.020 kg、COM、完整非对角惯量及工具位置。

`summary.json` 按项保存 Study、规范化任务、任务源文件及继承源身份、各 condition 的任务身份、实际独立验收任务身份。源 TaskDefinition、canonical task 与候选按具名零初值展开后的 effective task 采用各自身份，不能混称同一个哈希。

| ID | 实际根任务 identity（完整 condition 身份见 JSON） | Study identity |
|---|---|---|
| M1 | `bba6b2817da1feb38893287e811964f0ff935c68f6a005456e852bb63c38c8fc` | `430a4927e42b72d5b1dc1085eecaca74ae13c395c1fe198705abc5f4a2e3338a` |
| M2 | `fc2e65f7d9e82f5eb71c9bd479a89477ad3980e6899fba4d55d99cbf93e7e097` | `93d006fbe3a65c9dd5dbecf49c6e2c190ff43c80d3c58b394e5ab97ead1efc8a` |
| M3 | `a0e6777f4494fb3762b93dc6463a626ae3dc4884a416681181bcaf5579f9b234` | `139ad6a2b606665a139a8613bffd76e38bf97c19a577ce11da16ae16feffa642` |
| M4 | `e41a4600feefe39614b7f660147208a73373d1f5f6fde23a0790a0a13dde472c` | `3d6ab5e460d27cb651fe0a5cae1fb5f37b30dc56ca75fdea9d3eb5c837f00c09` |
| M5 | `17de11a26ef7c7ecadd833f4ccb0f12036b0ef113061369c80b4e1e08f2bf14a` | `f39dc9c47a13c12c223e0567bee5516e139ecdb4741c94ee1b55a9cb905621a5` |
| M6 | `43d086056e1c704b00ce4762ae9baaef6526750d2ed15b57e59d8b309019ef45` | `2276e4a718685befb2306554e41eff369e6aedbe74785963bd6d1f53777a084a` |

**预算与真实成本。** 预算以实际原时间步换算：M2/M3 为 0.5 ms，其余为 1 ms。每次 Native 请求先保守保留回调上限乘完整时域积分步数，每次 replay 先保留完整步数加一个失败调用槽；原 Study 数学次数、回调和 backend 上限仍同时有效。累计上限按任务冻结，不能通过换 Study 重置。

| ID | 任务步数硬上限 | Study 数学请求上限 × 单次回调上限 | 独立回放上限 | 全部最坏尝试上界 | 实际尝试 | Native kernel s | Store numerical s | operation driver elapsed s |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| M1 | 8,000,000 | 16 × 800 | 100 | 7,740,100 | 1,449,600 | 138.259 | 157.159 | 204.173 |
| M2 | 8,000,000 | 14 × 800 | 100 | 7,910,100 | 1,248,100 | 119.300 | 135.376 | 173.625 |
| M3 | 4,000,000 | 4 × 800 | 20 | 3,220,020 | 1,178,000 | 110.762 | 119.138 | 125.678 |
| M4 | 2,000,000 | 6 × 500 | 20 | 1,812,020 | 63,600 | 6.254 | 9.113 | 10.790 |
| M5 | 3,000,000 | 6 × 800 | 20 | 2,892,020 | 33,000 | 3.114 | 5.842 | 7.321 |
| M6 | 5,000,000 | 10 × 800 | 20 | 4,812,020 | 377,851 | 37.298 | 47.509 | 54.257 |

总计：按任务计结构提案 11 次，数学请求 22 次，Native 回调尝试 6,151 次，独立回放 18 次（12 accepted、5 valid_failure、1 incomplete）。物理积分调用尝试 **4,350,151 / 30,000,000（14.5005%）**，剩余授权 25,649,849 步不再使用；六项首次见证均已完成。确认完成物理步 4,350,150；BF6 数值失败回放的最后一次调用计入尝试，其内部完成状态未知，没有填成零或重发未知请求。当前所有调用的尝试计数可确定，累计尝试下界与上界一致；没有未结保留或 pending。

活动科学阶段为北京时间 2026-10-28 12:48:23–13:04:25，历时约 961.531 s，含 Codex 判断、工具间隔和进程开销；operation driver 区间累计 575.843 s。六个活动 Store numerical 合计 474.137 s；另有零积分预检 Store 的构建 numerical 0.736 s。Native kernel、driver、Store numerical 是相互包含/不同口径的时间，不能再相加当总成本。M6 初次失败 Native 的 kernel 时间字段缺失，该列只加已记录值；driver 和 Store 时间仍保留该次开销。

Provider 请求与其货币费用为零；仓库 Research Agent、NMPC、PPO 均未执行。Codex 自身的模型/编排服务使用成本不在仓库 Provider 账本中，未获得可核对货币明细，不能把 Provider 零费用解释为整项研究零成本。

**研究决策与瓶颈。**

六项最终均通过，未留下整体 not_run 或 unresolved。探索过程中的失败和不完整执行仍保留：M2 的 full-span 候选累计 1,000 回调后独立位置 14.001 mm、速度 28.003 mm/s；M1 full-span 的 central_high 累计 1,200 回调后独立位置 26.178 mm、速度 78.549 mm/s；M3 full-span 累计 1,000 回调后独立位置 14.587 mm、速度 29.201 mm/s。这些是有限搜索下的真实违反量，不能推成结构不可行。合法分布锚点候选在相同任务及 12-cell 网格下分别重新优化所有必要控制，并重新独立验收。

M2 negative 曾在速度阈值上方约 8.96e-16 m/s，被原严格 evaluator 判为 valid_failure；没有修改阈值、舍入成通过或抹去该记录。后续仅用既有 `safety_margin_fraction` 增加内部搜索裕量，使用同候选既有输出源续算，最后独立通过。其他续算也只使用原工具返回的同候选完整 schedule，重新绑定完整时间窗与原输入界；没有手工求出或注入隐藏成功张力数组。

M6 原默认结构的低张力起点在 0.225 s 触地，Native 返回 execution_incomplete；独立回放随后发生数值失败，原任务验收为 incomplete。材料调整使全时域计算能完成；其 full-span 候选在累计 476 回调后出现工具/位置联合停滞，独立位置 18.603 mm、轴角约 15.508°。再改变合法锚点分组，重新从工具初始化的低张力起点优化，最终通过完整有向轴任务、真实负载绑定和逐步无环境接触评价。这里区分了初始化不完整、有效任务失败和可行见证；没有把去掉负载或只达到位置当成扫描成功。

M5 是本轮最容易的任务（54 Native 回调 + 一次回放），M4 也在公开固定结构下较快通过（105 回调 + 一次回放）；目前更适合校准控制优化。M1/M2 与 M6 更适合作联合设计候选，M3 在 draft 协议正式批准后也有价值。结构对照均为开发中的自适应有限协议：失败结构没有形成独立冻结、同机会、全条件完整对照。不同结构的有限预算通过差异只提示结构辨别潜力；没有统计优势、因果机制或物理无解证明。本轮所有任务首次完整通过后即停止，没有追加为制造结构优势而设计的对照。

真正影响下一步的数学信息是原 Native local response / constrained response 搜索中的完整位置、速度、轴约束反馈及停滞信息，它支持控制续算、锚点比较和 M6 材料调整。未额外调用 GVS/PCC/SoRoSim、CONIC、T1/T2 或短响应扫描。BF2 的完整 COM 外力不能由不支持该外力的 GVS 代理代替；BF5/BF6 完整有向轴代理、Tracking/工具轴 Reach-only T1/T2，以及没有配套同协议保存结果的 T2 均不作为可行性证据。原方法目录与适用性检查保存在私有预检证据。

**私有见证复核。** 所有者根目录为 `D:/softrobot-agent/.worktrees/base-only-benchmark-feasibility/runs/base-only-owner-20261028-r2`。每项 `<ID>/review_manifest.json` 内容身份如下；完整候选、源控制、raw/evaluation/profile、独立 receipt、联合选择和完整搜索记录均通过此索引定位到 `<ID>/private-store/platform.sqlite`。公开不含控制数组、完整赢家设计或原 Store。

| 索引 | ID / 私有相对路径 | review_manifest 内容 SHA-256（原 canonical digest） |
|---|---|---|
| W1 | `M1/review_manifest.json` | `ac240c3bdd8bc02606f70876eb3743f8ae56471b4e8636a6a519720772ca5421` |
| W2 | `M2/review_manifest.json` | `4b93f0faa9ccf22c7b3c4f2d1c3d956f462ef5b9dd97ec01f07f7e899d00e567` |
| W3 | `M3/review_manifest.json` | `438c8fdf5833535eb51e3db37b0924c86a39b505a3634115e461cedbb1056251` |
| W4 | `M4/review_manifest.json` | `7f29b99b4d3b38fd9aac4b0a015998b2b824e4f1e552482131a74552145c9f7e` |
| W5 | `M5/review_manifest.json` | `434cb1144d8ee445b17f3b7816e8a76eb4e9dea4be1044ec266f0974d1563ba3` |
| W6 | `M6/review_manifest.json` | `b0713695227ca0be5cdb0220b251988d25638b5134c95926281ac25e8ee984c7` |

所有者可执行 `D:/softrobot-agent/.f3-prestudy-env/Scripts/python.exe -m tools.base_only_audit` 重做收据/内容地址/来源绑定审计和脱敏标量导出；该命令不积分、不重新评分、不恢复或重发计算。审计核对原 `_source_issue` / `_outcome_issue`、receipt execution ID、source schedule 绑定、raw/evaluation/profile、真实 Base 起点、全部联合 condition、相同物理结构和 mesh、BF6 负载/逐步无接触。任务成功只消费原 evaluator 与原 SELECT 结果。

未来 Agent 评测必须采用干净 checkout、独立 Store 与上下文，并在文件/工具可读范围中明确排除本轮所有者 runs、本聊天、隐藏报告及原历史赢家。`.gitignore` 仅避免提交，不能提供访问控制；不能让未来 Agent 直接使用当前所有者 worktree 充当隔离环境。本轮未启动未来 Agent Study。

**工程隔离、预检与验证。**

起点远端 Stage 0 为 `e0200b4b2415139088e8fea7780d4156a16cbbc1`。远端 integration/research-next 为 `455ec55347ce6ab05cfbf71ad439044e9db77aca`，本地仍为 `618bb16b2a42a1be93ca80c527e4608d67e30371`；未合并、覆盖或推送其本地研究提交。独立分支为 `research/base-only-benchmark-feasibility`，独立 worktree 为 `D:/softrobot-agent/.worktrees/base-only-benchmark-feasibility`。原主工作区的既有未跟踪运行文件、Stage 0、其他研究 worktree 与历史 Store 未修改。

早期 v1 M4 的 formal_research / 零 Provider 组合触发原 protected-closeout，零积分 STOP；改用原有 `engineering_numerical` 模式承载外部 Codex 组织，保留正式 Study 工具、冻结、权限与原预算检查。v2 预检识别 M2/M3 原时间步为 0.5 ms，尚未积分即修正次数上限，并保留已创建 M4/M2 的零积分 STOP。实际研究仅使用新 v3 / r2 Store。旧配置与 Store 的拒绝/失败没有被覆盖；v1/v2 是退休预备快照，不是可运行入口。初次编排器腱路检查误用 route 字段，已在无积分阶段改为原 schema 的 points/attachment；没有改原腱路或物理实现。

配置 authorization 在科学执行前已冻结用户本轮完整授权；供 discovery-view 使用的 formal_study_authorization 范围元数据另以原 Store 事件保存。M4 首次 Native 时 discovery-view 的附加范围标志尚未填写，执行本身已通过原有 numerical owner 准入和冻结授权；该元数据随后补齐，不宣称它是事前已存在的额外批准。没有修改权限/预算内核或以零 Provider 自动关闭规则为由改生产准入。

19 项 Base-only 定向回归全部通过，使用原 `tests.research.stage0_no_integration` 禁止任何积分/外部 Provider，禁止调用尝试为空；没有重跑或修改 Stage 0 已知五项基线问题。六项真实预检记录 FamilySpace、任务/控制/Registry 适用性、时间网格、实际 Base 起点和预算最坏上界；科学执行及最终审计再检查完整输出与独立 SELECT。编排脚本通过 py_compile 和 git diff --check。

新增文件：`tools/base_only_campaign.py`（正式工具调用、预算保留/监督、收据索引）；`tools/base_only_audit.py`（既有结果绑定核对与标量导出）；两个任务专用 Base-only FamilySpace；六个任务的 v1/v2/v3 Study 快照；预算 v1/v2 快照；本报告与 `evidence/base_only_benchmark_feasibility_20261028/summary.json`。仅 v3 和预算 v2 为活动协议。没有修改 `tools/research/`、物理/数学实现、原任务、Agent、Prompt、上下文投影、Store 或预算内核。

科学执行绑定的代码提交为 `668d2c251`（完整 SHA 见各 Store freeze / summary implementation）。交付提交与远端分支 SHA 以本次最终交付消息和 `git rev-parse HEAD` / `git ls-remote origin refs/heads/research/base-only-benchmark-feasibility` 核对。允许推送此独立分支，不自动合并主线。
