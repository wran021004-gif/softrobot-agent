# 公共能力目录（生成）

由 `python examples/export_platform_contracts.py` 生成；不是授权清单。

分类、内部库和兼容入口说明见 [领域能力边界](../platform_domain.md)。存在绑定不代表物理验证。

| 身份 | 分类 | 角色 | 类型 | 版本 | 实现存在 | 绑定入口 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| analysis.force_peak | mathematical_models | teaching_example | tool | 1.0.0 | True | extensions.learning_peak.implementation:calculate | 计算力序列的最大绝对值；输入输出单位为牛顿，不判断机器人任务成功。 |
| analysis.pcc_condition | mathematical_models | public_tool | tool | 1.1.0 | True | tools.math_extensions:pcc_condition | Singular values/rank of the local PCC tip Jacobian; geometric conditioning, no controllability or task claim. |
| analysis.pcc_jacobian | mathematical_models | public_tool | tool | 1.1.0 | True | tools.public_services:pcc_jacobian | Single section inextensible PCC tip/Jacobian, m and m/rad, base +x, yz bending; norm(bend)<=pi. Geometry only. |
| analysis.pcc_tolerance | mathematical_models | public_tool | tool | 1.0.0 | True | tools.pcc_tolerance:analyze | Propagate independent length/bend standard deviations to first-order tip covariance, principal error directions and ranked tolerance contributions. Geometric approximation, no task assessment. |
| analysis.vector_norm | mathematical_models | public_tool | tool | 1.0.0 | True | extensions.reference.implementation:vector_norm | 带单位与坐标的向量范数；接入不改核心循环 |
| analysis.versioned_value | mathematical_models | teaching_example | tool | 1.0.0 | True | extensions.convergence.implementation:value_v1 | Independent offline development example; no physical calibration |
| analysis.versioned_value | mathematical_models | teaching_example | tool | 2.0.0 | True | extensions.convergence.implementation:value_v2 | Independent offline development example; no physical calibration |
| backend.genesis | simulation | unimplemented | backend | 1.0.0 | False | 未实现 | 待实现：必须检查目标版本并完成模型、信号与执行通道适配 |
| backend.limited_synthetic | simulation | teaching_example | backend | 1.0.0 | True | extensions.convergence.implementation:LimitedBackend | Independent offline development example; no physical calibration |
| backend.math_planar | mathematical_models | adapter | backend | 1.0.0 | True | extensions.experiment_dynamics.backends:PlanarBackend | 原 MATLAB 平面 v1 算法，直接读取公共物理量，无 MuJoCo |
| backend.math_spatial | mathematical_models | adapter | backend | 1.0.0 | True | extensions.experiment_dynamics.backends:SpatialBackend | 独立三维 16 自由度耦合动力学；无 MuJoCo 依赖 |
| backend.matlab | simulation | adapter | backend | 1.0.0 | True | extensions.reference.legacy:MatlabBackend | 保留 MATLAB 平面动力学一次性求解适配 |
| backend.mujoco | simulation | adapter | backend | 1.0.0 | True | extensions.reference.legacy:MujocoBackend | 保留 MuJoCo 一次性求解适配 |
| backend.reference | simulation | adapter | backend | 1.0.0 | True | extensions.reference.implementation:ReferenceBackend | 廉价确定性参考后端，非真实物理、非 Genesis |
| backend.scene_mujoco | simulation | adapter | backend | 1.0.0 | True | extensions.experiment_dynamics.backends:MujocoBackend | 公共物理和统一场景映射到 MuJoCo |
| candidate.controller | robot_design | adapter | candidate_builder | 1.0.0 | True | tools.platform_candidates:apply_control | Apply existing typed controller parameters |
| candidate.rod_design | robot_design | adapter | candidate_builder | 1.0.0 | True | extensions.robot_domain.candidate:apply_design | 单 section / 八节等效杆：从冻结 DesignSpec 重编译派生量 |
| candidate.synthetic | robot_design | teaching_example | candidate_builder | 1.0.0 | True | extensions.convergence.implementation:apply_design | Independent offline development example; no physical calibration |
| controller.experiment_length | control | adapter | controller | 1.0.0 | True | extensions.experiment_dynamics.backends:LengthController | 复用 C1/C2；世界末端实时观测转换到安装坐标 |
| controller.legacy_length | control | adapter | controller | 1.0.0 | True | extensions.reference.legacy:LegacyController | 旧 C1/C2 参数与数值控制适配 |
| controller.length_reference | control | adapter | controller | 1.0.0 | True | extensions.reference.implementation:LengthController | 参考长度指令生命周期 |
| deepseek | platform_services | adapter | model_adapter | 1.0.0 | True | tools.platform_models:DeepSeekAdapter | Existing text/tool model service transport |
| diagnostics.sample_exceeds | signals_diagnostics | public_tool | tool | 1.0.0 | True | tools.platform_tools:diagnose | 基于保存信号的带版本阈值诊断 |
| diagnostics.sample_exceeds | signals_diagnostics | public_tool | tool | 1.1.0 | True | extensions.robot_domain.signals:sample_exceeds | 按名称/实体/相位选择保存标量并检查严格大于阈值；无新求解/评分 |
| diagnostics.saved_trajectory | signals_diagnostics | public_tool | tool | 1.1.0 | True | tools.public_services:saved_diagnosis | Legacy reach signal rules; saved physical time, no simulation or scoring. |
| diagnostics.saved_trajectory | signals_diagnostics | public_tool | tool | 2.0.0 | True | extensions.robot_domain.saved:diagnosis | 平台结果引用自动进入旧保存轨迹诊断；无新求解/评分 |
| diagnostics.signal_rule | signals_diagnostics | public_tool | tool | 1.1.0 | True | tools.diagnostic_rules:run_saved_rule | Run a versioned saved-signal rule; distinguish missing, no event, inapplicable and failure. |
| diagnostics.signal_rule | signals_diagnostics | public_tool | tool | 2.0.0 | True | extensions.robot_domain.saved:rule | 平台结果引用自动进入既有保存信号规则 |
| evaluate.hold | evaluation_comparison | adapter | evaluator | 1.0.0 | True | extensions.reference.implementation:evaluate_hold | 评价窗口内最大与 RMS 偏差 |
| evaluate.reach | evaluation_comparison | adapter | evaluator | 1.0.0 | True | extensions.reference.implementation:evaluate_reach | 末端距离评价，阈值来自任务 |
| evaluate.terminal | evaluation_comparison | teaching_example | evaluator | 1.0.0 | True | extensions.convergence.implementation:terminal_evaluate | Independent offline development example; no physical calibration |
| evaluation.run | evaluation_comparison | public_tool | tool | 1.0.0 | True | tools.platform_tools:evaluate | 显式评价保存结果并产生新身份 |
| evidence.read | platform_services | public_tool | tool | 1.0.0 | True | tools.platform_tools:read_evidence | 只读不可变证据及分页 |
| evidence.read_json | platform_services | public_tool | tool | 1.1.0 | True | tools.public_services:read_json | Read hash-verified saved JSON using bounded JSON Pointer pages. |
| initialize.experiment | scene_assembly | adapter | initializer | 1.0.0 | True | extensions.experiment_dynamics.scene:initialize | 显式八节 y/z 关节位置和速度；不随机改变初态 |
| initialize.legacy_zero | scene_assembly | adapter | initializer | 1.0.0 | True | extensions.reference.implementation:initialize_legacy | 原编译初态和零速度 |
| initialize.length | scene_assembly | adapter | initializer | 1.0.0 | True | extensions.reference.implementation:initialize | 显式种子的长度初始化 |
| memory.save | platform_services | public_tool | tool | 1.0.0 | True | tools.platform_tools:memory_save | 保存有来源的笔记或观测记录 |
| memory.search | platform_services | public_tool | tool | 1.0.0 | True | tools.platform_tools:memory_search | 检索跨运行记录并校验来源 |
| model.observing | platform_services | teaching_example | model_adapter | 1.0.0 | True | extensions.convergence.implementation:ObservingAdapter | Independent offline development example; no physical calibration |
| offline | platform_services | adapter | model_adapter | 1.0.0 | True | tools.platform_models:OfflineAdapter | Offline scripted compatibility fixture |
| search.scalar_sequence | parameter_search | adapter | search | 1.0.0 | True | extensions.reference.implementation:ScalarSequenceSearch | 确定性候选序列参考搜索器；算法拥有状态 |
| search.stateful | parameter_search | teaching_example | search | 1.0.0 | True | extensions.convergence.implementation:StatefulSearch | Independent offline development example; no physical calibration |
| session.control | platform_services | public_tool | tool | 1.0.0 | True | tools.platform_tools:stop | 停止、暂停、缺少信息或能力 |
| signals.read | signals_diagnostics | public_tool | tool | 1.0.0 | True | extensions.robot_domain.signals:read_signal | 按名称/实体/相位读取保存统一信号，歧义拒绝 |
| simulation.run | simulation | public_tool | tool | 1.0.0 | True | tools.platform_tools:simulate | 执行当前冻结任务与候选 |
| skills.propose | platform_services | public_tool | tool | 1.0.0 | True | tools.platform_tools:skills_propose | 提案进入开发候选库，无人工批准 |
| skills.search | platform_services | public_tool | tool | 1.0.0 | True | tools.platform_tools:skills_search | 读取现有技能生命周期中的适用策略 |
| skills.validate | platform_services | public_tool | tool | 1.0.0 | True | tools.platform_tools:skills_validate | 登记与证据相符的验证记录 |
| strategy.evidence | platform_services | teaching_example | strategy | 1.0.0 | True | extensions.convergence.implementation:EvidenceStrategy | Independent offline development example; no physical calibration |
| strategy.tool | platform_services | adapter | strategy | 1.0.0 | True | tools.platform_models:ToolStrategy | One typed tool request per decision |
| task.reach | evaluation_comparison | adapter | task | 1.0.0 | True | extensions.reference.implementation:reach_task | 已有到达语义的开发任务 |
| task.signal_hold | evaluation_comparison | adapter | task | 1.0.0 | True | extensions.reference.implementation:hold_task | 离散长度信号保持开发示例；无末端目标点 |
| task.terminal | evaluation_comparison | teaching_example | task | 1.0.0 | True | extensions.convergence.implementation:terminal_task | Independent offline development example; no physical calibration |
| visualization.render_simulation_video | signals_diagnostics | public_tool | tool | 1.2.0 | True | tools.simulation_video:_render_simulation_video | Render saved trajectory; native cache and bounded encoder, zero solves. |
| visualization.render_simulation_video | signals_diagnostics | public_tool | tool | 2.0.0 | True | extensions.robot_domain.saved:video | 同一证据桥接调用已有视频执行器；显式派生产物 |
| visualization.saved_replay | signals_diagnostics | public_tool | tool | 1.0.0 | True | extensions.robot_domain.saved:replay | 恢复原始包并准备已有回放 observation；不开窗口 |
| worker.inventory | platform_services | teaching_example | worker | 1.0.0 | True | extensions.convergence.implementation:diagnostic_worker | Independent offline development example; no physical calibration |
| worker.math | platform_services | teaching_example | worker | 1.0.0 | True | extensions.convergence.implementation:math_worker | Independent offline development example; no physical calibration |
| worker.signal | platform_services | adapter | worker | 2.0.0 | True | extensions.reference.workers:run_signal_worker | 读取同一固定证据的确定性本地工作者 |
| workers.accept | platform_services | public_tool | tool | 1.0.0 | True | tools.platform_tools:worker_accept | 协调者检查并接收独立输出 |
| workers.cancel | platform_services | public_tool | tool | 1.0.0 | True | tools.platform_tools:worker_cancel | 请求取消本地工作者 |
| workers.status | platform_services | public_tool | tool | 1.0.0 | True | tools.platform_tools:worker_status | 查询工作者状态 |
| workers.submit | platform_services | public_tool | tool | 1.0.0 | True | tools.platform_tools:worker_submit | 启动有边界的本地工作者 |
