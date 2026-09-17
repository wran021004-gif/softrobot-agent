# 绳驱串联机器人：模型、控制与双后端入口

推荐入口是 `examples/platform_tendon_family.py`。它仍使用公共 Host、Registry、Store、预算、缓存、回执、评价、信号和 `ExportBundle`，但输入不再复制两份任务。

## 有界优化、保存诊断与按需视频

公共 Python 入口为 `extensions.tendon_family.optimization.optimize(root, request)`；项目使用既有 `Store.create(ProjectConfig)` 授权。`family.optimization_request` 包含 `session`、可选完整 `template`、`variables` 的边界、`method`、`max_trials` 和归一化步长 `step`。目标、单位、方向及成功容差都引用 `session.task`，求解配额来自 `session.policy.budget` 和项目总预算。

`prepare-opt` 生成的 `inputs/optimization.json` 是自包含请求快照；编辑这个文件后再执行 `build-opt`，不要期望之后修改其他输入文件会隐式改写它。`inputs/execution.json` 只供示例的另一后端复核选择后端。模板选择先完成，再冻结为会话基线；原始请求封存在 Store 的 optimization 事件中。每个候选的 `CandidateInput` 保存实际设计、离散、控制、模型和后端配置。恢复要求同一请求、依赖和会话；重复已封存调用返回原回执，不新增求解。

实体路径沿用 `components/<id>/...`、`tendons/<id>/...` 等 `Space.parameters`；控制路径为 `control/feedback_gain`、`control/damping`、`control/max_joint_update_rad`、`control/ramp_s`，边界在 `Space.control_parameters`。只接受有界连续数值变量，并继续检查已有任务窄约束。模板和条件参数接受既有最终候选检查；离散可在实验方案中配置，但不能进入连续实体性能搜索；轨迹变量未实现。外层调用者可分别提供不同模板请求，在相同任务和后端条件下比较，当前不是混合整数优化器。

`search.family_coordinate` 复用已有有界坐标步，基线后按正、负方向逐轴提案。无效候选/不支持能力保留原因，不参与排名；有效但任务未达标的候选仍有真实指标。求解失败不会成为普通低分；预算不足返回已知最佳有效候选及停止原因。设计与控制共同变化时，结论针对完整组合，不归因于单一结构参数。

```powershell
Set-Location D:\softrobot-agent
conda activate softagent
$run = 'runs/my_family_optimization'  # 首次准备使用新目录
python examples/workbench.py platform tendon-family prepare-opt $run
# 按需编辑 $run/inputs/optimization.json；默认固定 tube_distal 模板、搜索 near 长度
python examples/workbench.py platform tendon-family build-opt $run
python examples/workbench.py platform tendon-family optimize $run
$best = python examples/workbench.py platform tendon-family best $run | ConvertFrom-Json
$best.best.candidate_id
$best.configuration.effective  # 完整实际配置
python examples/workbench.py platform tendon-family crosscheck $run
python examples/workbench.py platform tendon-family diagnose $run
python examples/workbench.py platform tendon-family video $run --t-start-s 0.01 --t-end-s 0.35 --fps 25 --azimuth-deg 135 --elevation-deg -20
```

默认常规预算是 MuJoCo 3 个候选（含基线）加 MATLAB 1 次复核。示例参数为 near 长度 `[0.14, 0.20] m`，归一化步长 `0.2`；选择模板的基线长度为 `0.16 m`，控制反馈增益固定为 5。请求中已声明控制增益 `[2,8]` 授权范围，需要联合整定时把 `control/feedback_gain` 加入 `variables`；3 次试验通常尚未遍历第二轴，不应据此声称收敛。

诊断使用具名关节、绳索和执行器，保留单位、坐标系及相位；末端误差曲线仅描述保存观测，不再评价任务。近拉力上限、近零张力及最短区间复用 `tools.trajectory_diagnosis.RULES`；执行器行程用 1% 行程带、速度用相邻命令采样差分及已保存速度上限的 99%，这些现象不证明实际裁剪。无数据时列出缺失项。关节只报告已记录运动/速度，当前未配置关节限位。关键发现带结果 EvidenceRef 和信号时间区间，可能原因与建议保持独立。

视频选择输入结果即可确定后端。MuJoCo 从保存 XML 和具名关节状态调用 `mj_forward` 重建画面，**不调用 `mj_step`**；MATLAB 从保存刚体姿态和绳路复用 `tf_view` 原生 Figure。输出 MP4、预览、来源、视角/帧率和零额外求解回执，恢复/封存及超时继续使用现有公共工具。默认不会为优化候选生成视频。旧不兼容格式会明确失败；MATLAB Figure 适配的无积分检查与实际渲染验证范围见本轮记录。

模型默认值在 `resolve_execution` 统一规范化，省略默认值与显式默认值具有同一模型身份；`included/omitted` 必须等于已注册实现，不能作为物理开关。build 的 MJCF 与 run 使用同一后端参数。旧 compare 从不可变 `CandidateInput`、任务、结果和已知旧模型映射恢复依据；材料不足返回 `not_comparable`，不修改历史记录。

实际候选、误差、诊断和视频见 [步骤 5–6 结果](steps_5_6_result.md)。

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
