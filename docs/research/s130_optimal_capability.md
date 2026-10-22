# S130-T1：sampled-affine signed minimax 的凸优化数值对照

2026-10-22。仅 T1；未实施 T2 敏感性或 T3 接入。

## 仓库审计与复现来源

使用已有 `.worktrees/s130-optimal-capability`、分支 `research/s130-optimal-capability`。
开始时工作树干净，没有已有 T1 实现。实际 HEAD 为
`40a1a3409209565b1036c4f6fc2aaad33d3cbfa7`，是指定研究基线
`13ddf460f9cb792cfb8e809a4e4f225c0bfd22f0` 的祖先，相差四个 F2/F2.1 提交。
没有重建、reset、切换、合并或覆盖工作树。主 checkout 为 `feat/gvs-dynamics`
`d629a80d`，存在无关未跟踪文件，未改动。主 checkout 没有 AGENTS.md；遵守目标工作树的 AGENTS.md。

已审阅 `task_capability.py`、`trajectory.py`、`platform_analysis.py`、
`tools/research/{capability,analysis,task_constraints}.py`、现有数学测试和 B/F2 文档，
并从指定基线只读查看 F2.1 文档。两版的上述数学内核、分析 schema 及保存的
`evidence/s129_math_capability/gvs_pair.json` 完全一致；没有把 F2.1 主链路改动移入本分支。

原始 B 文件包含完整的两个 `EndpointLinearizedModel`、`TaskAnalysisRequirement`、
`TaskAnalysisProtocol`、控制及原始结果身份，因此无需重新构建模型。
文件 SHA256 为 `cb20119c565f950242754c862295c740f0dc69331f840586c59f534cca60add6`。
原始输入在 `/baseline`、`/changed` 下，新结果保存其源路径、artifact IDs、输入内容哈希和实现哈希。
本轮没有 GVS、MATLAB、MuJoCo、NMPC、PPO 或 Provider worker。

新增入口：

```python
from extensions.math_analysis.conic_capability import conic_capability
result = conic_capability(model, requirements, protocol,
                         initial_delta=None, solver_options=None,
                         check_tolerance=1e-7)
```

这是可独立调用的离线数学核，不是 Agent tool。原 `task_capability()`、默认 SLSQP、
正式注册、Agent、Reporter、Store、Session、预算、验收、既有证据文件全部未改。

## 与原数学问题的等价性

直接复用 `prepare_trajectory()`、`normalization()`、`verify_witness()`。
令 `z` 为按原控制顺序堆叠的物理张力增量，`u0` 为名义张力，
`l=-u0`、`h=tension_limits_n-u0` 按时域重复。输入合法性仍是绝对张力
`0 <= z+u0 <= tension_limits_n`。未使用新的任务参数或物理模型。

每个实际覆盖的约束/采样行有残差 `r_i(z)=M_i z+b_i`，其中 `b_i`
包括初始扰动、仿射漂移、工作点输出和该时刻参考。采样映射沿用精确 ZOH，
边界输出使用前一个 hold；原点 feedthrough 使用已知的 previous_applied_input_n。
不对采样网格插值，不补齐未覆盖的过去时刻。零剩余时域保留常量行和一个 epigraph 变量。

原目标与新问题均为

\[
 V=\min_{l\le z\le h}\max_i g_i(z)=\min_{z,t}t,\qquad g_i(z)\le t.
\]

- 范数：`g=||r||/rho-1`，显式 SOC 为 `(t+1,r/rho) in Q`。
- 区间：`s=max(abs(lower),abs(upper))`，分别加入每个分量的
  `(lower-r)/s <= t`、`(r-upper)/s <= t`，不丢弃某一侧。
- `rho=0`、`s<=0` 或非有限尺度返回 `not_applicable`，不添加任意 epsilon。
- 纯区间任务是 LP，含范数时是 SOCP。正尺度仿射范数/仿射函数凸；张力盒紧且非空，
  有限数据与至少一个被分析行保证最优值存在。由于张力界宽度为正，可取盒内部的 `z`
  和足够大的 `t` 严格满足所有锥约束，满足 Slater 条件。零控制维数时同理选足够大的 `t`。
  因而该有限凸问题在精确实数算术下具有强对偶；浮点求解结果仍需要下述检查。

`-1` 是解析严格下界：范数非负；区间每个分量的两侧最大值至少为
`-(upper-lower)/(2s) >= -1`。本轮的等价性仅针对原函数**实际分析的采样子问题**，
不是完整机器人任务或连续时间问题。调用者仍须提供适用的冻结局部模型，
本数学核不替代已有 `model_assessment/check_analysis_applicability` 的物理支持判定。

## 对偶量与独立数值检查

实现用显式规范化 SOC，避免 CVXPY 隐含辅助变量的身份歧义。
对 SOC `(t+1,(M_i z+b_i)/rho_i)`，CVXPY 公共 dual_value 为 `(alpha_i,v_i)`，
约定拉格朗日项为

\[
 -\alpha_i(t+1)-v_i^T(M_i z+b_i)/\rho_i.
\]

原 signed minimax 乘子就是 `lambda_i=alpha_i`；范数支撑方向为 `-v_i/alpha_i`
（alpha>0 且 KKT 成立时）。零残差处使用锥向量，不除以残差范数。
区间各侧公共 inequality dual_value 就是该侧的 signed 乘子 lambda。
若改用物理单位约束 `||r||-rho-rho*t<=0` 或 `lower-r-s*t<=0`，
对应乘子为 `lambda/rho` 或 `lambda/s`，已另存 `physical_excess_multiplier`。
本实现没有另外缩放控制变量，盒乘子对应物理 N 坐标的增量上下界。

独立检查，不借用求解器报告残差：

1. 从原采样映射计算 epigraph 最大违反和张力盒违反。
2. 从公开原始变量和乘子重算 z 驻点残差、`|1-sum(lambda)|`、
   SOC 对偶锥/非负乘子违反、锥内积及线性/盒互补残差。
3. 重算拉格朗日常数项（含盒乘子）作为 `dual_objective_estimate`，
   `raw_duality_gap=t-dual_objective_estimate`。若驻点/锥条件仅近似满足，
   该常数项不是严格对偶可行值。
4. 对原始控制越界不超过 `protocol.endpoint_check_atol` 的情况，显式 clip 到盒，
   保留 raw_primal 与 `box_repair_inf_n`；更大越界不给见证。重新调用 `verify_witness()`
   递推状态和输出，再从其物理 margins 计算 signed score。不会只检验组装矩阵自身。
5. 保存每个任务行的原始物理 margins、违反、单位、参考、采样索引、重放误差、
   完整状态序列、最小物理张力余量及原始/重放控制序列。

还计算不要求驻点完全成立的**张力盒支撑下界估计**。令非负权重由各行的
`max(alpha,0)` 归一化为总和 1；范数方向
`d=-v/max(max(alpha,0),||v||,tiny)`，故实数算术下 `||d||<=1`。
区间行直接使用它的仿射 signed 函数。所有支撑函数的加权和是 `a^T z+c`，满足

\[
 \max_i g_i(z)\ \ge\ \sum_i w_i\ell_i(z)=a^Tz+c,
 \qquad L=c+\sum_j\min(a_j l_j,a_j h_j)\le V.
\]

这里的公式在满足精确锥/归一化条件时严格成立；代码中的方向、权重、求和、
模型离散化均用浮点数，**没有有向舍入或区间包围**，故计算出的 L 明确标为
`numerically_checked_float_not_rigorous`，不声称严格有效浮点下界。
保存归一化权重、支撑方向、权重和与盒修正项，可以独立复核该估计。
`replayed_support_gap=G_replay-L` 比直接假设浮点驻点精确成立更有用。

`optimality_status=numerically_checked` 要求公共 solver status 为 `optimal`，
有效独立重放、epigraph/盒检查，以及上述驻点、对偶锥、互补和两种 gap 均通过。
检查阈值为 `1e-7`；分数、gap、互补使用 `1e-7*(1+max(|G|,|t|))`，
物理盒/重放用协议的 `endpoint_check_atol`。这是一套公开的数值判据，不是证书。

实际核对了安装版本的 `CLARABEL.invert`、`parse_solver_opts` 源码和小问题 API。
CVXPY 1.9.3 的 Clarabel 适配器只填入 solve_time、num_iters，不暴露底层原始/对偶残差、
对偶目标或 extra_stats；这些 solver-reported 字段返回 null/unavailable，不能伪造。
记录的公共 solver status、objective、iterations、solve_time 是求解器报告；wall/kernel 时间由本地计时。
官方接口依据：[CVXPY solver statistics](https://www.cvxpy.org/tutorial/solvers/index.html#solver-stats)、
[Clarabel Python problem format](https://clarabel.org/stable/python/getting_started_py/)。

## 科学对照实测

完整新产物：[comparison.json](../../evidence/s130_optimal_capability/comparison.json)。
两模型均为 24 状态、6 张力通道、35 个控制区间，控制步长 0.01 s、时域 0.35 s。
覆盖原来全部 13 个任务约束采样行：终点位置以及 0.30–0.35 s 的位置/速度。
原文件的矩阵、任务、协议直接验证为现有 schema，SLSQP 与 SOCP 输入完全相同。

| 量 | 0.160 m | 0.161 m |
|---|---:|---:|
| 历史 SLSQP / 本次重新优化 SLSQP G | -0.1999999515720519 | -0.09999951729772974 |
| SOCP 独立重放 G | -0.19999999998602022 | -0.09999999999948331 |
| 支撑下界估计 L | -0.20000000017849437 | -0.10000000011124482 |
| G-L | 1.92474e-10 | 1.11762e-10 |
| SLSQP G 减 SOCP G | 4.84140e-8 | 4.82702e-7 |
| 原始 epigraph 最大违反 | 7.12039e-12 | 0 |
| z 驻点无穷范数残差 | 3.38591e-12 | 2.54845e-12 |
| t 驻点残差 | 5.20739e-12 | 2.56617e-12 |
| 对偶锥违反 | 0 | 0 |
| 最大绝对互补残差 | 1.88111e-12 | 9.93546e-13 |
| 原始对偶目标估计 | -0.2000000006700257 | -0.10000000032843567 |
| 原始 t-dual gap | 6.76885e-10 | 3.31876e-10 |
| 最大预测/递推重放差 | 4.05231e-15 | 3.21965e-15 |
| 最小张力余量 N | 2.64875 | 2.64403 |
| Clarabel 迭代数 | 13 | 11 |

两边 solver 均为 optimal，数值最优性检查通过，完整采样见证均满足 signed G<0。
比解析 -1 得到了显著更紧的下界**估计**。虽然 SLSQP 三个起点仍全部到达 100 次上限，
本次证据说明它们保存的最好控制已经非常接近该凸模型的数值最优值，
“未报告收敛”不等于“分数明显不佳”。历史控制独立重放也复现到约 8e-15 以内。

两者最优分数差的浮点支撑区间估计约为
`[0.0999999998747754, 0.10000000017901106]`，远离 0。
因此对**这两个冻结模型、同一任务及采样盒**，0.161 m 的最佳 signed 分数更差约 0.1，
有很强的数值证据；没有宣称严格的结构最优排序、区域下降方向或非线性性能排序。
这也不否定 F2.1 的另一比较：同一 0.161 m 结构重新优化控制优于使用旧结构的固定控制。
原固定控制分数 `-0.08298844105123286` 及历史对照保持不变。

值得保留的新解释：SOCP 中显著非零权重都位于终点位置和 holding 位置，
速度行权重很小；原 0.161 m 的 SLSQP 单一瓶颈是 0.30 s 速度，不能据此判断最优问题的活跃集合。
原子行级身份、尺度、lambda、锥向量、盒乘子已保存。终点位置与同一时刻 holding 位置
可能重复，最优乘子分配可以不唯一；不能直接把本次乘子当作唯一结构导数。

计算成本（单次本机观测，不是性能 benchmark）：首次冷加载 kernel 0.608 s，
第二次 0.0243 s；problem.solve wall 分别 0.0201/0.0144 s，
Clarabel 报告 solve_time 为 0.00560/0.00283 s，SLSQP kernel 为 0.544/0.438 s。
冷加载包含 CVXPY import；这些嵌套时间不应相加。采样映射仍为稠密堆叠矩阵，
大时域/高维控制的内存和分解成本尚未测量。

## 结论强度、失败模式与未来接口

- `feasible_witness`：合法控制经独立重放，G<=0，且原重放判据通过。
  `all_requested_checked` 另行取决于覆盖；局部子问题见证不能充当全任务验收。
- `positive_optimum_numerical_evidence`：数值最优性检查通过且 L 明显为正，
  只提供模型内不可行的数值证据。外层仍 `inconclusive`，certificate=null。
- `unknown`：未收敛、optimal_inaccurate、缺少/非有限原始或对偶量、残差/gap不满足、
  越界或重放失败。solver failure 从不转成结构不可行。
- 非法尺度/网格、无可分析输出、缺少依赖为不适用或明确失败；缺少原点 feedthrough
  输入使该采样保留 unchecked，其他兼容行仍可求解。
- 退化活跃集、病态矩阵、极端尺度、局部模型偏差及不唯一乘子均是限制。
  小 gap 不检验线性化正确性，也不验证连续时间、鲁棒性或真实执行。

T2 可读取 `raw_primal`、重放后的控制、`dual_checks.constraint_multipliers`、
盒乘子和 `provenance`。`epigraph_active` 表示 `g_i≈t`，
`task_boundary_active` 表示 `g_i≈0`，两者不能混淆。
后续敏感性必须另外处理模型结构导数、正则性、重复约束与乘子非唯一性；本轮不计算这些量。

T3 适配设计（未实施）：在原 `analysis.py/capability.py` 的数学结果适配边界显式选择
方法版本，保留原 operation 的默认 SLSQP 语义；先扩展实现指纹/可比性条件和成本记录，
再将新方法证据交给已有注册与预算入口，不能绕过冻结数据或 model applicability。
`ScopedMathematicalClaim` 的 binding、requirement/model/protocol identity、operating_point、
horizon、coverage、原始指针继续使用原身份来源；本内核内容哈希作为额外可核查来源，
不冒充 Store artifact identity。partial 覆盖和 certificate=null 必须透传。

映射到现有 `MathematicalQuantity` 时，解析 -1 可为 verified；
replayed_violation 的 verified 只描述合法输入下的数值重放；浮点原始/对偶/支撑估计
仍为 unverified_estimate，附 numerical_checks 的条件和 exact source pointer。
严格上界及严格最优值为 unavailable，绝不能因为 optimal status 升级。
L2 保留推导和精确来源；L1 保留 signed 方向、差距、检查强度与覆盖；
L0 只投影原始事实及来源，未知不变成零。Reporter 不计算最优值或改变阈值；
TaskAnalysisRequirement、任务验收、物理模型 loader、Store 历史证据无需改变。

## 环境与验证

默认 Python 3.14 与共享 `.mainline5-env` 均缺 CVXPY/Clarabel。
使用目标工作树独立 `.t1-env`，Python 3.11.16；未在共享环境安装包。
实际版本见 [requirements-s130-t1.txt](../../requirements-s130-t1.txt)：
CVXPY 1.9.3、Clarabel 0.11.1、NumPy 2.4.6、SciPy 1.17.1、Pydantic 2.14.1。
所有运行 OPENBLAS/OMP/MKL 线程环境变量为 1。局部求解选项为
`max_iter=200, tol_gap_abs=tol_gap_rel=tol_feas=1e-9`，来源与覆盖参数单独记录，
未重复定义任务时间、阈值、结构或物理边界；未新增 YAML。

```powershell
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
.t1-env/Scripts/python.exe -m unittest tests.research.test_conic_capability tests.research.test_trajectory_feasibility.NumericalTests -v
$env:PYTHONPATH='.;tests/research'
& D:/softrobot-agent/.mainline5-env/Scripts/python.exe -m unittest tests.research.test_s129_task_capability.SignedTests -v
.t1-env/Scripts/python.exe -m tests.research.s130_conic_comparison --output .t1-tmp/new-comparison.json
git diff --check
```

最终限定测试 **36/36**：新增 17、既有轨迹数值 10、既有 signed 数值 9。
包括正/零/负解析最优、真实二维范数、非对称区间、多约束冲突、非零名义张力、
初始状态/漂移/时变参考/前一输入、零时域/部分覆盖、无效归一化、NaN、
求解器实际迭代上限与异常、损坏的原始/对偶量、重放失配、显式张力修复、
optimal_inaccurate 不升级，以及保存 B 模型对照。
这些合成系统只是测试夹具，不是新机器人实验。

保留测试过程中的限制：初次新增测试发现零时域 SOC 常量需包装为 cp.Constant，已修复并复测。
另一次命令误选整个 trajectory 测试模块，25 项通过、8 项 integration 测试在 setUp
导入 `test_mainline` 时失败，未进入 worker；没有把这 8 项写为通过。
随后收窄到纯数值类，不扩装/启动集成物理依赖。正式 Agent/Reporter 集成和 nonlinear
验证未执行，也不属于 T1 通过范围。记录见 [validation.json](../../evidence/s130_optimal_capability/validation.json)。
