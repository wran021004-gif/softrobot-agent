# MATLAB 三维后端与绳驱机器人家族接口

本轮基线及当前分支：`feat/independent-spatial-dynamics`，`6b2d9dd6f2c08d6cededbbf1b73b864335806c1d`。开始时工作区干净，未切换旧提交、未覆盖历史任务、未 commit/push/merge。旧 `backend.matlab`、`backend.math_planar`、`backend.math_spatial`、`backend.scene_mujoco` 保留原身份。

新增 `backend.matlab_spatial / matlab_serial_bending_v1` 和 `backend.family_mujoco / mujoco_serial_bending_v1`。主链路仍是原 Host 的 `simulation.run → candidate → compile/check → initialize → run → BackendResult → evaluation.run / signals.read`，复用预算、控制观测、执行回执和不可变 ExportBundle，没有另建 Harness。

## 直接执行

新运行必须使用新目录；下面创建三次真实求解。`build`、`compare` 和 `view` 不积分。MATLAB Engine 在 Codex 沙箱里启动时可能需要沙箱外运行权限，普通本地 PowerShell 不经过该沙箱。

```powershell
Set-Location D:\softrobot-agent
conda activate softagent
$familyRun = 'runs/my_tendon_family'
python examples/workbench.py platform tendon-family prepare $familyRun
python examples/workbench.py platform tendon-family build $familyRun
python examples/workbench.py platform tendon-family run $familyRun --backend single
python examples/workbench.py platform tendon-family run $familyRun --backend matlab_spatial
python examples/workbench.py platform tendon-family run $familyRun --backend family_mujoco
python examples/workbench.py platform tendon-family compare $familyRun
python examples/workbench.py platform tendon-family view $familyRun --backend matlab_spatial
python examples/workbench.py platform tendon-family view $familyRun --backend family_mujoco
```

查看本轮已经保存的结果不需要重跑：

```powershell
$familyRun = 'runs/tendon_family_20260917'
Get-Content "$familyRun/continuous_candidate.json" -Raw -Encoding UTF8
Get-Content "$familyRun/structural_candidate.json" -Raw -Encoding UTF8
Get-Content "$familyRun/shared_design.json" -Raw -Encoding UTF8
python examples/workbench.py platform tendon-family compare $familyRun
python examples/workbench.py platform tendon-family view $familyRun --backend matlab_spatial
python examples/workbench.py platform tendon-family view $familyRun --backend family_mujoco
# 本轮旧单段成功运行使用了显式重试标签：
python examples/workbench.py platform tendon-family view $familyRun --backend single --label permitted
```

可选的针对性检查命令（没有完整动力学求解）：

```powershell
python -m unittest tests.test_tendon_family_candidates
python examples/validate_tendon_family.py $familyRun --matlab
python examples/check_tendon_saved.py runs/tendon_family_20260917
```

最后一个命令专门读取本轮证据，包括 `single_permitted` 故障重试后的记录。普通新目录的单段保存于 `saved/single`。不需要为了查看数据再次执行这些验证。

## 文件与公共接口

| 内容 | 文件 |
|---|---|
| 设计、部件、截面站位、绳路、执行器、空间与结果契约 | `extensions/tendon_family/contracts.py` |
| 面积、质心、面积矩、合法内孔、截面插值 | `extensions/tendon_family/sections.py` |
| 串联连接、质量惯量、主轴弯曲、物理位置绑定与实体映射 | `extensions/tendon_family/compiler.py`；公共 `tools/design_compiler.py` 也接受 `Design` |
| 静态几何、绳长雅可比、虚功接口 | `extensions/tendon_family/geometry.py` |
| 数值/整数/选项/条件修改、完整模板替换 | `extensions/tendon_family/candidate.py` |
| 场景、具名初态、执行器控制与实时反馈 | `extensions/tendon_family/{scene,control}.py` |
| 独立后端生命周期与 MuJoCo 转换 | `extensions/tendon_family/{backends,mjcf}.py` |
| 信号与能力登记 | `extensions/tendon_family/{signals,manifest}.py` |
| 原 MATLAB 物理适配 | `extensions/tendon_family/legacy.py`（不改旧模型身份） |
| MATLAB 数学模型 | `matlab/tf_geometry.m`, `tf_point.m`, `tf_routes.m`, `tf_terms.m` |
| MATLAB 控制、积分、观测、静态检查 | `matlab/tf_control.m`, `tf_run.m`, `tf_observe.m`, `tf_static.m` |
| 保存轨迹原生查看 | `matlab/tf_view.m`, `extensions/tendon_family/saved.py` |
| 可继续修改的开发样例 | `examples/platform_tendon_family.py` |

`design.family_build@1.0.0` 接收 `family.build_request`：`baseline`、`space`、`changes`，返回完整候选、修改摘要、派生物理、映射和适用性。真正求解时 `candidate.family` 只使用冻结在会话策略中的 `family.space` 授权范围，不能用工具调用偷偷扩大搜索范围。原连续 `changes` 用法保持；公共操作不再将所有值转成 float。旧搜索器没有被升级成混合整数优化器。

例如连续修改为 `{"components/near/length_m":0.17}`；整数修改为 `{"components/near/cells":4}`；结构修改为 `{"template":"tube_distal"}`。模板保存完整新设计，包含连接、路由、锚点、驱动及默认值；可以用完整模板表达添加、删除、替换部件或改变绳数，无任意代码执行。字段路径采用具名部件选择，站位列表内使用明确序号。`type=number/integer/choice`、`bounds/options` 和 `when` 是当前支持的空间语法；任务 `policy.editable` 中额外给出的数值范围继续生效。

`family.initial` 使用具名关节字典，未指定项明确为零。改变单元数无需重写零初态；显式引用已删除关节会被拒绝。信号实体按实际解析结果展开；`actuator_command` 按执行器分别声明 `m` 或 `rad`，一个共享执行器始终只有一个命令实体。绳索张力按绳索实体展开，与执行器数无关。

`visualization.saved_replay` 已接入 `family.backend_data` 的导出包恢复；准备保存轨迹，不打开引擎。原信号读取、`diagnostics.sample_exceeds` 可以继续使用。旧专用诊断规则和视频服务尚未迁移到家族轨迹格式，会明确拒绝，不能当作缺省零值。本轮实际验证了 `signals.read`、保存包恢复、MATLAB 原生 Figure 和 MuJoCo 保存 XML/qpos 的原生渲染；未自动打开交互窗口。

## 物理定义与边界

局部 x 沿结构段，截面在 yz 平面。每个柔性计算单元是一个带质量、质心、惯量的刚体，根部两个有弹性和阻尼的弯曲转动自由度。不是有限应变连续体求解器。实际结构段由设计指定，`cells` 只控制离散数量。

每个截面首先在其声明方向计算面积、质心及中心面积矩，然后选取弯曲主轴。材料模式 `EI=E I_area`，质量 `rho A ds`；非对角质量惯量保留，MuJoCo 通过 `fullinertia` 输入，MATLAB 使用旋转后的完整张量。刚性件质量、偏置 COM 和完整惯量参与所有祖先自由度的动力学。等效模式的线密度和两个主轴 EI 是唯一权威输入；惯量按指定截面的均匀面密度计算。该等效模式不宣称来自某种材料。阻尼为独立给出的主轴弯曲黏性除以单元长度。

站位 `s∈[0,1]` 绑定物理段位置，解析为所在单元及局部位置；边界归属下一个单元，末端归属最后一个单元。截面分段常量或同一解析类型的尺寸/方向线性插值，在单元中点取样，作为整个单元的常量。这是明确的离散近似，不声称精确积分任意变截面。多边形支持分段变化，不支持轮廓顶点插值。截面图形采用轮廓侧壁，端面开放；真实截面面积矩与显示三角网格精度分开。

自然曲率输入在段的物理 yz 轴定义，转换至局部弯曲主轴后形成弹簧自然角；它不是新增材料扭转自由度。所有段/刚性件按父连接的完整安装位姿递归计算。绳路按每根绳明确给出的 `start → guide… → anchor` 路径计算，不生成默认全臂路径。无摩擦直线绳段张力通过 `-J_lengthᵀ T` 作用于所有相关自由度，中间锚定绳对远端自由度的导数为零，跨段绳对近端导向部件仍施力。

引擎共用解析物理，互不读取对方数值。MATLAB 内部计算运动学、质量矩阵、惯性偏置、重力、弹性、阻尼、绳长/张力、外力及接触近似，用 `ode15s` 时间积分，无额外付费工具箱。Python 只负责解析、静态几何接口、启动和序列化，不为 MATLAB 提供三维加速度。MuJoCo 独立消费部件、完整惯量、逐点 site 路由和长度力元。

共同参数契约中的 `max_step_s / rtol / atol / contact_stiffness_n_m / contact_damping_n_s_m` 明确仅用于 MATLAB；MuJoCo 能力目录将它们列为未启用参数，非默认赋值在公共预检被拒绝，避免静默忽略调参。MuJoCo 使用场景 `timestep_s`、`implicitfast` 及 XML 中的接触参数。

理想传动满足 `length_target = reference_length + B u - pretension / servo_gain`。位移命令以米为单位；旋转命令以弧度为单位，`B=绕向/传动比×卷筒半径`。限速先作用于单个执行器，再做行程限幅；矩阵一次映射到所有关联绳索。长度伺服 `T=clip(kp(length-target),0,Fmax)`，松绳张力为零。伺服增益不是绳材料刚度；预紧是零位姿下的名义张力偏置。限拉力为每根绳的力元上限，没有宣称总电机转矩上限。MuJoCo XML 中每绳一个长度伺服是力元，共享电机由同一个 `u` 和 `B` 联动，实际电机列表及关联写入 `compiled_physics.json`。

反馈控制从当前世界末端误差和真实状态的末端/绳长雅可比计算限幅关节增量，投影到实际执行器映射后更新命令。它是确定性阻尼逆雅可比反馈，不是多段 PCC，也不保证任务成功。确定性模式则按具名执行器命令和斜坡直接运行。两后端观测均在控制区间开始；保存状态/绳长位于区间末端，张力和力矩位于开始的 `pre_step_solver`，不能混用采样时刻。

场景使用固定安装、具名平面、具名初态和作用于部件 COM 的世界外力。外力窗口为 `[start,end)`，边界需落在控制网格；柔性段外力需指定解析单元实体，刚性件可直接使用部件名。本轮 MATLAB 使用最低包络顶点的法向惩罚，MuJoCo 使用凸包接触；没有验证接触精度。两后端无切向摩擦/自碰撞。一般多边形和内孔的面积惯量是真实截面计算，MuJoCo 的凸包碰撞会填平凹处和内孔；导向件为盒状碰撞包络。外置绳路不受旧 `0.9 × body_radius` 规则约束；只检查显式导向孔的孔壁、间距和绳径。连续内通道、滑轮包络和摩擦没有实现。

## 支持与实际验证

| 对象 | 可描述 | 可编译/求解 | 本轮验证 |
|---|---|---|---|
| 串联多段、变单元数、逐段物性、非圆方向 | 是 | MATLAB / MuJoCo | 两段候选各 0.35 s，10 DOF |
| 固定刚性连接件、导向件、末端负载 | 是 | 两后端 | 偏置 COM、非对角惯量与外力实际生效 |
| 圆、圆管、椭圆、矩形、合法带孔简单多边形 | 是 | 两后端；接触近似 | 解析几何检查；椭圆/矩形动态；圆管结构候选两引擎静态；多边形未单独动态求解 |
| 跨段逐根路由、中间/末端锚定 | 是 | 两后端 | Jacobian、虚功、静态引擎对应及动态轨迹 |
| 独立/共享理想执行器、绕向/卷筒、限幅 | 是 | 两后端 | 独立驱动动态；共享双绳两引擎静态控制/力计算，没有额外共享动态求解 |
| 连续、整数、选项、条件参数、完整结构模板 | 是 | 公共候选编译 | 连续及结构双后端输入；三项针对性边界测试 |
| 分支、闭环、索并联、离散柔性/绳驱刚性关节 | 类型保留 | 否，公共预检拒绝 | 不会产生性能分数 |
| 材料扭转、剪切、轴向伸长、弹性绳、摩擦、电机动力学 | 明确未实现 | 否 | 无支持声明 |

候选构建分别返回 `physically_invalid` 与 `backend_unsupported`。后端积分故障返回失败并保存部分证据；评价器只对有效结果给出性能分数，评价有效而未达目标为 `task_success=false`。旧搜索驱动不会把公共预检失败当作低性能标量。

## 本轮证据

证据目录 `runs/tendon_family_20260917`；简要可版本化报告为 `docs/evidence/tendon_family.json`。原始回执、配置、描述、物理、场景、控制观测、命令和轨迹均在原平台库及 `saved/` 下。`continuous_candidate.json`、`structural_candidate.json`、`shared_design.json` 可直接检查。

两段基线为近段 0.16 m 椭圆、远段 0.12 m 变矩形；连续候选把近段改为 0.17 m，质量 0.0775749761 kg。结构候选把远段改成圆管并由 2 单元增至 3 单元，总 12 DOF，质量 0.0782339769 kg（该模板保留近段基线 0.16 m）。每段三绳只属于样例配置。另一个小例有一个 0.12 m / 两单元等效段、两根绳和一个相反绕向的 0.01 m 卷筒执行器。

本轮实际完整求解 **3 次**。第一次 MATLAB 启动被 Windows 沙箱拒绝，未开始积分，但 Host 保守记账消耗了 1 次 backend_solves；保留失败记录后用 `single_permitted` 显式重试。因此平台账面合计 **4 次**，实际数值求解为下面三次。没有第四次完整求解，也没有为变更查看器重复求解。

| 运行 | 仿真时间 | 公共准备/解析 | 引擎准备 | 纯求解 | 后端调用总耗时 |
|---|---:|---:|---:|---:|---:|
| MATLAB 旧单段适配 | 0.04 s | 0.00336 s | 9.282 s 启动 | 0.635 s | 10.125 s |
| MATLAB 新多段 | 0.35 s | 0.00446 s | 6.927 s 启动 | 2.045 s | 9.160 s |
| MuJoCo 同一多段 | 0.35 s | 0.00421 s | 0.0201 s 编译 | 0.0118 s | 0.3078 s |

MATLAB 的准备还包含单次静态输出/JIT，计入后端总耗时，未混进 `.m` 内部 `solve_s`。MuJoCo 总耗时也包括库导入/导出。两个候选的公共预检及真实 MuJoCo 编译合计约 1.142 s。以上只代表此次小模型/机器，不说明数学后端天然更快。

两后端共同初始目标误差 60.075 mm；MATLAB 最终 31.5909 mm，MuJoCo 最终 31.5461 mm，均未达到固定 10 mm 容差。最终末端后端差异 **0.05647 mm**，整段轨迹末端差异 RMS **0.07417 mm**，绳长最大差异 **0.01369 mm**，张力最大差异 **0.009016 N**。两后端 y/z 关节变化范数约 0.226/0.179 rad，体现空间弯曲；0.12–0.19 s 的八个预采样点记录了负载外力。

静态独立计算检查：连续/结构/共享配置的 MATLAB 与 MuJoCo 质量矩阵最大绝对差异不超过 `1.94e-15 kg·m²`，惯性偏置减重力与 MuJoCo bias 差异不超过 `4.17e-17 N·m`；跨段绳长方向导数有限差分误差不超过 `6.76e-10 m/rad`。旧单段 MATLAB 静态质量、偏置、重力与既有 Python 空间模型也匹配。它们说明离散模型实现一致，不是物理标定或完整模型精度证明。

保存结果检查确认：动态信号数量跟随候选、实时观测等于上一保存状态、共享矩阵公式与实际命令一致、绳路/末端可由保存 q 重建、完整惯量进入 MuJoCo。`matlab_saved_figure.png` 为 MATLAB 原生 Figure 导出；`mujoco_saved_frame.png` 使用实际保存 XML/qpos 渲染。读取和查看没有触发新动力学求解。

下一步从 `examples/platform_tendon_family.py::example_design()` 或 `inputs/design.json` 继续；对新结构先调用 `design.family_build` 或 `build`，查看 `status / applicability / entity_map`，再用显式新会话求解。尚未完成的范围是表中预留家族与接触/材料物理，以及通用混合整数搜索和旧视频诊断格式迁移；没有把这些列为可计算能力。
