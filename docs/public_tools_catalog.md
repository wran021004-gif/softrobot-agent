# 统一工具清单（生成视图）

由 `python examples/public_tools.py catalog --markdown --output docs/public_tools_catalog.md` 生成。
版本 1.0 / 工具版本 1.0.0。输入/输出 schema、依赖和完整约束请读取 JSON catalog；[接口规范](public_tools.md)。
所有可调用项仍受绑定会话的权限、证据、预算和后端依赖检查。

| 公共身份 | 权限 | 用途 | 实现入口 |
| --- | --- | --- | --- |
| workbench.inspect_task | read_inputs | 解析冻结合同、设计语法及工具适用性 | tools.workbench_actions:execute |
| workbench.analyze_design | analysis | 现有 PCC 直态局部雅可比；不判断任务成绩 | tools.workbench_actions:execute |
| workbench.evaluate_design | simulate | 原 Harness 完整评价；或请求创建时登记的封存历史运行回放（零后端，单独标明历史成绩）；整次候选为恢复边界 | tools.workbench_actions:execute |
| workbench.diagnose | read_evidence | 读取原评价和诊断证据；因果归因保持 UNKNOWN | tools.workbench_actions:execute |
| workbench.observe | derived_artifacts | 复用 ObservationViewer；保存数据回放，零动力学调用 | tools.workbench_actions:execute |
| workbench.read_evidence | read_evidence | 按 evidence_id 和 JSON Pointer 读取字段或有限片段；catalog:cNNN 的 /entries 为候选文件目录；返回 cite_as 可直接引用 | tools.workbench_actions:execute |
| workbench.create_candidate | candidate_design | 只修改权威 envelope 允许的参数；必须引用 parent_id 的本轮评价证据，不能提前生成序列 | tools.workbench_actions:execute |
| workbench.check_candidate | analysis | 检查指定候选的语法、范围与关系约束，生成独立 IR 和 PCC 局部分析 | tools.workbench_actions:execute |
| workbench.evaluate_candidate | simulate | 指定候选经原 Harness 的 MATLAB M0/M1/形状、C1、编译、MuJoCo 和冻结评价；成功与失败均返回真实数据 | tools.workbench_actions:execute |
| workbench.compare_candidates | read_evidence | 仅比较指定候选已有的本轮评价；任务状态与误差来自既有评价程序 | tools.workbench_actions:execute |
| workbench.observe_candidate | derived_artifacts | 用原观察器从指定候选保存数据生成动画和曲线，不重新仿真 | tools.workbench_actions:execute |
| dynamics.analyze_pcc | analysis | Task-independent analytic PCC tip/Jacobian for explicit length and bend; local geometry only, zero backend solves, no task score. | tools.dynamic_campaign:DynamicCampaign.dispatch |
| dynamics.create_candidate | candidate_design | Branch any registered candidate, changing design, equivalent physics or control; cite recorded evidence. | tools.dynamic_campaign:DynamicCampaign.dispatch |
| dynamics.simulate_candidate | simulate | Run only the selected backend. MATLAB screening does not set canonical reach success. One rollout charged even on failure. | tools.dynamic_campaign:DynamicCampaign.dispatch |
| dynamics.evaluate_candidate | simulate | Compatibility: evaluate candidate in MuJoCo with its own controller, no bundled MATLAB calls. | tools.dynamic_campaign:DynamicCampaign.dispatch |
| dynamics.optimize_matlab | analysis | MATLAB bounded local coordinate search, checkpoint every trial, one dynamic budget unit per actual rollout. Resume identical search_id. Choose a small evidence-based variable subset and a bounded batch. | tools.dynamic_campaign:DynamicCampaign.dispatch |
| dynamics.diagnose_trajectory | read_evidence | Query exact entity and time from saved trajectory. Force and state have distinct time phases. Returns sampled facts, events and evidence refs. | tools.dynamic_campaign:DynamicCampaign.dispatch |
| dynamics.compare_candidates | read_evidence | Paged design/control/physics/backend comparison. Unevaluated backends remain NOT_RUN. | tools.dynamic_campaign:DynamicCampaign.dispatch |
| dynamics.observe_candidate | derived_artifacts | Render saved MATLAB or MuJoCo coordinates, curves and event list; zero backend solves. | tools.dynamic_campaign:DynamicCampaign.dispatch |
| dynamics.render_simulation_video | derived_artifacts | On demand: render a registered saved result with its native backend to an MP4 file reference, without solving or scoring. Use reason to state a specific visual inspection question. Optional time interval defaults to the saved trajectory. A text model receiving the video reference has NOT seen or visually understood the frames. | tools.dynamic_campaign:DynamicCampaign.dispatch |
| dynamics.read_evidence | read_evidence | Read registered JSON with pointer, offset, limit and max_bytes. Follow next_read; oversized items return child pointers and resume_container. Array offsets are original source indices. | tools.dynamic_campaign:DynamicCampaign.dispatch |
| dynamics.record_verified_diagnosis | read_evidence | Record your concrete diagnostic statement with exact machine-checkable entity, time interval, numeric field and value from a diagnosis record. | tools.dynamic_campaign:DynamicCampaign.dispatch |
| dynamics.stop_design | read_evidence | Stop with cited results and limitations; distinguish workflow, numerical completion, MATLAB prediction and canonical MuJoCo success. | tools.dynamic_campaign:DynamicCampaign.dispatch |
| workbench.stop_design | session_control | Record a cited terminal decision with reason; no numerical execution. | tools.workbench:Workbench.submit |
| workbench.capability_missing | session_control | Record a cited terminal decision with reason; no numerical execution. | tools.workbench:Workbench.submit |
| analysis.pcc_jacobian | analysis | Analytic single-section, inextensible PCC tip and local Jacobian. Origin at base, +x straight, bending in yz. No gravity, contact, elasticity, dynamics, calibration or task scoring; norm(bend_rad)<=pi. Outputs m and m/rad. | tools.public_services:pcc_jacobian |
| evidence.read_json | read_evidence | Hash-verified registered JSON, bounded JSON Pointer pages; never simulate or score. | tools.public_services:read_json |
| diagnostics.saved_trajectory | read_evidence | Query registered saved trajectory by entity and physical time. Default interval comes from saved state/solver samples. Existing diagnostic rules remain model-specific; no simulation or scoring. | tools.public_services:saved_diagnosis |
| visualization.render_simulation_video | derived_artifacts | On demand: render a registered saved result with its native backend to an MP4 file reference, without solving or scoring. Use reason to state a specific visual inspection question. Optional time interval defaults to the saved trajectory. A text model receiving the video reference has NOT seen or visually understood the frames. | tools.simulation_video:render_simulation_video |

## 库能力（不授予公共调用权限）

IMPLEMENTED 表示已声明实现；AST 检查只证明声明入口存在，未启动后端。PLANNED 不可执行。
库名可与公共名称相似，但参数和调用层级不同；不得自动互换。

| 库身份 | 声明状态 | 源码核对 | 既有入口 |
| --- | --- | --- | --- |
| library.spec.load_task | IMPLEMENTED | ENTRYPOINT_SOURCE_PRESENT_NOT_RUNTIME_PROBED | tools.spec_tools:load_task |
| library.spec.validate_task_spec | IMPLEMENTED | ENTRYPOINT_SOURCE_PRESENT_NOT_RUNTIME_PROBED | tools.spec_tools:validate_task_spec |
| library.spec.validate_environment | IMPLEMENTED | ENTRYPOINT_SOURCE_PRESENT_NOT_RUNTIME_PROBED | tools.spec_tools:validate_environment |
| library.spec.validate_design | IMPLEMENTED | ENTRYPOINT_SOURCE_PRESENT_NOT_RUNTIME_PROBED | tools.spec_tools:validate_design |
| library.spec.build_robot_ir | IMPLEMENTED | ENTRYPOINT_SOURCE_PRESENT_NOT_RUNTIME_PROBED | tools.design_compiler:build_robot_ir |
| library.model.analyze_workspace | IMPLEMENTED | ENTRYPOINT_SOURCE_PRESENT_NOT_RUNTIME_PROBED | tools.matlab_tools:MatlabTools.analyze_workspace |
| library.model.plan_pcc_reach | IMPLEMENTED | ENTRYPOINT_SOURCE_PRESENT_NOT_RUNTIME_PROBED | tools.matlab_tools:MatlabTools.plan_pcc_reach |
| library.model.analyze_clearance | IMPLEMENTED | ENTRYPOINT_SOURCE_PRESENT_NOT_RUNTIME_PROBED | tools.matlab_tools:MatlabTools.analyze_clearance |
| library.model.analyze_actuation | IMPLEMENTED | ENTRYPOINT_SOURCE_PRESENT_NOT_RUNTIME_PROBED | tools.actuation_tools:analyze_actuation |
| library.model.pcc_centerline | IMPLEMENTED | ENTRYPOINT_SOURCE_PRESENT_NOT_RUNTIME_PROBED | tools.matlab_tools:MatlabTools.pcc_centerline |
| library.model.analyze_stiffness | PLANNED | NO_IMPLEMENTATION_DECLARED | — |
| library.model.solve_equilibrium | PLANNED | NO_IMPLEMENTATION_DECLARED | — |
| library.model.analyze_dynamics | PLANNED | NO_IMPLEMENTATION_DECLARED | — |
| library.model.simulate_reduced_dynamics | PLANNED | NO_IMPLEMENTATION_DECLARED | — |
| library.model.pcc_sensitivity | IMPLEMENTED | ENTRYPOINT_SOURCE_PRESENT_NOT_RUNTIME_PROBED | tools.pcc_math:pcc_sensitivity |
| library.optimization.optimize_design | IMPLEMENTED | ENTRYPOINT_SOURCE_PRESENT_NOT_RUNTIME_PROBED | tools.experiment_tools:optimize_design |
| library.optimization.fit_model_parameters | PLANNED | NO_IMPLEMENTATION_DECLARED | — |
| library.control.plan_open_loop | IMPLEMENTED | ENTRYPOINT_SOURCE_PRESENT_NOT_RUNTIME_PROBED | controllers.open_loop_length:plan_open_loop |
| library.control.synthesize_feedback | IMPLEMENTED | ENTRYPOINT_SOURCE_PRESENT_NOT_RUNTIME_PROBED | controllers.pcc_tip_feedback:synthesize_feedback |
| library.control.synthesize_model_controller | PLANNED | NO_IMPLEMENTATION_DECLARED | — |
| library.control.optimize_controller | PLANNED | NO_IMPLEMENTATION_DECLARED | — |
| library.mujoco.compile_mujoco | IMPLEMENTED | ENTRYPOINT_SOURCE_PRESENT_NOT_RUNTIME_PROBED | tools.mujoco_tools:compile_mujoco |
| library.mujoco.validate_task | IMPLEMENTED | ENTRYPOINT_SOURCE_PRESENT_NOT_RUNTIME_PROBED | tools.mujoco_tools:validate_task |
| library.mujoco.run_task | IMPLEMENTED | ENTRYPOINT_SOURCE_PRESENT_NOT_RUNTIME_PROBED | tools.mujoco_tools:run_task |
| library.mujoco.validate_physics | PLANNED | NO_IMPLEMENTATION_DECLARED | — |
| library.mujoco.evaluate_metrics | PLANNED | NO_IMPLEMENTATION_DECLARED | — |
| library.diagnostics.compare_shape_model_sim | IMPLEMENTED | ENTRYPOINT_SOURCE_PRESENT_NOT_RUNTIME_PROBED | tools.shape_tools:compare_shape_model_sim |
| library.diagnostics.compare_model_sim | IMPLEMENTED | ENTRYPOINT_SOURCE_PRESENT_NOT_RUNTIME_PROBED | tools.diagnostic_tools:compare_model_sim |
| library.diagnostics.check_actuator_limits | IMPLEMENTED | ENTRYPOINT_SOURCE_PRESENT_NOT_RUNTIME_PROBED | tools.diagnostic_tools:check_actuator_limits |
| library.diagnostics.check_tendon_tracking | IMPLEMENTED | ENTRYPOINT_SOURCE_PRESENT_NOT_RUNTIME_PROBED | tools.diagnostic_tools:check_tendon_tracking |
| library.diagnostics.check_tendon_slack | PLANNED | NO_IMPLEMENTATION_DECLARED | — |
| library.diagnostics.check_collision | IMPLEMENTED | ENTRYPOINT_SOURCE_PRESENT_NOT_RUNTIME_PROBED | tools.diagnostic_tools:check_collision |
| library.diagnostics.inspect_numerics | IMPLEMENTED | ENTRYPOINT_SOURCE_PRESENT_NOT_RUNTIME_PROBED | tools.diagnostic_tools:inspect_numerics |
| library.diagnostics.run_parameter_sensitivity | IMPLEMENTED | ENTRYPOINT_SOURCE_PRESENT_NOT_RUNTIME_PROBED | tools.experiment_tools:run_parameter_sensitivity |
| library.artifacts.create_run | IMPLEMENTED | ENTRYPOINT_SOURCE_PRESENT_NOT_RUNTIME_PROBED | tools.artifact_tools:create_run |
| library.artifacts.save_tool_result | IMPLEMENTED | ENTRYPOINT_SOURCE_PRESENT_NOT_RUNTIME_PROBED | tools.artifact_tools:save_tool_result |
| library.artifacts.finalize_run | IMPLEMENTED | ENTRYPOINT_SOURCE_PRESENT_NOT_RUNTIME_PROBED | tools.artifact_tools:finalize_run |
| library.learning.build_mdp | PLANNED | NO_IMPLEMENTATION_DECLARED | — |
| library.learning.train_policy | PLANNED | NO_IMPLEMENTATION_DECLARED | — |
| library.learning.evaluate_policy | PLANNED | NO_IMPLEMENTATION_DECLARED | — |
| library.closeout_analysis.closeout_mechanics_solve | IMPLEMENTED | ENTRYPOINT_SOURCE_PRESENT_NOT_RUNTIME_PROBED | tools.mechanics_tools:MechanicsTools.solve |
| library.closeout_analysis.export_compiled_analysis_parameters | IMPLEMENTED | ENTRYPOINT_SOURCE_PRESENT_NOT_RUNTIME_PROBED | tools.mechanics_tools:export_parameters |
| library.closeout_analysis.resolve_closeout_analysis | IMPLEMENTED | ENTRYPOINT_SOURCE_PRESENT_NOT_RUNTIME_PROBED | tools.mechanics_tools:resolve_analysis_capability |
| library.workbench.query_tools | IMPLEMENTED | ENTRYPOINT_SOURCE_PRESENT_NOT_RUNTIME_PROBED | capabilities.registry:query_tools |
| library.workbench.load_observation | IMPLEMENTED | ENTRYPOINT_SOURCE_PRESENT_NOT_RUNTIME_PROBED | tools.observation_tools:load_observation |
| library.workbench.compare_dynamic_observations | IMPLEMENTED | ENTRYPOINT_SOURCE_PRESENT_NOT_RUNTIME_PROBED | tools.observation_tools:comparison_eligibility |
| library.workbench.generate_task_instance | IMPLEMENTED | ENTRYPOINT_SOURCE_PRESENT_NOT_RUNTIME_PROBED | tools.task_family_tools:generate_task_instance |
| library.workbench.evaluate_task_instance | IMPLEMENTED | ENTRYPOINT_SOURCE_PRESENT_NOT_RUNTIME_PROBED | tools.task_family_tools:evaluate_task_instance |
| library.workbench.describe_task_families | IMPLEMENTED | ENTRYPOINT_SOURCE_PRESENT_NOT_RUNTIME_PROBED | tools.task_family_tools:describe_tasks |
| library.workbench.observe_saved_motion | IMPLEMENTED | ENTRYPOINT_SOURCE_PRESENT_NOT_RUNTIME_PROBED | tools.observation_viewer:ObservationViewer |
| library.workbench.round4_length_campaign | IMPLEMENTED | ENTRYPOINT_SOURCE_PRESENT_NOT_RUNTIME_PROBED | tools.round4_campaign:run_campaign |
| library.workbench.round4_diagnostic_solve | IMPLEMENTED | ENTRYPOINT_SOURCE_PRESENT_NOT_RUNTIME_PROBED | tools.round4_validation:solve_diagnostic |

Bundle 别名：`{'matlab_analysis': 'model'}`。

未实现的公共扩展：通用优化器/评价器插件、模型控制器适配和宿主视觉理解；参见接口规范中的路线。
