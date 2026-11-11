# M1 Full：三目标主动 Reach/Hold

Study：`m1-core-full-20261111`。本文件整理既有正式分支，不新增计算；统计只包含正式分支。研究结果是同一两段六腱结构在三个条件下分别获得合法控制，并通过独立评价和联合 SELECT。主要贡献是自主控制研究与控制修正。

## Task Description

| 条件 | 世界坐标目标 [x, y, z]，m |
|---|---|
| positive_high | [0.285, 0.035, 0.185] |
| negative_low | [0.275, -0.040, 0.135] |
| central_high | [0.295, 0, 0.215] |

三个条件共享物理结构与离散模型，允许分别使用合法控制。终点及保持窗位置误差不超过 10 mm；最后 0.06 s 保持速度不超过 30 mm/s。执行时长 0.6 s，物理步长 0.001 s，控制及正式采样周期 0.02 s，保持样本为 0.54、0.56、0.58、0.60 s。保留原重力、10 g 载荷、零关节初态、张力边界、执行完整性和错误数检查，不放宽阈值。

## Robot Structure

| 项目 | 实际结构 |
|---|---|
| 段数 / 腱数 | 2 / 6 |
| 段长 | 0.16 / 0.11 m |
| Young's modulus | 7.2 / 5.4 MPa |
| 截面 | 近段椭圆；远段渐变矩形 |
| 腱路 | 两组三腱；近组锚定近段，远组经导向锚定远段；相对相位 60° |
| 路由半径 / 离散 | 18 mm / 每段 12 cells |
| 理想张力范围 | 每通道 0–8 N |

生成后没有改变段长、材料、截面、路由或拓扑。`candidate_18`、`candidate_206`、`candidate_446` 是同一结构针对三个条件的绑定对象，不能算作三次形态设计。

## Initial Research Hypothesis

Main 提出，分布于近、远两段的两组三腱可提供分布式弯曲驱动，使同一结构通过条件专属控制到达不同方向目标。其可检验预期是：路由合法、有限时间轨迹稳定，且有界张力控制能同时降低位置误差和保持速度。本次没有相位或跨度的单变量对照，因此最终通过只支持这个组合结构可用，不能归因于某一个路由参数。

## Main's Research Decisions

1. 保留初始结构，优先研究各条件的有限时间控制可行性。
2. 正目标经 Native 优化后独立通过；负目标首次数学结果略超速度边界，继续有限精修后独立通过。
3. 中央目标的三结点控制接近约束边界，但独立评价严格失败；改用 Direct 研究仍未获得通过裕量。
4. 请求完整控制网格。原每请求 4 结点额度阻止了 30 结点请求；用户授权将上限提高到 30，并从指定拒绝点接续。该接口及额度修复属于工程干预，不是 Main 自主产生的科学结论。
5. 接续后的两次完整网格计算均执行不完整，Main 转向局部物理响应探针；发现一个有效单通道修正后停止探测。
6. 读取三个条件的独立通过结果，执行同一结构的联合 SELECT，随后 STOP。

## Mathematical Analysis

| 次序 | 实际方法 | 目的与结果 |
|---|---|---|
| 1 | `mujoco_nonlinear_task_capability_v1` | positive_high：三结点控制研究，得到可独立通过的控制 |
| 2 | 同上 | negative_low：首次结果保持速度略超严格边界 |
| 3 | 同上 | negative_low：有限精修，获得通过裕量 |
| 4 | 同上 | central_high：位置和速度接近边界，独立评价仍失败 |
| 5 | `mujoco_direct_control_v1` | central_high：未改善最佳边界结果 |
| 6 | `mujoco_nonlinear_task_capability_v1` | central_high：30 结点完整网格，执行不完整 |
| 7 | `mujoco_direct_control_v1` | central_high：30 结点完整网格，执行不完整 |

共 5 次 Native 非线性任务能力研究、2 次 Direct 控制研究，主要属于控制可行性分析。没有据此获得结构机制辨识、结构敏感性或 Coupled Block 的成功结果。

两次完整网格搜索均在试探轨迹约 0.231 s 出现 floor/payload 接触，触发 `NATIVE_V1_REQUIRES_FINITE_CONTACT_FREE_UNCONSTRAINED_STATE`；各记录 182 次 rollout 尝试、108,831 个物理步。失败说明这些试探越出方法的无接触状态适用域，没有形成可直接验收的新完整控制，也不证明结构不可行或更多时间自由度无效。

## Control Feasibility and Physical Response

中央目标原独立评价的保持误差为 0.010000000000387073 m，保持速度为 0.030000000000649462 m/s。尽管超限极小，仍沿用严格失败判定。Main 因此选择在原物理执行中直接测量局部控制效果，避免继续依赖已遇到适用域问题的搜索。

`initialize_control(method=physical_response)` 原计划最多使用 8 次物理评价、探测 6 通道，差分步长 0.02 N、信赖半径 0.1 N。实际复用已有基线，只新增两个独立物理探针：对 tendon_0 全时段加 0.02 N 未通过；对 tendon_1 全时段加 0.02 N 通过，触发 `first_original_task_pass` 提前停止。未完成六通道响应矩阵或正规化最小二乘拟合。

## Final Control Modification

最终中央目标控制相对原基线仅将 **tendon_1 的全时段张力增加 0.02 N**，其他通道保持基线。该局部控制修正具有原任务下的通过证据；它不是结构改造，也不构成六通道联合拟合或单腱机制的普遍因果证明。

## Final Results

下表沿用原始最终指标及给定精度，不重新计算验收。

| 条件 | 终点误差 mm | 保持误差 mm | 保持速度 mm/s | 独立评价 |
|---|---:|---:|---:|---|
| positive_high | 3.45237 | 4.09633 | 28.32184 | 通过 |
| negative_low | 8.34697 | 9.94547 | 29.97925 | 通过 |
| central_high | 9.73155 | 9.98103 | 29.85012 | 通过 |

三条件共享同一物理结构和离散模型，分别采用合法控制；联合 SELECT 接受 3/3 条件。数学内部 rollout 与独立物理评价分开计数。

## Computational Cost

| 指标 | 正式分支数值 |
|---|---:|
| Provider Requests | 48 |
| Mathematical Evaluations | 7 |
| Physical Evaluations | 5 |
| Input Tokens | 1,336,728 |
| Output Tokens | 30,723 |
| Successful Conditions | 3/3 |

5 次物理评价包括正、负目标各一次通过、中央目标原基线失败及两个局部探针。废弃分支不计入上述请求数、Token 或科学成本；此处不合并其他分支费用。

## Limitations

结果限于原数值模型、离散、初态和有限时域；没有形态因果对照、连续时间保证、硬件或普遍鲁棒性结论。负目标速度和中央目标保持误差仍接近阈值。运行包含用户预算授权、结点接口修复及指定检查点接续，不能描述成全程无人工干预的固定版本运行。

Reporter 确有解释产物，但其解释改变 Main 后续决策的独立作用为 UNKNOWN。唯一保存的显式 Knowledge 读取由 Reporter 读取 `general-material-inertia@1`；不能把配置中的其他通用 Skill 全部记为 Main 已读。具体使用边界见 [能力盘点](analysis_capability_inventory.md)。

整理来源：原仓库 `paper_experiments/case_studies/M1_main_full.md`、`paper_experiments/m1_study_manifest.json`、已有 `audit_evidence/m1_case_claims.json` 及既有抽取中的最终评价/处置摘要。初始 Core 为 `2c83f8b7bd654328dd7648f844295c54a7c15223`，接续 Core 为 `7f034a60f1ea0be5ac3174c5b6c8908a8f56dd40`；本轮没有修改它们。
