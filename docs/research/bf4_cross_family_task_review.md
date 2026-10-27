# BF4：跨机器人任务类别审计

日期：2026-10-27。分支：`research/bf4-cross-family-benchmark`。
基线：`integration/research-next@d7b0f91f966ef96fa17b181ead99dff9a2d457cc`。
远端 HEAD 已核对一致；BF2 来源仍为 `ce2feacdcf3a4f194f33f7fcbf804c55a75ee90d`，未合并其分支或数据。

本轮优先实现**时间约束轨迹跟踪**。代码审计支持原定优先级，没有发现必须换题的阻塞。
B2/BF2 不重新搜索；C 线的 Agent Prompt、研究决策上下文、监督逻辑不修改。

## 能力与优先级

| 排序 / 类别 | 应用与结构作用 | 控制问题 | 真实已有接口 | 最小缺口 / 成本 |
|---|---|---|---|---|
| 1 / 时间约束轨迹跟踪 | 连续扫描、涂胶、检测；腱路影响方向驱动能力，长度分配改变工作空间、惯量与瞬态响应 | 在指定时刻追踪 `r(t)`，处理方向变化和局部减速 | `task.tracking`、`TrackingGoal.time_requirement`、`evaluate.tracking`；adapter 的 timed `norm_bound`；NativeModel 完整序列；既有 response/pattern 搜索；独立 MuJoCo 回放 | 原基线缺 timed 复合验收，物理路由拒绝 timed，native/public search 限 Reach/Hold。本轮最小适配；无需新优化器。每个 0.6 s 完整回放 600 步，适合有限三结构研究 |
| 2 / 位置—姿态联合 | 工具定向、插入、规定方向接近；分段长度及驱动分配影响位置与切向之间的权衡 | 同时满足位置和姿态误差；仅有弯曲自由度，不能默认任意扭转可控 | MuJoCo 内部有 site 旋转与角雅可比；`mjcf.tip_site`，`gvs_reporting.reconstruct_motion` 调用 `mj_jacSite` | 保存信号和 `platform_analysis` 输出限 tip_position/tip_velocity；无正式姿态任务/误差/evaluator。下一候选宜先审计并定义工具轴方向，不能把 tip 位置称为姿态控制。工程成本中等，科研计算量待该契约确定 |
| 3 / 全身避障与受限空间 | 狭窄通道到达；分段与腱路影响整条软臂形状 | 约束每个臂段与障碍的距离/接触，而非仅 tip | 分段实体几何、MuJoCo 凸接触、报告中的接触计数；FamilySpace 仅做腱路站点/导孔几何检查 | `scene.assemble_physical` 仅接受一个命名地面；NativeModel 拒绝接触/引擎约束；无全身 clearance evaluator、障碍任务适配或连续碰撞保证。最小原型评估为这些接口尚不连通，本轮不增加模拟。工程成本高，需先限制到简单静态障碍 |
| 4 / 动态拦截、接触、接球 | 移动目标接触与捕获；结构影响可达速度、接触响应与保持 | 接触时刻、相对速度、持续接触/捕获与失落判据 | 物理后端有基本接触机制、已有时钟与 tip 运动信号 | 无移动物体任务执行与观测契约、接触对/时序评价或捕获机制；Native 数学不支持接触。到达球的位置不构成接球。成本最高，保留后续 |

## Tracking 的语义边界

- **Timed**：评分窗内每个保存的 post-step 时刻满足 `||p(t_k)-r(t_k)|| <= tolerance`；完整记录仍覆盖全任务。
- **Untimed**：保存折线的距离、覆盖、起点、终点、进度回退，由原 evaluator 独立判定；不能指定一套时间表后称其等价。
- 基线已有 `tracking_linear_development.json` 和 `tracking_timed_development.json` 均保留原字节和 draft 状态。本轮新增独立 BF4 规范，没有重写 4 mm 旧示例。
- 新协议 `offline_timed_tracking_v1` 只组合原 evaluator 与执行完整性、采样完整性、求解错误和张力边界。无 Reach 终点/保持速度替代目标，无新增隐藏硬条件。
- 当前登记的 timed evaluator 仅有 `tracking_max_error` 硬条件。RMS、末端误差为诊断；若未来任务增加姿态、进度或独立终点硬条件，须版本化相应任务与注册评价，不能由优化器自行省略。

## 数学与控制适用范围

`ResearchTaskAdapter.control_search_options()` 从冻结任务提取评分时刻、参考位置和容差。
既有 `constraint_vectors`、`task_measure`、`local_control_search` 同时支持原 Reach/Hold 和 timed Tracking。
Native 仍使用合法绝对张力、相同控制/采样网格及完整 MuJoCo 序列；其预测不会产生任务通过结论。

局部有限差分响应可说明哪些张力系数影响哪些时刻，并给出一次有限信赖域建议；全部探测均有实际积分成本。
它不能证明全局可行性、结构不可行性或结构收益。结构变化必须重新优化控制，再由独立原评价比较。

未迁移 nonlinear T1/T2、端点制动工具到 Tracking；T1 明确 `not_applicable`。
已有 affine timed `norm_bound` 数学表达保留；合成模型数学测试不构成该机器人模型已验证的 Tracking 预测能力。
几何 Tracking 的完整 saved-polyline 约束仍显式 unsupported，不能让局部 path proxy 代替。
无 Bayesian、VOI、概率代理模型、Provider 请求、RL 或长期 NMPC。

## 下一步

已按获授权的 S1 和事先限额续段取得完整独立 Tracking 见证（最大误差 11.40 mm < 12 mm），成功后立即停止；见 [S1 报告](bf4_tracking_s1.md)。
尚需在另行冻结的公平预算下完成结构—控制比较和必要的独立起点复核；当前不能宣称结构收益。
在可信验证之后，下一独立类别优先考虑“末端位置 + 工具轴方向”，先明确姿态信号和可控制方向。
本轮只正式开发 Tracking；不能据接口准备声称其余三类已支持。

当前交付状态、工程成本和科学预算边界见 [Tracking 报告](bf4_tracking_benchmark.md)。
