# 公共接口版本与定版决策

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

