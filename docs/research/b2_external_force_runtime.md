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
