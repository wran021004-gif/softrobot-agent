# PPO 跨任务兼容性审计与最小适配（2026-10-27）

代码基线 `c190f64ae`。检查 `tools/research/rl.py`、`tools/rl/{env,checks,run,train,continuation}.py`、`tools/research_tasks.py`、`tool_axis_task.py` 和注册任务评价/验收接口。没有启动训练、评价 episode、科学 worker 或新 Study。

结论：BF4 定时 Tracking、BF5 位置—工具轴和 BF6 真实负载定向 Tracking 均不能直接使用当前 PPO。现有语义是 Reach/Hold 与开发态 untimed geometric Tracking；支持后者不等于支持同一 task family 下的定时参考。本次不放宽白名单，只将这一本来在环境中才暴露的限制提前至 `prepare_input` 的 scene/XML 构建之前，并在 TaskAdapter/Agent 控制能力中明确投影。

## 现有环境实际做什么

`prepare_input` 验证 owned candidate，沿用 scene/compiler 生成冻结 XML，并绑定 hash、候选/任务身份、命名关节与绳序。它要求 ideal tension，拒绝外力 scene。此前只有 family reach/tracking 粗筛；`TensionEnv` 仍会检查 Tracking 的 control_reference 必须是 free_progress，否则 `RL_TIMED_TRACKING_UNSUPPORTED`。

observation 为所选关节 qpos/qvel、目标或局部路径位置误差、世界末端速度、上一实际张力和时域进度；几何 Tracking 额外有 path progress。无工具轴、方向误差/参考、真实负载一致性结果或接触状态。time fraction 的存在不代表定时 reference 已接通。

reward 现为位置/Reach holding speed/实际张力变化平滑，以及几何 path error/progress/regression。几何参考由 polyline 局部投影选取，位置 shaping 还保留端点语义。没有 timed-reference 位置奖励、联合轴奖励或 no-contact 奖励/硬终止语义。reward 高不建立原任务通过。

action 是所选 tendon channel 的 [-1,1] 向量；direct 仿射映射至 XML 的合法 Newton 张力界，residual 为兼容完整参考张力加有界残差，再 clip 至物理界。执行器要求 tendon transmission、fixed gain=-1、无 bias/dynamics、gear=1、控制/力界一致；下一实际张力来自负的 actuator_force。它不是位置、力矩或任意归一化控制。现有这个映射应复用，不因跨任务而变号、改单位或忽略 clip。residual 参考须匹配候选、任务、绳序、时间格和完整时域。

step 在每物理子步检查 warning、时间倒退和非有限状态；failure_mode=terminal 返回最后有效区间边界的显式训练 surrogate，valid_physical_transition=false。独立 `run_episode` 排除 surrogate，不把引擎重置后的状态当真实成功。正常完整 horizon 为 terminated；没有任务成功提前终止或“接触违反但数值未报错”的任务处理。数值稳定且有接触的轨迹当前仍可能经过环境，不能据此宣称无接触。

`checks.run_episode` 的 Tracking 分支只输出位置 signal 给原 `evaluate.tracking`，再检完整性和实际张力界。Reach 分支检查 holding/terminal 规则。它没有 BF5/BF6 的双信号、真实负载编译绑定和每物理步 contact 证据；简单开放 family 将使评价缺失或落错分支。

## 最小适配差异

| 接口 | BF4 定时 Tracking | BF5 位置—工具轴 | BF6 真实负载定向 Tracking |
| --- | --- | --- | --- |
| observation | 从原 TaskAdapter 取得当前/下一 post-step 时刻的定时参考；明确状态/命令/测量相位，不能继续自由路径投影 | 加实际世界单位工具轴、目标有向轴/方向误差、剩余时间；保持原位置和动态状态 | 同 BF4 的定时位置，加定时轴参考；真实负载为环境动力学的一部分，必要接触观测另明确定义 |
| reward | 定时误差和原阈值归一化；几何 progress 不替代时间一致性，holding speed 仍为零 | 联合位置/轴；单位轴 chord 可 shaping，但方向验收仍 arccos，不能用无向轴或位置一项替代 | 全时域位置/轴联合 shaping；无接触是额外硬条件，不能仅用软罚项代替 |
| action | 复用 actual ideal tension；保持通道顺序、SI 界、direct/residual 和实际力记录 | 同左；新 observation 意味旧 checkpoint 不能直接宣称兼容 | 同左；不得把质量/完整惯量替换成 world force 或更轻负载 |
| termination | 保留完整时域；早期接近不等于已满足后续样本 | 两个原评分时刻及完整时域，不能位置达标就早停 | 每 `mj_step` 记录 contact；训练提前终止可作为显式失败 surrogate，独立验收不得伪造完整记录 |
| independent evaluation | 完整 30 点、真实 post-step grid、注册 evaluator + 原协议 | 独立生成世界位置和 site_xmat 投影轴，原 0.58/0.60 s 同时验收，原 8 组件 | 原 30 点双信号、质量/COM/完整惯量/site 编译核对、每物理步无接触与原 10 组件 |

BF4 最小增量最小：已有定时位置 evaluator 可复用，但环境 reference/observation/reward 和独立导出仍需适配。BF5 再加真实轴状态/目标、联合奖励、原双信号注册验收。BF6 再加移动轴、真实 payload binding 和逐物理步接触生命周期；XML 能携带实体质量，并不意味着完整的 BF6 任务与验收已实现。

## 下阶段实现边界（本次未执行）

适配应由原 TaskAdapter 拥有任务参考/约束和能力声明，原 TensionEnv 消费它，原 compiler 拥有实际物理与 actual tension。独立评价复用注册 evaluator 及现有 acceptance assembly；不另建 PPO 专用的弱验收。训练 reward 与确定性科学验收始终分开。

变更 observation/reward/termination 或信号导出需要显式环境语义版本及 checkpoint 兼容检查，保留原 Reach/几何 Tracking 的含义；不能悄悄续训旧权重并混记样本。冻结 physics/control/sample dt、初始化、动作/力界、失败 surrogate 标记和真实预算，区分训练动作、尝试/完成积分、模型调用与独立评价 episode。完整独立评价额度要预留，训练曲线不授权 SELECT。

未来只需针对定时参考相位、轴方向正反/roll、不完整轨迹、实际张力、接触与负载绑定及独立评价做定向 fixture，再另行申请有限科学训练。无长时域反馈/扰动恢复等明确研究问题时，当前 BF5/BF6 已验证的 Native 路线仍是可比较的基线；“数学不好表达”并不是 PPO 自动优先的理由。任何 PPO 优势都需匹配任务和总预算的正式研究证明。

本次只完成审计、最小方案、能力投影及原不支持语义的提前拒绝，没有开发 optimizer、PPO 新任务环境或训练。

方法目录同步修正：Native direct-control 的完整跨任务路线不再被 T1/T2 直接继承；后两者目录与实际 Native admission 共用原不适用理由，明确本轮 BF4/BF5/BF6 不适用。它们不是 PPO 的替代兼容性声明。
