# S138：任务条件化数学分析与自主结构设计

2026-10-23（Asia/Shanghai）。基线 `origin/feat/s135-task-conditioned-control`
`dcbca1b3d477ec079390d4b1cfa6432f6cbcba24`；独立 worktree
`.worktrees/s138-task-conditioned-research`，分支 `feat/s138-task-conditioned-research`。
已阅读 AGENTS.md、S134、S135、S136 报告和条件矩阵。

## 跨任务数学准入

删除 `analysis.dispatch` 的 Tracking 整类拦截，以及以“必须有 Reach target_m”
解释所有 Tracking 模型不可构建的旧理由。准入检查现有模型提供者、物理能力、
参考类型、信号实体/维度/单位/坐标/采样相位、工作点与时域、覆盖、预算和冻结授权。
已知不适用的请求在启动 worker、扣除数学次数之前返回原因；实际模型构建后仍复查。

| 现有方法 | 本轮行为与边界 |
| --- | --- |
| linearization / controllability | 可分析 Reach、自由进度、定时参考的合法 GVS 初始模型；Gramian 仍只是局部诊断 |
| equilibrium / static IFT | 目标平衡/halfway 需要常量参考；IFT 仍要求 SoRoSim 的明确静态工作点。当前 SoRoSim 动态参考准备未实现，会准确说明准备器假设 |
| endpoint / braking | 从 adapter 的终端 norm 条件提取参考和阈值；定时位置参考可只分析终端。没有速度硬条件时不把 braking 或 Reach 保持条件强加给任务 |
| trajectory / T1 / T2 | 消费原有任务条件；自由进度仍需既有 CONIC/PATH 方法。T2 复用验证过的候选模型组，不要求再次构建模型 |

真实结构候选的数学准备复用同一 initializer、坐标与张力顺序、物理上下界和 GVS
动力学；与物理执行准入分开。新回归用同一生成结构验证 Reach、Untimed、Timed
的 A/B/C/D/drift/x0/u0 一致；Timed 的物理执行限制仍保留。

没有修改正式 Study 审批、冻结 mathematical_methods、TaskDefinition/Evaluator
或 T1/T2 数值内核。不存在自动添加 grant；直接离线预检也不会创建正式 Study。
任意新任务、接触/避障等未建模物理仍不因此获得支持。PATH 保留五项独立几何验收的
未覆盖记录，`full_task_supported=false`；数值见证不是独立物理成功。

## 预算与搜索

令 B 为每个模型的内部 SOCP 子问题数：无折点为 1，两段路径为采样数减 2。
T1 预留 `1+B`（一次模型构建）；T2 对 k 个中心差分步长预留
`(1+2k)×B+2k`，模型准备另计。目录、T2 planning、正式调度和搜索统一此含义。
21 点两段路径的 T1 为 20；T2 的 k=1/2 分别为 59/99，不再是 5/9。
返回记录区分 kernel 调用和内部求解；中断保持未知实际次数，已预留额度不返还，
旧 receipt 复用不重复收费，历史证据不回写。

既有坐标/混合结构搜索新增显式 `objective="task_violation"`，选择已授权 CONIC，
按当前任务可表达条件的独立重放有符号违反量排名，并保留覆盖和数值最优性状态。
`max_evaluations` 计入模型准备与内部求解，不把 20 次消耗当成一次设计评价。
无 grant 或不足预算时不能自动改用别的方法。旧静态残差/Gramian 仍可由 Agent
明确选择为诊断。物理搜索新增任务中性名称 `task_acceptance`，旧名称兼容保留。

物理排名和 `core` 最佳候选交付沿用独立 acceptance。Tracking 现在读取路径偏差、
覆盖、起点、终点、回退五个有效条件；缺采样/无效执行不会凭低误差排在有效失败之前。
数学搜索的 root Plan 准入使用数学预算，不再展示 NMPC 执行容量。

## 极简双条件结构预检

复用两个独立 Reach TaskDefinition 和原 `evaluate.reach`，目标预先选为
`[0.29, 0.035, 0.19] m` 与 `[0.29, -0.035, 0.19] m`。
复用源相对参数生成器，比较基准、近端缩短 2 mm、近端加长 2 mm 三种结构；
远端反向调整，保持总长 0.27 m。两个目标的控制分别重新优化，没有新多目标框架。

A 的“原控制”明确指 S129 保存的基准数学控制序列
`gvs_pair.json#/baseline/trajectory/applied_input_n`，**不是原 NMPC 的新物理执行**。
所有 evaluator 输入都是完整、明确标注来源的局部仿射模型预测。

| 比较 | 目标 1：有符号违反量 / Reach evaluator | 目标 2：有符号违反量 / Reach evaluator |
| --- | --- | --- |
| A：基准结构 + 原序列 | -0.199999952 / 通过 | 6.045734316 / 失败 |
| B：基准结构 + 各目标重优化 | 约 -0.2 / 通过 | 约 -0.2 / 通过 |
| C：近端缩短 2 mm + 各目标重优化 | 约 -0.2 / 通过 | 约 -0.2 / 通过 |
| C：近端加长 2 mm + 各目标重优化 | 约 -0.2 / 通过 | 约 -0.2 / 通过 |

B 与 C 的差异绝对值最大约 `1.19e-11`，本次预检没有显示结构修改的有效增益。
A 在第二目标失败、B 通过，说明必须区分控制重优化的收益与结构收益。
这不证明结构没有价值，也不证明真实软臂已经通过；局部模型、固定工作点和有限时域
限制仍在。数学未收敛、代理失败或 A 失败都不能证明基准结构不可行。

原始配置、参数、模型、控制、重放、独立评价和来源哈希保存在
[structure_precheck.json](../../evidence/s138_task_conditioned/structure_precheck.json)。
脚本：[s138_structure_precheck.py](../../tests/research/s138_structure_precheck.py)，输出路径必须不存在。
实际预检：6 次模型构建、6 次 CONIC、2 次固定控制重放，23.00 s。

## Agent 目前可自主进行的动作

Agent 可以读取候选绑定的方法目录、覆盖/成本和保存模型；依据数学结果、真实失败反馈、
待检验假设及剩余预算选择下一步；在已有 grant 内生成长度、材料、截面、布腱/拓扑和
控制 recipe 变化，选择显式代理或任务违反量搜索；有匹配模型组时选择 T2 比较固定控制
与重新优化的结构响应；选择控制调整、已授权的独立物理验证、继续调查、停止或提交
独立验收通过的候选。各动作仍受原有 Schema、候选身份、授权和证据要求约束。

本轮没有 Provider 决策实验，也没有替 Agent 固化“先改结构/先调控制”等研究顺序。
上述 A/B/C 是一次离线诊断，不是新研究策略、通用优化器或新 Agent。

## 验证与未覆盖项

135 个不同的针对性测试最终通过，包含 9 个 S138 新测试；这是分批与修复后局部复测的
合计，不是一次全套测试。3 项旧 mixed-search 回归失败已在独立的原始 S135 worktree
逐项复现：历史配置哈希、旧 runtime-unavailable 断言、物理环境校准检查次序。
没有为它们绕过运行保护或修改旧科学材料。详细批次见
[validation.json](../../evidence/s138_task_conditioned/validation.json)。

Provider 调用、真实 MuJoCo 步数、PPO 训练、新正式 Study 全部为 **0**。
已有 T2 合成回归出现过 Clarabel 精度 warning，不提升证据强度。
没有验证真实物理结构增益、全局可行性、鲁棒性、实时性或 Agent 决策质量提升。
