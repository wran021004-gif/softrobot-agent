# Softrobot-Agent C0/C1 开发报告

基线为 `codex/r3-b-stage3ab-passive-study-integration` / `35640f0ff2d680bb01f9f9806cda2b0db77ded65`。远端 HEAD 与本地基线一致，原工作树干净。全部修改位于独立工作树、分支 `codex/r3-b-c0-c1-structure-task-bridge`。未修改原阶段分支，未合并 main，未启动 C2 或自主 Study。

C0 检查点为本地提交 `cd356500`；C1 源码检查点为 `b5cea9c1`。发布通过 GitHub 原生工具建立等价代码树，远端提交与本地提交的对应关系随本地交付提供；原始证据继续保留实际执行时的本地 implementation，未重写历史证据。

## 完成内容与边界

C0 增补现有科学冻结清单和被动 Registry sources 中缺失的 `passive_equilibrium.py`、`passive_inverse.py`。`scene.py`、`mjcf.py` 已被原 PHYSICAL_SOURCES 冻结，因此没有再建立另一套清单。独立临时目录中的扰动测试验证变化检测和恢复后的相等性。

TaskAdapter 从冻结 evaluator/protocol 提取上界、下界、载荷、时间窗、信号、单位与来源。`signed_violation` 对上界为 observed − bound，对下界为 bound − observed；非零冻结边界的绝对值提供明确正尺度。零阈值、缺测和数值无效不会得到任意 epsilon 分数。原 acceptance 和证书仍决定正式验收；新诊断字段不改变原验收条件。历史证书缺少新诊断字段时，所有原字段仍精确比较；若新字段存在也必须重算相等。已只读验证原 III-A/B 封存证书仍完整有效，伪造诊断不能获得证书。

单次 Main 请求准备共享临时 Store 读取快照、短引用集合与已确认交付解析，退出即丢弃；没有持久缓存、第二账本或新状态机。L0 中重复 TaskGap 卡片只保留一处事实，完整约束仍可按原 evidence 路径查询。V4 默认动作及 diagnose Schema 不再重复展示 `single_parameter_effect`，历史编译语义仍兼容。

C1 新增 V4 内部效应 `finite_time_task_response`，仍属于原 `research_analysis` 的结构领域。它固定原初态、采样网格和全部加载协议，调用原 `passive_execution.execute`，由数学研究和独立 evaluator 共用纯函数 `task_metrics` 提取物理量。完整动态观察不是独立 Replay，不产生证书或 SELECT 资格。

新能力描述分别给出 actuation、constraints、state_solution、interaction、evaluation，来自冻结装配、通道、控制与后端声明。历史纯静力 Study 中虽保留控制器声明，但没有实际执行器，仍正确归为无主动控制。混合主动执行器与固定 payout、接触结构响应等缺失后端返回明确 unsupported，不静默改成另一类问题。原 TaskDefinition 对混合情况继续拒绝，只将错误说明改为缺失混合后端。

动态研究继续使用原数学评估上限，并在原 Store 原子预留全部计划 episode 的 backend_solves，保留原 RL 评价额度保护。Worker 的原检查点目录保留逐 episode 进度、失败和真实成本；恢复不重启计算。失败保留为 incomplete 证据，不伪装成结构不可行。最大预留、实际完成和费用分开记录。

## Main 实际接口

默认三个领域为 `mechanism_research`、`control_feasibility`、`structure_control_codesign`；被动任务中的控制领域明确不可用。动作内部仍是 inspect / differentiate / optimize / compare，没有新增 SDK 工具或 V5。

有限时间比较的 V4 结构载荷示例（候选由已完成 diagnose 拥有，短引用以当前 Schema 为准）：

```json
{
  "version": "scientific_question_v4",
  "domain": "structure",
  "structure": {
    "operation": "compare",
    "effect_semantics": "finite_time_task_response",
    "target": "finite_time_task_violation",
    "operating_point": "frozen_task_initial_state",
    "control_treatment": "no_active_control",
    "physical_problem": "passive_unilateral_equilibrium",
    "load_condition": "all_frozen_conditions",
    "comparison_candidates": ["candidate_11"],
    "requested_budget": 2
  }
}
```

真实动态结果的只读 Main 投影包含两组各 17 项约束的数值、冻结边界、单位、载荷、时窗、违反量和来源；最新结果可见 `effect_semantics=finite_time_task_response`、`task_acceptance=unmeasured`，而 `scientific_results.latest_evaluation` 指向同一事实所有者。已实际检查该 L0，未把原始轨迹送给 Main。完整 SDK/Mock 回归继续验证没有内部完整 SHA 或私有引用映射，Reporter 故障不影响固定数值、证书及 SELECT。

## 结构目标与方法路由

合法共同尺度齐备且全部观察完整有效时，结构目标为：

`J_task(d) = max(condition, constraint) normalized_signed_violation(d)`。

目标是减小 J；J ≤ 0 只说明该次研究观察中的相应冻结约束满足。缺工况、无效、缺测或任何必需约束没有合法尺度时不产生该分数。

本工程任务的 `no_contact <= 0` 没有冻结归一化参考尺度。因此真实双结构比较保留全部物理结果，但 **J 为 null，真实工程任务的该标量 differentiate/optimize 明确拒绝**。没有修改阈值、忽略接触项或给它添加 epsilon。具有完整正尺度的多工况差分、非严格方向和原 Powell 搜索，已用单独命名的合成数学夹具验证；不能把它称为真实任务优化成功。

原 FamilySpace、1–2 个合法连续参数、两尺度差分、两参数一致性检查及原有界 Powell 仍是唯一结构研究计算链。最大约束切换会标明非光滑，不能取得严格梯度声明；不支持的分支返回原因。建议只形成 StructureDirection / generate 参数交接，正式候选、控制重优化和独立 Replay 继续由原 Plan 与 Main 决定。

DifferentiationRouter 现在选择已有 Native 瞬时差分、被动重新平衡成对比较、被动 KKT 隐式敏感性、完整动态成对/差分、保存 Native T1/T2、保存 Conic 敏感性。它返回方法、效应、参数、工作点、控制处理、比较范围、数值一致性、方向强度、有效性、证据与成本。KKT 仍须通过原正则性检查；T2 保留有限预算 best-found 割线语义。没有保存 T1/Conic 时返回准备信息，不自动启动搜索。主动完整动态结构观察与可微接触尚不支持，原主动控制后端未重写。

参考语义区分 `re_equilibrated_unloaded` / `re_equilibrated_loaded` 的理想硬约束静力、`frozen_dynamic_initial_state`、`same_episode_unloaded_sample` 的 MuJoCo 软约束动态，以及保存主动执行状态。原初态和同 episode 最后无载采样点也不同。静态/动态跨模型方向不能因表面冲突自动判错。本轮没有额外执行同参数静力—动态数值一致性研究。

## 验证、成本及已发现的问题

| 验证 | 结果 |
|---|---|
| C0 定向批次 | 36 项中 35 通过；1 项因开发时源码变动触发冻结保护，停止编辑后单独复测通过 |
| C0 干净树 V4 检查 | 原 3 项通过 |
| C1 定向回归批次 | 23 项中 22 通过；新增伪造诊断测试发现读取异常，已修复 |
| 修复后桥接测试文件 | 全部 10 项通过，包含历史证书、伪造拒绝、能力、预算、合成多工况/Powell/生成交接 |
| 最后失败分类补测 | 合成正常与失败路径通过，0 真实物理步 |
| 原 V4 定向检查 | 2 项通过；此前能力推断曾错误拒绝历史静力夹具，已按实际装配修复 |
| 原静力 Native/单侧约束、原被动 SDK Replay 闭环 | 2 项通过 |

失败和中间日志均保留，没有放宽原断言或冻结任务阈值。原结构归因、保存 Native/Conic、R3 证书读取门禁及 SELECT/STOP 回归通过。未跑完整历史 Benchmark、NMPC/PPO 训练或真实 Provider。

真实计算总计 **5 个新模型、6 个动态 episode、2,400 个 mj_step，真实 Provider 0**：结构动态比较为 2 模型/4 episode/1,600 步；原静力检查为 2 模型/0 积分步；原独立 Replay 为 1 模型/2 episode/800 步。动态研究记录 6,408 次 native forward、约 1.458 s 内核时间；原 Replay 记录 3,204 次 forward。静力另有主动 forward 3 次、被动 forward 183 次。每项原始成本都保存在本地证据中，未用总墙钟冒充内核成本。

真实结构对照的 tendon_0 payout 从 0.160100 m 改为 0.160106 m，两者均松弛、最大张力 0 N。两个工况的 tip 最大位移都分别约为 0.445195 mm、1.306676 mm；这次合法微扰没有改变这些响应，未宣称改善。每结构均保留 17 项冻结约束。相同数学请求重用原收据没有新增计算；仅 1 个物理额度不能承载 2 episode，请求在 Worker 启动前被拒绝。研究结果没有进入 physical_replays。

原独立 Replay 经 Main 完整证书阅读后 SELECT 自动 STOP；Reporter 故意不可用仍通过。5 个真实 SDK/Mock HTTP 请求的完整 wire 分别为 40,648、41,779、64,139、88,656、65,335 字节，完整证书首次交付保留。它们与 C0 固定旧包络对照不是同一测量，不混作压缩比例。

C0 同一旧 Store 与同一保存 SDK 包络的对照：artifact 枚举 10→1，artifact body 读 317→121，SQL 读 1395→360，准备时间单次观察 2.596→1.986 s，L0 25,036→24,743 字节，重建完整 wire 39,962→39,651 字节。收益主要在读取，长度下降较小；时间不是统计性性能结论。

## 文件与整理

新增文件为 C0 报告、本报告、单个 C0/C1 桥接测试文件及精简公开验证摘要。源码文件修改如下；没有移动或删除历史源码文件。

| 文件 | 改动原因 |
|---|---|
| `tools/research/state.py`, `extensions/tendon_family/manifest.py` | 补足原冻结范围 |
| `tools/platform_store.py` | 仅请求内的不可变读取复用 |
| `tools/research/object_choices.py`, `research_context.py`, `agent.py` | 短引用、交付解析、事实去重及 V4 菜单/Schema |
| `tools/research_tasks.py`, `feedback.py`, `task_constraints.py` | 原适配器派生能力、约束观察、统一差距与研究视图 |
| `extensions/reference/passive_response.py` | 抽出共享纯指标函数，删除 evaluator 内重复的对应逻辑 |
| `extensions/math_analysis/mechanism_registry.py`, `differentiation_router.py` | 注册内部动态目标、选择现有计算并标明证据强度 |
| `tools/research/scientific_intent.py`, `contracts.py` | 兼容扩展 V4、编译动态请求与原准入 |
| `tools/research/structure_research.py` | 原 Worker 中执行完整多载荷响应，复用差分/局部搜索/生成交接 |
| `tools/research/analysis.py`, `execution_worker.py`, `native_analysis.py` | 原原子预算、进度恢复、动态适用性与成本 |
| `tools/research/evidence_views.py` | 新旧证书诊断字段的最小兼容比较 |
| `schemas/platform.py` | 明确混合后端不支持的既有拒绝原因 |

实质整理是共用 evaluator 指标提取、消除重复全 artifact 枚举/同请求历史 wire 解析、删除重复默认动作和重复 L0 数值卡片。没有为了行数删除仍有调用者的物理内核。保留了 V1/V2/V3 编译入口、V4 旧动作别名、旧无诊断字段证书和真实不同的主动/被动数值算法；没有第二套 Store、Planner、预算、证书、控制来源或结构优化器。

## C2 准入结论

**未启动 C2。** 现有工程任务可做受原预算约束的完整动态成对比较及原独立验收；本轮真实对照没有结构改善证据。若 C2 需要统一标量结构优化，最小前置项是另行明确并冻结零/类别约束的合法研究归一化或独立比较规则，不能追改历史任务来取得分数；同时冻结科学任务、合法结构域、控制处理与预算并取得该阶段授权。混合动力学、接触敏感性、主动全动态结构比较及同参数静/动态一致性研究仍须独立验证。

完整 Store、原始 wire、数值轨迹和中间失败日志只在本地授权目录及交付压缩包中。远端只发布源码、测试、报告和精简数值/成本摘要。
