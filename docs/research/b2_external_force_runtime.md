# B2 外力执行接口（B1）

2026-10-26，Asia/Shanghai。基线 `618fba9a11a1a1d0c9fca5228d25e873b7c8dddd`；
独立 worktree，分支 `feat/b2-load-force-runtime`。

## B1.1 统一物理语义

沿用 `task.environment.data.external_forces` 的既有 `TimedForce`，经
`assemble_physical` 冻结为 `scene['forces']`，不增加另一套外力输入。
第一版 `world_body_com_force_v1`：在已命名机器人 body 的质心，施加世界坐标系
恒定向量 `force_n`，单位 N。时间窗口为 `[start_s,end_s)`，边界必须在控制网格上且
位于任务时域内。每个实际积分子步之前按该子步起点重新写入 `xfrc_applied`，
重叠力相加，窗口外清零；采用整数积分 tick 避免引擎累计时刻的浮点误差移动边界。
同一子步内部维持该世界力不变；不改变积分器或其他物理参数。

`xfrc_applied` 的前三项为世界力，后三项为关于 body 质心的零力偶。
广义力为 `J_body_com.T @ force_n`，会产生关节力矩。**这不是 tip_site 点载荷**，
两点通常不重合；不额外施加假想 tip 力矩，不实现附加物件质量、惯量或抓取接触。
既有 schema 继续拒绝非 world、非 center_of_mass、非恒定向量及非法时间窗口。

普通 MuJoCo 后端改用同一施力函数；保留既有碰撞、地面、数值失败和任务评价。
本阶段未执行新积分。Native 与独立张力回放将在后续阶段接入。

## B1.2 Native 接通

Native 初始化使用原场景合法性检查，接受既有 world / center_of_mass 定时恒力。
不支持的形式仍经原 schema / 适用性入口拒绝。restore 后由冻结场景重建
`xfrc_applied`，拒绝额外的 `qfrc_applied`；reconstruct 校验前缀的外力、初态及网格。
forward 与三个积分循环（前缀、常输入、张力序列）均刷新外力。
控制优化继续使用原搜索器，所有候选从同一状态克隆，并使用同一个冻结外力定义。

力学输出新增 body COM 外力的广义力及其末端加速度贡献；原 `qfrc_applied`
仍保留原含义。质量平衡继续基于引擎 `qfrc_smooth`，解释式显式包含 `J_com.T F`。
保留每子步接触、约束、警告、非有限检查，未改变地面、碰撞或积分器。
成本区分成功返回的 `physics_steps` 与调用前计数的 `physics_step_attempts`。
本阶段仅编译检查，新增积分 0；真实匹配验证集中在 B1.4。

## B1.3 独立张力回放接通

`playback_tensions` 使用与 Native、普通后端相同的绑定/施力函数，采样 forward、
命令 forward 和每个实际 mj_step 前都刷新外力。原 `physical_replay.binding`
已按完整 task identity 绑定冻结任务，调用路径无需新增参数或第二套 Schema。
保留绝对张力、ZOH、初态、控制/采样网格和独立注册 evaluator / 复合验收。
完整执行仍可任务失败；不完整或数值失败不能成为结构不可行结论。

原始回放结果保存冻结外力、语义、成功积分数、尝试积分数、forward 次数及墙钟。
引擎失败快照也记录尝试步数；失败调用的内部部分进度仍标为 unknown。
本阶段仅编译检查，新增积分 0。

## B1.4 验证协议（积分前提交）

`examples/b2_load_force_smoke.py` 只复用已有中性两段四腱机器人配置，**不读取旧成功张力**。
固定全部四腱 0.2 N、原零初态、0.35 s、0.01 s 控制/采样、0.0005 s 积分；
原重力、地面、碰撞、质量惯量及 implicitfast 均保留。
测试外力为既有 `payload` body 质心 `[0,0.02,-0.03]` N，窗口 `[0.10,0.25)` s。
该机器人原有 body 名为 payload；本轮未添加物件、质量或惯量。

五次完整执行：基线提交原 Native 零外力、新 Native 零外力、独立零外力回放、
新 Native 非零外力、独立非零外力回放，预计 3,500 步。
从独立非零回放重建 0.10 s 前缀再 restore / suffix，预计 700 步；
两次同初态同张力 0.02 s 常输入候选，预计 80 步。总预计 **4,280 / 5,000 步**。
每次真实 mj_step 调用前审计外力、质心力偶及整数 tick，累计尝试数硬限 5,000，
异常也写成本，拒绝覆盖已有输出；不自动重试或扩额。
只比较时间、tip 位置/速度及张力，不要求完整内部状态逐字段相等。
原 evaluator 和复合验收如实保留；任务失败与数值未完成分开。

积分前 24 项定向测试通过（含 unittest 自动收集的 8 项既有 Reporting fixture 测试），
均没有 mj_step；追加的 task-only 配对组合检查亦通过，累计 25 项不同测试。
准备时发现继承任务的空字典会合并而不会清除具名关节，已改用独立 task-only
零条件加一层外力条件继承，未改配置合并器；准备/检查错误均发生于任何积分之前。

## B1.5 待冻结任务

`tasks/b2_load_hold_zero_v1.json` 与 `tasks/b2_load_hold_v1.json` 构成 task-only 草案。
两条件相同目标 `[0.29,-0.035,0.19]` m、相同零初态和网格，相同结构完成，
允许各自从 0.2 N 冷启动重新优化。原终点/保持位置 0.010 m、保持速度 0.020 m/s、
末 0.05 s 保持窗口不变。
草案有力条件暂设 `[0,0.02,-0.03]` N，作用于命名 payload 的质心，窗口 `[0.10,0.35)` s，
覆盖保持段。工程 smoke 的窗口较短以检验结束后清零；**草案完整负载保持窗口尚未进行
物理可执行性验证，目标、力大小及窗口均未正式冻结**。本轮不搜索可行解。
