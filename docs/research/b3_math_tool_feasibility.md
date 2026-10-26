# B3 数学工具可行性研究（B 线）

2026-10-26，Asia/Shanghai。**现有数学控制工具能够从已知失败输入重新找到冻结 B3 可行解。**
本次只在 R1 新结构上优化控制，完成一次 native 响应更新后，独立完整 MuJoCo 回放和原
Reach/Hold 验收全部通过。保持峰速 **0.019924587874246717 m/s**，速度裕量仅 **0.3771%**。
一次独立进程的名义重复回放得到完全相同的完整采样内容；未开展扰动鲁棒性试验。

## 范围、代码与来源

- 固定起点：`c153e1731ae0925e756467f75a783b28abce2873`。
- 独立分支：`research/b3-math-tool-feasibility`；工作树：`D:\softrobot-agent\.worktrees\b3-math-tool-feasibility`。
- 原 `research/b3-r1-autonomous-pilot` 保持在上述起点，其他工作树及主目录未跟踪工作保留。
- 数值优化实际执行代码 SHA：`f41c7aadf`；其驱动文件内容身份、完整运行环境见
  [request.json](../../evidence/b3_math_tool_feasibility/search_01/request.json)。
- 后处理修正及第一份新结果提交：`b7b1b9105`；独立完整验收在该提交执行。
- R1 Study 和账本均未写入；本目录单独记录真实运行成本，研究 Provider/Reporter/新 LLM API 调用为 **0**。
- 未合并或挑选 T1/T2 和结构敏感性分支代码；生产数值内核、任务评价器未修改。

采用已封存候选 `e85fc8e3…f7543`，初始控制来自其**未通过的实测 NMPC 输入**
`e3a06aa1…a4a48`，原执行 `629f68ea…208f`。通过原 `numerics.archived` 验证归档和成员哈希。
封存通过控制 `b34d0feb…2115` 仅用于 `archived_solution_replay` 和最终来源差异核查，
优化函数不读取它、R1 native 优化状态或最终修正系数。

本次从 **16 个全零修正系数**启动，8 个后段系数参与优化；新的完整输入逐项可由本次
SLSQP 返回系数重建。新旧通过输入最大差异 **0.0026914524673493645 N**，不是复制旧答案。
完整控制初始化、原始数值输出和后处理问题都保存在证据目录中。

## 冻结任务与结构

任务 `b3-reach-hold-050-draft@1.0.0`、`reach_free`，目标 `[0.29,-0.035,0.19] m`，
重力 `[0,0,-9.81] m/s²`。初态全部候选自由度位置与速度为零，seed=17。
总时长 0.50 s，控制/评价周期 0.01 s，积分步长 0.0005 s；
50 条四腱绝对张力、51 个含初态的运动样本、保持窗 `[0.45,0.50] s` 的全部六个 post-step 样本。
每次完整回放 1,000 积分步；每腱张力区间 `[0,8] N`，ideal direct tension。

canonical task 用 `all_candidate_dofs_zero_v1` 规则表达初态，候选配置已将它展开为逐关节零值。
准备阶段核对原 initialization provenance、所有零值与 canonical 规则的一致性；没有改变初态。
完整冻结任务、合法机器人、离散化、物理模型及原控制配方见
[canonical_task.json](../../evidence/b3_math_tool_feasibility/canonical_task.json)、
[configuration.json](../../evidence/b3_math_tool_feasibility/configuration.json)。

结构为原 R1 两段四腱候选：段长 0.16/0.11 m，每段 12 cells，截面半径 0.008 m，
Young 模量 9.0/5.4 MPa，腱路半径 0.018 m。全部其他结构参数保留原值，见
[design_parameters.json](../../evidence/b3_math_tool_feasibility/design_parameters.json)。
本次没有生成新的结构变体，也没有取得结构单因素收益证据。

## 实际实验与判断

| 实验 | 终点误差 m | 保持最大误差 m | 保持峰速 m/s | 原完整验收 |
|---|---:|---:|---:|---|
| R1 封存控制独立正向回放 | 0.004169056300315 | 0.004504720409357 | 0.019934319730102 | 通过，仅基准 |
| R1 自身失败 NMPC 输入独立回放 | 0.004033427599093 | 0.004033427599093 | 0.043009681835388 | 仅速度失败 |
| 本次新 native 控制独立完整回放 | 0.004165288341735 | 0.004504169109783 | **0.019924587874247** | **通过** |
| 本次新控制独立进程重复回放 | 0.004165288341735 | 0.004504169109783 | **0.019924587874247** | **通过** |
| 冻结上限 | 0.010000000000000 | 0.010000000000000 | 0.020000000000000 | 未变 |

1. **正向基准。** 原通过解精确复现 R1 的三个指标。这仅验证当前执行/验收链路。
2. **失败起点。** 自身 NMPC 张力同样精确复现历史结果，仅保持速度超限。
   最坏采样在 0.49 s，归一化超限 1.150484；位置仍有余量，优先尝试终端制动修正。
3. **独立重新求解。** 直接调用原 `native_control.calculate`，由它调用
   `local_control_search.search`、`NativeModel.rollout_sequence` 和
   `control_correction.constrained_response_step`。采用后段分段线性张力偏移，
   knots `[0,0.30,0.41,0.50] s`，仅 flat knot-major 系数 8–15 活跃。
   0–0.30 s 输入保持原值，0.30 s 后逐步修正。该时间设置与 R1 最终优化不同。
4. 差分步长 0.04 N，初始信赖半径 0.15 N，系数界 ±2 N；最多 4 外层迭代、60 rollout，
   `safety_margin_fraction=0`。这些是计算请求上限，实际只用到 1 外层迭代、10 rollout。
   输入按原合法界投影，SLSQP 对终点位置及六个保持位置/速度范数做 epigraph 约束。
   先执行 1 基线 + 8 单边有限差分，再执行 1 次非线性候选检验。
   局部响应秩为 8，尺度条件数约 8.63e4；这是局部数值诊断，不是全局可控性证书。
5. SLSQP 17 次内部迭代，状态 `Optimization terminated successfully`。
   非线性候选第一次即满足全部采样代理约束，原搜索以 `local_target_reached` 停止。
   最大实际张力修正仅 **0.08504574985290425 N**；实际输入范围合法，通道最大值为
   `[5.81060,7.99998,7.65064,4.73854] N`。
6. **正式验收。** 新进程通过原 `playback_tensions` 从冻结初态重新创建模型、执行全部
   1,000 步，再调用 `evaluate_playback` 中注册的 Reach evaluator 和原
   `assemble_acceptance`。完整性、六点保持覆盖、张力、solver errors 与三项指标全部通过。
   native 预测和独立回放全部位置/速度样本最大绝对差为 **0**。
7. **有限确认并停止。** 鉴于峰速仅有 `0.0000754121257533 m/s` 裕量，另一个独立进程
   原样回放一次。完整 raw 内容身份相同。没有为提高非必要评分继续搜索。

相对失败 NMPC，保持峰速下降 **53.6742%**，改善来自同一结构上的控制优化。
相对封存通过控制只有极小指标差别，不能据此宣称本方法优于 R1。
这组结果也没有证明保持速度失败由驱动上限导致，更没有证明需要改结构。

## 费用与 R1 对照

| 本次口径 | 实际成本 |
|---|---|
| 独立搜索内核 | 1 model build，10 rollout，10,000 积分步，1,011 forward，0.7484345 s |
| 原 `calculate` 调用，含外围分析 | 0.8751331 s |
| 优化外层/响应更新/SLSQP 内部迭代 | 1 / 1 / 17 |
| 首次新解正式回放 | 1 完整 rollout，1,000 步，1 原任务物理评价，0.7197134 s |
| 重新搜索至首次新解验收 | 11 rollout，11,000 步，1.5948465 s（上述两阶段相加） |
| 含两次准备回放至首次新解验收 | 13 rollout，13,000 步，3 物理评价，测得阶段计时合计 6.2747861 s |
| 含最终重复确认的全研究数值量 | 14 rollout，14,000 步，4 物理评价；重复回放另用 0.7178616 s |
| 新 NMPC / PPO / T1/T2 / Provider | 0 / 0 / 0 / 0 |

这里的秒数是记录的实验阶段墙钟，**不含聊天推理、目录检查、导入启动和 Git 操作的全部耗时**，
也未将继承的 NMPC 输入生成成本伪装为本次新计算。`preparation` 的 4.6799396 s 包括归档
校验、配置准备和两次完整回放。详细资源从真实返回值汇总至
[summary.json](../../evidence/b3_math_tool_feasibility/summary.json)。

R1 已封存 native 阶段同样使用 10 rollout/10,000 步、1 响应更新，内部 SLSQP 16 次，
kernel 0.7707482 s，随后独立回放 1,000 步。本次 SLSQP 为 17 次，kernel 0.7484345 s；
单次墙钟差异不能说明速度提升。R1 还承担两次 NMPC、研究 Agent 117 次 Provider/220 次
公开操作和 959.233 s 原 numerical 账本；这些是不同的研究范围和计时口径，不能直接作为
本次纯控制局部优化的等预算性能对照。

## 可用工具与具体接口问题

已直接验证的有效工具为：归档成员校验、原结构/任务绑定、native 完整非线性序列响应、
有限差分、受限 SLSQP、独立 MuJoCo 张力回放和完整冻结任务验收。
数学工具最直接的贡献是用 8 个真实响应探针形成后段控制方向，再用原非线性仿真检验。

所用环境为 `D:\softrobot-agent\.mainline5-env\Scripts\python.exe`：
MuJoCo 3.13.0、NumPy 2.4.6、SciPy 1.17.1、CasADi 3.7.2、Pydantic 2.14.0。
GVS/NMPC 实现及 CasADi 可找到，但本次未执行新 GVS、IPOPT 或闭环 NMPC。
该环境没有 torch/SB3；因已获得可行解，没有为 PPO 安装依赖或启动训练。
SoRoSim/MATLAB、CONIC、T1/T2、结构敏感性等未测，不作有效/无效判断。

本次仅遇到两个研究驱动问题，均未更改生产数学实现：

- 初态检查将 canonical 规则直接与已展开数据比较，触发 AssertionError，发生在零数值
  rollout 时。按原候选 initialization provenance 核对后继续；保存 preparation_issue.json。
- 数值优化已完成并保存控制后，打印语句误取顶层 `cost`，触发 KeyError。
  原返回成本位于 `native_dynamics.cost`。只修正打印字段，从已保存控制单独启动正式回放，
  **未再次运行优化或伪造一次新搜索**；保存 postprocessing_issue.json。

主 Agent 可据此优先把“自身实测失败 NMPC 完整输入→native 控制修正→独立完整回放”作为
已有验证的工具组合。一次小规模控制优化即可完成当前名义任务，不需要先扩展整套数学能力。
仍应准确交付原结果字段层级、控制来源、实际已执行计算与独立验收状态。

## 可复现实验

在本分支工作树下执行以下 PowerShell 命令，选择新的输出目录以保留已完成证据。
已有环境路径可替换为安装上述版本的 Python；没有任何命令调用研究 Provider。

```powershell
Set-Location D:\softrobot-agent\.worktrees\b3-math-tool-feasibility
$b3Python = 'D:\softrobot-agent\.mainline5-env\Scripts\python.exe'
$b3Output = 'runs/b3_math_feasibility_reproduction'
& $b3Python -m tools.research.b3_math_feasibility prepare --output $b3Output
& $b3Python -m tools.research.b3_math_feasibility optimize --output $b3Output
& $b3Python -m tools.research.b3_math_feasibility replay --output $b3Output --name nominal_repeat
& $b3Python -m tools.research.b3_math_feasibility audit --output $b3Output
```

只回放已交付的新控制，不重新优化：

```powershell
& $b3Python -m tools.research.b3_math_feasibility replay --name additional_nominal_replay
```

入口对完成的准备/搜索/回放目录拒绝覆盖。`audit` 仅重新读取和核查已保存数据，不发起仿真。
本次真实首次独立回放因打印问题由单独命令恢复：
`replay --name search_01/independent_replay`。

主要交付路径：

- 合法完整结构与环境：[configuration.json](../../evidence/b3_math_tool_feasibility/configuration.json)。
- 完整 50×4 新张力序列：[search_01/schedule.json](../../evidence/b3_math_tool_feasibility/search_01/schedule.json)。
- 请求、初始化、全部优化探针及 solver：[search_01](../../evidence/b3_math_tool_feasibility/search_01)。
- 完整新仿真、编译模型与原验收：[independent_replay](../../evidence/b3_math_tool_feasibility/search_01/independent_replay)。
- 重复确认：[nominal_repeat](../../evidence/b3_math_tool_feasibility/nominal_repeat)。
- 来源/输入重建/预测实测对齐及成本核查：[summary.json](../../evidence/b3_math_tool_feasibility/summary.json)。

## 结论边界与版本交付

已证明：在原 R1 合法结构、冻结初态/环境/张力界/全采样规则下，从其失败 NMPC 输入出发，
现有数值工具能重新生成一条名义 B3 Reach/Hold 开环通过序列，并经原独立验收确认。
尚未证明：扰动鲁棒性、连续时间约束、实机表现、NMPC 闭环通过、策略泛化、结构改进收益、
参考结构充分优化后的不可行性或全局最优性。名义确定性重复不能替代鲁棒性结论。

本地已分阶段提交代码、正向回放和新的优化结果；最终提交包括正式验收、重复确认和本报告。
首次混合 commit/push 请求被自动审批拒绝，理由是未确认 GitHub 目的地/证据外发授权；
该命令未执行，后来本地提交成功。已核对附件明确授权
`origin/research/b3-math-tool-feasibility`，远端 URL 对应原指定 GitHub 仓库。
最终远端状态以独立推送及 `ls-remote` 实际核对为准，不能将本地提交冒充推送成功。
