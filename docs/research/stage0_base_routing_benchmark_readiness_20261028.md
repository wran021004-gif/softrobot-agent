# Stage 0：Base-only 腱路与跨任务接口交付

日期：2026-10-28（Asia/Shanghai）。本次仅工程集成、历史只读审计与无积分 fixture；没有 Benchmark 求解、Study、Provider、NMPC 或 PPO 科学执行。

## 基线与隔离

- 远端 `origin/integration/research-next` 经 fetch 后仍为 `455ec55347ce6ab05cfbf71ad439044e9db77aca`，与任务推荐一致。
- 独立分支 `feat/stage0-base-routing-benchmark-readiness`；worktree `D:/softrobot-agent/.worktrees/stage0-base-routing`。
- 本地集成分支为 `618bb16b2a42a1be93ca80c527e4608d67e30371`，比远端多一笔研究归档、Agent 生成提示和 search 提示提交；未纳入本次基线，也未发布该未推送研究归档。
- 原工作树 `feat/gvs-dynamics@d629a80d0027` 有大量既存未跟踪运行文件。原工作树、集成 worktree 和其决策架构修改未操作。参考研究 worktree 的 tracked status 均干净。Git 历史及现存 worktree 的相关生成源码中未发现另一个 Base-only 实现。
- 基线复现另用 detached `stage0-baseline455`，不改集成分支。不 merge、rebase、cherry-pick 研究历史，不改冻结任务、历史 Store 或证据。

## A. 实际执行契约

复用现有 `serial_family_space_v1/v2`、`serial_family_generation_v1/v2`、builder 和 compiler。在已有 `conditional_rules` 字段中新增明确版本 `base_only_consecutive_spans_v1`，它参与 `family_space_identity`，不引入新的生成器或顶层契约版本。

新公共设计空间：[family_space_stage0_base_only_v1.json](../../configs/research/family_space_stage0_base_only_v1.json)。它通过已有单层 `base_space` 机制复用公开 v1 prototypes，沿用公开 v2 的串联规则及数值域，没有历史成功参数或控制。

在**新的、另行冻结的** Study 中将 `family_space` 指向此文件即可采用新规则；已有 TaskDefinition、Study、默认空间和历史身份均不迁移。任务专用空间若须保留工具负载/控制域，应保留其实际定义并显式选用同一 `conditional_rules`，另行冻结。该规则也适用于已有 v1 两段入口；改写请求版本不能绕过冻结空间规则。

| 项目 | 新空间执行规则 | 旧空间兼容 |
| --- | --- | --- |
| spans | 每个显式 `first_segment` 必须为 0；默认 span 仍覆盖全链；`last_segment` 选择终止柔性段 | `selected_segments_and_consecutive_spans_v1` 原义保留；`first_segment>0` 实际起于该段前的 guide |
| 路径 | `fixed_base/start`，零或多个 `guide`，一个终止 `anchor` | 历史构建及其 compiler 角色检查不变 |
| overrides | 原顺序精确使用，再做同一 Base/角色检查；空路径、非 Base start、重复 start、假 Base hole、错 anchor 均拒绝 | 不重解释、补点或重排历史 route |
| 几何 | 继续复用站点唯一递增、span/anchor 归属、截面避让、独立 Base 起点间距、导向孔所有权/间隙、compiler 与几何有效性检查 | compiler 不作全局 Base-only 修改，历史物理设计仍可读 |
| 公开生成 | `research_plan(generate)`、`generate_candidate`、`generate_family`、registry builder 的授权复算共用同一校验 | 选择旧空间是显式选择旧的冻结科学域，其身份不同，不是新空间的逃逸入口 |
| 搜索 | `whole_chain` 保持原义；新增 `base_to_distributed_anchors`：通道 j 从 Base 到 `j % segment_count` 段 | `distal`、`distributed_consecutive` 保持原物理含义，只在旧规则空间适用 |

`search_domains` 在提案/评价前拒绝新空间中的旧策略；`mixed_moves.generation` 也检查策略适用性，防止直接调用提案函数绕过。旧策略即使碰巧在单段退化为 Base 路径，在新空间中仍明确不适用。新策略不声称保留旧 distal-only 力学作用。

同一冻结空间下，默认与物理等价的显式 spans/override 继续重用候选；改变实际 anchor/路径会改变物理身份。规则变化导致空间身份改变，旧候选不能直接重绑到新空间。未重算或覆盖任何历史 identity/digest。无效构建只保留原构建耗时/失败记录，不发出数学或物理评价。

能力说明沿用 `decision_summary` 和现有搜索请求 guidance。生产代码仅改 `family_space.py`、`generated_serial.py`、`mixed_moves.py`、`search.py` 及必要的搜索策略枚举；`compiler.py`、`design.py`、Agent、上下文、Store、预算、Reporter、Provider、NMPC/PPO 与积分内核无需修改。

## B. BF2 / BF4 / BF7 历史合法性

这里的合法/不合法仅指**新 Base-only 结构规则**。历史中段起点不违反当时冻结契约，不能据此否定历史结果。合法路由也不表示任务可行或可公开迁移隐藏答案。

固定来源：

- **B2**：`research/bf1f2-benchmark-discovery@ce2feacdcf3a4f194f33f7fcbf804c55a75ee90d`。任务 `tasks/bf2_multidirectional_hold_frozen_v1_{zero,positive,negative}.json`；协议 `configs/research/bf2_multidirectional_validation_v1.json`；公开证据 `evidence/bf2_benchmark_validation/{summary,selection,audit}.json`。私有只读根 `D:/softrobot-agent/.worktrees/bf1f2-benchmark-discovery/runs/bf-hidden-20261026`。
- **B4**：`research/bf4-cross-family-benchmark@8a6a15d4667b946d4e1dd6b20e544cc8d683452a`。任务 `tasks/bf4_tracking_direction_change_v1.json`；冻结/公开证据 `configs/research/bf4_tracking_s2_freeze.json`、`evidence/bf4_tracking_s2/summary.json` 及相应 S1/S3 文档。私有只读根 `D:/softrobot-agent/.worktrees/bf4-cross-family-benchmark/runs`。
- **B7**：`research/bf7-shared-structure-benchmark@5dc576f43e0ac0d9599d8857ee36c6d3b6e253be`。任务 `tasks/bf7_shared_reach_v1_{positive_high,negative_low,central_high}.json`；`configs/research/bf7_{protocol_v1,r2_protocol,native_protocol_v1}.json`；公开证据 `evidence/bf7_final/independent_witness.json`、`evidence/bf7_native_v1/`。私有只读根 `D:/softrobot-agent/.worktrees/bf7-shared-structure-benchmark/runs`。

下表起点按 `tendon_0..5` 顺序；`B=fixed_base/start`，`G=guide_1/start`。BF2 使用 v1 生成语义；两种私有候选均无 route override，不公开完整设计映射或成功控制。

| 历史任务/结构 | 实际起点 | 新规则分类 | 证据位置/完整性 | 可否作为新 Benchmark 结构 |
| --- | --- | --- | --- | --- |
| BF2 H0、H1（三个抗扰条件，各两种起始控制） | B B B B B B | 合法 | B2 私有 `bf2-candidates.json` 与 `bf2/candidates.json` 一致；manifest identity `5bf0d1e873def0db44a83dae27db815c61caa9350be2226f7f5e000d18d99892` 与冻结协议一致；`bf2/*/{zero,positive,negative}/*/configuration.json` 共 24 份实际配置均核对 receipt 文件哈希和起点。科学实现 `15521172b` | 路由规则兼容；**不能把私有成功设计复制为公共起点**，公开 Benchmark 须另行冻结设计域 |
| BF4 engineering、S1 full-span、S1B | B B B B B B | 合法 | B4 `bf4-{engineering,s1,s1b}/private-store/platform.sqlite` 实际 candidate；S1/S1B 实现 `948a53868144` / `d8859b5fc4b1` | 公开全跨度结构可在新空间显式再冻结；不继承旧验收 |
| BF4-S1 两个中段起始变体 | B B B G G G | 不合法 | B4 `bf4-s1/private-store/platform.sqlite`，两个不同物理结构；有效 artifact 引用见下一段 | 需把后三根腱重新设计为 Base 起始，保留/重选终止段；不能声称物理等效 |
| BF4-S2 full_span，02/06 两组 | B B B B B B | 合法 | B4 冻结 `candidate_requests.full_span`，以及 `bf4-s2/full_span-{02,06}/private-store/platform.sqlite`；实际构建实现 `f5d30b2b2caa` | 公开路由可复用，须新空间冻结身份；历史失败不改 |
| BF4-S2 split_span，02/06 | B B B G G G | 不合法 | 同一冻结的 `candidate_requests.split_span`：后三根 `first_segment=1`；两组实际 Store 均核对 | 后三根改为 Base 起始，作为新的物理结构 |
| BF4-S2 redistributed_lengths，02/06 | B B B G G G | 不合法 | 冻结 `candidate_requests.redistributed_lengths` 仍含相同 split routing；两组实际 Store 均核对 | **只改段长不能解决起点问题**；还须重新设计后三根路径 |
| BF4-S3 首次失败构建 | 无已物化 candidate | 无法判断 | B4 `bf4-s3/structure-search/private-store/platform.sqlite` 无 generation candidate；`evidence/bf4_s3_initial_failure/summary.json` | 否；不能从失败请求推定一个已生成结构合法 |
| BF4-S3R1 搜索的 5 个结构、control_only、structure_first | B G B G B G | 不合法 | B4 `bf4-s3r1/{structure-search,control_only,structure_first}/private-store/platform.sqlite`；`distributed_consecutive` 实际候选，而非从报告推测 | 奇数通道须改为 Base 起始；新规则的分布锚点策略是不同拓扑 |
| BF7 v1 三个数学提案及 best/peer 结构 | B G B G B G | 不合法 | B7 `bf7-v1/{math,best,peer}/private-store/platform.sqlite`；math 实现 `7cacc71d5deb` | 不可直接用；奇数通道重新路由 |
| BF7 R2 两个提案及共享三条件见证 | B G B G B G | 不合法 | B7 `bf7-r2/{math,best}/private-store/platform.sqlite`，共享候选 artifact `b40392cf842a980e57d2507512fa6549a6cc361eb12447d9f2148575c6702e38`；私有 witness 的 generation records 交叉核对；实现 `8deb8c5e4d90` | 旧共享见证保留；不可移作新规则可行见证，须新结构与另行授权验证 |
| BF7 Native A/B 及 refinement | B G B G B G | 不合法 | B7 `bf7-native-v1/{screen,refinement}/private-store/platform.sqlite`；screen 两个实际结构、refinement 一个；实现 `48d090311085` / `8e6b65a82ec0` | 同上；不能仅改 spans 声明而保持旧真实路由 |

Store 审计均用 SQLite URI `mode=ro`，只选含 `generation_version` 的顶层 candidate，读取其 `configuration.robot.structure.data.tendons`；验证 artifact body 的 SHA-256 等于 Store key，不调用 Host.prepare、恢复或历史实验驱动。BF4-S1 中段变体的实际示例 artifact 为 `5267a4427e13b0245a88aa206f91a9c6cfb5be1086f8f11c60e93c6db1368c7c`。BF4-S2 三类 02 组示例依次为 `87cd17bb16a134b3b01bb409f5ce36d1dff39acaba8d76782c41fc5e871ff7c5`、`b3f6dd613e0a580b98c36cf23e3dcd3ecf2a29d13fdce365455f207590fe7af4`、`2f466a2ee8cc8c58b06e3dbdd2f409770829d7ade97f891adf899ebbdfbbc76f`；06 组独立核对，起点相同。私有数据均未复制进本分支配置或交付文件。

以上是来源和新规则分类审计，不重跑几何/任务性能，不修改旧成功率、成本、失败、SELECT 或验收记录。BF7 R2 的历史 joint SELECT 限制仍按旧公开证据记载；当前基线已有按各 condition 身份检查的修复，本次无须修改。

## C. 跨任务工具矩阵

以下能力**已有，无需修改**。统一 `ResearchTaskAdapter/task_adapter`、原 Registry、`conditions.py`、`native_control.py/local_control_search_v2` 和 `physical_replay`。表中的支持均还要求实际冻结授权、模型适用性、完整时间窗与合法候选，不表示本次执行过物理任务。

| 任务 | Registry / evaluator | adapter / 条件 | Native | math | replay / joint SELECT |
| --- | --- | --- | --- | --- | --- |
| Reach/Hold | `task.reach` / `evaluate.reach` 加原保持窗组合验收 | 终点、保持位置/速度、时间网格 | direct control、Reach T1/T2；结构搜索逐条件重新优化控制 | GVS/CONIC 局部覆盖，非物理验收 | 原独立回放；2/3 个冻结条件、同结构/mesh、独立控制及完整收据 |
| BF2 多方向 COM 外力 Reach/Hold | 同上；冻结外力、原 evaluator 不改 | 每个条件保留世界系力、时窗、COM 作用点 | 已有 COM 力逐步施加/叠加、Native 准入 | GVS/PCC/SoroSim 外力敏感用途拒绝；不能以无外力代理代替 | 原完整任务/保持窗及来源检查；多条件接口已有 |
| BF4 Timed Tracking | `task.tracking` / `evaluate.tracking` | timed reference 的每个规定采样点 | `mujoco_direct_control_v1` 已有；Native 结构 T1/T2 搜索不支持 | 已有 sampled timed GVS/CONIC，仍是局部代理 | `offline_timed_tracking_v1`；真实误差完整网格，单项 SELECT fixture 已验证 |
| BF5 位置 + 工具轴 | `task.position_tool_axis` / `evaluate.position_tool_axis` | 位置和有向轴两个约束 | direct sequence 已有，T1/T2 不适用 | affine/GVS/CONIC 不覆盖完整轴约束 | 原位置/方向评价及源绑定；公共 fixture 已验证 |
| BF6 负载定向 Tracking | `task.oriented_tracking` / `evaluate.oriented_tracking` | timed 位置/有向轴；真实工具质量、COM/惯量与接触检查 | direct sequence 已有，T1/T2 不适用 | 不支持完整方向任务，不降格为位置成功 | `offline_oriented_tracking_v2`；负载绑定/完整性/每步无接触证据，fixture 已验证 |
| BF7 三条件 Reach/Hold | 复用 `task.reach` / `evaluate.reach` | 三个实际任务、同结构、独立种子/控制/评价 | `family_mixed_search_v1` 的 `mujoco_control` 模式遍历各条件，取有限预算各自 best-found J 的 max | 旧 mathematical_proxy 搜索仅根任务；不冒充多条件或完整验收 | 独立 replay 后全条件 joint SELECT；缺条件、错结构、错源、未读证据均拒绝 |

能力边界核对：

- NMPC 已有 Reach/Hold 与 timed/geometric Tracking 路线，仍需模型与场景准入；BF5/BF6 不支持有向轴 NMPC。外力敏感的 GVS 模型不得假装已表达 BF2 扰动。
- PPO 仍仅在 Reach/Hold 或 untimed geometric Tracking 的任务语义上条件适用，外力场景等还会被原准入拒绝；BF4 timed、BF5/BF6 在 scene/XML 前明确拒绝。
- Native direct-control 的跨任务能力不传递给 Reach-only T1/T2。Native family search 当前只允许完整 Reach/Hold 时间窗，未实现 Tracking/工具轴的结构—控制 T1 搜索。
- `mathematical_proxy` 多条件共同评分未实现；Native 模式已有逐条件评分。单条件数学结果、共享 Native J 和局部优化停止均不等于完整验收。
- 联合 SELECT 仍要求全部冻结条件的独立回放、原评价/profile/raw 来源、同物理结构/mesh 和证据读取；各任务 family 的存在不表示任意跨 family 组合已适配。当前多条件冻结接口针对 2/3 个 Reach/Hold 条件。
- 无效生成与不适用策略在任何真实积分前拒绝。费用/断点恢复/失败来源由原实现拥有；新测试验证单段物理等价策略的重用不重复计入三条件分析费用。

## D. 无积分验证

解释器：`D:/softrobot-agent/.f3-prestudy-env/Scripts/python.exe`，已安装 MuJoCo `3.13.0`。测试 runner 在 NumPy 导入前设置原单线程环境；无需安装依赖。

```powershell
# 基线：detached 455ec55347ce，复制同一 guard runner；仅指定原七模块
& D:\softrobot-agent\.f3-prestudy-env\Scripts\python.exe -m tests.research.stage0_no_integration `
  tests.research.test_family_space tests.research.test_mixed_search `
  tests.research.test_bf7_native_search tests.research.test_cross_task_integration `
  tests.research.test_bf4_tracking tests.research.test_bf5_tool_axis `
  tests.research.test_bf6_oriented_tracking

# 新分支：原七模块 + 新规则回归 + 选定外力/PPO/T1/T2 边界 fixture
& D:\softrobot-agent\.f3-prestudy-env\Scripts\python.exe -m tests.research.stage0_no_integration
```

| 验证集 | 总数 | 通过 | failure | error | skip |
| --- | ---: | ---: | ---: | ---: | ---: |
| 原七模块，基线 | 52 | 47 | 4 | 1 | 0 |
| 新 Base-only fixture（含原跨任务/Native 检查复用） | 19 | 19 | 0 | 0 | 0 |
| COM 外力、PPO、T1/T2 边界定向 fixture | 9 | 9 | 0 | 0 | 0 |
| 新分支完整定向集 | 80 | 75 | 4 | 1 | 0 |

保留且已在未修改基线复现的原失败：

| 测试 | 基线事实 |
| --- | --- |
| `FamilySpaceTests.test_compact_summary_exact_evidence_and_claims` | 原 summary 长度 5619，不满足冻结 fixture 的 `<4702.2` 断言 |
| `FamilySpaceTests.test_legacy_configuration_identity` | 当前解析 digest 为 `a6446a271e68c152df9c684f792a140b3245a9ab8439817830b09b41d0087dc0`；fixture 仍期待 `31af3e097ad29fef1ffd74c5178a6267fc5ffe35889c63e98f531dd42c0df69e` |
| `MixedSearchTests.test_search_contract_and_legacy_identities` | 同一个既有固定摘要断言不匹配 |
| `MixedSearchTests.test_recorded_exact_six_segment_failure_never_reprobes` | 本机环境不匹配历史 XML-load 失败凭据，fixture 期待 runtime_unavailable，实际 runtime_unresolved；未重探或消耗积分 |
| `MixedSearchTests.test_screening_synthetic_pass_cannot_close_or_select` | 原重复实验准入先拒绝 `EQUIVALENT_SCIENTIFIC_EXPERIMENT_REQUIRES_EXPLICIT_REPLICATION_GRANT`，尚未到 fixture 期望的 final-fidelity 分支 |

原七模块的失败/error 名单在基线与新分支逐项比较完全一致；其余 28 项全部通过，无新增失败。基线 102.816 s，最终完整集 173.386 s。没有为绿灯改摘要、历史配置、预算、权限或无关业务逻辑。初次试跑的 guard 还拦截了 Windows `platform` 读取版本的 `ver` 命令；随后仅放行该只读元数据命令，并在 detached 基线上重新运行，表中使用后一次结果。早期未设置线程变量时的环境准入错误也不计入最终回归比较。

`stage0_no_integration.py` 禁止 `mujoco.mj_step/mj_step1/mj_step2`、可用的 `mj_rollout`、`NativeModel.rollout/rollout_sequence/reconstruct`、真实 Native 计算、外部执行 worker、`solve_ivp`、HTTPX 发送及非只读子进程。既有 fixture 只能用显式替身提供合成评分/回放收据；其中字段里的模拟 physics_steps/成本不是实际积分。本次真实积分、Provider、NMPC/PPO/Study 科学执行均为零。MuJoCo XML/model 构建、静态 forward、数学 shape 检查照常允许。

## E. 交付范围与限制

- 必要改动：5 个生产 Python 文件、1 个公开空间配置、1 个新测试模块、1 个严格无积分 runner、本文。未导入研究驱动、私有 Store、成功控制或历史预算。
- Stage 0 不证明新路由的控制可行性、性能、鲁棒性或 Benchmark 难度；这些需要后续单独授权。不能把历史中段起始见证当作新规则见证。
- 原五项测试问题保留并有基线解释；无新的未解释回归才满足本次交付。没有进入 Stage 1。
- 分支单独 commit/push，不更新集成/决策分支；最终 Git SHA、推送状态与干净 worktree 由交付回复给出，避免在提交内自引用其 SHA。
