# T10 — Impact-Recovery Control

T10 适合正文的研究决策与物理执行案例。它展示的是**固定机器人上的控制路线调整与多工况验收**，不是结构演化。材料来自历史 FULL/C Study `codex-expert-T10-20261113-verified-common` 及保留的前驱 Store；本次只读取历史状态、做表格和绘图算术，没有新求解、优化或物理积分。

## 主体身份与可支持的结论

原始 `RUNTIME.json` 的模型为 `codex-surrogate-no-provider`，Store receipts 的调用者为 `codex_surrogate_main`。最终报告明确“未运行正式 Main/Provider”。论文应称 **Codex expert / surrogate research execution**；不能把 replay 输入、专家路线或本素材整理改称 Main SDK 自主重复成功。

原始模型是强制冻结的 M2 硬件：两段柔性体，长度 0.16/0.11 m；六腱、六独立驱动；每段 12 个 cell、每 cell 两个弯曲关节，共 48 DOF。近端椭圆截面，远端渐变矩形截面；中间导向件 2 g、连接件 3 g、末端 payload 10 g。段刚度对应 Young 模量 7.2/5.4 MPa。腱路半径 18 mm，两组三腱的连续跨段关系保留。10 个精选节点的完整设计数据比较未发现结构参数改变（浮点等价容差 1e-11 相对、1e-13 绝对；仅忽略 metadata/provenance/id）。具体段截面、导向点、惯量和腱路应读原候选 `robot.structure.data`，不要凭外观重新设计。

主要原始来源：

- `paper_experiments/five_task_completion_20261113/T10_M7_impact_recovery/T10_RUN_06/STORE_RESEARCH/platform.sqlite`。
- 同目录 `TASK_PROTOCOL.json`、`COMMON_CONTROLLER_PREPHYSICS_CHECK.json`、`CONTROL_native_feedback.json`、`CORE_LOCK_PHYSICAL_EXECUTION.json`。
- 前驱 `paper_experiments/ten_task_codex_solve_20261112/T10_M7_impact_recovery/STORE` 和 `T10_RUN_02/STORE`；后续 `five_task_completion.../T10_M7_impact_recovery` 及 `T10_RUN_02` 至 `T10_RUN_06`。

所有可读绝对证据路径、candidate artifact、execution ID、原 XML 和结果引用均保存在 [evidence_bundle.json](evidence_bundle.json)。

## 推荐的研究决策链

1. **N01：完整约束暴露启动问题。** 在无冲击固定输入 replay 中，最终保持误差仅 3.135 mm，但冲击前误差 10.098 mm、速度 32.363 mm/s、腱速 26.452 mm/s，分别违反 10 mm、20 mm/s、25 mm/s 限值。原始决策指出历史插值控制与 Core 每间隔保持一个命令的语义不同，不能把名义末端保持好看等同完整可行。
2. **N02：改用 midpoint 命令，保留证据边界。** 同一候选 artifact 的新 midpoint 初始化使原无冲击协议通过：冲击前误差 9.135 mm、速度 13.921 mm/s，腱速 22.072 mm/s。但它仍是固定输入/开放环诊断，不是主动抗冲击控制方案。
3. **N03：形状化 GVS NMPC 被实测否决。** `T10_RUN_02` 测试平滑 approach 与腱速代价。原始物理 evaluator 的腱速 100.383 mm/s、行程 16.138 mm、最终保持速度 77.807 mm/s 超限。该回合仿真和评价完成，但 profile 因导出缺 `controller_observations.json` 失败，因此完整交付状态为 `execution_incomplete`；不能伪装成完整独立验收。此结果不证明所有 NMPC 配置或所有反馈方法不可行。
4. **N04：转向原生状态反馈。** `T10_RUN_03` 将历史原生静力参考、完整力切线、精确线性保持输入离散化、离散 LQR 与有界输入接到正式控制器。重新计算参考节点与增益后，`positive_y` 独立物理验收通过，最终保持误差 2.543 mm、速度 4.969 mm/s。该单工况通过仍不能替代最终共同控制器的三工况验证。
5. **N05：共同控制器证据检查拒绝旧组。** `T10_RUN_04` 个别 required 工况均通过，但严格联合检查发现实际首工况默认权重与其余配方不同。原始 `T10_RUN_05/REPAIR_VARIANT_PROVENANCE.json` 记录仅调整合法 bootstrap 默认选择：holding speed weight 0.1→0.5、terminal speed weight 0.1→0；物理域和控制边界保持不变。这是控制器一致性/接口修复证据，不要把它包装成新结构发现。旧组不能拼接为最终共同控制器成功。
6. **N06–N10：共同配方重新验收。** `T10_RUN_06` 在物理计算前核对五份实际控制器一致，重新执行三个 required 与两个 frozen 对照，再按原协议角色联合选择并封存。required 三项通过，frozen 两项保持真实失败。

精确原始 `trace.decision` rationale 与 actor、timestamp、evidence references 在 [agent_decision_timeline.csv](agent_decision_timeline.csv)。上述中文是归纳；CSV 明确区分原始字段、原始 rationale 和事后整理，未杜撰 Agent 内部推理。另保留 [complete_decision_index.csv](complete_decision_index.csv) 的 132 个原始决策 artifacts，不将它们全部放入正文。

## 最终任务与原始结果

目标 tip 坐标 `[0.29, -0.035, 0.19] m`。任务 1 s；physics timestep 0.5 ms，control/sample period 10 ms；重力 `[0,0,-9.81] m/s²`。冲击是施加于 payload 质心、世界 y 方向的 0.04 N 半正弦脉冲（0.50–0.55 s）。主动控制器只读普通原生状态、固定目标与自身参考时钟；冲击施加及 frozen actual input 由环境负责。

原协议窗口：approach 0–0.3 s；pre-impact hold 0.3–0.5 s；pulse 0.5–0.55 s；recovery 0.55–0.9 s；final hold 0.9–1 s。保持要求位置误差 ≤10 mm、tip speed ≤20 mm/s；脉冲结束后 0.35 s 内须出现至少 100 ms 连续有效保持。腱张力 0–8 N、行程 ≤15 mm、实际腱速 ≤25 mm/s，无非预期接触/警告。

| 工况（角色） | 最终保持最大误差 mm | 最终保持最大速度 mm/s | 恢复时间 ms | 原始验收 |
|---|---:|---:|---:|---|
| no_impulse（required） | 4.028091 | 5.416476 | 0 | PASS |
| positive_y（required） | 4.031812 | 5.430562 | 0 | PASS |
| negative_y（required） | 4.131382 | 5.565169 | 1.5 | PASS |
| positive_y_frozen（control） | 7.127697 | 21.582538 | 294.5 | FAIL：最终速度/全窗保持 |
| negative_y_frozen（control） | 7.620003 | 25.357390 | unavailable | FAIL：恢复/最终速度/全窗保持 |

恢复时间 0 表示脉冲结束起即满足原 evaluator 的有效保持条件，**不等于机器人完全没有响应或恢复速度无限快**。最终 negative_y 仅在脉冲结束后约 1.5 ms 恢复；不要把小幅扰动渲染成显著击退。positive_y_frozen 虽在截止前恢复一次，仍因最终速度失败而整项失败。

required 最大腱速 21.785914 mm/s、最大行程 5.711338 mm、最大张力 7.575620 N，均在限值内。每工况 14 个原始硬约束，三个 required 共 42/42 通过。两个 controls 按原角色单列，不能把它们改成 required failures，也不能改写为 PASS。

[FINAL_CASE_RESULTS.csv](FINAL_CASE_RESULTS.csv) 为逐项数值；`SOURCE_EXTRACTS/*_raw_evaluation.json` 是选中节点的原始评价摘出，不以旧论文汇总替代原始结果。

## 数学证据与成本的解释

最终原生反馈 preparation 文件记录：静力 least squares、centered full-force tangent、精确线性 held-input 离散化及 `solve_discrete_are`。两参考节点静力残差为 1.133831e-6 和 2.034816e-5 N·m。第一个节点因达到 120 次 nfev 停止、`success=false`；第二节点 nfev=49、`success=true`。这些是局部构造与残差证据，不是非线性稳定性证明，也不替代物理验收。

最终 `run06` 单独 Store 账本：5 次 physical launches，每次 2000 steps；charged mathematical-tool evaluations=0，provider calls=0，Codex host Token=unavailable。原 preparation 每次另记 9072 次 forward evaluations、0 physics steps，必须与 charged math 次数分开。最终账本 wall_s=44.2139835000271，recorded numerical wall=42.223230499977944；二者范围不同，不相加。早期 Study 版本、失败回合和配额迁移保留在 [resources_per_run.json](resources_per_run.json)，没有跨 run 简单求和。

## 原生渲染与论文图推荐

同一结构应展示真实状态与控制改变：最终 negative_y 的 initial、prehold、pulse peak、recovery、final；辅以 frozen negative_y 的 recovery/final，及 N03 GVS nominal 失败和 N04 native 单工况通过的状态对照。统一相机、尺度与光照。不可为 T10 制造几何不同的“候选结构”。

[STATE_SNAPSHOTS.json](STATE_SNAPSHOTS.json) 保存 10 个节点共 80 帧原始 dense qpos/qvel、原 XML、准确时刻、force/control/tension 与 source pointer；无需积分。final `RENDER_INPUTS/*_MOTION.json` 是统一管线直接摘出的 2001 帧密集物理状态。100 帧 `trajectory.json.gz` 是控制采样导出，不能用它替代 2001 帧评价网格核算极短恢复时间。

已制作并视觉检查两组正式 2D 图（PNG+可编辑 SVG）：

- [主动/冻结对照](FIGURES_PAPER/T10_impact_active_vs_frozen.png)：position error 和 tip speed 两 panel，聚焦 0.3–1 s。三个 required 为实线，两个 frozen controls 为虚线。限值只在原 prehold/final hold 窗口标示；pulse 为细竖线。展示实际反馈抑制残余振动的证据。
- [控制路线指标对照](FIGURES_PAPER/T10_control_route_constraint_comparison.png)：GVS nominal 不完整诊断、native 单工况通过、最终共同控制器三工况最差值。三个物理指标使用各自单位，离散点无连线；不同范围不是统一收敛曲线。

源数据和原来源保存在 `FIGURE_DATA/T10_final_execution_source.csv`、`T10_control_route_comparison_source.csv`；十个 final hold 算术重读值与原始 evaluation 逐一相符（差值 <1e-9 SI），检查在 `T10_plot_arithmetic_checks.json`。图注在 [FIGURE_CAPTIONS.md](FIGURE_CAPTIONS.md)，booktabs 表在 [TABLES.tex](TABLES.tex)。

## 仍有的边界

- 无正式 Main/Provider 重复执行、无权威 Codex host Token，标记 unavailable。
- 没有结构变化；候选 JSON 数量不是独立物理形态数量。当前索引 49 个候选 artifacts、22 个带可读独立物理结果的记录；这些仅是当前查阅范围，非实验总代价声明。
- 早期不完整 profile、拒绝的联合选择和实现版本修复均保留，不能改写成一条全成功科研轨迹。
- 不把无冲击开放环通过当成抗冲击反馈通过，也不把单工况通过当成共享控制器完整通过。
- 机器人 PNG/MP4、视觉 XML 与 `render_manifest.csv` 由统一 MuJoCo 管线生成；本文件不预先宣称渲染验证完成。
