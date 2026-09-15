# 扩展接口与独立验收

开发者安装的是可信仓库 Python 包。模型和任务配置不能传入 import 路径。发现机制按路径排序读取 `extensions/*/manifest.py`；声明文件只导入轻量契约，不启动可选引擎。相同身份与版本重名直接拒绝。多个版本可以登记，但当前会话允许工具必须唯一确定版本，不能依赖发现顺序覆盖。

## 公共调用

任意入口提交 `ToolRequest` 到 `Host.invoke`：命令行、人类、离线／真实模型都使用该边界。调用者来自宿主构造，不接受工具实参中的 caller、管理员身份或其他预算账户。可信 Python 开发者仍能直接调用函数；这不意味着模型获得了相应权限，也不构成 OS 沙箱或远程认证。

扩展自己的输入、输出必须是 `Contract` 子类；复杂负载通过 `Payload(contract, version, data)` 传递，调用 `Registry.parse` 校验。manifest 绑定输入类型、输出类型、版本、依赖、资源、缓存、副作用和能力说明。公共宿主不增加工具名分支。

## 各类实现责任

| 类型 | 实现与可复用接口 | 最小参考与验收 |
| --- | --- | --- |
| 数学工具 | 输入声明单位／坐标／模型身份；输出声明结论层级；需要模型量时用 PCCModel、SharedModel 或 RobotIRProvider | `analysis.vector_norm`、现有 `analysis.pcc_condition`；测试数学→读取→继续决策 |
| 任务／评价器 | family 检查目标、初始化、评价绑定；评价消费明确保存信号，返回 EvaluationResult | `task.signal_hold`、`evaluate.hold`；有效失败仍可排名，缺失／未完成不可排名 |
| 诊断 | 独立查询保存信号与规则判断；记录索引、原数据引用、规则版本 | `diagnostics.sample_exceeds`；原 `diagnostic_rules.py` 仍处理历史信号；测试缺失／无事件／不适用 |
| 控制器 | 自有参数与状态契约；reset、command、finish、checkpoint、restore；声明周期、观测、通道和可编辑量 | `LengthController`；旧 C1/C2 仍由 controllers/registry.py 执行，不承诺旧 C2 任意中点状态恢复 |
| 搜索器 | propose、feedback、stopped、save、restore；算法拥有迭代及随机状态 | `ScalarSequenceSearch` + `tools/platform_search.py`；原坐标搜索继续保留旧适配，不强加其缩步规则 |
| 后端 | check、compile、initialize、run、close；只有声明逐步能力才提供 step／observe／export／cancel | `ReferenceBackend`；一次性 MuJoCo／MATLAB 适配见 `extensions/reference/legacy.py` |
| 工作者 | 输入 WorkOrder、固定内容身份、独立输出 WorkerOutput；宿主校验身份、来源和分配额度 | `worker.signal`；真实双进程重叠、取消、失败、冲突和过期候选验收 |

可执行参考集中在 `extensions/reference/implementation.py`，协议概览在 `schemas/platform_protocols.py`。模板目录 `docs/templates/platform/extension/` 提供一个可复制运行的数学包和各类职责骨架；带 `NotImplementedError` 的模板明确待实现，不能加入可执行目录冒充能力。

新增包通常只修改自己的实现、契约、manifest 和测试。要增加新的状态物理意义、执行通道、环境对象或公共生命周期操作，仍需集成者升级共同边界；本基线不承诺未来永远无需升级接口。

## 后端能力与资源

声明支持的任务族、机器人、执行器、环境、信号及相位、控制器、一次性／分步操作、资源和超时覆盖。`compile_input` 先拒绝不兼容组合；昂贵启动只在 `simulation.run` 已完成预留之后进行。后端始终在 finally 中 close。

参考后端为合成信号模型。MuJoCo 保留原单次执行器；MATLAB 保留平面自由度、近似法向接触、缺少摩擦与自碰撞的限制。MATLAB 引擎启动和关闭没有硬超时保证，future.cancel 也不证明外部服务已终止。未知完成状态保留额度，不自动再求解。

新实现的能力声明必须真实。分步控制的连续运行、reset 与 restore 含义分别定义；输出单位和执行通道不能靠改字段名转换。当前真实后端只接绳长通道。

## Genesis 接入任务

`backend.genesis` 当前只有未实现声明。未来开发者应：

1. 确定目标版本，检查真实支持的结构、自由度、接触和执行器，不沿用本轮猜测。
2. 定义参数与后端数据契约；将共同 RobotDescription/RobotIR 转成该版本模型。
3. 实现兼容检查与所需生命周期，明确不支持的效应并在启动前拒绝。
4. 导出有实体、维度、单位、坐标和相位的信号，至少满足所接任务的评价／控制需求。
5. 声明资源、依赖、取消、启动／执行／关闭超时和遗漏项。
6. 运行 `platform check`、自己的最小契约测试，再由集成者批准独立短计算配置；不能借用历史预算。

## 验证命令

```powershell
python -m unittest tests.test_platform.PlatformTests.test_math_extension_loop_discovery_delivery_and_pagination -v
python -m unittest tests.test_platform.PlatformTests.test_search_lifecycle_restore_and_ranking_identity -v
python examples/export_platform_contracts.py
```

新包应附独立使用示例和小范围测试。只有公共接口变更才由集成者运行相关组合验收，不要求各开发者重跑全仓库或历史实验。
