# P6.3-A 数学研究决策接口

完成范围：候选绑定的数学研究发现、当前 L0 投影、既有结果事实交付和离线验证。未启动正式 Study。真实 Provider、数学 Worker、物理 Worker、NMPC、RL 均为 0。测试中的数值全部为明确标记的合成 fixture，不是新的科学证据。

## 基线与实际信息边界

2026-10-29 核对 `git ls-remote origin HEAD refs/heads/codex/p6-2k-knowledge-consolidation`：默认远端 HEAD 为 `2a854280db69425dc50af9012b8da52194a679ee`，指定基线仍为 `97bdf9e6ca6aa72ee1adbe5a1d1a564fe5364f58`。本轮从后者创建 `codex/p6-3a-math-decision-interface`，worktree 为 `D:/softrobot-agent/.worktrees/p6-3a-math-decision-interface`。原工作区 `feat/gvs-dynamics` 及其未跟踪文件未改动。

已读取根 `AGENTS.md`（没有子目录规则）、P6.2-K 数学审计、信息审计及实际源码。原信息边界如下：

| 原模块 | 实际进入 Main 的内容 | 缺口及处理 |
|---|---|---|
| `mathematical_method_view` | 通过候选的 `mathematical_capabilities` 显式查询得到完整方法、冻结模板、Schema、准备状态 | 原方法目录保留，新增 `/research_opportunities` 关联视图 |
| `mathematical_catalog` | `agent_decision_brief` 中的候选方法摘要、状态、费用和查询 | 本身没有合并参数域与任务量；继续复用原目录 |
| `research_decision_brief_v3` | 方法名、planning/execution 状态、预估数学计数进入 action menu；参数表、单位和前提关联不在此投影 | 加入小型 `mathematical_research`，不注入完整参数表 |
| `information_flow_brief` | P6.1 会重新构造 Provider packet，原方法状态通过工具动作目录进入请求 | 显式传递同一 `mathematical_research`；SDK Mock HTTP 实际 wire 验证 |
| `selected_analysis_schema` | 完成 diagnose 的选中方法投影；bound 模式只让 Main 填科学变量 | T1、T2 v1/v2 均通过 Provider Schema JSON 序列化和原 Pydantic 校验；未发现兼容问题，不改 `agent.py` |
| `quantitative_facts` → Reporter | 原结果模型量、约束、费用、紧凑数学事实 | 增加 T1 具名任务量/J/可靠性和 T2 方向状态、来源及费用查询；固定输入/重新优化仍由已有数学 quantities 表示 |

没有修改 `AnalysisRequest`、Plan、admit_decision、analysis.dispatch、Solver 或 Reporter 结构。原 bound 接口自动绑定明确选中的候选、操作、MuJoCo 来源和完整冻结协议；任务由该候选配置决定。Main 仍选择假设、方法、参数、步长、科学控制设置、是否继续或停止。`research_plan(diagnose)` 只记录并诊断科学选择，`research_analysis` 单独执行原准入；不以只读调查代替数学请求。

## L0 与 L1 交付实例

[完整机器可读实例](p63a_interface_examples.json) 包含实际生成候选、派生 L0 投影、L1 两个段长行、完整 T1/T2 请求及 Reporter/Main handoff。P6.3-B0 已明确 `/l0_kind`：此 `/l0` 没有动态工具目录，不是完整 Provider wire。新增 `/mock_provider_request` 单独复用实际保存的 Mock HTTP L0 与 tools 摘录，五类 capabilities 均有动作，来源 request ref 和 Store 保留；其候选与五点 fixture 不同。所有实例 ID 都来自隔离的离线 fixture Store，不能作为未来 Study 的候选所有权或科学引用。

实例冻结 `bf7-shared-reach-v1-central_high@1.0.0`，有效任务 identity 为 `52e6c2bfb2502d80851eb2d5362a8b3c73dff515e46afcb2e189095694ce3ab8`，与历史 M1 central_high 相同。它是新生成的合法工程候选，不继承历史成功结构、控制或任务接受。选用该条件和两段长仅用于接口验证。

历史 M1 SELECT 包的 `candidate=fef9a819…` 实际配置是 positive_high；不得把它直接标成 central_high。已只读查看原 Store 中该字段，原多条件结果保持不变。

L0 新增字段的实际内容（下列是摘录，完整对象见 JSON `/l0/mathematical_research`）：

```json
{
  "version": "candidate_mathematical_research_v1",
  "parameters": {
    "total": 39,
    "continuous_authorized": 2,
    "categories": ["segment"],
    "registered_categories": ["controller", "discretization", "geometry", "routing", "segment", "tendon", "topology"]
  },
  "metrics": [
    {"metric_id": "terminal_error_m", "unit": "m"},
    {"metric_id": "holding_max_error_m", "unit": "m"},
    {"metric_id": "holding_max_speed_m_s", "unit": "m/s"},
    {"metric_id": "best_found_J", "unit": "1"}
  ],
  "methods": [
    {"method": "fixed_input_structure_v1", "status": "unauthorized", "estimated_evaluations": 3},
    {"method": "mujoco-nonlinear-task-capability-v1", "status": "unauthorized", "estimated_evaluations": 1},
    {"method": "mujoco-reoptimized-structure-response-v1", "status": "unauthorized", "estimated_evaluations": 1}
  ],
  "detail_query": {
    "reference": {"artifact_id": "380b847f1653fe021d8d0352a6f6597436a8e05237dc7803962ca91fed81c6ee", "media_type": "application/json"},
    "view": "mathematical_capabilities",
    "pointer": "/research_opportunities"
  }
}
```

派生 L0 的数学字段还包含候选/任务绑定、每方法 missing、wall_cost=unknown、所有方法目录查询和推断边界。完整参数表留在 L1，其他方法继续通过既有目录发现。没有候选时明确 `requires_owned_candidate`。此 fixture 没有正式数学 scope，末尾还测试了预算耗尽，因此显示 unauthorized 与真实 missing，而非伪装 ready。正式授权、参数准备和预算是独立条件。P6.3-B0 将 categories 限定为当前 Study 获准且有效的连续参数类别；registered_categories 单列全部注册类别，原域和授权规则未改。

L1 由 `family_analysis_parameters` → 原 `parameter_capabilities`、当前 `TaskAdapter.analysis_requirements` 和已有 methods 合成：

| 参数 | 当前值 | 注册域 | 单位 | 关联方法及指标 |
|---|---:|---|---|---|
| `segments.0.length_m` | 0.16 | [0.08, 0.24] | m | T2 的三个任务约束与 J；来源计算为 T1；fixed_input_structure 仅短响应诊断 |
| `segments.1.length_m` | 0.11 | [0.06, 0.20] | m | 同上，独立轴；不声称两参数的混合偏导 |

这两条域来源分别是 `segment_domains.0.length_m`、`segment_domains.1.length_m`，没有新增参数注册。离散 `cells` 和无效理想腱物理量的原限制保留。每条 metric 保留原 constraint、坐标/相位、采样索引和精确候选来源指针，包括 controller 所有的 holding 门槛。

实例任务末端位置阈值 0.01 m，holding 位置阈值 0.01 m，holding 速度阈值 0.03 m/s。末端索引 30，holding 索引 27–30；网格 0.02 s，完整 horizon 0.6 s。`best_found_J` 是原 T1 在已访问控制中找到的最小最大归一化有符号超限；不是新指标注册、全局最优值或任务接受。没有从 J 推导任意机制指标。

准确完整请求分别位于实例 JSON `/requests/T1` 与 `/requests/T2`；协议全字段及 source refs 均未省略。实际 Main bound 请求填法为：

- 先以 `research_plan(action=diagnose)` 的 `decision.selected_candidate` 与注册 `selected_method` 作科学选择，同时保留假设、支持/削弱观察及固定条件。
- T1 的 `research_analysis`：`operating_point=standardized_initial_pretension`、`control_optimization.source=<该候选 initialize_control 返回的 source>`，以及原 v2 `settings`。例中 `knots_s=[0,0.6]`、`correction_window_s=[0,0.6]`、`active_coefficients=[0]`、`evaluation_requests=4`、`iterations=1`，仅为 fixture 设置。
- T2 v1：同一 operating_point，`nonlinear_response={variable,unit,t1_results:[baseline,minus,plus]}`。单位错配按原契约得到 not_comparable，不修正输入。
- T2 v2：同一 operating_point，`nonlinear_response={version:nonlinear_response_v2,directions:[...]}`；每方向明确 `direction_id`、`variables`（dp/ds）、`coordinate_unit=m`、`coordinates=[0,-h,h]`、三个原 T1 refs，共用 baseline。实例 h 是实际浮点差 `0.0050000000000000044`，不是在展示中改写的精确十进制。

固定 candidate、operation、model_source、protocol 由现有程序绑定，Main 不重复提交。未完成的控制源或 T1 stencil、变更任务/协议、未授权方法、超预算仍由原入口处理。模板可以被读取，不等于已获执行许可。

## 一次离线 T1/T2 → Reporter → Main

`test_five_saved_t1_two_parameters_t2_reporter_main_and_budget` 完成以下工程链路：

1. 用原生成器和编译校验创建五个实际候选：共同 baseline、第一段长 ±0.005 m、第二段长 ±0.005 m；每个使用自己的原 baseline control 初始化。
2. 对原 `AnalysisRequest` 调用 `analysis.dispatch`。仅将 `_run_contained` 替换为内存 fixture，不启动子进程；T1 返回明确标记的伪造数值/数组。真实 Store 保留原请求、绑定、结果和模拟计数。
3. 原 `candidate_responses` 找到两条可比 stencil，并生成 T2 v2 请求。原 `saved_context` 验证候选、协议、单参数、初态约定、共同输入及搜索设置；原 T2 聚合器只处理已保存的合成数据。
4. `result_card` 保留四个有原 pointer 的量：两轴各 fixed_control 和 reoptimized 的 central secant，合成值分别为 2、−3 signed J/m。iteration_limit 导致两轴仍为 unresolved；这不是新的梯度验证。
5. `reporter.scientific_feedback` 保存确定性报告，`reporter_handoff_summary` 将关键量、可靠性、费用和精确查询交给 Main；最终 L0 verified_facts 中实际包含该结果。Reporter interpretation=deferred，没有调用模型解释。
6. 模拟数学准入总数 6（五 T1、一 T2），同 key 重读不重复扣费。T2 引用五个 T1 的既有成本，新 model/rollout/physics_steps 均为 0；T1 中的 400 steps 等数字也是伪造 fixture，不用于资源估算。原预算耗尽拒绝和旧 v1 单位约束均验证。

真实 ledger 中 model_calls/backend_solves/worker_calls=0，无独立物理结果、无 NMPC/RL。Mock contained boundary 会保存执行协议的模拟成功字段，不能把这些 fixture receipt 当作真实 Worker 已运行。独立 SDK wire 测试中的 Mock HTTP 计数也不是真实 Provider 调用。

## 九项任务支持矩阵

[机器可读核对记录](p63a_tool_support.json) 保留六项原 Store 候选、原 Study stopped 状态及用当前代码求得的适用性；另有被动分支实际 Git tree、提交与本地文件可用性。历史成功仅适用于原冻结协议及模型。

| 任务 | 历史见证 | 数学内核实现 | 当前分支接入 | 当前候选可执行状态与缺口 |
|---|---|---|---|---|
| M1 Reach/Hold | 原三条件 accepted | affine sampled/conic；native bounded control；Reach T1/T2 | 已接 AnalysisRequest/TaskAdapter | 当前单条件工程候选已生成并验证请求；真实数学未授权。原成功 Study stopped；三条件须分别绑定，不能混做一条差分 |
| M2 Reach/Hold | 原多条件 accepted | 同上 | 已接 | 原候选是历史所有权；新 Study 需生成/拥有对应条件候选、源和预算 |
| M3 Reach/Hold | development draft accepted | 原 Reach 内核可用 | 开发任务已接，正式 benchmark 未批准 | 不将 draft 见证升级为正式接受；当前原 Store stopped |
| M4 timed Tracking | 原 accepted | affine sampled/conic 与 native direct sequence | 已接 | Reach 非线性 T1/T2 unsupported；新 Study 可用已适配 timed/native 方法，必须完整时序覆盖 |
| M5 position + tool axis | 原 accepted | native direct sequence、native mechanics | 已接 TaskAdapter/独立 evaluator | affine/GVS 和 Reach T1/T2 unsupported；不能丢掉轴向条件代替原任务 |
| M6 loaded oriented Tracking | 原 accepted | native direct sequence，已声明外力适用范围 | 已接 | affine/GVS 和 Reach T1/T2 unsupported；外力/接触/模型前提继续检查 |
| C1 同结构多任务 | 原同 XML batch PASS | 各子任务 native 工具 | 子任务已接；没有单一 C1 数学 TaskAdapter/T1/T2 | Reach 子项可用 Reach 方法，Tracking/axis 子项分别适配；不能宣称一个 Reach T1 覆盖整个 C1 |
| PHS-2D | 开发十工况 pass，非 formal SELECT | passive equilibrium KKT、modal target、Jacobian matching、design sensitivity 等跨分支实现 | 当前分支仅知识 Trace；无被动 AnalysisRequest/TaskAdapter 接入 | 当前接口 unsupported；不得借 Reach scaffold 执行被动任务 |
| P3 被动渐进变刚度 | 原任务及两单元 pass；四单元 INVALID | 本地 passive equilibrium/response、独立被动 evaluator | 当前分支仅知识 Trace；无被动 AnalysisRequest 接入 | 当前接口 unsupported；精度/分支有效性问题保留，不能把源码存在当可执行证据 |

PHS 远端 `research/phs2d-inverse-passive-design` 已核实为 `9d6d160e050c836b87d0563a497fc0ec1c3761a8`，本地同提交。其 `extensions/tendon_family/passive_equilibrium.py`、`passive_inverse.py` 和 `tools/research/phs2d*.py` 实际存在。

P3 源码实际位于本地 `codex/passive-progressive-stiffness@83d9b8f35…` 和 `codex/p3-spatial-fidelity@f0379f850…`，含 `passive_response.py`、`passive_load.py`、`passive_evaluation.py`。`codex/p3-knowledge-integration@6b982c7b4…` 的 Git tree 没有这些求解源码。2026-10-29 只读远端查询没有返回上述 P3 分支 refs，因此准确状态是“本地源代码可用”，不声称已发布远程实现。本阶段没有移植。

## P6.3-B 真实预算估算及启动条件

预算必须按选中的方法计算，不能把 affine conic 的内部 solve 计数用到 nonlinear T1。对现有 Reach native T1，数学准入每候选 1；T2 每个 v2 聚合请求 1。令 P 为唯一候选数，E 为每候选允许的 callbacks，Q=(deadline−state_time)/physics_dt（实际整步规则由原 kernel 决定）：

| 研究 | 数学 allowance | native 模型预算 | rollout 上限 | integration steps 粗上限 |
|---|---:|---:|---:|---:|
| 一个方向三点 baseline/±h | 3 T1 + 1 T2 = 4 | 约 3 | 3E | 3EQ + 必要重建 |
| 两方向五点共用 baseline | 5 T1 + 1 T2 v2 = 6 | 约 5 | 5E | 5EQ + 必要重建 |

T2 不新增 native 积分，只记一次聚合及其实际 wall time；原 T1 花费不重扣。固定控制对照已由每个 T1 的初始控制回放记录，无须另建一套 Solver。更多步长、独立初始化或 holdout 候选增加唯一 T1 数量，不能用五点声称收敛验证。

response 搜索机会按现有目录计算：S 个起点 baseline，后续每次完整更新约 D 个有效系数探针 + 1 proposal，始终受 E 的总 cap 限制。失败/部分 callbacks、prefix reconstruction、cache/reuse 和实际 iterations 以原 cost/receipt 为准。`physical_launches=0` 不等于 native integration 免费。

实例条件 duration=0.6 s、dt=0.001 s 时 Q=600。若未来 Agent 自选 E=64，仅作算术例：三点至多约 115,200 steps；五点约 192,000 steps（不含额外检查、失败部分和独立验收）。该 E 不是本轮授权，也不是对 Main 的强制路线。

真实时间标尺来自原 M1 Store，已在矩阵 JSON `historical_resource_examples` 保存引用：

- `05acb70e…`：176 rollouts、105,600 steps、kernel_wall=10.1572727 s、charged_numerical=11.2999861 s。
- `92904253…`：400 rollouts、240,000 steps、kernel_wall=22.7764559 s、charged_numerical=24.1519636 s。

对相同硬件、网格和模型规模，使用原 recorded kernel_wall/rollouts × E 做初始 wall 估计，并另列原 parent/process overhead、T2/Store/Reporter 成本；上述 E=64 算术约每候选 3.6–3.7 s kernel，另有原样本约 1.1–1.4 s parent 差额。这里只是由既有实测外推，候选规模、拓扑、负载和执行环境改变后 wall_cost 仍未知。本轮未测新候选吞吐，不把 wall time 当 CPU time，也不拿合成 fixture 来标定真实资源。

独立物理验收、误差/半步长验证、失败后重试另列预算；不得从 T1 J 或 T2 方向直接宣告任务接受。Provider 预算独立记 Main 决策/查询/修订及 Reporter 解释的请求与 tokens，不能由 4/6 次数学 allowance 推断模型请求数。确定性 Reporter handoff 不需要 Provider；模型解释和正式决策的费用用冻结 Provider 配置及实际 token 记录估算。

正式 Agent 决策测试只有在以下条件全部满足后启动：

1. 用户明确授权一个新的可执行 Study、真实 Provider/数据发送范围、数学方法与有限资源上限；冻结知识/盲测策略、任务条件、域、控制源规则及 Reporter 策略。不恢复旧 Store，不从本轮接口任务推导正式执行授权。
2. 当前 checkout 实际接入该任务和所选方法，依赖就绪；候选为当前 Study 所有、编译合法，冻结协议/初态/输入/网格匹配。Main 可查询并自主选择研究路线；不把本轮 M1 两段长组合写成强制科学选择。
3. 三点或五点的模型/搜索/聚合、验证与 closeout 预算可容纳，原 request-binding、结果来源、Reporter/Main handoff 与正式接受门槛保留。只在已授权范围内启动，后续根据真实结果继续决策。

## 修改与验证

| 文件 | 修改 |
|---|---|
| `tools/research/task_constraints.py` | 组合已有参数/任务/方法为候选 L1；由关联生成小型 L0 |
| `tools/research/research_context.py` | 现有 v3 与 information-flow packet 传递数学机会，缺候选明确提示 |
| `tools/research/evidence_views.py` | 原 quantitative_facts 增加有来源的 T1 指标/J/可靠性、T2 状态与成本查询 |
| `tests/research/test_p63a_math_interface.py` | 四项必要离线测试和隔离 fixture helper |
| `tests/research/p63a_interface_audit.py` | 仅读取已完成 fixture、原 Store 与 Git tree，导出实例及支持核对 |
| 本文、`p63a_interface_examples.json`、`p63a_tool_support.json`、`p63a_validation.json` | 交付、原始引用和检查结果 |

验证明细见 [p63a_validation.json](p63a_validation.json)。使用既有 `D:/softrobot-agent/.f3-prestudy-env/Scripts/python.exe`，未安装依赖。

- 四个核心模块 28 项通过，80.057 s；当时新模块含 3 项。
- 更新后的新模块 4 项，加三个定向 P6.2-F/K 兼容检查，共 7 项通过，34.817 s。
- 最后缩小 L0 关联方法投影后，只重跑直接受影响的真实 SDK Mock HTTP wire 测试，1 项通过，4.743 s。
- 支持矩阵/实例导出成功，`git diff --check` 通过。未启动大型回归套件。

测试期间修正的是合成 fixture 缺字段、测试对象层级和错误预期；没有为测试放松科学准入。跨模块独立测试用例合计 32 项，部分因修正或最终投影调整重复执行。Mock HTTP 日志中的 RequestBoundaryHandoff 是既有请求边界 fixture。最终所有列出的必要检查通过。

未新增优化器、参数目录、方法注册、Planner、Memory、求导系统、恢复框架、SHA 防御或证据库。交付到独立分支，未合并主线；完成后停止。
