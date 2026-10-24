# 阶段 A：MuJoCo 原生数学接入

**三项原生数学能力已进入原 `research_analysis`、Store 和 L0–L3 证据链。**
S142 原张力的完整 0.35 s 终点可靠复现。一次局部修正使终点速率降低 **12.47%**，
但仍为 **0.0200005283 m/s > 0.02 m/s**，没有通过原阈值。
远段 Young 模量降低在该固定输入下恶化短时速率；截面高度增加 1% 同时改变质量、刚度和响应，
短时速率有所改善。两者均不是重新优化后的结构能力，也不是完整任务结论。

本工作从已推送的 `research/s148-mass-intervention@34a3b22ca` 建立独立工作树
`.worktrees/mujoco-native-math-stage-a` 和分支 `codex/mujoco-native-math-stage-a`。
已读取 AGENTS、S142–S148 报告和相关实现；S142 报告从其原工作树读取。
主工作树的环境、未跟踪文件以及旧研究 Store 均不修改。

## 审计与实现边界

原项目已有结构生成/编译、MuJoCo 执行、局部受限响应优化、冻结任务约束、
Store/worker 恢复、F0–F2 ResultCard/Reporter/L0–L3。S144 的原生 checkpoint
已验证可复现 S142 增刚结构的 0.34–0.35 s；S145–S148 的 GVS 投影/质量诊断
不需要重跑。

实际缺口是 `analysis.calculate/dispatch` 绑定控制器准备的低维模型与 GVS 保存状态，
没有公共原生动力学、实际张力短时响应或固定输入结构功能响应。
因此只扩展原 `AnalysisRequest` 和 `research_analysis`，不另建 Agent、Store 或解释系统。

新增 `extensions/tendon_family/mujoco_analysis.py` 负责原生求值/积分，
`tools/research/native_analysis.py` 负责请求适用性、结构配对与原任务约束的局部解释。
结构仍通过原 `construct → resolved_configuration → generated_serial → compiler → compile_xml`。
原数值内核使用原编译器的内存 XML 输出，避免 Windows 临时目录 ACL 问题。

MuJoCo 使用 [原生 API](https://mujoco.readthedocs.io/en/stable/APIreference/APIfunctions.html)
提取质量矩阵、求解质量系统和 Jacobian；力分量遵循
[官方计算语义](https://mujoco.readthedocs.io/en/stable/computation/index.html)。
重力 **bias** 由相同构型零速度求值分离，重力驱动力为其负号；
速度 bias 为两次原生 bias 之差。被动力保留 spring/damper 等原生分量。
`J M⁻¹ passive` 明确是被动力对末端加速度的贡献，不是机器人的总恢复响应。
总末端加速度包含 `J qacc + Jdot qvel`。

## 公共调用

继续调用原 `research_analysis`，保持 `candidate`、冻结 `protocol` 与原预算准入。
新方法明确使用 `model_source="mujoco"`、`operating_point="saved_state"`：

```json
{
  "candidate": {"artifact_id": "<原候选证据 ID>"},
  "model_source": "mujoco",
  "operation": "short_input_response_v1",
  "operating_point": "saved_state",
  "saved_state": {"artifact_id": "<完整原生 checkpoint 的证据 ID>"},
  "protocol": "<原冻结 TaskAnalysisProtocol 对象>",
  "native": {
    "horizon_s": 0.01,
    "difference_step_n": 0.1,
    "correction_radius_n": 0.25
  }
}
```

上例为字段占位示意；实际 `protocol` 必须使用原冻结对象。每项真实调用的完整请求也可从结果的
`/requested_operation` 按原证据接口读取。

`native_dynamics_v1` 只作零步进力学；`short_input_response_v1` 对每通道使用两档
实际合法张力差分，必要时单侧；`fixed_input_structure_v1` 增加
`structure_response={variable,candidates}`，比较已通过原结构授权的 1–2 个单参数候选。
`correction_radius_n` 仅用于短时输入响应的可选一次局部提案。
差分不是重新优化后的能力，Conic/KKT/包络接口原义不变。

也可用 `execution + update_id` 读取当前 Study 拥有的完整理想张力执行：
在原数学 worker 内只重放所需实际输入前缀，逐点验证已保存 native 状态/末端量，
之后才克隆原生 checkpoint；前缀成本计入该结果。不要求旧优化器完整输入记录。
只保存 GVS `x` 的状态会返回不适用，不能冒充完整原生状态。

不指定 `model_source` 时旧 GVS/SoRoSim 调用与序列化保持原义。
显式 `gvs`/`sorosim` 选择低维 provider；SoRoSim 仍需候选冻结的原 solver 设置，
不会从其他控制器臆造。MuJoCo 不需要 GVS Basis、投影、动力学图或 MATLAB。

原生 v1 范围限定为无接触/约束、无外部施力、无 activation 状态的具名 hinge 模型及理想张力，
支持最长 0.05 s 的短时分析。本阶段不开发完整 MuJoCo-NMPC、全局结构搜索或自主 Study。

## 必要验证

用原 `.mainline5-env` 单线程环境，运行定向契约回归及
`tests/research/mujoco_native_stage_a.py`。后者通过真实 `analysis.dispatch`、原 contained worker、
Store receipt、ResultCard、Reporter 和 evidence_read 完成四个分析请求：原生力学、
六路输入响应、远段 Young 模量两档单侧扰动、远段截面高度 +1% 与基线配对。
主 Agent/Reporter 不调用 Provider；完整矩阵只保存在原分析结果中。

## 真实数值证据

### 原生力学与短时控制

使用原增刚执行 `3c78b551965f443abd966bfb68b969dd`，物理身份
`3b25cafae82de64d960b42508c42425c15368e4a73cd494359fcf5b9b3e32eac`。
从 S144 已验证的 `native_start.npz` 恢复完整 `mjSTATE_INTEGRATION`，
原生模型有 48 个 qpos、48 个 qvel、6 个直接张力输入、0 个 activation 状态。
恢复的完整 qpos/qvel 与 S142 的 0.34 s 保存值逐项相同；没有先投影 GVS。
原生 checkpoint 的未保存内部量与历史原始执行的一致性，仍沿用 S144 的验证范围，
不额外声称逐项比较过历史未记录的内部状态。

六路顺序为 `near_t0, near_t1, near_t2, far_t0, far_t1, far_t2`；
实际绝对输入为 `[6.984303281,7.922288457,4.393994441,4.198743008,3.343842164,3.151046626] N`，
边界仍为每路 0–8 N。0.34–0.35 s 使用原 `implicitfast`、0.0005 s 步长、20 步。

| 量 | 原生结果 |
| --- | ---: |
| 0.34 s 末端速率 | 0.009927943990 m/s |
| 原输入下的质量平衡残差最大分量 | 6.59195e-17 N·m |
| 0.34 s 原输入末端加速度 xyz | [−13.919252, +2.988260, −0.663293] m/s² |
| 局部末端加速度输入映射的奇异值 | [171.701002, 130.408397, 17.638502] m/(s²·N) |
| 原输入 0.35 s 速率 | 0.022849089711 m/s |
| 对原终点完整 qpos/qvel/位置的最大差 | 全部 0 |
| 对原终点速度的最大逐分量差 | 5.20417e-18 m/s |

位置/速度输入 Jacobian 分别为 3×6，保存在 `/native_dynamics/input_response`。
例如 `far_t0` 的终点速度列为 `[−0.076243,+0.102694,+0.097653] m/(s·N)`，
`far_t2` 为 `[+0.060585,+0.024356,−0.140193] m/(s·N)`。
这些方向只针对当前状态、输入和 0.01 s 区间。

差分请求步长为 **0.1/0.05 N**。粗步的 `near_t1` 因原输入距上界仅约 0.0777 N 而使用单侧差分；
其余可行方向使用中心差分。分母取两次**实际施加张力之差**，没有用裁剪前的请求步长。
两档位置/速度 Jacobian 的相对范数差分别为 **0.010258% / 0.014101%**。
这通过本方法的 5% 描述性一致性检查；两档差分不提供区域误差界或连续时间收敛证明。

复用原 `constrained_response_step`，半径上限 0.25 N，只求一个局部提案，SLSQP 3 次迭代。
实际六路修正约为
`[−0.0004775,−0.0016811,+0.0013219,−0.0091182,−0.0034870,+0.0110741] N`。
原生非线性 20 步验证如下：

| 0.35 s 短时代理 | 原输入 | 局部修正 |
| --- | ---: | ---: |
| 位置误差/m | 0.003136441884 | 0.003118858278 |
| 速率/(m/s) | 0.022849089711 | 0.020000528285 |
| 相对 0.02 m/s 的速度余量/(m/s) | −0.002849089711 | **−5.28285e-7** |

实际速率降低 **12.46685%**。线性响应预测接近阈值，但非线性执行仍超限；
没有放宽容差、追补第二轮优化或将其记为通过。y 速度的绝对值略增，不能说各分量都改善。
该提案只作为证据保存，没有自动采纳为后续控制。

### 结构参数—机制—功能—任务

所有扰动均经过原合法 source-relative 生成链和候选核验；近段参数、输入、任务、离散网格不变。
以原具名 qpos/qvel 为比较状态，在**基线与所有变体中统一重置 solver history**，
再施加相同六路绝对张力。每个模型的合法输入重新检查，未跨维度相减。
这定义的是同姿态/速度比较，不是同平衡、同能量或各结构从零态到达该状态的比较。

远段 `distal1.young_pa` 基线为 **6,209,999 Pa**，取 −1% 和 −0.5% 两档合法单侧扰动；
基线已接近原允许上界，因此没有添加越界正扰动。
第二个参数为远段第 0 截面 `height_z_m`，从 **0.0095 增至 0.009595 m（+1%）**，
只改变这一站的高度，其余站和参数保持原值。

| 扰动 | 全质量矩阵相对差 | 全关节刚度向量相对差 | 固定状态加速度输入映射相对差 | 被动力末端加速度贡献相对差 |
| --- | ---: | ---: | ---: | ---: |
| 远段 E −1% | 0 | 0.282542% | 0 | 0.709567% |
| 远段 E −0.5% | 0 | 0.141271% | 0 | 0.354783% |
| 截面高度 +1% | 0.148244% | 0.311030% | 0.022781% | 0.180526% |

表中均为相应**完整数组的范数相对变化**，不是某个关节的百分比、因果贡献份额或任务改善率。
E 扰动直接缩放受影响的远段刚度；原生数据同时表明质量/惯量、阻尼、同构型腱长和输入力映射不变。
E −1% 时被动力对末端加速度的贡献向量改变约 **1.61168 m/s²**；
总加速度也改变该向量，但因其他项抵消，其相对差约 **11.3086%**。
固定状态瞬时输入映射不变，不能外推为有限时域的控制作用也不变。

截面高度 +1% 同时改变 body mass、主惯量和关节刚度；其全向量相对差分别为
**0.145434%、0.072761%、0.311030%**，阻尼未变。
同构型测得腱长不变，输入力映射相对差约 `3.89e-16`；
但质量系统变化使末端加速度输入映射及其方向发生小幅变化。
最小奇异值从 **17.638502** 降至 **17.595952 m/(s²·N)**。
因此不能把该参数叫作纯刚度或纯质量干预。

| 固定输入，0.35 s 短时端点 | 位置误差/mm | 速率/(m/s) | 相对基线速率变化/(m/s) |
| --- | ---: | ---: | ---: |
| 基线 | 3.136442 | 0.022849090 | 0 |
| E −1% | 3.142035 | 0.023475938 | +0.000626848 |
| E −0.5% | 3.139237 | 0.023160618 | +0.000311529 |
| 截面高度 +1% | 3.131103 | 0.022151235 | −0.000697855 |

任务代理直接复用原 `TaskAnalysisRequirement` 和 norm/interval margin 计算，
保留 10 mm / 0.02 m/s 原界限；表中所有结构变体的终点速度仍超限。
E 两档位置/速度响应割线的相对差约 **0.024655% / 0.044826%**，只支持这两个扰动附近的局部数值关系。
截面高度仅作一个合法配对，没有声称参数步长收敛。

有两项直接反例限制“功能指标越好、任务就越好”的解释：
E −1% 将起点瞬时速率导数从 **5.95743 降至 5.78078 m/s²**，但终点速率反而升高；
截面增高使最小瞬时输入奇异值略降，但短时终点速率改善。
单一瞬时功能量不能替代整段响应。尚未执行完整固定控制回放、控制重新优化或完整冻结任务验收，
更没有结构最优性、全局可行性/不可行性结论。

## 原架构核对与代码职责

| 模块 | 本次职责 |
| --- | --- |
| `extensions/tendon_family/mujoco_analysis.py`，213 行 | 原编译链、具名原生状态/力学、短时积分、实际张力差分、同坐标结构对照 |
| `tools/research/native_analysis.py`，212 行 | 原接口的适用性、合法单参数配对、原任务代理、一个复用的确定性投影 |
| `contracts.py` / `analysis.py` | 显式模型/方法、原预算和 worker 分派、原 Store 结果与诊断强度 |
| `numerics.py` | 完整 native checkpoint 或 owned execution 的原始前缀读取；执行 owner 的 run_id 不冒充科学差异 |
| `task_constraints.py` | 原数学方法目录及模型适用性扩展，保留原任务/Conic/KKT 含义 |
| `evidence_views.py` / `research_context.py` | 原 ResultCard 和数学决定视图增加数值/来源，不携带完整数组 |
| `reporter.py` | 仅增加 4 行复用原 ResultCard 投影，使已保存报告也能显示同一不可变原始证据的新确定性摘要 |
| `agent.py` | 工具说明与按模型检查可用性；MATLAB 不可用不再隐藏已授权的原生分析，MATLAB 请求仍受原检查 |
| `state.py` | 新数值模块加入已有实现冻结列表；身份算法、worker 恢复和正式证据准入不变 |

相对 S148，生产代码 **增加 576 行、删除 29 行，净增 547 行**，两个主要新模块共 425 行。
新增一个 105 行定向测试文件和一个 144 行工程案例入口。
另从 S142 封存 Store 原样恢复其已声明但 S148 分支缺失的 `s142_model_scope.json`（14 行）；
保留相同内容身份，没有改默认任务、阈值或物理参数。

逐项核对：

- 主 Agent 提出假设/分配预算/选择结构控制，原 Reporter/子 Agent 只读解释与按需调查；职责未改。
- L0 Decision Brief、L1 原 ResultCard/Reporter、L2 原 Evidence Relations、L3 原 EvidenceQuery/JSON Pointer 全部保留。
- `decision_result → ResultCard → mathematical_decision_view → agent_decision_brief` 和 `compact_result` 使用同一确定性投影。
- 摘要含问题、模型/时间/实际输入、关键数值、短时约束余量、限制、成本和源路径；单项数学视图约 6.2–8.9 KB。
- 完整 checkpoint、48×48 质量矩阵、3×6 响应、探针与变体数组只按需读取；没有进入默认数学视图。
- 原 Reporter 自动保存/解释、动态委派、独立有界上下文、稳定前缀、按需 schema、Session 恢复及正式读证据义务不变。
- 旧 GVS/SoRoSim 方法和请求序列化保持原义；没有将 native 离散数值塞入连续仿射 Schema。
- 没有第二个 Store/预算/Reporter/Agent 工具框架或固定双 Agent 工作流；没有必经的新 LLM 步骤。
- 重用原候选/配置/物理/scene 身份；原生数学绑定复用已有精确配置身份，没有新增 SHA manifest 或重复身份算法。

## 验证、失败保留与资源

**23 项不同的定向测试最终通过**：新 native 契约/合法差分/单参数范围/owned prefix/证据下钻 5 项，
原任务数学契约 14 项、旧请求序列化/授权 1 项、原卡片/读取模式 2 项、SoRoSim 原入口 1 项。
另完成一次上述四项真实案例组合、实际原输入复现、真实标量指针读取、矩阵按需读取、
原 Store receipt 的零重算复用和现有 Reporter/L0 投影检查。未运行全仓库测试或重复 S145–S148。

第一次数值 worker 的输入响应在返回后因局部修正量仍为 ndarray 而 JSON 发布失败。
已修复为显式列表；原失败 artifact、worker log、1 次分析额度和 wall 均保留。
通过原 `bind --reason` 语义迁移后用新 operation key 执行修复版本，没有覆盖旧请求或重置预算。
另一次视图检查将合法的矩阵**路径字符串**误判成矩阵内容，修正断言后直接复用原完成 receipt，未重做数值。

| 已发布的成功计算 | 模型构建 | 力学读出 | 显式 forward | 短时 rollout | 物理步 | 内核 wall/s | worker wall/s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 原生力学 | 1 | 1 | 3 | 0 | 0 | 0.029343 | 0.975549 |
| 输入响应及一次修正 | 1 | 1 | 53 | 25 | 500 | 0.062986 | 1.037020 |
| E 两档对照（含 reset 基线） | 3 | 4 | 18 | 3 | 60 | 0.103287 | 1.111733 |
| 截面高度对照（含 reset 基线） | 2 | 3 | 13 | 2 | 40 | 0.078446 | 1.045867 |
| 成功发布合计 | **7** | **9** | **87** | **30** | **600** | **0.274063** | **4.170169** |

原计数仍为 **8/8 数学求值**：成功发布 7 个模型求值，加原失败 1 次；实际含 5 次 contained analysis worker 启动。
失败 worker wall 为 **1.008925 s**，累计 worker wall **5.179094 s**。
原 Store 还记录候选构建累计 **0.546567 s**、numerical_s **5.823801 s**；它们有包含关系，不相加冒充总 CPU。

失败发生在最终 JSON 写出时，未持久化内核计数；按原固定请求/已进入的分支可确定完成了 baseline 和 23 个探针，
即 480 步，另一次候选核验可能再有 20 步。因此失败积分只报告 **480–500 步范围**，
本轮累计物理积分为 **1080–1100 步**，不能虚称完整精确计数。
额外 checkpoint 准备与零步进 smoke 共 4 次成功模型构建、7 次 forward、1 次力学读出，均为 0 物理步；
另一次临时目录 ACL 失败发生在 MuJoCo 模型加载之前，改为原编译器内存 XML 输出后解决。
这些工程准备没有被冒充为零成本，也没有篡改原数学 ledger 的含义。

MuJoCo 3.13.0、Python 3.11.16，原数值环境与线程设置未改；上述单次本机 wall 不证明实时能力。
Provider 请求、完整 NMPC/长时结构搜索、PPO、正式自主 Study、完整任务物理回放全部 **0**。
原 S142 SQLite 始终 `mode=ro&immutable=1` / `query_only=ON`，前后大小/mtime 和
events/artifacts/calls **478/532/73** 不变；原状态 stopped、pending=null。

证据使用原 Store 导出格式保存在 [`evidence/mujoco_native_stage_a`](../../evidence/mujoco_native_stage_a/)，
包含原失败和不可变原始结果；本地工作 Store 为 `runs/mujoco-native-stage-a/store`。
`summary.json` 给出结果/Reporter 引用与最新确定性视图；原始矩阵入口为各结果的 `/native_dynamics`。
导出只复用原有 `core.export`，没有另建持久化、查询或 SHA 系统。

## 阶段 B 可以复用与仍缺内容

可以直接复用合法结构生成/编译、具名原生 checkpoint、同起点克隆、实际张力执行、
原生力学/短时响应、现有受限局部响应优化、冻结约束代理，以及原 Store/成本/恢复/L0–L3。
后续离线控制优化仍需在单独阶段定义完整控制参数化与时域，构造轨迹级目标/约束，
处理整段导数成本与优化过程，并用独立完整 MuJoCo 回放和原冻结评价器核验。
当前接口最长 0.05 s、只有一个局部修正提案，没有开发这些阶段 B 功能，也不自动继续研究。
