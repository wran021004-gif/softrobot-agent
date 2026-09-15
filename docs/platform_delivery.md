# 公共核心修复与扩展接口定版交付

基线为 `c677c22`，当前分支 `feat/unified-development-platform`。开始时工作区干净，沿现有实现继续；改动留在工作区，未提交、推送、合并或改变默认分支。

## 四项修复

| 问题 | 当前行为 |
| --- | --- |
| 结果正文没有进入模型请求 | ToolObservation 投递最近一份受限正文，证据页正文直接进入下一请求。选中输入、实际适配器请求、原始响应和规范决定分别留存；解析失败保留响应引用。实算结果 5 与 10 触发不同候选。 |
| 候选预检与执行不同 | 注册构建器只构建一次，CandidateInput 冻结有效输入，预检与执行共用。示例上限 0.305 拒绝新指令 0.31，后端运行零次；合法输入逐字段一致。 |
| 搜索丢失提案后状态 | pending 与提案后的算法/RNG 状态一起保存；恢复先处理 pending，即使算法已经停止提案。已封存工具按原请求复用，反馈、试验记录和新状态一起提交。 |
| 会话没有精确工具版本 | policy.tool_bindings 绑定名称和版本，目录、模型声明、授权、缓存、依赖与事件统一使用。两个版本可共存；旧唯一版本配置明确规范化，歧义定位配置字段。 |

## 三类可运行接口

- **模型／策略**：ModelInput/Response 1.0，策略输出 ToolRequest。适配器负责 encode/respond/decode；保留 offline 和 DeepSeek，独立 ObservingAdapter/EvidenceStrategy 由 manifest 接入同一循环。只有文本，未传输图片或视频。
- **工作者**：WorkerOutput 2.0 封装身份、状态、来源、具体 Payload、错误和用量；注册检查器校验领域结果。两个本地进程分别调用数学工具、返回信号清单诊断，经共同 Host 和原 SQLite 账本执行。子会话独立写入，工作单计算额度是子调用上限，父级不重复预扣计算。
- **候选**：CandidateInput 1.0 与 candidate_builder 注册边界。默认控制参数适配保留，独立示例支持 structure.response_fraction。初态和种子固定，任务、环境与成功标准不可修改；真实机器人继续使用 RobotDescription/RobotIR。

ToolReceipt / EvaluationResult 的可选来源信息采用 1.1；未改变语义的扩展无需统一升级。决策及兼容策略见 [接口决策](platform_interface_decisions.md)。

## 独立扩展与接入路径

演练包拥有 `extensions/convergence/contracts.py`、`implementation.py`、`manifest.py`；两份配置位于 `configs/platform/convergence/hold.yaml`、`terminal.yaml`；对应验收在 `tests/test_platform_convergence.py`。新增工具、适配器、策略、工作者、评价器、搜索器和合成构建器都由声明发现，公共循环没有这些名称的路由分支。

本次集成者修改公共契约、宿主、注册、模型、调度、候选、依赖及 CLI。公共操作类型移至 `schemas/platform_operations.py`，信号工作者回到参考包。来源闭包由 sources、assets、extension_dependencies、contract_dependencies 记录；无关包和文档不再成为全局失效开关。

内容摘要与执行身份分开，一份内容可以关联多个执行。评价显式携带候选和源执行。默认经验检索保留模型、机器人与后端假设范围；接收工作者结果不等于验证自然语言科学结论。

## 使用与验证

```powershell
conda activate softagent
python examples/development_platform.py check configs/platform/convergence/terminal.yaml
python examples/development_platform.py project-create runs/my_core_dev configs/platform/project.yaml
python examples/development_platform.py create runs/my_core_dev configs/platform/convergence/terminal.yaml
python examples/development_platform.py run runs/my_core_dev convergence-terminal
python examples/development_platform.py inputs runs/my_core_dev convergence-terminal
```

项目配置的 grant_id 应使用新的独立开发身份，不能复制已有绑定来增加额度。填写说明见 [任务指南](platform_tasks.md)、[策略模板](templates/platform/policy.blank.yaml)，接入与独立命令见 [扩展指南](platform_extensions.md)，排查见 [调试指南](platform_debugging.md)。

一次受影响组合验收 **12 项通过**；随后修正模型服务参数重名，只补了本地解码检查与结果投递组。本次累计（含分组、失败与补测）：54 次离线回复、30 次合成执行、17 次数学工具完成、13 个工作者进程；真实模型、MATLAB、MuJoCo、Genesis 均为零。口径、失败及修复见 [验证记录](platform_validation.md)，不将历史物理实验算作本次成果。

## 仍需升级或实现的边界

| 未来工作 | 接入位置和具体缺口 |
| --- | --- |
| 新工具、策略、既有信号评价 | 自己包的契约、实现和 manifest，使用现有公共调用路径 |
| 接球、动态对象、新物理 | 环境／对象／初态契约、成功与冲击评价器、真正支持这些语义的后端 |
| Genesis、新材料／形态／执行通道 | RobotDescription/RobotIR 转换与物理来源；新通道由控制器和后端共同定义 |
| 结构变化需要映射初态 | 显式初态映射契约；本版不能重新采样改变任务难度 |
| 多目标搜索 | 反馈适配和真正支持多目标的算法；仅设置 multiobjective 标志不会放行 |
| 完整视觉或流式响应 | 媒体编码、实际传输与回执契约；当前仅文本 |
| 任意代码、远程集群、复杂图调度 | 额外隔离、传输与调度实现；本地应用边界不是恶意代码沙箱 |
| 自动技能训练 | 复用原技能库，补可验证训练来源与适用范围；自然语言经验不直接成为程序 |

当前基线可进入具体扩展包开发；不承诺未来永远无需修改公共接口。
