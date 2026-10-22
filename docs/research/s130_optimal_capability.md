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

# S130-T2：固定拓扑的最优任务能力结构敏感性

2026-10-22。在 T1 `3d782aa435e7c3b1e1cc7cd6eac27fe5565859cb` 上继续开发。
本节新增 T2 研究，不改写上面的 T1 历史结论。工作树开始时干净，仍为
`research/s130-optimal-capability`；保留起点 `40a1a340` 与 F2.1 指定基线间四个提交的差异。
未 reset、重建工作树、合并主线或实施 T3。

## 真实参数与模型来源

保存的 B 线机器人实际柔性段为 `near`、`distal1`；`far_t*` 是张力通道名，
不能据此假设存在 `segments.far`。本轮选择真实可编辑、material 模式的：

| 参数 | 基准 | 对称步长 | 冻结范围 | 单位 |
|---|---:|---:|---:|---|
| `segments.near.length_m` | 0.160 | 0.00050、0.00025 | [0.152, 0.168] | m |
| `segments.distal1.young_pa` | 5,400,000 | 54,000、27,000 | [4,590,000, 6,210,000] | Pa |

实际参数来自 B 导出候选的 `parameters`，原始结构和网格来自其保存的
`candidate_builder.parameters.data.source_design/source_mesh`。范围从固定 Git 对象
`3d782aa4:configs/research/study.json` 读取；该文件与原 B 分支版本一致。
这只是本次用户授权离线数学研究使用的既有范围来源，没有打开/重启该 Study 或取得其预算。
因此可报告 `xi=(d-dmin)/(dmax-dmin)` 的归一化差分；没有范围的其他输入只能报告 SI 单位。

离线脚本调用原 `resolved_configuration()` / `generated_serial.generate()`，
再用原 `make_graph_from_input()`、`_candidate_points(..., ['controller_start_input'])`、
`linear_model()`。初始化仍经过原 `candidate_numerical()` 的投影和有界预张力准备，
时间原点按现有 analysis 规则设为 0。基准及两个参数各四个变体共 **9 个模型**。
任务、controller recipe、拓扑源、通道顺序及物理张力界保持不变。
没有重新求目标平衡点、调用控制器执行或运行物理后端。

基准重建的 A、B、漂移、x0、u0、位置和速度的 value0/C/D 与 B 保存模型
逐项最大绝对差均为 **0**。所有模型、配置、初始投影来源和构建成本保存在
[t2_models.json](../../evidence/s130_optimal_capability/t2_models.json)。
所有变体都是从真实结构生成器重建，不是修改保存矩阵伪造设计。

## 数学入口、比较前提与三种不同量

新增 `extensions/math_analysis/capability_sensitivity.py`，入口：

```python
result = capability_sensitivity(points, parameter, protocol)
```

`points[0]` 为基准。每个点显式提供 `value, parameters, model, requirements,
initial_delta, context, source_reference`，可附 `construction_s`。
数学核不构建候选、不调用 Registry/Store/Provider、不解析研究配置。
同一参数之外的参数字典、固定配置身份、源身份、拓扑身份、构造规则、
状态/输入定义、坐标/张力顺序、任务约束及参考、时间相位和实际覆盖必须匹配。
模型自身的 source/task/protocol 绑定也不能彼此矛盾。元数据是来源声明，
不是数学核对任意第三方模型构建正确性的证明；本次脚本另做了基准重建核对。

默认拒绝改变物理输入集合。若一个参数化解析模型确有输入界依赖，必须显式提供
`input_bounds_treatment='parameter_dependent'` 及来源，并使各点模型与 requirement 的界一致；
这项能力由合成测试验证，本次真实 GVS 研究没有改变冻结的 0–8 N 张力界。
不满足比较条件时在 SOCP 前返回 not_applicable；数值最优性不足则保留诊断并不输出敏感性。

分别保存：

1. **固定绝对张力**：在各点用 `verify_witness()` 重放同一基准物理控制序列，
   报告 G 的中心/单侧割线及每项 signed 约束的变化。若变动的输入盒使该序列非法，
   标明 input_legal=false，仅保留诊断，不把它当合法能力见证。
2. **控制重优化**：各点独立调用原 T1 `conic_capability()`，只有全部通过 T1 检查才继续。
   比较至少两个步长、中心及左右单侧差分，传播各点浮点支撑下界估计到割线区间。
   该区间不是严格误差界，也不包含有限差分截断误差；反向/倒置区间不能通过分辨率检查。
3. **条件包络估计**：固定基准合法 U 和 T1 原始乘子，对完整重新组装的拉格朗日函数差分。
   它不是只对 A、B、末端输出或静态残差求导。

## 绝对张力坐标下的完整拉格朗日公式

对每个结构 d，原 prepared row 为 `r=M(d)z+b(d)`，其中 b 包含初始扰动、
工作点、仿射漂移、ZOH 传播和时变参考。令 `U=z+u0_stack(d)`，则

\[
 R_i(d,U)=[M_i(d)U+b_i(d)-M_i(d)u_{0,stack}(d)]/s_i.
\]

所有点重新调用 prepare_trajectory，因此上述项的结构变化均进入差分。
范数行 `g_i=||R_i||-1`；区间的每一侧已经写成无量纲仿射函数 `g_j(d,U)`。
张力盒为 `L(d)<=U<=H(d)`，本框架当前的物理下界 L=0。
使用 T1 SOC 对偶 `(alpha_i,v_i)`、区间乘子 lambda 和盒乘子 mu：

\[
 \mathcal L=t-\sum_{i\in SOC}\{\alpha_i(t+1)+v_i^T R_i(d,U)\}
 +\sum_{j\in LP}\lambda_j(g_j(d,U)-t)
 +\mu_L^T(L(d)-U)+\mu_H^T(U-H(d)).
\]

固定基准 U、t 和乘子，完整方向估计为

\[
 D_d\mathcal L=-\sum_i v_i^T D_dR_i
 +\sum_j\lambda_j D_dg_j
 +\mu_L^TD_dL-\mu_H^TD_dH.
\]

SOC 的 alpha 与区间 lambda 都是**原 signed minimax** 的无量纲任务乘子。
R、g 已含原任务尺度，不再重复乘/除 radius。若用物理未归一化约束导数，
则须按 T1 规则用 alpha/radius 或 lambda/scale。不能直接将不同物理单位残差相加。
固定 U 时 `-M(d)u0(d)` 项必不可少；本轮明确测试了变化的 u0、初始扰动以及输入上界，
不会把固定 delta tension 冒充固定物理输入。每个任务行、采样索引、残差偏导、
signed 割线、乘子和贡献均保存在原始结果中。

在适当的解映射稳定性/正则性下，这种拉格朗日参数偏导可以描述最优值变化。
本实现提供数值必要检查和对照，不证明这些正则性条件。
理论边界参考 [Boyd–Vandenberghe §5.6](https://stanford.edu/~boyd/cvxbook/bv_cvxbook.pdf)
及 [Differentiating Through a Cone Program](https://www.web.stanford.edu/~boyd/papers/diff_cone_prog.html)：
强对偶和可用乘子不自动保证参数化最优值处处可微；对解映射求导也需要相应条件。

## 活跃约束、重复乘子与尚未解决的正则性

保留 `g_i≈t` 的 epigraph 活跃集合与 `g_i≈0` 的任务通过边界，二者分开。
本次全部采样点的主要 epigraph 活跃行均为终点位置和 0.30–0.35 s holding 位置。
不是速度行。终点位置和 0.35 s holding 位置在所有模型的绝对输入映射完全相同，
所以只把原子行 **[0,6]** 作为精确重复组；同分但映射不同的其他行不强行聚合。

该组基准 alpha 总和为 `0.32510470632327787`。将组内 alpha、SOC 向量全部分配给
第 0 行或第 6 行，得到两套不同的分配。因为整组函数及各结构点映射完全相同，
在精确算术中锥可行性、驻点、对偶目标和互补性保持，有限参数差分贡献也相同。
浮点核查的驻点变化约 `6.46e-27`、锥违反 0；长度贡献两种分配均为
`32.51047062773354 m^-1`。因此这项明确的乘子非唯一性**没有破坏该组总敏感性**。

另外用 CVXPY/Clarabel 在基准的近最优对偶面上最小化/最大化包络线性泛函：
保留全部 SOC/区间/盒乘子、驻点和总权重约束，要求对偶目标至少达到
`G_baseline-1e-6`。不是只看优化器返回的一套乘子。对每个返回独立复核锥、
驻点、权重和及原始/对偶差距；只有 optimal 且数值检查通过才标为已检查端点。
该面是数值厚度为 1e-6 的近最优集合，端点本身也只是浮点估计，不是严格导数范围。

实际没有完全解决这个诊断：长度两种步长的最小端点约 `99.999875 m^-1` 通过检查，
最大端点均 optimal_inaccurate；模量较大步长得到约
`[-7.52e-15,1.16e-14] Pa^-1` 的数值范围，较小步长两端均 optimal_inaccurate。
这些未收敛端点明确 unavailable；不能用它们宣称“所有最优乘子给出唯一梯度”。
初期 face 厚度 1e-8 在解析例子上过薄，改为显式 1e-6 后解析测试通过；
真实案例依然保留上述失败，没有为了通过而把 optimal_inaccurate 升级。
最终 face solver 的 gap 选项为 1e-8，feas 为 1e-9，独立残差判据为 1e-7，
与 T1 原始求解选项分开记录。

普通梯度仍可能受到最优原始解非唯一、未探索的乘子或分支切换影响。
不把 LICQ 未证明/重复行直接解释成必然不可微，也不把 FD 吻合解释成已证明可微。

## 实测结果与科学解释

最终完整结果：[t2_final_comparison.json](../../evidence/s130_optimal_capability/t2_final_comparison.json)。
先前诊断结果和成本摘要保留在 [t2_validation.json](../../evidence/s130_optimal_capability/t2_validation.json)，
以及未覆盖的 [t2_comparison.json](../../evidence/s130_optimal_capability/t2_comparison.json)。
每个结果包含完整 T1 原始/对偶解、独立固定控制重放、贡献表、对偶面端点及来源哈希。

| 参数/步长 | 重优化中心差分 | 完整包络差分 | 固定控制中心差分 |
|---|---:|---:|---:|
| 近段长度，0.00050 m | 100.00000000598 | 99.99999999879 | 99.58836446830 |
| 近段长度，0.00025 m | 100.00000002180 | 99.99999999879 | 99.89682521676 |
| 远段模量，54,000 Pa | 5.27e-17 | 5.32e-19 | -1.71e-10 |
| 远段模量，27,000 Pa | -1.88e-16 | 5.32e-19 | -4.27e-11 |

长度单位为 score/m，模量为 score/Pa。长度重优化单侧差分也均约 100，
浮点下/上估计传播后的两个割线区间分别约为
`[99.9999998910,100.0000000301]`、`[99.9999998917,100.0000000701]`。
对冻结范围的归一化差分约为 **1.6 per xi**。
在这组局部数学模型中，减小近段长度得到更低、更好的 signed G。
状态为 `stable_reoptimized_direction_envelope_unresolved`：
**重优化有限差分方向稳定，当前乘子的包络吻合，但一般乘子稳健性尚未解决**。

模量两边最优分数都约 -0.2，差分符号随步长改变且小于数值分辨率。
两个割线区间均跨 0（约 [-1.61e-15,2.96e-15]、[-1.09e-15,2.73e-15] Pa^-1）。
状态为 `numerically_flat_fd_envelope_unresolved`，不发布增加/减小模量的改善方向，
也不把它写成严格零梯度或跨参数最优排名。

固定控制的有限步长响应确实不同。长度 h=0.0005 m 的左右割线为
91.7227/107.4540，h=0.00025 m 为 95.9664/103.8273；模量固定控制的左右
响应也不对称，而重优化可以保持约 -0.2。**这些真实数据只说明有限步长下不同**；
它们趋于相近的一阶极限，不能据此宣称 h→0 时两种导数一定不同。
单独的解析测试 `g1=U-1, g2=(1+d-U)/2-1` 则明确给出：
重优化/包络导数 1/3、固定控制中心差分 1/4，左右固定控制导数 0 和 1/2。
该例是合成验证，不是机器人科学证据。

长度变化贡献几乎全部来自位置行：终点约 16.2629、holding 六行合计约 83.7371，
速度贡献在约 1e-9 m^-1 以下。当前真实张力盒不变，盒偏导贡献为 0；
不能把“该例为 0”理解为以后可以省略盒项。

另有独立、易核查的模型解释：9 个重建模型的世界 x 位置输出 C/D 第一行均精确为 0，
因此该冻结仿射模型中的 x 残差与控制无关。基准常量残差约 0.008 m，
位置半径 0.01 m，给出投影下界估计 `abs(r_x)/0.01-1≈-0.2`。
长度变化后该分量随长度变动，模量扰动则不改变它；各点重优化值都接近该下界。
这解释了长度斜率约 100 和模量平台，但不代替上面的完整拉格朗日分析，
也不表示真实弯曲机器人世界 x 位置在非线性运动中不受控制。

原 0.160→0.161 m B 线对照仍标为**有限割线**：重优化割线约
99.9999999865 m^-1，固定基准乘子的有限拉格朗日割线约 99.9999999988 m^-1。
局部方向判断依据本轮额外的两套对称扰动，不能把原来的单条割线重新命名为局部导数。

## T3 可消费内容与不能接入的强结论

结果提供 task/model scope、参数来源/单位/真实归一化范围、固定控制与重优化处理、
全部采样原始记录、独立模型身份、数值最优性、正则性限制、活跃行、贡献和成本。
简短 summary 包括基准参数、模型身份、任务绑定、来源、受支持方向、主要约束、
可靠性状态及后续验证需要。它不是设计命令或自动研究计划。

T3 值得接入的是有来源的局部 FD 方向、flat/unknown、固定控制与重优化差别、
重复组总贡献及数值可靠性诊断。包络量仍须作为 conditional/unverified_estimate，
严格梯度、严格导数误差界、一般乘子唯一性及区域下降仍 unavailable。
现有 ScopedMathematicalClaim/MathematicalQuantity 可保留原 status/来源语义，
ResultCard、L2/L1/L0、Reporter/evidence_read 只消费这些结构化事实与原始指针。
本轮没有修改上述主链路模块、正式 operation、验收、Store 或预算。

数值方向门槛显式采用 `2% * max(abs(slope)) + 1e-7 / q`，
其中 `q=max(abs(d0),最大扰动步长)` 仅用于数值尺度，不作为物理参数排名的归一化。
至少两个步长、左右差分（存在时）、传播区间宽度及活跃集合均须通过相应检查。
只有包络一致且对偶面两端可用、范围足够窄时才给出 numerically_stable_local_direction；
若仅 FD 通过，则保留上述 envelope_unresolved 状态。所有状态都不宣称严格可微性。

## 成本、失败记录与复现

沿用 `.t1-env`，仅增加仓库已用的 CasADi 3.7.2、PyYAML 6.0.3，
见 [requirements-s130-t2.txt](../../requirements-s130-t2.txt)。共享 `.mainline5-env`
仅只读运行既有 signed 回归，未安装/修改共享依赖。线程环境 OPENBLAS/OMP/MKL 均为 1。

9 次模型构建合计 **60.3521 s**。最终一次分析使用 **10 次 T1 SOCP + 8 次对偶面锥规划**，
T1 kernel 合计约 **0.7647 s**，对偶面 wall 合计约 **0.2443 s**。
基准在两参数分析中独立求解两次，所以 9 个唯一模型对应 10 次能力求解。
包括开发诊断和最终复核在内，共 4 次离线分析，**40 次能力求解 + 32 次对偶面求解**，
分别合计 3.0708/0.9595 s；模型只构建过上述 9 次，不重复计 60.35 s。
这些是本机观测，包含部分首次加载，不是严格性能 benchmark；测试成本另列。

最终目标测试 **51/51**：T2 新增 15、T1 17、已有轨迹数值 10、已有 signed 9。
覆盖解析可微值、固定/重优化区别、u0 和初始投影、变动输入盒、重复乘子、
活跃集切换、步长敏感、数值未知、倒置浮点区间、时变参考/区间、非法比较和单侧边界。
初次 12 项 T2 测试为 7 通过、4 失败、1 错误，原因是对偶面数值失败和缺失范围；
明确调整诊断并增加未知分支后通过。构建脚本预检的一处括号错误在任何构建开始前修复。
没有将真实模型对偶面尚未收敛的端点写为通过。

```powershell
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
.t1-env/Scripts/python.exe -m unittest tests.research.test_capability_sensitivity tests.research.test_conic_capability tests.research.test_trajectory_feasibility.NumericalTests -v
$env:PYTHONPATH='.;tests/research'
& D:/softrobot-agent/.mainline5-env/Scripts/python.exe -m unittest tests.research.test_s129_task_capability.SignedTests -q
# 不需重建即可复核保存模型；输出文件必须尚不存在。
.t1-env/Scripts/python.exe -m tests.research.s130_sensitivity_comparison analyze --models evidence/s130_optimal_capability/t2_models.json --output .t1-tmp/t2-new-check.json
# 如需独立重建，以下命令仅进行 9 个本地数学模型构建，约一分钟。
.t1-env/Scripts/python.exe -m tests.research.s130_sensitivity_comparison build --output .t1-tmp/t2-new-models.json
```

未解决问题保留为：一般近最优对偶面的可靠极值、原始解非唯一对敏感性的影响、
严格可微性/截断误差与区域下降、模量的有效改善方向，以及非线性闭环和物理验证。
这些限制没有阻止 T2 提供受支持的有限方向信息，也没有被转换为否定机器人可行性的结论。
