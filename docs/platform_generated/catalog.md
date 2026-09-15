# 公共能力目录（生成）

由 `python examples/export_platform_contracts.py` 生成；不是授权清单。

| 身份 | 类型 | 版本 | 实现存在 | 说明 |
| --- | --- | --- | --- | --- |
| analysis.pcc_condition | tool | 1.1.0 | True | Singular values/rank of the local PCC tip Jacobian; geometric conditioning, no controllability or task claim. |
| analysis.pcc_jacobian | tool | 1.1.0 | True | Single section inextensible PCC tip/Jacobian, m and m/rad, base +x, yz bending; norm(bend)<=pi. Geometry only. |
| analysis.pcc_tolerance | tool | 1.0.0 | True | Propagate independent length/bend standard deviations to first-order tip covariance, principal error directions and ranked tolerance contributions. Geometric approximation, no task assessment. |
| analysis.vector_norm | tool | 1.0.0 | True | 带单位与坐标的向量范数；接入不改核心循环 |
| backend.genesis | backend | 1.0.0 | False | 待实现：必须检查目标版本并完成模型、信号与执行通道适配 |
| backend.matlab | backend | 1.0.0 | True | 保留 MATLAB 平面动力学一次性求解适配 |
| backend.mujoco | backend | 1.0.0 | True | 保留 MuJoCo 一次性求解适配 |
| backend.reference | backend | 1.0.0 | True | 廉价确定性参考后端，非真实物理、非 Genesis |
| controller.legacy_length | controller | 1.0.0 | True | 旧 C1/C2 参数与数值控制适配 |
| controller.length_reference | controller | 1.0.0 | True | 参考长度指令生命周期 |
| diagnostics.sample_exceeds | tool | 1.0.0 | True | 基于保存信号的带版本阈值诊断 |
| diagnostics.saved_trajectory | tool | 1.1.0 | True | Legacy reach signal rules; saved physical time, no simulation or scoring. |
| diagnostics.signal_rule | tool | 1.1.0 | True | Run a versioned saved-signal rule; distinguish missing, no event, inapplicable and failure. |
| evaluate.hold | evaluator | 1.0.0 | True | 评价窗口内最大与 RMS 偏差 |
| evaluate.reach | evaluator | 1.0.0 | True | 末端距离评价，阈值来自任务 |
| evaluation.run | tool | 1.0.0 | True | 显式评价保存结果并产生新身份 |
| evidence.read | tool | 1.0.0 | True | 只读不可变证据及分页 |
| evidence.read_json | tool | 1.1.0 | True | Read hash-verified saved JSON using bounded JSON Pointer pages. |
| initialize.legacy_zero | initializer | 1.0.0 | True | 原编译初态和零速度 |
| initialize.length | initializer | 1.0.0 | True | 显式种子的长度初始化 |
| memory.save | tool | 1.0.0 | True | 保存有来源的笔记或观测记录 |
| memory.search | tool | 1.0.0 | True | 检索跨运行记录并校验来源 |
| search.scalar_sequence | search | 1.0.0 | True | 确定性候选序列参考搜索器；算法拥有状态 |
| session.control | tool | 1.0.0 | True | 停止、暂停、缺少信息或能力 |
| simulation.run | tool | 1.0.0 | True | 执行当前冻结任务与候选 |
| skills.propose | tool | 1.0.0 | True | 提案进入开发候选库，无人工批准 |
| skills.search | tool | 1.0.0 | True | 读取现有技能生命周期中的适用策略 |
| skills.validate | tool | 1.0.0 | True | 登记与证据相符的验证记录 |
| task.reach | task | 1.0.0 | True | 已有到达语义的开发任务 |
| task.signal_hold | task | 1.0.0 | True | 离散长度信号保持开发示例；无末端目标点 |
| visualization.render_simulation_video | tool | 1.2.0 | True | Render saved trajectory; native cache and bounded encoder, zero solves. |
| worker.signal | worker | 1.0.0 | True | 读取同一固定证据的确定性本地工作者 |
| workers.accept | tool | 1.0.0 | True | 协调者检查并接收独立输出 |
| workers.cancel | tool | 1.0.0 | True | 请求取消本地工作者 |
| workers.status | tool | 1.0.0 | True | 查询工作者状态 |
| workers.submit | tool | 1.0.0 | True | 启动有边界的本地工作者 |
