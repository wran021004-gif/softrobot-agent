# 结构与决策变化索引

原始逐字段结构差异见CANDIDATE_EVOLUTION.csv；PHS原始九候选及模型见SOURCE_DATA/PHS_CANDIDATE_INDEX.csv。下表仅保留真正改变研究方向或确定可行性的节点。Hypothesis列为原rationale的编辑性概括，作用解释不等于已完成因果实验。

## T01 多目标到达与保持

最终：3个目标，同结构3/3通过；最大保持位置误差9.9059 mm。

| 节点 / 候选 | 观察及假设 | 决策与后果 |
|---|---|---|
| T01-116 / 原始ID见CSV | 密集腱速约束阻碍到达与停稳。 缩小合法腱路半径可降低同样运动引起的腱长变化。 | 采用较小合法半径，保留完整执行器验收。 后续14 mm边界设计仍有0.199%腱速超限，转向增加可达余量。 |
| T01-127 / 原始ID见CSV | 最小合法半径和完整控制网格仍有0.199%峰值腱速超限，位置在10 mm边界。 增加总柔性长度5 mm可能缓解近伸直目标下的位置—制动冲突。 | 两段各增2.5 mm，后续工况必须共用新结构。 最终162.5/112.5 mm共同结构通过3/3工况。 |
| T01-159 / 原始ID见CSV | 正向工况从原初值搜索停滞。 当前同结构中央工况的平滑张力序列可提供不同控制初始盆地。 | 仅迁移当前控制输入，再按正向原任务重新求值。 最终同结构central_high、negative_low、positive_high全部通过。 |

证据：KEY_RESEARCH_NODES.csv中的evidence_reference，以及SOURCE_DATA/SELECTED_RESEARCH_EVENTS.json中的决策和相邻原始正式请求。

## T02 带载受扰保持（M2）

最终：三受力工况3/3；最大保持误差9.8971 mm。

| 节点 / 候选 | 观察及假设 | 决策与后果 |
|---|---|---|
| T02-004 / 原始ID见CSV | 静力/GVS构造不能覆盖实际外部受力的完整任务。 应在包含真实外力的原生有限时间动力学中优化控制。 | 转向实际受力下的原生控制响应方法。 14 MPa候选仍呈现位置—制动冲突，随后调整刚度。 |
| T02-018 / 原始ID见CSV | 当前14 MPa结构在有限控制搜索中停滞。 降低刚度可在保留执行器约束下增加带载可达性。 | 进行有界刚度比较并独立检查三种受力工况。 12 MPa共同结构三工况通过；最大保持误差9.8971 mm。 |

证据：KEY_RESEARCH_NODES.csv中的evidence_reference，以及SOURCE_DATA/SELECTED_RESEARCH_EVENTS.json中的决策和相邻原始正式请求。

## T03 快速到达（M3）

最终：0.5 s快速到达；终端误差2.1099 mm，保持最大2.6627 mm。

| 节点 / 候选 | 观察及假设 | 决策与后果 |
|---|---|---|
| T03-005 / 原始ID见CSV | 静力目标输入不证明0.5 s快速到达及0.45–0.5 s保持。 必须同时搜索快速运动、末端制动与密集执行器约束。 | 在原生完整动力学中搜索后独立验收。 终端误差2.1099 mm，保持最大误差2.6627 mm，正式工况通过。 |

证据：KEY_RESEARCH_NODES.csv中的evidence_reference，以及SOURCE_DATA/SELECTED_RESEARCH_EVENTS.json中的决策和相邻原始正式请求。

## T04 双叶八字轨迹跟踪

最终：完整22 s双周期；RMSE0.68785 mm，最大1.02066 mm。

| 节点 / 候选 | 观察及假设 | 决策与后果 |
|---|---|---|
| T04-010 / unavailable | 历史单段0.27 m几何不满足当前根段设计域。 历史准静态跟踪思路可以迁移，但必须重新构造合法两段结构与初态。 | 保留冻结连接和2 g负载，构造总长0.258 m的合法两段候选。 后续原GVS控制路线未取得完整成功，转向原生平衡点组。 |
| T04-216 / unavailable | 89点平衡组由全4 N初值触发非法优化试探，未生成可用组。 局部已知平衡初态和内点预张力可避免边界与全局初值问题。 | 使用当前t0平衡，仅将0.2 N项内移至0.21 N，保留原生守卫。 生成89点平衡组；静态最大位置误差0.6110 mm。 |
| T04-220 / 原始ID见CSV | 静态组可用仍不能保证22 s双周期动态轨迹通过。 独立初态资格加周期张力前馈可能满足完整路径和执行器约束。 | 独立执行原22 s任务，不以静态优化终止状态代替验收。 完整22 s通过；RMSE0.68785 mm，最大误差1.02066 mm。 |

证据：KEY_RESEARCH_NODES.csv中的evidence_reference，以及SOURCE_DATA/SELECTED_RESEARCH_EVENTS.json中的决策和相邻原始正式请求。

## T05 工具位置与轴向姿态（M5）

最终：位置7.4585 mm；有向工具轴0.0518235 rad。

| 节点 / 候选 | 观察及假设 | 决策与后果 |
|---|---|---|
| T05-005 / 原始ID见CSV | 位置静力构造不适用于有向工具轴的完整约束。 需在实际局部轴到世界轴变换下联合优化位置与轴向。 | 采用原生直接控制响应，保留10 g真实工具COM及完整惯量。 位置7.4585 mm、轴向0.0518235 rad，两类约束同时通过。 |

证据：KEY_RESEARCH_NODES.csv中的evidence_reference，以及SOURCE_DATA/SELECTED_RESEARCH_EVENTS.json中的决策和相邻原始正式请求。

## T06 带载位置—姿态扫描（M6）

最终：20 g时序扫描；位置11.8198 mm；有向轴0.110448 rad。

| 节点 / 候选 | 观察及假设 | 决策与后果 |
|---|---|---|
| T06-004 / 原始ID见CSV | 带时序的20 g负载扫描不能用单目标静力或位置指标代表。 完整非对角惯量和有向轴时序应共同进入原生响应。 | 搜索原0.6 s位置—轴向序列并独立执行。 最大位置误差11.8198 mm、轴向0.110448 rad，原任务通过。 |

证据：KEY_RESEARCH_NODES.csv中的evidence_reference，以及SOURCE_DATA/SELECTED_RESEARCH_EVENTS.json中的决策和相邻原始正式请求。

## T07 四独立腱共同结构多任务（C1）

最终：同一四腱结构M1_A/M1_B/M1_C/M5全部通过。

| 节点 / 候选 | 观察及假设 | 决策与后果 |
|---|---|---|
| T07-060 / 原始ID见CSV | 历史几何通过B，但A仍约10.6%超限，C接近可行。 圆形8 mm根段可同时改变质量、刚度和跨平面耦合；不是单因素导数。 | 检验圆形根段，保留长度、材料、路由及四个独立输入。 A超限降至0.875%，再测试长度与路由。 |
| T07-074 / 原始ID见CSV | 分布增长162.5/112.5 mm使A超限增至4.40%。 返回最佳158.5 mm根段并将路由14.1→14 mm可能降低剩余腱速冲突。 | 放弃较长方案，采用合法边界路由，全部工况重新验收。 当前结构A独立通过，随后B与有向轴M5通过。 |
| T07-106 / 原始ID见CSV | 同一硬件A/B/M5通过，C从历史控制盆地仍超限4.11%。 采用当前A控制作为输入初值可能突破C的局部搜索停滞。 | 保留共同硬件，仅用当前A张力序列重新优化C。 同一四腱结构最终4/4原工况通过。 |

证据：KEY_RESEARCH_NODES.csv中的evidence_reference，以及SOURCE_DATA/SELECTED_RESEARCH_EVENTS.json中的决策和相邻原始正式请求。

## T08 被动渐进刚度（P3）

最终：双方向刚度比1.63145；低载7.9281 mm，高载22.5085 mm。

| 节点 / 候选 | 观察及假设 | 决策与后果 |
|---|---|---|
| T08-006 / 原始ID见CSV | 1.5 mm放绳偏置候选刚度比约1.367，小于冻结1.5要求。 在同一二段二腱结构中将偏置改为1.8 mm可改变高载招募区间。 | 对称调整固定放绳偏置，不更改载荷和验收阈值。 双方向刚度比1.63145475；低载7.9281 mm，高载22.5085 mm。 |
| T08-009 / 原始ID见CSV | 核心指标通过尚需冻结协议的成对机制及复核。 去除腱限位的配对试验与半步长/初态扰动可检查响应来源和稳定性。 | 采用已有独立双方向与机制复核结果作最终依据。 双方向最终通过；保留task.passive_response / development_valid分类。 |

证据：KEY_RESEARCH_NODES.csv中的evidence_reference，以及SOURCE_DATA/SELECTED_RESEARCH_EVENTS.json中的决策和相邻原始正式请求。

## T09 复杂导向件弹簧按钮接触

最终：深度/力联合保持0.5 s；误差0.052753 mm、0.0024651 N。

| 节点 / 候选 | 观察及假设 | 决策与后果 |
|---|---|---|
| T09-210 / 原始ID见CSV | 实际导向孔/支架必须保留质量、COM、惯量；初次接触策略错误重启了附件碰撞。 应修复附件接触保真，不能删除真实导向结构换取通过。 | 构造包含20个真实孔/支撑总成的候选并修复接触策略。 后续完整独立按钮任务通过。 |
| T09-213 / 原始ID见CSV | 修复模型后仍需完整按压、保持和释放任务确认。 包含真实附件的接触响应可满足0.5 s深度/力联合保持。 | 独立执行完整任务，保留负载与接触要求。 深度最大误差0.052753 mm、力误差0.0024651 N，释放接近零。 |

证据：KEY_RESEARCH_NODES.csv中的evidence_reference，以及SOURCE_DATA/SELECTED_RESEARCH_EVENTS.json中的决策和相邻原始正式请求。

## T10 外部冲击主动恢复（M7）

最终：同配方required3/3，control0/2；最终最大保持误差4.1314 mm。

| 节点 / 候选 | 观察及假设 | 决策与后果 |
|---|---|---|
| T10-017 / 原始ID见CSV | 原GVS/NMPC路线存在保持、腱速/行程冲突。 必须先诊断原生启动/制动，不应把开环目标到达当作冲击恢复。 | 采用原生启动试验检查完整约束，后续切换状态反馈路线。 历史失败促成原生状态反馈方法选择；最终三required通过。 |
| T10-210 / 原始ID见CSV | 需原M2硬件、共同控制器和对外部脉冲未知的反馈执行。 静力参考、完整原生切线、离散LQR与有界张力分配可形成恢复控制。 | 每次执行重新计算参考与增益，并冻结共同配方。 早期组因默认参数不一致被拒；最终修复后全部五工况同配方。 |
| T10-222 / 原始ID见CSV | 正/负脉冲与无脉冲必须共用控制器，冻结控制只作为control。 共同反馈应在原±Y半正弦脉冲后满足完整保持窗。 | 执行同配方三required及两frozen control，不向控制器提供脉冲时刻。 required3/3通过，frozen control0/2；最终最大保持误差4.1314 mm。 |

证据：KEY_RESEARCH_NODES.csv中的evidence_reference，以及SOURCE_DATA/SELECTED_RESEARCH_EVENTS.json中的决策和相邻原始正式请求。

## PHS-2D 被动腱结构的受力点柔顺与末端抑制

最终：十工况及半步长通过；point最小14.7981 mm，Tip最大4.3470 mm，ratio最大0.153751。

| 节点 / 候选 | 观察及假设 | 决策与后果 |
|---|---|---|
| N01 / F0 | F0 继承的默认长度和松弛腱使该结构仅能诊断，不能记为正式任务候选。 Correct only the declared interface version to match the existing frozen V2 generator / Use actual unilateral active sets and core local QP response before choosing payout, material or route changes / Read existing construction facts rather than recomputing them or assuming catalogue defaults were applied | 检查实际继承参数；F0 仅作诊断，转向精确腱长及显式长度输入。 F0 实际总柔性长度 270 mm；四腱均不活跃，张力均为 0；最小松弛裕量 121.905190 mm。 |
| N02 / F1 | 腱被激活后仍存在明显 Tip/受力点耦合；局部约束有效不等于输出被隔离。 Correct the input station cardinality without changing the scientific hypothesis / Create a physically installed constrained baseline rather than tune inactive tendon parameters / Distinguish constraint activation and motion transfer before full finite-load evaluation / The compact scalar norm omits tip/point ratio and must not be treated as a task score | 四腱从同一基座经过实体导向；局部单侧响应仍把 Tip 与受力点强耦合，改变杠杆分布。 F1 在 s=.3、+0.001 N 局部 QP 的 Tip/point=1.799204135。 |
| N03 / F2 | 局部 0.001 N 预测不能代替任务 0.1 N、8 s 有限过程。 Change the constraint transfer mechanism and test a falsifiable joint design, using only current F1 evidence and declared bounds / Freeze the actual independently proposed F2 design under current Store ownership / Test the proposed mechanism with actual unilateral QP and qualification, not an imagined Jacobian / Preserve distinction between mechanism and task score | 局部小增量响应改善，进入有限 0.1 N 载荷验证。 F2 同一局部增量比值=0.151812211；+0.1 N 有限载荷 Tip=4.773199 mm。 |
| N04 / F2/F3/F4 | 漂移变小不能单独建立力平衡；F2/F3/F4 加载尾窗均失败。 Finite tendon slack and nonlinear response can invalidate a local QP; test one informative search case before all six, with holdouts untouched / Follow the real object schema; retain the failed read instead of inventing a result / Matched finite-time test addresses the failure that static KKT and local compliance could not assess / Compare actual measurements, retaining partial-task coverage explicitly / Use fresh finite-time physics to test continued damping benefit versus slower relaxation / Do not extrapolate the viscosity trend without fresh evidence | 黏性调整未能单独解决尾窗残差；放弃单纯增加阻尼的解释。 s3+：F2/F3/F4 尾窗漂移依次 0.693135/0.255104/0.061843 mm；静力残差依次 0.00369426/7.53479e-05/0.00370682 N m。 |
| N05 / F3 | 局部优势未延续到远端有限载荷；几何诊断给出明确实体和跨度，支持改变导向拓扑。 Test one unmeasured informative search load before spending on complete invalid coverage or another damping value / Choose geometry revision using actual spatial violations, with unseen loads excluded / Inspect raw episode schema before selecting route-safety child fields; avoid silently relying on a partial evaluator | 远端响应与局部预测不一致，且腱路穿柔性单元；改用更密集实体导向。 F3 s7+ Tip=72.291259 mm，ratio=0.8714539251249074；初始腱 0/span 2 穿 segment_2_cell_4。 |
| N06 / F5 | 按实际连接件 6 mm 半包络和腱半径处理安装净空；此阶段同时改变质量/间距，不能声称单因素因果。 Respond to actual finite-transfer and installation failures, rather than continue viscosity-only tuning / Instantiate the route-safety and finite-transfer hypothesis through the official Store generator / Two informative extremes test whether the geometry revision addresses the actual failures before all six search loads / Separate measured geometry, settling and displacement causes rather than combine them into an unexplained score / Use the actual collision body/span and physical envelope to choose clearance, not a visual impression | 七段方案仍穿 connector_6；按真实包络调整连接间隙和导向偏置。 F5：7×40 mm、6 个导向板；初始腱 0/span 5 穿 connector_6；s7+ Tip=16.615233 mm。 |
| N07 / F6 | 低传递比仍可能超出绝对 Tip 5 mm；实测受力点 >10 mm 给刚度调整提供了依据。 Use actual geometric and response failures to choose a new joint candidate, not a copied historical design / Materialize actual corrected clearance, lever shape and material distribution / Correct only data shape and preserve failed request; no solver or threshold change / Excellent row matching is still only a mechanism proxy; repeat the same two physical search extremes to test finite realization / Read actual performance instead of inferring it from C047 low local row residual / Geometry must be checked independently before spending another material comparison | 合法腱路及尾窗通过后仍有 Tip 超限；利用实测受力点裕量提高模量。 F6 s3+ point=17.082564 mm；s7+ Tip=6.389832 mm；两工况几何/加载尾窗通过。 |
| N08 / F7 | 正负载荷不必对称；负向近失效与受力点裕量支持最后一次材料调整。 Use measured near-motion margin for a matched stiffness change, rather than altering the successful route/settling mechanism / Check sign asymmetry and the intermediate search point before spending the held-out final validation / Read sign-specific actual components before freezing candidate and exposing holdouts | 负向远端 Tip 仍超限；保留几何、放绳和黏性，仅调整分段模量。 F7 六工况中 s7- Tip=5.161427 mm >5 mm；其余五个搜索工况性能通过。 |
| N09 / F8 | 完整受测证据支持进入留出验收；冻结发生在留出结果之前。 Use measured sign asymmetry and available compliance margin for one further matched stiffness change; no holdout tuning / The previous near-pass cannot be accepted; repeat both signs and intermediate search load at the exact new candidate / Check all measured bounds and tails before exposing held-out conditions / A complete raw episode audit prevents repeating the earlier partial-metric geometry oversight / Bind the final design and import only the task-definition source required by official independent replay; no historical candidate or score import | 冻结候选及任务；s=.4/.6 四个留出工况此前不用于调参。 F8 六个搜索工况均通过性能、尾窗与保存姿态几何检查；C059 冻结 candidate=6115d7d91892f91e5dde3faa5878463c105a9e4049c4d07e8872d0cecc2738b4。 |
| N10 / F8 | 当前 Store 的完整注册验收证书与新物理进程轨迹共同支持数值通过；不转移历史验收。 Only an independent complete frozen-task evaluation can establish the task-level result; no mathematical proxy or archived success transfers acceptance / Export the exact owned structure for review while independent validation proceeds; this read does not depend on holdout outcomes / Use the complete formal acceptance view, not a success flag or selected metric excerpt, for final claims | 原冻结任务独立进程完成十工况并通过；停止搜索。 10/10 accepted；point_min=14.798132 mm，Tip_max=4.346997 mm，ratio_max=0.153750600；352000 步。 |
| N11 / F8 | 只改变数值步长与验证元数据；两个步长不能建立普遍收敛或初态鲁棒性。 Verify existing numerical-confirmation capability instead of assuming it or developing a substitute; no execution until nominal acceptance / Independent physical ownership requires actual construction in the verifier, not imported trajectory or acceptance / Prove that numerical confirmation changes only timestep/metadata, and supply the exact frozen task source required by official replay / Complete the existing-core-supported timestep check after stopping search, with no new solver, private-state injection or acceptance change / Close numerical confirmation using the full formal view rather than a compact accepted flag | 只改变步长与验证元数据；当前结构十工况复核通过。 dt=0.0625 ms、10/10 accepted、704000 步；Tip_max=4.346996552 mm。 |

证据：KEY_RESEARCH_NODES.csv中的evidence_reference，以及SOURCE_DATA/SELECTED_RESEARCH_EVENTS.json中的决策和相邻原始正式请求。
