# 公共物理、独立数学模型与统一实验场景

后续新增的真正 MATLAB 三维执行、多段家族设计与双后端贯通见 [tendon_family.md](tendon_family.md)。本文保留原单段模型的历史说明和身份。

当前入口仍是 `python examples/workbench.py platform ...`。本轮基于 `fix/domain-signal-contracts` 的 `ca777786817a944e30b401b30b5e2f7889d87a57`，在 `feat/independent-spatial-dynamics` 实现；没有提交、推送或合并。原工作区干净，旧任务、历史数据、学习扩展和模型身份保留。

主链路：`domain.rod_design → candidate.rod_design → RobotIR → ResolvedPhysics + Scene → backend.math_spatial / backend.scene_mujoco → BackendResult → signals.read / evaluation.run / diagnostics.sample_exceeds`。全部通过原 Host、ToolRequest、ToolReceipt、预算、EvidenceRef 和 ExportBundle；没有新增证据库或运行系统。

人定义任务目标、评分和设计空间；LLM 可以选择工具及参数；数值优化器负责搜索；控制器和后端负责时间步。本例没有 LLM 请求、搜索循环或自动筛选调度。

## 一次完整示例

在仓库根目录使用新目录；默认 C2。prepare 只读取设计和环境／任务 YAML，不读引擎模型文件，不启动后端。math_spatial 不需要安装 MATLAB 或 MuJoCo。

```powershell
conda activate softagent
$runDir = 'runs/my_spatial_development'
python examples/workbench.py platform spatial-example prepare $runDir
python examples/workbench.py platform check "$runDir/inputs/math_spatial.json"
python examples/workbench.py platform spatial-example run $runDir --backend math_spatial
# 可以在另一时刻，或安装了 MuJoCo 的环境中单独执行：
python examples/workbench.py platform spatial-example run $runDir --backend scene_mujoco
python examples/workbench.py platform spatial-example compare $runDir
```

每个 run 建立会话并依次调用 `simulation.run`、`evaluation.run`、`signals.read`（末端／张力）、`diagnostics.sample_exceeds@1.1.0`、`evidence.read`。数学 run 自动进入干净子进程：导入钩子阻断 MuJoCo，文件审计阻断 `.xml/.mjb` 读取；从候选构建、预检、装配到求解、导出、评价都在此进程。无缓存回放，仿真请求明确 `cache=new`。同名会话再次 run 会拒绝；继续查看用 status/evidence，不以新 run 重复求解。

如需固定绳长模式，在新的目录 prepare 时加 `--control C1`，其余命令相同。每份项目预算两次求解、每个会话一次；数学与物理可以分开执行。原模型／任务文件不会被改写。

生成的配置和 simulation.json 也可用于普通 `platform project-create / create / call`，示例只是同一公共调用的固定流程编排。运行记录位于 `<backend>_record.json`，内容证据在原 `platform.sqlite`。读取结果的通用工具请求如下（引用和 execution_id 从 simulation 回执取得）：

```json
{"request_id":"read-joint","tool_id":"signals.read","tool_version":"1.0.0","arguments":{"result":{"artifact_id":"替换为结果的64位内容身份"},"name":"joint_position","entity":"joint_3_z","phase":"post_step"},"reason":"读取保存结果"}
```

本例改变总长为 0.32 m、体半径为 0.019 m、绳路半径为 0.016 m，控制弯曲向量为 [0.5, 0.8] rad。安装点 [0.01, −0.01, 0.03] m，绕世界 z 旋转 0.15 rad；每节初始 [y,z]=[−0.003,0.002] rad，初速度 [0,0.01] rad/s。末节质心在 [0.006,0.014) s 承受世界力 [0,0.2,0.1] N。目标 [0.30,0.04,0.08] m、容差 0.01 m，20 ms 运行；这些是独立开发配置，目标和评分不随候选改变。

## 接口与职责

所有新契约版本为 1.0.0，均在 `extensions/experiment_dynamics/manifest.py` 的原注册表登记。公共信封未改类型；`task.reach` 额外接受成对的 `experiment.assembly + initialize.experiment`，仍使用原 `evaluate.reach` 和目标／容差语义。

| 分类／角色 | 入口及文件 | 输入 → 输出／语义 |
| --- | --- | --- |
| 机器人设计／原适配 | `extensions/robot_domain/candidate.py:apply_design` | 冻结会话设计＋绝对 changes → 完整重建 RobotIR；candidate_id 仅为标签，不加载父候选 |
| 公共物理／内部库 | `experiment_dynamics/physics.py:resolve_physics` | DesignSpec 或 RobotIR → `experiment.physics`，版本／IR 来源／内容身份、具名零件和绳路 |
| 场景装配／内部库 | `scene.py:assemble` | SessionInput＋公共物理 → `experiment.scene`，安装关系、环境、初态、目标、外力、来源和身份 |
| 初态／注册适配 | `initialize.experiment`，`scene.py:initialize` | `experiment.initial` 的 16 维 q/v → 原 Payload；无随机改变 |
| 数学模型／内部数值库 | `spatial.py:SpatialModel` | 公共物理、场景、数学参数、q/v/命令/外力 → 几何、雅可比、质量矩阵、广义力和加速度 |
| 控制／注册适配 | `controller.experiment_length`，`backends.py:LengthController` | 原 `legacy.control` C1/C2 → 四根长度指令；复用已有控制算法 |
| 数学／仿真后端适配 | `backends.py` 三个 backend | compile → initialize → run → export → close；输出原 BackendResult |
| 信号／内部适配 | `signals.py` | 模型实体展开＋真实原始行 → SignalSpec／Signal；复用旧符号／选择工具 |
| 评价与诊断／原公共工具 | `evaluation.run`、`signals.read`、`diagnostics.sample_exceeds@1.1.0` | 已保存引用 → 评价、信号、阈值事件；不再求解 |
| 固定示例编排 | `examples/platform_spatial_example.py` | 原公共工具顺序调用；不是新原子或新搜索器 |

表中文件短路径均相对于 `extensions/`。完整输入输出 Schema 和实现状态来自 [生成目录](platform_generated/catalog.md) 与 [生成契约](platform_generated/contracts.json)。原八类能力、旧数值库和待办分类见 [领域指南](platform_domain.md)。证据、会话、记忆、技能、工作者仍属平台公共服务。本轮没有新增搜索算法或多模型调度。

## 唯一物理来源

`tools/design_compiler.py:build_exploration_ir` 继续定义 `ds=L/8`、`m=线密度×ds`、等效圆柱质心惯量、`k=EI/ds`、`c=弯曲粘性/ds`、`natural_y=−自然总角/8`。root EI 与 tip 比率的原逐节插值保留。线密度、EI、粘性是独立等效输入，没有从半径另推材料定律。

`resolve_physics` 只搬运这些已推导量，没有第二套质量／惯量／刚度公式。每个 Part 记录实体、父实体、父坐标中的连接位置、局部长度／半径、质量、局部 COM、关于 COM 且在零件局部轴表达的完整 3×3 惯量、y/z 轴、双轴刚度／阻尼／自然角。当前圆柱完整惯量是对角矩阵，空间计算用 `R I Rᵀ` 转到世界坐标。每根 Tendon 记录绳实体、执行器实体、局部 yz 偏置、路径经过实体、长度伺服增益和拉力上限。

数学模型直接读取这份说明。四绳 V2 的 `compile_mujoco` 从同一说明写入显式质量、COM、惯量、刚度／阻尼和伺服参数；旧 V1 与其他旧模型兼容逻辑保留。MuJoCo 的编译反读仅在物理运行中作为实际输入证据导出，绝不是数学运行的输入。

设计输入在会话中只存一份 `domain.rod_design`。现有开放连续参数及单位、全局范围见 [设计空间表](platform_domain.md#设计空间唯一-designspec--完整-robotir)；仍包含总长、体半径、绳路半径、线密度、EI／tip 比、粘性、自然角、伺服增益／拉力上限及原控制参数。会话 editable 是更窄的授权边界。固定 one section、eight segments、four tendons；segments 是计算离散节，不能当作八个结构 section。没有开放任意路由或新的离散参数。

## 模型选择和数值含义

无需另一套模型注册器：选择 `policy.backend` 的注册身份和类型化参数。

| backend | 参数契约／模型身份 | 适用范围与依赖 |
| --- | --- | --- |
| `backend.math_spatial` | `experiment.spatial_parameters` / `spatial_rigid_link_v1` | NumPy、SciPy；16 自由度空间耦合、任意固定安装姿态、显式 q/v、地面、定时质心外力；C1/C2 |
| `backend.math_planar` | `experiment.planar_parameters` / `matlab_tdcr_planar_dynamic_v1` | 仅 NumPy＋已有 MATLAB Engine；原 MATLAB 算法完全保留；单位安装、零初态、世界 x-z 目标／重力／控制、无外力；C1/C2 |
| `backend.scene_mujoco` | `experiment.mujoco_parameters` / `mujoco_assembled_rod_v1` | NumPy、MuJoCo；与三维数学模型消费相同公共物理和场景；C1/C2 |

平面适配超出范围会明确返回 `PLANAR_V1_SCOPE`，不会把 z 轴状态丢弃后继续执行。新三维模型拥有独立身份，不解释成原 MATLAB 平面结果。旧 `backend.matlab`、`backend.mujoco`、`DynamicsBackends`、`export_shared` 保留原兼容含义；旧 MATLAB 反读 MuJoCo 的路径不再用于新接口／示例。

三维模型每节按 `Ry(q_y) Rz(q_z)` 组合转动，轴随上游姿态改变。使用每节质心平移／转动雅可比累加完整质量矩阵；零广义加速度下递推偏置加速度及角加速度，保留离心、科氏和陀螺项。动力学方程及实现位于 spatial.py 文件头。不是两个二维系统拼接。推导依据：[MIT 多体动力学](https://underactuated-r1.csail.mit.edu/multibody.html)；MuJoCo 驱动／力矩映射参照[官方计算文档](https://mujoco.readthedocs.io/en/latest/computation/)。

绳长是基座导向点经各节远端导向点的三维折线长度；张力 `T=clip(kp×(length−command),0,fmax)`，广义绳力 `−J_lengthᵀ T`，不允许推绳。重力、弹性、阻尼和外力均进入同一耦合方程。数学积分默认 RK45（rtol=1e−6、atol=1e−8、max_step=0.0002 s），MuJoCo 默认 implicitfast；均独立记录求解配置。

数学地面使用各节两端半权重、单边法向弹簧／阻尼近似，参数放在 SpatialParameters；MuJoCo 使用引擎接触求解和 MJCF 中记录的默认接触／摩擦设置。它们不是同一个接触模型。未实现轴向伸长、剪切、材料扭转、绳索摩擦、自碰撞；空间姿态组合不等于新增材料扭转自由度。

## 场景与控制

`experiment.assembly` 持有原 EnvironmentSpec、明确 floor_id、固定 mount 和外力列表。`experiment.initial` 由任务 initializer 提供唯一 q/v 源，顺序为 `joint_0_y, joint_0_z, …, joint_7_y, joint_7_z`。目标仍来自任务 goal；Scene 只带来源明确的冻结投影，不开放可另改的评分或目标。

安装使用 robot_id=`robot`、mount_id=`fixed_base`、世界位置（m）、单位 wxyz 四元数。零件实体为 `segment_i`；物体使用自身 name 和 floor_id 选择，不取数组第零项。当前只允许一个水平无限地面；球、斜坡、窗框、移动平台等会报具体不适用对象。

TimedForce 绑定 `robot / segment_i`，作用点固定为该节**移动质心**，世界坐标 N，无额外力偶；时间窗 `[start_s,end_s)` 必须落在会话 timestep 网格且在总时长内。空列表表示无外作用。数学通过 `J_comᵀ F` 映射，MuJoCo 用 `xfrc_applied` 的质心世界力；相同实体多个力相加。

C1 保持既有长度映射；C2 复用 `controllers/pcc_tip_feedback.py`。新空间后端每个控制时刻读取实际末端、q/v 和绳长；记录真实世界观测，将末端和目标转换到固定安装坐标后交给原 PCC 反馈。反馈只使用末端；没有声称张力反馈已实现。controller_observations.json 保存实时输入，controller_updates.json 保存实际更新。数学平面仍由 MATLAB 内部原 C2 观察实际平面末端，更新日志未由旧程序导出，因此该适配的 controller_updates 为 null，空 Python 日志不代表无反馈。

## 信号、评价和证据

| 名称 | 实体／单位／坐标 | 空间后端时间语义 |
| --- | --- | --- |
| tip_position | tip，3 维 m，world | post_step，t=(k+1)dt |
| joint_position / joint_velocity | 每节 y/z 共 16 个标量，rad / rad/s，joint_local | post_step |
| tendon_length / tendon_command | tendon_0…3，m，actuator | pre_step_solver，t=kdt；命令在本间隔保持 |
| actuator_force / tendon_tension | tendon_0…3，N，actuator | pre_step_solver；驱动力负号表示拉，张力=负驱动力，正号表示拉 |
| actuator_torque / passive_torque | 各 joint_i_y/z，N.m，joint_local | pre_step_solver；passive 为弹性＋阻尼 |
| external_torque | 各 joint_i_y/z，N.m，joint_local | pre_step_solver；已施加世界质心外力的广义力 |
| contact_count | contact，count，world | 数学为正近似法向力的节数，MuJoCo 为检测接触点数；不可直接作同一物理量比较 |
| floor_gap / contact_normal_approx | segment_i，m / N，world | 仅空间数学后端，pre_step_solver；后者为世界 +z 法向近似 |

执行器力的信号实体沿用绳路实体约定；与 ResolvedPhysics 中 `tendon_i_actuator` 一对一显式对应，不按未声明数组推断。模型实际节数／绳数用于展开；平面适配仅八个 y 关节。平面原信号均在 sampled_state，位置和力使用原 MATLAB 同时采样语义。空间数学与物理的步后状态不与步前力强行对时；缺失信号不补零。三维原始路线／形状和配置继续保存。

读取同名信号时指定 entity／phase；歧义会拒绝。`solver_status=completed`、`EvaluationResult.validity=valid`、`task_success=true` 是三件不同的事。评价调用仍在原 task.reach 目标和容差下进行；不同模型保留独立 comparison_identity，本例 compare 仅在物理／场景身份一致时展示差值，不合并评价身份或宣布物理真值。

ExportBundle 保存 resolved_physics.json、experiment_scene.json、robot_ir.json、solver_configuration.json、trajectory.json.gz、控制观测／更新等文件；MuJoCo 另存 robot.xml 与 compiled_physics.json。候选、源结果、执行 ID、来源事件均沿用平台链路。新装配结果可用通用信号读取／阈值诊断；旧保存轨迹诊断和图形回放明确拒绝 `SAVED_LEGACY_MODEL_UNSUPPORTED`，不伪装成旧平面 JSON。旧路径和旧证据的桥接不变。

## 本轮验证与限制

定向检查：`python -m unittest tests.test_experiment_dynamics -v`，三组通过；另运行旧保存数据桥接测试 `tests.test_platform_domain.DomainTests.test_archive_bridge_aliases_and_legacy_entry`，通过。覆盖原派生量、来源／场景同一性、空间惯性耦合、绳长有限差分雅可比、绳索／外力虚功、惯性功率恒等式、C1/C2 实际控制调用、模型范围拒绝、信号实体和旧入口。没有全仓测试。

实际证据目录 `runs/independent_spatial_20260917`，摘要见 [验证记录](evidence/independent_spatial.json)。真实求解仅 **2 次**：空间数学 1 次（干净子进程，无 MuJoCo 或引擎文件），MuJoCo 1 次，均 20 ms。两边各调用六个公共工具，模型调用为零；评价／读取／诊断额外求解为零。

数学／物理最终末端距离分别为 0.048838704 / 0.048870853 m，原容差均为 0.01 m，因此均 valid、task_success=false。两边末端差约 0.000150493 m。数学实际 y/z 关节变化范数分别 0.059798 / 0.033149 rad，证明不是只旋转基座得到“空间”轨迹。两边均确认四个外力采样时刻、10 个真实控制观测；compiled_physics 的质量、COM、惯量特征值、刚度、阻尼和初态与公共说明一致。compare 的后续审计只读内容存储，没有额外编译／求解／评分。

未验证：新平面输入适配的 MATLAB 数值运行（本轮预算只执行上述两次，原 MATLAB 算法未改）；C1 完整数值积分仅复用已验证求解通路，定向检查实际固定命令生成；长时稳定性、接触精度、实物标定、复杂场景和跨后端统计一致性均不在本轮范围。例中没有接触发生，不把地面近似称作已验证接触模型。后续如需平面短运行，必须使用新目录：

```powershell
python examples/workbench.py platform spatial-example prepare runs/my_planar_development --control C1
python examples/workbench.py platform spatial-example run runs/my_planar_development --backend math_planar
```

该独立平面配置显式改为零初态、单位安装和 x-z 目标、无外力，保留原容差；不能拿它与上述不同空间场景强行配对。仅需本机已有 MATLAB Engine／许可证，不安装任何额外付费工具箱。

后续待办限于新模型保存轨迹诊断／回放适配、必要模型验证，以及将来在现有搜索器之上编排少量物理复核。本轮未实现批量初筛调度、优化算法或新机器人家族。
