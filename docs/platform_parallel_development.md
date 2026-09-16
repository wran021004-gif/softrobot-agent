# 多人并行开发代码

此处是代码集成流程，与 `WorkOrder` 管理运行时工作者分开。

当前入口是 `python examples/workbench.py platform ...`，它转发到 `examples/development_platform.py`；从 [平台指南](platform.md) 定位操作，从 [扩展指南与最小模板](platform_extensions.md#从现有模板开始) 完成包内接入。接口版本以源码和 [生成契约](platform_generated/contracts.json) 为准，不沿用历史报告的统一版本说法。合成参考、兼容后端、未实现骨架及环境缺依赖的区别见 [能力说明](platform.md#权威数据来源)。

## 可独立领取的模块

| 工作包 | 主要拥有文件 | 依赖接口 | 独立验收 |
| --- | --- | --- | --- |
| 数学工具 | extensions/<math_package>/ 与本包测试 | Contract、Extension、模型量接口 | 单位／坐标、已知值、缺失量、一次公共调用 |
| 新诊断 | extensions/<diagnostic_package>/ | Signal、EvidenceRef、规则输出 | 缺失／无事件／不适用／索引来源 |
| 控制算法 | extensions/<control_package>/ | Controller 协议、已支持通道 | reset、周期、观测、restore、输出类型 |
| 搜索算法 | extensions/<search_package>/ | Search 协议、EvaluationResult | 提案／反馈、无效样本、状态恢复、多目标声明 |
| 后端 | extensions/<backend_package>/ | RobotDescription、任务快照、BackendResult | 无依赖发现、兼容拒绝、参考或独立短执行 |
| 任务族／评价器 | extensions/<task_package>/、configs/platform/<task>/ | TaskDefinition、具体 Payload | 缺字段、能力检查、成功／优化分离 |
| 模型适配／策略 | extensions/<model_package>/ | ModelInput/Response 1.0、ToolRequest、Registry | 收到的结果决定后续调用，错误保留来源 |
| 候选构建 | extensions/<candidate_package>/ | CandidateInput 1.0、SessionInput、editable | 实际预检和执行同一输入，禁止改写任务 |
| 协作工作者 | extensions/<worker_package>/ | WorkOrder 精确工具绑定、WorkerOutput 2.0、RestrictedClient | 独立输出、来源、失败／取消和过期候选 |
| 记忆／技能检索 | 本包适配器及测试 | MemoryEntry、原 SkillRegistry | 来源校验、失效筛选、实际上下文投递 |

## 集成者维护的共享部分

`schemas/platform.py`、`schemas/platform_operations.py`、`schemas/platform_protocols.py`、`tools/platform_registry.py`、`platform_host.py`、`platform_store.py`、`platform_models.py`、公共 CLI，以及原科学契约／授权核心由集成者维护。已有服务中央注册 `tools/tool_registry.py` 仍由集成者维护；新包优先拥有自己的 manifest，避免多人同时编辑中央大文件。包作者负责准确声明输入输出、绑定、精确版本、必要依赖和适用边界，使用共同 Host 校验与账本，不另建调用或收费路径。

## 分支、任务单与合并

每个任务从已验收的接口基线创建独立分支或 worktree。填写 [development_order.md](templates/platform/development_order.md)：目标、输入输出、依赖版本、拥有文件、禁止修改的共享部分、验收入口和交付物。

1. 开发者在自己的包内实现类型、实现绑定和测试，不绕过公共校验或预算。
2. 公共接口变化先提交变更说明：具体触发、行为变化、兼容版本、旧运行处理、受影响包与验收。
3. 集成者检查 manifest 的确定性发现、重名／版本冲突和 sources 依赖闭包；生成契约与目录。
4. 合入集成分支后运行相关组合检查。数学或纯配置改动不应触发研究仿真或全仓库测试。
5. 需要真实求解时提交明确独立开发策略与短预算；不借用历史研究授权。

开始工作时核对实际分支、提交和已有改动，在有效成果上继续；历史审阅基线不是回退指令，不覆盖其他开发者的工作。

各工作包填写自己的输入输出、精确契约版本、sources/assets、扩展依赖及独立命令，新会话用 policy.tool_bindings 选择工具精确版本。演练实现与可直接运行的验收入口见 [扩展接口表](platform_extensions.md)。ToolReceipt/EvaluationResult 当前默认 1.2.0、WorkerOutput 为 2.0.0；其余契约各自版本不变。工具版本不等于结果契约版本；来源字段及旧版本兼容见 [接口决策](platform_interface_decisions.md)。

公共核心和接口版本仍由集成者维护。这是后续协作规则，不要求本次公共修复逐文件确认；正常包内扩展直接完成实现和验收，公共语义变化交付具体变更及兼容方案。
