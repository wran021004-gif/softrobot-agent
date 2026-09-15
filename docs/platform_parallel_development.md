# 多人并行开发代码

此处是代码集成流程，与 `WorkOrder` 管理运行时工作者分开。

## 可独立领取的模块

| 工作包 | 主要拥有文件 | 依赖接口 | 独立验收 |
| --- | --- | --- | --- |
| 数学工具 | extensions/<math_package>/ 与本包测试 | Contract、Extension、模型量接口 | 单位／坐标、已知值、缺失量、一次公共调用 |
| 新诊断 | extensions/<diagnostic_package>/ | Signal、EvidenceRef、规则输出 | 缺失／无事件／不适用／索引来源 |
| 控制算法 | extensions/<control_package>/ | Controller 协议、已支持通道 | reset、周期、观测、restore、输出类型 |
| 搜索算法 | extensions/<search_package>/ | Search 协议、EvaluationResult | 提案／反馈、无效样本、状态恢复、多目标声明 |
| 后端 | extensions/<backend_package>/ | RobotDescription、任务快照、BackendResult | 无依赖发现、兼容拒绝、参考或独立短执行 |
| 任务族／评价器 | extensions/<task_package>/、configs/platform/<task>/ | TaskDefinition、具体 Payload | 缺字段、能力检查、成功／优化分离 |
| 协作工作者 | extensions/<worker_package>/ | WorkOrder、WorkerOutput、Coordinator | 独立输出、来源、失败／取消和过期候选 |
| 记忆／技能检索 | 本包适配器及测试 | MemoryEntry、原 SkillRegistry | 来源校验、失效筛选、实际上下文投递 |

## 集成者维护的共享部分

`schemas/platform.py`、`platform_protocols.py`、`tools/platform_registry.py`、`platform_host.py`、`platform_store.py`、`platform_models.py`、公共 CLI，以及原科学契约／授权核心由集成者维护。已有服务中央注册 `tools/tool_registry.py` 仍由集成者维护；新包优先拥有自己的 manifest，避免多人同时编辑中央大文件。

## 分支、任务单与合并

每个任务从已验收的接口基线创建独立分支或 worktree。填写 [development_order.md](templates/platform/development_order.md)：目标、输入输出、依赖版本、拥有文件、禁止修改的共享部分、验收入口和交付物。

1. 开发者在自己的包内实现类型、实现绑定和测试，不绕过公共校验或预算。
2. 公共接口变化先提交变更说明：具体触发、行为变化、兼容版本、旧运行处理、受影响包与验收。
3. 集成者检查 manifest 的确定性发现、重名／版本冲突和 sources 依赖闭包；生成契约与目录。
4. 合入集成分支后运行相关组合检查。数学或纯配置改动不应触发研究仿真或全仓库测试。
5. 需要真实求解时提交明确独立开发策略与短预算；不借用历史研究授权。

本次分支未自动提交、推送或合并。建议审阅新增平台文件、四处兼容改动及验收证据后，在原有效成果上集成；不要因为远程默认分支名为 main 就覆盖当前开发基线。
