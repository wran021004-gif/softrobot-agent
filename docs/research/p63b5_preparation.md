# P6.3-B5：Native 数学入口修复与独立 M 准备

基线 `b1e51c1579ef88e56c323da9a2283ca3a3d360e1`，独立分支
`codex/p6-3b5-native-math-entry`。只完成离线修复与工程输入准备，未执行真实 Provider、
数学或物理 Worker，未继续 B4 M、未重算 M0。MuJoCo 数值始终是仿真参考，不是实物真值。
[原始失败输入、精确配置、初始化引用、账本及代码绑定](p63b5_preparation_audit.json)。

## B4 原始失败与交接

已阅读 [B4 结果](p63b4_live_results.md)、[M 审查 JSON](p63b4_m_live_audit.json) 和
[M0 原始结果投影](p63b4_m0_live_results.json)。原 M 第 9/10 次 Provider 请求分别为：

| 原始设置 | 原始 source | 原拒绝 | Worker |
| --- | --- | --- | --- |
| v2 pattern，margin=0.05 | candidate `d2f4fb61…bcecd1` | SAFETY_MARGIN_REQUIRES_RESPONSE_METHOD | 未启动 |
| v2 response，margin=0.05 | 同一个 candidate | BOUND_EXECUTABLE_CONTROL_SOURCE_REQUIRED | 未启动 |

两次其它实际设置相同：window=[0,0.6] s，knots=[0,0.2,0.4,0.6] s，coefficient_limit=2 N，
difference_step=0.01 N，initial/minimum_radius=0.1/0.0001 N，callbacks=24，iterations=3。
审查 JSON 保留两个完整 raw_main_input、原 binding/input/feedback 引用和错误对象。
第一次完整 AnalysisRequest 验证失败；第二次完整 Contract 通过后被来源准入拒绝。
没有 initialize_control，也没有数学数值结果，不能归为求解失败或无解。

原调用关系：research_plan(initialize_control) 在 core.dispatch 中调用 seed_control；baseline 分支
生成整段冻结 ZOH 网格、检查原 binding，保存 explicit_control_schedule_v1 并返回 candidate/source。
AnalysisRequest 只验证引用形状；analysis.dispatch 再验证 source 类型、来源和原 schedule binding。
结构 candidate 可以通过引用形状验证，但不能作为可执行序列。

selected_analysis() 只接受**最近完成**的 diagnose，且选择候选/方法一致。初始化 Plan 会取代最近
diagnose，因此必须重新提交 diagnose；不能沿用旧分析交接。现在 T1 行动视图、source 与 baseline
字段的 Schema 说明，以及初始化完成后的 L0 都说明此步骤。Operator 准备直接调用同一个
seed_control baseline 实现，不伪造 Main Plan，所以新 M 启动时仍由 Main 首次自主 diagnose。

## 最小修改与离线验证

生产修改只在 contracts.py、task_constraints.py、research_context.py、agent.py：说明 candidate 是
结构，source 是完整可执行序列；展示原 initialize_control 入口、实际已登记 source 和重新 diagnose
要求；明确 pattern 的 margin 必须为 0，正 margin 要求兼容 v2 response；明确 correction_window_s
允许修改控制，不是 Reach/Hold 的评分保持窗口。T1 仍只允许原冻结初始工作点。

没有新增 Planner、代选方法/参数/方向、求解器、计算接口或来源检查；数学内核、模型、冻结任务、
原准入和预算规则均未修改。完整 Schema 与实际 Provider Schema 均从原 Contract 产生。

新增三项必要用例，复用原 B3/B4 与 Mock HTTP 测试设施：

1. 新的合法当前 Study 候选误作 source，被原来源检查拒绝；原 baseline source 通过 candidate/task/
   channel/time/bounds 绑定及 Native applicability，到原 Store.reserve 入口前截停，未预留或计费，未启动 Worker。
2. 验证 pattern/response 与 margin 的合法组合及原准确拒绝码；实际 Mock HTTP 验证 T1 行动视图、
   工具 Schema、diagnose → initialize_control → 再 diagnose 的交接及完整请求绑定。
3. 独立准备 Store 只含一个 Operator 候选和一个 Operator 初始化 source；无 Main Plan、数学结果、
   独立评价或正式授权。正式授权检查仍明确拒绝执行。

原定向组合 **9/9 通过（80.986 s）**。后续针对最终 T1 工作点说明及行动视图实际 wire 投影的
单项复核结果见审查 JSON。Mock 的 RequestBoundaryHandoff 日志是原请求边界控制信号，测试通过；
所有 wire 请求都是脚本夹具，不能记为 Main 真实决策。原 NativeModel 构造和 contained Worker
边界均被测试哨兵禁止。git diff --check 通过。

## 新 M 的精确准备

[配置](../../configs/research/study_p63b5_m_native_sol_prepared.json)，原准备脚本
`tests/research/p63b5_prepare.py`。实际独立 Store：
`runs/research/p63b5-m-native-sol-20261029`（本 worktree 内，完整 Store 不提交）。

| 字段 | 准备值 |
| --- | --- |
| Study | p63b5-m-native-sol-20261029 |
| Resolved identity | a1ae8242263061e3701270b55d29c6327b424b0dfd4e6fa6fefee1e506caa127 |
| 结构 | 原生成器 baseline，2 段/4 腱，每段 12 cells，任务未评价；candidate `5ea5e8f8ff70825d07d756cc666cdd3388b51cefdd678cc5cebcd3298a171b04` |
| 控制 | 原 seed_control(method=baseline)，source `4d5721137c201c7667ef2dedb8bcb10d5c5a253cfb51756feec3964aba6de956` |
| 网格/边界 | 0–0.6 s，period=0.02 s，31 时点/30 区间，tendon_0…3，各 0.2 N，边界各 [0,8] N |
| Provider | gpt-5.6-sol，reasoning=none，最多 12（含 Reporter、失败和 1 次保护收尾） |
| 数学 | 共享 4；每请求 callbacks≤24、iterations≤3、knots≤4 |
| 公共操作 | 32，含 2 次保护操作 |
| 独立物理 / NMPC / RL / NLP / BDF | 全 0 |
| Knowledge | 保留原九项 success_case 和 procedures 可读；未注入正文、未导入历史结果 |

结构 artifact 的 provenance.decision_owner=Operator。控制保留原不可变 source.provenance、
operation_key=`operator-p63b5-initialize-control`；另保存独立 Operator 来源凭据
`7cc3d605fd2035bbbc41d4518c345c98b8b6b19c0682353bce23f996103f5fd8`，精确关联 candidate、source、
原初始化请求与实现。二者都是工程输入，task_acceptance=unmeasured，不是 Main 原创科研成果。
canonical task identity 与完整 configuration task hash 的不同用途及精确值分别保留在审查 JSON；
原 binding 使用完整 task/model/design/channel/grid/bounds，未替换为简化身份。

Main 自主选择假设、适用的已注册 Native 机制分析、固定输入结构响应或非线性任务能力方法及后续
方向，无预设执行顺序。研究数值仅使用直接 MuJoCo Native 动力学、矩阵及 rollout，不以 GVS、
SoRoSim、降阶或学习代理预测替代。原控制配置中的模型/执行身份元数据不充当数值证据。
Native 构建、rollout、callbacks、积分步及 wall time 仍按原规则完整计账，独立物理=0 不代表免费积分。

当前真实 Store：Provider=0，数学评价/结果=0，独立物理=0，Main Plans=0，pending=null，正式授权与
live_handoff_admission 均为 0。准备 numerical_s=0.482425，其中 control_initialization_s=0.130848，
没有将工程开销抹为零。实际代码绑定沿用原 core.bind，准确 freeze/回执记录在审查 JSON。
Provider/网关实时可用性和修复后 Main 行为未验证；不做 models GET 或 smoke 推理。

## M0 可复用字段及数值局限

本轮只阅读原 M0 JSON，不重算、不复制到新 M。原结果 reference 为
`6a8dc5fa66a43114455b9a7836e3644fbad41d781012e8533dd7acd609f055b0`，中心后处理为
`467dda548089bbaf898c248a2483d46773bda050048f5bc63b3d84f878fcb8b1`。
可复用原 Native 五项 mechanics 字段：

| 字段 | 原单位 |
| --- | --- |
| mass_matrix_kg_m2 | kg·m² |
| tip_jacobian_m_rad | m/rad |
| tendon_jacobian_m_rad | m/rad |
| tip_acceleration_input_map_m_s2_n | m/(s²·N) |
| passive_tip_acceleration_contribution_m_s2 | m/s² |

原路径为 `/native_dynamics/structure_baseline/mechanics/<field>`、
`/native_dynamics/structure_responses/{0,1}/mechanics/<field>` 和各侧
`mechanism_changes/<field>/finite_difference_per_parameter`。保留有符号完整矩阵、实际参数差、
坐标/通道/输入/初始态和单位；中心割线 `(F_plus-F_minus)/(p_plus-p_minus)` 不能用范数替代方向。

原 M0 仅在 length=0.160±0.001 m、零 qpos/qvel、各通道 0.2 N、0.01 s 的一次 h 下计算。
质量矩阵条件数约 3.17e6–3.22e6；内部质量平衡残差约 5.97e-16 N·m 不是敏感性误差界或硬件精度。
腱 Jacobian 和加速度输入映射的相对原量变化约 1.54e-16/9.29e-14，接近数值噪声，不能据小割线
的相对差宣称可靠方向。被动项严格是 J M^-1 qfrc_passive；其零值不是全部漂移为零，gravity bias
与总加速度需分开。一次中心割线不证明步长收敛、严格梯度、再优化结构能力或任务提升；0.01 s
端点也不是保持窗口或独立任务接受证据。未来若另行授权复用，须保留 Operator/历史所有权并通过
原 Evidence/Reporter 引用机制显式声明依赖，不能自动导入本次 M。

## 执行门槛与停止

准备不是执行授权；本轮未创建 formal_study_authorization 或 live_handoff_admission。只有另行明确
授权并按原机制登记准确 Study 范围后，才可运行原入口：

```powershell
& D:/softrobot-agent/.f3-prestudy-env/Scripts/python.exe -m tools.research run --run-id p63b5-m-native-sol-20261029 --session-handoff --max-new-provider-requests 12
```

成功分级：M1=Main 正式自主科学选择；M2=至少一次实际 Native 数学 Worker 返回可读科学结果；
M3=Main 引用该结果给出有依据的下一决策。HTTP 200、合法请求、Operator 初始控制或单独 computed
均不能冒充自主科研闭环。目前仅准备完成，未宣称新 M 达成任何等级。提交并 push 独立分支后停止，
不合并、不追加实验或预算。
