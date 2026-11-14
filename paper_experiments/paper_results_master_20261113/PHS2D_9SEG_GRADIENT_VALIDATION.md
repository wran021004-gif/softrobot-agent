# 九段四腱 PHS-2D：KKT 隐式梯度与重新求平衡有限差分证据审计

审计日期：2026-11-14。只解析历史封存 JSON、数学请求、Store receipt 和 artifact，并离线计算差值、范数、误差及单位换算；没有执行 MuJoCo、KKT/QP 求解、结构优化、候选生成或任何新的平衡求解。

六个最终 `task_metric_revision=2` 搜索分支均可提取成对的隐式梯度、实际正负扰动重新求平衡的坐标、已保存的中心有限差分及误差。任务指标的最大相对误差复核为 **0.11912227179584377%**，按四位小数百分数舍入为原报告的 **0.1191%**。该结论属于固定拓扑、九段共同模量方向上的局部被动平衡敏感性。

## 1. 冻结来源、版本与可定位方式

唯一科学来源 commit：`9d6d160e050c836b87d0563a497fc0ec1c3761a8`，研究分支 `research/phs2d-inverse-passive-design`。主要来源为 [第三轮报告](https://github.com/wran021004-gif/softrobot-agent/blob/9d6d160e050c836b87d0563a497fc0ec1c3761a8/docs/research/phs2d_round3_results_20261028.md)、[Study v2](https://github.com/wran021004-gif/softrobot-agent/blob/9d6d160e050c836b87d0563a497fc0ec1c3761a8/evidence/phs2d_round3_20261028/study_v2.json)、[最终设计记录](https://github.com/wran021004-gif/softrobot-agent/blob/9d6d160e050c836b87d0563a497fc0ec1c3761a8/evidence/phs2d_round3_20261028/solution/design.json)及其引用的封存 Store v2 artifact。

本表六条记录的 `run_id/study_id` 均为 `phs2d-inverse-passive-design-20261028-v2`，receipt 的 `execution_status=completed`、`solver_status=completed`，工具为 `research.phs2d_development`，`tool_version=1.0.0`；`analysis_status=development_not_registered`，不是已注册独立验收或硬件结果。没有将 v1 与 v2 拼成同一次实验。

检查了 [Study v1](https://github.com/wran021004-gif/softrobot-agent/blob/9d6d160e050c836b87d0563a497fc0ec1c3761a8/evidence/phs2d_round3_20261028/study_v1.json)、[v1 calls](https://github.com/wran021004-gif/softrobot-agent/blob/9d6d160e050c836b87d0563a497fc0ec1c3761a8/evidence/phs2d_round3_20261028/store_v1/calls.json)、[v1 manifest](https://github.com/wran021004-gif/softrobot-agent/blob/9d6d160e050c836b87d0563a497fc0ec1c3761a8/evidence/phs2d_round3_20261028/store_v1/archive_manifest.json)与 [v2 calls](https://github.com/wran021004-gif/softrobot-agent/blob/9d6d160e050c836b87d0563a497fc0ec1c3761a8/evidence/phs2d_round3_20261028/store_v2/calls.json)、[v2 manifest](https://github.com/wran021004-gif/softrobot-agent/blob/9d6d160e050c836b87d0563a497fc0ec1c3761a8/evidence/phs2d_round3_20261028/store_v2/archive_manifest.json)。六个最终结果的输出 ID、请求 ID 和 run_id 均定位于 v2。v1 只用于谱系核对，不提供本表任一梯度数值。

`source_artifact_refs` 是 JSON 数组。`sealed_artifact` 项提供冻结 commit、manifest 路径、归档 member（`artifacts/<SHA256>.json`）、artifact ID 与 JSON Pointer；`git` 项提供该 commit 下文件和数组下标或代码行段。artifact 内容从本地已有 Store 的只读 SQLite 中取出，逐个核对其完整原始字节 SHA256 与冻结 manifest；本次提交不包含私有 Store、归档、完整矩阵或原始轨迹。可依据 manifest 的 `archive_parts/reconstruction` 定位已有封存归档中的同名 member。

## 2. 研究对象与实际设计参数

最终结构为 `P3_real9_E80_full8`：九段、四条被动腱、72 个弯曲单元和 144 个广义弯曲坐标，运行 XML 无执行器。每段长度 `0.031111111111111114 m`，总柔性长度 0.28 m，圆截面半径 0.003 m。四条固定放绳长度均为 `0.39274245978073885 m`；正负扰动中不变。载荷沿世界 x 方向；`material_s` 是累计柔性材料长度的归一化位置，不含刚性连接件长度；Tip 另行测量。

| 对象 | artifact ID / 身份 |
| --- | --- |
| 基准 assembly | `0bde4fd77ac561a441ab9e5faf65d65760ca2b5bdd2caa41ff8307e22ff03d3d` |
| 基准 candidate artifact | `023bea360a83f67f12c7aee8346e9e62f2cc09e48a979dc2689c5881460932e5` |
| 基准 candidate scientific ID | `core-3e18c3a90bbeb743615036a80043041629763771fe64d4e1563b0b414e36e233` |
| 负扰动 assembly | `93161e2c433e06713cf5ed8f4b40f5a5d10bc3d3faf284cf474b74689f1f115b` |
| 负扰动 candidate | `80812545d12bf52dbee893b7627c30bf4497309201ab9bb2ed853a2862b5e7bc` |
| 正扰动 assembly | `ab12a916b0547873ab6b99dc76e50ca3ee938bf4085bc22658ea2d5e370deb9b` |
| 正扰动 candidate | `e805d59cc3feddfbdf2e473bad401079023653fdbd60f325913bc33a12f9cd8e` |

实际变化经 generation 与候选物理配置的递归比较双重核实：仅九个 `young_pa` 同时变化，其他物理组件、截面、腱路、放绳长度、材料密度、黏性及离散网格均一致。这是**一个绑定的九段共同模量方向**，不是九个独立偏导，也不能分离为某一段的独立贡献。

| segment ID | generation 参数路径 | candidate 参数路径 |
| --- | --- | --- |
| segment_0 | `/generation/segments/0/young_pa` | `/configuration/robot/structure/data/components/0/physics/young_pa` |
| segment_1 | `/generation/segments/1/young_pa` | `/configuration/robot/structure/data/components/3/physics/young_pa` |
| segment_2 | `/generation/segments/2/young_pa` | `/configuration/robot/structure/data/components/6/physics/young_pa` |
| segment_3 | `/generation/segments/3/young_pa` | `/configuration/robot/structure/data/components/9/physics/young_pa` |
| segment_4 | `/generation/segments/4/young_pa` | `/configuration/robot/structure/data/components/12/physics/young_pa` |
| segment_5 | `/generation/segments/5/young_pa` | `/configuration/robot/structure/data/components/15/physics/young_pa` |
| segment_6 | `/generation/segments/6/young_pa` | `/configuration/robot/structure/data/components/18/physics/young_pa` |
| segment_7 | `/generation/segments/7/young_pa` | `/configuration/robot/structure/data/components/21/physics/young_pa` |
| segment_8 | `/generation/segments/8/young_pa` | `/configuration/robot/structure/data/components/24/physics/young_pa` |

归一化定义和实际扰动：

\[u=\frac{E-2\times10^6\ \mathrm{Pa}}{13\times10^6\ \mathrm{Pa}},\quad u_0=\frac6{13},\quad h=0.001.\]

| 状态 | 九段各自 E / Pa | u | 相对基准的 ΔE / Pa |
| --- | --- | --- | --- |
| 基准 | 8000000 | 0.46153846153846156 | 0 |
| 正扰动 | 8013000 | 0.46253846153846156 | +13000 |
| 负扰动 | 7987000 | 0.46053846153846156 | -13000 |

中心差分分母 `2h=0.002`，参数跨度为 26000 Pa。CSV 的 `baseline_parameter/positive_parameter/negative_parameter` 单位均为 Pa；`positive_step/negative_step` 表示有符号物理增量 +13000 / −13000 Pa，`normalized_step` 表示无量纲 h。模量单位换算由 `d/du=13 MPa × d/dE` 给出。这里的“13 MPa”来自实际请求归一化定义，不是扰动模量本身。

## 3. 数学流程与指标定义

数学实现引用 [passive_equilibrium.py](https://github.com/wran021004-gif/softrobot-agent/blob/9d6d160e050c836b87d0563a497fc0ec1c3761a8/extensions/tendon_family/passive_equilibrium.py#L9-L95) 与 [passive_inverse.py](https://github.com/wran021004-gif/softrobot-agent/blob/9d6d160e050c836b87d0563a497fc0ec1c3761a8/extensions/tendon_family/passive_inverse.py#L72-L156)。隐式结果记录的实现 commit 为 `d377310165c9f49d3300ef467db02c3696a349b4`；这两个文件在该实现 commit 与冻结来源一致。原始加载/无载平衡记录实现 commit 为 `f42e86358001aea7e2e6ca9a59584c31459c7112`，其 `passive_equilibrium.py` 也与冻结版本一致。

历史平衡是原生三维铰链离散模型的势能最小化：弹性势能、重力势能和恒定外力势能，理想硬单边腱长约束；它使用原生模型的位置、力和 Jacobian，但不是物理轨迹积分。SLSQP 将目标与不等式统一乘 1000 改善数值尺度；下述保存的 KKT 检查使用未缩放的 SI 物理量。

\[\min_q\Pi(q,E;F,s),\qquad c_i(q,E)=\ell_i(q,E)-L_i\le0,\quad\lambda_i\ge0,\quad\lambda_i c_i=0.\]

\[\nabla_q\Pi+J_\ell^T\lambda=0,\quad\begin{bmatrix}H&J_A^T\\J_A&0\end{bmatrix}\begin{bmatrix}q_u\\\lambda_{A,u}\end{bmatrix}=-\begin{bmatrix}\partial_u(\nabla_q\Pi+J_\ell^T\lambda)\\\partial_u c_A\end{bmatrix}.\]

`H` 为拉格朗日函数对 q 的 Hessian，`J_A` 为活跃腱约束 Jacobian。源实现的 H 由对广义平衡梯度的中心有限差分得到，步长为 `1e-5 rad`；参数偏导在基准 q、λ 固定下，使用实际 ±E 模型以 h=0.001 中心差分估计，再解 KKT 线性系统。位置导数包含位置 Jacobian 乘 q_u 与显式参数项。故应称为**采用数值偏导的 KKT 隐式微分**，不能写成全解析梯度或自动微分。H、Jlength、qpos 和乘子保存在原平衡 artifact；独立的完整 KKT 矩阵、参数偏导向量及线性方程求解残差没有序列化。

`task_metric_revision=2` 对加载状态与设计相关的无载状态各执行一次 `design_sensitivity`：

\[\Delta p(u)=p_{\mathrm{loaded}}(u)-p_{\mathrm{unloaded}}(u),\qquad\Delta p_u=p_{\mathrm{loaded},u}-p_{\mathrm{unloaded},u}.\]

受力点任务指标是 `point_dx_m=|Δp_point,x|`，不是有符号 x 位移；Tip 指标是 `tip_xy_m=||Δp_tip,xy||₂`；`ratio=tip_xy_m/point_dx_m`。隐式任务梯度通过绝对值与欧氏范数链式求导。各分支的位移非零，满足代码的可微指标门槛。两份基准位置及加载、无载原始 `dposition_du` 都可定位；CSV 同时保存二者向量与相减结果，以保留仅加载求导与相对位移求导的区别。

\[a_u=\operatorname{sgn}(\Delta x)\Delta x_u,\quad b_u=\frac{\Delta p_{\mathrm{tip},xy}^{T}\Delta p_{\mathrm{tip},xy,u}}{\|\Delta p_{\mathrm{tip},xy}\|_2},\quad r_u=\frac{b_u}{a}-\frac{b\,a_u}{a^2}.\]

## 4. 实际重新求平衡有限差分及误差复核

源函数在相同基准 qpos 作为初值下，对实际负/正扰动候选分别重新调用平衡求解；加载与无载各自执行，历史输出在 `resolved_comparison` 和 `baseline_response/resolved_comparison` 中保存 `minus_positions/plus_positions`、求解资格状态、活跃集合一致性布尔值及广义坐标/位置的中心差分。任务 FD 由每个扰动设计自己的加载减无载位置计算，存于 `task_resolved_directional_derivatives`。本审计直接提取该 FD，并用四组已保存位置重新算指标及中心差分，未通过报告误差反推 FD。

\[D_{\mathrm{FD}}=\frac{g(u+h)-g(u-h)}{2h},\quad D_L=\frac{g(u)-g(u-h)}h,\quad D_R=\frac{g(u+h)-g(u)}h.\]

只有一个材料参数步长 h=0.001。有保存的正负状态支持中心差分；本次额外离线算出的左右割线明确标为派生值，不是新的平衡实验。未找到 h/2 的材料敏感性结果，相关字段统一为 `unavailable_in_sealed_evidence`。[numerical_comparison.json](https://github.com/wran021004-gif/softrobot-agent/blob/9d6d160e050c836b87d0563a497fc0ec1c3761a8/evidence/phs2d_round3_20261028/numerical_comparison.json) 的半时间步比较属于 MuJoCo 动力学积分收敛性检查，不能充作材料扰动半步长梯度验证。

误差按原实现逐指标计算：

\[e_{\rm abs}=|D_{\rm implicit}-D_{\rm FD}|,\qquad e_{\rm rel}=\frac{e_{\rm abs}}{\max(|D_{\rm implicit}|,|D_{\rm FD}|,10^{-8})}.\]

原始位移梯度以 m/du 代入该公式，ratio 梯度以 1/du 代入。绘图/主表的位移梯度转换为 mm/du；若在 mm/du 单位重新计算，分母下限应相应变为 1e-5，不能仍用 1e-8。CSV 同时保留原始梯度、分母、误差分数和百分数；`gradient_difference` 采用 implicit−FD，有符号；绝对误差取绝对值。

### 4.1 受力点梯度配对

| s | F / N | 隐式 / mm·du⁻¹ | 中心 FD / mm·du⁻¹ | 绝对误差 / mm·du⁻¹ | 相对误差 / % |
| --- | --- | --- | --- | --- | --- |
| 0.7 | -0.1 | -18.1252040074 | -18.1362284517 | 0.0110244442391 | 0.0607868624307 |
| 0.3 | 0.1 | -6.2834340653 | -6.28442851432 | 0.000994449015648 | 0.0158240166689 |
| 0.3 | -0.1 | -6.24999571672 | -6.24255057984 | 0.0074451368849 | 0.119122271796 |
| 0.5 | -0.1 | -10.1428906037 | -10.141339685 | 0.00155091870527 | 0.0152906973551 |
| 0.7 | 0.1 | -18.1013291845 | -18.093402588 | 0.00792659648964 | 0.0437901350163 |
| 0.5 | 0.1 | -10.1793513314 | -10.1763220677 | 0.00302926369422 | 0.0297589069833 |

### 4.2 Tip 梯度配对

| s | F / N | 隐式 / mm·du⁻¹ | 中心 FD / mm·du⁻¹ | 绝对误差 / mm·du⁻¹ | 相对误差 / % |
| --- | --- | --- | --- | --- | --- |
| 0.7 | -0.1 | -4.88766524678 | -4.88919822982 | 0.00153298303544 | 0.0313544872468 |
| 0.3 | 0.1 | -0.825187456781 | -0.825269441019 | 8.19842379955e-05 | 0.00993423891891 |
| 0.3 | -0.1 | -0.896786047978 | -0.895884635771 | 0.000901412207088 | 0.100515859844 |
| 0.5 | -0.1 | -1.53636635254 | -1.53650742967 | 0.000141077129253 | 0.00918167569704 |
| 0.7 | 0.1 | -4.41197038345 | -4.4105565748 | 0.0014138086454 | 0.0320448353575 |
| 0.5 | 0.1 | -1.38207733312 | -1.38183173969 | 0.000245593437094 | 0.0177698766348 |

### 4.3 ratio 梯度与原报告最大误差

| s | F / N | 隐式 ratio / du | 中心 FD ratio / du | ratio 误差 / % | 三指标最大误差 / % | 报告 / % |
| --- | --- | --- | --- | --- | --- | --- |
| 0.7 | -0.1 | -0.10365391417 | -0.103665454167 | 0.0111319599758 | 0.0607868624307 | 0.0608 |
| 0.3 | 0.1 | -0.0400382176558 | -0.0400401785764 | 0.00489738233732 | 0.0158240166689 | 0.0158 |
| 0.3 | -0.1 | -0.0444132271586 | -0.0443752988191 | 0.0853987470489 | 0.119122271796 | 0.1191 |
| 0.5 | -0.1 | -0.0380919674011 | -0.0381025495826 | 0.0277728958527 | 0.0277728958527 | 0.0278 |
| 0.7 | 0.1 | -0.093435500748 | -0.0934129572226 | 0.024127366176 | 0.0437901350163 | 0.0438 |
| 0.5 | 0.1 | -0.033469480187 | -0.0334666925936 | 0.0083287623765 | 0.0297589069833 | 0.0298 |

原报告各行“最大梯度相对误差”是 point、tip、ratio 三项的最大值。例如 s=0.50、F=−0.10 N 的最大值来自 ratio（0.02777289585265149%），不是 point 或 tip。全局最大来自 s=0.30、F=−0.10 N 的 point。六行均按四位小数百分数与原报告一致，报告中的受力点和 Tip 梯度亦与原 artifact 的舍入值一致。

### 4.4 可直接复算的三个标量端点

**受力点 |Δx| / m**

| s | F / N | g(u−h) | g(u) | g(u+h) |
| --- | --- | --- | --- | --- |
| 0.7 | -0.1 | 0.02809604690885062 | 0.0280778865480405 | 0.02805977445194725 |
| 0.3 | 0.1 | 0.01118494400700177 | 0.01117865688415053 | 0.01117237514997314 |
| 0.3 | -0.1 | 0.01116113537498009 | 0.01115489722233788 | 0.01114865027382042 |
| 0.5 | -0.1 | 0.02290592215938149 | 0.02289578011282647 | 0.0228856394800115 |
| 0.7 | 0.1 | 0.02803666612258689 | 0.02801856212091879 | 0.02800047931741086 |
| 0.5 | 0.1 | 0.02293309818835524 | 0.02292289945606958 | 0.02291274554421979 |

**Tip 水平位移范数 / m**

| s | F / N | g(u−h) | g(u) | g(u+h) |
| --- | --- | --- | --- | --- |
| 0.7 | -0.1 | 0.003067922283521538 | 0.003063022683937182 | 0.003058143887061908 |
| 0.3 | 0.1 | 0.0006726269618308769 | 0.0006718009359878192 | 0.000670976422948839 |
| 0.3 | -0.1 | 0.0007172389609507817 | 0.0007163431172872069 | 0.0007154471916792401 |
| 0.5 | -0.1 | 0.001500899106622536 | 0.001499361428400378 | 0.001497826091763192 |
| 0.7 | 0.1 | 0.002781366607100992 | 0.002776949513072893 | 0.002772545493951386 |
| 0.5 | 0.1 | 0.001385988615383852 | 0.00138460389141017 | 0.001383224951904479 |

**ratio（无量纲）**

| s | F / N | g(u−h) | g(u) | g(u+h) |
| --- | --- | --- | --- | --- |
| 0.7 | -0.1 | 0.1091940903100892 | 0.1090902151305596 | 0.1089867594017558 |
| 0.3 | 0.1 | 0.0601368197650174 | 0.06009674891626029 | 0.06005673940786461 |
| 0.3 | -0.1 | 0.06426218631471987 | 0.06421781420385635 | 0.0641734357170817 |
| 0.5 | -0.1 | 0.06552450044050373 | 0.06548636565392324 | 0.06544829534133861 |
| 0.7 | 0.1 | 0.09920461280737897 | 0.09911106433972247 | 0.0990177868929337 |
| 0.5 | 0.1 | 0.06043616976652624 | 0.06040265081054357 | 0.0603692363813391 |

以上端点由保存的位置离线计算；CSV 的 `selected_equilibrium_positions_m` 保留名义/正/负、加载/无载的受力点和 Tip 三维位置，并给出原始完整位置数组引用。未上传其他监测点的整组轨迹。图数据 CSV 共 18 行，为 6 分支 × point/tip/ratio；每行还保留左右割线、中心差分、原单位分母与扰动步长。平面外最大范数只有已保存的方向性 FD，没有普通隐式梯度，未加入配对散点数据。

### 4.5 广义坐标误差不能替代任务指标误差

| s | F / N | 加载 q 梯度误差 / % | 无载 q 梯度误差 / % | task_gradient_trustworthy |
| --- | --- | --- | --- | --- |
| 0.7 | -0.1 | 0.295666471502 | 1.11473119693 | true |
| 0.3 | 0.1 | 0.0628812795196 | 1.11473119693 | true |
| 0.3 | -0.1 | 0.314370321434 | 1.11473119693 | true |
| 0.5 | -0.1 | 0.239908429301 | 1.11473119693 | true |
| 0.7 | 0.1 | 0.104738997992 | 1.11473119693 | true |
| 0.5 | 0.1 | 0.547450807756 | 1.11473119693 | true |

artifact 顶层 `gradient_relative_error` 比较 144 维 q_u，使用 L2 范数并以隐式 q_u 范数为分母，下限 1e-12；它和三项 `task_gradient_relative_errors` 的分母定义不同。无载 q 梯度相对误差约 1.1147%，所以“最大误差 0.1191%”只能限定于六个分支的三个任务标量梯度，不能扩大为全部状态导数的最大误差。原 `gradient_trustworthy` 阈值为 5%，还要求实际重求平衡状态合格及活跃集合一致；这是实现中的局部数值诊断，不是全局保证。

## 5. 活跃集合、正则性与稳定性

腱顺序为 `tendon_0, tendon_1, tendon_2, tendon_3`。原约束方向为 length−fixed_payout≤0：正张力只能拉，松弛腱 λ=0；源 SLSQP 输入采用相反号的 ≥0 形式。每条候选的物理腱路与顺序在正负扰动中保持不变。

| s | F / N | 名义加载活跃腱 | E− / E+ 加载 | 无载及其 E− / E+ | LICQ / 严格互补 / 二阶条件 | KKT condition（加载） |
| --- | --- | --- | --- | --- | --- | --- |
| 0.7 | -0.1 | ["tendon_0","tendon_2"] | 与名义相同† | tendon_1, tendon_3† | true / true / true | 273.218849874 |
| 0.3 | 0.1 | ["tendon_1","tendon_3"] | 与名义相同† | tendon_1, tendon_3† | true / true / true | 299.698438062 |
| 0.3 | -0.1 | ["tendon_0","tendon_2"] | 与名义相同† | tendon_1, tendon_3† | true / true / true | 301.726193901 |
| 0.5 | -0.1 | ["tendon_0","tendon_2"] | 与名义相同† | tendon_1, tendon_3† | true / true / true | 289.949615727 |
| 0.7 | 0.1 | ["tendon_1","tendon_3"] | 与名义相同† | tendon_1, tendon_3† | true / true / true | 270.144669268 |
| 0.5 | 0.1 | ["tendon_1","tendon_3"] | 与名义相同† | tendon_1, tendon_3† | true / true / true | 287.534471266 |

† 名义加载及无载活跃布尔数组直接保存；正负扰动没有单独序列化活跃数组。这里根据已保存 `same_active_set=true` 和代码第 105 行的确切比较 `minus.active == nominal.active == plus.active` 推得两侧集合，而非声称读取到两份显式列表。无载的两侧集合由 `baseline_response/resolved_comparison/same_active_set=true` 同样推得。CSV 的 `perturbed_active_set_basis` 明示该推导，`perturbed_active_set_explicit_lists` 仍标 unavailable。每个分支均有加载与无载各一组该比较。

LICQ 以活跃 Jacobian 的秩等于活跃数判定，秩阈值为 max(1e-12, σ_max×1e-8)；所有名义加载和共享名义无载均为秩 2。活跃判定容差为 1e-7 m；严格互补按所有活跃张力大于 1e-7 N 判定。稳定性为正乘子约束 Jacobian 零空间上的拉格朗日 Hessian 正定充分检查，最小特征值门槛为 1e-7。不是整个全局能量景观、硬件或活跃集合切换处的稳定性证明。

| s | F / N | 活跃 σ_min | 最小约化 Hessian 特征值 | 加载张力 / N |
| --- | --- | --- | --- | --- |
| 0.7 | -0.1 | 0.0837676646635 | 0.104536520891 | [0.3625070556967058,0.0,0.3488164861419476,0.0] |
| 0.3 | 0.1 | 0.0838155861647 | 0.128742161267 | [0.0,0.10342368333717637,0.0,0.08940948792106762] |
| 0.3 | -0.1 | 0.0838126141591 | 0.129923135646 | [0.0875803669899032,0.0,0.07357414199290235,0.0] |
| 0.5 | -0.1 | 0.0837932227993 | 0.119799811942 | [0.20127103510580338,0.0,0.18739100607591425,0.0] |
| 0.7 | 0.1 | 0.083773268283 | 0.102671331037 | [0.0,0.3791762877163908,0.0,0.3654539841296518] |
| 0.5 | 0.1 | 0.0837970079107 | 0.118105674652 | [0.0,0.21738367889467242,0.0,0.20348324030761375] |

共享无载名义状态：活跃腱 tendon_1、tendon_3；LICQ=true；严格互补=true；二阶充分条件=true。

共享无载 artifact 原请求的 s=0.50、force_n=0；在零外力下这是同一无载构型。各分支的 `baseline_response.s` 则与该分支的受力点 s 一致，原任务函数据此提取对应材料位置的无载位置导数。CSV 将 `unloaded_source_material_s` 与 `unloaded_sensitivity_material_s` 分别保留，不把零载构型的请求位置误作所有梯度分支的受力位置。

| 量 | 保存值 |
| --- | --- |
| 张力 / N | [0.0,0.014786373642602473,0.0,0.0007467432240251971] |
| 活跃奇异值 | [0.17847478840142456,0.08384243057213092] |
| 最小约化 Hessian 特征值 | 0.13095464953162597 |
| KKT condition | 309.26577891440155 |
| 稳定性范围 | finite-difference sufficient positivity on nullspace of positive multipliers; no global or hardware certificate |

正负扰动的加载与无载状态均保存 `qualified_local_minimum`，该状态在实现中要求 KKT、二阶充分条件、张力容量和无接触检查通过；但其具体 LICQ/严格互补数组、奇异值、乘子和约化谱没有作为独立平衡 artifact 留存。不能将名义正则性数值复制为扰动状态的数值。

## 6. KKT 残差、平衡残差与求解状态

以下每项均直接取原始名义平衡 artifact 的 `equilibrium`，不是敏感性导数或物理轨迹尾窗指标：

| CSV 字段 | 原始字段 | 含义 | 单位 |
| --- | --- | --- | --- |
| KKT_primal_residual | primal_violation_m | max(0,max_i c_i) | m |
| KKT_stationarity_residual | stationarity_inf_nm | \|\|∇Π+Jᵀλ\|\|∞，未缩放广义静力平衡 | N·m |
| KKT_dual_residual | dual_violation_n | 保存值 0；实现用 NNLS 得非负乘子并固定写 0 | N |
| complementarity_residual | complementarity_nm | max_i \|λ_i c_i\| | N·m |

`nm` 后缀在该代码表示 N·m，不是纳米。四项采用不同单位，不能取未归一化的混合最大值冒充统一 KKT 残差。dual=0 是原实现字段的真实语义，不是另一次独立的对偶验证实验。

| s | F / N | primal / m | stationarity / N·m | dual / N | complementarity / N·m |
| --- | --- | --- | --- | --- | --- |
| 0.7 | -0.1 | 5.06128472466e-12 | 6.12479559589e-09 | 0.0 | 1.83475142358e-12 |
| 0.3 | 0.1 | 1.64424029947e-13 | 3.03438348883e-10 | 0.0 | 1.70053388063e-14 |
| 0.3 | -0.1 | 1.42885703269e-13 | 8.15623078625e-10 | 0.0 | 1.25139823299e-14 |
| 0.5 | -0.1 | 8.72135696994e-13 | 2.44927820975e-09 | 0.0 | 1.75535654487e-13 |
| 0.7 | 0.1 | 4.08445499644e-12 | 1.29942728613e-08 | 0.0 | 1.5487284829e-12 |
| 0.5 | 0.1 | 2.42067477174e-12 | 3.04937161394e-09 | 0.0 | 5.26215187289e-13 |

| 无载共享名义状态 | 值 |
| --- | --- |
| primal / m | 0.0 |
| stationarity / N·m | 2.6171092381177975e-09 |
| dual / N | 0.0 |
| complementarity / N·m | 4.724574436499864e-15 |
| length_residual_m | [-5.233793091696803e-07,-3.1952218648712005e-13,-5.233854987185538e-07,-3.1907809727727e-13] |

保存的 KKT 容差：stationarity≤1e-6 N·m，primal≤1e-8 m，complementarity≤1e-8 N·m；六个加载和共享无载均 `kkt_pass=true`。`length_residual_m` 是四条腱的约束值，负值表示松弛，不是广义静力平衡残差；`dlength_residual_du` 更是约束值的导数，也不能替代上述任何残差。

六个名义加载状态的原始 `optimizer_success=false`，`optimizer_message="Positive directional derivative for linesearch"`；均经后续显式 KKT/稳定性/容量/接触资格检查归为 `qualified_local_minimum`。共享无载为 `optimizer_success=true`，`Optimization terminated successfully`。报告保留该差别，不把 receipt completed 或后验资格写成 SLSQP 原始成功。

对这些硬约束敏感性状态，没有另一个独立命名并保存的物理 `loaded_equilibrium_residual` / `unloaded_equilibrium_residual` 标量。尽管 KKT stationarity 本身有未缩放广义静力平衡含义，本审计将它保留在对应 KKT 字段，另两个请求字段标为 `unavailable_in_sealed_evidence`，不重复改名充数。MuJoCo 最终轨迹的尾窗软静态残差是另一模型/执行记录的指标，未填入本表。正负扰动的逐状态 KKT 残差和独立平衡残差亦未保存；`qualified_local_minimum` 只能提供资格状态，不能还原各项残差数值。

## 7. 六个分支的请求与原始证据索引

以下完整 ID 可在冻结 `store_v2/calls.json` 和 manifest 中检索；JSON Pointer 以 `/` 开始、数组下标从 0 开始。主 CSV 每行提供更完整的 machine-readable refs。

### PHS9_E_s0.70_Fminus0.10

- s=0.7，F=-0.1 N；Study `/analyses/1`；solution `/sensitivity/0`；calls `/229`。
- request_id：`phs-401a866e8221350766806a1b449b2d3b7c617ad9c331423dded654ed2aa7a06b`；execution_id：`5af41588779b44b1b136dcc7588cf6ba`。
- 敏感性输出：`197839ae64e447fa28f2e19b2773b009e8edebbb05d4cab241dabf673ce9cf21`；member `artifacts/197839ae64e447fa28f2e19b2773b009e8edebbb05d4cab241dabf673ce9cf21.json`。
- 名义加载平衡：`009174f647cf4a1561e149a8b3a4c2dbf1d7afe32548258c908c3da87a70b60f`；名义无载平衡：`a3355f9b65ae496ace500812f29f2e695ea115926807dab39383e6ab48e7048a`。
- 数学请求：输出 `/request`，含 assembly、minus、plus、protocol、source、baseline_source、parameter、normalized_step。
- 隐式位置导数：`/dposition_du`、`/baseline_response/dposition_du`；任务指标：`/task_derivatives_du`。
- 重新求平衡坐标：`/resolved_comparison/{minus_positions,plus_positions}` 和 `/baseline_response/resolved_comparison/{minus_positions,plus_positions}`；保存的 FD：`/task_resolved_directional_derivatives`。
- 活跃集合/正则性：`/active`、`/LICQ`、`/strict_complementarity`、`/KKT_condition` 及 `/baseline_response` 同名字段；扰动集合的一致性：两处 `/resolved_comparison/same_active_set`。
- 名义 KKT 与二阶结果：加载/无载平衡 artifact 的 `/equilibrium/{primal_violation_m,stationarity_inf_nm,dual_violation_n,complementarity_nm,active_singular_values,reduced_eigenvalues,H,Jlength,qpos,tensions_n}`。

### PHS9_E_s0.30_Fplus0.10

- s=0.3，F=0.1 N；Study `/analyses/4`；solution `/sensitivity/1`；calls `/224`。
- request_id：`phs-5f32d0a3dfa80ba1c1743237bbb9e6b12eee90baed785355474ba885409df82e`；execution_id：`28f4473558ba404982e9bcdeb308c617`。
- 敏感性输出：`b0251413eb6e13e01b46cbe1d3af2967264fcb234e8ddbcfdbecd2b6d6ebbbc8`；member `artifacts/b0251413eb6e13e01b46cbe1d3af2967264fcb234e8ddbcfdbecd2b6d6ebbbc8.json`。
- 名义加载平衡：`74986381e91128164c7c76005fc544e6db8153b10c10a7265f7bae440e7b38f7`；名义无载平衡：`a3355f9b65ae496ace500812f29f2e695ea115926807dab39383e6ab48e7048a`。
- 数学请求：输出 `/request`，含 assembly、minus、plus、protocol、source、baseline_source、parameter、normalized_step。
- 隐式位置导数：`/dposition_du`、`/baseline_response/dposition_du`；任务指标：`/task_derivatives_du`。
- 重新求平衡坐标：`/resolved_comparison/{minus_positions,plus_positions}` 和 `/baseline_response/resolved_comparison/{minus_positions,plus_positions}`；保存的 FD：`/task_resolved_directional_derivatives`。
- 活跃集合/正则性：`/active`、`/LICQ`、`/strict_complementarity`、`/KKT_condition` 及 `/baseline_response` 同名字段；扰动集合的一致性：两处 `/resolved_comparison/same_active_set`。
- 名义 KKT 与二阶结果：加载/无载平衡 artifact 的 `/equilibrium/{primal_violation_m,stationarity_inf_nm,dual_violation_n,complementarity_nm,active_singular_values,reduced_eigenvalues,H,Jlength,qpos,tensions_n}`。

### PHS9_E_s0.30_Fminus0.10

- s=0.3，F=-0.1 N；Study `/analyses/5`；solution `/sensitivity/2`；calls `/225`。
- request_id：`phs-63437d693675f2682aa917d4573745963cbed7473b112357bdad9e2abcb57264`；execution_id：`92cb9358554b4d6f9ee12e81a09c062c`。
- 敏感性输出：`9507fa4b9719bd1fad9e49ad5b464f8f37374f92cb0b3d894591c0f9387520fd`；member `artifacts/9507fa4b9719bd1fad9e49ad5b464f8f37374f92cb0b3d894591c0f9387520fd.json`。
- 名义加载平衡：`bc4be0a6f4648362749f4a02588c5f2f90241d97f8dcd6944360d4348b7f8a51`；名义无载平衡：`a3355f9b65ae496ace500812f29f2e695ea115926807dab39383e6ab48e7048a`。
- 数学请求：输出 `/request`，含 assembly、minus、plus、protocol、source、baseline_source、parameter、normalized_step。
- 隐式位置导数：`/dposition_du`、`/baseline_response/dposition_du`；任务指标：`/task_derivatives_du`。
- 重新求平衡坐标：`/resolved_comparison/{minus_positions,plus_positions}` 和 `/baseline_response/resolved_comparison/{minus_positions,plus_positions}`；保存的 FD：`/task_resolved_directional_derivatives`。
- 活跃集合/正则性：`/active`、`/LICQ`、`/strict_complementarity`、`/KKT_condition` 及 `/baseline_response` 同名字段；扰动集合的一致性：两处 `/resolved_comparison/same_active_set`。
- 名义 KKT 与二阶结果：加载/无载平衡 artifact 的 `/equilibrium/{primal_violation_m,stationarity_inf_nm,dual_violation_n,complementarity_nm,active_singular_values,reduced_eigenvalues,H,Jlength,qpos,tensions_n}`。

### PHS9_E_s0.50_Fminus0.10

- s=0.5，F=-0.1 N；Study `/analyses/6`；solution `/sensitivity/3`；calls `/227`。
- request_id：`phs-6e4697c7d7ada97871064d46397618b004ad84588c02339290451016b9a069cf`；execution_id：`bcd20fa5e0a1406092ad43c9b199247a`。
- 敏感性输出：`05c95aed3733a424aa193dac45f9598501021d5b8fbaea2cb15e5b00da4a57c6`；member `artifacts/05c95aed3733a424aa193dac45f9598501021d5b8fbaea2cb15e5b00da4a57c6.json`。
- 名义加载平衡：`36388000a844561cfe68090a543a5fa48c5d431901ebb5bd8f8f245dc162a3d4`；名义无载平衡：`a3355f9b65ae496ace500812f29f2e695ea115926807dab39383e6ab48e7048a`。
- 数学请求：输出 `/request`，含 assembly、minus、plus、protocol、source、baseline_source、parameter、normalized_step。
- 隐式位置导数：`/dposition_du`、`/baseline_response/dposition_du`；任务指标：`/task_derivatives_du`。
- 重新求平衡坐标：`/resolved_comparison/{minus_positions,plus_positions}` 和 `/baseline_response/resolved_comparison/{minus_positions,plus_positions}`；保存的 FD：`/task_resolved_directional_derivatives`。
- 活跃集合/正则性：`/active`、`/LICQ`、`/strict_complementarity`、`/KKT_condition` 及 `/baseline_response` 同名字段；扰动集合的一致性：两处 `/resolved_comparison/same_active_set`。
- 名义 KKT 与二阶结果：加载/无载平衡 artifact 的 `/equilibrium/{primal_violation_m,stationarity_inf_nm,dual_violation_n,complementarity_nm,active_singular_values,reduced_eigenvalues,H,Jlength,qpos,tensions_n}`。

### PHS9_E_s0.70_Fplus0.10

- s=0.7，F=0.1 N；Study `/analyses/7`；solution `/sensitivity/4`；calls `/228`。
- request_id：`phs-71fdf53d4c230bc2996fa28af122f9dfd8064dc3555af110030749728c29b281`；execution_id：`e23d1abdebea48699cc734743c74e1c6`。
- 敏感性输出：`9a701ef2acc5a3863a587487bcb19c38918be124b13705a6827f073688e6ebf4`；member `artifacts/9a701ef2acc5a3863a587487bcb19c38918be124b13705a6827f073688e6ebf4.json`。
- 名义加载平衡：`2514749132f86ec879550e240e8718dd88f90dffb7cfc31c7bbcc2f414a845b5`；名义无载平衡：`a3355f9b65ae496ace500812f29f2e695ea115926807dab39383e6ab48e7048a`。
- 数学请求：输出 `/request`，含 assembly、minus、plus、protocol、source、baseline_source、parameter、normalized_step。
- 隐式位置导数：`/dposition_du`、`/baseline_response/dposition_du`；任务指标：`/task_derivatives_du`。
- 重新求平衡坐标：`/resolved_comparison/{minus_positions,plus_positions}` 和 `/baseline_response/resolved_comparison/{minus_positions,plus_positions}`；保存的 FD：`/task_resolved_directional_derivatives`。
- 活跃集合/正则性：`/active`、`/LICQ`、`/strict_complementarity`、`/KKT_condition` 及 `/baseline_response` 同名字段；扰动集合的一致性：两处 `/resolved_comparison/same_active_set`。
- 名义 KKT 与二阶结果：加载/无载平衡 artifact 的 `/equilibrium/{primal_violation_m,stationarity_inf_nm,dual_violation_n,complementarity_nm,active_singular_values,reduced_eigenvalues,H,Jlength,qpos,tensions_n}`。

### PHS9_E_s0.50_Fplus0.10

- s=0.5，F=0.1 N；Study `/analyses/8`；solution `/sensitivity/5`；calls `/226`。
- request_id：`phs-88fdaeb8648a473e86f33efd961478e597ebde4b901fc319836d237655332eac`；execution_id：`00b4210d800f473f8bb9f687eb0dba61`。
- 敏感性输出：`23eb33bb2cbcae8c71493ea68519ba3cd57b0af53ecde093a4bae720aa21ffe5`；member `artifacts/23eb33bb2cbcae8c71493ea68519ba3cd57b0af53ecde093a4bae720aa21ffe5.json`。
- 名义加载平衡：`2b74f84f60328ef345f4d906307878c8f342b9f705800adc43b1f2b23d71a867`；名义无载平衡：`a3355f9b65ae496ace500812f29f2e695ea115926807dab39383e6ab48e7048a`。
- 数学请求：输出 `/request`，含 assembly、minus、plus、protocol、source、baseline_source、parameter、normalized_step。
- 隐式位置导数：`/dposition_du`、`/baseline_response/dposition_du`；任务指标：`/task_derivatives_du`。
- 重新求平衡坐标：`/resolved_comparison/{minus_positions,plus_positions}` 和 `/baseline_response/resolved_comparison/{minus_positions,plus_positions}`；保存的 FD：`/task_resolved_directional_derivatives`。
- 活跃集合/正则性：`/active`、`/LICQ`、`/strict_complementarity`、`/KKT_condition` 及 `/baseline_response` 同名字段；扰动集合的一致性：两处 `/resolved_comparison/same_active_set`。
- 名义 KKT 与二阶结果：加载/无载平衡 artifact 的 `/equilibrium/{primal_violation_m,stationarity_inf_nm,dual_violation_n,complementarity_nm,active_singular_values,reduced_eigenvalues,H,Jlength,qpos,tensions_n}`。

## 8. 覆盖率、缺失与未混用的记录

| 证据项 | 覆盖范围 | 结论边界 |
| --- | --- | --- |
| 最终 revision 2 分支、请求和 receipt | 6/6 | 均为 Study v2 / Store v2 |
| 隐式 point / tip / ratio 与保存 FD | 18/18 配对 | 六分支 × 三指标；不是十工况全部梯度 |
| 加载/无载 × 正/负重求平衡的位置与状态 | 24/24 内部状态组 | 保存于六个敏感性 artifact，不存在 24 个独立平衡 artifact ID |
| 名义加载活跃数组、LICQ、严格互补、二阶与四项 KKT 残差 | 6/6 | 六个不同名义加载平衡 artifact |
| 名义无载同类数据 | 6/6 引用，同一个唯一无载 artifact | 不得统计为六次独立无载实验 |
| 扰动活跃集合一致性比较 | 12/12 比较（加载/无载各 6） | 24 个两侧集合可由真值逻辑推得；显式列表 0/24 |
| 正/负状态逐项 KKT 残差、LICQ/严格互补细节、约化谱 | 0/24 | 仅保存资格状态与集合相等比较，不能填入名义值 |
| 独立命名的加载/无载物理平衡残差 | 0/6 + 0/6 | 不以 KKT 或其他轨迹尾窗值替代 |
| 材料参数 h/2 差分 | 0/6 | 仅 h=0.001，无步长收敛阶结论 |
| 完整 KKT 矩阵、参数偏导向量、隐式线性系统残差 | 0/6 独立 artifact | H/Jlength/q/λ 可引用，未重新组装求解或补算残差 |
| 平面外最大范数的普通隐式梯度 | 0/6 | 仅 FD 方向性结果，代码明确拒绝普通 max-norm 梯度主张 |

所有不可提取项统一使用 `unavailable_in_sealed_evidence`，不使用空字符串、估计值或数值 0 表示缺失。名义物理残差字段的缺失也包含字段语义边界，而不是断言历史中完全没有任何静力平衡诊断。

早期输出 `4275000920e828ba7edb585027490c7ed93064bc981159e1c068b7b1b0702d23`（请求 `phs-aa6b718a6eceeded877a22fa5af3b1b359065deb3979e8b64fe68b0e9d58333f`）属于同一九段结构的 s=0.70、F=+0.10 N 加载状态敏感性，但没有 `task_metric_revision=2` 或 `baseline_response`，不计为第七个最终分支。更早 `7fc2c8f1d5e94c2ec5088686282351782ae4917855935913c7ad68fe8c8fe9ca` 是其他 assembly 的 terminal-lever 参数研究，不纳入共同模量六分支表。

检查了 [experiment journal](https://github.com/wran021004-gif/softrobot-agent/blob/9d6d160e050c836b87d0563a497fc0ec1c3761a8/evidence/phs2d_round3_20261028/experiment_journal.json)、[summary](https://github.com/wran021004-gif/softrobot-agent/blob/9d6d160e050c836b87d0563a497fc0ec1c3761a8/evidence/phs2d_round3_20261028/summary.json)、[curvature evidence](https://github.com/wran021004-gif/softrobot-agent/blob/9d6d160e050c836b87d0563a497fc0ec1c3761a8/evidence/phs2d_round3_20261028/curvature_evidence.json)、[v2 configuration](https://github.com/wran021004-gif/softrobot-agent/blob/9d6d160e050c836b87d0563a497fc0ec1c3761a8/evidence/phs2d_round3_20261028/store_v2/configuration.json)、[v2 ledger](https://github.com/wran021004-gif/softrobot-agent/blob/9d6d160e050c836b87d0563a497fc0ec1c3761a8/evidence/phs2d_round3_20261028/store_v2/ledger.json)。configuration 的通用 analysis_protocol 默认参数不能替代实际敏感性请求；summary 的十工况物理通过、曲率记录和数值积分比较不能扩大梯度覆盖。本文没有采用 FULL 结果目录中七段四腱 PHS 的参数、身份或指标。

## 9. CSV 转换规则和精度

| 字段组 | 规则 |
| --- | --- |
| implicit_point_gradient / implicit_tip_gradient | 原 artifact /task_derivatives_du/{point_dx_m,tip_xy_m} ×1000，单位 mm/du |
| fd_point_gradient / fd_tip_gradient | 原 /task_resolved_directional_derivatives 对应字段 ×1000；没有由误差反推 |
| ratio 梯度 | 保留原值，单位 1/du |
| relative_error / relative_error_percent | 原无量纲分数；百分数字段为分数 ×100 |
| positive_step / negative_step | 实际 E 值减基准 E，有符号增量 Pa；normalized_step 另存 h |
| nominal / minus / plus_metric | 从已保存加载位置减同设计的无载位置后，按原指标定义算绝对值/范数/比值 |
| left/right_secant | 从上述三点离线求左右割线；不是额外实验或 h/2 结果 |
| active_set_positive/negative | 由保存的 same_active_set 与源代码精确比较逻辑推得，来源明示；原显式列表缺失 |
| KKT / stability / LICQ | 名义平衡中的保存值；二阶最小特征值仅取保存数组的 min，不重新求特征值 |
| selected_equilibrium_positions_m | 仅六类状态的受力点及 Tip 三维坐标；保留端点复算依据，不输出完整轨迹 |
| source_artifact_refs | 冻结 Git 路径/下标/代码行和归档 member/hash/JSON Pointer，详见第 1 节 |

CSV 数值用原 JSON 解析后的 IEEE-754 双精度值的可往返十进制表示输出；不对科学主数据做报告级舍入。Markdown 数值表通常显示 12 位有效数字、端点表 16 位，不能用其显示截断值替代 CSV 做高精度复算。归档 SHA256 在解析前以原始完整字节核对，不通过重排 JSON 计算。Artifact 工具写入并读回全部表格单元格，逐值验证后序列化为带引号 UTF-8 CSV（LF）。

18 个任务配对的相对误差以原双精度值逐项复算，与保存字段一致；从保存坐标再算 FD 的最大数值差为 `0.0`（此数是不同单位行的机器算术核对统计，不能作为物理量的混合残差）。每行实际同单位差保留在 `fd_recomputation_absolute_difference`，用于验证，没有新求解。

## 10. 论文可以支持的结论

可引用表述：在固定九段四腱 PHS-2D 结构、绑定的九段共同 Young 模量方向及 h=0.001 的归一化扰动下，六个已研究搜索分支均通过所记录的名义 LICQ、严格互补和局部二阶充分条件检查；加载与无载状态的实际正负扰动重新求平衡记录均显示活跃集合保持一致。采用数值偏导的 KKT 隐式微分对设计相关加载−无载相对位移求导，与重新求平衡的中心有限差分在受力点位移、Tip 水平位移和位移比三个标量上相符，18 个配对的最大相对误差为 0.1191223%。

该结论仅验证理想硬单边约束被动平衡模型的局部数值一致性；不代表主动机器人 M2 最优任务能力敏感性，不代表完整 M0–M3 已验证，不代表十个物理加载工况都做了梯度验证，不代表所有结构参数可微。它不延伸到腱路拓扑改变、材料点绑定切换、活跃集合改变或非正则点；不证明全局结构最优、不同软约束动力学模型的梯度一致性或硬件性能。KKT、隐式函数定理与有限差分是采用的已有数学理论，此处证据贡献是实际结构研究中的可定位数值验证。

任务 A 的三个交付文件保持原提交不变。本任务只新增两个 CSV 和本 Markdown；没有修改来源数据、Trace、Store、候选或既有其他工作。
