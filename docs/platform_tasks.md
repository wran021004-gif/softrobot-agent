# 人工任务填写与检查

## 需要提供什么

| 内容 | 填写位置 | 校验与含义 |
| --- | --- | --- |
| 身份与状态 | task_id、task_version、name、status、source | 草稿、开发有效、正式批准分别表达。本地开发宿主只接受 development_valid，不将配置文本当作人工审批凭据。 |
| 行为与对象 | family、goal.contract/version/data | 任务族自己的类型；到达有 target_m，长度保持只有 length_m。 |
| 环境 | environment_file 引用独立环境定义 | 快照中展开；重力单位 m/s²，环境契约声明对象类型。 |
| 机器人和执行器 | robot_families、actuator_channels、robot_file | 匹配实际机器人、后端和控制器；压力、力矩不会被当作绳长。 |
| 初始状态 | initializer 身份、版本及参数 | 登记初始化器执行；采样值、seed 固定进入运行快照。旧后端只支持原编译初态与零速度。 |
| 时间 | timing | 物理步长、控制周期、采样周期、持续时间均为秒，后三者为步长整数倍；实际耗时另记。 |
| 成功 | evaluator 身份与参数 | 声明文字不能代替实现；不存在时给出 IMPLEMENTATION_REQUIRED 与实现位置。 |
| 优化 | objectives | 指标名、方向、单位、可选正权重；不改变成功判据。当前搜索拒绝多目标。 |
| 失败与约束 | failure_policy、评价器输出 constraints | 保留失败与无效结果；工具完成、求解完成、计算有效及任务成功互相独立。 |
| 所需信号 | observations | 名称、实体、维度、单位、坐标和相位；缺少信号拒绝或未评价，不补零。 |
| 评价实例 | sampling | 开发 seeds 0..999，评价 seeds 10000..10999；本地开发策略拒绝正式评价分区。窗口单位秒；当前逐实例输出，汇总算法需显式扩展。 |
| 可编辑参数 | policy_file 中 editable | 仅允许控制器声明的可编辑参数及范围；任务、环境、评价器不进入搜索向量。 |
| 模型、工具、资源 | policy_file / project.yaml | 与任务科学标准分开。相同任务可由不同策略运行。 |

具体必填字段、默认值和嵌套类型来自 [生成字段说明](platform_generated/task_fields.json) 与 [JSON Schema](platform_generated/contracts.json)。空白模板见 [task.blank.yaml](templates/platform/task.blank.yaml)；它故意保持草稿与必填空值，不能误当成可执行示例。

## 三阶段判断

```powershell
python examples/workbench.py platform check configs/platform/signal_hold/session.yaml
```

- `definition_valid`：外层字段与基础类型合法。
- `capabilities_ready`：具体目标、初始化、评价、后端与控制契约齐全，且声明依赖可用。
- `executable`：完整会话配置通过开发状态、种子、权限及兼容检查。不会因此启动引擎；实际启动仍可能因许可证等失败。
- `formally_approved`：本地开发基线始终为 false。

典型错误：`length_m Field required` 表示缺少以米为单位的目标；`REQUIRED_SIGNAL` 指出缺少的实体／单位／相位；`IMPLEMENTATION_REQUIRED` 指出未登记评价器；`BACKEND_INCOMPATIBLE` 在求解前拒绝无法表示的任务或执行通道。增加未来任务时，先完成 `extensions/<包>/contracts.py + manifest.py + implementation.py`，再提交可执行配置。

## 两类完整示例

1. [到达开发任务](../configs/platform/reach_shifted/session.yaml)：目标 `[0.30,0,0.08]` m，时长 0.08 s／40 步，原环境和 0.01 m 容差。机器人 IR 使用原 V1 声明物理值；编译质量惯量仍由原后端导出。它是本次独立开发配置，不替换历史 reach_free。
2. [长度信号保持任务](../configs/platform/signal_hold/session.yaml)：没有末端目标点。参考模型是明确的一阶离散方程 `x[k+1]=x[k]+0.5*(command-x[k])`；评价窗口内最大偏差与 RMS 偏差。它验证不同任务语义、分步后端、控制及搜索接口，不代表真实绳索动力学。

完整文件均能通过真实解析与能力检查。真实 MuJoCo 的短验证和参考信号计算分别计数。后端不支持的摩擦、活动物体、执行通道和观测不得静默省略。

## 修改、冻结与运行

修改目标、评价或初始分布时增加 task_version，使用新 run_id。会话创建后修改配置文件不改变已保存输入。跨版本恢复需要显式迁移或新运行，不替换旧快照。

```powershell
python examples/workbench.py platform create runs/my_platform configs/platform/reach_shifted/session.yaml
# 显式调用文件示例见 templates/platform/simulate.request.yaml
python examples/workbench.py platform call runs/my_platform reach-shifted docs/templates/platform/simulate.request.yaml
```

相同 request_id 重送返回原回执；参数改变必须换 request_id。同参数的新实验使用新 request_id 并设 `cache: new`。缓存复用仍消耗一次获准工具调用，但不消耗新求解额度。

## 温和接球：待定义／待实现清单

[gentle_catch.checklist.yaml](templates/platform/gentle_catch.checklist.yaml) 是人工决策清单，**不是可执行任务包**。

需要用户明确：球的质量、半径、材料／接触假设、初始位置与速度或分布、释放时刻、重力与地面、机器人范围、允许执行器；“接住”是保持接触、包络约束还是指定区域内速度达标，连续保持多久；允许掉落、反弹、穿透、碰撞对象；冲击评价是峰值接触力、冲量、球加速度还是其他指标，单位、采样窗口及聚合方法；任务成功与温和程度优化如何分开；开发与正式测试实例；哪些设计和控制量可搜索。

平台尚缺活动球初始化与环境契约、碰撞实体信号适配、接住评价器、冲击评价器及对应后端验收。本轮没有接球仿真或凭空定义这些科学值。
