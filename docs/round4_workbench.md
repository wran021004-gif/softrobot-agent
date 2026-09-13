# 第四轮研究工作台

本轮没有接入大模型、智能体框架或硬件。MATLAB、MuJoCo 是后端；按问题组织工具，复用现有 `capabilities/catalog.yaml`、各工具 manifest 和解析器。查询：

```powershell
python examples/run_round4.py catalog
```

```python
from capabilities.registry import query_tools
query_tools(category='mathematical_analysis')
query_tools(implementation_status='PLANNED')
```

| 功能类别 | 可用入口与范围 |
|---|---|
| 设计表达与编译 | `validate_design`、`build_robot_ir`、`compile_mujoco`；设计、单段机器人 IR、旧物理参数的离散模型 |
| 数学建模与分析 | `analyze_workspace`、`analyze_clearance`、`analyze_actuation`、`pcc_sensitivity`；`MechanicsTools.solve` 的受限静态/动态/单参数辨识；第四轮独立诊断版 |
| 设计与控制生成 | `plan_pcc_reach`、`plan_open_loop`、`synthesize_feedback`、已有 `optimize_design`；种子化任务实例；本轮一次粗筛及一次实际结果驱动细化 |
| 仿真与实验执行 | `run_task`、已有 harness；新增 `run_campaign` 将原编译器、规划器、控制器和评价器串成有限配对执行 |
| 评价、诊断与观察 | 既有 reach/window 评价、执行器诊断、形状比较；新增三任务评价、动态数据适用性检查、统一观察器和 PNG/GIF 导出 |
| 代码与能力管理 | `query_tools`、原工件/版本/trace 服务、任务族说明；按实现、验证证据和标定状态分别查询 |

通用多自由度动力学、通用材料辨识、学习控制等原 `PLANNED` 条目仍明确未实现。受限 `closeout_mechanics_solve` 能做单总弯角分析和合成刚度恢复，不等于这些通用能力已经实现。任务不达标返回 `TASK_FAILED` 或 `EVALUATED/task_success=false`，不改写为“不支持”。工具执行失败、无效输入、条件不适用和证据缺失单独报告。

各 manifest 包含问题、输入输出、单位/坐标/时间、假设、限制、实际入口、依赖、调用成本和证据。布尔 `calibrated=false` 与实现状态分开；历史验证引用旧报告，新能力引用本轮检查，元数据本身不是实测标定。

## 三个任务族

`TaskInstance` 不取代冻结 `TaskSpec/TaskContract`，只描述开发任务的来源、随机化与评价。

```python
from tools.task_family_tools import generate_task_instance, execution_task, evaluate_task_instance
i = generate_task_instance('reach_free', seed=17, split='development')
# 另外两类：reach_obstacle、tip_stability_external_force
task, environment = execution_task(i)
# result、trajectory 来自同一次正常 run_task 结果；不要传 debug 轨迹。
evaluation = evaluate_task_instance(i, result, trajectory)
```

开发 seed 0–999，独立评估 seed 10000–10999，固定分区、不交叉。本轮只执行开发 seed=17，未把独立评估样本用于调参。允许目标 Z∈[0.14,0.16] m；X=0.25 m，Y=0。环境、初始零关节位置/速度及2 s时长显式固定。三类调用同一固定指令控制器，没有专属求解算法。

自由到达复用 `tasks/reach_free`；障碍到达复用 `tests/fixtures/reach_window_dev` 及其已有窗口约束。该窗口开发场景允许初始机器人跨窗口，并不证明“从窗口前方完整穿越”。稳定任务保持世界系目标，扰动是 segment_7 上的世界系外力，基座不动；它不是基座振动补偿。外力时段0.5–0.7 s，Z分量0.08–0.12 N；评价0.8–2 s的最大误差和RMS，最大误差≤0.01 m才成功。这些新增参数是接口验证用开发选择，没有正式基准批准。

首次执行三例的入口为 `python examples/run_round4.py development`，结果已有时直接读取封存摘要。三份实例、控制输入、原始轨迹和评价分别在 `runs/round4/tasks/<family>/`。仍缺少基座运动执行、标定物理模型与任务最优控制；无需这些能力即可正常评价失败结果。

## 有限执行、恢复与读写范围

长度对照首次使用 `freeze` 保存候选规则、输入和源码快照，再使用 `length`。本轮已执行完成；结果摘要存在时不会启动后端。中断的未完成候选使用 `length --resume`，此前预约仍扣账，再试消耗新额度；完成结果按哈希复用。不允许并发实验所有者。中断时可能留下预算写锁，此时应先确认没有活跃写进程并审计账本，不能直接重置预算。

新预算在 `runs/round4/budget.json`；历史预算不变。保存的任务、设计、控制、分析模型与评价分离。读写限于指定工件目录，后台仿真有120 s运行上限，诊断求解30 s内部保护和45 s Engine等待限制；MATLAB启动由现有本机 Engine 管理。新入口没有操作系统隔离，不能把路径校验、文件锁或工作分支说成沙箱。

`raw_manifest.json` 封存349个原始工件，`execution_sources.zip` 保存正式执行所用源码。交付前增加的缓存输入一致性检查、任务证据绑定和只读审计入口与数值执行版本分开：没有重算或改写任何原始数值。图表、截图、GIF和审计输出位于 `derived/`。离线操作：

```powershell
python examples/run_round4.py audit --root runs/round4
python examples/run_round4.py derive --root runs/round4
```

小型便携证据在 `docs/evidence/round4/raw_evidence.tar.xz`。解包后将 `--root` 指向其中的 `round4` 目录；审计只读数值、哈希和源码快照，不运行其中代码。动画和主要表格无需解包即可查看。
