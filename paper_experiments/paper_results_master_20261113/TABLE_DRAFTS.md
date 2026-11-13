# 论文结果表草稿（数值已整理，排版待定）

## Table I：全部Full案例

| 任务 | 原任务分类 | 结构：柔性段/腱 | required通过 | 最终结果摘要 |
|---|---|---|---|---|
| T01 多目标到达与保持 | active_reach_hold | 2 / 6 | 3/3 | 3个目标，同结构3/3通过；最大保持位置误差9.9059 mm |
| T02 带载受扰保持（M2） | loaded_hold | 2 / 6 | 3/3 | 三受力工况3/3；最大保持误差9.8971 mm |
| T03 快速到达（M3） | fast_reach | 2 / 6 | 1/1 | 0.5 s快速到达；终端误差2.1099 mm，保持最大2.6627 mm |
| T04 双叶八字轨迹跟踪 | trajectory_tracking | 2 / 4 | 1/1 | 完整22 s双周期；RMSE0.68785 mm，最大1.02066 mm |
| T05 工具位置与轴向姿态（M5） | position_orientation | 2 / 6 | 1/1 | 位置7.4585 mm；有向工具轴0.0518235 rad |
| T06 带载位置—姿态扫描（M6） | loaded_timed_scan | 2 / 6 | 1/1 | 20 g时序扫描；位置11.8198 mm；有向轴0.110448 rad |
| T07 四独立腱共同结构多任务（C1） | shared_structure_multitask | 2 / 4 | 4/4 | 同一四腱结构M1_A/M1_B/M1_C/M5全部通过 |
| T08 被动渐进刚度（P3） | task.passive_response / development_valid | 2 / 2 | 2/2 | 双方向刚度比1.63145；低载7.9281 mm，高载22.5085 mm |
| T09 复杂导向件弹簧按钮接触 | contact_manipulation | 2 / 4 | 1/1 | 深度/力联合保持0.5 s；误差0.052753 mm、0.0024651 N |
| T10 外部冲击主动恢复（M7） | dynamic_disturbance_rejection | 2 / 6 | 3/3 | 同配方required3/3，control0/2；最终最大保持误差4.1314 mm |
| PHS-2D 被动腱结构的受力点柔顺与末端抑制 | passive_shape_design | 7 / 4 | 10/10 | 十工况及半步长通过；point最小14.7981 mm，Tip最大4.3470 mm，ratio最大0.153751 |

以上是最终结果快照，不是重复试验成功率。T10 controls单列：positive_y_frozen、negative_y_frozen均FAIL。原source_classification见ALL_TASK_RESULTS；不要将开发任务提升为已注册基准。

## Table II：代表性物理量与原阈值

| 任务 / 工况 | 指标 | 观测值 | 原阈值 | 单位 |
|---|---|---|---|---|
| T02 / negative (required) | holding_position | 0.009897088402 | {"limit": 0.01, "unit": "m", "passed": true} | m |
| T02 / negative (required) | holding_speed | 0.01975728033 | {"limit": 0.02, "unit": "m/s", "passed": true} | m/s |
| T02 / positive (required) | holding_position | 0.009880943306 | {"limit": 0.01, "unit": "m", "passed": true} | m |
| T02 / positive (required) | holding_speed | 0.01972586571 | {"limit": 0.02, "unit": "m/s", "passed": true} | m/s |
| T02 / zero (required) | holding_position | 0.005357274332 | {"limit": 0.01, "unit": "m", "passed": true} | m |
| T02 / zero (required) | holding_speed | 0.01979083027 | {"limit": 0.02, "unit": "m/s", "passed": true} | m/s |
| T04 / default (required) | tracking_rmse | 0.0006878528448 | {"limit": 0.003, "unit": "m", "passed": true} | m |
| T04 / default (required) | tracking_max | 0.001020663903 | {"limit": 0.006, "unit": "m", "passed": true} | m |
| T04 / default (required) | cycle_drift | 0.001008878252 | {"limit": 0.002, "unit": "m", "passed": true} | m |
| T05 / default (required) | tool_position | 0.007458477557 | {"limit": 0.008, "unit": "m", "passed": true} | m |
| T05 / default (required) | tool_axis_direction | 0.05182348756 | {"limit": 0.05235987755982988, "unit": "rad", "passed": true} | rad |
| T06 / default (required) | tracking_max_error | 0.01181978923 | {"limit": 0.012, "unit": "m", "passed": true} | m |
| T06 / default (required) | tool_axis_direction | 0.1104481188 | {"limit": 0.17453292519943295, "unit": "rad", "passed": true} | rad |
| T08 / plus_x (required) | low_minimum | 0.007928066911 | {"limit": 0.006, "unit": "m", "passed": true} | m |
| T08 / plus_x (required) | high_maximum | 0.02250849035 | {"limit": 0.025, "unit": "m", "passed": true} | m |
| T08 / plus_x (required) | stiffness_ratio | 1.631454749 | {"limit": 1.5, "unit": "1", "passed": true} | 1 |
| T08 / plus_x (required) | residual_maximum | 6.858960175e-07 | {"limit": 0.002, "unit": "m", "passed": true} | m |
| T08 / minus_x (required) | low_minimum | 0.007928066911 | {"limit": 0.006, "unit": "m", "passed": true} | m |
| T08 / minus_x (required) | high_maximum | 0.02250849035 | {"limit": 0.025, "unit": "m", "passed": true} | m |
| T08 / minus_x (required) | stiffness_ratio | 1.631454749 | {"limit": 1.5, "unit": "1", "passed": true} | 1 |
| T08 / minus_x (required) | residual_maximum | 6.858960174e-07 | {"limit": 0.002, "unit": "m", "passed": true} | m |
| T09 / default (required) | depth_and_force_hold_0p4s | 0.5 | {"limit": 0.4, "unit": "s", "passed": true} | s |
| T10 / positive_y (required) | final_hold_position | 0.004031812003 | {"limit": 0.01, "unit": "m", "passed": true} | m |
| T10 / positive_y (required) | final_hold_speed | 0.005430562171 | {"limit": 0.02, "unit": "m/s", "passed": true} | m/s |
| T10 / negative_y (required) | final_hold_position | 0.004131381938 | {"limit": 0.01, "unit": "m", "passed": true} | m |
| T10 / negative_y (required) | final_hold_speed | 0.005565169055 | {"limit": 0.02, "unit": "m/s", "passed": true} | m/s |
| T10 / no_impulse (required) | final_hold_position | 0.004028091382 | {"limit": 0.01, "unit": "m", "passed": true} | m |
| T10 / no_impulse (required) | final_hold_speed | 0.005416475658 | {"limit": 0.02, "unit": "m/s", "passed": true} | m/s |
| T10 / positive_y_frozen (control) | final_hold_position | 0.007127696967 | {"limit": 0.01, "unit": "m", "passed": true} | m |
| T10 / positive_y_frozen (control) | final_hold_speed | 0.021582538 | {"limit": 0.02, "unit": "m/s", "passed": false} | m/s |
| T10 / negative_y_frozen (control) | final_hold_position | 0.007620003032 | {"limit": 0.01, "unit": "m", "passed": true} | m |
| T10 / negative_y_frozen (control) | final_hold_speed | 0.02535739003 | {"limit": 0.02, "unit": "m/s", "passed": false} | m/s |
| PHS-2D / s3_positive (required) | point_x_abs_m | 0.01487723293 | {"lower": 0.01} | m |
| PHS-2D / s3_positive (required) | tip_projected_m | 0.002101252389 | {"upper": 0.005} | m |
| PHS-2D / s3_positive (required) | ratio | 0.141239463 | {"upper": 0.3} | 1 |
| PHS-2D / s3_negative (required) | point_x_abs_m | 0.0147981317 | {"lower": 0.01} | m |
| PHS-2D / s3_negative (required) | tip_projected_m | 0.002138233736 | {"upper": 0.005} | m |
| PHS-2D / s3_negative (required) | ratio | 0.1444934928 | {"upper": 0.3} | 1 |
| PHS-2D / s4_positive (required) | point_x_abs_m | 0.01932879147 | {"lower": 0.01} | m |
| PHS-2D / s4_positive (required) | tip_projected_m | 0.002227899721 | {"upper": 0.005} | m |
| PHS-2D / s4_positive (required) | ratio | 0.1152632706 | {"upper": 0.3} | 1 |
| PHS-2D / s4_negative (required) | point_x_abs_m | 0.01925623206 | {"lower": 0.01} | m |
| PHS-2D / s4_negative (required) | tip_projected_m | 0.002306372611 | {"upper": 0.005} | m |
| PHS-2D / s4_negative (required) | ratio | 0.1197727886 | {"upper": 0.3} | 1 |
| PHS-2D / s5_positive (required) | point_x_abs_m | 0.02427550897 | {"lower": 0.01} | m |
| PHS-2D / s5_positive (required) | tip_projected_m | 0.002482524067 | {"upper": 0.005} | m |
| PHS-2D / s5_positive (required) | ratio | 0.1022645527 | {"upper": 0.3} | 1 |
| PHS-2D / s5_negative (required) | point_x_abs_m | 0.0242364155 | {"lower": 0.01} | m |
| PHS-2D / s5_negative (required) | tip_projected_m | 0.002657275061 | {"upper": 0.005} | m |
| PHS-2D / s5_negative (required) | ratio | 0.1096397716 | {"upper": 0.3} | 1 |
| PHS-2D / s6_positive (required) | point_x_abs_m | 0.02802856219 | {"lower": 0.01} | m |
| PHS-2D / s6_positive (required) | tip_projected_m | 0.003464990807 | {"upper": 0.005} | m |
| PHS-2D / s6_positive (required) | ratio | 0.1236235659 | {"upper": 0.3} | 1 |
| PHS-2D / s6_negative (required) | point_x_abs_m | 0.02804222097 | {"lower": 0.01} | m |
| PHS-2D / s6_negative (required) | tip_projected_m | 0.003749327485 | {"upper": 0.005} | m |
| PHS-2D / s6_negative (required) | ratio | 0.1337029435 | {"upper": 0.3} | 1 |
| PHS-2D / s7_positive (required) | point_x_abs_m | 0.02816663424 | {"lower": 0.01} | m |
| PHS-2D / s7_positive (required) | tip_projected_m | 0.003957508373 | {"upper": 0.005} | m |
| PHS-2D / s7_positive (required) | ratio | 0.1405034176 | {"upper": 0.3} | 1 |
| PHS-2D / s7_negative (required) | point_x_abs_m | 0.02827303794 | {"lower": 0.01} | m |
| PHS-2D / s7_negative (required) | tip_projected_m | 0.004346996547 | {"upper": 0.005} | m |
| PHS-2D / s7_negative (required) | ratio | 0.1537506 | {"upper": 0.3} | 1 |

完整逐工况结果及所有限制见TASK_CASE_RESULTS.csv。PHS额外保留加载/无载尾窗、残差、腱路几何、约束超长及半步长，见SOURCE_DATA/PHS2D。

## Table III：组件证据与最小对照

| 组件 | 直接证据所支持的作用 | 对照/边界 |
|---|---|---|
| Agent Reasoning | 提出物理假设、识别控制与结构耦合、否定无效分支并选择新初值。 | C1：PHS-2D Full vs Fixed-Plan |
| Task Protocol | 约束研究声明与验收范围；默认控制器不一致阻止组验收。 | 所有对照保持协议不变；不建议删除验收器作为收益消融 |
| Knowledge | 提供候选机制、适用边界和失败经验；历史成功不替代当前验收。 | C3：T04 Knowledge+Skill ON vs OFF |
| Skill | 复用结构化研究程序，规定资格门禁与独立物理验收。 | C3：T04联合关闭；单独组件效应需要额外分解 |
| Research Intent Projection | 将实际外力、有向轴和机制问题绑定到合法数学请求，保留变量/固定条件。 | C2：选择/问题组织层ON vs 同底层工具直接调用；语义投影细分尚无独立对照 |
| Mathematical Research Architecture | 组织有边界的研究问题，反馈可用性与局限，支持设计/控制/停止决策。 | C2：M2及PHS-2D Full-Selective vs Direct-Math-Tools |
| Tool Registry / Dispatch | 工具发现、适用性约束、参数路由和执行；拥有目录不等于算法有效。 | C2中两臂保留相同注册能力，避免权限差异混淆 |
| Store / Trace / Evidence | 保持研究状态与证据可追溯，区分当前同结构控制初值与旧结果。 | 记录设施两臂相同；可复现性检查不等于任务效果消融 |
| Physical Backend / Evaluator | 运行真实动力学与完整任务验收，阻止静力/局部结果被当作完整成功。 | 所有消融冻结同一后端/网格/验收；不关闭物理器来证明研究价值 |
| Budget Accounting | 记录资源使用和失败开销；部分字段不可得时不归零。 | C1/C2/C3设置相同预算；当前无预算管理独立收益对照 |
| Replay | 支持决策与调用的重建；本轮未执行任何新的端到端Replay。 | 未来固定版本重放一致性检查；不作为已完成的因果实验 |
