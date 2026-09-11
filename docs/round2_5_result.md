# ROUND 2.5 RESULT

工作基线：`feat/round2-constrained-reach` / `5218fce`。
本轮完成 Gate 科学语义、初态验收与未批准 benchmark proposal；没有新增 Agent runtime、
优化器、控制器、物理规律、Skill 或 workflow framework。未 commit，未 push。

## STAGE RESULTS

| Stage | Result | 实际完成 |
| --- | --- | --- |
| 1 Audit | PASS | 核对 Round 2 contracts、共享环境、模型、仿真、诊断、trace/artifact；修改前 8 项真实 baseline/窗口测试通过。 |
| 2 Gate contract | PASS | schemas/gate.py 定义 HARD / SCREENING / CANONICAL 与固定动作；不提供 Agent override 参数。 |
| 3 Gate assignment | PASS | Harness 的所有 GATE_EVALUATED 均显式带 gate_type；区分模型执行失败与模型预测失败。 |
| 4 Early stop | PASS | HARD FAIL 停止候选，SCREENING FAIL 继续 MuJoCo，最终 CANONICAL FAIL 保持 TASK_FAILED。 |
| 5 Formal benchmark decision | BLOCKED_FOR_HUMAN_APPROVAL | 没有正式窗口审批；三份 candidate YAML 均为 PROPOSED_NOT_APPROVED，未注册、未复制为正式 task。 |
| 6 Initial state | PASS | WindowAcceptance 可表达 before_window / unrestricted；实际 evidence 按包含半径的全 capsule 范围判断墙侧。 |
| 7 Passage acceptance | PASS | evaluator 显式组合 target、required initial side、final aperture 与 forbidden contact；不宣称连续穿越证明。 |
| 8 Promotion mechanism | PASS | proposal README 提供逐项 Human 审批、生成 XML、现有 loader 验证及人工注册流程；没有自动 promotion。 |
| 9 Gate evidence | PASS | gate_type 进入 trace.jsonl；每个 Harness run 新增 gate_summary.json，含停止原因、SCREENING 失败、最终判定与任务 truth status。 |
| 10 Agent contracts | PASS | Engineer/Diagnosis/Coding 文档明确能力与禁区，Human 独占 benchmark/Gate/Physics Contract 科学权威。 |

## GATE SEMANTICS

| Gate | Type | Authority | Failure meaning | Continue to MuJoCo? | Can Agent override? |
| --- | --- | --- | --- | --- | --- |
| spec_gate | HARD | Human Task/Environment/Design contracts | 非法输入或不支持的验收/环境语义 | NO | NO |
| design_grammar_gate（含 capability resolution） | HARD | Human grammar + capability manifests | 不在批准结构范围，或所需能力尚不可执行；不等于真实机器人绝对不可行 | NO | NO |
| workspace_execution_gate | HARD | M0 executable result contract | 无有效分析结果；区别于已完成的几何预测失败 | NO | NO |
| workspace_gate | HARD | 固定基座、无伸长 RobotIR 几何 + 已有 TaskSpec tolerance | norm(target-base) > L+tolerance，违反该表示下到达容差球的必要上界 | NO | NO |
| model_execution_gate | HARD | PCC finite-output / positive-command contract | 缺少可执行的 PCC commands | NO | NO |
| model_prediction_gate | SCREENING | PCC contract + TaskSpec tolerance | 低阶 PCC 预测 tip error 不满足容差 | YES | NO |
| clearance_execution_gate | HARD | clearance Tool 执行 contract | 几何分析未完成，缺少可用结果 | NO | NO |
| model_clearance_gate | SCREENING | PCC swept-radius geometric approximation | 当前模型预测净空风险；不是实际物理碰撞的必然结论 | YES | NO |
| compilation_gate | HARD | RobotIR / Environment compiler contract | 无可执行的组合模型 | NO | NO |
| physics_sanity_gate | HARD | run_task finite-state execution checks | 没有完整有限的任务执行证据；证明执行合法性，不证明任务成功或物理真实性 | 已尝试执行；不产生有效最终验收 | NO |
| execution_gate（异常路径） | HARD | Harness/tool executable contract | 当前 stage 运行异常；不能由此归因设计不可行 | NO further execution | NO |
| task_metric_gate（reach）/ target_metric_gate（window） | CANONICAL | TaskSpec actual-tip evaluator；正式 reach 来自 frozen benchmark | 实际终点误差超过 task tolerance | N/A，final evidence | NO |
| initial_required_side_satisfied_gate | CANONICAL | TaskSpec window acceptance | 实际初始全体区域不满足要求 | N/A，final acceptance | NO |
| aperture_constraint_satisfied_gate | CANONICAL | TaskSpec window acceptance + full-slab geometry | 最终整臂 aperture 条件不满足 | N/A，final acceptance | NO |
| obstacle_contact_occurred_gate | CANONICAL | TaskSpec forbidden-contact policy | 出现禁止的采样窗口接触 | N/A，final acceptance | NO |
| task_success_gate（window） | CANONICAL | 所选 task evaluator 的 conjunction | 任一必要任务验收项失败，最终 TASK_FAILED | N/A，final result | NO |

HARD 表示**指定 contract 下**的必要条件或执行合法性。非法 schema、缺能力、数值失败
不证明真实物理设计不可能。只有固定基座无伸长表示下的长度上界失败，才具有对应的
几何必要性。Physics sanity 不提供收敛、稳定性或真实物理有效性证书。

本轮审计发现 M0 原始 `norm(target)<=L` 未计任务容差，因此不能将它的 status 直接
作为任务 HARD rejection。原 MATLAB M0 数值/输出保持原状，Harness 独立检查
`norm(target)<=L+tolerance`。根据三角不等式，若实际 tip 可在 L 内，则满足目标容差
至少要求该不等式成立。这没有新增力学规律或改变容差。聚焦测试中 L=0.4、tol=0.01：
target x=0.42 被拒绝；x=0.405 虽使 M0 精确目标点检查失败，仍可进入 MuJoCo。
这些是测试输入，不是新增 benchmark 数值。

SCREENING 的 ToolResult 可为 pass（分析已完成），但 Gate 为 FAIL（预测不佳）。
反之，Tool 执行错误归 HARD execution，不能混同于 SCREENING。诊断仍可在最终失败后
运行取证，但不能改写最终状态。新 Gate action 固定，无新 route-policy 配置入口。

CANONICAL 表示**所选 task 的最终评价角色**，不自动授予 frozen benchmark 身份。
开发 fixture 的最终 Gate 仍明确引用 NON_CANONICAL_DEVELOPMENT_ONLY；其 PASS/FAIL
不能被当作正式 benchmark 成绩。旧 trace 的缺失 gate_type 读为 None/LEGACY_UNTYPED，
不追认历史权威、不改写旧文件。新的 Harness gate events 全部带明确类型。

## BENCHMARK STATUS

- **reach_free: FROZEN**。现有 benchmark entry 增加显式 `truth_status: FROZEN`
  元数据；Task/Environment/target/tolerance/metric 实现行为不变。
- **reach_window: PROPOSED_NOT_APPROVED / BLOCKED_FOR_HUMAN_APPROVAL**。
  `proposals/benchmark/reach_window_v1/` 包含 candidate_task.yaml、
  candidate_environment.yaml、candidate_acceptance.yaml 和审批 README。
- 候选几何仅参考 Round 2 dev 数值，没有移除待批准标记。Proposal 的 truth_status
  被 runtime schema 拒绝，且不具有正式 package 文件结构，也不在 benchmark tasks 中。
- 将来正式 window package 必须显式提供 `TaskSpec.acceptance` 与
  `EnvironmentSpec.truth_status: HUMAN_APPROVED`。Human 编辑/批准准确内容后，生成
  EnvironmentSpec 的 XML representation，用现有 load_task_package 验证，再人工登记
  FROZEN benchmark entry。验证成功、run、Finding、Skill、Agent 输出均不是审批。
- 该流程使用现有 Human-owned 文件边界，不是认证系统；没有服务/UI/自动升格接口。

## INITIAL / PASSAGE SEMANTICS

- **初态**：`initial_robot_region=before_window|unrestricted`。before_window 要求
  所有 capsule 的 x 最大边界（中心线端点加半径）严格小于近墙面 x；不是只看 tip。
  Region evidence 还区分 after_window、straddles_window、intersects_window_slab。
- **当前开发初态**：保持 zero-qpos 直臂和 unrestricted，完整 x 范围约 [-0.02, 0.42] m，
  而近墙面为 0.17 m；初态已 straddle/window aperture。没有通过修改参数让它符合插入语义。
- **建议正式初态**：before_window，但精确状态表示/数值未获批且本轮没有新增 initializer。
  对当前直臂选择 before_window 会得到 initial_required_side_satisfied=false，不能靠添加
  一个字段把已穿窗的初态变成真实插入。Human 可以明确决定不同语义，但 Agent 无权代选。
- **穿窗定义**：沿用全臂连通中心线在整个墙厚 slab 中通过按半径收缩的 aperture，且
  跨越近/远两面。最终 tip 在后方本身不充分；这也不是时间轨迹的连续 swept-path 证明。
- **最终态**：达到 target tolerance AND 满足 initial required side AND final aperture
  AND no forbidden contact。除了 aperture，不新增 whole-body 最终区域限制；固定基座
  仍在原点。Randomization 当前只支持 none。
- **contact policy**：当前可执行值 forbid，禁止采样到的非正距离 robot-window contacts，
  含初态；地板仍排除。允许接触的力/距离/时长阈值尚无批准和实现，proposal 留为待决。
- **证据**：复用 window_evidence.initial_configuration 并新增 initial_aperture_state、
  initial_side_of_wall、final_side_of_wall；结果增加 initial_required_side_satisfied、
  no_forbidden_window_contact 及 resolved acceptance。无逐步 trajectory 存储或穿越事件伪证明。
  这些是 sampled physical evidence，not a continuous mathematical collision certificate。

## HUMAN INPUT REQUIRED

仅正式 reach_window 尚未批准的数值与验收语义：窗口 plane/x、centre、width、height、
thickness、outer extent；target、tolerance、coordinate/environment convention；准确
initial configuration、是否整个初始 body 必须在墙前；是否要求整条空间/时间路径穿孔；
是否允许任何窗口接触及允许时的阈值；最终整个 body 的区域要求；randomization。

完整 16 项见 [reach_window_human_decision.md](reach_window_human_decision.md)。
其中 before_window 与当前 straight initializer 不兼容是明确 blocker，不是已解决的插入能力。

## REGRESSION RESULT

| 项目 | reach_free | Round 2 reach_window_dev |
| --- | --- | --- |
| 最终真实 run | 20260911T094026_035046Z_832778ce | 20260911T094033_672395Z_5c868455 |
| PCC predicted error / m | **0.08714456960728613** | **0.08714456960728613** |
| MuJoCo actual error / m | **0.17116166894090315** | **0.17116166894090315** |
| Final status | **TASK_FAILED** | **TASK_FAILED** |
| SCREENING failures | model_prediction_gate，随后执行 MuJoCo | model_prediction_gate，随后执行 MuJoCo |
| HARD failures | 无 | 无 |
| Final evaluator | FAIL | FAIL（development scope） |
| 初态/终态侧别 | 不适用 | straddles_window / straddles_window |
| 实际最小窗口净空 / m | 不适用 | **0.009769850850218975** |
| Artifacts / trace events / gates | 30 / 70 / 9 | 33 / 83 / 15 |

两个新 run 中，旧 Round 2 的全部 metrics 字段值（排除 run comparison identity）递归
比较一致；仅新增验收/侧别证据。两条链路各 8 个 artifacts 与原 run 逐字节一致：
task.yaml、environment.yaml、robot.xml、robot_ir.yaml、physics.yaml、controller.json、
tendon_command.json、simulation_state.json。两条 run 的全部 artifact hashes 验证通过。

新增 gate_summary.json 保存 gate type、action、authority、metric/threshold、evidence refs、
stopped_by、screening_failures、canonical_result 和 task_truth_status。窗口另存 acceptance.json，
指出其采用未获批的 Round 2 default。没有创建新的 artifact 层级或正式 Skill。

| 验证 | 实际结果 |
| --- | --- |
| 修改前现有真实 baseline/window tests | 8/8 PASS，22.806 s |
| 新增 5 项 focused tests + 现有 trace tests | 15/15 PASS，3.662 s |
| 最终 `SOFTROBOT_TEST_MATLAB=1 python -m unittest discover -s tests -q` | **86/86 PASS，53.558 s，无 skip** |
| 回归后最终真实 MATLAB + MuJoCo 两条链路 | PASS（执行验证）；任务均 TASK_FAILED，证据留档 |
| 新 trace schema 导出及现有 drift checks | PASS |
| `git diff --check` | PASS |

新增测试仅验证：带容差的 HARD 必要条件停止/继续；PCC 和 clearance SCREENING
同时失败仍执行真实 MuJoCo；最终 CANONICAL FAIL；proposal 与 frozen 隔离；全体初态
判定；执行失败区别于负预测。SCREENING 双失败的路由测试使用明确标注的模型 test double，
不是实际 MATLAB 预测证据；最终两条真实 run 则证实实际 PCC prediction FAIL 后继续执行。

未更改 reach_free 包、Round 2 dev fixture、物理 contracts、controllers、configs、grammar
optimization bounds 或 baseline expected values。生产 Skill 目录仅有 .gitkeep，未生成新
Finding/Skill。本轮无 LLM、RL、反馈控制、设计优化、初态生成器、复杂状态机或权限扩展。

## OPEN ITEMS FOR ROUND 3

- approved optimization variables/bounds。
- first feedback-controller target。
- remaining Human physics decisions：材料/EI 到等效刚度、damping、tendon elasticity/slack/
  friction、validated actuator model、multi-section coupling。
