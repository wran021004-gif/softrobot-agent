# P6.3-H：结构修改方向研究

对本任务的第一段长度，现有 Conic 给出跨两个步长稳定的“缩短”局部数值方向，但 Native 重新优化没有验证这一修改建议。缩短在两个步长下都使最终 J 变差；加长 2 mm 有改善，加长 4 mm 变差。因此记录为**模型方向与非线性观察冲突、有限预算方向不稳定**，不主张严格梯度或稳定修改建议。

研究使用 H1 同一 Study、任务、六腱/两段拓扑和原 FamilySpace。第一段长度 `segments.0.length_m` 的单位为 m，基准 0.160，使用 ±0.004 和 ±0.002。参数由当前有效连续域及原 `family_parameters` 准入确认，构型通过原生成器产生；未预设增加刚度更好。选择长度的依据是 H1 Direct Native 的最终最坏约束已经变为端点位置，而该参数在原 Conic 敏感性中实际支持重建比较。

## 三种效应

固定控制效应采用所有结构完全相同的绝对 pretension 序列，以各 T1 第一次 rollout 衡量；没有跨结构隐式继承任务接受状态。Conic 的 fixed-control 效应则保持基准 **Conic** 最优绝对输入序列，两者不是同一控制，不能将两个导数直接视为同一物理量的交叉验证。

Conic 调用原 `controlled-capability-sensitivity-v1`，复用当前 Study 已保存的基准及四个 GVS 模型；新模型构建 0，5 次 Conic 和 4 次 dual-face solve。返回值为局部数值方向，envelope regularity 未证明，两个步长的 dual-face 均 unresolved。

Native 的五个结构都使用原 baseline 初始化、同一四 knot Response、200 callback/60 迭代上限及完整约束。实际五组均为 200 callback、8 次迭代和8次完成响应步。原 T2 对 h、h/2 分别聚合三点 T1，复用基准，不再次执行优化或积分。每个最终控制另经原独立 Replay，六次 Replay 中的五次对应这五个结构，全部失败。

| 第一段长度 (m) | Conic 重优化 J | Native 固定 baseline J | Native 重优化 J | 末端/保持误差 (m) | 保持速度 (m/s) | Native 最坏约束与时间 |
|---|---:|---:|---:|---:|---:|---|
| 0.156 | −0.600000 | 17.174746 | 0.722863 | 0.017207 / 0.017207 | 0.034457 | 保持速度，0.45 s |
| 0.158 | −0.400000 | 18.810606 | 0.657500 | 0.016575 / 0.016575 | 0.033069 | 末端位置，0.50 s |
| 0.160 | −0.200000 | 20.451755 | 0.539774 | 0.015398 / 0.015398 | 0.030755 | 末端位置，0.50 s |
| 0.162 | ≈0 | 22.092217 | 0.442640 | 0.014002 / 0.014002 | 0.028853 | 保持速度，0.50 s |
| 0.164 | +0.200000 | 23.726257 | 0.812971 | 0.013900 / 0.013900 | 0.036259 | 保持速度，0.50 s |

固定 baseline 序列下，缩短确实降低任务违反；重新优化控制后，这个方向反转。这说明固定控制结构响应与相同搜索机会下的最佳控制表现必须分开讨论。

## 差分与可信度

数值均为 signed J / m；原始每约束值、时刻、来源和单位完整保留在 summary 及内容寻址归档。

| 效应 | 步长 (m) | 左割线 | 右割线 | 中心有限差分 |
|---|---:|---:|---:|---:|
| Native 固定 baseline | 0.004 | +819.252 | +818.626 | +818.939 |
| Native 固定 baseline | 0.002 | +820.574 | +820.231 | +820.403 |
| Native 重优化 | 0.004 | −45.772 | +68.299 | +11.263 |
| Native 重优化 | 0.002 | −58.863 | −48.567 | −53.715 |
| Conic 重优化 | 0.004 | — | — | +100.000 |
| Conic 重优化 | 0.002 | — | — | +100.000 |

Conic 在固定基准 Conic 控制下的中心响应约 −52.081 / −120.395，而条件 envelope 两步均约 +100。这些不同的效应和不稳定固定控制响应均保留，不能只选择重优化数值掩盖差异。Conic 的 preferred direction 为 decrease，`direction_status=stable_reoptimized_direction_envelope_unresolved`，strict gradient 不可用。

Native h 的左右割线异号、h/2 的左右割线同为负，中心差分跨尺度变号。h 的原 T2 原因包括 `FLAT_OR_OPPOSING_LEFT_RIGHT_RESPONSE` 和 `CONTROL_SEARCH_QUALITY_UNRESOLVED_AT_LIMIT_OR_FAILURE`；h/2 仍存在后者。五组均耗尽 callback，无法证明控制搜索已解决到可比最优质量，因此 T2 均保守返回 unresolved。

最坏约束在端点位置与保持速度之间切换。加长 4 mm 虽继续改善位置误差，却恶化速度，故其 J 变差；不能把不同物理目标的导数混成单调结构收益。零初态局部 Conic 的 world-x 一阶状态/输入系数为零，其 x 偏差随长度改变，给出几何主导的稳定 +100 数值斜率；这不证明非线性 x 不可控或 MuJoCo 会按该方向改善。

当前可保留的有限结论是：**加长 2 mm 在这一次同预算搜索中优于基准，但不构成跨尺度稳定建议；Conic 所建议的缩短方向得到反例。** 没有结构通过完整任务；没有 time-to-success、全局最优、不可行性、连续时间保证、硬件或重复性结论。

## 证据入口与 Main

`numerical_summary.json` 的 `sensitivity` 保留全部 fixed-control、reoptimized、envelope、dual-face、适用性和模型来源；`structure.structure-full/structure-half` 保留原 T2、每指标割线和已计费 T1 引用；`native` 和 `replays` 保留完整指标与独立原 acceptance。`best_found_J.csv` 和 `research_curves.png` 由保存历史生成，未新增仿真。

沿用现有 mathematical capability 详情、结果 summary、原 Reporter 的来源引用和 `research_investigate` 阅读接口，Main 可以看到方向状态、假设和限制；没有增加第二个规划 LLM，也没有固定程序自动修改结构。新增的 bounded_control_initialization 问题与原 Native control_feasibility 语义分离。接口及控制 handoff 回归测试使用清楚标注的 fixture，不充当上述科学结果。

结果属于 `codex/p6-3h-conic-native-study` 独立分支，未自动合并。实验已停止，未扩展到多参数搜索或完整自主 Study。成本与恢复缺口见配套《Conic → Native 成本对照》。

定向验证最终覆盖 82 个不同测试：80 项主回归、5 项末次入口/成本检查（4 项复测）及 1 项新增 Conic Main Mock wire 检查，最终均通过。逐日志及初次 fixture 修正保留在证据目录；Mock 计费不属于本研究科学账本。归档 91 个成员逐哈希核验通过，A/B 完整请求仅 source 不同，成本总和核对通过。
