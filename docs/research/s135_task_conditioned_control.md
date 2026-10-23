# S135：任务条件化控制与开发验证

日期：2026-10-23。范围：既有双段六张力候选、GVS/CasADi、MuJoCo 开发验证；非正式 Study。
阶段性交付：实现、针对性测试及单次 Tracking 执行已完成；单次 Reach 原配置执行仍在运行，结果另行补交。

1. **基线集成。** 从远端 S136 创建独立分支，无冲突合入 S134。修复方法目录把
   retained `unsupported` 条件误当作 PATH 内核完全不支持的问题。五项独立几何验收条件、
   数值见证时域、有符号违反量、模型范围、内部求解成本、原始引用和 Reporter 硬指标均保留。
   部分数学支持始终不等于任务成功。

2. **解除的绑定。** `ResearchTaskAdapter` 输出 `constant`、`free_progress`、`timed` 参考视图。
   GVS 初态/预张力准备、机器人动力学和初始局部线性模型不再要求 Reach `target_m`。
   同一候选两种任务的物理 identity、坐标/张力顺序及 A/B/C/D/drift 已实测相同。
   静态目标平衡仍要求明确的工作点；Tracking 不把首参考点冒充静态平衡。

3. **NMPC 路线。** 复用现有 GVS/CasADi 动力学、隐式积分、物理张力界、IPOPT、
   warm state regeneration、可用计划校验和失败保持逻辑。只扩展目标与固定参考参数，未复制求解器。
   Untimed 使用当前状态在当前路径段上的投影与局部 lookahead，接近折点后才进入下一段。
   NMPC 使用观测投影后的 GVS 末端位置，RL 使用 MuJoCo site 位置；独立评价使用实际物理记录。
   **这不是张力与路径进度联合最优的 NMPC。** 参考不随时间推进，窗口不强制到路径终点，
   停顿/变速允许；成本下降、零路径偏差或控制器局部进度均不代表路径完成。

4. **支持范围。**

   | 任务 | 支持 | 明确限制 |
   | --- | --- | --- |
   | Reach | 原 11.0.0 控制路由、固定目标、保持速度、终端成本及 deadline 缩短窗口 | 单次开发执行不证明鲁棒性或复现率 |
   | Untimed Tracking | GVS 12.0.0 + MuJoCo 1.2.0 开发路由、独立 evaluator、development 组合验收、RL 奖励/观测接口 | 必须 development_valid；无正式 Study 准入 |
   | Timed Tracking | `r(t)`/`rdot(t)` 参考、同一离线 NLP，越出参考时域明确报错 | 物理路由与 RL 明确 unsupported；调用者需给出合法预测时域 |

5. **Agent 可调内容。** 既有 Generation v2 `controller_recipe` 参数覆盖可选择位置、张力、
   张力变化、相对速度、前进和回退成本及 lookahead/capture、horizon/substeps、迭代/容差配置。
   Reach 原保持/终端速度项保留，Tracking 拒绝误用绝对速度保持。
   Agent 上下文交付任务参考和注册参数 schema；Pydantic、任务路由和原授权机制负责边界。
   Reward 支持 endpoint position、path error、正向进度、回退、Reach holding speed、张力变化、数值失败。
   `start` 可选注册项，`continue` 仅在冻结 continuation grant 内修改，`resume` 使用保存的原配置。
   不自动扩张历史 grant，不执行任意奖励代码，不把不同权重的 return 当作可比较任务成绩。

6. **证据链。** TaskDefinition/evaluator → 现有 adapter 与 S136 requirements →
   模型及控制目标/奖励 → 真实记录 → 原 `evaluate.reach` / `evaluate.tracking` → 组合验收。
   Tracking 新开发协议另外检查执行完整、运动/张力采样覆盖、力界与 solver errors；
   evaluator 自己仍拥有路径偏差、覆盖、起点、终点、回退五项判定。没有修改 evaluator 算法。
   RL Direct 映射不变，Residual 保留候选/任务/张力顺序/时间网格完全匹配检查。

7. **真实结果。** 原始输入、审核记录和便携证据归档位于 `evidence/s135_development/`；
   原始 S132 draft 未修改。归档包含 BackendResult 原始信号、运动、张力、求解记录及评价。

   | 项目 | Reach | Untimed Tracking |
   | --- | --- | --- |
   | 执行 | 原配置单次执行中 | 完整；0.4 s、400 个 MuJoCo 步、20 次控制更新 |
   | 独立任务评价／组合验收 | 待封存 | valid + false／valid_failure |
   | 可用计划／solver exception | 待封存 | 20/20／0 |
   | 张力范围／最大越界 | 待封存 | 0.0000031–5.289 N／0 N |
   | 模拟工具墙钟时间 | 待封存 | 146.422 s |

   Tracking 五项硬指标（限值均为 4 mm）：路径最大误差 **18.201 mm**、覆盖误差
   **16.573 mm**、起点误差 **4.842 mm**、终点误差 **22.008 mm**，均失败；
   回退 **1.920 mm** 通过。路径 RMS 12.772 mm 仅作诊断。
   所有 20 次 IPOPT 均到达 12 次迭代上限；可用计划不表示优化已收敛。
   horizon=4、max_iterations=12 在 Tracking 首次物理执行前选定，未调整验收阈值。
   平均完整控制更新 7.170 s，20 次超过 0.02 s 控制周期，不证明实时能力。
   运动与张力采样完整；采集结束时间不是无时间路径任务的完成期限。
   Tracking 已从归档原始信号重算 evaluator，数值指标与保存结果一致；重算无物理步骤。
   未通过后未调参重跑；本次数据不能证明该任务不可行。

8. **仍未覆盖的科学条件。** PATH 的 sampled path proxy 不等价覆盖真实折线的五项验收条件。
   局部仿射模型不证明全局非线性可行/不可行、连续时间成功、硬件性能或实时部署。
   正式 PATH 准入仍关闭，内部多分支求解成本需在未来正式授权时处理。
   未实现接触、避障、捕获、摩擦、伸长、扭转等新物理能力。

9. **验证与预算。** 51 个不同针对性 unittest 通过，新增 5 个测试方法；涉及修复后仅复测相关项。
   数值测试包含三种参考的真实 CasADi/IPOPT 离线求解、成本独立复算、同候选模型比较；
   RL 测试只计算奖励、加载 XML/观测和映射动作、验证配置保存恢复，物理步数为 0。
   真实物理执行已启动 2 次：Tracking 完成 1 次，Reach 在途 1 次；没有重跑。
   Provider 0、PPO 训练 0、新 MATLAB 计算 0、正式 Study 0；未验证主 Agent 的 Provider 决策 A/B。
   CLARABEL 合成测试出现既有精度 warning，不据此升级数学结论。
   Windows TemporaryDirectory ACL 与隔离环境 `.pth` 问题已在测试设施中修复。
   首次开发 runner 在 Store 创建前失败，物理调度 0；失败目录与日志保留，初始化已修复。
   验证解释器 `.s135-env` 复用现有科研/RL依赖，未安装或修改其他环境；
   Tracking RL 需要兼有科研依赖与 gymnasium 的解释器，原轻量 Reach RL 导入已回归检查。

10. **版本与交付。** 分支 `feat/s135-task-conditioned-control`。
    `4aae8af4`：S134/S136 语义集成修复；`936d3ca0`：任务参考、NMPC、奖励与开发输入；
    `a769b92c`：开发 runner 正确初始化既有 Store；`bfa42d2c`：首次执行前限缩 Tracking 计算配置。
    `8e700583`：Tracking 单次真实失败及可复算原始归档。以上提交均已正常 push 至同名远端分支。
    本报告先随已完成部分交付；Reach 运行结束后单独提交其证据与报告结果。
    未修改/合并 main、S132/S134/S136 分支或 F3 冻结验收和历史证据。
