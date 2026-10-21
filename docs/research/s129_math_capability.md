# F1-B：带符号任务能力与结构—控制对照

2026-10-21；分支 `feat/s129-math-capability`，从 F0
`6e5c0e4c7f3af62cc345d44461369d795af4da4b` 开始，初始工作树干净。
仅开发 B 线，未合并其他分支，未修改 S12.8 封存证据。

## 审计与边界

已审阅根 AGENTS、F0 evidence_reporting、task_analysis、任务/报告契约、
GVS 与 SoRoSim 分析接口、trajectory/kernels、任务适配、Store/dispatch、
S12.8 数学与预算诊断及交付。已有静态 IFT、Gramian、端点与制动、
离散轨迹重放和必要条件排除均保留。
静态结构敏感性不能充当重优化后的任务能力梯度，优化失败不能证明不可行。

F0 `ScopedMathematicalClaim`、`MathematicalEvidence`、`MathematicalQuantity`、
`ResultCard` 类型没有修改。B 线适配放在 `tools/research/capability.py`；
公共请求只增加一个 operation 和可选比较参数，旧请求序列化不增加空字段。
未修改主 Agent 会话、Provider、报告送达、任务验收或证据注册机制。
`state.py` 和 manifest 的改动仅把新数值源加入现有实现指纹。
生产 Python 净增 365 行：新数值核 185 行、B 线适配 127 行，其余为局部接入与复用。
核心函数为 `task_capability`、`prepare_trajectory`、`comparison_context`、
`compare_control_response`、`populate_mathematics`；新增测试 306 行。

## 可运行入口与定义

原 `research_analysis` / `analysis.dispatch` 接受：

```python
query = dict(candidate=candidate_ref, operation='task_capability',
    operating_point='controller_start_input', protocol=frozen_analysis_protocol)
# 通过原 dispatch/guard 获得 baseline_result_ref 后，对另一已授权候选：
query_b = dict(query, candidate=changed_candidate_ref,
    capability_comparison=dict(baseline_result=baseline_result_ref,
        variable='segments.near.length_m', normalization_scale=0.16))
```

底层 `task_capability(model, requirements, protocol)` 优化；传入
`applied_input_n` 则只计算给定物理张力序列，允许离线独立重放。
TaskAnalysisRequirement 仍由冻结任务适配器产生，没有第二套任务规范。

对于范数约束，`g=||y-reference||/radius-1`。
对于分量区间，残差 `r=y-reference`，保留所有分量的
`(lower-r)/s` 和 `(r-upper)/s`，`s=max(abs(lower),abs(upper))`。
这是原轨迹约束尺度的带符号形式；原单位、上下界、reference、时刻和索引全部保留。
`g<0/==0/>0` 分别表示内部、边界和违反；不截断为零。
零半径范数或全零区间没有该相对归一化尺度，明确 `not_applicable`，不擅自添加物理容差。

`G=max_i g_i` 是一个控制序列的任务分数。
理想定义仍是 `V_tau(d)=inf_U G_tau(d,U)`；实际返回
`best_found_violation`，不把它命名为已知的最优 V。
SLSQP 使用 epigraph `rho>=g_i`、已有解析约束导数、真实张力盒，
从名义输入、25% 和 75% 张力盒三个确定起点求解。
每起点的上限来自已有 `endpoint_max_iterations`，`ftol=1e-12`。
合法起点、迭代候选和最终控制都参与最佳已发现值选择；
不要求 solver.success 才保留有用控制，也不会信任成功标志下的 NaN。

`prepare_trajectory` 从旧 trajectory 内提取，没有复制 ZOH、输出映射或重放。
`verify_witness` 独立递推核验输入、状态和输出，最后再从重放裕量计算 signed score。
保存每个起点、停止状态、迭代数、最终 epigraph residual、被选控制来源、
输入余量、活跃/并列瓶颈、状态偏移与重放误差。
状态偏移没有已验证的局部有效半径；不因重放成功宣称非线性模型准确。

## 证据强度与覆盖

| 输出 | F0 status / 含义 |
|---|---|
| `replayed_violation` | `verified`：合法输入和离散重放后的数值评分；未验证最优性 |
| `best_found_violation` | `unverified_estimate`：本次搜索的最好数值，不是最优值证书 |
| `lower_bound=-1` | `verified`：由范数非负、区间半宽不超过最大绝对界直接得到的解析下界；通常很弱 |
| `witness_upper_bound_estimate` | `unverified_estimate`：合法控制的 G 在精确算术下给出上界，但此处浮点算术没有严格包围认证 |
| `upper_bound`、`optimal_task_violation` | `unavailable` / null；不捏造严格上界或最优值 |
| 结构 delta / normalized secant | `unverified_estimate`：本次有限对照，没有包络导数或区域下降保证 |

这些界和分数明确只针对已分析的采样子问题。缺失样本时，尤其不能把子问题的
可行点上界升级为完整任务上界。旧 trajectory 的必要条件排除证书仍独立保留，
新 minimax 不用“正的目标值”制造排除证书。

只有合法输入、完整数值重放通过且 signed G<=0 才给出采样 `feasible_witness`。
若 G>0，仍可输出已核验控制与瓶颈，但 claim 为 `inconclusive`。
未知物理、输出、单位、采样相位或不对齐时间按原适用性逻辑处理。
保存状态可分析剩余时间；过去样本保持 unchecked，`full_task_supported` 不升级。
完整采样见证也不是连续时间、非线性或独立物理验收。

## 固定拓扑对照与成本

比较仅接受已有 Store 中登记的、同实现/任务/协议/工作点的合法基线结果。
现阶段支持 `segments.<id>.length_m` 和显式数值 `young_pa`；
材料场景标签、拓扑和 NMPC 速度权重不作为连续结构变量。
候选仍经原 verify_candidate；除一个参数外，参数集、source/profile、任务、
controller/backend/model 必须一致，构建后再次核对采样、输入盒和通道/坐标顺序。
仅支持两种真实任务起点的结构对照；不同 saved_state 之间不擅自建立可比性。

当前候选重建自己的 GVS 模型并独立求解，然后重放基线的同一物理张力序列。
分别记录 `fixed_control_delta` 和 `reoptimized_control_delta`；
归一化割线是 `delta / actual_step * normalization_scale`，不是最优值梯度。
基线读取得到原 Store 引用；不重新求解基线。
一次普通能力分析计 1 次数学评估，带对照计 2 次（本候选求解与固定控制重放）。
原 dispatch 统一预留、worker 完成记账、持久化和幂等复用；预算不足在 worker 前拒绝。
原 charged_numerical_s 是 worker wall，包含建模；另存 kernel 与各起点 wall，不能重复相加。
最终工程对照两次 worker 分别为 8.9974 s、9.0364 s（合计 18.0338 s）；
两次 minimax kernel 约 0.4508 s、0.4505 s，固定控制重放约 0.0019 s。

## 离线工程案例

完整可核对产物在 [gvs_pair.json](../../evidence/s129_math_capability/gvs_pair.json)。
这是原保存配置生成的隔离工程夹具，没有启动正式自主 Study、Provider、
物理 rollout、NMPC、PPO 或 MATLAB Engine。
模型为 24 状态、6 张力、35 个控制区间，控制周期 0.01 s，任务 0.35 s；
覆盖终点位置及 0.30–0.35 s 的位置/速度共 13 个约束样本。

| 情形 | 最坏 signed G（越小越好） |
|---|---:|
| 近段 0.160 m，控制独立优化 | -0.1999999516 |
| 近段 0.161 m，固定基线控制 | -0.0829884411 |
| 近段 0.161 m，控制重新优化 | -0.0999995173 |

固定控制变化 +0.1170115105，重新优化后变化 +0.1000004343。
采用 0.16 m 的参数尺度，两个有限割线分别约 18.72184、16.00007。
此次加长 1 mm 后重优化缓解了固定控制退化，但两边真正的最优能力排序尚未认证。
基线瓶颈是 0.33 s 保持位置；变化候选为 0.30 s 保持速度。
两个数值见证的最小张力余量约 0.635 N、0.689 N，重放误差分别约
3.0e-15、1.8e-15。三个起点在两边都达到 100 次上限，均未报告收敛。
数值见证与未收敛同时成立；这正是本功能保留有用科研信息的情形。

Agent 的结果卡可读到 signed G、瓶颈、求解起点分歧、输入余量、结构差值、
验证范围与 exact source pointer；完整矩阵/输入/重放留在原 Store 数值产物。
建议进一步区分求解预算不足、局部模型偏差与模型内输入能力限制，
不能直接要求修改绳路，也不输出未经标定的机制概率或 VOI。
工程 Store 是临时夹具；导出保留两份完整原结果及其 artifact IDs、候选、冻结配置、
worker 日志、源码指纹和环境，可脱离临时目录核对原结果卡数值。

## 验证与限制

使用 `.mainline5-env`，`PYTHONPATH=.;tests/research;C:\Program Files\MATLAB\R2024a\extern\engines\python\dist`，
BLAS/OMP/MKL 线程数均为 1。MATLAB 路径仅供已有 capability discovery 使用。

```powershell
& D:\softrobot-agent\.mainline5-env\Scripts\python.exe -m unittest `
  test_s129_task_capability test_trajectory_feasibility test_task_analysis_contract `
  test_research_reporting test_mainline test_s127_math_admission test_evidence_policy test_sorosim_analysis -v
git diff --check
```

新增 14 项覆盖符号、单位、边界、minimax 与旧能量目标的区别、联合冲突、
失败/NaN/起点分歧、重放失配、部分时间/零时域、5/7 通道、unsupported、
F0 原始指针、比较混杂拒绝、预算准入及真实 GVS 对照/幂等记账。
SoRoSim 回归仅读取已有保存结果并使用 mock 接口，无新 MATLAB 求解。

最终按唯一测试计 **87/88 通过**：新增 **14/14**，既有 **73/74**；无未解决错误。
验证统计、唯一已知基线失败及复现说明见 [tests.json](../../evidence/s129_math_capability/tests.json)。
旧 `test_saved_m2_decision_boundary_and_paged_retrieval` 的摘要压缩比例断言
`11501 < 8192` 不成立；将 analysis 的两个摘要函数替换为 F0 原始源码后，
同一断言仍失败。B 线没有调整 A/F0 摘要大小或修改这项旧测试阈值。

尚未实现严格浮点上界、更强对偶下界、最优性/KKT 认证、完整包络梯度、
区域下降保证、非线性重放、跨拓扑导数、概率 VOI；未验证新功能的现场物理表现。
这些限制不妨碍合法输入、任务瓶颈和有限结构—控制对照作为有范围的科研依据。
