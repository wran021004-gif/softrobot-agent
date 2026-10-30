# V0：G3 近可行候选的独立物理复验

最终分类为 **valid_failure**。原独立评价执行完整、数值有效；唯一失败项是保持
速度超过原 0.02 m/s 阈值约 6.30×10⁻¹³ m/s。没有修改阈值、容差或比较规则，
没有将四舍五入后的数值当作通过。此次结果属于 Operator 独立验证，不是 G3
当时已完成的 Replay，也不是 V1 的 Main 自主成果或 SELECT。

## 来源与等价性

G3 原 Store 全程通过 SQLite mode=ro/query_only 读取，保持关闭。核对的引用为：

- 原候选：`da1c14850fcd93aa33705f1caae54ceafd5366e9225d77d2737168fd459f2dac`。
- 原数学结果：`536e97dd81f7f1df4e564f6c44b90f75261197137817d25f7df728fa364dcfe6`。
- 原优化 source：`39084ae2f79becfac990df5b9f65d71d67bbf9ed809dc231099a217fe3f00449`。

在新数值验证 Store `p63v0-g3-best-independent-replay-20261030` 中，用原生成器
重建候选，并按原绑定检查确认科学配置、物理结构、数值模型和最终保真度相同。
六通道、50 个 ZOH 区间的完整优化张力序列逐值保留；没有使用 Operator 的旧失败
baseline。仅 provenance 和新 Store 所有权不同。

保留原 12 cells/segment、0.50 s 总时长、最后 0.05 s 保持、0.0005 s 积分步长、
0.01 s 控制/采样周期、零初态、物理边界、模型和完整任务 evaluator。

## 未舍入结果

有符号超额定义为 value − threshold；只有原比较规则判定 passed 才算通过。

| 指标 | 独立 Replay 原数值 | 原阈值 | 有符号超额 | 原判定 |
|---|---:|---:|---:|---|
| 终点位置误差 m | 0.009999999999944607 | 0.01 | −5.5393190034891404e−14 | 通过 |
| 最大保持位置误差 m | 0.009999999999944607 | 0.01 | −5.5393190034891404e−14 | 通过 |
| 最大保持速度 m/s | 0.020000000000629993 | 0.02 | +6.299925858765931e−13 | 失败 |
| 张力越界 N | 0.0 | 原允许误差 1e−8 | −1e−8 | 通过 |
| solver errors | 0 | 0 | 0 | 通过 |

保持窗口完整覆盖 6 个均匀采样点；51 个状态采样、1000 个积分步；执行完整，
evaluation_validity=valid。原 endpoint evaluator 判定位置通过，但完整任务验收
还包括保持速度，因此最终 acceptance.accepted=false、status=valid_failure。
实际张力范围为 3.949152477943472–6.033830005674288 N，满足原 0–8 N 边界。

## 与数学轨迹的比较

原 source 不含 mathematical_outputs，因此原 Replay 返回的自动 comparison 字段
为 unavailable，第一份执行审计暂记 comparison_unresolved。随后从原数学结果的
`/native_dynamics/optimization/best/outputs` 读取保存采样，与已完成 Replay 作只读
比较，没有新增积分、优化或 Replay。

51 个状态采样全部对齐；最大时间戳差为 3.885780586188048e−16 s，属于浮点累计
表示差。最大位置差、最大速度差和逐区间实际张力差均为 **0.0**。原数学输入数组
按区间索引，物理第 k 个 post-step 采样对应第 k−1 个区间，比较保留了这一相位。
三个任务指标与原数学结果完全一致，没有证据表明存在新的物理机制差异。

`p63v0_replay_audit.json` 保留原执行/自动比较状态；
`p63v0_comparison_audit.json` 给出解决后的来源比较与最终 valid_failure 分类。
原数学结果、V0 Store 和 G3 Store 的不可变记录均未改写。

## 次数、费用与证据

恰好一次原独立 Replay，0 次 Provider、0 次 Reporter、0 次重试。
1 build、1 rollout、1000 physics steps、101 forward evaluations；kernel wall
0.28938729999936186 s，已包含在 Worker wall 3.054287699982524 s 范围。
候选重建计费 0.4893179000064265 s；本次数值工作共 3.5436055999889504 s。

独立结果引用：`180c88b360b0d01bfc63d3d1554c499265511281d66bdd70119f6a5aa879d7d5`。
原 evaluator 及验收 profile 的引用和完整回执保存在两份审计及 V0 Store 中；完整
采样数组保留在 Store，不复制到报告。V0 已按原工程关闭机制结束，未进行 SELECT。

直接相关检查为：原始三方绑定、重建科学配置等价、最终保真度、完整张力序列、
原独立 evaluator 的精确阈值比较、保存轨迹对齐，以及原 Store 大小/mtime 未变。
没有重跑 C0–G3 全套回归，也没有修改生产源码。
