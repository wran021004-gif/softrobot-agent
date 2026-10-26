# A1：数学工具与 Agent 研究接口集成

2026-10-26，Asia/Shanghai。工程集成完成；没有验证 Agent 科研效率提高。

## 基线、来源与隔离

- 分支：`integration/research-next`；独立 worktree：`D:/softrobot-agent/.worktrees/research-next`。
- 集成基线：`fix/c31-scientific-decision-feedback@e52b71c9e`。
- 数学来源：`research/mujoco-native-task-sensitivity@618fba9a1`。
- A4.5 来源：`research/a45-full-task-sensitivity-validation@628fac6c1`。
- B2 仅作参考：`research/b2-math-decision-benchmark@2aba47901`。
- C3.1 与数学/A4.5 的共同祖先均为 `c153e1731`；A4.5、B2 相对数学来源的共同祖先为 `618fba9a1`。

开始时主工作树为 `feat/gvs-dynamics@d629a80d0`，有其他任务的未跟踪环境和 runs 文件；保持原状。
本地及远端均未发现目标分支，才从指定 C3.1 提交创建新分支。
只对共同祖先至数学来源的生产代码补丁做三方移植，没有整体 merge 实验分支。
A4.5 只取固定控制数据缺失重优化 scope 时的跳过规则，以及相关离线测试。
B2 的实验程序、配置、数据和分支内容均未移植。

## 实际生产代码闭包

| 文件（相对仓库根目录） | 必要用途 |
|---|---|
| `tools/research/nonlinear_capability.py` | 复用来源的 T1 best-found 解释、保存证据 T2 比较及任务采样敏感性；无新算法 |
| `tools/research/native_analysis.py`、`native_control.py` | 接入既有 native 搜索、冻结初态/控制、机制与逐采样数据、失败进度 |
| `tools/research/analysis.py`、`execution_worker.py` | 原准入、worker、恢复、控制交付与计费路径接入 T1/T2；T2 不积分 |
| `tools/research/contracts.py`、`config.py`、`task_constraints.py` | 请求契约、显式版本授权、原候选数学目录中的可用性与请求模板 |
| `tools/research/optimal_capability.py`、`core.py` | 冻结 FamilySpace 参数解析、合法性与原 capabilities 查询 |
| `extensions/tendon_family/family_space.py`、`mujoco_analysis.py` | 实际参数域/物理作用分类、原生机制数组、峰速状态与失败成本 |
| `tools/research/capability.py`、`evidence_views.py`、`research_context.py`、`evidence_policy.py` | 原 ResultCard、mathematical_decision_view、L0/L1 中投影结果与科学边界 |
| `tools/research/budget.py` | 当前 Study 的 T2 零积分成本与失败已知小计；不重计引用的 T1 成本 |

三方应用的显式冲突位于 `evidence_views._resources`：保留 C3.1 的 `native_*` 名称、缺失值 unknown 和原始来源，
补入模型构建、T2 自身聚合及准备时间；同一 native rollout/积分成本只展示一次对应资源。

另外处理了三处语义冲突：

1. C3.1 的有限失败解释原先只匹配 `mujoco_direct_control_v1`，现同时覆盖 T1。
2. 数学来源的 L0 压缩会清除所属 Study、证据限制和成本范围；集成后保留这些字段。
3. 数学来源对生成候选的 fixed-input 结构分析新增了参数授权要求。
   旧模量/截面方法继续按原 analysis 权限调用并在参数视图可见；新增参数范围和 T2 仍按冻结授权检查。

没有修改 Agent 调度、Reporter 实现、Handoff、SELECT/STOP、验收评价器或历史导入权限。
EvidenceQuery 的空 fields Schema/运行时规则及其修正查询原样保留。
没有新增 View、Store、Reporter、数学目录或调度器。

## 能力和证据边界

- 旧冻结 Study 的 16 项数学方法全部保留；新增 T1/T2 仅在冻结 `mathematical_methods` 显式授权时进入目录。
  原 affine/conic、局部分析和 controlled sensitivity 方法继续使用原入口。
- T1 报告指定候选、其冻结初态、原始绝对张力序列、有限搜索设置、best-found signed J、停止原因和原始来源。
  全局最优性未建立、收敛未决；有限失败不证明结构不可行，也不排除控制参数化、权重或求解器限制。
- T2 比较合法且可比的已保存 T1，区分固定控制、有限预算重优化、耦合路径和离散比较。
  结构变化只表达有限观察；重优化最优结构梯度和严格改进方向未建立。
- A4.5 保留 `fixed_control` 局部预测；缺少重优化数据时不制造 `reoptimized_control`。
  4/4 留出分类正确只涉及原采样任务、结构、控制和扰动；没有全域、连续区间或数学误差界保证。
- 历史模型见证只可作为历史参考，不获得新 Study 的物理通过、执行、SELECT 或支出信用。
  新 Study 不能把旧实现/旧所有权的 T1 冒充当前 T2 输入；原绑定和冻结实现检查继续有效。
- native rollouts、physics_steps、优化 callbacks、准备/worker 时间保留实际来源。
  callback 与优化评价描述同一批 rollout；prefix reconstruction 已在 native 积分数中。
  T2 引用的 T1 成本已先前计费，聚合只计自身评价和实际时间。
  失败进度保留已知积分下界，完整成本仍为 unknown；独立物理回放及验收成本单列。

## 定向验证

使用已有 `D:/softrobot-agent/.f3-prestudy-env/Scripts/python.exe`，未安装依赖。
默认 Python 首次缺少 MuJoCo，切换上述已有环境后相关测试通过。
新增两份来源测试文件，并仅对既有测试补入授权/交付回归；无全仓测试。

**28 项不同定向测试最终通过：**

| 测试来源 | 项数 | 选择范围 |
|---|---:|---|
| `test_nonlinear_capability.NonlinearCapabilityTests` | 5 | signed J、成本、未决/不可比、保存绑定、授权与目录 |
| `test_native_task_sensitivity.NativeTaskSensitivityTests` | 7 | 留出、单位、切换、裁剪、固定控制 scope、L0 物理路径、接触失败 |
| `test_mujoco_reoptimized_structure.StructureProbeTests` | 2 | `test_generator_and_source_bind_each_own_zero_state`、`test_registered_acceptance_uses_new_backend_samples_and_no_gradient_claim` |
| `test_research_reporting.ReportingTests` | 2 | `test_math_card_preserves_existing_summaries_and_conclusion_strength`、`test_internal_card_does_not_grant_select_eligibility` |
| `test_b_decision_evidence_clarity` | 6 | 原目录 1 项、ScientificFeedbackTests 原 3 项、新 NonlinearIntegrationTests 2 项 |
| `test_f3_family_sensitivity.FamilySensitivityTests` | 2 | `test_sparse_defaults_and_actual_generated_geometry`、`test_grant_and_cost_boundaries` |
| `test_mujoco_analysis.NativeAnalysisTests` | 1 | `test_structure_context_requires_single_fixed_parameter`，补旧生成候选无 T2 grant 的回归 |
| 数学来源 `test_family_nonlinear_parameters.FamilyNonlinearTests` | 3 | `test_multiple_independent_and_coupled_directions_share_baseline`、`test_catalog_exposes_exact_admitted_requests`、`test_failed_worker_settlement_keeps_partial_cost_in_original_ledger` |

最后一组直接加载来源 `618fba9a1` 的三个函数，使用集成分支生产模块；未复制完整测试文件或执行其真实 smoke。
失败 worker 验证使用明确的人工夹具和模拟调用，不启动实际 worker。
新投影测试曾因复用共享 Mock 夹具出现测试污染，改为每项独立的只读封存边界后与原 C3.1 三项一起通过。

另有两类零积分核验：

1. 数学模块/契约正常导入；从数学来源已完成 Store 以 SQLite `mode=ro` 读保存 T1/T2，逐项核验
   ResultCard 数学量、资源来源、L1 和 L0 范围。读取前后源数据库 SHA256 相同。
   A4.5 用原 `numerics.archived` 校验封存包及成员哈希，原 evidence_read 读通结构/控制各 13 行预测和决策复核。
2. 复用 `c3_frozen_audit` 重投影 A/B/C 原决策边界；源状态、原 16 方法集合和不可见的最终 R1 引用均与 C3.1 相同。
   共检查 86 条查询：85 条可读；B 的一条历史 read_coverage 动态查询仍缺 `measured_control_initialization`，
   与 C3.1 原 treatment 结果完全一致。现行推荐查询可读，没有新增失败或历史信用。

精确证据索引（保留原所有权，没有复制档案）：

- T1：`2b1649587e228fe5359297759606aeea559f824d4a3ff6727bf39eae8e9b6896`。
- T2：`d444dbfc760330bfe1e6643b5315762d4dc8e15b18b7cc6aaf4762179215c0e2`。
  对二者分别用 `view=working_set`、`pointer=/mathematical_decision_view/nonlinear_capability` 或
  `/mathematical_decision_view/nonlinear_response`；详细原数据由内含 query 指向。
- A4.5：`1def36950da6336112258345698617c044079ec207d87aab3cbea394c9f4544a`，
  `view=full`、`pointer=/predictions/structure/samples` 或 `/predictions/control/samples`；
  原包在来源 worktree 的 `evidence/a45_full_task_sensitivity_validation/store_archive`。
- 本地核验短包和 A/B/C 重投影在本 worktree 忽略的 `runs/a1-offline/`，不作为新科学证据。

本轮新增物理积分、Provider、实际数学/native/NMPC/PPO/正式科研 worker、独立物理评价和完整 Agent Study 均为 **0**。
没有重跑 R1、A4.5、B2，也没有复制大型历史 Store 或原始实验档案。

## B 线后续接口与剩余问题

B2 已记录的外力支持缺口仍未集成：native `assessment`/`NativeModel` 与理想张力回放继续显式拒绝外载。
负载任务需要在两条既有路径使用一致的时间、受力实体和参考系，保留原评价器和实际成本，再另行授权匹配输入的独立执行。
普通后端已有施力循环不能证明这条完整链已接通；本分支没有静默去掉外载或宣称负载通过。

下一轮应沿用当前候选/任务/控制/冻结实现绑定、原 mathematical_capabilities 和 ResultCard 查询、原预算与独立验收入口。
改变控制、初始化、采样任务或模型后，A4.5 局部预测与历史有限预算趋势不能直接迁移；未来决策收益尚未验证。
没有已知当前集成阻塞；以上外力缺口、最优性/跨模型/物理验证及原陈旧历史查询仍是明确限制。

## 提交与交付

- `56de2887705395b700b007aac8082c34c1054c16`：数学核心、最小依赖及来源离线测试。
- `da2d21bf5071ee48c1bcfcb7a71d66a86de1574b`：C3.1 科学边界、资源投影、L0、当前成本及旧授权兼容。
- 本报告为独立收尾提交；交付 HEAD 为包含本报告的提交，最终完整哈希在任务交付消息中记录。

均以普通提交推送 `origin/integration/research-next`，无 force push、无基线分支合并。
