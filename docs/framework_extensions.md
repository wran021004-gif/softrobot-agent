# 框架与扩展机制交付

本轮基于开发分支 `1a0081b6822ccf802cfd08ce8d1ecb9c5049a69b`，开始时工作区干净。交付围绕现有单机器人、长度伺服、PCC 和分段动力学能力建立扩展接口。历史任务、物理定义、评分代码、实验授权和旧证据不变。没有引入新任务族、复杂搜索算法或多 agent 编排。

## 七项边界

| 边界 | 已落地的入口 | 本轮范围与限制 |
| --- | --- | --- |
| 工具目录与调用 | `tools/tool_registry.py`、`public_catalog.py`；动态工具的 `dynamic_actions.BINDINGS` | 服务注册同时提供身份、版本、schema、绑定、分析语义、执行需求。JSON 目录、原生 function 声明和生成文档共用定义。注册、存在实现、会话权限分别表达；未实现项不进入模型 function 列表。旧 Workbench 仍是兼容适配，新增独立能力使用服务注册。 |
| 公共执行 | `ServiceSession`、`service_execution`、`service_worker`；`EvaluationSession` | 服务复用严格校验、权限、调用预留、独立进程、缓存、封存、证据读取和中断恢复。数值评价适配拥有独立账本；原 campaign 的账本与保留额度继续生效。不同账本不互相授信。 |
| 模型与数据 | `PCCModel`、`SharedModel`、`QuantityRequest` | PCC 提供 tip/Jacobian；保存导出提供带单位的物理参数查询。结构来自 IR，编译物理参数来自 shared input/XML，状态来自轨迹。公开质量矩阵、科氏项等仍未实现，明确返回缺失能力。 |
| 观测与诊断 | `SIGNALS`、`SavedObservation`、`diagnostic_rules.RULES` | 数据查询与规则执行分开；时间阶段、单位、采样索引、源 hash 和规则版本可追踪。新增 `contact_presence` 只需已有接触计数。旧 reach 规则保留其模型假设。 |
| 任务与评价 | `TaskContext`、`development_context` | 目标、环境、初始状态策略、步数、dt、评价器身份一起冻结并保存。开发配置能独立改变目标和时长；仍使用 `metrics.reach.evaluate_reach` 的原容差和逻辑。新初始状态策略/任务语义须新增适配。 |
| 优化与评价 | `ParameterSpace`、`Evaluator`、`CampaignEvaluator`、`search_runtime.search` | 现有有界坐标搜索的提案、编码解码、候选构造、评价和记录分开。原 MATLAB 提案仍由其原账本收费；独立示例使用同一公式的 Python 适配与真实 MuJoCo 评价。无效/未完成结果不参与排名。 |
| 控制与执行 | `controllers.registry`、`factories`、`ControllerRuntime` | 生成器和执行循环分开；C1 无状态、C2 显式重置；声明观测需求、长度指令类型、周期、兼容后端。保存生命周期及 C2 更新记录。LLM 选择配置，逐步控制由确定性循环执行。 |

## 三项语义修复

1. 未完成/失败/未知求解不能从 `canonical_task_success=False` 推导任务失败，也不能从模型成功布尔值推导模型结论。MuJoCo 适配在未完成时直接输出 null；公共反馈分开表达 dispatch、solver、analysis、task。旧结果的原始字节保留；网关对新的调用回执重新正规化。
2. 接触事件查询不要求 tendon/joint 摘要。有有效事件时返回事件；存在样本但没有事件时返回 `NO_EVENT`。新增信号规则还能在完全没有关节/肌腱数据的记录上运行。
3. 默认时间窗口来自保存的物理采样时间；剩余时长来自 `shared_input.duration`。历史数据未记录时长时返回 null/`NOT_RECORDED`，不能用末尾采样或两秒常量猜测任务时长。

直接覆盖见 `tests/test_framework.py`。旧 `schemas.dynamic_workbench.Diagnose` 保留原两秒 campaign 的 wire 限制；它是冻结任务兼容适配。独立服务 `SavedDiagnosis/RuleQuery` 和新任务上下文不带该限制。

## 注册与执行契约

公共信封继续是 `ToolCall/PublicResult@1.0`，工具实现版本升级为 `1.1.0`。旧工具显式接受 `1.0.0` 请求作为输入兼容版本；返回当前实现版本并记录反馈语义版本。新增工具只接受 `1.1.0`。这是输入适配，不代表重现旧源码的数值结果。

一个 `ServiceTool` 声明以下内容：

- `tool_id/schema/output_schema/version/compatible_versions`：身份及输入、细节输出契约。
- `binding/adapter`：受信任仓库函数和参数调用约定，不能由模型传入 import 路径。
- `permission/resources`：需求，不能自行获得授权。服务仅有 analysis、read_evidence、derived_artifacts，不能通过声明升级成数值后端或模型调用。
- `isolation/timeout_s/cache/sources/input_refs/analysis_scope`：执行、缓存、证据依赖和反馈语义。

新服务默认独立进程，超时终止子进程后保留费用。现有小型 PCC 计算、JSON 分页和视频适配保留 inline 兼容方式；视频使用自己的缓存和编码器超时。inline 的 `timeout_s` 是声明，公共进程终止保证仅适用于 process 工具，不能把任意耗时扩展注册成 inline 并声称有硬超时。

每个允许执行的服务调用（包括缓存命中）预留一个 tool call；输入/权限拒绝不收费。缓存键包含版本、输入/输出 schema、实参、输入证据、依赖源码 hash 和运行环境。缓存内容必须通过已登记 hash 检查。请求、细节、结果和费用分开保存。进程中断后只恢复已封存证据；不存在封存结果时保留已用额度，不自动重放。

数值评价的账本分别记录 calls、evaluations、wall_s。先验证配置、候选、控制器与后端兼容，再为实际评价预留次数和墙钟额度。缓存命中只增加调用次数，不增加求解次数。失败仍保留求解次数；已知完成的墙钟按实测结算；不明中断保留整段墙钟预留。`seal.json` 允许恢复结果写入后、账本提交前的中断。恢复验证 bundle hash；未封存的同一评价身份返回 `INCOMPLETE`，不再求解。后端使用现有 MuJoCo 循环/MATLAB future 的超时适配；MATLAB 启动仍是后端依赖与活动开销，不声称能由 Python 杀掉整个 MATLAB 服务。

## 模型、信号与诊断

PCC 是单段、不可伸长、固定基座的几何近似，坐标为基座 +x 轴、yz 弯曲，Jacobian 单位 m/rad。`pcc_condition` 用它的奇异值描述局部几何条件，不声称动力学可控性、可达性或物理标定。

`SharedModel` 复用现有 IR 编译导出。mass、inertia_y、stiffness、damping 等均带单位及源 hash；y 轴惯量不能当完整空间惯量。MATLAB 保留平面自由度、未标定法向接触近似及摩擦/自碰撞缺失声明；MuJoCo 结果也不等于物理标定。

`SavedObservation` 只加载三份登记证据：result、shared input、trajectory。MuJoCo 的 `time_s` 是步后状态、`solver_time_s` 是求解器力相位；MATLAB 为插值采样状态/力，不混用为控制步。规则先检查 backend/entity 适用性，再声明并查询所需信号。

规则输出区分 `EVENTS_FOUND`、`NO_EVENT`、`MISSING_DATA`、`NOT_APPLICABLE`、`EXECUTION_FAILED`。事件分别保存观测值、规则判断和因果假设，并通过采样索引、阶段、trajectory 引用、规则版本/源码 hash、源证据 hash 定位。缺少信号不是“未发生事件”；接触计数不是接触力，也不建立阻塞等因果解释。运行规则的计算成本计入服务调用与耗时，后端求解数为零。

## 本地扩展实际修改面

| 验收扩展 | 能力自身的修改 | 是否再加公共调度分支 |
| --- | --- | --- |
| PCC Jacobian 条件数 | `math_extensions.py` 实现；`schemas/framework.py` 输入/输出；`ServiceTool` 一条注册；直接验证 | 否。发现、native call、独立进程、缓存、反馈和 evidence.read_json 复用公共实现。 |
| 接触采样规则 | `tools/rules/contact_presence.py`；`diagnostic_rules.RULES` 一条声明；信号/缺失/追踪验证 | 否。使用 `diagnostics.signal_rule` 统一调用；已有接触信号不需要改后端。 |
| C1/C2 适配 | `controllers/factories.py`、生成器和控制契约注册；C2 reset；生命周期验证 | 初次接入建立了通用 runtime。以后已有观测和长度通道的新算法只新增生成器/控制器及注册、契约和验证。 |
| 现有坐标搜索 | `optimization_interfaces.py` 的空间、提案与评价适配；搜索 checkpoint | 初次整理将原优化入口改为调用接口。新提案方法通过 `proposal` 注入，评价仍经 evaluator；不改求解账本。 |
| 开发目标/时长 | 两个 `configs/framework/*.yaml` | 否。TaskContext 传到执行、诊断、评价和展示。 |

框架初次建设必然修改公共执行、反馈和适配边界；上表说明这些机制建成后，具体扩展没有再往服务执行/反馈中添加工具名称判断。动态 campaign 的 dispatch 也已改成注册绑定查询。历史 Workbench 的老任务组合适配保留，不将它当成新任务族通用执行器。

## 扩展示例与使用

```powershell
conda activate softagent
python examples/public_tools.py catalog --runtime services
python examples/public_tools.py catalog --output docs/framework_tool_catalog.json
python examples/framework_acceptance.py          # 实际数学计算 + 保存数据，零动力学
python examples/framework_acceptance.py --real   # 3 次短 MuJoCo 评价，共 140 步
```

原生调用名为 `analysis__pcc_condition`；输入例如 `length_m=1`、`bend_rad=[0,0]`、reason、evidence。读取其返回的 `details_ref`，通过 `evidence__read_json` 查询 `/singular_values_m_per_rad`，可得到 `[0.5,0.5]`。示例程序实际调用原生函数适配，不只是直接运行数学函数；provider response 为离线夹具，不能称为外部 LLM 决策闭环。

任务配置示例分别是目标 `[0.30,0,0.08]`/40 步和 `[0.28,0.02,0.12]`/60 步。dt 保持 0.002 s，原容差 0.01 m 和环境/物理定义未变。新设计空间只接受明确授权的 design/control 参数键；task/environment/evaluator 不能混入搜索向量。更换 C1/C2 使用不同独立评价配置，不能修改已创建会话的控制授权。

## 迁移与历史兼容

没有修改 `design_continuation.SESSION_FILES`，没有降低历史 source/runtime 比较强度。新数学/任务/控制/优化模块进入现有源码身份机制；dynamic numerical identity 显式包含新增依赖。旧会话不能借新代码恢复同一数值身份。应保留旧账本与旧输出，以 hash 校验导入只读证据；新执行使用新配置、新目录和新验证记录。

`EvaluationSession` 是独立实验的 Python 评价接口，不自动成为历史 agent 会话的新增授权。旧 Dynamics agent 继续经 `submit -> dynamic_actions -> CampaignEvaluator/simulate` 使用原 grant。扩展外部 agent 时只需 transport/caller 适配到现有 native schema 与 invoke/submit；actor identity 由宿主提供，不能由工具实参伪造。跨 agent 调度、共享预算协调和任务分配留待后续。

旧缺少 duration 的数据仍可读，剩余时长显式未知；旧诊断记录不回写新版规则结果。新的诊断和展示引用原始 hash，并产生新的输出和处理器身份。工具的主版本变化应新增/显式迁移契约，不用宽泛版本通配符吞掉不兼容；废弃别名须保留明确目的运行时与接受版本，不能静默路由到另一种物理/评价语义。

## 后续接入路线

- 数学工具：优先请求 `PCCModel/SharedModel` 已公开量；新增所需模型量时扩展 provider 并声明单位、坐标、假设及缺失行为，然后新增 schema/实现/ServiceTool 与必要数值验证。
- 优化算法：实现提案接口并保存可恢复状态（随机方法必须保存 RNG 状态）；保留 ParameterSpace、候选校验、Evaluator 和逐次费用。改变可编辑设计变量需独立空间适配与授权，不能修改冻结任务。
- 控制器：实现生成器、command 和必要 reset；注册 level、backend、观测和输入类型。EvaluationConfig 可指定 controller_id。已有长度通道由 ControllerRuntime 执行；力矩/压力等必须先实现对应执行器与后端适配。
- Agent：使用生成的 native 工具声明和公共调用信封，宿主绑定 caller、会话和模型 API 账本；不把直接 Python 函数访问当作 agent 授权。
- 任务：同类 reach 目标/步数用开发配置；更换环境、初始化、成功语义时扩展 TaskContext 对应任务/环境/评价适配并产生新身份。MATLAB 目前只接受单地板 positional reach，不能静默运行窗口任务。
- 设计空间：扩展候选构造/空间适配及 schema、关系约束、授权上下界；IR 编译器仍校验结构和物理含义，搜索器不负责重新解释模型。

最终验证分类、数值结果与证据路径见 [验证记录](framework_validation.md)，阶段记录见 [执行进展](framework_progress.md)。
