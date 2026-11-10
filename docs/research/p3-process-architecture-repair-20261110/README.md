# P3 研究执行架构修复（2026-11-10）

工作树 `passive-research-capabilities-20261107`，分支 `codex/passive-research-capabilities-20261107`，起点 `ee790268ff541ff8d6b0ad747698d3ffe5064dec`。

本次仅修改通用代码、请求合同、版本化配置和历史证据投影。当前 Study 保持用户审查暂停，Provider 使用 **84/100、剩余 16**。没有 Provider 请求、新 Study、物理积分、新 Replay 或 Push。以下验证是离线接口与已有证据回归，不能证明新的物理解或 12-cell 可行性。

## 1. 五类根因和修复

| 问题 | 根因 | 修复后的行为 |
|---|---|---|
| 工具实际不可执行 | Compiler 强制 screening 与 final 字典相等；paired-required 被误用于 Baseline；生成器继承的默认 cells 又与搜索选择冲突 | 显式选择已声明 Fidelity；生成配置以该选择为准；Baseline 可进入同一个搜索、准入和 Worker |
| 科学反馈丢失 | 刚度分母、资格或首项失败提前 return；compact 视图合并了同信号约束 | 先独立测量，后汇总结论；逐腱谓词不依赖刚度分母；逐项保留已知值和 UNKNOWN |
| 探索成本与组织 | 动态问题被绑定完整双向任务和配对；跨请求只有局部 cache | Main 明确提交 execution_profile；Baseline 默认无消融；精确物理结果按原 Store Result 索引复用 |
| 任务配置 | 粗筛/精化/正式离散混用，重复 drift/qvel 否决，旧开发额度容易误读 | 新 v1.1 任务与离线配置草案，原 v1.0 不变；用途、阈值角色、单次努力与累计预算分开 |
| Main 研究策略 | 无正式标量时跳过交互对照；简单事实也强制 Reporter；多参数改变与归因混淆 | 保留诊断参数对照、分量变化与各自资格；简单单结果直接交给 Main；研究方法和是否做交互由 Main 选择 |

## 2. 实际修改位置

| 文件 / 函数 | 责任 |
|---|---|
| `extensions/reference/passive_evaluation_v2.py`：`inspect`、`stiffness`、`bound_values`、`diagnostic_metrics`、`qualification_observations`、`mechanism_metrics`、`metrics` | 证据完整性、独立测量、资格、机制与最终结论分离；不丢弃其他指标 |
| `extensions/reference/passive_response.py`：`bound_values_v1`、`task_metrics` | 原 v1 响应也保留部分独立测量；速度、张力不再无故依赖位移参考数据 |
| `extensions/reference/contracts.py`、`passive_program.py`：`PassiveExecutionProfile`、`execution_scope`、`execution_identity`、`qualification` | 同一任务的请求执行范围、精确物理身份与版本化资格角色 |
| `extensions/tendon_family/passive_execution.py`：`execute`、`execute_pair` | 同一执行器运行单方向/连续前缀/稀疏探索与完整协议；两臂独立复用、匹配与实际新增成本 |
| `tools/research/structure_research.py`：`finite_time_discovery`、`prepare_context`、`dynamic_protocol`、`dynamic_cost`、`calculate`、`reusable_execution`、`dynamic_summary` | Baseline/配对解耦；范围与成本贯通；无标量诊断对照；精确复用与来源投影 |
| `tools/research/structure_intent.py`、`passive_search.py`、`search.py`、`design.py`、`extensions/tendon_family/family_space.py` | 声明 Fidelity → Compiler → 真实候选构造 → 原 Worker；兼容范围内排名；同一 Fidelity 的结构比较 |
| `tools/research/contracts.py`、`scientific_intent.py`、`agent.py` | Main Schema、Compiler 和 Worker 使用同一 profile；动态 Main 请求显式选范围，不默默展开全任务；数学与搜索方法继续开放 |
| `tools/research_tasks.py`、`feedback.py`、`evidence_views.py` | 通用 TaskGap v2、完整组成事实、精确原始引用与窗口、旧证据只读重投影 |
| `tools/research/reporter.py`、`research_context.py` | 单结果确定性事实不创建强制解释往返；保留显式 investigation；nullable 额度兼容 |
| `tools/research/config.py`、`budget.py` | null 表示 usage-only；显式单次努力和旧版有限授权继续各自生效 |
| `schemas/platform.py`、`schemas/research_reporting.py` | EvaluationResult 1.3 允许资格失败时保留测量；ResultIdentity 显示实际 Fidelity、实现、求解配置和执行身份 |

没有新增 Main、Reporter、Evaluator、P3 专用 Search/Executor/Replay、数据库或人工分阶段审批。

## 3. Exploration 与 Final Acceptance

两者引用同一份冻结 TaskDefinition、载荷程序、Evaluator 和执行器。

| | exploration | final_acceptance |
|---|---|---|
| 方向/阶段 | Main 选载荷条件和从初始开始的连续阶段前缀 | 全部冻结方向、完整阶段与原始连续性 |
| 力、ramp、阶段时长、dt、约束模型 | 保留原定义 | 保留原定义 |
| 采样/路由/记录 | 可选较粗对齐采样、score-grid 路由、sampled 记录与观测窗口 | 原密集资格窗口、路由范围和必要 CSV |
| Fidelity | 当前授权的声明层级 | 冻结正式层级 |
| 结论 | `acceptance_status=not_evaluated`；覆盖、缺失项和资格单列 | 全部物理资格、任务约束、机制及独立验证满足才正式通过 |

新 Main 动态问题和 Baseline 搜索必须明确提交 `execution_profile`。例如：

```json
{
  "purpose": "exploration",
  "load_conditions": ["plus_x"],
  "stage_prefix": "middle",
  "sample_period_s": 0.01,
  "route_sampling": "score_grid",
  "recording": "sampled",
  "fidelity": "screening",
  "requested_observables": ["material_displacement", "tendon_transitions"]
}
```

这是执行范围参数，不是人工授权步骤。middle 仍从 unloaded 连续运行；不会直接跳到 middle。原 PHS 执行器的物理 snapshot 时钟与可变观测采样时钟分开，降低记录频率不会顺带改动其冻结积分调用语义。旧内部请求保留完整协议含义；明确的独立 Replay 仍是新计算。

## 4. Fidelity 和版本化配置

只读核对原空间比较文件及其 SHA256，并验证六个原 Store 引用：1、2 cells 的双向状态均为 PASS，4 cells 双向 INVALID。见 [fidelity-history.json](fidelity-history.json)。这些是旧模型的历史证据，不是当前 12-cell 通过证据，也没有把成功设计交给 Main。

| 新草案用途 | 名称 | cells/segment |
|---|---|---:|
| Screening | `screening` | 2 |
| Refinement/diagnostic | `diagnostic4`、`refinement8` | 4、8 |
| Final | `final_evaluation` | 12 |
| 可选数值敏感性 | `sensitivity16`、`sensitivity32` | 16、32 |

4-cell 明确保留历史 INVALID 背景，不是“已验证可靠精度”。不强制逐级通过。不同 Fidelity、执行范围或求解协议不混合排名和复用。

新增 `tasks/passive_progressive_stiffness_dev_v1_1.json` 与 `configs/research/study_p3_passive_progressive_stiffness_architecture_v1_1.json`。后者只是可解析、可审查的配置草案，未实例化 Study，也不代表新预算或启动授权。当前暂停 Study 的冻结配置仍是原 8/16/32 screening 与 12 final；它不会自动获得新 2-cell 配置或 v1.1 资格语义。

## 5. Baseline 与 Paired Mechanism

`passive_task_response` 执行 Baseline response，现有 Coordinate / FamilyMixed / Coupled Block 共用原搜索和数学 Worker。最终需要机制证据，不等于每次 Baseline 都需要消融。

Main 通过现有 `passive_ablation` 明确选择 Paired Mechanism。两臂使用相同结构、模型、求解配置、初态和公共资格边界，只改变指定 passive limit。Baseline 失败不再在工具层直接取消诊断性消融；不完整或不合格两臂、身份或 receipt 不匹配都不能形成正式机制结论。已有合法配对指标也会投影回 TaskGap，不能被误写为缺失。

## 6. TaskGap 与一次性评价

`Metric` 和 `ConstraintResult` 继续表示已测事实，通用 TaskGap 承载值、阈值、signed violation、单位、状态、来源、参考窗口和覆盖。P3 逐腱事实只由 Evaluator 提取，通用载体没有 P3 特判。

刚度返回位移、力、分母、spread、不确定度门槛、有效性、区间刚度和比值。每根腱分别返回 low/middle/high 张力、间隙、残差、活动比例与组成条件，保留 `slack_to_taut` 合取；分类为 early/no-high/intermittent engagement、length violation、valid transition 或 unresolved。

刚度无效不抹去转换事实；资格失败不抹去位移等独立数据；一个工况缺失不抹去其他工况。UNKNOWN 不转为 FAIL 或 PASS。完整诊断也不意味着正式评分可比较。

Evaluator 最后汇总 PASS / FAIL / INCOMPLETE：已知约束或资格失败为 FAIL；没有已知失败但证据不足为 INCOMPLETE；完整通过才 PASS。探索或关闭正式组成检查的内部计算不会获得 acceptance credit。Reporter 解释仍与确定性测量分开。

## 7. 资格条件的依据

- **原 v1.0 完全保留**，不改旧 TaskDefinition 或旧 Result。
- **v1.1 qvel**：保留实测值和原数值参考，改作离散坐标诊断，不再独立否决。
- **v1.1 drift**：保留数值；仅同一完整密集速度窗口覆盖时移出硬否决。0.25 s × 1 mm/s = 0.25 mm，小于原 0.5 mm。覆盖不一致仍保留独立 drift 判断。
- **static balance**：原 1e-5 N·m 不放宽。新采样同时记录真实广义力分量的最大无穷范数作为尺度及 residual/scale；零或缺失尺度为 UNKNOWN。归一化阈值尚未校准，不能据此宣称正式静力合格。
- **保留**：长度限制、接触、数值异常、tip/monitor 实际速度、变形稳定性、任务位移、渐进刚度和同一根腱的转换。tip 与 monitor 未合并。

## 8. 结果复用

同一物理身份包括任务、设计、backend/model、实现源码摘要、运行库与数值线程、初态、阶段/方向、Fidelity、时间与求解设置、路由、记录、观测和干预。原 Store Result 内的 `physical_execution_index` 是指向原始执行的轻量索引，不是另一套 Cache/数据库。

先查原结果元数据，只有匹配才读取完整执行。复用保留原 Result/pointer，新增模型构建和积分为零；重算评价/序列化仍有正常开销。配对两臂可分别复用，状态不匹配时不能拼接成正式因果证据。旧 CSV 路径保留原执行来源。不同 Fidelity/初态/干预/稀疏协议不命中；独立 Replay 从不走复用路径。

未携带完整新执行身份的历史结果不补签复用身份，也不追溯改写成本；它们仍可做只读诊断。该保守边界避免把旧实现结果冒充新实现的精确数值证据。

## 9. Main 与数学研究

理论、M0、M1、Coordinate、Coupled Block、匹配比较、生成和搜索均由 Main 自主选择，没有固定科研流程。提示只要求简述假设、改变参数、Observable、预测及下一步决定；联合改进不能直接归因于单一参数，也不强制所有联合变化做四点实验。

无正式标量时，显式请求的参数和交互对照继续执行，返回分量实际变化、来源与各自资格，标记 `diagnostic_comparison`；不发布正式梯度或下降方向。简单单结果直接返回确定性摘要和完整组成事实，不创建强制 Reporter 往返；复杂综合或竞争机制仍可显式 investigation。

## 10. 旧额度审计

原开发文件的 candidates=40、math_requests=300、physics_step_attempts=8000000、dynamic_candidates=12、final_reserved_steps=2000000、provider/research_agent=0 是原独立开发入口的历史限制；当前通用研究配置将该文件作为协议证据，并不将这些字段合并进 Study budget。它不被复制到新任务授权中。

新草案的 mathematical_evaluations、physical_launches、offline_nlp、bdf_replays 均为 null/usage-only；时间和独立 Replay 无累计额度。family_search 的 max_proposals/max_evaluations 为 null，取消 256 的额外授权上限；每次请求仍明确有限努力。Worker watchdog 保留。NMPC/PPO 的不适用性未为了形式完整而改变。原版本任务、FamilySpace、Study 和 runtime 文件保留，现有账本没有重置。

## 11. 定向验证

结果见 [test-results.json](test-results.json)；历史测量和 Main 投影见 [historical-projections.json](historical-projections.json)。仅运行七组新定向合同测试、一项历史回归和四项原 v1.0 兼容测试，共 12 项；测试环境禁止真实 `mujoco.mj_step` 与 HTTP Provider 发送。

覆盖：result2/9/14、非 P3 result75 的 251 项原数值、资格失败仍保留测量、早张紧与未高载参与区分；声明 Fidelity 的真实搜索编译和候选构造；Baseline 与独立配对；单方向/连续前缀/稀疏探索与完整协议；原 Store 跨请求复用和两臂零新增成本；qvel/drift/static 角色；无标量 Coordinate/Coupled Worker；确定性反馈不触发 Reporter。无完整测试套件、仿真、参数搜索或历史 Study 重跑。

## 12. 已解决和证据边界

接口、测量反馈、探索范围、Baseline/配对组织、精确复用、局部对照和预算语义已贯通，并保留冻结验收要求。当前 Study 的 state digest、账本、84/100 Provider 计数及用户审查暂停均保持不变。

仍缺少新路径的真实物理运行、12-cell 成功与收敛证据、4-cell INVALID 的进一步数值归因、静力归一化阈值校准及真实性能/耗时比较。本轮不声称 P3 可行解、新物理验证、实际加速比例或硬件结论。下一步采用哪个任务版本、是否接续或创建后继 Study，留给用户审查决定。
