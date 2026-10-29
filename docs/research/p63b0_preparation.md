# P6.3-B0：修复完成，B1 待单独授权

2026-10-29 核对远端：默认 HEAD 为 `2a854280db69425dc50af9012b8da52194a679ee`，指定分支 `codex/p6-3a-math-decision-interface` 仍为 `23d4b27f9a45d8172fa604120cb99063c51be235`。已读根 AGENTS.md（无下级规则）、A 交付和实际源码。本轮在独立 `codex/p6-3b0-math-study-preparation` worktree 实施，未改原工作区或主线。

## 两项修复

1. `mathematical_opportunity_summary.parameters.categories` 现在只统计 `study_authorized && continuous_perturbation && effective_in_current_execution` 的类别；同一筛选拥有 continuous_authorized 计数。`registered_categories` 显式单列全部注册类别，total 仍为全部注册行数。全部数据复用原 FamilySpace 参数投影，未改域或授权规则。A 两段长实例现在 categories=[segment]；B1 广些的获准域，在两段四腱 fixture 上得到 geometry/routing/segment 共 12 个获准连续参数。
2. A 的 `/l0` 标记为 `derived_projection_without_dynamic_tool_directory`，不再声称是完整 wire。`/mock_provider_request` 从原 Store 的 `r3_request` 元数据直接读取原 request artifact，保存实际 L0 与 tools 摘录，保留来源。五类动作数量为 Design 1、Control 1、Mathematical Research 3、Physical Validation 1（STOP）、Evidence & Knowledge 4。它是 Mock HTTP，不是真实 Provider；其他请求字段仍在原 artifact，且该候选不同于五点 fixture。导出支持指定已有 fixture/wire Store；本轮没有重跑五候选链，也未更新九任务矩阵。

实现只改 `task_constraints.py` 的 L0 统计；其余为直接相关的导出、说明、测试和新 Study 配置。`agent.py`、`research_context.py`、`analysis.py`、`nonlinear_capability.py`、FamilySpace、Reporter、Knowledge、Handoff、Store 与数学内核均未改。

## 最小预检的实际证据

[验证记录](p63b0_validation.json) 与 [wire/投影实例](p63a_interface_examples.json) 保留结果。

- 无候选：真实 SDK Mock HTTP 请求中显示 generate 和冻结 Domain 查询，数学视图是 requires_owned_candidate。未借 bootstrap scaffold 创建科研候选。
- 有候选：仅生成一个新的合法工程候选，查询到候选参数、单位/域、TaskAdapter 约束、方法状态和原精确模板；无旧所有权、控制或预算导入。
- 正式授权条件：先验证原 `require_authorization` 拒绝未授权，再仅在独立 B0 测试 Store 保存明确标为合成的原格式 scope approval。真实 B1 Store 没有该事件。T1 状态为 requires_parameters；T2 为 requires_comparable_t1_results，不能误称 unsupported。
- 完成实际候选绑定 diagnose 后，未 patch `selected_analysis`：下一次 Mock Provider 请求确实带 T1 `research_analysis` Schema；原绑定器恢复候选、MuJoCo 操作和完整冻结协议，原验证器接受科学变量。25 callbacks 被原 24 cap 拒绝，未触达 Worker。
- T2 ready：只读复用 A 的三点/五点合成结果，在测试中给出“正式 scope + 尚余一次数学”的视图前提，原方法显示 ready/executable，原 v2 请求和 Schema 有效；原 Store 字段/预算没有改动，没有重新算 T1/T2。
- unsupported：复用 A 的 M5 方法适用性测试，保留“native direct 可用，Reach T1/T2 与 affine 方法不覆盖该任务”的区别。

因此没有复现阻止合法数学请求的工程问题。未授权、缺源/设置、缺可比 T1、预算不够及不支持的任务，仍是原接口的真实状态。真实 Provider 连通性、当前账户模型可用性和数学运行时数值表现未在 B0 验证，不能由 Mock 结果代替。

原 A 已验证 dispatch → Store → Reporter → Main 的模拟证据交付、来源/单位和预算；本轮不重复该链。没有新包装、求解器、来源库或批准层。

## B1 的具体配置与准备状态

[待批准配置](../../configs/research/study_p63b1_m1_math_draft.json) 已通过原 resolver/prepare，独立 Store 位于：

`D:/softrobot-agent/.worktrees/p6-3b0-math-study-preparation/runs/research/p63b1-m1-central-high-knowledge-20261029`

Study ID：`p63b1-m1-central-high-knowledge-20261029`。冻结 resolved identity：`866dd41109a824c6cebddeca7df15fd4b8d67ebf5bd4ba839c3b7ab0a838ec0d`。准备后 candidates={}、reference_candidate=null、无控制或科研结果；所有真实执行计数为 0。交付代码提交后用原 bind 绑定干净 checkout；授权前仍由原 require_authorization 阻挡 Provider 和科学执行。

| 项目 | 冻结内容 |
|---|---|
| 任务 | `bf7_shared_reach_v1_central_high.json`；有原 M1 可行见证，未导入见证结构/控制 |
| 时间与验收 | horizon 0.6 s；control/sample 0.02 s；dt 0.001 s；末端 0.01 m；holding [0.54,0.60] s、位置 0.01 m、速度 0.03 m/s；原 TaskAdapter/evaluator 不变 |
| 起点与空间 | FamilySpace agent_choice，无初始科研候选；段数 1–3、腱数 3–6、12 cells/segment、冻结零初态；原域内长度、Young 模量、截面维度、路由半径/相位可供 Main 自选 |
| Provider | 沿用 `runtime_p5_luna_none.json`：chatgpt_gateway、`http://127.0.0.1:8787/v1`、gpt-5.6-luna；Main/Reporter 均 reasoning=none；不读凭据、不探测网络 |
| Provider 总额 | 8，含 Main、Reporter、失败请求；其中 1 个保留 closeout。首次监督 `max_new_provider_requests=8`，没有自动续窗/补额 |
| 公共操作 | 总额 32，其中 2 个 closeout |
| 数学 | 共享总额 4，规模按三 T1 + 一 T2 规划；T1/T2 冻结注册但可选；其他原合法数学方法仍可在各自准入与共享额度内选择 |
| Native 控制搜索 | 每请求 evaluation_requests≤24、iterations≤3、knots_s 数量≤4；Main 选实际 settings 和有效系数 |
| 独立物理评价/NMPC/RL | 全为 0；offline NLP/BDF 为 0；无 SELECT 任务成功路线 |
| Knowledge | **Knowledge-enabled procedural**，不是 blind。`mode=enabled, allow_benchmark_answers=false`；准备时原 manifest 冻结 16 条可读知识，九条 success_case 全部不可读 |
| Reporter | 原确定性事实与 source pointer；原只读模型解释、计入同一 Provider 池；可因 closeout 保护而跳过解释，不能替 Main 决策或授予正式阅读信用 |
| 历史导入 | history/mathematics/control_seeds/background/supplied_evidence 均空，无成功结构/控制/预算继承 |

域授权是可发现的研究选择，不是要求使用哪一组变量。T1/T2 也不是强制动作；不因 Main 选择其他合法方法就改成段长差分。

## 真实成本口径与监督边界

按现有 native T1，一次占一个数学 allowance，最多 24 cloned rollouts。完整初态单条件每 rollout 约 600 物理步，因此三份 T1 的算术规模为最多 72 rollouts / 43,200 steps；T2 占一个数学 allowance，无新 native 模型/积分。已有 T1 的固定控制基线就是对照，不再额外计一份 Solver。

**4 是共享额度，不存在单独“三份 T1”硬计数器。** 若 Main 将四次全用于 T1，则原配置最多 96 callbacks / 57,600 steps，而不是 43,200。这不是自动许可增加预算；是同一配置内的另一种合法分配。不得在报告中把 nominal 三点计划冒充实际程序强制的配额。其他原合法方法按其真实模型/积分/内部求解与原准入计数，不把 T1 的 callback 上限误用到它们。

Native 的 `cost.physics_steps`、physics_step_attempts、rollouts、model_builds、kernel_wall_s 与 charged_numerical_s 保留原记录。必要 prefix reconstruction 已含于原 physics_steps；完整 time-zero T1 本身没有历史前缀重建。失败/不完整记录保留实际或 lower-bound，缺数据表示 unknown；T2 引用旧 T1 成本不二次扣费。独立 physical_launches=0 与 native 数学产生积分步是不同口径。当前没有累计 native steps 硬 cap，不新增一个伪装成现有预算的检查器。

A 的两条原 M1 native 实测（见原 `p63a_tool_support.json/historical_resource_examples`）可给初始时间量级：24 callbacks 约 1.37–1.39 s kernel/候选，再有原样本约 1.1–1.4 s parent/process 差额；三份约 7.5–8.4 s 加 T2/Store/Reporter。它只是在相近硬件/模型下外推，段数、网格、控制维度和方法改变后时间未知，不是新测量或 wall-time 硬上限，也不是 CPU 时间。B0 不运行吞吐测试。

8 个 Provider 请求含发现、查询、切换工具、修正、Reporter 和反馈后决策，可能不足以完成数学调用及后续自主研究。达到窗口上限即停：区分“尚未进入数学”“已调用但无后续 Main 判断”“已有证据判断”，不能为了凑三点继续。Reporter 保留原 closeout/下一次 Main 请求保护规则。24 callbacks 下可能只完成部分控制探针，搜索未收敛或 T2 unresolved 都可以成为研究证据，不应因此改优化器。

## 用户单独批准后才可启动的方案

本文件和 config 是具体批准对象，不是执行授权。B1 批准需涵盖该 Study/resolved identity、冻结的本地 gateway/model、任务与必要候选/请求/结果/获准知识片段的数据发送范围、Main/Reporter 共用 8 请求、数学总额 4 及其 Native 积分成本、原续接机制与 closeout。不会发送凭据或无关文件。若更换 Provider、知识方案、任务或预算，应在执行前另行明确冻结方案，不能修改已运行 Store。

批准后用已有 `formal_study_authorization` scope 记录机制匹配 study_id/resolved_identity、Provider、budgets/capabilities、execution_scopes=registered mathematics；不再创建批准包装器。按原机制登记本窗口的 request-feedback continuation admission，再用同一已绑定 Store 启动：

```powershell
# 仅在用户另行批准且原 scope/continuation 记录完成后执行；B0 没有运行此命令。
D:/softrobot-agent/.f3-prestudy-env/Scripts/python.exe -m tools.research run --run-id p63b1-m1-central-high-knowledge-20261029 --session-handoff --max-new-provider-requests 8
```

监督只检查授权、绑定、原限额和真实结果，观察原请求/回执与下一次 Main 决定。成功标准是 Main 是否自主提出可检验问题、发现合适工具/参数/指标、构造合法数学请求，并依据其实际证据决定下一步；不以是否复现三点/五点、长度差分、任务通过或特定方法序列判定成功。不得替 Main 填科学选择或把错误请求自动改成另一个研究路线。

## 测试、兼容与停止

新增 2 项测试，复用 2 项已有测试，共 4 项通过（21.623 s）：

- `tests.research.test_p63b0_preparation`（授权条件下的真实 SDK Mock wire；只读 T2 ready）。
- `test_p63a_math_interface.test_candidate_parameters_task_units_and_l0_wire`（补类别语义断言）。
- `test_p63a_math_interface.test_task_coverage_stays_method_specific`（unsupported 原边界）。

本地 execution_environment 仅做原解释器、线程和依赖 import 检查，status=ready。`git diff --check` 通过。未运行全套回归、五候选 fixture、真实 Provider、数学/物理 Worker、NMPC 或 RL。B0 真实 B1 Store 没有授权事件；测试 approval 只存在独立显式合成 Store。

待真实决策实验回答的问题：Main 会选什么科学问题和方法、能否在小窗口内找到正确请求入口、如何分配有限搜索机会、收到不确定结果后如何修订假设。这些不是继续改架构的理由。B0 已通过，建议结束工程开发，直接申请 B1 的上述执行授权；本任务完成后停止。
