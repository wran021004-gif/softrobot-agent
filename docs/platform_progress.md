# 统一开发平台实施记录

## 基线与保护

- 基线：`feat/round9-matlab-dynamics-design-loop@63ae9b5`；开始时工作区干净。
- 本地工作分支：`feat/unified-development-platform`；不自动提交、推送或合并。
- 环境：`softagent`，Python 3.11.16、Pydantic 2.13.5；MuJoCo 和 MATLAB Engine 包可发现，是否能实际启动另行验证。
- 历史任务、物理、指标、预算和运行记录保持原身份；新配置全部用于开发接口验收。

## 基线审计与本次处理

| 对象 | 审计状态 | 已有权威实现 | 本次处理 |
| --- | --- | --- | --- |
| 公共工具契约、发现、执行 | 部分完成 | schemas/public_tools.py、tools/tool_registry.py、public_catalog.py、public_gateway.py、public_services.py | 复用声明和执行器，增加平台宿主及统一请求身份 |
| 旧模型主循环与授权 | 已完成（历史任务范围） | dynamic_campaign.py、dynamic_actions.py、workbench.py、harness.py | 保留旧入口与原账本，不将其授权扩展给新项目 |
| 任务包 | 部分完成 | task_context.py、task_family_tools.py、schemas/task_family.py | 增加版本化负载、初始化／评价登记与三阶段检查 |
| 结构与物理 | 部分完成 | design_compiler.py、schemas/robot_ir.py、model_provider.py、reach_dynamics.py | 共同描述复用 IR；显式区分独立参数与依赖仿真器的历史导出 |
| 后端 | 部分完成 | reach_dynamics.DynamicsBackends | 新增能力注册、兼容预检、生命周期和确定性参考后端 |
| 控制器 | 部分完成 | controllers/registry.py、factories.py | 保留 C1/C2，增加扩展自己的参数／状态契约 |
| 评价与搜索 | 部分完成 | optimization_interfaces.py、evaluation_runtime.py、search_runtime.py | 新评价不要求末端误差；算法管理自身状态，驱动负责提交和恢复 |
| 观测、诊断 | 已完成（已有信号） | observation_contract.py、diagnostic_rules.py、trajectory_diagnosis.py | 复用保存数据规则，新增统一信号外层与参考规则 |
| 证据、事务与恢复 | 部分完成 | artifact_tools.py、trace_tools.py、state_io.py、dynamic_recovery.py | 复用摘要与历史只读；新增项目 SQLite 原子预留／事件／回执事务 |
| 跨运行记忆 | 缺失 | design_memory.py 仅有工作记忆；schemas/memory.py | 增加本地索引、来源检查、兼容筛选和实际上下文投递 |
| 技能生命周期 | 已完成（旧证据格式） | skills/registry.py、tools/skill_policy.py | 复用版本／提案／验证机制，增加平台证据适配及公共接入 |
| 运行时协作 | 缺失 | agents/contracts/ 仅为角色／输出约定 | 本地并行参考工作者、独立输出、共享资源、协调验收 |
| 平台命令与视图 | 部分完成 | examples/workbench.py、tools/dynamic_view.py | 平台 CLI 和按指标生成的统一视图，旧页面保留 |
| 并行开发规范／模板 | 部分完成 | docs/framework_extensions.md | 补齐模块责任、扩展包和开发任务单模板 |

## 阶段

1. 基线审计完成；未运行历史实验。
2. 实施版本化契约、声明式注册、项目事务存储和会话宿主。
3. 完成到达／长度保持两类任务、原两个后端及参考后端、独立评价与可恢复搜索接入。
4. 完成事件、不可变内容、请求回执、共享资源与未知中断保护；模型实参不能自报调用者。
5. 完成跨运行记忆、原技能生命周期适配和确定性双工作者；实际重叠、取消、失败、冲突与过期候选路径通过。
6. 27 项聚焦组合验收通过；两次 MuJoCo 短执行及一次 MATLAB 短执行通过有效性检查。MATLAB 另有一次启动被访问控制拒绝、未进入求解。
7. 完成交付模板与中文指南；补查请求原文留存、开发记忆身份、原始文件导出及依赖声明完整性。最终结果见验证文档。
8. 最终 28 项组合检查及新增迟到输出恢复检查通过，共 29 个不同用例。两个完整配置、数学模板、工作台 CLI 闭环、8 条只读命令、生成目录及文档链接已检查。证据包和最终报告已交付；没有提交、推送或合并。

## 验证中发现并处理的问题

- 并发夹具时间窗口过短，不能据此声称重叠；扩大参考工作窗口后用实际时间戳证明重叠。
- failure_ready 是输出已产生而进程仍退出中的状态，不等同于费用已结算；验收等待显式收集。
- 历史 state、budget 和 working_memory 是可变状态，摘要变化单独展示，不改写为数值证据失败。
- V1 共同描述的力限是原文件中的 20 N；修正误引用其他历史实验 120 N 的测试预期，未改物理值。
- 平台脚本最初叫 platform.py，遮蔽 Python 标准库；更名为 development_platform.py，旧工作台转发保持平台命令。
- 旧技能测试的 tempfile 私有目录在当前 Windows 管理权限下不可访问；验收器改用普通工作区夹具目录，原断言不变且保留文件，不放宽业务检查。
- 故意篡改证据的测试不能再用篡改后的输出统计计算类型；统计改以冻结调度身份补充。
- 依赖声明加入资源后必须将 tuple 正规化为 JSON 数组，避免保存后出现伪依赖变化；已修复并定向复验。

验证次数以最终 `docs/platform_validation.md` 和结构化验收记录为准；不把离线回复、合成信号或故障注入称为真实模型／物理验证。
