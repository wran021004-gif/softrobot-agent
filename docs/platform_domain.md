# 公共平台与机器人领域能力

当前入口：`python examples/workbench.py platform ...`。本轮从 `a716f32` 创建 `feat/platform-domain-integration`，接通既有模型和工具，不改变历史任务、评分或实验。通用开发步骤见 [扩展指南](platform_extensions.md)，实际注册项及输入输出 Schema 见 [生成目录](platform_generated/catalog.md)／[capabilities.json](platform_generated/capabilities.json)。

**职责**：人定义目标、评价标准和设计空间；LLM 选择工具及参数；数值优化器提出搜索候选；控制器与后端执行时间步。`simulation.run` 是完整执行操作，不要求 LLM 逐步推进仿真。证据、记忆、技能、工作者和会话管理属于平台公共服务。

## 一条可直接运行的真实链路

从仓库根目录运行，选择新的独立开发路径。prepare 只生成配置和请求，不启动模型或求解器。

```powershell
conda activate softagent
python examples/platform_domain_example.py prepare runs/my_domain_dev
python examples/workbench.py platform check runs/my_domain_dev/inputs/mujoco.json
python examples/workbench.py platform project-create runs/my_domain_dev runs/my_domain_dev/inputs/project.json
python examples/workbench.py platform create runs/my_domain_dev runs/my_domain_dev/inputs/mujoco.json
python examples/workbench.py platform call runs/my_domain_dev domain-mujoco runs/my_domain_dev/inputs/simulation.json
python examples/platform_domain_example.py run runs/my_domain_dev --backend mujoco
python examples/platform_domain_example.py run runs/my_domain_dev --backend matlab
python examples/workbench.py platform events runs/my_domain_dev domain-mujoco
```

`run` 是七次公共 `Host.invoke` 的紧凑演示：仿真 → 评价 → 选择腱执行器力信号 → 保存轨迹诊断 → 接触规则 → 回放数据准备 → 读取有效候选。它与 CLI call 使用同一请求和账本，不直调底层函数完成主链路。上面的 CLI 已封存 `domain-solve` 后，脚本重用同一请求，不重复求解；也可只运行 prepare 和两条 run，由脚本创建项目／会话。不要修改已封存请求的参数后复用其 request_id。

输入沿用现有 `task.reach`、reach_shifted 目标 `[0.30, 0, 0.08] m`、0.01 m 容差和原环境，时长 0.08 s；没有新任务或批量优化。输出 `<backend>_record.json` 保存所有回执、有效候选、评价和费用，`platform.sqlite` 保存不可变证据。项目限两次求解，每个后端会话一次；模型预算为零。MATLAB 仍需已有 Engine／许可证，且这一路的共享模型导出需要 MuJoCo。

## 设计空间：唯一 DesignSpec → 完整 RobotIR

`candidate.rod_design@1.0.0` 使用 `domain.rod_design@1.0.0`（`RodDesign`，基于既有 DesignSpec）。会话 `robot.structure.data` 是唯一可编辑设计来源；candidate_builder 参数为空，不另放一份基线设计。后端同时保留原 `legacy.robot_ir` 输入兼容。

changes 是相对**冻结会话基线的绝对值覆盖**，不是增量，也不自动继承同名／父候选。`candidate_id` 只是标签；`CandidateInput` 保留 baseline_identity、changes、effective 和 content_identity。构建器复用 `build_robot_ir/build_exploration_ir` 的数值范围和 `r_tendon <= 0.9*r_body` 检查；重新生成节长、路由、每节质量／惯量、刚度／阻尼和自然角。实际后端再次从设计编译 IR，导出的 robot_ir.json/shared_input.json 保留真实编译量。

| changes 字段 | 单位 | 既有模型允许范围 | 作用 |
| --- | --- | --- | --- |
| design.total_length_m | m | [0.05, 0.8] | 节长 L/8、质量、惯量、EI/ds、粘性/ds |
| design.body_radius_m | m | [0.005, 0.05] | 碰撞几何与等效圆柱惯量 |
| design.tendon_routing_radius_m | m | [0.002, 0.045]，且不超过体半径的 0.9 | 全部绳路与长度映射 |
| physics.line_density_kg_m | kg/m | [0.02, 3] | m=线密度×节长；不从体半径擅自推密度 |
| physics.root_ei_nm2 | N·m² | [0.0001, 1] | 根部等效弯曲刚度 |
| physics.tip_ei_ratio | 1 | [0.1, 3] | 沿网格线性刚度比例；不是变截面新模型 |
| physics.bending_viscosity_nm2_s | N·m²·s | [0.000001, 0.05] | 每节阻尼 |
| physics.natural_total_angle_rad | rad | [-π, π] | 每节自然 y 角为 -总角/8 |
| physics.tendon_servo_kp_n_per_m | N/m | [100, 20000] | 长度伺服增益 |
| physics.tendon_force_limit_n | N | [5, 80] | 拉力上限 |
| controller.bend_y_rad / bend_z_rad | rad | 各 [-π, π]，向量范数≤π | PCC 绳长指令；MATLAB 要求 bend_y=0 |
| controller.bias_fraction | 1 | [-0.02, 0.05] | 基于 L 的指令偏置 |
| controller.gain_rad2_per_m2 | rad²/m² | [0, 100]，C2 时>0 | 已有 C2 反馈增益；C1 不使用 |
| controller.max_bend_update_rad | rad | (0, 0.2] | C2 单次更新限制 |
| controller.rate_limit_ref_per_s | 1/s | (0, 2] | 已有控制器的归一化指令变化率 |

以上是构建器能力范围；每个会话必须在 `policy.editable` 显式选择字段及更窄区间，不能把整包任意放行。示例选择其中 11 个参数，见 [CHANGES 与 session_input](../examples/platform_domain_example.py)。控制模式 C1/C2、update_every_steps 在会话控制配置中冻结，不作为本轮 changes 的离散搜索维度。

本轮固定 **sections=1、segments=8、tendon_count=4**。section 是机器人结构段，segments 是数值离散节数。既有 V2 编译器固定八节，部分内部路径能处理其他腱数，但本轮没有开放或验证离散结构搜索。任务、环境、初态定义、评价标准、积分步长及求解器配置均保持会话定义；等效物理参数不表示真实材料已标定。

## 统一信号与相位

映射源码为 [signals.py](../extensions/robot_domain/signals.py)，数据仍来自原 trajectory.json.gz。常规实体名按实际 IR 展开：`joint_i_y/z`（MATLAB 只有 y）、`tendon_i`、`segment_i`，不固定数组宽度。后端目录的 signal_templates 声明展开规则，signal_specs 保留当前任务所需的 tip 完整规格；扩展新任务观测时仍需补充精确规格。

| 统一名称 | 实体／维度 | 单位／坐标 | 数据和限制 |
| --- | --- | --- | --- |
| tip_position | tip／3 | m／world | 原 tip_m |
| joint_position、joint_velocity | 每个关节／1 | rad、rad/s／joint_local | 原 qpos_rad、qvel_rad_s |
| tendon_length、tendon_command | 每根腱／1 | m／actuator | 原求解器绳长及指令 |
| actuator_force、tendon_tension | 每根腱／1 | N／actuator | 前者负值表示拉；后者=-前者，正值张力，**不是接触力** |
| contact_count | contact／1 | count／world | MATLAB 为正近似法向力的节数；MuJoCo 为求解器接触点数，两者含义不同 |
| actuator_torque | 每个关节／1 | N·m／joint_local | 原广义执行器力 |
| passive_torque、constraint_torque | MuJoCo 每个关节／1 | N·m／joint_local | 约束合力矩不等于某个物体接触力 |
| contact_normal_force、contact_tangent_force | MuJoCo 单次接触点／1、2 | N／contact_local | 原接触局部坐标；正法向力表示压缩 |
| contact_position、contact_gap | MuJoCo 单次接触点／3、1 | m／world | 原接触点位置及间隙 |
| tendon_demand、tendon_velocity | MATLAB 每根腱／1 | N、m/s／actuator | 原未截断需求与路径速度 |
| floor_gap、contact_normal_approx | MATLAB 每节／1 | m／world、N／world_z | 原单侧地面近似；正法向力表示向上压缩，不是 MuJoCo 接触模型 |
| spring_torque、damping_torque、contact_torque_approx | MATLAB 每个关节／1 | N·m／joint_local | 原弹簧、阻尼及近似接触广义力 |

MuJoCo 状态为 `post_step`，使用 time_s；绳长、指令、力、接触及力矩为 `pre_step_solver`，使用 solver_time_s，不能挪到步后时间。MATLAB 状态和力均在同一保存输出时刻求值，标为 `sampled_state`；不是 ode15s 内部步。原始求解器字段、内部步日志和全部导出继续保存。

接触点不能跨帧假定身份稳定，因此 MuJoCo 每个接触记录使用 `contact_sample_i_point_j` 的稀疏单点信号，直接对应原始 rows[i].contacts[j]，几何对名称在该原始记录中。无接触时不产生该点信号；不存在的字段不补零。`signals.read@1.0.0` 接受 result、name、可选 entity/phase；多匹配报 SIGNAL_SELECTION_REQUIRED，缺失返回 missing_data。旧 diagnostics.sample_exceeds 遇到同名多实体也明确拒绝，不再默选第一项。

## 平台引用 → 已有保存数据工具

| 推荐平台调用 | 旧兼容路径入口 | 行为 |
| --- | --- | --- |
| diagnostics.saved_trajectory@2.0.0 | 同名 1.1.0；tools.public_services.saved_diagnosis | 同一实体／时间窗口统计与既有规则 |
| diagnostics.signal_rule@2.0.0 | 同名 1.1.0；tools.diagnostic_rules.run_saved_rule | 原 contact_presence@1.0.0 规则 |
| visualization.saved_replay@1.0.0 | tools.observation_tools.load_observation；NativeReplay／MATLAB saved Figure | 生成已有 observation_v1 供回放；该公共操作不开窗、不启动引擎 |
| visualization.render_simulation_video@2.0.0 | 同名 1.2.0；tools.simulation_video | 同一桥接后调用原有进程隔离视频执行器；本輪未编码验证 |

新输入为 `{result: EvidenceRef, execution_id: 所选仿真调用}`，其余选项按对应 Schema。旧版本 result_ref 仍为已登记路径，未静默改义；名称存在多个版本时，新会话须用 `policy.tool_bindings` 明确选择，旧 allowed_tools 不能替代版本选择。

共用 [saved.restore](../extensions/robot_domain/saved.py) 根据 result_executions 找到所选调用和原始执行，再从原始 simulation 事件定位匹配 ExportBundle，按内容摘要恢复该工具调用目录中的原文件布局。旧工具需要的路径登记只是本次适配器内存映射，不是第二套证据账本；调用方不必 export、搬运或手工登记。多个来源共享内容时必须给 execution_id，缺少可靠原始来源或原始文件包则报错，不猜来源。

输出 SavedProduct 包含 source、source_execution_id、original_execution_id、candidate_id、bundle、report 和 files（文件名→EvidenceRef）。report 是诊断／规则／回放报告的不可变引用，新视频文件也回存原内容库，saved_data 事件引用源结果、原包与候选输入。原始 result.json 不补写候选身份；身份来自封存来源记录，旧回放读取缺失 candidate_id 时保持为空，由平台派生报告补充可靠关联。

所有保存数据操作均为零动力学、零重新评分。旧诊断阈值和算法保持；其旧报告字段命名保留，解释 MATLAB 报告时以原轨迹时刻和本文 sampled_state 说明为准。本轮没有打开回放窗口或编码视频；已验证两种后端 observation 数据准备。

## 领域原子与固定编排边界

生成目录使用既有 `capabilities.category/role` 元数据；下面列出内部复用入口，不另建注册表或把每个内部函数包成 LLM 工具。所有路径均相对仓库根目录。

| 分类 | 实际入口／类型／状态 | 输入 → 输出与语义 | 适用范围与旧入口映射 |
| --- | --- | --- | --- |
| robot_design 机器人设计 | candidate.rod_design：已接通候选适配；tools.design_compiler.build_robot_ir：内部库 | DesignSpec+changes → 有效设计／RobotIR，SI、固定基座+x、yz 绳路 | 本轮等效杆单 section；原 V1 编译及旧候选入口保留 |
| scene_assembly 场景装配 | tools.mujoco_tools.compile_mujoco、tools.task_context.TaskContext：内部编译／上下文；initialize.legacy_zero：初始化适配 | RobotIR+EnvironmentSpec+任务 → XML／初态；world、m、m/s² | 原 reach 环境的机器人挂载和地面映射；不是通用场景编辑器 |
| mathematical_models 数学模型 | analysis.pcc_jacobian／pcc_condition／pcc_tolerance：公共工具；tools.pcc_math、model_provider：内部库 | 长度／弯曲角／误差 → 末端、雅可比、条件数、传播量；m、rad、m/rad，基座+x | 单 section PCC 几何，不含重力／接触动力学；旧 services 入口映射同实现 |
| mathematical_models 已有力学 | tools.mechanics_tools.MechanicsTools.solve、matlab/closeout_mechanics.m：内部独立分析／兼容执行 | AnalysisSpec／已导出参数 → 静态、动态或稳定性分析，按旧契约 SI 和模型范围 | 保留旧分析预算／模型定义；未新包装为平台求解工具，也未在本轮重跑 |
| control 控制 | controller.legacy_length：参数适配；controllers/registry.py、open_loop_length.py、pcc_tip_feedback.py：内部生命周期 | ExplorationControl+IR+观测 → 每腱长度指令 m；按冻结周期更新 | C1 固定／C2 反馈，原控制实现保留；后端执行时间步，LLM 不充当控制器 |
| simulation 仿真 | simulation.run：公共完整操作；backend.mujoco／matlab：适配；tools.reach_dynamics.DynamicsBackends：内部执行器 | 候选+任务／控制 → BackendResult、Signal、原始文件包 | 一次 MATLAB 平面或 MuJoCo 分段仿真；旧 dynamics.simulate_candidate 是旧账本固定编排 |
| signals_diagnostics 信号诊断 | signals.read、两项 diagnostics@2.0、visualization.saved_replay／render_simulation_video：公共保存数据工具 | EvidenceRef+执行身份／实体／窗口 → 选择信号或 SavedProduct | 时间相位见上表；内部 trajectory_diagnosis／diagnostic_rules／native_replay 复用，无新动力学 |
| evaluation_comparison 评价比较 | evaluation.run：公共工具；evaluate.reach：评价适配；tools.platform_search.rank、dynamic_comparison：内部比较 | 保存结果+固定任务 → EvaluationResult／可比较排序；距离 m | 当前到达距离与原阈值；比较检查任务实例／后端／模型身份。当前 score 按有效单目标指标排序，不承诺通用约束优先策略 |
| parameter_search 参数搜索 | search.scalar_sequence、search.stateful：可执行参考；tools.platform_search.run_search：公共 CLI 的 ask/tell 编排 | 参数序列+反馈+检查点 → 候选和试验列表；单位继承设计空间 | 两个参考器是序列提案，不是通用优化器；无新算法 |
| parameter_search 旧优化复用 | tools.optimization_interfaces.ParameterSpace/coordinate_proposal、search_runtime.search：内部库；DynamicCampaign.optimize：旧固定编排 | 有界／可对数参数空间 → 正负坐标试探、无改进缩步、保存状态 | MATLAB tdcr_search_step 是有界坐标模式局部搜索，不是梯度算法／全局最优；旧 optimize_matlab 保留旧授权账本，未整体迁移 |
| platform_services 平台服务 | evidence、memory、skills、workers、session、模型适配／策略 | 引用／状态／工作单 → 分页、检索、回执、会话状态 | 与机器人领域原子分开；Host 管授权／幂等／预留／证据，不另建收费系统 |
| 教学示例 | extensions/reference 的离散信号、extensions/convergence、analysis.force_peak | 合成状态或数值输入 → 接口示例输出 | learning_peak 保留；参考测试通过不等于真实机器人能力 |
| 待实现 | backend.genesis、扩展模板 *_skeleton.py | 仅声明或协议骨架 | IMPLEMENTATION_REQUIRED 不等于环境 DEPENDENCY_MISSING；不借本轮接入新求解器 |

完整编排（旧 campaign／workbench、当前 run_search、此处示例）与可复用原子分别列出，旧入口继续按原授权和账本工作。内部库不因列入目录就自动获得公共调用权限。

## 本轮验证与剩余边界

执行 `conda run -n softagent python -m unittest tests.test_platform_domain -v`：**3 项通过，1.239 s，0 失败／跳过**。范围仅为派生量重建／冻结范围、保存信号实体和相位、档案证据桥接／来源歧义／旧诊断调用；复用历史短轨迹只读数据，没有重跑历史实验。随后只读核对本轮两次真实编译输出与桥接报告。

代表记录位于 `runs/platform_domain_integration/20260917/{mujoco,matlab}_record.json`，可搬运摘要见 [platform_domain.json](evidence/platform_domain.json)。同一个非基线候选：L=0.32 m、体半径=0.019 m、绳路半径=0.016 m；每节质量=0.044 kg、y 惯量=9.8376667e-6 kg·m²、刚度=0.105 N·m/rad、阻尼=0.1 N·m·s/rad、伺服增益=1200 N/m、拉力限幅=22 N；与实际 shared_input／IR 摘要一致。

| 实际调用 | 结果 |
| --- | --- |
| MuJoCo | **1 次**，0.08 s／40 步后状态采样；7 次平台工具调用，诊断 20 个实体统计，接触规则 EVENTS_FOUND，回放数据 40 帧 |
| MATLAB | **1 次**，0.08 s／41 个输出采样（不是 41 个内部步）；7 次平台工具调用，诊断 12 个实体统计，接触规则 EVENTS_FOUND，回放数据 41 帧 |
| 评价 | 两者均 validity=valid、task_success=false；未改阈值、不要求优于历史结果 |
| 额外动力学／真实 LLM／视频编码／开窗 | **0**；测试也没有新求解，账本总 backend_solves=2 |

本轮代码不表示物理标定、跨后端动力学等价或结构最优；MuJoCo 接触点与 MATLAB 近似节接触不可直接比数量。视频适配已共用桥接和原执行器，但未运行编码／GUI；完整 C2 参数变化和所有边界组合未逐一物理试验，本轮代表例为 C1。不扩大参数扫描。

简短待办：通用统计可复用现有保存窗口统计但尚无任意信号统计工具；通用场景装配需在已有 EnvironmentSpec／XML 编译器上明确对象与挂载语义；完整质量矩阵／科氏项接口尚未公开；约束优先排序、多目标搜索需另定契约和反馈适配。多 section、离散网格优化、其他腱数、新执行器和 Genesis 均未在本轮开放。
