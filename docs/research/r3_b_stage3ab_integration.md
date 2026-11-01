# Softrobot-Agent 阶段 III-A/B 开发验收报告

日期：2026-11-01（Asia/Shanghai）。本阶段的注册、真实动态执行、独立评价及原 Study 闭环已完成。验证范围是明确标记的工程任务；未开展自主结构搜索、未调用真实 Provider、未启动阶段 III-C，也未修改或合并 main。

## 1. 基线、分支与提交

核对远端阶段 II.5 HEAD 为 `dd046307fe1cd49240877bdf5cd5baeacee351f2`，与用户指定基线一致。本地来源工作树干净，未发现需要保留的后续提交。开发在独立工作树、分支 `codex/r3-b-stage3ab-passive-study-integration` 中完成。

已发布实现 HEAD：`79a825b23fc20c97f85f279c9cf74d81847b4b78`；代码树为 `664e87d5a05d7210c8acbc3e121d54c6b841af68`。交付提交还包含错误模型来源的 profile 诊断标记及 backend 模型名称元数据校正，不改变任务阈值、物理积分或验收门禁；最终交付 HEAD 见分支及交付文件。

本机原生 Git 推送遇到认证/管道错误，提权后的认证调用无响应，已取消；后续只读 fetch 又遇到连接重置。改用已连接的 GitHub Git Data 接口按原顺序发布每个提交，逐个确认远端 tree SHA 与本地提交树完全一致。原始验证提交与发布提交的对应关系保存在 `evidence/stage3ab_passive/publication_mapping.json`。R3、II、II.5 来源分支没有写入。

## 2. III-A：无控制器真实物理执行

复用原 `PassiveModel`、`compile_xml`、`passive_fixed_payout_v1`、材料点 Jacobian 和 `mj_applyFT`。新增一个职责明确的 `passive_execution.py`，没有第二套 MJCF 生成器、机器人、Replay 平台或控制轨迹。

模型实际 `nu=0`。每个加载 episode 创建/重置真实 MjData，应用冻结的具名初始状态；无载动态前缀属于原始证据。载荷在世界坐标中于每个积分间隔起点刷新，实际调用 `mj_step` 推进时间。末端和材料点位置、速度来自引擎位姿/Jacobian；张力来自实际单侧腱限位约束反力。

保存完整规定采样网格、具名关节顺序、材料点及 tip 绑定、qpos/qvel、腱长/残差/张力/张紧状态、加载阶段与力、接触、求解器迭代及警告。每步检查接触、数值状态、全时域张力和长度极值；编译数、forward、尝试及已完成积分步、episode 数和耗时均保留。已存在的执行目录拒绝重新覆盖。

理想硬约束静力模型仍服务 KKT/机制诊断；MuJoCo 单侧软约束模型负责有限时间执行。二者没有互相替代，也没有为通过任务调整软约束或验收容差。

## 3. III-B：独立评价与原正式闭环

独立 evaluator 从 BackendResult 的实际物理样本计算全部冻结硬条件，不读取数学 Worker 的 task_observations、不求静力平衡、不修改候选。支持沿世界方向/投影的位移、材料点与 tip 速度、位移差形式、实际张力和长度超限、关节诊断以及禁止接触。比例分母为零时返回无效，未用 epsilon 构造有利比值。

结果保持原 EvaluationResult：`valid + task_success=true/false` 对应 valid_pass/valid_failure，缺失工况/网格返回 incomplete，数值失效或错误来源返回 invalid。失效结果没有任务分数或成功标记。

仍使用 `research_plan(action=physical_replay)`、原 execution_worker、Store、pending、receipt、预算及恢复。内部新增 `passive_protocol` route 和 `frozen_passive_protocol_v1` 来源，绑定候选、结构/payout、冻结任务、初态、加载协议和执行模型；Main 仅选择已有候选，无需虚构张力或控制 SHA。

`offline_passive_response_v1` 复用同一 `research.task_acceptance` 合同，检查执行有效性、完整动态采样、全部工况、物理来源、独立 evaluator、全部任务边界和求解器错误。没有被强行映射成主动 holding_coverage/force_bounds。

证书重读原始样本，重新运行独立评价和 profile/acceptance 组装；测试证明把失败 evaluator 和 accepted 标记伪造成成功仍无法获得完整证书。Main 实际收到完整证书之前，开发者读取、Reporter 读取或短摘要都不能授予 SELECT。通过后沿用 R3 的零额外确认 SELECT 自动 STOP。

## 4. Registry、任务及配置

| 身份 | 注册名称 |
|---|---|
| 任务 | task.passive_response@1.0.0 |
| 目标合同 | reference.passive_response_goal@1.0.0 |
| 评价参数 | reference.passive_response_evaluation@1.0.0 |
| 独立评价 | evaluate.passive_response@1.0.0 |
| 无控制声明 | controller.no_active_control@1.0.0 |
| 真实 backend | backend.family_passive_mujoco@1.0.0 |
| 原始数据合同 | family.passive_dynamic_data@1.0.0 |
| 验收协议 | offline_passive_response_v1 |
| 执行模型 | mujoco_passive_fixed_payout_v1 |

新增 `tasks/passive_response_engineering_v1.json`、冻结零响应失败对照、`control_passive_v1.json`、独立 FamilySpace、运行时及 Study 配置。任务硬阈值只由 evaluator 参数拥有；静力 observations 为空，不复制一套同名静力成功标准。无主动控制的配置不再读取 Reach 目标、settling、PPO 或 recipe；旧数学开发任务仍是 not_registered，不自动取得动态验收权。

工程任务为一个小型合法家族候选，1 段、2 cells、1 条固定 payout 腱；这只是冻结开发域，并非通用 backend 的科学上限。每个 episode 从相同具名零初态 reset，重力为零，安装位置 z=1 m，在材料 s=0.5 施加世界 +y 0.01 N / +z 0.02 N 两个工况。0–0.1 s 无载，0.1–0.2 s 线性 ramp，之后保持；0.3–0.4 s 为评价窗口。dt=1 ms，输出周期 10 ms，每工况含初态共 41 个样本。

阈值在第一次动态评价之前已写入并提交，之后没有修改任务文件或放宽指标。主要上限为材料点位移 0.05 m、tip 位移 0.1 m、保持速度 5 m/s、无载 tip 漂移 0.001 m、长度超限 0.002 m、张力 1 N、关节角 1 rad，且禁止接触。宽阈值只用于工程集成验证；不是新的科研 Benchmark 成功标准。

已只读核对历史 PHS 分支 `9d6d160e050c836b87d0563a497fc0ec1c3761a8` 的公开协议。历史 PHS v3 包含重力、不同安装姿态、0.1 N、6 个搜索及 4 个保留工况、更长稳定协议和更严格的运动/约束要求。本任务使用明确的新版本，并未复现或宣布通过 PHS，没有复制历史获胜结构。

## 5. 真实结果、成本与失败

| 最终工程默认装配 | +y 工况 | +z 工况 |
|---|---:|---:|
| 材料点最大位移 | 0.194660 mm | 0.567295 mm |
| tip 最大位移 | 0.445195 mm | 1.306676 mm |
| tip 保持最大速度 | 1.998800 mm/s | 5.913293 mm/s |
| 实际最大张力 | 0 N，松弛 | 0 N，松弛 |
| 独立评价 | 通过工程阈值 | 通过工程阈值 |

两工况共 800 个真实积分步、1 次模型编译、3204 次 forward。最终 SDK Worker 的引擎执行约 0.714 s，进程边界约 1.884 s；原 Store 收据计费 2 个 backend_solves。一次公开 Replay 请求明确包含两个独立 episode，没有把它们隐藏为一个物理额度。

另一个合法的较短 payout 装配产生实际最大张力 6.747986 N，超过冻结的 1 N，且无载 tip 漂移 2.505241 mm 超过 1 mm；独立评价为有效失败。额外的零位移上限负对照同样有效失败。没有因为失败重新调整阈值。

中断测试在第 7 次积分尝试前注入故障：已完成 6 个真实积分步、仅启动 1 个 episode，保留完整失败快照和 partial progress，验收为 invalid。原 Store 维持该请求预留的 2 个物理额度；实际成本明确写出 1 started / 0 completed，没有声称两个 episode 已执行。复用同一个已结算请求不产生新积分或二次计费。

最终 9 项专项测试的一次完整运行共 4006 个已完成积分步、4007 次积分尝试、6 次模型编译。这是该次测试运行的统计，不冒充整个开发过程或其他回归的总消耗；各个独立 Study 的原始账本和失败均保留。

## 6. Main 实际可见接口

实际 Mock HTTP 通过真实 Strands/Harness SDK，Main 发送已有工具的短引用请求，例如：

`physical_replay: {candidate: candidate_7}`

随后选择 `evaluation_43`，读取 `view=acceptance_certificate`，执行 SELECT。加载的 passive Replay schema 不要求 source，也没有单独的 passive_physical_replay 工具。

实际 L0：

`valid_complete: true; accepted: true; reference: evaluation_43`

实际固定事实包含英文 metric、值、单位和冻结阈值，例如：

`evaluator:lateral_response_maximum = 0.00019466041746258637 m; threshold = 0.05; passed = true`

Reporter 被故意设置为 unavailable 后，这些数值仍送达 Main。完整证书也真实送达，SELECT 随后自动停止；未用 Reporter 的解释代替证书。5 个 Mock Main 请求的单次 wire 约 41–68 KB，不包含内部 SHA、完整物理轨迹或额外参考映射。真实 Provider 请求数为零。完整 schema、L0 数值和原始 wire 在本地交付证据目录中。

## 7. 测试与证据

新增专项 9/9 通过；原有指定五个模块共 29 个用例均验证通过。回归批次日志保留了修复前 28/29 的事实；失败的旧被动 SDK 生成用例在修复后单独复测 1/1 通过。没有通过修改旧断言或任务门槛掩盖失败。

覆盖真实默认/不同方向/张紧装配、完整有效失败、缺失工况/样本/状态、错误模型来源、数值中断、冻结 reset、实际成本、预算不足、原收据复用、证书原始数据重算、证书阅读门禁、Reporter 故障、SELECT 自动 STOP、失败合法 STOP、旧数学任务未注册以及原主动 R3 闭环。

远端 `evidence/stage3ab_passive/validation_summary.json` 只发布精简数值摘要和成本，publication_mapping.json 记录等价代码树。完整原始证据保留在本地交付目录“原始验收证据”和“Softrobot-Agent_III-AB_原始证据.tar.gz”：包含三个独立 Worker Study 的 SQLite Store、source 快照、收据、样本、SDK 会话、进度、完整 wire、证书、测试日志及直接工程执行记录。负对照 Store 中带 synthetic_forged 前缀的记录仅为证书反例，不是成功科学结果。自动审批拒绝了完整原始 Store/wire 的外部发布；本次缩小为源码、测试、报告和精简摘要发布，完整原始证据没有加入远端分支。

## 8. 文件变更

源码和配置共 28 个路径：9 个新增、19 个修改。没有移动或删除文件，没有引入第二套 Store、Budget、Reporter、Memory、候选注册表或 acceptance 状态机。以下清单附上文档和证据目录；完整清单也在 validation_summary.json。

```text
A	configs/research/control_passive_v1.json
A	configs/research/family_space_passive_engineering_v1.json
A	configs/research/runtime_passive_engineering_v1.json
A	configs/research/study_passive_engineering_v1.json
M	extensions/reference/contracts.py
A	extensions/reference/passive_response.py
M	extensions/tendon_family/contracts.py
M	extensions/tendon_family/manifest.py
M	extensions/tendon_family/passive.py
A	extensions/tendon_family/passive_execution.py
A	tasks/passive_response_engineering_failure_v1.json
A	tasks/passive_response_engineering_v1.json
A	tests/research/test_passive_physical_acceptance.py
M	tools/research/agent.py
M	tools/research/budget.py
M	tools/research/config.py
M	tools/research/contracts.py
M	tools/research/core.py
M	tools/research/design.py
M	tools/research/evidence_views.py
M	tools/research/feedback.py
M	tools/research/physical_replay.py
M	tools/research/research_context.py
M	tools/research/scientific_intent.py
M	tools/research/state.py
M	tools/research/structure_research.py
M	tools/research/task_constraints.py
M	tools/research_tasks.py
A	docs/research/r3_b_stage3ab_integration.md
M	.gitignore
A	evidence/stage3ab_passive/validation_summary.json
A	evidence/stage3ab_passive/publication_mapping.json
```

## 9. 当前边界与 III-C 结论

当前支持已注册、无主动执行器、固定 payout、接触自由的合法 serial bending 模型与具名初态、冻结材料点外力和完整均匀采样协议。接触/摩擦任务、混合主动被动控制、适应性时间网格及硬件/鲁棒性结论不在本阶段范围。新 passive Study 的额外确认数必须为零；独立多 TaskCondition 聚合也在创建时明确拒绝，不能跳过确认要求。

III-A/B 的通用执行和正式门禁已就绪，可以在另行冻结科学任务、合法结构域及预算并取得相应授权后进入 III-C。当前工程 fixture 只能验证框架，不能作为 PHS 科研成功或自主结构设计成功的证据。本次没有启动 III-C；没有开展大规模搜索或鲁棒性研究。
