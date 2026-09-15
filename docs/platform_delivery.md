# 统一开发平台交付报告

## 1. 当前平台与运行顺序

平台是一个可检查、可恢复的本地开发宿主。人工任务／环境／机器人与实验策略分开；Pydantic 校验和能力检查形成输入快照；离线或现有供应方传输产生决定；公共宿主验证、授权、预留、执行、封存；评价／诊断读取保存结果；记忆、技能与工作者输出进入后续上下文或协调验收。架构和权威来源图见 [platform.md](platform.md)。

## 2. 复用与新增路径

复用 `tools/service_execution.py`、`tool_registry.py`、`public_gateway.py`、`reach_dynamics.py`、`design_compiler.py`、`model_provider.py`、原控制器与诊断、`skills/registry.py` 及 `tools/skill_policy.py`。旧动态／工作台主循环和历史账本保留原权限。

新增主要边界：`schemas/platform.py`、`platform_protocols.py`；`tools/platform_registry.py`、`platform_tasks.py`、`platform_host.py`、`platform_store.py`、`platform_models.py`、`platform_tools.py`、`platform_search.py`、`platform_physics.py`、`platform_workers.py`、`platform_worker.py`、`platform_skills.py`、`platform_view.py`、`platform_history.py`、`platform_config.py`；扩展包在 `extensions/reference/` 和 `extensions/services/`。

旧文件仅作必要兼容修改：工作台转发平台命令；原技能注册器与策略检查器增加可注入证据适配，默认行为不变；README 与忽略规则更新。任务、物理、原指标、研究预算和历史结果无修改。

## 3. 人工新增任务

填写身份／版本／状态、目标契约、环境、机器人与执行器范围、初始化、时间、成功评价器、优化指标、失败约束、信号需求和评价实例；在独立策略中填写可编辑参数、工具、模型与预算。

```powershell
conda activate softagent
python examples/workbench.py platform check configs/platform/signal_hold/session.yaml
python examples/workbench.py platform project-create runs/my_platform configs/platform/project.yaml
python examples/workbench.py platform create runs/my_platform configs/platform/signal_hold/session.yaml
python examples/workbench.py platform run runs/my_platform signal-hold --decisions configs/platform/offline.yaml
```

详见 [填写指南](platform_tasks.md)、[空白模板](templates/platform/task.blank.yaml)、[到达例子](../configs/platform/reach_shifted/session.yaml)、[不同语义例子](../configs/platform/signal_hold/session.yaml)、[接球清单](templates/platform/gentle_catch.checklist.yaml)。

## 4. 开发者新增能力

在自己的 `extensions/<package>/` 提供契约、实现、manifest、最小测试和例子；配置引用稳定身份。通过同一个 `Host.invoke` 或 `platform call` 调用。声明 sources、依赖、能力、资源与副作用。新增普通数学工具／规则／已支持通道上的控制和搜索不需要修改模型循环、预算或展示程序。见 [扩展指南](platform_extensions.md) 与 [包模板](templates/platform/extension/README.md)。

## 5. 并行工作与共享所有权

任务／评价器、数学、诊断、控制、搜索、后端和参考工作者可以各包并行开发。公共信封、宿主、SQLite 事务、模型循环、CLI 及原科学定义由集成者维护；改变共享语义须先提交版本与兼容方案。见 [责任表与合并流程](platform_parallel_development.md)、[开发任务单](templates/platform/development_order.md)。运行时协作是独立概念，见 [记忆技能与协作](platform_collaboration.md)。

## 6. 实际验证

29 个不同聚焦用例通过（28 项组合＋1 项后续恢复检查），没有全仓库重放。累计真实模型 0；正常数学工具 20；离线回复 41；合成参考执行 51；真实 MuJoCo 2 次／100 步；真实 MATLAB 1 次／473 个成功内部步，另一次启动失败未求解。累计本地工作者进程 33 个，覆盖正常并发和故障注入；代表性双工作区间重叠 0.7831 s。计数与证据见 [验证文档](platform_validation.md)。

## 7. 并行扩展判断与边界

在已声明本地接口范围内，**具备并行扩展条件**。不声称所有物理、执行器、仿真器或真实模型已验证；Genesis、完整接球、视觉传输、多目标搜索、新执行通道等保持明确缺失。新物理和语义仍需显式接口扩展，不承诺接口永不升级。

## 8. 分支与集成

基线 `63ae9b5`，本地分支 `feat/unified-development-platform`。改动均留在工作区，**未提交、未推送、未合并**。建议先审查公共契约／事务和兼容改动，再审查参考包与证据，最后从当前有效开发成果集成；不要把旧默认主分支当成当然基线。来源与恢复规则见 [platform_recovery.md](platform_recovery.md)，排查顺序见 [platform_debugging.md](platform_debugging.md)。
