# C1：开放 NMPC、MuJoCo-direct 和 PPO 的自主 Study

**已完成：主 Agent 独立冷启动，选择 NMPC 实测控制 → MuJoCo-direct → 独立回放，
原任务全部通过，公开读证据后正式 SELECT，零额外确认下封存。**
这支持本次冻结 Reach/Hold 的一次仿真任务通过；没有结构改进、PPO、鲁棒性或跨任务证明。

Study `mujoco-c1-autonomous-20261024`，从用户指定 C0 提交
`12f0464ca8fb78907a081c2520b4f83dcb3758b9` 建立独立 worktree 和分支
`codex/mujoco-c1-autonomous-study`。用户 C1 附件明确授权一次正式研究及持续工程监督、
同 Study 恢复、必要修复、普通 commit/push；不授权改变冻结验收或启动另一项 Study。

## 启动前冻结

配置为 `configs/research/study_mujoco_c1_autonomous.json`，保留原 robot/task/control/runtime。
新 Store、Provider session、证据目的地；history、mathematics、control_seeds、supplied_evidence 全为空。
不提供历史候选、控制、成功序列或科学动作顺序。源结构及注册控制默认是工程先验。
结构仍由原 source-relative propose 生成，不新增拓扑或任务域。

| 资源 | 冻结上限 |
| --- | ---: |
| Provider / 其中保护 | 32 / 6 |
| Public operations / 其中保护 | 120 / 12 |
| 数学评价 | 10 |
| 共享物理启动 | 9 |
| NMPC / 固定张力回放 | 2 / 5 |
| PPO stages / actions / 每 trial actions | 1 / 8192 / 8192 |
| RL 独立评价 | 1 |
| 新增独立确认 | 0 |

所有物理子额度共享 9 次；原 reserve_rl_evaluation 保护已准入 PPO 的独立评价。
未使用独立 local_solves/offline_nlp/bdf_replays，均为 0；MuJoCo-direct 使用数学评价额度。
所有科学 wall-time 限制仍为 null。PPO 原 n_steps=256、默认 allocation=2048、
rollout 对齐及至少两优化批次规则保持。Agent 自行决定有限 allocation 和科学路线。

已阅读 AGENTS、A/B/C0 报告及原实现。现有 measured_nmpc_trajectory 已核对当前 Study、
完整性、科学配置、实际 SI 张力及原执行所有权；不要求任务通过。
只在 control_initialization_methods 增强权威说明，并在 research_plan 工具描述引用它，
补齐 capability_sequence 简短说明。没有新增 Schema 或实现第二套转换。
NMPC、MuJoCo-direct、direct/residual PPO 均可选，原模型适用范围及独立验收边界保留。

预检验证配置解析、依赖导入、凭据存在。尝试的旧 NMPC 合成测试因其 SoRoSim
fixture 缺少 matlab.engine，未进入测试主体；另一个旧环境路径不存在。
这不影响实际冻结的 GVS NMPC，未安装 MATLAB 或修改测试/生产准入。
没有发送预检 Provider 请求或进行科学仿真。host 沿用现有 .s135-env；
worker 使用冻结 .mainline5-env / .rl-pilot-env，单线程环境不变。未安装依赖。

## 实际科研决策与冷启动独立性

主 Agent 使用原 `python -m tools.research run` / Strands 会话，session 与 Study ID 相同。
科学实施冻结在 `68729f7a86b6ef4c9e939914d394c1bd210942ad`；运行期间无迁移、重启、预算扩容。
`--pause-after-completed-invocations 1` 未造成中途暂停：原 SDK invocation 内持续消费反馈，
直到正式 SELECT，进程正常返回。Codex 的监督读取没有提交科学动作。

Agent 保留原基准结构（近段 7.2 MPa、远段 5.4 MPa，长度 0.16/0.11 m），
没有 propose 新结构，也没有采用阶段 B 的增刚结构。新 Store 初始无实验或控制结果。
“冷启动”指没有历史科学答案输入，允许冻结源结构及注册控制器默认作为工程先验；
本次没有验证从常量预张力直接优化也能成功。

所有科学选择可追溯至原工具请求和正式计划，完整引用见
[supervision_summary.json](../../evidence/mujoco_c1_autonomous/supervision_summary.json)。

| Agent 选择 | 原证据 / artifact_id 前缀 | 实际结果 |
| --- | --- | --- |
| H1：基准结构闭环 NMPC | `5e0c3dfc` | 完整 35 更新；保持速度失败，实测张力可用 |
| H2：initialize_control baseline | `2e155dec` | 本 Study 同候选实测 SI 张力，parent=candidate，无 channel_map；新 schedule 未评价 |
| MuJoCo-direct 数学请求 | `3e35393b` | 从冻结 t=0 初态，使用上述 schedule，得到局部预测与新 schedule `6e08ba12` |
| H3：独立 physical_replay | `c953cb38` | 全程回放通过原全部组合验收 |
| H4：公开读证据、SELECT | selected_solution `cc2c985d` | stopped；pending=null；新增确认 0 |

NMPC 是 Agent 自主选择的可选控制来源；Codex 没有规定科学动作次序、结构方向、
优化结点或系数。MuJoCo-direct 的局部响应/SLSQP 是工具内部确定性数值工作；
主 Agent 决定调用它以及之后独立评价。数学预测本身始终 task_acceptance=unmeasured。

## 数学、控制与独立验收

数学请求显式使用 `model_source=mujoco`、`operating_point=standardized_initial_pretension`，
从冻结命名零初态与本候选预张力在 native worker 内构造原生状态，起始时间为 0。
它没有依赖一份为了获取 t=0 而额外执行的物理回放；控制参考来自本 Study 的真实 NMPC。
已逐项核对初始化 schedule 的 35×6 张力等于原 controller_observations 的 actual_tension_n，
没有使用求解器未执行预测、未完成轨迹拼接或历史张力。

Agent 选择 response search、窗口 [0,0.35] s、结点 [0,0.12,0.23,0.34] s，
24 个 knot-major 系数，允许修正上限 1.5 N、初始半径 0.15 N、差分 0.02 N、内部目标裕量 5%。
它请求最多 350 回调/12 次外迭代，实际仅运行 **26 回调：1 基线 + 24 差分 + 1 提案**，
1 次外迭代即达到局部目标。内部 SLSQP 7 次迭代、success=true；没有全局最优证明。
其局部响应条件数约 3.86×10⁷，也不支持区域稳健结论。

| 原验收量 | 完整 NMPC | 优化后的完整独立回放 | 冻结阈值 |
| --- | ---: | ---: | ---: |
| 终点误差 / m | 0.003119743968 | 0.002626273873 | ≤0.01 |
| 保持最大位置误差 / m | 0.003139022698 | 0.002745601932 | ≤0.01 |
| 保持最大速度 / m/s | 0.023209852646 | 0.018985308193 | ≤0.02 |
| 完整执行 / 保持覆盖 | 35 更新 / 6 样本 | 35 区间 / 6 样本 | 完整且含端点 |
| 实际张力越界 / N | 0 | 0 | ≤1e-8 |
| 组合验收 | valid_failure | accepted | 全部组件通过 |

保持最大速度描述性下降 **18.2015%**，相对阈值留出约 5.07% 余量。
native 最佳预测的三个指标与独立回放一致；二者使用相同 MuJoCo 物理，
“独立”指独立启动、全程执行并由原注册 evaluator 组合验收，不代表跨模型验证。
没有对未修正 schedule 另加一次完整回放；其 native 基线与闭环实际轨迹对齐，
因此不能宣称完成了额外的独立配对重复实验。

原 NMPC 35 次 IPOPT 均为 Maximum_Iterations_Exceeded；原策略仍提供可用控制并完成物理执行，
不是优化收敛。其平均每更新约 93.046 s，simulation wall 3265.328 s，未展示实时性。
完整失败的张力仍成功构成后续起点，支持本次 NMPC→schedule 交接能力。

数学结果实际影响了下一步：主 Agent 依据 native 的完整保持样本预测与 5% 裕量，
选择 H3 全程回放，而不是直接 SELECT 数学结果。独立通过后停止探索，公开读取原评价再 SELECT。
未调用额外 native 力学/结构敏感性、GVS T1/T2 或 PPO；不能声称已验证这些方法在本 Study 的收益。
direct/residual PPO 保持开放，但首次通过门禁阻止继续探索，训练 stages/actions/评价均为 0。
没有真实 checkpoint，因此本次未验证 PPO 训练或 residual 参考使用效果。

## 账本、错误与恢复

| 资源 | 实际 / 冻结上限 |
| --- | ---: |
| Provider requests | 16 / 32（主会话 14，Reporter 2） |
| Public operations | 18 / 120 |
| 数学评价 | 1 / 10 |
| 共享物理启动 | 2 / 9 |
| NMPC / 固定张力回放 | 1 / 2；1 / 5 |
| PPO stages / actions | 0 / 1；0 / 8192 |
| RL 独立评价 / 新增确认 | 0 / 1；0 / 0 |

原 ledger wall 为 3434.1963475 s，原 cumulative numerical_s 为 3271.7644684 s；
两者时间口径不同，不相加，也不是 CPU 成本。数学 worker wall 2.0927088 s，
其中 native 内核约 0.8502096 s；独立回放 worker wall 1.1366387 s。
数学内部 26 rollouts、18,200 物理步、1 次模型构建、1,847 次显式 forward。
NMPC 和完整回放各 700 个 MuJoCo 步，合计本次 **19,600 个 MuJoCo 积分步**；
GVS/IPOPT 内部求解工作另外包含在原日志和耗时中，不能把一次数学评价解释为一次引擎计算。

Provider 均为 HTTP 200，原用量合计 prompt 635,639 tokens（cache hit 271,616）、
completion 26,799（含 reasoning 15,246），total 662,438。Provider 未返回金额，金额保持未知。
r3_response 的 received/metadata_saved 是同请求的两次持久化，不是两次发送；按原 request_id
去重核对共 16 次发送，0 重发、0 未知结果、0 重复计费。所有 36 个 calls 均有 receipt
（completed 33、failed 3）；工具级拒绝并不一一对应独立 call，不能据此增加或抹除费用。

首次启动在进程创建前被自动审批拒绝，理由是需要明确具体 DeepSeek 外发授权。
已向用户说明，并获得“批准本次 C1 的上述外发与运行”，记录到同一冻结 Store 后启动。
拒绝前 Provider/科学计算均为 0；没有绕过审批或改请求 ID 重试未知发送。
正式运行中没有网络、worker 中断或恢复 dispatch，没有迁移和重置预算。

Agent 自身有 7 次工具参数/读证据门禁错误：不存在的候选字段、缺 native 状态来源、
physical_replay 多余字段、decision candidate 不一致、不存在 task_passed 字段、
未满足 exact_actual_read、尚未正式 evidence_read 评价。原反馈保留，Agent 自行更正，
这些拒绝未启动额外科学 worker。Codex 没有代填科研参数或绕过 SELECT 的读取要求。

## 证据层与最小工程修改

F0–F2、主 Agent、原子 Agent/Reporter、ResultCard 和 L0–L3 均保留。
实际使用原 Reporter 的 2 次模型解释请求；没有 research_investigate 或额外 Codex 子 Agent。
物理通过后的确定性摘要、原始 acceptance 读取和 SELECT 不依赖新增 Reporter 请求。

数学结果 `3e35393b` → schedule `6e08ba12` → physical result `c953cb38` →
evaluator `67e61a3c` / raw `d90973cc` → selected_solution `cc2c985d` 的引用一致。
数学与回放的 design_identity 相同；各自 model_identity 保留配置模型与执行模型的原义。
原 NMPC 的完整 ControlEvidence 所有权/科学配置核验直接支持初始化，未补造预测或验收结论。
L3 保存全部 36 个状态样本，保持窗口 6 个原始样本均满足阈值；审计中只摘取这 6 个标量。

运行期间实际 L0 包含原方法目录、候选、决策与 Reporter 摘要：首包 39,831 bytes，
范围 39,831–92,088 bytes；带工具 Schema/会话历史的实际 Provider wire 为 28,780–200,909 bytes。
没有上下文溢出、截断或会话清空。没有默认反复注入完整 96 维状态或全部控制表；
因此没有借本次任务重构上下文系统。L0 的增长和 Provider 历史成本仍存在，未宣称已完全最简。

封存后只读审计发现：旧 physical_replay result 漏存 evaluation_version，
使 working_set 中本次 NMPC/回放比较错误地 comparable=false。
在 `3c222b13` 做最小修正：新结果直接保存原候选版本；旧结果只有在 candidate/profile
精确匹配时投影该可信版本。显式版本不一致仍拒绝比较，不改旧 artifact。
本次原 Store 及导出 snapshot 仍保持科学实施 `68729f7a`，没有事后迁移封存科学结果。
后续只读视图能正确比较相同候选与验收指标，不建立因果或结构优越性结论。

相对 C0 的生产代码共 **3 文件，+8/−3 行，净增 5 行**；测试只加 1 个元数据断言。
其余是冻结配置和交付证据/报告。未修改动力学、优化器、任务计算或验收，未新增平台模块。
定向检查：配置/依赖/凭据与原 Schema 检查通过；本 Study 封存 Store 的 L2 投影和
显式版本/profile 不匹配检查通过，并确认 Store、事件、账本不变；
原合成 SELECT/零与正额度确认恢复测试（增加评价版本断言）通过；git diff --check 通过。
合成测试无科研意义。旧 S127 MATLAB fixture 的预检失败已记录，未运行全仓库、A/B 搜索，
也没有为了测试修改再跑真实科学计算。

## 交付与未证明部分

原 Store 导出：[evidence/mujoco_c1_autonomous](../../evidence/mujoco_c1_autonomous)。
包含原 immutable_artifacts.tar.gz（所有原 artifact 与 session/events/calls snapshot）、
archive_manifest.json、configuration.json、calls.json、ledger.json、disposition.json、
design_package.json，及只读工程审计 supervision_summary.json。
原活动 Store 保留在 `runs/research/mujoco-c1-autonomous-20261024/platform.sqlite`；
导出经实际凭据字节检查，没有把 API key 存入归档。没有提交环境文件。

本次事实支持：主 Agent 可从无历史控制的新会话选择方法，利用完整失败的 NMPC 控制，
选择局部 native 优化、检验其物理实现、修正接口错误、读取成功证据并自行 SELECT。
它不证明跨模型推理、结构搜索收益、PPO、自主选择全方法的优越性、多次重复或跨任务泛化。
只有一个候选、一个 seed、一个冻结任务；任务通过也不改变上述边界。

下一阶段优先研究**控制初始化与参考质量**：本次成功依赖一次约 54 分钟的闭环 NMPC 起点，
尚未证明常量预张力等更廉价起点也能在相同有限优化额度内成功；小修正的数值精度敏感性
和独立重复也未评估。结构能力比较应对每个结构重新绑定合法初态/控制并给相同重优化预算；
跨任务泛化应另行冻结任务和相应适用方法，不能沿用 Reach/Hold-only 结论。
这些是建议，**没有自动启动下一项 Study**。

提交：`68729f7a` 冻结配置/中性说明；`3c222b13` 封存后评价版本投影修正；
最终报告与原 Store 证据单独提交并普通推送同一分支。
