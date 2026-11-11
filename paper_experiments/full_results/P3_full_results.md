# P3 Full：被动渐进刚度

Study：`p3-passive-progressive-stiffness-autonomous-20261110-v1_2`。Main 已找到可行数值设计 `candidate_2915`，完成双方向五阶段响应；记录的核心任务指标满足对应数值阈值。本文件复用既有结果，不进行新的独立验收或资格审查。

## Task Description

机器人采用固定 payout 的单向腱约束，没有主动控制。+X、-X 各执行 20 s：无载、0.05 N、0.10 N、0.20 N、卸载恢复，各阶段 4 s。物理步长 0.000125 s，记录周期 0.01 s，各阶段最后 0.25 s 为评分窗。位移观察点为材料坐标 `s=0.7`，相对无载均值取受载方向位移，不能与末端位移混用。

要求包括低载位移 ≥6 mm、高载位移 ≤25 mm、恢复残差 ≤2 mm、中—高与低—中区间刚度之比 ≥1.5，以及方向性同腱 slack-to-taut、无接触等检查。原协议另含阶段资格及成对机制/独立验证要求，结果边界在文末保留。

## Initial Research Hypothesis

Main 从三段、四条等角全长腱和有限对称放线余量出发，假设低载时腱保持松弛，较高载荷招募对应方向腱，从而兼顾低载柔顺与高载承载。先检查卸载平衡/活动集，再研究完整动态响应，避免用一个局部平衡替代整段加载性能。

这项具体结构与研究路线由 Main 选择；单向腱不能推、固定 payout 属于约束、活动集和有限动态需要分别验证等原则已存在于 Knowledge。本案例不把这些历史知识写成 Main 首次发现。

## Mechanism Analysis

实际工具检查了卸载局部平衡、单边约束活动集、腱松弛间隙与张力，以及有限加载过程中的位移、恢复、阶段沉降和接触。Main 据此区分了“延迟招募”“高载刚度不足”和“动态沉降不足”，再改变研究方向。

初始候选高载位移约 44.734 mm；增加放线余量虽恢复延迟招募，高载位移仍约 46.506 mm、刚度比约 1.07553。这削弱了仅调整招募时机即可达标的假设，促使 Main 研究截面、路由、材料与惯性的组合影响。

## Mathematical Research

| 实际能力 | 已保存使用情况 | 解释边界 |
|---|---|---|
| `mechanism_structure_v1 / inspect` | 45 份结果；含卸载活动集/KKT 和有限时间响应 | 局部静态条件不保证完整动态性能 |
| `compare` | 3 份结果 | 有限候选对照，不自动是单变量因果证明 |
| `interact` | 2 份结果，均为 `matched_two_parameter_four_point_v1` | 有限尺度交互；`strict_derivative=false` |
| `optimize` | 1 份结果；黏性单坐标 4 次有限评价、8 个方向 episode | 实际为 `bounded_directional_comparison`；导数未定义、改善不可比较，不能称成功梯度下降 |
| 有界结构搜索 | 7 份搜索结果，`bounded_mixed_coordinate_v1` | 搜索器内部提案与 Main 手工设计区别计述 |

51 份分析结果与累计 67 次数学评价是不同计数口径。两次交互分别研究 `payout_offsets_m.tendon_1 × spans.0.radius_m`，以及远段密度 × 截面半径。它们提供实际双参数分析基础，但不证明专门的 Coupled Block 求解器被执行；该工具的实际使用为 UNKNOWN，不能由配置授权推断。

## Structural Design Iterations

| 阶段 | Main 的假设与实际修改 | 工具观测及后续决策 |
|---|---|---|
| 初始三段四腱 | 3×0.10 m、圆半径 6 mm、E=7 MPa；全腱放线余量 1.0→1.5 mm | 延迟招募得到改善，高载位移和刚度比仍不达标，转向几何/路由搜索 |
| 截面、路由、阻尼 | 有界搜索得到 `candidate_920`：半径 8 mm、较大弯曲黏性及调整后 payout | 低载约 7.445 mm、高载约 21.890 mm、刚度比 1.56877；低载/恢复阶段仍有动态资格问题 |
| 质量分布与局部交互 | 增截面降 E、非均匀材料/截面、放线—路由交互；段长改为 0.11/0.10/0.09 m；探索分布锚点 | 多项改动没有消除全部沉降问题；不能把 Main 的近似 EI 或惯性解释直接当作工具已证明的定律 |
| 三段→四段 | 初次 4×0.075 m 含连接件后超长，构造失败；随后 4×0.072 m 的 `candidate_1775` 合法生成 | 刚度比约 1.64549，沉降仍需改善；四段成为继续细化的可用架构，未证明段数单独决定收益 |
| 缩短与减惯性 | 段长降至 0.068 m、E 降至 6 MPa；继而半径 8→6.5 mm、E 升至 13.77 MPa；继续调整密度、长度与放线 | `candidate_2132` 恢复残差约 18.406 μm；后续缩短进一步改善沉降，同时需保持低载柔顺及渐进刚度 |
| 最终权衡 | 4×0.058 m、E=10.26 MPa 的刚度比仅 1.48388；路由和 payout 细调恢复刚度比，却仍有低载位移缺口 | 最后四段 E 联合降至 10.10 MPa，形成 `candidate_2915`，记录指标同时达标 |

实际可辨的主要架构变化是三段变四段，并探索了腱跨度/锚定路由。初始和最终均为四腱；现有汇总不足以声称发生过一条特定的腱数优化链。四段四腱是沿这条实际搜索路径保留下来的可行组合，不是对所有段数、腱数的全局最优证明。

## Final Candidate

| 参数 | `candidate_2915` |
|---|---:|
| Flexible Segments | 4 |
| Tendons | 4 |
| 每段长度 | 0.058 m |
| 圆截面半径 | 0.0065 m |
| 每段 Young's Modulus | 10.10 MPa |
| 密度 | 1000 kg/m³ |
| 弯曲黏性（两弯曲轴） | 0.0007 N·m²·s |
| 每腱 Fixed Payout | 0.27522 m |
| Cells per Segment | 2 |

最终一步仅将四段 E **同时由 10.26 MPa 降至 10.10 MPa**，保持几何、payout、阻尼、密度、拓扑和原协议。该结果属于联合材料参数块修改，不能将收益归于某个特定段。完整路由、连接件及安装信息仍以保存候选为准，以上表格不是完整重建规格。

## Bilateral Physical Response

| 指标 | +X | -X | 原数值要求 |
|---|---:|---:|---|
| Low displacement | 6.01794 mm | 6.01794 mm | ≥6 mm |
| Middle displacement | 11.11727 mm | 11.11727 mm | 机制记录点 |
| High displacement | 17.75103 mm | 17.75103 mm | ≤25 mm |
| Recovery residual | 0.001246 mm | 0.001246 mm | ≤2 mm |
| Progressive stiffness ratio | 1.537391 | 1.537391 | ≥1.5 |
| Contact | 0 | 0 | 0 |

恢复残差 0.001246 mm 约为 1.246 μm。低载位移裕量仅约 **17.94 μm**。区间刚度约为低—中 9.80520 N/m、中—高 15.07442 N/m。双方向均完成五阶段，保存的采样窗口检查及全程路由检查支持该数值设计的可执行性。

## Progressive Stiffness Mechanism

+X 下 tendon_3、-X 下 tendon_1 分别表现为同一腱的低载松弛、高载张紧：低载张力为 0，低载最小松弛间隙约 0.485682 mm；高载最小张力约 0.422375 N、活动比例为 1。该方向互换的招募现象与区间刚度增加同时出现，支持单边腱招募的机制解释。

这是工具测得的关联。Main 提出了腱机制假设，Reporter 对物理观测及证据边界进行了说明；现有总结不能单独确定 Reporter 的解释是否改变了 Main 后续决策。没有获得完整可比较的成对腱消融机制证据，因此不能声称腱招募是渐进刚度的唯一原因，骨架和几何非线性仍可能参与。

## Computational Cost

| 指标 | 既有 Full 统计 |
|---|---:|
| Provider Requests | 150/160 |
| Mathematical Evaluations | 67 |
| Analysis Results | 51 |
| Physics Episodes | 98 |
| Physics Steps | 15,680,000 |
| Token Usage | UNKNOWN：原始完整汇总未提供 |
| 美元费用 | UNKNOWN：不作估算 |

物理 episode/steps 包含研究计算中的实际动态执行，不等同于独立 Replay 证书数量。最终候选的一次双方向响应为 2 episodes、320,000 steps，已包含于 Study 汇总，不能再次相加。配置文件的 80 次是启动额度；150/160 是历史扩展后的最终使用/上限。

## Limitations

P3 已取得满足记录中核心数值要求的设计，不能写成未找到可行解。其结论限于保存的两 cell 数值模型和采样资格范围；原记录没有成功的 fresh 独立 Replay、原 Evaluator 验收证书或完整可比较的成对机制证据。该边界不取消已有数值性能结果，本轮也不追加资格审查。低载裕量很小，不能据此外推制造容差、硬件有效性或普遍鲁棒性。

Knowledge 的实际读取包括被动力学、研究流程和参数建模/匹配对照/有限搜索等 Skill；其中包含已标注来源的历史经验，不能写成本 Study 的首次发现。直接读取 `p3-case@3` 未在读取记录中出现，配置包含该条目不等于实际使用。详细角色区分见 [能力盘点](analysis_capability_inventory.md)。

整理来源：原仓库 `paper_experiments/case_studies/P3_main_historical.md` 及既有成本/分析摘要；本工作树的 [Main 最终报告](../../docs/research/p3-autonomous-study-v1_2-launch-20261110/main-final-answer-20261111.md)、[启动说明](../../docs/research/p3-autonomous-study-v1_2-launch-20261110/README.md)、[Study 配置](../../configs/research/study_p3_passive_progressive_stiffness_autonomous_v1_2.json)。历史最终执行 freeze 为 `b6ab46c1bacbd7e6b67c288e617d277b95297c75`，本次文档归档基线为 `fd2c1694dbef225cc08a516d2249735c9c180053`；两者不是同一版本身份。
