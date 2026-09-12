# ROUND 3 FINAL RESULT

本轮出口：**PHYSICS_MODEL_REFINEMENT_REQUIRED**。三变量设计探索的最佳已观测 MuJoCo 端点误差为 **0.1089206160124638 m，TASK_FAILED**；解析 PCC 匹配长度能够消除几何端点误差，但不能消除模型与仿真的形状差异。

基线：`feat/round3-1-debug-visualization` / `dbff31596fccabca24eddc18ccd5691ced164206`。研究使用真实 MATLAB Engine / MuJoCo、原 `reach_free_v1`、M0/M1、C1、`legacy_v1_surrogate`。任务、阈值、gate、基线设计、控制参数、PhysicsContract 均未改动。无 commit / push。

证据入口：[研究总表](../runs/20260912T065841_048677Z_327e752a/round3_final_summary.json)。五组研究新增 63 次候选评估，其中 26 次 MuJoCo；复用 12 条已有评估记录。父研究的 PASS 表示计划执行完整；所有接受 MuJoCo 评估的设计仍为 TASK_FAILED。

## V1 DESIGN ENVELOPE

长期权威源：[SURROGATE_EXPLORATION_ENVELOPE_V1](../capabilities/robot_families/tendon_driven_continuum/envelope.yaml)，对应 [Human 授权](../configs/experiments/round3_final_human_authorization.md)。长度下界按最终指示保留 **0.05 m**。

| 字段 | 可表达范围 | 本轮探索权限 |
|---|---|---|
| sections | 1 | 固定；多 section 尚不支持 |
| total_length_m | 0.05–0.80 m | 可优化 |
| tendon_routing_radius_m | 0.002–0.018 m | 可优化 |
| tendon_count | 整数 3–8 | 可离散优化 |
| body_radius_m | 0.010–0.050 m | 可表达；优化为 PHYSICS_ASSUMPTION_REQUIRED |
| segments | 整数 4–24 | 仅 NUMERICAL_SENSITIVITY_ONLY |

长度与半径须有限且为正，并校验 `tendon_routing_radius_m < body_radius_m`。Engineer 可直接提交包络子集 ExperimentPolicy，引用已有授权；越界、遗漏关系约束、改变物理/控制路线或把 segments 当设计变量仍被拒绝。历史 Round 3.1 小范围授权兼容保留。该包络只授权 surrogate 探索，不代表制造、材料或真实机器人验证。

## LENGTH STUDY

固定 routing radius = 0.015 m、tendon count = 4、body radius = 0.020 m、segments = 8。目标为 `[0.25, 0, 0.15] m`；解析 PCC 解为 `L = 0.3062377168199977 m`、`theta = 1.0808390005411683 rad`、`phi = pi/2`。使用同一 PCC 公式推导长度，不修改 M1 planner。

| L (m) | M1 端点误差 (m) | MuJoCo 端点误差 (m) |
|---|---:|---:|
| 0.05 | HARD 几何拒绝 | 未运行 |
| 0.10 | HARD 几何拒绝 | 未运行 |
| 0.20 | HARD 几何拒绝 | 未运行 |
| 0.25 | HARD 几何拒绝 | 未运行 |
| 0.29 | 0.0152216443 | **0.1201748210** |
| 0.30 | 0.0058433049 | 0.1218785425 |
| 0.3062377168（解析解） | **4.61987347e-8** | 0.1233191748 |
| 0.32 | 0.0128735035 | 0.1274606879 |
| 0.35 | 0.0408427752 | 0.1405118443 |
| 0.40（旧基线） | 0.0871445696 | 0.1711616689 |
| 0.50 | 0.1783105297 | 未运行 |
| 0.60 | 0.2668840821 | 0.3337022742 |
| 0.80 | 0.4296763472 | 未运行 |

13 点筛查、7 次 canonical 比较覆盖基线、解析解、邻点与明显长臂。短臂按既有必要可达条件拒绝，不生成虚假 M1/MuJoCo 数值。后续采用 canonical 最佳已观测长度 0.29 m；它不是长期包络下界，也未证明是连续长度最优值。[完整记录](../runs/20260912T065841_163036Z_f8fb4c1b/study_rows.json)

## ROUTING RADIUS STUDY

固定 L = 0.29 m、count = 4。所有点的 M1 端点误差相同（0.0152216443 m），Jacobian rank = 2、condition number ≈ 1；半径改变腱命令和 Jacobian 尺度，因此按行程尺度覆盖选择 MuJoCo 代表点。

| routing radius (m) | 最大绝对行程 (m) | MuJoCo 端点误差 (m) |
|---:|---:|---:|
| 0.002 | 0.002124587 | 0.155312050 |
| 0.004 | 0.004249173 | 未运行 |
| 0.006 | 0.006373760 | 0.149737655 |
| 0.008 | 0.008498347 | 未运行 |
| 0.010 | 0.010622933 | 0.135827666 |
| 0.012 | 0.012747520 | 未运行 |
| 0.015 | 0.015934400 | 0.120174821（复用） |
| 0.018 | 0.019121280 | **0.115210920** |

8 点筛查、5 次 canonical 比较（4 次新增 MuJoCo）。最佳已观测半径 0.018 m 位于批准上界；未扩展边界，也不据此宣称真实机械优势或所需腱力。[完整记录](../runs/20260912T065913_229449Z_d98573f2/study_rows.json)

## TENDON COUNT STUDY

固定 L = 0.29 m、routing radius = 0.018 m。全部 6 种拓扑接受 canonical 比较（5 次新增）。M1 端点误差相同，几何 Jacobian 均 rank = 2、condition number ≈ 1。

| count | 最大绝对行程 (m) | MuJoCo 端点误差 (m) | 最大最终腱长跟踪误差 (m) | 观测峰值力 (N) |
|---:|---:|---:|---:|---:|
| 3 | 0.016559514 | 0.122768090 | 0.006796093 | 16.559514 |
| 4 | 0.019121280 | 0.115210920 | 0.004555813 | 19.121280 |
| 5 | 0.018185418 | 0.113008928 | 0.003758456 | 18.185418 |
| 6 | 0.016559514 | 0.111140417 | 0.002795002 | 16.559514 |
| 7 | 0.018641870 | 0.109923833 | 0.002760184 | 18.641870 |
| 8 | 0.019121280 | **0.108920616** | 0.002551894 | 19.121280 |

所有结果 TASK_FAILED，警告计数为 0，未观测到 20 N 最大拉力限幅。增加腱数量也改变 surrogate 驱动配置；该局部趋势不构成制造最优或控制器充分性的结论。[完整记录](../runs/20260912T065928_791538Z_47ffcb4d/study_rows.json)

## JOINT SEARCH RESULT

包络内 seed = 17 的小规模联合研究：**20 个模型筛查候选 / 10 个 canonical 比较**，满足 ≤30 / ≤10 的上限；新增 17 次模型评估、5 次 MuJoCo，其余复用。候选来自先前 canonical 代表点、解析长度邻域与证据引导的随机采样；覆盖半径/数量差异后再参考 M1 排序，没有全组合网格。联合研究未超过前序 count = 8 的结果。

| 最佳已观测 surrogate candidate | 值 |
|---|---|
| total_length_m / tendon_routing_radius_m / tendon_count | **0.29 / 0.018 / 8** |
| 固定 sections / body_radius_m / segments | 1 / 0.020 / 8 |
| M1 prediction / MuJoCo actual | 0.015221644271566406 / **0.1089206160124638 m** |
| TASK status | **TASK_FAILED** |
| theta / phi | 1.0622933394693397 / 1.5707963267948966 rad |
| 最大绝对行程 / 行程跨度 / 最大行程除以臂长 | 0.019121280110448113 m / 0.03824256022089623 m / 0.06593544865671763 |
| 命令正性 / Jacobian rank / singular values / condition | true / 2 / [0.036, 0.036] m/rad / ≈1 |

`analyze_actuation` 同时保存每根腱的中性长度、目标、正负行程、绝对行程和归一化行程；Jacobian 坐标为 `(theta*cos(phi), theta*sin(phi))`。它只提供几何驱动分析，不输出所需腱力或电机扭矩。

最佳证据：[run](../runs/20260912T065938_430868Z_300d5612/run.json)、[驱动分析](../runs/20260912T065938_430868Z_300d5612/actuation_result.json)。RobotIR SHA-256：`4a74a1f179e87a2e4d9ad73cb728e09fd51d62149b450c95788cf0d1a1208739`。这是有限样本中的最佳已观测值，**不是 global optimum**。[联合候选与结果](../runs/20260912T065940_759649Z_d28aa479/study_rows.json)

## DISCRETIZATION SENSITIVITY

固定上述最佳三变量设计，仅改变 segments。六组的 controller、tendon command、task、environment、run settings、simulator、physics 文件逐字节一致；每关节 stiffness/damping 沿用旧参数，没有加入随段长缩放的物理规律。

| segments | 总质量 (kg) | MuJoCo 端点误差 (m) | 最大最终腱长跟踪误差 (m) | 中心线 RMS 差异 (m) |
|---:|---:|---:|---:|---:|
| 4 | 0.498466034 | 0.086994238 | 0.004704324 | 0.049991934 |
| 6 | 0.565486678 | 0.098304715 | 0.003074552 | 0.055121936 |
| 8 | 0.632507321 | 0.108920616 | 0.002551894 | 0.059263039 |
| 12 | 0.766548607 | 0.118673972 | 0.001973764 | 0.062193676 |
| 16 | 0.900589894 | 0.124925195 | 0.001657411 | 0.063902716 |
| 24 | 1.168672467 | 0.131677028 | 0.001365769 | 0.065391226 |

每组 1000 步均完成、状态有限、warning = 0、TASK_FAILED；相同命令下观测峰值力均为 19.121280 N，无最大拉力限幅。总质量随分段数增加：现有 capsule 分段引入额外端帽体积，编译出的每体质量/惯量随之变化。[完整质量、惯量、力、跟踪和数值证据](../runs/20260912T070008_427162Z_cb6745f9/study_rows.json)

因此 segments 已改变有效 surrogate 力学，不能作为纯网格收敛或物理设计优化来解释。segments = 4 不参与最佳物理设计排名；腱长跟踪误差减小时端点误差反而增大，也不足以单独诊断控制器问题。

## MODEL VS SIMULATION SHAPE

普通工具产物 `model_shape.json` 保存 MATLAB PCC 中心线；`mujoco_result.json` 保存最终 segment 原点与 tip 构成的折线。相同 run/RobotIR/任务/环境/坐标系/常值命令下，按归一化弧长重采样 65 点。`shape_comparison.json` 保存 RMS、最大值位置和逐点差异，不读取 debug 文件、不增加仿真步、不改变 gate。

| 代表设计 | tip discrepancy (m) | RMS discrepancy (m) | max discrepancy (m) |
|---|---:|---:|---:|
| 原基线 | 0.184104561 | 0.097600432 | 0.184104561 |
| 解析匹配长度，原半径/数量 | 0.123319131 | 0.066457875 | 0.123319131 |
| 最佳长度 | 0.114159121 | 0.061711209 | 0.114159121 |
| 最佳半径 | 0.109004903 | 0.060634046 | 0.109004903 |
| 最佳联合设计 | **0.102344769** | **0.059263039** | **0.102344769** |

这些代表例的最大差异均在归一化弧长 s = 1。最佳联合设计预测 tip ≈ `[0.238453493, 0, 0.140081500] m`，实际 tip ≈ `[0.271525829, 0, 0.043227629] m`。[正常形状诊断产物](../runs/20260912T065938_430868Z_300d5612/shape_comparison.json)

未定义新的形状容差；差异是观测证据，`failure_attribution = UNKNOWN`，不自动升级为 MODEL_MISMATCH。

## PHYSICS LIMITATIONS

- body radius 尚未与材料、EI、质量/惯量、刚度/阻尼建立获批的统一耦合；本轮保持固定，优化仍需 PHYSICS_ASSUMPTION_REQUIRED。
- 分段 capsule 质量与每关节固定参数不保证离散化后的物理等价；需先定义物理合同，才能讨论收敛或迁移到真实结构。
- PCC 几何假设与 MuJoCo 分段、受力、单向拉力驱动之间没有已校准的映射；缺少获批 tracking/mismatch/stability 阈值。无警告、未达最大拉力均不能证明真实物理有效或确认失败原因。

## DEBUG / VISUALIZATION

复用已有 debug exporter；所有 26 个新增 MuJoCo run 均有 trajectory、PCC、tip error/xyz、tendon tracking、actuator force、qpos/qvel 图及无错误的 status。以下入口覆盖要求的代表设计，图像标签保留 DEBUG_ONLY / NON_CANONICAL：

| 代表 | 图像入口 |
|---|---|
| 基线 | [PCC](../runs/20260912T065852_959860Z_ac884a29/debug/matlab_pcc.png) |
| 最佳长度 | [端点误差](../runs/20260912T065858_654996Z_25985350/debug/tip_error.png) |
| 最佳半径 | [驱动力](../runs/20260912T065926_549878Z_f23117ad/debug/actuator_force.png) |
| 最佳联合设计 | [PCC](../runs/20260912T065938_430868Z_300d5612/debug/matlab_pcc.png)、[端点误差](../runs/20260912T065938_430868Z_300d5612/debug/tip_error.png) |
| segments = 24 | [腱长跟踪](../runs/20260912T070018_474250Z_764b5e62/debug/tendon_tracking.png)、[qpos/qvel](../runs/20260912T070018_474250Z_764b5e62/debug/qpos_qvel.png) |

数值结论取自正常工具产物，图像仅辅助人工阅读。所有 69 个研究 run（1 总表、5 父研究、63 子评估）通过 artifact hashes、source snapshot 和 trace 审计；12 条复用记录核验原 parent/candidate/run/manifest。[审计结果](../runs/20260912T071338_839204Z_836a696a/artifact_audit.json)

## TEST RESULT

- Focused tests：13 项新增行为测试及 4 项受授权变化影响的测试通过；只补包络、几何分析、解析长度、形状证据和研究复用路径。
- 最终 full suite：**133 tests / 135.982 s / OK，退出码 0**，设置 `SOFTROBOT_TEST_MATLAB=1`；本轮仅执行一次完整回归，通过后未重复。[原始日志](../runs/20260912T071338_839204Z_836a696a/full_suite.log)
- 真实 MATLAB/MuJoCo：五组正式研究完成；原基线 M1 `0.08714456960728613`、MuJoCo `0.17116166894090315`、TASK_FAILED 精确保持。

## ROUND 3 EXIT DECISION

**PHYSICS_MODEL_REFINEMENT_REQUIRED**。解析长度处 M1 误差约 4.62e-8 m，实际误差仍为 0.123319 m；最佳联合设计仍有 0.102345 m 的模型/仿真 tip 差异；segments 改变同时造成质量和结果变化。这些证据足以安排物理模型细化，但不足以确认单一失败机理。

## NEXT PHASE

1. 提交 Human 审核的 PhysicsContract 细化方案：质量/惯量、材料/EI 与段长、body radius 的一致映射；本轮不实现新规律。
2. 在获批合同下做受控的驱动与形状校准，区分几何假设、单向拉力驱动、被动力学和跟踪误差的贡献。
3. 定义获批的形状/跟踪/离散化验收标准后，复用本轮代表设计重评；随后再决定扩大设计搜索或研究新控制路线。
