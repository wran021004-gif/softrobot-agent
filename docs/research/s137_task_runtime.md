# S137：任务运行契约与配置统一

日期：2026-10-23（Asia/Shanghai）。基线：`origin/feat/s135-task-conditioned-control`
（`dcbca1b3`）。分支：`feat/s137-task-runtime`；独立 worktree：`.worktrees/s137-task-runtime`。
已先阅读本基线 AGENTS.md、S135 报告、S136 审计与条件矩阵。

## 实际修改和复用接口

扩展现有 `ResearchTaskAdapter`，没有新增任务体系、编译器、配置管理器或身份系统。

```python
from tools.research.config import resolve, effective_input, configuration_ownership, same_robot_structure
from tools.research_tasks import task_adapter

study = resolve('configs/research/study.json')  # 新研究才读取源配置
adapter = task_adapter(study)                  # 也接受已保存的完整有效快照
reference = adapter.control_reference()
conditions = adapter.condition_view()
execution = adapter.execution_requirements()
requirements = adapter.analysis_requirements({})
owners = configuration_ownership(study)
```

- `condition_view()` 按需投影，不持久化第二份任务。`TaskConditionView` 提供条件 ID、
  指标、真实含义、限值、单位、完整信号规格、采样/时间语义、来源指针和数学可表达性。
  `sampled_norm_bound` 只描述已有采样局部模型的表达，不表示物理执行成功。
- Reach 终点与最终窗口位置、绝对世界 tip 速度保持分开。保持值仍从旧有效快照的
  `policy.controller.parameters.data.settling` 读取；没有搬迁、重解释旧 F3 数据。
- Untimed 的路径偏差、覆盖、第一条测量起点、末条测量终点、最近点弧长进度回退
  五项全部保留。`geometry_step_m` 是独立评价的空间采样参数；采集时长不是任务 deadline。
  五项在条件视图中标为 `proxy_only`，既有数学需求继续保留五项 unsupported rows，
  与可求解 `geometric_path` 代理分开。具体模型适用性仍由原数学工具检查。
- Timed 保留评分窗口内每个 post-step 时刻的 `norm(p-r(t))` 上界；不增加末点、
  全时域或速度硬条件。数学网格、预测窗口、完整记录覆盖仍有不同职责。
- Tracking 判据清单提取到注册 evaluator 所在的 `tracking_condition_specs()`；
  几何 evaluator 和适配器复用清单，数值计算、阈值和评价结果不变。
- `execution_requirements()` 给出任务信号、环境/初始化、机器人/通道、时间、已选
  controller/backend/model 绑定、张力顺序/物理界及现有组合协议所需分量。
  它是需求声明；实际技术兼容性继续调用 `check_compatibility()`，复用
  `platform_tasks.compile_input`、注册信号语义和 route hooks，不授予执行权限。
- `config.effective_input()` 统一读取 SessionInput、`effective`/`input` 包装和
  `resolve()` 的 `configuration`。适配器旧导入路径仍可使用；读取快照不重读源 JSON。
  S135 的 `task_adapter(dict(task=task))` 继续取得控制参考，也支持直接 TaskDefinition。
  缺少有效配置时，条件视图明确报告缺少 Reach 保持来源，执行视图报告缺配置，
  数学/执行兼容性接口以 `EFFECTIVE_CONFIGURATION_REQUIRED` 拒绝补造数据。

## 所有权和配置边界

`configuration_ownership()` 是现有所有权/授权的只读说明；不替代原校验或预算 ledger。

| 内容 | 权威及边界 |
| --- | --- |
| 冻结任务 | 审核 TaskDefinition、seed 与已保存 Study；draft 仍是 draft |
| 硬验收 | 注册 evaluator 和冻结协议；Reach 保持继续归冻结 settling；recipe/reward 不拥有阈值 |
| 结构变量 | 实际 `/robot/structure` 和结构授权；旧 allowed_parameters 中 `segments.*` 单独列入结构 grant |
| 控制设计 | 候选 recipe/solver、独立 reward/PPO 配置；旧控制权重 grant 与结构 grant 分开，不能扩大授权 |
| 算法授权 | Study capabilities、允许动作、NMPC/RL 上限和既有 continuation grants；没有 Study 时这些值为未知 |
| 预算 | Study 总量、SessionInput 执行预算及现有消费 ledger；读视图不重置预算或历史失败 |

`same_robot_structure(a, b)` 比较机器人 family 和完整结构 Payload 的实际值，忽略任务、
控制配置、candidate identity。同一实际结构可为不同任务选择不同控制配置；长度、材料、
截面、张力界等结构字段改变会得到不同结果。这是保守的结构 Payload 相等比较，
不规范化重命名/排序，也不替代原科学候选、模型、残差参考的完整证据身份检查。

数学需求、NMPC 参考、RL 参考可以来自同一 adapter；各自的 cost/reward、预测窗口和
优化权重继续独立。调整这些权重不改 evaluator/settling 阈值，return/cost 也不成为通过指标。
没有修改 `resolve()` 的组合输出、旧 TaskDefinition、TaskAnalysisRequirement schema、
`compile_input()` 或组合验收协议。没有迁移旧数据或修改 sealed evidence。

## 离线验证

复用 S135 已有 `.s135-env/Scripts/python.exe`，未安装依赖。
新增 7 项契约测试，加 8 项直接相关回归，共 **15 个不同测试通过**：
配置包装读取、来源不重载、三类条件/参考、评分窗口、任务单独调用、权重/验收分离、
实际结构比较、所有权、S136 条件留存、S135 几何进度/独立失败、Tracking 反例/Timed
记录验证，以及 S131 F3 保存身份/验收检查。最后绑定说明变更后仅复测受影响的 2 项。

另外只读加载基线 adapter，在相同 Reach、Untimed、Timed 配置下逐项比较
`control_reference()`、`describe()`、`analysis_requirements()`，**9 项输出完全一致**。
`git diff --check` 通过。所有数值输入均为既有配置或合成测试，不是新增科研证据。
Provider 请求 0、物理仿真 0、NMPC 优化 0、RL 训练 0。

## 残余缺口

Untimed 的五项真实几何验收仍不能被已有采样自由进度代理完整证明；Timed 物理路由、
RL 与组合物理验收仍未实现。单独任务无法提供旧 Reach 保持、机器人、算法授权和预算。
可表达性不代替具体模型的信号/物理/时域适用性检查；不支持接触、避障等新物理任务。
手工替换冻结 settling 仍会改变旧 Reach 的验收，必须继续遵循原冻结快照和授权边界。

## S137.1 集成前最小修复（2026-10-23）

基线 `f4800096`，继续使用原独立 worktree。远端目标分支也已核实为该基线。
仅修改四个生产文件、原 S137 测试文件和本文；未修改 evaluator 数值、阈值、正式成功判定或保存证据。

条件视图增加两个小字典，保留原条件 ID、`expressibility` 等字段：

| 条件 | `evaluation_binding` 的实际来源/字段 | `mathematical_binding.constraint_id` |
| --- | --- | --- |
| Reach `terminal_error_m` | `EvaluationResult.metrics[position_error]`，`constraints[task_bound]` | `terminal_error_m` |
| Reach `holding_max_error_m` | 组合验收同名 metric、`components.holding_position`；Profile detail 的 `/sampled_settling/max_error_m` | 同条件 ID |
| Reach `holding_max_speed_m_s` | 组合验收同名 metric、`components.holding_speed`；Profile detail 的 `/sampled_settling/max_speed_m_s` | 同条件 ID |
| Tracking `tracking_max_error` | `EvaluationResult.metrics[max_position_error]`，`constraints[tracking_max_error]` | Timed 为 `timed_tracking`；Untimed 为同条件 ID |
| Untimed `path_coverage` | `metrics[path_coverage_error]`，同名 constraint | 同条件 ID |
| Untimed `path_start` | 仅 `constraints[path_start]`，`metric=null` | 同条件 ID |
| Untimed `path_end` | `metrics[terminal_position_error]`，同名 constraint | 同条件 ID |
| Untimed `path_progress_regression` | `metrics[progress_regression]`，同名 constraint | 同条件 ID |

方括号表示按 `name` 选择已有列表项，无新结果解析器。Reach 保持量不属于普通 Reach evaluator 的输出。
Reach/Timed 的 `coverage=exact_sampled_expression` 仅表示采样局部模型中的表达等价，不是已求解或物理成功。
Untimed 五项的 `coverage=unsupported` 对应 S136 原有五项 unsupported rows；
`proxy_constraint_id=geometric_path` 明确关联独立代理，不能替代五项真实验收。
下游可按约束 ID 关联既有数学结果 coverage，仍须检查实际 analyzed/unchecked indices 和模型适用性。
S134 的数学结果强度说明保持不变：numerically_checked 不提升为严格最优性，代理失败不证明不可行。

执行视图保留 `protocol_id` 原用法，另列 `protocol_template_id`、`task_reviewed`、配置是否存在、
`configuration_check=not_checked`、`capability_check=not_checked`、`execution_admission=not_assessed` 和 `known_blockers`。
已知协议只表示模板适用；配置存在不表示已验证。draft、缺配置、Timed 无物理组合协议等已知阻碍显式列出，
列表不冒充完整准入检查。实际检查仍由 `check_compatibility()`、`compile_input()`、Registry、route hooks
及 Study 原授权/预算承担；未升级任何 draft，也未开放 Timed 物理执行。

结构所有权保留旧连续 `grant`，复用 FamilySpace `decision_summary()` 展示实际域、生成范围和执行影响；
`declared_only` 列出超出生成器范围的段数/腱数。FamilySpace 原完整字段继续保留，新增结构域摘要中将
`control_domains` 归入控制所有权。旧生成器能力复用已注册 `parameter_declarations`，不创建参数目录。
另直接展示冻结 Study 的 `family_search`（变量组、计数范围、提案/评价上限）、`topology_authorization`、
长度限制及授权来源。混合搜索连续范围仍由原 `search_domains()` 按所选域检查，未复制授权算法。
声明域、生成能力和 Study 权限分别展示；未获生成支持的计数仅是声明，其他域也须受允许动作、能力和预算限制。
控制权重、Reward/PPO 继续归控制配置，不能修改结构授权或硬验收；缺 Study 时授权保持未知。
`same_robot_structure()` 语义未改，未重读源配置、重置预算或修改历史数据。

验证复用 S135 `.s135-env/Scripts/python.exe`：S137 原 7 项及新增 3 项全部通过；
S136 全部 7 项、S135 几何进度/独立失败 1 项、Tracking 几何反例及 Timed 评价 2 项、
S131 保存 F3 身份/验收 1 项、S134 数学强度投影及保存 F3 指标来源 2 项全部通过，合计 **23 项不同测试**。
回归命令曾误写 S135 测试类名，已改为 `ControlTests` 并通过；`git diff --check` 通过。
Provider、MuJoCo 物理执行、NMPC/MATLAB 实验、PPO 训练和正式 Study 均为 0。
剩余限制仍为 Untimed 五项未被等价数学覆盖、Timed 物理路线未实现、只读视图不授予研究权限。

最终提交为本节所在 HEAD：`fix: clarify task condition bindings and runtime capability views`。
普通 push 至 `origin/feat/s137-task-runtime`；最终短 SHA 见交付回复。
交付时该独立 worktree 干净并与远端同步，其他 worktree 和独立研究进程未操作。
