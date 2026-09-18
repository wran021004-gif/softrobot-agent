# 公共接口版本与定版决策

## 数学模型、控制依赖与求解器公共边界（基线 a6f5f8e）

新代码使用 `schemas/platform_math.py` 的数据契约和 `schemas/platform_protocols.py` 的运行协议。
`TaskDefinition` 仍描述任务要求；`RobotDescription` / `family.Design` 仍拥有机器人实体与真实物理量。
`MathematicalModel` 描述数学坐标、所需机器人数据、离散契约与能力，不执行后端，也不复制机器人参数。

| 对象 | 权威入口 | 接入约定 |
|---|---|---|
| MathematicalModel / ModelCapabilities | `schemas/platform_math.py` | 五项显式布尔能力：kinematics、statics、dynamics、linearization、gradients；未支持项为 false |
| DynamicSystem | 同上；`platform.dynamic_system@1.0.0` | 具体有序状态/输入/输出坐标、x0/u0、函数表达式与 continuous/discrete 时间域 |
| LinearizedModel | 同上；`platform.linearized_model@1.0.0` | 同样的坐标和工作点、A/B、时间域、秒单位 timestep；离散模型必须给 timestep |
| OptimizationProblem / OptimizationResult | 同上；`platform.optimization_problem/result@1.0.0` | 独立数学问题及结果，可按原 Payload/Store/EvidenceRef 机制保存引用 |
| Solver / Search | `schemas/platform_protocols.py` | `solve(problem) -> result` 与原 propose/feedback 两套独立协议 |
| Space.model_parameters | `extensions/tendon_family/contracts.py` | 默认为空；沿用路径到 type/bounds/options 的规格，不迁移旧配置 |
| BackendResult / Signal / SignalSpec | `schemas/platform.py` | 所有后端的统一公共出口，已有生命周期和输出语义保留 |

**能力声明与控制器要求。** 模型仍注册为 `dynamics_model`，在
`Extension.capabilities['mathematical_model']` 放入 `MathematicalModel.model_dump(mode='json')`。
例如 `ModelCapabilities(kinematics=True, dynamics=True)` 明确不支持 gradients。
控制器在 `capabilities['model_requirement']` 放入 `ModelRequirement` 的 JSON：
`input='none'`、`'mathematical_model'`、`'dynamic_system'` 或 `'linearized_model'`，并可列出所需 capabilities。
缺少该 metadata 的旧控制器按 none 处理，不要求旧对象新增属性或方法。
`Registry.mathematical_model(binding)` 读取声明；`check_controller_model(controller, model)` 在
`compile_input` 检查匹配，不通过类名或 hasattr 猜测。要求标准 IR 时，还检查模型的
`representations`，防止将“能执行动力学”当成“已有 DynamicSystem 导出接口”。

`family.DynamicsModel` 是旧方程参数负载的兼容入口；其只读 `mathematical_model` 属性是当前串联模型
到公共契约的适配，manifest 从该属性生成 metadata。旧 `family.dynamics_model` JSON 和
`execution.model_definition()` 返回值不变。当前串联模型声明 kinematics/dynamics，未承诺通用
statics/linearization/gradients 或标准 IR 导出。新增模型直接声明公共契约，无需继承家族负载。

**标准中间模型。** 声明模板可用具名符号维度；实际 DynamicSystem/LinearizedModel 使用现有
SignalSpec 的具体 dimension、units、frame、phase，列表顺序决定展平后的向量顺序。
连续 dynamics 表达 xdot=f(x,u)，离散 dynamics 表达 x_next=f(x,u)，可选 output 表达 y=h(x,u)。
函数沿用 typed Payload 或 EvidenceRef，表达式格式由注册的负载契约定义、由相应适配器解释；
不在 JSON 中持久化 Python callable、NumPy、MATLAB 或 CasADi 对象，也不执行配置文本。
LinearizedModel 的 A/B 表达工作点处的扰动模型；可选 drift 保留非平衡工作点的偏移，省略表示平衡点。
LinearizedModel 不假设输出等于状态；未来需要输出线性化时再增量补充 C/D。
`DynamicSystemProvider.build_system(...)`、`Linearizer.linearize(system)` 和
`ModelBasedController.configure_model(...)` 是独立可选协议。未来模型导出 IR 后交给控制器，
控制器只导入公共 IR。本轮只建立这些边界，现有执行器不自动生成模型、线性化或配置新控制器。

**Search 与 Solver。** 原 `Search` 负责候选 → 昂贵执行 → Evaluation → feedback；
`family.optimization_request` 和现有 route.optimize 仍属于该路径。新 OptimizationProblem 描述一次
显式数学问题：variables 复用 Space 的路径/规格表示，向量或轨迹可使用索引路径；objective 复用
TaskDefinition 的 Objective，objective_function 给出实际数学表达式，constraints 给出标量上下界
（相等即等式）。它不是 TaskDefinition，也不是一次黑箱搜索请求。
model_reference 复用 Binding/EvidenceRef；horizon 是阶段数；initial_guess 与 optimum 用相同变量路径。
OptimizationResult.status 描述求解终止原因，不表示任务成功，也不承诺全局最优；objective_value 是
Objective 对应的原始指标。constraint_violation 的尺度由问题适配器约定并在 evidence 记录。
Solver 以 `Extension(kind='solver', input_schema=参数契约, output_schema=OptimizationResult, ...)`
登记，用 `Registry.bind(binding, 'solver')` 解析，再以参数构造实例并调用 solve。
Search 不能通过该 kind 检查。问题本体没有 solver 字段；当前没有新增实际 Solver 实现。

**四类参数。** `Space.parameters` 是实体/真实设计参数（含材料 Young 模量）；
`control_parameters` 是控制器参数；`model_parameters` 是模型特有参数（例如 regularization）；
`discretization_parameters` 是数值离散（例如 cells、未来 GVS basis order）。
物理量不能因某数学模型使用它就复制到 model_parameters。templates 仍表示完整实体设计选择。
`model/<path>` 只编辑 `policy.dynamics_model.parameters.data`；候选公共边界仍冻结模型 ID、版本和
参数契约，并由 Registry 解析最终负载。原 serial_bending 模型没有新增可调项，未知参数仍被拒绝。
独立 `family.build_request` 只构建设计/离散，不承载模型；模型参数编辑须走带模型 binding 的
session candidate。路线概览展示四类参数；现有连续搜索仍只接受实体/控制变量，未扩展搜索算法。

**统一结果与信号。** OneShotBackend.run / SteppingBackend.export 都返回 BackendResult；
observe 返回 Signal 列表。后端原生结果可存入 data 或 ExportBundle，进入公共层后使用统一信号。
名称是可扩展 Identifier，现有 tip_position、tendon_length、tendon_tension、joint_position、
joint_velocity 及未来 contact_force 无需新增结果类。每个 Signal 用实际 times_s 表达非均匀或稀疏采样，
SignalSpec 指定实体、维度、单位、坐标系和采样相位；缺失信号不能补零，也不能把不同相位/符号的量
仅凭名字视为相同。历史 contact_normal_force/contact_tangent_force 等名称不改写。
BackendResult.solver_status 保留后端执行状态含义，与数学 Solver 的 OptimizationResult.status 分开。

**路由和后续接入。** Combination 仍只有 dynamics_model/backend/controller，不添加 solver、
linearizer 或 optimization_problem 字段；已有 Host、Store、Evaluator 和 public_tools 流程继续使用。
PCC/GVS 接 MathematicalModel 及可选 IR 导出；LQR 接 LinearizedModel，NMPC 接 DynamicSystem；
IPOPT/acados 的数学求解适配注册 solver；Bayesian/evolutionary 昂贵设计搜索注册 search；
SoRoSim/SOFA 接现有 Backend 协议并规范为 BackendResult/Signal。这里只建立契约，未实现这些算法。
旧 evidence/run 不重写；代码依赖变化仍按原 Host.compatibility 规则要求新会话或显式迁移后再执行。

JSON Schema 和能力目录由 `python examples/export_platform_contracts.py` 从源码生成；不维护第二份手写契约。

## 领域信号断点修复（基线 04bf31e）

复用 Extension.hook，后端可选声明 `capabilities.signal_specs_resolver='可信模块:函数'`，签名 `(SessionInput, Registry) -> list[SignalSpec]`。返回当前机器人可声明的完整稳定实体规格，供任务和控制器共用严格语义检查；未声明时保留静态 signal_specs 行为。resolver 及传递依赖须纳入后端 sources；请求不能提供模块路径。MATLAB/MuJoCo 复用 robot_domain 的实际映射定义与 IR 实体规则，不预声明稀疏接触发生记录。

新增 `diagnostics.sample_exceeds@1.1.0`：原 BackendResult 引用加可选 entity/phase，返回所选身份、来源与严格标量大于阈值的样本；旧 1.0.0 保留。新版本、旧版本分别由 policy.tool_bindings 精确选择，现有旧示例补充 1.0.0 绑定。公共信封与结果契约版本不变。字段、只读调用和随仓库测试样例见 [领域指南](platform_domain.md)。

## 领域接入增量（基线 a716f32）

公共信封版本不变。`domain.rod_design@1.0.0` 作为会话唯一设计负载，`candidate.rod_design@1.0.0` 重用原等效杆编译；既有后端继续接受 legacy.robot_ir，并新增此设计表示。后端输出增量统一信号，明确实际实体和 state／solver 时间。`signals.read@1.0.0` 提供精确选择，旧单字段诊断遇到歧义明确拒绝。

`diagnostics.saved_trajectory`、`diagnostics.signal_rule`、`visualization.render_simulation_video` 新 **2.0.0** 输入 EvidenceRef 和执行身份，原路径版本及字段语义保留。`visualization.saved_replay@1.0.0` 只准备原回放数据。输出 SavedProduct 关联源结果、所选／原始执行、候选、ExportBundle、报告和文件引用；复用原 SQLite 内容库与账本。`capabilities.category/role` 与目录 binding 只是发现元数据。详细字段、兼容映射、范围和验证见 [领域指南](platform_domain.md)。

当前入口与开发步骤见 [平台指南](platform.md) 和 [扩展指南](platform_extensions.md)。本页顶部记录当前结果契约与复用语义，后半部保留上一轮历史决策；历史“开发接口 2.0”不是全部工具或契约的统一版本。

源码是权威：公共信封见 `schemas/platform.py`、操作类型见 `schemas/platform_operations.py`、Python 开发协议见 `schemas/platform_protocols.py`，具体负载和绑定见各扩展包。运行 `python examples/export_platform_contracts.py` 同步 [contracts.json](platform_generated/contracts.json) 和 [capabilities.json](platform_generated/capabilities.json)，不手写第二套接口。ToolReceipt／EvaluationResult 默认 1.2.0、WorkerOutput 2.0.0，各工具的精确 version 和其他契约版本独立保留；新会话通过 policy.tool_bindings 选择工具版本。

## 公共接口两项修复（审阅基线 6751639）

- 输出统一按 `Extension.output_schema` 严格验证，缓存字典同样恢复为该契约类型。只有声明为 `BackendResult` / `EvaluationResult`（含子类）才提取求解／评价状态；普通工具的 `validity`、`solver_status` 不参与分类。结果自带的 `contract_version` 在正常和缓存回执中一致保留；未定义该属性时继续使用工具精确版本。
- 普通工具作者无需新增结果类别声明，只需现有输入输出契约。普通纯计算缓存仍使用 `cache=True`。经 `simulation.run` 接入的后端无需自行实现复用登记或账本。
- 仿真启用 `cache=True`，在现有 `capabilities` 增加可选可信绑定 `cache_reuse`。函数签名为 `(host, arguments, prepared, cached_receipt)`，在预检后、预留前只读检查；返回 `None` 表示不能复用，回到正常执行；返回来源字典则由宿主封存。未声明时保持普通不可变输出复用。绑定源码和传递依赖仍须纳入现有 sources 声明；不得接受请求提供的模块路径。
- 仿真正常执行将来源放入 `InvocationContext.result_execution`（默认 `None`），复用钩子返回相同结构：`original_execution_id`、`instance`、`backend`、`task`、`candidate`、`candidate_input`。`Store.complete(..., result_execution=None)` 与输出、回执和结算原子保存；Store 以本次封存输出和请求覆盖 `artifact_id`、`request_id`，并记录含不可变来源证据的 `result_provenance` 事件。无需新表或扩展账本。
- `ToolReceipt`、`EvaluationResult` 新输出默认 **1.2.0**，增量字段 `original_execution_id: str | None = None` 指向产生轨迹的原始仿真。真实执行指向自身，连续复用直接指向原始执行；评价结果的 `source_execution_id` 保持“选中的仿真调用”原义。普通工具回执及缺少来源的旧记录默认为 `None`。继续读取 1.0.0／1.1.0，保留其版本且不写回；旧消费者若严格只接受旧版本，需显式接入 1.2.0。工具版本和 `BackendResult` 结构不变。
- 新调用仍检查冻结依赖兼容性；旧会话若依赖已变化则按现有规则只读或显式迁移。旧仿真缺必要来源时不命中缓存、不补造来源。范围限同一会话、现有缓存键，不包含跨会话或跨候选名去重。

## 历史：上一轮定版决策（开发接口 2.0）

以下保留当时版本与结论；其中结果契约 1.1 的描述已由上方 1.2.0 增量决策更新，不作为新开发默认版本。

基线：`c677c22`，`feat/unified-development-platform`；开始时工作区干净。历史任务、参数来源及证据不改写。

| 分类 | 决策 |
|---|---|
| 保留 | Host 执行边界、Registry 发现、Store SQLite 账本、已有物理适配与技能库 |
| 修复 | 结果正文投递、候选预检输入、提案后检查点、精确工具版本 |
| 接口调整 | 注册模型适配/策略、候选构建器、通用工作者结果与受限客户端、语义能力与依赖闭包 |
| 后续实现 | 真实新物理/Genesis、视觉传输、多目标算法、远程调度、自动技能训练 |

## 所有权与兼容

Host 是会话状态写入者；模型策略提出类型化请求，适配器拥有编码/传输/解码，扩展不复制循环。模型输入内容与实际适配器请求分别保存并记录交付事件，原始响应和规范决定分别留存。

新会话冻结 `policy.tool_bindings` 的名称与精确版本。旧 `allowed_tools` 仅在版本唯一时规范化并记入新快照；旧封存快照不修改，依赖变化要求新会话或显式迁移。

候选构建一次，范围检查后以同一有效输入预检和执行；任务、种子与初态不属于设计向量。内容摘要允许关联多个执行，评价必须消除来源歧义。

通用工作者使用 2.0 共同封装，领域负载留在扩展并经注册检查器验证。工作单额度是子调用上限，不是再次扣费的计算预留池；派发只计 worker 槽和进程墙钟，子调用在原 SQLite calls 中结算一次，同时受项目、父会话与工作单上限约束。各工作者使用独立会话作用域，协调者接收结果。

扩展声明输入输出、源码/资产、扩展依赖及契约依赖。公共核心不导入示例契约。能力以环境、机器人表示、执行通道与完整信号语义匹配；旧后端专属转换保留明确限制。

开发接口证明离线可接入；不代表真实模型质量、物理标定或恶意代码隔离。后续新增语义可以升级公共契约。

版本：ToolReceipt / EvaluationResult 的可选来源信息采用 1.1，读取兼容旧内容而不写回；WorkerOutput 将领域负载移出是破坏性变化，采用 2.0；模型观测、适配器、策略、候选是首次发布的 1.0。工具版本与返回结果契约版本分别记录。

