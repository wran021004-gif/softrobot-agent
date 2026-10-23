# S139：任务条件化执行与 Backend 收口

日期：2026-10-23。基线：`origin/feat/s135-task-conditioned-control`（`dcbca1b3`）。
独立 worktree：`.worktrees/s139-task-conditioned-execution`；分支：`feat/s139-task-conditioned-execution`。

1. **解除的绑定。** 复用 S135 的 `constant/timed/free_progress` 与同一 NLP。
   GVS 常量参考、初态准备及 RL Reach 参考统一经过已有适配器；历史
   `checked_reach/reach_numerical` 名称保留为兼容入口，注册 payload、Controller Registry、
   Backend 和配置系统没有另起一套。Tracking 的 endpoint reward 仍是原有合法终点塑形，
   observation 仍使用有序局部路径参考；未改变权重含义、PPO 或 Direct/Residual 映射。

2. **物理与控制分离。** `scene.assemble_physical` 只消费环境、安装、初态、力和时钟，
   不读取 goal/controller；原 `assemble` 负责绑定已有控制器和通用 `task_reference`。
   无时间路径不再标为 `time_reference`，不构造 Reach target。
   Reach 的 `target_world_m` 仅作为旧 XML 的可视化 marker 保留，不参与 Backend 误差计算。
   新增 `physical_scene_identity`，任务、控制与完整执行 scene identity 继续各自保存。

3. **Backend 与回放。** Backend 导出实际位置、关节状态、张力、时钟和求解记录；
   补充真实 post-step 世界系 `tip_velocity`（引擎 site Jacobian × 实际关节速度）。
   固定张力回放不再计算 Reach `position_error_m`，也不再传空/虚假 target。
   回放结算调用任务注册的独立 evaluator；仅 Reach 计算保持窗口，开发 Tracking 复用
   S135 组合验收并检查运动/张力采样覆盖。原候选、任务、模型、通道、时间网格、预算与
   Store 恢复绑定保留。任务侧从实际位置复算 Reach 误差；诊断保留原始位置指针和推导说明。

4. **保留的算法边界。**

   | 路线 | 保留行为与限制 |
   | --- | --- |
   | Reach 11.0.0 | 原保持/终端成本、deadline 缩窗、张力界、warm regeneration、失败保持 |
   | Tracking 12.0.0 | development_valid、untimed、有序投影/lookahead；不联合优化路径进度 |
   | Timed Tracking | 仅离线工作区；超出参考时域报错，物理路由及 RL 仍 unsupported |
   | SoRoSim/MATLAB | 现有 NMPC 需要静态目标；manifest 明确不支持 Tracking，未重写 MATLAB NLP |
   | RL | 原组合 reward、start/continue/resume、冻结授权与 Residual 精确兼容检查保留 |

   RL Reach 仍可在原轻量解释器运行：适配器的 schema/Store 导入改为按需发生，
   无需给旧 Reach worker 安装 `pydantic`、CasADi 或科研环境依赖。

5. **真实链路核验。** S135 Tracking 归档的 XML 与当前生成结果逐字节相同；
   Reach 原输入的当前 XML 与基线 scene 生成结果也逐字节相同。
   新 scene/源码身份变化属于本轮实现变化，不覆盖旧执行身份或证据。
   原 Tracking BackendResult 重算独立评价与保存 metrics 完全一致，仍为 `valid_failure`：
   **20/20 可用计划，20 次 `Maximum_Iterations_Exceeded`，0 solver exception，0 张力越界**。
   路径/覆盖/起点/终点分别为 18.201/16.573/4.842/22.008 mm，限值均 4 mm；
   回退 1.920 mm 通过。接口和采样链路已经执行；可用计划不等于收敛或任务成功。
   这些失败没有被改写为接口失败或不可行性证明，也没有调参重跑。

6. **验证与消耗。** 37 个不同针对性 unittest 已通过（S139 新增 7 个）。
   其中 S135 原数值测试只运行一次：constant/free_progress/timed 各一次离线 IPOPT，
   horizon=2、substeps=1、max_iterations=3；检查可用计划、有限成本及独立成本复算。
   其余覆盖物理 scene 分离、Backend 速度/相位、回放数值失败/越界/错网格、两任务独立结算、
   Tracking 历史失败、RL reward/观测/Direct/Residual/保存配置、Reporter 与 SoRoSim 路由边界。
   首轮一个新增测试把 Tracking 的评价窗与 Reach 时长混用，夹具修正后通过。
   原轻量 RL 解释器额外完成 Reach XML 加载、reset/观测，确认未导入 pydantic/CasADi。
   Python 编译与 `git diff --check` 通过。

   **新真实 MuJoCo 物理步数 0，完整实验 0，Provider 0，PPO 0，MATLAB 0。**
   Backend 测试的推进均为显式 mock/合成夹具，不作为物理性能证据。
   新回放 Tracking 结算通过离线接口测试；本轮没有新物理验证，不能声称几何性能改善、
   实时能力、鲁棒性或正式 Study 准入。
