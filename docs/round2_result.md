# ROUND 2 RESULT

基线分支：`feat/round1.5-trace-skill-infrastructure`，基线提交：`86458c0`。
本轮复用现有 contracts、Harness、registry、diagnostics 和 artifact/trace 服务。
通用 constrained reach 能力已实现；正式 reach_window benchmark 等待 Human 审批。
未 commit，未 push。

## STAGE RESULTS

| Stage | 结果 | 实际实现 |
| --- | --- | --- |
| 1 Audit | PASS | 审阅 schemas/tasks/benchmarks/physics/capabilities/tools/controllers/metrics/runs/skills/agents；修改前 26 项架构测试通过，真实 baseline 误差符合原值。 |
| 2 Task / Environment | BLOCKED（正式 benchmark）；PASS（开发 fixture） | 未找到获批窗口参数；创建 `tests/fixtures/reach_window_dev/`，明确标记 NON_CANONICAL / DEVELOPMENT_ONLY，未注册 benchmark。 |
| 3 analyze_clearance | PASS | MATLAB 采样完整 PCC 中心线，用臂体半径及采样误差界计算保守窗口净空，保存相交、最近段和穿窗证据。 |
| 4 Shared environment | PASS | 扩展现有 EnvironmentSpec 与 environment_xml；共享 window_boxes 从同一环境生成 MATLAB 参数和 MuJoCo 四根框条，XML 仍由现有一致性检查验证。 |
| 5 MuJoCo evidence | PASS | 真实 capsule–box 距离、接触对及计数、最近时刻、初始姿态和最终穿窗结果，保留紧凑汇总。 |
| 6 Diagnostics | PASS | 现有 bundle 新增 check_collision；区分预测相交、净空不能保证、预测/仿真碰撞不一致和无窗口接触，继续复用到达/执行器/数值诊断，归因 UNKNOWN。 |
| 7 Registry | PASS | analyze_clearance、check_collision 均为 IMPLEMENTED 且有真实 callable；同步 MuJoCo manifest，优化及学习工具仍为 PLANNED。 |
| 8 Deterministic route | PASS | reach_window 显式执行 M0 → M1 → clearance → 原 C1 → MuJoCo → metrics → diagnostics，新增 Tool/Gate 进入已有 trace。 |

## NEW CAPABILITIES

| Tool | 输入 | 输出 | Fidelity / limitation |
| --- | --- | --- | --- |
| `MatlabTools.analyze_clearance` | RobotIR、TaskSpec、EnvironmentSpec、已完成 PCC ToolResult | 最小净空下界、采样净空、预测相交/violation、最近位置/样本/机器人段/框条、穿窗指标、完整预测中心线 | low / geometric；PCC shape approximation；单节、固定 y-z 窗口；不含重力、动力学、地板及执行器可行性。 |
| `check_collision` | 同 run 的 clearance 与 simulation ToolResult，可选 evidence_paths | 预测与实际净空、接触及计数、disagreement observation、穿窗结果、UNKNOWN 因果归属 | 确定性证据运算；采样 surrogate 事实，不是因果诊断或连续碰撞保证；证据缺失返回 unavailable / UNKNOWN。 |

`matlab/analyze_clearance.m` 只接收 Python 从环境导出的 box centres/half sizes，
没有独立 MATLAB 环境文件。默认采样间距为 `min(0.001 m, radius/4, thickness/4)`；
本次为 401 个点、1 mm 间距。点到 box 的 signed distance 减臂半径后，再减半个
弧长间距（本次 0.5 mm），利用距离函数的 Lipschitz 界得到保守净空。
负下界与采样点确认相交分别记录，不能把负下界直接宣称为确定碰撞。
最近位置是采样最小值的位置，不声称是精确连续极值。

MuJoCo 使用 `mj_geomDistance` 获取实际 capsule–box signed distance，并从
真实 contact arrays 汇总非正距离的接触点。实现及算法边界参考
[MuJoCo geom distance 文档](https://mujoco.readthedocs.io/en/latest/computation/#geom-distance)。
新增观测没有向原 integration loop 插入 forward 或 step，物理常数和控制命令不变。

## END-TO-END RESULT

运行环境：Python 3.11.16；MATLAB R2024a `24.1.0.2537033`；MuJoCo 3.13.0。

| 项目 | reach_free canonical | reach_window_dev NON_CANONICAL |
| --- | --- | --- |
| 最终 run | `20260911T083554_614312Z_634800bf` | `20260911T083602_356646Z_25a425fc` |
| MATLAB predicted error | **0.08714456960728613 m** | **0.08714456960728613 m** |
| MuJoCo actual error | **0.17116166894090315 m** | **0.17116166894090315 m** |
| Target tolerance | 0.01 m，原值 | 0.01 m，开发 fixture |
| Target reached | false | false |
| MATLAB minimum clearance lower bound | 不适用 | 0.03950000000000001 m |
| MATLAB sampled minimum clearance | 不适用 | 0.04000000000000001 m |
| MuJoCo minimum window clearance | 不适用 | 0.009769850850218975 m |
| Window contact / count | 不适用 | false / 0 |
| Final aperture constraint | 不适用 | true，margin 0.00992697333975821 m |
| 最终结果 | **TASK_FAILED** | **TASK_FAILED** |

开发 fixture：target `[0.25, 0, 0.15]` m；window centre `[0.18, 0, 0.06]` m；
width 0.12 m、height 0.18 m、thickness 0.02 m、frame width 0.15 m；
base 位于 world origin，直臂沿 +x，窗口平面为 y-z，法向 +x。
这些值仅用于开发验证，不是获批 benchmark 或设计优化边界。

开发 evaluator：`target_reached AND final_aperture_constraint_satisfied AND
NOT obstacle_contact_occurred`。穿窗检查整条中心线在整个 wall slab 内的部分，
将孔洞按臂半径收缩，拒绝绕过有限框体但末端位于后方的路径。
地板不纳入 window contact gate；窗口距离证据也明确限定为机器人与窗口框条。

本次初始直臂已穿过窗口，初始净空为 0.009999999999999998 m，没有窗口接触。
因此该运行验证受窗口约束的最终形状/到达流程，**不证明从缩回姿态开始的插入动作**。
无窗口接触使本次物理轨迹与 reach_free 相同，这是实际结果而非重新调参。

## EVIDENCE RESULT

- 最终 baseline 保留 29 个 hashed artifacts、64 个 trace events；开发运行保留
  31 个 hashed artifacts、74 个 trace events。两个运行的 artifact hashes 全部验证通过。
- 新 `clearance_result.json` 包含 MATLAB 全中心线、采样精度、最近机器人段/框条和
  环境窗口参数；`mujoco_result.json / window_evidence` 包含 1001 次观测的紧凑汇总。
  最近实际几何对为 `capsule_3` / `aperture_bottom`，时刻约 0.022 s。
- 新 `check_collision.json` 和现有 `diagnostic_summary.json` 报告
  `no_window_contact_observed`，到达诊断继续适用；`failure_attribution=UNKNOWN`。
- `trace.jsonl` 包含 analyze_clearance、check_collision、model_clearance_gate、
  target_metric_gate、aperture_constraint_satisfied_gate、obstacle_contact_occurred_gate
  和 task_success_gate。预测筛查失败不阻止实际仿真取证。
- Environment/Task/Design snapshots、RobotIR、physics、controller、XML、最终状态、
  source_snapshot.zip 和参数 provenance 继续保留；开发几何的 scientific_status
  明确为 NON_CANONICAL_DEVELOPMENT_ONLY。
- 显式运行已有 extractor，生成
  `proposals/diagnosis/round2_candidate_finding.json`：9 项精确 observation，
  含窗口净空及接触，使用带 hash 的 artifact pointers。没有生成正式 Skill，
  production candidates/approved/deprecated 仍为空。
- 聚焦真实测试额外覆盖“预测形状相交”和“预测无碰撞但实际初始姿态有接触”；
  后者明确标记为初始重叠案例，不将其误报为运动中碰撞的因果证明。
- Numerical failure 沿用 inspect_numerics，缺少已完成仿真证据时 check_collision
  返回 unavailable / UNKNOWN。现有 actuator/tracking 诊断仍可报告限制观察。

实际距离只覆盖离散初始/每步积分前几何及最终刷新；contact_count 是跨样本接触点数，
不是独立撞击次数。单次运行不会自动转化为策略、Skill 或物理规律。

## HUMAN INPUT REQUIRED

1. **reach_window benchmark geometry 与验收语义**：target position、task tolerance、
   window centre/plane/orientation、width/height、wall thickness、有限墙体范围
   （当前表示为 frame_width）、coordinate convention。还需确认初始配置是否应缩回，
   是否采纳本开发版本的“最终穿窗且全程无采样窗口接触”判据。
   任意旋转窗口需要额外实现，当前仅支持 y-z 平面法向 +x。
2. **approved optimization variables and bounds**：允许变量、上下界、单位、约束和
   objective authority；现有 grammar 没有获批边界，optimize_design 保持 PLANNED。
3. **物理及因果判据（既有待决项）**：EI/material 到等效刚度、damping law、
   tendon elasticity/slack/friction、validated actuator model、multi-section coupling，
   以及 model mismatch/tracking/anomaly 的获批判据；本轮没有补造这些规律。

## REGRESSION RESULT

- 修改前：26/26 架构测试通过；真实 baseline 记录在
  `runs/20260911T082230_391536Z_8d69f682/`，两个误差与规定值精确相同。
- 新增测试仅 **7 项**，覆盖共享几何、整臂约束、真实距离/接触、诊断证据、
  MATLAB nominal/相交/预测不一致案例及一条实际 Harness 集成。
- 最终完整回归：`SOFTROBOT_TEST_MATLAB=1`，
  `python -m unittest discover -s tests -q`：**81/81 PASS，62.881 s，无 skip**。
- 完整回归之后再次实跑 canonical 与 development 两条链路，均完成并保存证据。
  canonical 两个误差精确一致；全部 simulation metrics 除 run identity 外一致。
- 8 个 canonical artifacts 与修改前逐字节一致：robot.xml、robot_ir.yaml、physics.yaml、
  design_input.yaml、design_final.yaml、controller.json、tendon_command.json、simulation_state.json。
- 初始 shell 的 base Python 缺 PyYAML，改用已安装 softagent 环境。
  初次 sandbox 执行遭遇 Windows 临时目录访问拒绝，正常权限重跑成功；本轮留下的
  14 个空临时目录经逐路径检查后已清理，没有为环境问题修改测试预期。
- `git diff --check` PASS；reach_free Task/Environment、benchmark、grammar bounds、
  physics contracts、controller 实现和原 baseline expected values 均未更改。
- 无 LLM、RL、optimizer、Memory DB、新 physics law、Skill automation 或 orchestration dependency。
