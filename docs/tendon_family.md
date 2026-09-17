# 绳驱串联机器人：模型、控制与双后端入口

推荐入口是 `examples/platform_tendon_family.py`。它仍使用公共 Host、Registry、Store、预算、缓存、回执、评价、信号和 `ExportBundle`，但输入不再复制两份任务。

## 权威来源

| 内容 | 权威文件或契约 | 派生物 |
|---|---|---|
| 公共任务、目标、评价、成功标准、环境、安装、初态、外力和时间条件 | `inputs/experiment.json` / `TaskDefinition` | 两个后端的 `SessionInput` 快照、`experiment_scene.json` |
| 实体设计与物理输入 | `inputs/design.json` / `family.design` | 候选实体、质量/惯量/刚度/阻尼、绳路和传动 |
| 设计空间和候选 | `inputs/space.json`、`inputs/<candidate>_request.json` | `<candidate>_candidate.json`、选择身份 |
| 离散 | `inputs/discretization.json`；结构模板可在 `Space.template_discretizations` 提供完整离散 | `model_discretization.json`、逐刚体/逐关节表示 |
| 数学模型与执行后端 | `inputs/execution.json` / `ExperimentPolicy.dynamics_model` 与 `backend` | `dynamics_execution.json`、`BackendResult.model_id` |
| 参考、控制算法 | `inputs/control.json` / `family.control` | `control_spec.json`、`controller_observations.json` |
| 后端数值设置 | `execution.json` 中各后端 binding | `solver_configuration.json`、结果中的 `execution_plan` |

`ExperimentPolicy.model` 仍是 LLM/模型服务配置；机器人动力学使用独立的 `ExperimentPolicy.dynamics_model`，两者不能互换。

## 数学模型与后端

当前唯一实现的数学模型是 `model.serial_bending_cells`：每个离散单元使用两个主轴弯曲角，采用串联刚体动力学、铰链弯曲弹性/阻尼、重力、具名外力和直线无摩擦绳长伺服。忽略轴向伸长、剪切、材料扭转、绳摩擦、绳弹性、电机动力学和自碰撞。

注册表中的后端 `models` 关系是兼容性的唯一来源：

- `backend.matlab_spatial@1.1.0` 执行原生 MATLAB 空间串联动力学，使用 `ode15s`、`rtol`、`atol`、`max_step_s`，地面接触是最低包络顶点罚函数。
- `backend.family_mujoco@1.1.0` 执行 MuJoCo 关节刚体动力学，使用公共物理步长、`implicitfast` 和记录在 XML 中的原生凸接触/摩擦设置。

二者独立消费同一实体、离散和实验来源。MATLAB 不读取 MuJoCo XML、数值结果或引擎状态。相同公共输入不表示接触近似相同。不支持的模型—后端组合在 `compile_input` 和求解预检阶段以 `DYNAMICS_MODEL_BACKEND_UNSUPPORTED` 拒绝，不会自动换模型，也不会消耗求解预算。

旧 `family.parameters@1.0.0` 中的 `model` 字段继续作为历史快照兼容入口；推荐配置使用后端专用的 `family.matlab_parameters` 或 `family.mujoco_parameters`。

## 参考、控制和执行器映射

`control.json` 可选择两种现有模式：

- `deterministic`：`reference.kind=actuator_commands`，具名命令按 `ramp_s` 斜坡进入控制器。
- `tip_feedback`：`reference.kind=task_goal`，目标来自公共 `TaskDefinition.goal.target_m`；算法是现有阻尼最小二乘末端反馈，参数为 `feedback_gain`、`damping` 和 `max_joint_update_rad`。

控制周期开始时读取末端、关节和绳长观测并更新命令；力信号也对应区间开始的求解器状态。区间积分结束后保存位置、速度和末端状态。每次运行从零执行器命令初始化并清空观测，不实现跨运行恢复。

映射顺序保持不变：具名执行器命令 → 按执行器速度限幅 → 行程限幅 → 传动矩阵（含卷筒半径、绕向和比例）→ 参考绳长 → 扣除预紧伸长 → 后端中的只拉不推及逐绳力上限。执行器的 `m`/`rad` 命令不是绳索力；实际执行器命令和绳长目标分别保存在 `actual_commands.json`。

未来控制器的预测模型与这里的仿真验证模型是不同职责。本轮没有实现规划器、轨迹优化、LQR、NMPC 或跨模型状态转换。

## 结构模板与离散

候选构建先选择最终完整结构，再验证离散。若模板增加、删除或替换柔性段，应在 `Space.template_discretizations.<template>` 给出与最终段 ID 完全匹配的完整离散；或者请求本身提供与最终结构完全匹配的离散。新增段没有明确来源会报 `DISCRETIZATION_MISSING_SEGMENT`，被删除段的空间参数不再应用；对失效段的显式修改会报 `DISCRETIZATION_SEGMENT_INACTIVE`。最终设计空间、任务窄约束、条件参数和物理检查仍全部执行。

## PowerShell 工作流

以下命令从仓库根目录运行。`prepare`、`build`、`compare` 和读取命令不启动动力学求解；每个 `run` 启动一次完整求解。

```powershell
conda activate softagent

# 只生成公共输入，不求解
python examples/platform_tendon_family.py prepare runs/my_family_run

# 编辑共同目标、安装或外力（两后端下次构建都会读取这一个文件）
$p = 'runs/my_family_run/inputs/experiment.json'
$j = Get-Content -Raw $p | ConvertFrom-Json
$j.task.goal.data.target_m = @(0.29, 0.035, 0.19)
$j | ConvertTo-Json -Depth 100 | Set-Content -Encoding utf8 $p

# 在 execution.json 选择 model.serial_bending_cells 和两个后端的专用数值设置
# 在 control.json 将 mode/reference 切换为 tip_feedback/task_goal 或
# deterministic/actuator_commands。编辑后重新 build。

# 构建、公共预检、MJCF 编译；不进行时间积分
python examples/platform_tendon_family.py build runs/my_family_run --candidate structural

# 各启动一次完整求解
python examples/platform_tendon_family.py run runs/my_family_run --backend matlab_spatial --candidate structural
python examples/platform_tendon_family.py run runs/my_family_run --backend family_mujoco --candidate structural

# 复用保存结果；不求解
python examples/platform_tendon_family.py compare runs/my_family_run --candidate structural
Get-Content -Raw runs/my_family_run/structural_comparison.json | ConvertFrom-Json
Get-Content -Raw runs/my_family_run/saved/structural_family_mujoco/control_spec.json | ConvertFrom-Json
Get-Content -Raw runs/my_family_run/saved/structural_family_mujoco/dynamics_execution.json | ConvertFrom-Json
```

旧单段入口仍可用：`python examples/platform_tendon_family.py run <root> --backend single`。旧的完整 `<backend>.json` 也仍由 `preparation.py` 读取；若两个旧输入的实验条件不同，它们会形成不同 `scene_identity`，一致性比较会拒绝，而不会静默选一份覆盖另一份。

## 结果与身份

每个保存目录包含实体描述、解析物理、离散、实验场景、实验身份、模型—后端执行计划、数值配置、控制规范、控制观测、实际命令、压缩轨迹和统一结果。`build` 还从注册源生成 `capability_catalog.json`，不维护第二份手写接口清单。选择记录保留请求、设计、离散、物理输入、模型、控制、场景和公共实验身份；改变来源后旧构建由 `CANDIDATE_BUILD_STALE` 拒绝，必须显式重建。
