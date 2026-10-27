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

## 阶段二：计算前冻结

任务沿用 BF7 v1 三目标 `(0.285,0.035,0.185)`、`(0.275,-0.040,0.135)`、`(0.295,0,0.215)` m，seed17，同零关节位置/速度；0.6 s、1 ms 积分、20 ms 控制/采样；终点和末四样点位置 ≤10 mm、保持速度 ≤30 mm/s，原世界系、重力、安装、10 g 负载、实际 floor 掩码和 evaluator 全部不变。原 floor 可能与 payload 接触；Native 接触限制不豁免。

使用既有 BF7 R2 FamilySpace 的物理域（不是历史优化结果），两段、六腱、原截面/材料/路由、12 cells/段，0..8 N。预先选两个合法长度假设：A 为 0.16/0.12 m、B 为 0.16/0.14 m；Young 模量均为 12/10 MPa。差异是远段长度 20 mm，对几何余量与柔度的影响待验。

每组合从新鲜均匀 0.2 N 控制开始，相同 v2 response、4 knots `[0,.2,.4,.58]`、24 系数、差分 .02 N、半径 .2 N、系数上限 8 N、内余量 .02、最多 51 完整 Native 回调、2 response、一次独立回放。共至多 306 回调、6 回放、187200 积分尝试；失败/部分回调仍计费。

只有完整结果显示相对起点 J 降低至少 5%，且第二 response 的最好 J 继续下降，才选择共享 J 最小结构进行一次精化。精化决定和新 grant 在运行前另行冻结；每目标至多 201 回调、一次回放，无循环续算。公平初筛和精化单列。有限失败不证明结构不可行。

权威配置：`configs/research/bf7_native_protocol_v1.json`、`study_bf7_native_v1.json`；编排入口 `python -m tests.research.bf7_native_benchmark screen`，只调用原研究工具。阶段三后不重跑本批科学计算。
