# BF7 MuJoCo-only：分阶段记录

本次继续已有 `research/bf7-shared-structure-benchmark` worktree，不改生产或 integration 分支。历史 v1/R1/R2 文件、失败、CONIC 费用和未完成记录保留；本轮不执行这些入口，不从 BF4/BF5/BF6 导入结构、控制或 Store。新实验使用独立 `bf7-native-v1` 账本。没有正式 LLM Agent、Provider、PPO 或 Flash/Pro 对照。

## 阶段一：现有工具审计

- `design.generate_candidate` 从冻结 FamilySpace 生成、编译合法结构并保存候选。初始化所需的 GVS 坐标/基底投影是既有候选元数据准备；不构建 GVS 动力学模型，不求 CONIC，不用于本轮结构评分。
- `conditions.condition_candidate` 从结构根绑定冻结任务、seed 和零初态，保持物理结构和网格；`physical_replay.seed_control` 为每条件创建合法绝对张力序列。
- `native_control.calculate` 使用 NativeModel 的完整时域 MuJoCo 回调和原 `local_control_search.search`。每个结构、每个条件均重新优化控制。`mujoco_direct_control_v1` 与 T1 `mujoco_nonlinear_task_capability_v1` 调用同一个控制内核；后者只额外调用 `t1_summary` 解释该次搜索，不重复积分。本轮使用 T1 入口保存可复用结果。
- `physical_replay.dispatch` 通过原 worker、Store 和预算独立重放，原 evaluator 与 Reach/Hold 组合验收决定通过。`conditions.joint_assessment` 检查三个任务的完整合法 owned 收据、读取、结构/材料/腱路/网格相同，随后原 SELECT。
- T1 是逐候选逐任务的有限预算已找到最好 signed maximum normalized excess（J），不是全局最优。共享评分是三个完整 T1 的 max；任一中断则共享评分未决，不能使用部分轨迹补齐。
- T2 `nonlinear_capability.saved_context/response` 只读取同 Store、同冻结实现/协议、相同任务/初态约定/控制设置的已有 T1。连续 secant 需三个对称结构；两个结构可用 v2 finite_comparison。多条件必须逐条件各调用一次，禁止把不同目标混入一个 T2。T2 不新建模型、不积分；不适用时直接确定性逐条件比较 Store 的原 J 和成本，不绕过门槛。
- `task_constraints` 对 Native 覆盖仅给 diagnostic，完整任务接受仍需回放。`core`、`contracts`、`research_context` 已有权限、预算、收据、恢复、方法目录和多条件展示。

实际缺口：`search.py` 的 `family_mixed_search_v1` 默认 proxy，task_violation 调 CONIC 且只用主条件；`initial_structure_strategy=math_search` 的 config 准入明确要求 CONIC。仅配置切换不能构成 Native 结构搜索。先用上述原 dispatch 组织阶段二；阶段二完成且恢复合法后再最小扩展 FamilyMixedSearch 的显式 Native 模式，保留旧序列化和历史语义。

历史 R2 收尾同时暴露 `final_fidelity_matches` 把第二、第三个正确冻结条件误判为非根任务的组合缺陷。阶段二之前修复该检查：有 condition_id 时只接受该冻结条件的 task digest；无条件仍要求根 identity，所有原 fidelity/backend/网格检查保留。定向无积分 fixture 覆盖正确条件、错任务、未冻结条件和错网格。此修复不更改 evaluator 或旧 Store，不把旧 R2 的拒绝改写为 SELECT。

## 阶段二：计算前冻结

任务沿用 BF7 v1 三目标 `(0.285,0.035,0.185)`、`(0.275,-0.040,0.135)`、`(0.295,0,0.215)` m，seed17，同零关节位置/速度；0.6 s、1 ms 积分、20 ms 控制/采样；终点和末四样点位置 ≤10 mm、保持速度 ≤30 mm/s，原世界系、重力、安装、10 g 负载、实际 floor 掩码和 evaluator 全部不变。原 floor 可能与 payload 接触；Native 接触限制不豁免。

使用既有 BF7 R2 FamilySpace 的物理域（不是历史优化结果），两段、六腱、原截面/材料/路由、12 cells/段，0..8 N。预先选两个合法长度假设：A 为 0.16/0.12 m、B 为 0.16/0.14 m；Young 模量均为 12/10 MPa。差异是远段长度 20 mm，对几何余量与柔度的影响待验。

每组合从新鲜均匀 0.2 N 控制开始，相同 v2 response、4 knots `[0,.2,.4,.58]`、24 系数、差分 .02 N、半径 .2 N、系数上限 8 N、内余量 .02、最多 51 完整 Native 回调、2 response、一次独立回放。共至多 306 回调、6 回放、187200 积分尝试；失败/部分回调仍计费。

只有完整结果显示相对起点 J 降低至少 5%，且第二 response 的最好 J 继续下降，才选择共享 J 最小结构进行一次精化。精化决定和新 grant 在运行前另行冻结；每目标至多 201 回调、一次回放，无循环续算。公平初筛和精化单列。有限失败不证明结构不可行。

权威配置：`configs/research/bf7_native_protocol_v1.json`、`study_bf7_native_v1.json`；编排入口 `python -m tests.research.bf7_native_benchmark screen`，只调用原研究工具。阶段三后不重跑本批科学计算。

## 初筛结果与精化冻结

初筛实现 `48d090311`；6 项均 51 完整回调、2 response、一次完整独立回放，原验收均 valid_failure。A/B 的逐条件 best J 为 `(6.263104,3.768657,8.126199)` / `(6.007782,4.668359,7.139580)`；共享 J 为 8.126199 / 7.139580。B 降低最坏值约 12.14%，但 negative_low 更差，未覆盖更多通过目标。共同固定 0.2 N 下 A/B 最坏 J 为 14.407247 / 16.861131：固定输入排序与重新优化后的共享排序相反。

T1 六次均 computed。T2 三次逐条件请求均明确 not_comparable：原 Study 没有额外的 `family_sensitivity_variables` 授权，报 `AUTHORIZED_FAMILY_CONTINUOUS_PARAMETER_REQUIRED`。不追加权限重解释冻结账本，不混合目标；沿用 Store 原 J、样点和成本做确定性比较。T2 实际新积分/模型构建均为零，三次分析入口和 worker 时间仍计费。

初筛实际 306 完整 Native 回调、0 失败回调、183600 Native 步，加 6×600 独立回放步，共 187200 步；Native/replay 模型构建各 6。9 分析单位，37.466073 s Store 数值，57.978254 s driver。完整结构/条件结果、原度量、成本及 T2 拒绝见 `evidence/bf7_native_v1/screen_summary.json`。

按事前规则选 B：三个任务相对起点均改善超过 5%，第二 response 全部继续改善；例如 central_high 从 16.861131 到第一轮下降后再到 7.139580。唯一精化 grant 见 `bf7_native_refinement_v1.json`：每目标最多 201 回调、8 response、一次独立回放，在新独立 Study 中从该目标自己的 B 初筛最好控制重新从零执行。最大新增 603 回调、3 回放、363600 步；不再续算。初筛成本不会并入公平对比中的 B 性能，也不会清空。

## 阶段二最终结果

| 结构/阶段 | positive_high J | negative_low J | central_high J | 独立通过 |
| --- | ---: | ---: | ---: | ---: |
| A 公平初筛 | 6.263104 | 3.768657 | 8.126199 | 0/3 |
| B 公平初筛 | 6.007782 | 4.668359 | 7.139580 | 0/3 |
| B 唯一精化 | −0.020928 | 2.340449 | −0.033223 | 2/3 |

精化三个目标实际 198、201、147 回调。通过项保持位置/速度为 9.767011 mm /29.372154 mm/s、8.774150 mm /29.003312 mm/s；失败的 negative_low 为 33.404490 mm /95.518007 mm/s，原验收 valid_failure。负侧目标在精化后成为共享瓶颈。没有三项同时通过，因此原 SELECT 不执行，两 Study 均原 STOP。精化即使还有未用额度也不扩展或重新初始化预算。

在相同初筛预算下，B 的共享 J 比 A 改善约 12.14%，但通过目标数量相同，负侧退步。固定共同输入时 B 更差，重新优化后 B 的最坏值更好：不能以固定张力结构响应替代结构能力。两个结构均完成相同 51 回调/2 response，成本接近；这只是两个长度假设、该初始化和有限算法的观察，不是统计显著性、结构因果梯度或全局结构优势。B 精化结果不用于与 A 初筛宣称公平优势。

| 新实验阶段 | Native 完整/失败回调 | 独立回放 | 实际积分步（含回放） | Native/回放模型构建 | Store 数值 s | driver s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 公平初筛 | 306 /0 | 6 | 187200 | 6 /6 | 37.466073 | 57.978254 |
| 唯一精化 | 546 /0 | 3 | 329400 | 3 /3 | 39.790388 | 55.194555 |
| 合计 | 852 /0 | 9 | 516600 | 9 /9 | 77.256461 | 113.172808 |

12 个原分析入口（6 T1 初筛、3 T2 聚合、3 T1 精化）；构建、初始化、兼容准备、Native kernel 和回放 kernel 时间在 `cost_summary.json` 分列，kernel 时间是 Store 数值时间的子集，不能再次相加。全部回调完整且无数值失败，积分尝试数等于完成步数。旧 v1/R1/R2 成本和失败仍在原历史报告/账本中，未抵扣本轮余额。工具冻结前两次干净工作区准入拒绝没有科学执行。

`receipt_recovery.json` 验证原 `core.recover`、相同 Native 请求和相同回放 Plan 的收据重用，计数/数值时间/账本完全不变；分析 guard 若被触发会直接报错，实际未触发。原 `core.export` 保存两个 Study 的完整 artifacts archive、状态、原调用收据及 ledger，路径在 `evidence/bf7_native_v1/screen/` 和 `refinement/`。阶段二因此已验证合法结构生成、逐条件优化、独立评价、确定性比较和恢复，允许接入阶段三。

本轮 MuJoCo-only 有限预算**没有新三目标可行见证**。此前 R2 已有同结构三目标分别独立通过的历史证据，但结构提案使用 CONIC、单目标预算上限 401，且当时联合 SELECT 被旧 fidelity gate 拒绝；它不作为本轮 MuJoCo-only 成功或公平结构收益。旧文件与旧拒绝保持原义。
