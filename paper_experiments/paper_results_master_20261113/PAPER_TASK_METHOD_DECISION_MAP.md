# 11项 FULL 任务的数学方法与科研决策证据审计

本审计重建保存的研究过程，覆盖 T01–T10 与独立研究分支的九段四腱 PHS-2D。结构修改、控制搜索、数学诊断和独立物理验收分别报告。审计仅执行离线文件/JSON/CSV/SQLite解析、原始 artifact 哈希检查及 Git 检查，没有运行新的物理仿真、优化、求平衡或敏感性计算。

## 数据冻结、身份与推断范围

| 对象 | 冻结版本 | 证据范围 |
| --- | --- | --- |
| T01–T10 | `15d4667050351c1cbf84e6ade6f573286d6d8ed0` | [FULL证据索引](https://github.com/wran021004-gif/softrobot-agent/blob/15d4667050351c1cbf84e6ade6f573286d6d8ed0/paper_experiments/paper_results_master_20261113/EVIDENCE_INDEX.md)；最终指标/候选从该 commit 逐字节读取 |
| PHS九段主案例 | `9d6d160e050c836b87d0563a497fc0ec1c3761a8` | [第三轮报告](https://github.com/wran021004-gif/softrobot-agent/blob/9d6d160e050c836b87d0563a497fc0ec1c3761a8/docs/research/phs2d_round3_results_20261028.md)；[study_v1](https://github.com/wran021004-gif/softrobot-agent/blob/9d6d160e050c836b87d0563a497fc0ec1c3761a8/evidence/phs2d_round3_20261028/study_v1.json) / [study_v2](https://github.com/wran021004-gif/softrobot-agent/blob/9d6d160e050c836b87d0563a497fc0ec1c3761a8/evidence/phs2d_round3_20261028/study_v2.json) |
| 审计分支基点 | `15d4667050351c1cbf84e6ade6f573286d6d8ed0` | 核对远端所有分支头及祖先关系后，最新包含FULL基线的分支为origin/codex/m1-ablation-gates-20261111；远端main HEAD 2a854280不含该基线；独立工作树，不覆盖原工作区 |
| 补充原始过程 | 25份本地原始Trace，按文件SHA-256绑定 | 前驱/失败研究与Store只读核对；本文件末尾列全路径和哈希；不冒称全部属于Git冻结快照 |

FULL目录内 PHS 的 F0–F8、七段候选 `6115d7d9…`、8 s工况及其 14.798132 mm / 4.346997 mm 指标属于另一轮结构。它们全部排除于本报告的九段主案例。独立第三轮研究内也有一个七段中间候选；它有自己的 `P2_real_guides_7_circle` 身份，仅作为九段方案的真实前驱，不与FULL七段F8混用。

`candidate_id` 是候选的科学身份，`candidate_artifact_id` 是保存该候选的内容寻址artifact，`assembly` 另有身份。控制或任务绑定改变可能产生新候选ID而硬件不变；不能用ID变化直接声称结构变化。CSV 的 `structure_changes` 来自保存物理字段的逐字段差异；其比较基准明确标注，未补造父子关系。

T01/T04/T07/T09/T10 的完成研究有 Codex/Operator 组织、历史 Knowledge/Skill 输入及 Core 接口修复。T02/T03/T05/T06/T08 也保留原 `codex-surrogate-*` 研究身份。本文不把这些结果归为已经验证的 Main 全自主成功。九段PHS明确未执行Provider/Research Agent，仍是独立开发任务的数值见证。

## 方法判定与论文表述

Native Response 实际优化的是 knot-major 绝对张力偏移系数：对可施加的输入序列做单侧有限差分，形成局部控制响应矩阵，检查响应秩/SVD，再用 SLSQP epigraph 子问题提出有界控制修正，并根据真实原生响应更新信赖半径。裁剪输入时证据注明 projected response。局部子问题的解析约束Jacobian不构成结构解析梯度。Native Pattern 是有界坐标试探；T02保存了实际调用和未解决的失败。原生完整时域积分代理仍要求独立原任务重放。源实现导航见末尾代码表；调用本身以请求/返回artifact为证。

GVS、Native、Conic、LQR分别是模型/方法范围不同的名称。GVS静力适用性失败不等于真实机构静力不可行；`mujoco_nonlinear_task_capability_v1` 的方法名也不表示已经求得全局最优任务能力。本文将其 signed J 作为有限搜索最佳归一化违反量，J>0为剩余违反，J<0为该代理内余量；正式通过只取完整独立验收。未在本证据范围找到实际Conic结构敏感性请求，不能由工具目录或源文件存在补填。

| 层级 | 严格定义 | 本审计所需证据 |
| --- | --- | --- |
| M0 | $\partial m(d)/\partial d$ | 明确机制指标与其对结构变量的实际敏感性；仅Jacobian、秩或零空间不够 |
| M1 | $\left.\partial g_\tau(d,U)/\partial d\right\|_U$ | 真实结构扰动，并保持完整输入U一致；控制系数有限差分不属于此层 |
| M2 | $\mathrm d V_\tau(d)/\mathrm d d$ | 不同结构重新优化控制并审查最优值/导数意义；有限预算离散比较只能记M2-style |
| M3 | $\partial g_{\tau,H}(d,\theta)/\partial d$ | 结构扰动、实际闭环执行和结构对闭环性能的敏感性；使用反馈器本身不够 |

| 任务 | M0 | M1 | M2 | M3 |
| --- | --- | --- | --- | --- |
| T01 | not_executed | partial_or_analogous | partial_or_analogous | not_executed |
| T02 | not_executed | not_executed | partial_or_analogous | not_executed |
| T03 | not_executed | not_executed | not_executed | not_executed |
| T04 | not_executed | not_executed | not_executed | not_executed |
| T05 | not_executed | not_executed | not_executed | not_executed |
| T06 | not_executed | not_executed | not_executed | not_executed |
| T07 | not_executed | partial_or_analogous | partial_or_analogous | not_executed |
| T08 | partial_or_analogous | not_applicable | not_applicable | not_applicable |
| T09 | not_executed | not_executed | not_executed | not_executed |
| T10 | not_executed | not_executed | not_executed | not_executed |
| PHS-2D | partial_or_analogous | partial_or_analogous | not_applicable | not_applicable |

44个判定单元中：31个 `not_executed`、8个 `partial_or_analogous`、5个 `not_applicable`；没有单元支持严格 M0–M3 结构梯度的 `directly_executed`。PHS的被动平衡梯度在M1行的 `separate_passive_sensitivity_status=directly_executed` 单独报告。T01/T07的M1类比来自保存序列的事后精确比对，不声称原Agent执行了专门M1导数请求。没有把确定未执行误记为unavailable；unavailable用于确实缺失的输出/字段。T02任务名 `M2_loaded_hold`、T03任务名 `M3_fast_reach` 均不改变上述判定。

| 数学研究内容 | 实际调用/结果 | 可支持与不能支持的结论 |
| --- | --- | --- |
| 静力与动力学 | T01/T03有实际equilibrium构造；T02/T05不适用；T04原生平衡组；PHS硬绳静力与软约束动力学分列 | 静力张力只作构造/初值；完整动态验收单独确认 |
| Jacobian、秩、行空间、零空间 | PHS实际modal/matching输出；Native Response有控制响应秩/SVD；T10有原生状态/腱Jacobian | 这些对象的自变量不同；不自动构成机制对结构的M0梯度 |
| KKT、活跃约束、乘子、切线 | PHS实际硬绳KKT、正张力集合、LICQ/互补/稳定性及设计隐式导数；T10切线对状态q | PHS正则固定分支是局部结论；T10无结构扰动；未调用的最优控制包络/KKT方法不补填 |
| 固定输入结构响应 | T01/T07保存的旧优化序列与新结构初始序列可精确匹配；PHS固定放绳/载荷的被动平衡扰动单列 | 仅把重优化前、同U同任务同初态的保存响应记M1-style；后续控制系数FD不属于结构M1 |
| 重新优化任务能力 | T01/T02/T07实际不同结构上重新优化控制并比较有限预算J | M2-style，未证明真实最优V或报告dV/dd |
| 解析梯度、AD、隐式微分 | Native Response局部SLSQP约束有解析控制Jacobian；PHS实际KKT隐式微分；未见主动结构AD/解析梯度请求 | 未将GVS求解器内部状态/控制导数冒充结构梯度；PHS不是全解析或自动微分结构实现 |
| 有限差分与有限尺度联合修改 | 实际Native控制系数单侧FD；PHS归一化设计参数扰动/重新求平衡核查；T01/T07等联合结构变化 | 没有已执行的结构二阶交互/交叉偏导结果；联合修改不能拆分独立贡献 |
| 轨迹、制动、可控性 | T01/T02/T03/T07原生时域与执行器制动诊断；T04完整22 s轨迹；T10局部LQR与真实恢复 | 未由控制响应秩或LQR推出全局非线性可控性或闭环结构敏感性 |
| 有效性与适用性 | T02/T05拒绝不适用模型；T04构造标志/资格/动态分开；PHS几何/尾窗/KKT独立检查 | 失败求解不是不可行定理；小位移不是完整有效性或验收 |

### 保存记录中可匹配的固定输入比较

离线逐项核对旧结构 `optimized_schedule/trajectory` 与新结构 `original_schedule/trajectory`，确认完整times_s、tensions_n、tendon_order、任务/模型身份及实际初态q/qdot/u等字段完全相同，只有设计身份改变。下表只摘录原保存J，没有计算差、差商或新结构响应；每行在CSV标为 `audit_saved_input_match`，不是一次新科学请求。它支持有限尺度M1-style证据。新结构的同输入表现可能变差，而重新优化后改善；这正是固定输入效应与结构—控制适配应分开报告的原因。

| 任务 / 旧→新请求 | 旧结构保存优化J | 新结构保存初始J（同U） | 新结构重优化J | 原始raw artifact（旧；新） |
| --- | --- | --- | --- | --- |
| T01 / T01-115-native-central-dense-actuator-search → T01-119-native-smaller-radius-central | 0.4100053151313443 | 3.418903479491167 | 0.009565849011012428 | `4bb8321212f757c566405e3fd280c19eca8c39d86f0646fd260cd549fd8526f7`；`14a3da54422d5332718984261142600cd6d3ebb1aecd1c6f6b09af5314be3a3b` |
| T01 / T01-122-full-control-grid-final-local-test → T01-126-refine-minimum-radius-central | 0.0024707150086265006 | 0.02004445207971539 | 0.001987557745892543 | `0c174e524209b95d17a1250a88ca9c1b7b151781d50c2eab00310315ed9e9640`；`16229a2f8bb9e7d20f9f24a5062055f12f79cb35c9f63a6e22d5b2b082c0fb02` |
| T01 / T01-126-refine-minimum-radius-central → T01-130-native-reach-margin-central | 0.001987557745892543 | 1.6014929705187568 | -0.010000000000000009 | `16229a2f8bb9e7d20f9f24a5062055f12f79cb35c9f63a6e22d5b2b082c0fb02`；`6ce00fec834d6e8aeb02a5cafb7d37735a0e5e32fd74ecf13f52563f77eea78d` |
| T07 / T07-062-native-isotropic-root-A → T07-065-native-one-mm-root-A | 0.008747859181325923 | 0.20676534173453032 | 0.011385196907741868 | `9bed8bcffe4a11cfaee26afd5e2db1467251cd177b0b28a2bbd8ac53fd8f8b87`；`f09cba78ae1405ad7e395de7c7caa9a5a9284c70f18fff56e0ddf0fdec20a4f2` |
| T07 / T07-067-native-full-grid-root-A → T07-072-native-distributed-reach-A | 0.01098378058326177 | 1.6902056459555586 | 0.04396835416276468 | `c329b6dc404d55cd3e25ace9aac0436f4baa4eab3482a9a66c7cb5e37b86d38f`；`416f75cbf1d86a0fa322bc5788ddf757f3627b9d445ade8a0de1e03033ac06da` |
| T07 / T07-062-native-isotropic-root-A → T07-076-native-boundary-radius-best-root-A | 0.008747859181325923 | 0.0368948621643983 | -0.010000000000000009 | `9bed8bcffe4a11cfaee26afd5e2db1467251cd177b0b28a2bbd8ac53fd8f8b87`；`563f6dee16c28dda702b7f6a5552c4f7b681ebd1569b698f48b61f3472ede5fb` |

没有将这六对数据提升为局部结构导数或独立完整验收。原研究中这些序列承担初值迁移功能；本次审计仅证明保存数据的输入相同性。T02跨刚度的保存控制未找到同任务、同完整输入的匹配对，因此M1仍记not_executed。

## T01 多目标到达与保持

最终完成run内实际硬件修改是腱路半径18→14.1→14 mm，以及两段长度160/110→162.5/112.5 mm。各段材料和截面保持相应保存值；长度修改是两参数联合变化。前驱研究还保存了均匀/柔顺材料、默认长度、非对称路由等尝试，以及执行器密集约束修复前后的失败；它们在CSV标为precursor_or_superseded_run，不回填为最终结构的单因素贡献。

**结构及身份。** 最终执行结构为 2 段、6 腱、6 个独立执行器。本轮首个保存候选 artifact=`3bfd3e3abc7f0c47c5049972d4a09cec7a4ef2cf8506bebdfcfecbcb21ca1e14`，candidate_id=`core-15ba0c323c98da47b90bb171252dab475b76eb6cf948acdc688f1e9835cd368d`；其参数取自 [冻结首候选](https://github.com/wran021004-gif/softrobot-agent/blob/15d4667050351c1cbf84e6ade6f573286d6d8ed0/paper_experiments/paper_results_master_20261113/SOURCE_DATA/CANDIDATES/T01/3bfd3e3abc7f0c47c5049972d4a09cec7a4ef2cf8506bebdfcfecbcb21ca1e14.json)。最终工况候选身份见下表；不同工况的候选 ID 可不同，共同硬件须按结构字段比较。

| 段 | 长度 m | 材料参数（SI） | 截面站点 |
| --- | --- | --- | --- |
| segment_0 | 0.1625 | {"bending_ei_nm2":null,"bending_viscosity_nm2_s":[0.0005,0.0007],"density_kg_m3":1100.0,"line_density_kg_m":null,"mode":"material","young_pa":7200000.0} | s=0.0:ellipse {"semi_y_m":0.0095,"semi_z_m":0.0076} angle=0.35 |
| segment_1 | 0.1125 | {"bending_ei_nm2":null,"bending_viscosity_nm2_s":[0.0003,0.0004],"density_kg_m3":1050.0,"line_density_kg_m":null,"mode":"material","young_pa":5400000.0} | s=0.0:rectangle {"height_z_m":0.0095,"width_y_m":0.0133} angle=-0.25; s=1.0:rectangle {"height_z_m":0.008549999999999999,"width_y_m":0.0114} angle=0.15000000000000002 |

腱路请求：`[{"anchor_angle_offset_rad":0.0,"anchor_s":null,"angular_offsets_rad":[],"count":3,"first_segment":0,"guide_angle_offset_rad":0.0,"guide_s":null,"last_segment":0,"phase_rad":0.0,"radius_m":0.014},{"anchor_angle_offset_rad":0.0,"anchor_s":null,"angular_offsets_rad":[],"count":3,"first_segment":0,"guide_angle_offset_rad":0.0,"guide_s":null,"last_segment":1,"phase_rad":1.0471975511965976,"radius_m":0.014}]`。该表述只作索引，真实逐腱 RoutePoint、孔位、附件、COM、惯量、自然曲率和连接关系，以 [最终完整候选](https://github.com/wran021004-gif/softrobot-agent/blob/15d4667050351c1cbf84e6ade6f573286d6d8ed0/paper_experiments/paper_results_master_20261113/SOURCE_DATA/T01_central_high_CANDIDATE.json) 的 `/configuration/robot/structure/data` 为准。

| 保存run / 版本 | 代表候选artifact | 长度 m | E Pa | 实际差异摘要 |
| --- | --- | --- | --- | --- |
| codex-expert-T01-20261113-s1 / 1 | `3bfd3e3abc7f0c47c5049972d4a09cec7a4ef2cf8506bebdfcfecbcb21ca1e14` | [0.16, 0.11] | [7200000.0, 5400000.0] | 该run首版本；不是跨run因果父项 |
| codex-expert-T01-20261113-s1 / 2 | `60d7aafafc0a96c1dc4261a1c512cc9f1ce90e66a23bda01d69b0130d4325fb8` | [0.16, 0.11] | [7200000.0, 5400000.0] | 实际孔位/腱路坐标变化，逐字段见CSV |
| codex-expert-T01-20261113-s1 / 3 | `ba0b6bc760948beed871616a78a8d9f469a0a7f64e5cd110c003eef444c38177` | [0.16, 0.11] | [7200000.0, 5400000.0] | 实际孔位/腱路坐标变化，逐字段见CSV |
| codex-expert-T01-20261113-s1 / 4 | `4ee894d03a24742c6632ae5ee4c1a48d077a09d099d9ed2728bde45d470932d7` | [0.1625, 0.1125] | [7200000.0, 5400000.0] | /data/components/0/length_m: 0.16 → 0.1625; /data/components/3/length_m: 0.11 → 0.1125 |
| codex-expert-T01-20261113 / 1 | `98dd1698ed04ecd5b6fd9783414938bc4455fd19eea20dd3f95450fda08e75f2` | [0.16, 0.11] | [7200000.0, 5400000.0] | 该run首版本；不是跨run因果父项 |

版本及科学ID来自 [冻结CANDIDATE_EVOLUTION](https://github.com/wran021004-gif/softrobot-agent/blob/15d4667050351c1cbf84e6ade6f573286d6d8ed0/paper_experiments/paper_results_master_20261113/CANDIDATE_EVOLUTION.csv)。同一 run 内保存顺序只用于差异导航，未据此补造 `causal_parent`。前驱/已废弃研究的实际生成请求和结构差异另保留在决策 CSV；不把这些前驱候选的结果替换为 FULL 最终结果。

**控制与数学。** 最终使用 `mujoco_nonlinear_task_capability_v1` 与 `local_control_search_v2/response`，离线优化张力系数并开环完整重放。历史张力和当前工况张力只作输入初值。positive_high由当前central序列重新优化，未继承接受结果。前驱 `mechanism_structure_v1` 返回not_applicable；`native_dynamics_v1` 是原生力学诊断，不能据此标M0。未见结构固定输入导数、结构AD/解析梯度或闭环结构扰动。

| 实际请求方法 | 控制版本 | 返回状态 | 去重保存请求数 |
| --- | --- | --- | --- |
| equilibrium / GVS bounded-tension SLSQP construction (check applicability) | not_applicable | computed | 10 |
| mechanism_structure_v1 | not_applicable | not_applicable | 1 |
| mujoco_nonlinear_task_capability_v1 | local_control_search_v2 | computed | 33 |
| mujoco_nonlinear_task_capability_v1 | local_control_search_v2 | execution_incomplete | 1 |
| native_dynamics_v1 | not_applicable | computed | 1 |

| 节点 / run | Observation | Hypothesis | Decision / Modification | 保存结果 / 后续验证 |
| --- | --- | --- | --- | --- |
| `T01-116-generate-smaller-radius-hypothesis` / `codex-expert-T01-20261113-s1` | 原18 mm路由的原生控制搜索仍有腱速超限，J=0.4100053151313443。 | 缩小合法路由半径可减少相同弯曲的腱长变化，但所需力必须实测。 | 18 -> 14.1 mm；控制重新优化。 | 后续J依次0.009565849011012428、0.007976383626541184、0.0024707150086265006；未获完整通过。 |
| `T01-127-test-upward-reach-margin-geometry` / `codex-expert-T01-20261113-s1` | 14 mm路由下控制重优化仍有约0.199%峰值腱速超限。 | 增加近伸直目标的可达和制动余量。 | 两段同时从160/110改为162.5/112.5 mm。 | T01-130 J=-0.010000000000000009；后续三工况同结构独立验收3/3。 |
| `T01-159-native-positive-from-central-basin` / `codex-expert-T01-20261113-s1` | positive_high由原盆地延长搜索后J仍为0.22762472992368643。 | 当前同结构central控制可作为另一输入初值。 | 迁移当前central张力序列，再优化positive原任务。 | J=-0.010000000000000453；完整positive验收见FULL-final-positive_high。 |

这些链条是对原 rationale 和相邻请求的编辑性整理。`mathematical_method`、`mathematical_result`、`physical_validation_result` 与 `related_evidence_nodes` 保留计算及验收的边界；失败分支不据此推断全局不可行。

| 最终工况 / 角色 | 候选artifact | candidate_id | 原记录通过 | 原始指标（m、s、rad、N，比例无量纲） |
| --- | --- | --- | --- | --- |
| central_high / required | `cc436f71da2963e55b84a80258ca3ee590049a83ea707dd2f253a2f10a689161` | `core-9ba52ca3def428ee59326edf2a8bc8f6fac2a196593a2ffbd3b4e6abe26ae6ef` | True | `{"holding_max_error_m":0.009146735638176468,"holding_max_speed_m_s":0.029699999854067648,"geometric_tendon_speed_max_m_s":0.02475}` |
| negative_low / required | `5ead7a3a4d720bca70edac24ec7fc7f175b2af44d2437a21d5871dd62c22ebb0` | `core-b121acd5ec47188907cbc0b3e83b4434a34f318982cb2121d896204a6a7cf3a6` | True | `{"holding_max_error_m":0.009905895250612671,"holding_max_speed_m_s":0.0297196178042583,"geometric_tendon_speed_max_m_s":0.024772647745639094}` |
| positive_high / required | `a0313a7adbd1fe6657562aa2c2760d09c885baf79960fdfa4eaf0026bf2613fc` | `core-ce5a791d7ddd02503ce107f9d6821669febc050b164277a127d0530179e1246e` | True | `{"holding_max_error_m":0.009899999999999973,"holding_max_speed_m_s":0.029699999928910016,"geometric_tendon_speed_max_m_s":0.02474999999999999}` |

最终值引用 [冻结 TASK_CASE_RESULTS](https://github.com/wran021004-gif/softrobot-agent/blob/15d4667050351c1cbf84e6ade6f573286d6d8ed0/paper_experiments/paper_results_master_20261113/TASK_CASE_RESULTS.csv) 与 [T01 candidate/result/XML绑定](https://github.com/wran021004-gif/softrobot-agent/blob/15d4667050351c1cbf84e6ade6f573286d6d8ed0/paper_experiments/paper_results_master_20261113/SOURCE_DATA/MODEL_BINDINGS.json)；完整约束、原 result artifact 和 raw reference 保留在原表及决策 CSV 的 `FULL-final-*` 行。该表是原保存结果的审计视图，不增加执行或成本。

**M0–M3。** M0=`not_executed`；M1=`partial_or_analogous`；M2=`partial_or_analogous`；M3=`not_executed`。逐项定义、实际扰动、控制处理、证据 ID 和判定理由见配套审计 CSV。

## T02 带载受扰保持

唯一保存的本run结构修订是两段Young模量14→12 MPa；160/110 mm长度、圆截面与14.1 mm路由保持。两段模量同时变化，不分别归因。

**结构及身份。** 最终执行结构为 2 段、6 腱、6 个独立执行器。本轮首个保存候选 artifact=`0cfa8e1df7cce8f720f3b2c61e15fb3a60adf834039fc571865fe4c5332d2658`，candidate_id=`core-6eb4f711ee7204e1794bba64c0e49e0a0b865a84318b58736a9640c204a182b2`；其参数取自 [冻结首候选](https://github.com/wran021004-gif/softrobot-agent/blob/15d4667050351c1cbf84e6ade6f573286d6d8ed0/paper_experiments/paper_results_master_20261113/SOURCE_DATA/CANDIDATES/T02/0cfa8e1df7cce8f720f3b2c61e15fb3a60adf834039fc571865fe4c5332d2658.json)。最终工况候选身份见下表；不同工况的候选 ID 可不同，共同硬件须按结构字段比较。

| 段 | 长度 m | 材料参数（SI） | 截面站点 |
| --- | --- | --- | --- |
| segment_0 | 0.16 | {"bending_ei_nm2":null,"bending_viscosity_nm2_s":[0.0005,0.0007],"density_kg_m3":1100.0,"line_density_kg_m":null,"mode":"material","young_pa":12000000.0} | s=0.0:circle {"radius_m":0.009} angle=0.0 |
| segment_1 | 0.11 | {"bending_ei_nm2":null,"bending_viscosity_nm2_s":[0.0003,0.0004],"density_kg_m3":1050.0,"line_density_kg_m":null,"mode":"material","young_pa":12000000.0} | s=0.0:circle {"radius_m":0.007} angle=0.0; s=1.0:circle {"radius_m":0.007} angle=0.0 |

腱路请求：`[{"anchor_angle_offset_rad":0.0,"anchor_s":1.0,"angular_offsets_rad":[],"count":3,"first_segment":0,"guide_angle_offset_rad":0.0,"guide_s":[0.5],"last_segment":0,"phase_rad":0.0,"radius_m":0.0141},{"anchor_angle_offset_rad":0.0,"anchor_s":1.0,"angular_offsets_rad":[],"count":3,"first_segment":0,"guide_angle_offset_rad":0.0,"guide_s":[0.5],"last_segment":1,"phase_rad":1.0471975511965976,"radius_m":0.0141}]`。该表述只作索引，真实逐腱 RoutePoint、孔位、附件、COM、惯量、自然曲率和连接关系，以 [最终完整候选](https://github.com/wran021004-gif/softrobot-agent/blob/15d4667050351c1cbf84e6ade6f573286d6d8ed0/paper_experiments/paper_results_master_20261113/SOURCE_DATA/T02_negative_CANDIDATE.json) 的 `/configuration/robot/structure/data` 为准。

| 保存run / 版本 | 代表候选artifact | 长度 m | E Pa | 实际差异摘要 |
| --- | --- | --- | --- | --- |
| codex-surrogate-T02-20261112 / 1 | `0cfa8e1df7cce8f720f3b2c61e15fb3a60adf834039fc571865fe4c5332d2658` | [0.16, 0.11] | [14000000.0, 14000000.0] | 该run首版本；不是跨run因果父项 |
| codex-surrogate-T02-20261112 / 2 | `a54869e94ed3fbd05ecbde50ed62ec4cb2ff4e816c99491532ad648619650c17` | [0.16, 0.11] | [12000000.0, 12000000.0] | /data/components/0/physics/young_pa: 14000000.0 → 12000000.0; /data/components/3/physics/young_pa: 14000000.0 → 12000000.0 |

版本及科学ID来自 [冻结CANDIDATE_EVOLUTION](https://github.com/wran021004-gif/softrobot-agent/blob/15d4667050351c1cbf84e6ade6f573286d6d8ed0/paper_experiments/paper_results_master_20261113/CANDIDATE_EVOLUTION.csv)。同一 run 内保存顺序只用于差异导航，未据此补造 `causal_parent`。前驱/已废弃研究的实际生成请求和结构差异另保留在决策 CSV；不把这些前驱候选的结果替换为 FULL 最终结果。

**控制与数学。** T02-003的GVS静力请求因遗漏任务外力、模型验证缺失及基函数覆盖限制返回not_applicable。研究据此转向含真实外力的原生有限时域动力学。14 MPa下Response、精细Response及Pattern均留下正J；Pattern首次安全余量设置不兼容失败，后续合法设置实际执行。12 MPa结构分别重新优化负/正/零受力控制并独立验收。属于有限预算M2-style比较；没有材料导数或固定U实验。

| 实际请求方法 | 控制版本 | 返回状态 | 去重保存请求数 |
| --- | --- | --- | --- |
| equilibrium / GVS bounded-tension SLSQP construction (check applicability) | not_applicable | not_applicable | 1 |
| mujoco_nonlinear_task_capability_v1 | local_control_search_v2 | computed | 8 |
| mujoco_nonlinear_task_capability_v1 | local_control_search_v2 | no_output | 1 |

| 节点 / run | Observation | Hypothesis | Decision / Modification | 保存结果 / 后续验证 |
| --- | --- | --- | --- | --- |
| `T02-003-negative-fresh-static-input` / `codex-surrogate-T02-20261112` | 任务包含外部受力，GVS模型遗漏该力且模型一致性未验证。 | 静力构造不适用于完整带载任务。 | 保留not_applicable，不把请求当成成功静力求解。 | artifact f50ccf27633b77e5573076e0c507a307bb7c32493ae78643bb818d22d15d8ad5；转原生受力动力学。 |
| `T02-008-negative-pattern-compatible-settings` / `codex-surrogate-T02-20261112` | 14 MPa下Response细化停滞；Pattern首个请求因设置不兼容失败。 | 有限预算Pattern可能检查另一局部改进方向。 | 在原生动力学中改用合法Pattern设置；无结构扰动。 | 500 callbacks后J=0.04286055209469919；仍未通过。 |
| `T02-018-final-bounded-stiffness-comparison` / `codex-surrogate-T02-20261112` | 14 MPa结构三个受力工况的有限搜索仍有正违反量。 | 降低材料刚度可能缓解位置与制动冲突。 | 两段E同时14 -> 12 MPa，分别重新优化三工况控制。 | 最终3/3；最大保持误差0.009897088402492153 m；仅为M2-style经验比较。 |

这些链条是对原 rationale 和相邻请求的编辑性整理。`mathematical_method`、`mathematical_result`、`physical_validation_result` 与 `related_evidence_nodes` 保留计算及验收的边界；失败分支不据此推断全局不可行。

| 最终工况 / 角色 | 候选artifact | candidate_id | 原记录通过 | 原始指标（m、s、rad、N，比例无量纲） |
| --- | --- | --- | --- | --- |
| negative / required | `9df57f510c42a321e4f9f7b58fa67ddd7255ba39f4f5f3675e02c8a6a8ce8969` | `core-dcf0e30cadb05f529eb52313a4876e95f5ae9d7f8b3a24028aaed768beaf1fd9` | True | `{"holding_max_error_m":0.009897088402492153,"holding_max_speed_m_s":0.019757280334218204}` |
| positive / required | `6f75954bda64ef713ced9db0eff0139a19c71224ad60b21bb789464edf8ad647` | `core-b8e04ed0f174688c7fc8ad03db346ddf30a8878745c7ac4550a8de8af4c002c9` | True | `{"holding_max_error_m":0.009880943306424453,"holding_max_speed_m_s":0.019725865714044232}` |
| zero / required | `ebb144c06c9914db2ac14f70e03983cc9e46afca5e2ce5c91039461ca042738f` | `core-06409bc7a3901fe14efbed3958bd3751ef843e8916030720e193d6623e2d754a` | True | `{"holding_max_error_m":0.005357274331766039,"holding_max_speed_m_s":0.019790830274628676}` |

最终值引用 [冻结 TASK_CASE_RESULTS](https://github.com/wran021004-gif/softrobot-agent/blob/15d4667050351c1cbf84e6ade6f573286d6d8ed0/paper_experiments/paper_results_master_20261113/TASK_CASE_RESULTS.csv) 与 [T02 candidate/result/XML绑定](https://github.com/wran021004-gif/softrobot-agent/blob/15d4667050351c1cbf84e6ade6f573286d6d8ed0/paper_experiments/paper_results_master_20261113/SOURCE_DATA/MODEL_BINDINGS.json)；完整约束、原 result artifact 和 raw reference 保留在原表及决策 CSV 的 `FULL-final-*` 行。该表是原保存结果的审计视图，不增加执行或成本。

**M0–M3。** M0=`not_executed`；M1=`not_executed`；M2=`partial_or_analogous`；M3=`not_executed`。逐项定义、实际扰动、控制处理、证据 ID 和判定理由见配套审计 CSV。

## T03 快速到达

本run保持两段160/110 mm、各12 MPa、六腱六执行器结构；候选身份更新来自任务/控制绑定，没有保存的硬件修订。

**结构及身份。** 最终执行结构为 2 段、6 腱、6 个独立执行器。本轮首个保存候选 artifact=`ae40f2af576044f51837dfa1058f25d001d46e9a72dbe20f55c94945c0898960`，candidate_id=`core-52e4dbb14a159b64c4d1b51390208efcf82f99a55023eb5d56b5cc80b1eb9da8`；其参数取自 [冻结首候选](https://github.com/wran021004-gif/softrobot-agent/blob/15d4667050351c1cbf84e6ade6f573286d6d8ed0/paper_experiments/paper_results_master_20261113/SOURCE_DATA/CANDIDATES/T03/ae40f2af576044f51837dfa1058f25d001d46e9a72dbe20f55c94945c0898960.json)。最终工况候选身份见下表；不同工况的候选 ID 可不同，共同硬件须按结构字段比较。

| 段 | 长度 m | 材料参数（SI） | 截面站点 |
| --- | --- | --- | --- |
| segment_0 | 0.16 | {"bending_ei_nm2":null,"bending_viscosity_nm2_s":[0.0005,0.0007],"density_kg_m3":1100.0,"line_density_kg_m":null,"mode":"material","young_pa":12000000.0} | s=0.0:circle {"radius_m":0.009} angle=0.0 |
| segment_1 | 0.11 | {"bending_ei_nm2":null,"bending_viscosity_nm2_s":[0.0003,0.0004],"density_kg_m3":1050.0,"line_density_kg_m":null,"mode":"material","young_pa":12000000.0} | s=0.0:circle {"radius_m":0.007} angle=0.0; s=1.0:circle {"radius_m":0.007} angle=0.0 |

腱路请求：`[{"anchor_angle_offset_rad":0.0,"anchor_s":1.0,"angular_offsets_rad":[],"count":3,"first_segment":0,"guide_angle_offset_rad":0.0,"guide_s":[0.5],"last_segment":0,"phase_rad":0.0,"radius_m":0.0141},{"anchor_angle_offset_rad":0.0,"anchor_s":1.0,"angular_offsets_rad":[],"count":3,"first_segment":0,"guide_angle_offset_rad":0.0,"guide_s":[0.5],"last_segment":1,"phase_rad":1.0471975511965976,"radius_m":0.0141}]`。该表述只作索引，真实逐腱 RoutePoint、孔位、附件、COM、惯量、自然曲率和连接关系，以 [最终完整候选](https://github.com/wran021004-gif/softrobot-agent/blob/15d4667050351c1cbf84e6ade6f573286d6d8ed0/paper_experiments/paper_results_master_20261113/SOURCE_DATA/T03_default_CANDIDATE.json) 的 `/configuration/robot/structure/data` 为准。

| 保存run / 版本 | 代表候选artifact | 长度 m | E Pa | 实际差异摘要 |
| --- | --- | --- | --- | --- |
| codex-surrogate-T03-20261112 / 1 | `ae40f2af576044f51837dfa1058f25d001d46e9a72dbe20f55c94945c0898960` | [0.16, 0.11] | [12000000.0, 12000000.0] | 该run首版本；不是跨run因果父项 |

版本及科学ID来自 [冻结CANDIDATE_EVOLUTION](https://github.com/wran021004-gif/softrobot-agent/blob/15d4667050351c1cbf84e6ade6f573286d6d8ed0/paper_experiments/paper_results_master_20261113/CANDIDATE_EVOLUTION.csv)。同一 run 内保存顺序只用于差异导航，未据此补造 `causal_parent`。前驱/已废弃研究的实际生成请求和结构差异另保留在决策 CSV；不把这些前驱候选的结果替换为 FULL 最终结果。

**控制与数学。** 先实际调用GVS静力构造获得目标张力信息，再把0.5 s快速到达与0.45–0.5 s保持、制动及执行器约束放入原生Response搜索。优化变量是张力系数；最终完整独立重放。静力结果是初值/诊断，不是快速可达证书。任务标签M3没有闭环敏感性含义。

| 实际请求方法 | 控制版本 | 返回状态 | 去重保存请求数 |
| --- | --- | --- | --- |
| equilibrium / GVS bounded-tension SLSQP construction (check applicability) | not_applicable | computed | 1 |
| mujoco_nonlinear_task_capability_v1 | local_control_search_v2 | computed | 1 |

| 节点 / run | Observation | Hypothesis | Decision / Modification | 保存结果 / 后续验证 |
| --- | --- | --- | --- | --- |
| `T03-005-full-original-fast-reach-native-search` / `codex-surrogate-T03-20261112` | 目标静力张力不能证明0.5 s到达与0.45-0.5 s保持。 | 把运动与制动一起纳入完整原生时域搜索。 | 固定结构，Response优化张力控制系数。 | 独立验收终端误差2.1099 mm、保持最大2.6627 mm（精确值见最终行）。 |

这些链条是对原 rationale 和相邻请求的编辑性整理。`mathematical_method`、`mathematical_result`、`physical_validation_result` 与 `related_evidence_nodes` 保留计算及验收的边界；失败分支不据此推断全局不可行。

| 最终工况 / 角色 | 候选artifact | candidate_id | 原记录通过 | 原始指标（m、s、rad、N，比例无量纲） |
| --- | --- | --- | --- | --- |
| default / required | `79fde88c9ae96823dd1e61edc572523fbecf785b4b50effbf7ea4cc0736c309e` | `core-f3172b2bec2f4c4762ed028583aa605ff7edf5b2695840a1e9d0f87a510ec330` | True | `{"terminal_error_m":0.002109920802953995,"holding_max_error_m":0.002662671632155634}` |

最终值引用 [冻结 TASK_CASE_RESULTS](https://github.com/wran021004-gif/softrobot-agent/blob/15d4667050351c1cbf84e6ade6f573286d6d8ed0/paper_experiments/paper_results_master_20261113/TASK_CASE_RESULTS.csv) 与 [T03 candidate/result/XML绑定](https://github.com/wran021004-gif/softrobot-agent/blob/15d4667050351c1cbf84e6ade6f573286d6d8ed0/paper_experiments/paper_results_master_20261113/SOURCE_DATA/MODEL_BINDINGS.json)；完整约束、原 result artifact 和 raw reference 保留在原表及决策 CSV 的 `FULL-final-*` 行。该表是原保存结果的审计视图，不增加执行或成本。

**M0–M3。** M0=`not_executed`；M1=`not_executed`；M2=`not_executed`；M3=`not_executed`。逐项定义、实际扰动、控制处理、证据 ID 和判定理由见配套审计 CSV。

## T04 双叶八字轨迹跟踪

历史单段0.27 m只作参考；实际合法结构为140/118 mm、各4 MPa、四腱四执行器。后续三run保存的几何一致，主要变化在初态/控制构造与接口版本，不应写成后期结构优化。

**结构及身份。** 最终执行结构为 2 段、4 腱、4 个独立执行器。本轮首个保存候选 artifact=`5bb8205923a19aa2f423c02d34e1a3907512b4078eb43827103bf196dfc273ed`，candidate_id=`core-b7cc8e9f6bd8c6f9f69ff9903b50a50a4a89d932fb6e3d009967213ed17c1093`；其参数取自 [冻结首候选](https://github.com/wran021004-gif/softrobot-agent/blob/15d4667050351c1cbf84e6ade6f573286d6d8ed0/paper_experiments/paper_results_master_20261113/SOURCE_DATA/CANDIDATES/T04/5bb8205923a19aa2f423c02d34e1a3907512b4078eb43827103bf196dfc273ed.json)。最终工况候选身份见下表；不同工况的候选 ID 可不同，共同硬件须按结构字段比较。

| 段 | 长度 m | 材料参数（SI） | 截面站点 |
| --- | --- | --- | --- |
| segment_0 | 0.14 | {"bending_ei_nm2":null,"bending_viscosity_nm2_s":[0.0005,0.0007],"density_kg_m3":1100.0,"line_density_kg_m":null,"mode":"material","young_pa":4000000.0} | s=0.0:circle {"radius_m":0.008} angle=0.0 |
| segment_1 | 0.118 | {"bending_ei_nm2":null,"bending_viscosity_nm2_s":[0.0003,0.0004],"density_kg_m3":1050.0,"line_density_kg_m":null,"mode":"material","young_pa":4000000.0} | s=0.0:circle {"radius_m":0.008} angle=0.0; s=1.0:circle {"radius_m":0.008} angle=0.0 |

腱路请求：`[{"anchor_angle_offset_rad":0.0,"anchor_s":null,"angular_offsets_rad":[],"count":4,"first_segment":0,"guide_angle_offset_rad":0.0,"guide_s":null,"last_segment":1,"phase_rad":0.0,"radius_m":0.0141}]`。该表述只作索引，真实逐腱 RoutePoint、孔位、附件、COM、惯量、自然曲率和连接关系，以 [最终完整候选](https://github.com/wran021004-gif/softrobot-agent/blob/15d4667050351c1cbf84e6ade6f573286d6d8ed0/paper_experiments/paper_results_master_20261113/SOURCE_DATA/T04_default_CANDIDATE.json) 的 `/configuration/robot/structure/data` 为准。

| 保存run / 版本 | 代表候选artifact | 长度 m | E Pa | 实际差异摘要 |
| --- | --- | --- | --- | --- |
| codex-expert-T04-20261113-s1 / 1 | `8d5a5e8bf6d39908b05dc48138378c458bfa6866f1998516c9284907de0dbc9a` | [0.14, 0.118] | [4000000.0, 4000000.0] | 该run首版本；不是跨run因果父项 |
| codex-expert-T04-20261113-core028-bank / 1 | `6c3ba33f447d4fa1181421b1589bd2df69047d041e2ac55f9285e21262f7dcbb` | [0.14, 0.118] | [4000000.0, 4000000.0] | 该run首版本；不是跨run因果父项 |
| codex-expert-T04-20261113-core029-interior / 1 | `5bb8205923a19aa2f423c02d34e1a3907512b4078eb43827103bf196dfc273ed` | [0.14, 0.118] | [4000000.0, 4000000.0] | 该run首版本；不是跨run因果父项 |

版本及科学ID来自 [冻结CANDIDATE_EVOLUTION](https://github.com/wran021004-gif/softrobot-agent/blob/15d4667050351c1cbf84e6ade6f573286d6d8ed0/paper_experiments/paper_results_master_20261113/CANDIDATE_EVOLUTION.csv)。同一 run 内保存顺序只用于差异导航，未据此补造 `causal_parent`。前驱/已废弃研究的实际生成请求和结构差异另保留在决策 CSV；不把这些前驱候选的结果替换为 FULL 最终结果。

**控制与数学。** 早期停止于初态接口缺口；后续GVS/NMPC完整试验未建立成功，转原生SLSQP平衡点组。RUN_02的组构造返回迭代上限，后续重放因phase_rad接口缺失失败。RUN_03全4 N种子触发原生守卫；局部t0平衡加0.21 N内点种子生成89点组。其optimizer_success=false、qualified=false被保留，随后单独task.initial_state.qualify检查通过。Core将返回张力插值到10 ms控制网格并零阶保持，最终22 s独立开环前馈通过；未把静态优化终态直接当动态验收。

| 实际请求方法 | 控制版本 | 返回状态 | 去重保存请求数 |
| --- | --- | --- | --- |
| equilibrium / GVS bounded-tension SLSQP construction (check applicability) | not_applicable | not_applicable | 1 |
| native_dynamics_v1 | not_applicable | computed | 1 |

| 节点 / run | Observation | Hypothesis | Decision / Modification | 保存结果 / 后续验证 |
| --- | --- | --- | --- | --- |
| `T04-010-generate-legal-tracking-geometry` / `codex-expert-T04-20261113-s1` | 历史单段0.27 m结构不满足当前设计域。 | 可迁移准静态思路，但须重建合法结构与初态。 | 请求合法两段；失败/修正请求分别保留，不将未生成候选算作修改。 | 最终实际结构140/118 mm；中间GVS路线未建立完整成功。 |
| `T04-211-construct-native-frozen-reference-bank` / `codex-expert-T04-20261113-core029-interior` | 89点平衡组的全4 N初值/试探触发原生状态守卫。 | 平衡组初值需贴近已知局部物理平衡。 | 保留构造失败；不关闭守卫或放松物理验收。 | RUN_03失败NATIVE_V1_REQUIRES_FINITE_CONTACT_FREE_UNCONSTRAINED_STATE；RUN_02与RUN_03须按run_id区分。 |
| `T04-216-construct-local-interior-reference-bank` / `codex-expert-T04-20261113-core029-interior` | 全4 N初值构造失败，已存在t0平衡。 | 局部平衡加内点预张力可修复构造初值。 | 采用当前t0状态；仅将0.2 N项内移到0.21 N；构造89点。 | 最大静态位置误差0.0006110494311492155 m；optimizer_success=false且qualified=false；随后单独资格检查通过。 |
| `T04-220-independent-full-local-interior-feedforward` / `codex-expert-T04-20261113-core029-interior` | 可用静态组不保证22 s双周期动态跟踪。 | 经独立初态资格的平衡张力前馈可完成原任务。 | 89点张力由Core插值到10 ms网格再零阶保持，独立全时域重放。 | 完整22 s通过；RMSE0.68785 mm，最大1.02066 mm；无结构梯度。 |

这些链条是对原 rationale 和相邻请求的编辑性整理。`mathematical_method`、`mathematical_result`、`physical_validation_result` 与 `related_evidence_nodes` 保留计算及验收的边界；失败分支不据此推断全局不可行。

| 最终工况 / 角色 | 候选artifact | candidate_id | 原记录通过 | 原始指标（m、s、rad、N，比例无量纲） |
| --- | --- | --- | --- | --- |
| default / required | `a2b86a9c493cbc5d15bc37f341f86ec0600f418522b41f8e8c8d3de8fc92884f` | `core-c9bb26910328b896b9d19bb52ae2ec0a75d35675161731df476f4d0df1402206` | True | `{"tracking_rmse_m":0.0006878528448055238,"max_error_m":0.0010206639031726755,"cycle_phase_matched_max_difference_m":0.0010088782522628332}` |

最终值引用 [冻结 TASK_CASE_RESULTS](https://github.com/wran021004-gif/softrobot-agent/blob/15d4667050351c1cbf84e6ade6f573286d6d8ed0/paper_experiments/paper_results_master_20261113/TASK_CASE_RESULTS.csv) 与 [T04 candidate/result/XML绑定](https://github.com/wran021004-gif/softrobot-agent/blob/15d4667050351c1cbf84e6ade6f573286d6d8ed0/paper_experiments/paper_results_master_20261113/SOURCE_DATA/MODEL_BINDINGS.json)；完整约束、原 result artifact 和 raw reference 保留在原表及决策 CSV 的 `FULL-final-*` 行。该表是原保存结果的审计视图，不增加执行或成本。

**M0–M3。** M0=`not_executed`；M1=`not_executed`；M2=`not_executed`；M3=`not_executed`。逐项定义、实际扰动、控制处理、证据 ID 和判定理由见配套审计 CSV。

## T05 工具位置与有向轴姿态

本run固定两段160/110 mm、各12 MPa、六腱六执行器，保留10 g真实工具COM与完整惯量；没有实测的结构修改。

**结构及身份。** 最终执行结构为 2 段、6 腱、6 个独立执行器。本轮首个保存候选 artifact=`83fa73b8bf78d9179e6d2894022ff74722e95f9cd6aa6dbad0207d3092904f0c`，candidate_id=`core-d28cb63e809aed71a9507521102c5b7ffaae3cd2c61bcaab30040af024ab1ddc`；其参数取自 [冻结首候选](https://github.com/wran021004-gif/softrobot-agent/blob/15d4667050351c1cbf84e6ade6f573286d6d8ed0/paper_experiments/paper_results_master_20261113/SOURCE_DATA/CANDIDATES/T05/83fa73b8bf78d9179e6d2894022ff74722e95f9cd6aa6dbad0207d3092904f0c.json)。最终工况候选身份见下表；不同工况的候选 ID 可不同，共同硬件须按结构字段比较。

| 段 | 长度 m | 材料参数（SI） | 截面站点 |
| --- | --- | --- | --- |
| segment_0 | 0.16 | {"bending_ei_nm2":null,"bending_viscosity_nm2_s":[0.0005,0.0007],"density_kg_m3":1100.0,"line_density_kg_m":null,"mode":"material","young_pa":12000000.0} | s=0.0:circle {"radius_m":0.009} angle=0.0 |
| segment_1 | 0.11 | {"bending_ei_nm2":null,"bending_viscosity_nm2_s":[0.0003,0.0004],"density_kg_m3":1050.0,"line_density_kg_m":null,"mode":"material","young_pa":12000000.0} | s=0.0:circle {"radius_m":0.007} angle=0.0; s=1.0:circle {"radius_m":0.007} angle=0.0 |

腱路请求：`[{"anchor_angle_offset_rad":0.0,"anchor_s":1.0,"angular_offsets_rad":[],"count":3,"first_segment":0,"guide_angle_offset_rad":0.0,"guide_s":[0.5],"last_segment":0,"phase_rad":0.0,"radius_m":0.0141},{"anchor_angle_offset_rad":0.0,"anchor_s":1.0,"angular_offsets_rad":[],"count":3,"first_segment":0,"guide_angle_offset_rad":0.0,"guide_s":[0.5],"last_segment":1,"phase_rad":1.0471975511965976,"radius_m":0.0141}]`。该表述只作索引，真实逐腱 RoutePoint、孔位、附件、COM、惯量、自然曲率和连接关系，以 [最终完整候选](https://github.com/wran021004-gif/softrobot-agent/blob/15d4667050351c1cbf84e6ade6f573286d6d8ed0/paper_experiments/paper_results_master_20261113/SOURCE_DATA/T05_default_CANDIDATE.json) 的 `/configuration/robot/structure/data` 为准。

| 保存run / 版本 | 代表候选artifact | 长度 m | E Pa | 实际差异摘要 |
| --- | --- | --- | --- | --- |
| codex-surrogate-T05-20261112 / 1 | `83fa73b8bf78d9179e6d2894022ff74722e95f9cd6aa6dbad0207d3092904f0c` | [0.16, 0.11] | [12000000.0, 12000000.0] | 该run首版本；不是跨run因果父项 |

版本及科学ID来自 [冻结CANDIDATE_EVOLUTION](https://github.com/wran021004-gif/softrobot-agent/blob/15d4667050351c1cbf84e6ade6f573286d6d8ed0/paper_experiments/paper_results_master_20261113/CANDIDATE_EVOLUTION.csv)。同一 run 内保存顺序只用于差异导航，未据此补造 `causal_parent`。前驱/已废弃研究的实际生成请求和结构差异另保留在决策 CSV；不把这些前驱候选的结果替换为 FULL 最终结果。

**控制与数学。** GVS/仿射位置静力请求返回not_applicable，因为完整任务还有有向工具轴。转mujoco_direct_control_v1，Native Response联合优化位置与轴向的张力控制系数，最终开环独立重放。实际局部轴到世界轴变换参与评估；没有结构参数求导。

| 实际请求方法 | 控制版本 | 返回状态 | 去重保存请求数 |
| --- | --- | --- | --- |
| equilibrium / GVS bounded-tension SLSQP construction (check applicability) | not_applicable | not_applicable | 1 |
| mujoco_direct_control_v1 | local_control_search_v2 | computed | 1 |

| 节点 / run | Observation | Hypothesis | Decision / Modification | 保存结果 / 后续验证 |
| --- | --- | --- | --- | --- |
| `T05-003-fresh-position-static-trial-only` / `codex-surrogate-T05-20261112` | 位置与有向工具轴两类约束必须同时满足。 | 现有仿射/GVS静力位置分析不能覆盖该任务。 | 保留not_applicable，转mujoco_direct_control_v1。 | 原生联合位置/轴向搜索后独立完整通过。 |
| `T05-005-native-directed-position-and-axis-search` / `codex-surrogate-T05-20261112` | 静力工具不适用于完整位置/轴向约束。 | 真实工具COM/惯量及轴变换应进入原生控制响应。 | 固定结构，联合优化位置和有向轴的张力控制系数。 | 完整验收位置7.4585 mm，轴向0.0518235 rad；局部求解器成功不单独代表验收。 |

这些链条是对原 rationale 和相邻请求的编辑性整理。`mathematical_method`、`mathematical_result`、`physical_validation_result` 与 `related_evidence_nodes` 保留计算及验收的边界；失败分支不据此推断全局不可行。

| 最终工况 / 角色 | 候选artifact | candidate_id | 原记录通过 | 原始指标（m、s、rad、N，比例无量纲） |
| --- | --- | --- | --- | --- |
| default / required | `b43827b0a1cd9f98a93aa3340fb577c8d599acae84d117e0d24d7a44c128f5b2` | `core-f8e4901b2264bc3c3c6ab055271c4f8ca4dcbd4791d26ecba23a3f5200c84208` | True | `{"max_position_error":0.007458477556880469,"max_tool_axis_angle_error":0.05182348756322416}` |

最终值引用 [冻结 TASK_CASE_RESULTS](https://github.com/wran021004-gif/softrobot-agent/blob/15d4667050351c1cbf84e6ade6f573286d6d8ed0/paper_experiments/paper_results_master_20261113/TASK_CASE_RESULTS.csv) 与 [T05 candidate/result/XML绑定](https://github.com/wran021004-gif/softrobot-agent/blob/15d4667050351c1cbf84e6ade6f573286d6d8ed0/paper_experiments/paper_results_master_20261113/SOURCE_DATA/MODEL_BINDINGS.json)；完整约束、原 result artifact 和 raw reference 保留在原表及决策 CSV 的 `FULL-final-*` 行。该表是原保存结果的审计视图，不增加执行或成本。

**M0–M3。** M0=`not_executed`；M1=`not_executed`；M2=`not_executed`；M3=`not_executed`。逐项定义、实际扰动、控制处理、证据 ID 和判定理由见配套审计 CSV。

## T06 带载位置—姿态扫描

本run固定两段160/110 mm、各12 MPa、六腱六执行器，保留20 g负载、COM、完整非对角惯量；未保存结构变更。

**结构及身份。** 最终执行结构为 2 段、6 腱、6 个独立执行器。本轮首个保存候选 artifact=`2bed9ba999538c46c5cb50daa76f9e4f40387dfdf351674dcf1609fd61b9761c`，candidate_id=`core-8b3c965f416d6b660e4071c1ce5954db0ecfee049e1b09a29c977b11fcca92e8`；其参数取自 [冻结首候选](https://github.com/wran021004-gif/softrobot-agent/blob/15d4667050351c1cbf84e6ade6f573286d6d8ed0/paper_experiments/paper_results_master_20261113/SOURCE_DATA/CANDIDATES/T06/2bed9ba999538c46c5cb50daa76f9e4f40387dfdf351674dcf1609fd61b9761c.json)。最终工况候选身份见下表；不同工况的候选 ID 可不同，共同硬件须按结构字段比较。

| 段 | 长度 m | 材料参数（SI） | 截面站点 |
| --- | --- | --- | --- |
| segment_0 | 0.16 | {"bending_ei_nm2":null,"bending_viscosity_nm2_s":[0.0005,0.0007],"density_kg_m3":1100.0,"line_density_kg_m":null,"mode":"material","young_pa":12000000.0} | s=0.0:circle {"radius_m":0.009} angle=0.0 |
| segment_1 | 0.11 | {"bending_ei_nm2":null,"bending_viscosity_nm2_s":[0.0003,0.0004],"density_kg_m3":1050.0,"line_density_kg_m":null,"mode":"material","young_pa":12000000.0} | s=0.0:circle {"radius_m":0.007} angle=0.0; s=1.0:circle {"radius_m":0.007} angle=0.0 |

腱路请求：`[{"anchor_angle_offset_rad":0.0,"anchor_s":1.0,"angular_offsets_rad":[],"count":3,"first_segment":0,"guide_angle_offset_rad":0.0,"guide_s":[0.5],"last_segment":0,"phase_rad":0.0,"radius_m":0.0141},{"anchor_angle_offset_rad":0.0,"anchor_s":1.0,"angular_offsets_rad":[],"count":3,"first_segment":0,"guide_angle_offset_rad":0.0,"guide_s":[0.5],"last_segment":1,"phase_rad":1.0471975511965976,"radius_m":0.0141}]`。该表述只作索引，真实逐腱 RoutePoint、孔位、附件、COM、惯量、自然曲率和连接关系，以 [最终完整候选](https://github.com/wran021004-gif/softrobot-agent/blob/15d4667050351c1cbf84e6ade6f573286d6d8ed0/paper_experiments/paper_results_master_20261113/SOURCE_DATA/T06_default_CANDIDATE.json) 的 `/configuration/robot/structure/data` 为准。

| 保存run / 版本 | 代表候选artifact | 长度 m | E Pa | 实际差异摘要 |
| --- | --- | --- | --- | --- |
| codex-surrogate-T06-20261112 / 1 | `2bed9ba999538c46c5cb50daa76f9e4f40387dfdf351674dcf1609fd61b9761c` | [0.16, 0.11] | [12000000.0, 12000000.0] | 该run首版本；不是跨run因果父项 |

版本及科学ID来自 [冻结CANDIDATE_EVOLUTION](https://github.com/wran021004-gif/softrobot-agent/blob/15d4667050351c1cbf84e6ade6f573286d6d8ed0/paper_experiments/paper_results_master_20261113/CANDIDATE_EVOLUTION.csv)。同一 run 内保存顺序只用于差异导航，未据此补造 `causal_parent`。前驱/已废弃研究的实际生成请求和结构差异另保留在决策 CSV；不把这些前驱候选的结果替换为 FULL 最终结果。

**控制与数学。** 实际方法为mujoco_direct_control_v1与local_control_search_v2/response，优化0.6 s时序位置/轴向任务的张力控制系数，随后完整独立开环重放。未发现本任务实际调用GVS静力、结构KKT、结构AD或Conic求解；目录中存在这些工具不算调用。

| 实际请求方法 | 控制版本 | 返回状态 | 去重保存请求数 |
| --- | --- | --- | --- |
| mujoco_direct_control_v1 | local_control_search_v2 | computed | 1 |

| 节点 / run | Observation | Hypothesis | Decision / Modification | 保存结果 / 后续验证 |
| --- | --- | --- | --- | --- |
| `T06-004-native-full-loaded-timed-axis-search` / `codex-surrogate-T06-20261112` | 20 g负载、时序位置及有向轴不能用单点静力代表。 | 完整时序原生响应可联合处理真实约束。 | 固定结构，0.6 s Native Direct Response控制搜索。 | 独立验收最大位置11.8198 mm、轴向0.110448 rad。 |

这些链条是对原 rationale 和相邻请求的编辑性整理。`mathematical_method`、`mathematical_result`、`physical_validation_result` 与 `related_evidence_nodes` 保留计算及验收的边界；失败分支不据此推断全局不可行。

| 最终工况 / 角色 | 候选artifact | candidate_id | 原记录通过 | 原始指标（m、s、rad、N，比例无量纲） |
| --- | --- | --- | --- | --- |
| default / required | `2e254af5ad79897b25f701d3f5e2ce72bf92e21a6bff6ae6b21519bb1814653b` | `core-69886b40d1b203929f8d6cf833bd3d2b044f20966cbc08f42f75bc56e9605416` | True | `{"max_position_error":0.011819789230672182,"max_tool_axis_angle_error":0.11044811880898212}` |

最终值引用 [冻结 TASK_CASE_RESULTS](https://github.com/wran021004-gif/softrobot-agent/blob/15d4667050351c1cbf84e6ade6f573286d6d8ed0/paper_experiments/paper_results_master_20261113/TASK_CASE_RESULTS.csv) 与 [T06 candidate/result/XML绑定](https://github.com/wran021004-gif/softrobot-agent/blob/15d4667050351c1cbf84e6ade6f573286d6d8ed0/paper_experiments/paper_results_master_20261113/SOURCE_DATA/MODEL_BINDINGS.json)；完整约束、原 result artifact 和 raw reference 保留在原表及决策 CSV 的 `FULL-final-*` 行。该表是原保存结果的审计视图，不增加执行或成本。

**M0–M3。** M0=`not_executed`；M1=`not_executed`；M2=`not_executed`；M3=`not_executed`。逐项定义、实际扰动、控制处理、证据 ID 和判定理由见配套审计 CSV。

## T07 四独立腱共同结构多任务

共同硬件依次经历18→14.1 mm路由、根段椭圆改8 mm圆、158.5→159.5 mm根段长度、162.5/112.5 mm分布增长，以及回退158.5/109 mm并将路由降至14 mm。末段材料/渐变矩形及四个独立输入保留。根段截面修改同时影响质量、惯性、刚度及耦合；最终回退节点同时改变两段长度和路由，不拆成独立贡献。

**结构及身份。** 最终执行结构为 2 段、4 腱、4 个独立执行器。本轮首个保存候选 artifact=`2b7f1d1bb5c7bda061239f157c2c0e312a2c085c457ac7b746de69c48c3304c5`，candidate_id=`core-b678a5028aa41ba37526bed67ea421f957ae47102eb3306e4b316f24cf7e4aa9`；其参数取自 [冻结首候选](https://github.com/wran021004-gif/softrobot-agent/blob/15d4667050351c1cbf84e6ade6f573286d6d8ed0/paper_experiments/paper_results_master_20261113/SOURCE_DATA/CANDIDATES/T07/2b7f1d1bb5c7bda061239f157c2c0e312a2c085c457ac7b746de69c48c3304c5.json)。最终工况候选身份见下表；不同工况的候选 ID 可不同，共同硬件须按结构字段比较。

| 段 | 长度 m | 材料参数（SI） | 截面站点 |
| --- | --- | --- | --- |
| segment_0 | 0.1585 | {"bending_ei_nm2":null,"bending_viscosity_nm2_s":[0.0005,0.0007],"density_kg_m3":1100.0,"line_density_kg_m":null,"mode":"material","young_pa":7200000.0} | s=0.0:circle {"radius_m":0.008} angle=0.0 |
| segment_1 | 0.109 | {"bending_ei_nm2":null,"bending_viscosity_nm2_s":[0.0003,0.0004],"density_kg_m3":1050.0,"line_density_kg_m":null,"mode":"material","young_pa":5400000.0} | s=0.0:rectangle {"height_z_m":0.0095,"width_y_m":0.0133} angle=-0.25; s=1.0:rectangle {"height_z_m":0.008549999999999999,"width_y_m":0.0114} angle=0.15000000000000002 |

腱路请求：`[{"anchor_angle_offset_rad":0.0,"anchor_s":null,"angular_offsets_rad":[0.0,-0.5235987755982987],"count":2,"first_segment":0,"guide_angle_offset_rad":0.0,"guide_s":null,"last_segment":0,"phase_rad":1.5707963267948966,"radius_m":0.014},{"anchor_angle_offset_rad":0.0,"anchor_s":null,"angular_offsets_rad":[0.0,-1.5707963267948966],"count":2,"first_segment":0,"guide_angle_offset_rad":0.0,"guide_s":null,"last_segment":1,"phase_rad":0.7853981633974483,"radius_m":0.014}]`。该表述只作索引，真实逐腱 RoutePoint、孔位、附件、COM、惯量、自然曲率和连接关系，以 [最终完整候选](https://github.com/wran021004-gif/softrobot-agent/blob/15d4667050351c1cbf84e6ade6f573286d6d8ed0/paper_experiments/paper_results_master_20261113/SOURCE_DATA/T07_M1_A_CANDIDATE.json) 的 `/configuration/robot/structure/data` 为准。

| 保存run / 版本 | 代表候选artifact | 长度 m | E Pa | 实际差异摘要 |
| --- | --- | --- | --- | --- |
| codex-expert-T07-20261113 / 1 | `2b7f1d1bb5c7bda061239f157c2c0e312a2c085c457ac7b746de69c48c3304c5` | [0.1585, 0.109] | [7200000.0, 5400000.0] | 该run首版本；不是跨run因果父项 |
| codex-expert-T07-20261113 / 2 | `0a8368b21bd33a1902f18765b7afbd505b53583812697087e8e225c400a402a3` | [0.1585, 0.109] | [7200000.0, 5400000.0] | 实际孔位/腱路坐标变化，逐字段见CSV |
| codex-expert-T07-20261113 / 3 | `b00003fcb922cdc30e100ec88013615ffe682f16ca97904f924e37ee1eb620ab` | [0.1585, 0.109] | [7200000.0, 5400000.0] | /data/components/0/sections/0/section/kind: ellipse → circle; /data/components/0/sections/0/section/parameters/radius_m: unavailable → 0.008 |
| codex-expert-T07-20261113 / 4 | `f1d6b215df57f0b270725e43054b81e6f03a775beab46d6c54d48864b44785f5` | [0.1595, 0.109] | [7200000.0, 5400000.0] | /data/components/0/length_m: 0.1585 → 0.1595 |
| codex-expert-T07-20261113 / 5 | `ef5eaf36c890d8157a59de97c5231384915767120dcc714badbee6537cbdd58c` | [0.1625, 0.1125] | [7200000.0, 5400000.0] | /data/components/0/length_m: 0.1595 → 0.1625; /data/components/3/length_m: 0.109 → 0.1125 |
| codex-expert-T07-20261113 / 6 | `5b531f7c25e21d2146837681b4d0f95d505720cd2b94fe6b4f986a2cd40ee67e` | [0.1585, 0.109] | [7200000.0, 5400000.0] | /data/components/0/length_m: 0.1625 → 0.1585; /data/components/3/length_m: 0.1125 → 0.109 |

版本及科学ID来自 [冻结CANDIDATE_EVOLUTION](https://github.com/wran021004-gif/softrobot-agent/blob/15d4667050351c1cbf84e6ade6f573286d6d8ed0/paper_experiments/paper_results_master_20261113/CANDIDATE_EVOLUTION.csv)。同一 run 内保存顺序只用于差异导航，未据此补造 `causal_parent`。前驱/已废弃研究的实际生成请求和结构差异另保留在决策 CSV；不把这些前驱候选的结果替换为 FULL 最终结果。

**控制与数学。** 每种结构重新进行Native Response张力系数搜索，A/B/C使用nonlinear_task_capability，M5使用direct_control。历史与当前输入可作种子；C由当前A序列重新优化后才独立通过。共同硬件要求的是跨四工况同结构，不是同一开环输入。不同预算、网格及初值下最佳J比较属于M2-style；无最优值结构导数。

| 实际请求方法 | 控制版本 | 返回状态 | 去重保存请求数 |
| --- | --- | --- | --- |
| equilibrium / GVS bounded-tension SLSQP construction (check applicability) | not_applicable | computed | 3 |
| mujoco_direct_control_v1 | local_control_search_v2 | computed | 2 |
| mujoco_nonlinear_task_capability_v1 | local_control_search_v2 | computed | 19 |

| 节点 / run | Observation | Hypothesis | Decision / Modification | 保存结果 / 后续验证 |
| --- | --- | --- | --- | --- |
| `T07-060-test-isotropic-root-mechanism` / `codex-expert-T07-20261113` | 相同椭圆根段结构B通过，A约10.6%超限、C近失效。 | 8 mm圆根段可能改变质量、刚度与平面耦合。 | 只在当前14.1 mm路由/158.5,109 mm长度背景下改根段截面；截面同时改变多个物理机制。 | A的J降至0.008747859181325923；不能解释为单独刚度导数。 |
| `T07-063-add-one-mm-root-reach-margin` / `codex-expert-T07-20261113` | 圆根段后A仍小幅超限。 | 根段再长1 mm可能增加可达余量。 | 158.5 -> 159.5 mm；重新优化A。 | J=0.011385196907741868，全控制网格细化后0.01098378058326177；未改善至可行。 |
| `T07-070-test-distributed-root-tail-reach-margin` / `codex-expert-T07-20261113` | 单根段增长与全网格细化仍未通过A。 | 分布式增加两段长度可能缓解任务冲突。 | 测试162.5/112.5 mm共同结构。 | T07-072 J=0.04396835416276468；增长度方案更差。 |
| `T07-074-test-original-radius-boundary-on-best-root` / `codex-expert-T07-20261113` | 增长度方案A的J增至0.04396835416276468。 | 回到最佳长度并减小剩余路由半径。 | 回退158.5/109 mm，同时14.1 -> 14 mm；不是单参数干预。 | T07-076 J=-0.010000000000000009，后续A/B/M5完整通过。 |
| `T07-106-native-current-C-from-A-basin` / `codex-expert-T07-20261113` | 共同硬件A/B/M5通过，C由历史盆地仍有J=0.0411246204910618。 | 当前A控制初值可改变C搜索盆地。 | 同硬件将A张力序列作为初值，再独立优化C。 | J=-0.010005715515327807；最终同一硬件4/4原工况通过。 |

这些链条是对原 rationale 和相邻请求的编辑性整理。`mathematical_method`、`mathematical_result`、`physical_validation_result` 与 `related_evidence_nodes` 保留计算及验收的边界；失败分支不据此推断全局不可行。

| 最终工况 / 角色 | 候选artifact | candidate_id | 原记录通过 | 原始指标（m、s、rad、N，比例无量纲） |
| --- | --- | --- | --- | --- |
| M1_A / required | `5b531f7c25e21d2146837681b4d0f95d505720cd2b94fe6b4f986a2cd40ee67e` | `core-69da95e8943a1aea4d87e3944d375c0ef9dfea48ec19f294496061379069d243` | True | `{"holding_max_error_m":0.00989999999999998}` |
| M1_B / required | `6334547068f3b0abee1266ddfe91c5f2fb3d5da97db0d9ae0183d84516a28379` | `core-0a64525c75517042ef3cb0f0940de5404f582e2b4a57c36cbb404856f678af2e` | True | `{"holding_max_error_m":0.009895482501791793}` |
| M1_C / required | `93956f49a3d73900bad1af93665281b3f2043045951cb0ad5c3789b6ac220380` | `core-f18d04addc286b943e6c8d7f5c8f3c73070dfdce6c30ecc60564ee1aebdeb630` | True | `{"holding_max_error_m":0.009897784609851577}` |
| M5 / required | `6e00204c2921d63ce5220daaceaf3d528d26b59232b4421893493101bde76c53` | `core-6bf58a8acaf5422ec92a47cb44928c87cd327fd39a7ae6e8a572356009093a9f` | True | `{"max_position_error":0.007919999999999996,"max_tool_axis_angle_error":0.05183616091804452}` |

最终值引用 [冻结 TASK_CASE_RESULTS](https://github.com/wran021004-gif/softrobot-agent/blob/15d4667050351c1cbf84e6ade6f573286d6d8ed0/paper_experiments/paper_results_master_20261113/TASK_CASE_RESULTS.csv) 与 [T07 candidate/result/XML绑定](https://github.com/wran021004-gif/softrobot-agent/blob/15d4667050351c1cbf84e6ade6f573286d6d8ed0/paper_experiments/paper_results_master_20261113/SOURCE_DATA/MODEL_BINDINGS.json)；完整约束、原 result artifact 和 raw reference 保留在原表及决策 CSV 的 `FULL-final-*` 行。该表是原保存结果的审计视图，不增加执行或成本。

**M0–M3。** M0=`not_executed`；M1=`partial_or_analogous`；M2=`partial_or_analogous`；M3=`not_executed`。逐项定义、实际扰动、控制处理、证据 ID 和判定理由见配套审计 CSV。

## T08 被动渐进刚度

两段各100 mm、各7 MPa、两腱、零执行器。实际结构设计变化是两根固定放绳偏置同步1.5→1.8 mm，绝对放绳长度0.2155→0.2158 m；18 mm路由及材料/截面保持。

**结构及身份。** 最终执行结构为 2 段、2 腱、0 个独立执行器。本轮首个保存候选 artifact=`e204a256575b9c22c8abc38c870fb0a1d6cdf80c895d2f1895eb404632737ff6`，candidate_id=`core-e85cb55c2d4898fe2b5b22e020e102c38aafc65687214492c74fc4384edaead5`；其参数取自 [冻结首候选](https://github.com/wran021004-gif/softrobot-agent/blob/15d4667050351c1cbf84e6ade6f573286d6d8ed0/paper_experiments/paper_results_master_20261113/SOURCE_DATA/CANDIDATES/T08/e204a256575b9c22c8abc38c870fb0a1d6cdf80c895d2f1895eb404632737ff6.json)。最终工况候选身份见下表；不同工况的候选 ID 可不同，共同硬件须按结构字段比较。

| 段 | 长度 m | 材料参数（SI） | 截面站点 |
| --- | --- | --- | --- |
| segment_0 | 0.1 | {"bending_ei_nm2":null,"bending_viscosity_nm2_s":[0.0004,0.0004],"density_kg_m3":1100.0,"line_density_kg_m":null,"mode":"material","young_pa":7000000.0} | s=0.0:circle {"radius_m":0.006} angle=0.0 |
| segment_1 | 0.1 | {"bending_ei_nm2":null,"bending_viscosity_nm2_s":[0.0004,0.0004],"density_kg_m3":1100.0,"line_density_kg_m":null,"mode":"material","young_pa":7000000.0} | s=0.0:circle {"radius_m":0.006} angle=0.0 |

腱路请求：`[{"anchor_angle_offset_rad":0.0,"anchor_s":1.0,"angular_offsets_rad":[],"count":2,"first_segment":0,"guide_angle_offset_rad":0.0,"guide_s":[0.5],"last_segment":1,"phase_rad":1.5707963267948966,"radius_m":0.018}]`。该表述只作索引，真实逐腱 RoutePoint、孔位、附件、COM、惯量、自然曲率和连接关系，以 [最终完整候选](https://github.com/wran021004-gif/softrobot-agent/blob/15d4667050351c1cbf84e6ade6f573286d6d8ed0/paper_experiments/paper_results_master_20261113/SOURCE_DATA/T08_both_directions_CANDIDATE.json) 的 `/configuration/robot/structure/data` 为准。
固定放绳长度 m：`{"tendon_0":0.21580000000000002,"tendon_1":0.21580000000000002}`。

| 保存run / 版本 | 代表候选artifact | 长度 m | E Pa | 实际差异摘要 |
| --- | --- | --- | --- | --- |
| codex-surrogate-T08-20261112 / 1 | `e204a256575b9c22c8abc38c870fb0a1d6cdf80c895d2f1895eb404632737ff6` | [0.1, 0.1] | [7000000.0, 7000000.0] | 该run首版本；不是跨run因果父项 |
| codex-surrogate-T08-20261112 / 2 | `bca367320313f088af99417da17cb55e04362532109e0be80587c7e65b00e8bd` | [0.1, 0.1] | [7000000.0, 7000000.0] | /data/fixed_payout_lengths_m/tendon_0: 0.21550000000000002 → 0.21580000000000002; /data/fixed_payout_lengths_m/tendon_1: 0.21550000000000002 → 0.21580000000000002 |

版本及科学ID来自 [冻结CANDIDATE_EVOLUTION](https://github.com/wran021004-gif/softrobot-agent/blob/15d4667050351c1cbf84e6ade6f573286d6d8ed0/paper_experiments/paper_results_master_20261113/CANDIDATE_EVOLUTION.csv)。同一 run 内保存顺序只用于差异导航，未据此补造 `causal_parent`。前驱/已废弃研究的实际生成请求和结构差异另保留在决策 CSV；不把这些前驱候选的结果替换为 FULL 最终结果。

**控制与数学。** 没有主动控制优化，也没有research.math顶层调用。原生被动配对执行记录低/高载位移、刚度比、松弛到张紧及去腱限位机制对照，另保存独立复核、半步长/初态扰动。有限尺度放绳偏置比较支持招募机制效应，不构成机制指标导数。原分类为task.passive_response/development_valid，数学/物理通过不升级为主动SELECT成功。

本任务未找到 `research.math` 顶层调用；生成、控制器执行、被动 evaluator 或原生初态工具中的计算按各自原证据记录，未据工具目录补填调用。

| 节点 / run | Observation | Hypothesis | Decision / Modification | 保存结果 / 后续验证 |
| --- | --- | --- | --- | --- |
| `T08-006-generate` / `codex-surrogate-T08-20261112` | 1.5 mm放绳偏置结构刚度比约1.367，低于1.5。 | 偏置改变高载腱招募区间。 | 同结构两根腱固定放绳偏置同时1.5 -> 1.8 mm。 | 双方向刚度比1.63145475；低载7.9281 mm、高载22.5085 mm；有限尺度机制效应。 |
| `T08-009-independent-confirmation` / `codex-surrogate-T08-20261112` | 主指标通过仍需成对机制与数值复核。 | 去腱限位配对、半步长和初态扰动可检查响应来源及稳定性。 | 读取并保留独立双方向机制/复核结果。 | 保留task.passive_response/development_valid分类，不改写为正式主动任务验收。 |

这些链条是对原 rationale 和相邻请求的编辑性整理。`mathematical_method`、`mathematical_result`、`physical_validation_result` 与 `related_evidence_nodes` 保留计算及验收的边界；失败分支不据此推断全局不可行。

| 最终工况 / 角色 | 候选artifact | candidate_id | 原记录通过 | 原始指标（m、s、rad、N，比例无量纲） |
| --- | --- | --- | --- | --- |
| plus_x / required | `a0438dc77c16e221b07447f2a75d2f3d1739d1741dbd14840ff28a54f1b647cc` | `core-658a3063ed8430c18810c1b723e06584d1807d1f92234645a60db8d3230723d1` | True | `{"stiffness_ratio":1.6314547492588845,"low_minimum":0.007928066911447334,"high_maximum":0.022508490353744023}` |
| minus_x / required | `a0438dc77c16e221b07447f2a75d2f3d1739d1741dbd14840ff28a54f1b647cc` | `core-658a3063ed8430c18810c1b723e06584d1807d1f92234645a60db8d3230723d1` | True | `{"stiffness_ratio":1.631454749259155,"low_minimum":0.007928066911447379,"high_maximum":0.02250849035374532}` |

最终值引用 [冻结 TASK_CASE_RESULTS](https://github.com/wran021004-gif/softrobot-agent/blob/15d4667050351c1cbf84e6ade6f573286d6d8ed0/paper_experiments/paper_results_master_20261113/TASK_CASE_RESULTS.csv) 与 [T08 candidate/result/XML绑定](https://github.com/wran021004-gif/softrobot-agent/blob/15d4667050351c1cbf84e6ade6f573286d6d8ed0/paper_experiments/paper_results_master_20261113/SOURCE_DATA/MODEL_BINDINGS.json)；完整约束、原 result artifact 和 raw reference 保留在原表及决策 CSV 的 `FULL-final-*` 行。该表是原保存结果的审计视图，不增加执行或成本。

**M0–M3。** M0=`partial_or_analogous`；M1=`not_applicable`；M2=`not_applicable`；M3=`not_applicable`。逐项定义、实际扰动、控制处理、证据 ID 和判定理由见配套审计 CSV。

## T09 复杂导向件弹簧按钮接触

真实结构为149/120.5 mm、各8 MPa、四腱四执行器，保留20个孔/支撑总成的质量、COM和惯量。前run与修复run的名义柔性段参数相同，关键修复是实体安装/附件接触策略。不能把删除真实附件当改良，也不能把模型修复写成段长度或材料优化。

**结构及身份。** 最终执行结构为 2 段、4 腱、4 个独立执行器。本轮首个保存候选 artifact=`55d4282a0428f79ccf0811c49d5a3247a529195927c39c8dbc8e663c4d3de3a3`，candidate_id=`core-f020809c71d4972fc5b699d16f360772c1872dcc362ee66e0aabf36f41c2a53f`；其参数取自 [冻结首候选](https://github.com/wran021004-gif/softrobot-agent/blob/15d4667050351c1cbf84e6ade6f573286d6d8ed0/paper_experiments/paper_results_master_20261113/SOURCE_DATA/CANDIDATES/T09/55d4282a0428f79ccf0811c49d5a3247a529195927c39c8dbc8e663c4d3de3a3.json)。最终工况候选身份见下表；不同工况的候选 ID 可不同，共同硬件须按结构字段比较。

| 段 | 长度 m | 材料参数（SI） | 截面站点 |
| --- | --- | --- | --- |
| segment_0 | 0.149 | {"bending_ei_nm2":null,"bending_viscosity_nm2_s":[0.0005,0.0007],"density_kg_m3":1100.0,"line_density_kg_m":null,"mode":"material","young_pa":8000000.0} | s=0.0:ellipse {"semi_y_m":0.011685,"semi_z_m":0.01064} angle=0.35 |
| segment_1 | 0.1205 | {"bending_ei_nm2":null,"bending_viscosity_nm2_s":[0.0003,0.0004],"density_kg_m3":1050.0,"line_density_kg_m":null,"mode":"material","young_pa":8000000.0} | s=0.0:rectangle {"height_z_m":0.015674999999999998,"width_y_m":0.017689} angle=-0.25; s=1.0:rectangle {"height_z_m":0.014107499999999997,"width_y_m":0.015162000000000002} angle=0.15000000000000002 |

腱路请求：`[{"anchor_angle_offset_rad":0.0,"anchor_s":null,"angular_offsets_rad":[0.0,-0.2617993877991493],"count":2,"first_segment":0,"guide_angle_offset_rad":0.0,"guide_s":null,"last_segment":0,"phase_rad":1.5707963267948966,"radius_m":0.021},{"anchor_angle_offset_rad":0.0,"anchor_s":null,"angular_offsets_rad":[0.0,-1.5707963267948966],"count":2,"first_segment":0,"guide_angle_offset_rad":0.0,"guide_s":null,"last_segment":1,"phase_rad":0.6981317007977318,"radius_m":0.021}]`。该表述只作索引，真实逐腱 RoutePoint、孔位、附件、COM、惯量、自然曲率和连接关系，以 [最终完整候选](https://github.com/wran021004-gif/softrobot-agent/blob/15d4667050351c1cbf84e6ade6f573286d6d8ed0/paper_experiments/paper_results_master_20261113/SOURCE_DATA/T09_default_CANDIDATE.json) 的 `/configuration/robot/structure/data` 为准。

| 保存run / 版本 | 代表候选artifact | 长度 m | E Pa | 实际差异摘要 |
| --- | --- | --- | --- | --- |
| codex-expert-T09-20261113 / 1 | `b965d27126108e39e4266fc0fcee3132f6ce9be724868e27a8a95b96f9bca16f` | [0.149, 0.1205] | [8000000.0, 8000000.0] | 该run首版本；不是跨run因果父项 |
| codex-expert-T09-20261113-core027 / 1 | `55d4282a0428f79ccf0811c49d5a3247a529195927c39c8dbc8e663c4d3de3a3` | [0.149, 0.1205] | [8000000.0, 8000000.0] | 该run首版本；不是跨run因果父项 |

版本及科学ID来自 [冻结CANDIDATE_EVOLUTION](https://github.com/wran021004-gif/softrobot-agent/blob/15d4667050351c1cbf84e6ade6f573286d6d8ed0/paper_experiments/paper_results_master_20261113/CANDIDATE_EVOLUTION.csv)。同一 run 内保存顺序只用于差异导航，未据此补造 `causal_parent`。前驱/已废弃研究的实际生成请求和结构差异另保留在决策 CSV；不把这些前驱候选的结果替换为 FULL 最终结果。

**控制与数学。** 早期接口不支持完整复杂导向件而停止。后续完整附件模型出现不正确的附件碰撞，修复接触策略后，用保存历史中点张力命令在200个控制间隔完整开环重放。最终流程没有本轮新的控制优化或结构敏感性调用；声明的GVS控制器配置不表示最终重放执行了NMPC。完整接触验收覆盖按压、持续深度/力联合保持和释放。

本任务未找到 `research.math` 顶层调用；生成、控制器执行、被动 evaluator 或原生初态工具中的计算按各自原证据记录，未据工具目录补填调用。

| 节点 / run | Observation | Hypothesis | Decision / Modification | 保存结果 / 后续验证 |
| --- | --- | --- | --- | --- |
| `T09-010-generate-history-informed-baseline` / `codex-expert-T09-20261113` | 原接口缺少真实导向件与接触支持。 | 必须恢复历史完整实体、质量、COM与惯量。 | 通过新注册接口构造完整硬件。 | 早期附件接触策略又引入错误碰撞；不是实体质量应被删除。 |
| `T09-210-generate-collision-faithful-hardware` / `codex-expert-T09-20261113-core027` | 完整导向孔/支架模型在错误接触策略下出现附件碰撞。 | 应修复附件碰撞策略而保留全部真实部件。 | 20个真实孔/支撑总成及原质量/惯量保留；接触策略修复。 | 后续用保存历史中点命令独立完整重放通过；没有本轮新的控制优化或结构梯度。 |
| `T09-213-replay-complete-collision-faithful-task` / `codex-expert-T09-20261113-core027` | 修复模型与保存命令仍需完整按压、保持、释放验收。 | 真实附件模型可完成原按钮接触任务。 | 保持原任务、完整质量惯量及200步保存命令。 | 联合深度/力保持0.5 s；最大误差0.052753 mm、0.0024651 N；释放约束另见最终完整结果。 |

这些链条是对原 rationale 和相邻请求的编辑性整理。`mathematical_method`、`mathematical_result`、`physical_validation_result` 与 `related_evidence_nodes` 保留计算及验收的边界；失败分支不据此推断全局不可行。

| 最终工况 / 角色 | 候选artifact | candidate_id | 原记录通过 | 原始指标（m、s、rad、N，比例无量纲） |
| --- | --- | --- | --- | --- |
| default / required | `52fbff225dd926fb7d2bc7f3bba7d89a18a90047adaece3471f750970141caf9` | `core-a4d93be1bab9fa20b46dd84ef323eb3fa2109e1ccb36f479b1d79656b4a6db4f` | True | `{"hold_valid_continuous_s":0.4999999999999559,"max_hold_depth_error_m":5.2752700179421914e-05,"max_hold_contact_force_error_n":0.002465057424524908}` |

最终值引用 [冻结 TASK_CASE_RESULTS](https://github.com/wran021004-gif/softrobot-agent/blob/15d4667050351c1cbf84e6ade6f573286d6d8ed0/paper_experiments/paper_results_master_20261113/TASK_CASE_RESULTS.csv) 与 [T09 candidate/result/XML绑定](https://github.com/wran021004-gif/softrobot-agent/blob/15d4667050351c1cbf84e6ade6f573286d6d8ed0/paper_experiments/paper_results_master_20261113/SOURCE_DATA/MODEL_BINDINGS.json)；完整约束、原 result artifact 和 raw reference 保留在原表及决策 CSV 的 `FULL-final-*` 行。该表是原保存结果的审计视图，不增加执行或成本。

**M0–M3。** M0=`not_executed`；M1=`not_executed`；M2=`not_executed`；M3=`not_executed`。逐项定义、实际扰动、控制处理、证据 ID 和判定理由见配套审计 CSV。

## T10 外部冲击主动恢复

始终遵守原任务指定的M2硬件：160/110 mm、7.2/5.4 MPa、六腱六执行器。此处“原M2硬件”是历史任务结构名，不等于T02最终12 MPa结构，更不等于数学M2层。后续变化是控制/数值接口和共同配方，没有结构扰动。

**结构及身份。** 最终执行结构为 2 段、6 腱、6 个独立执行器。本轮首个保存候选 artifact=`030ec52c054eb0e92eec5dd0192785fa78beb58180f4a9e131d754fd61d54824`，candidate_id=`core-25bab8da1dc1ef9851a71d681d886683ea1dc4e1fece41ad677fc161ed2f0f25`；其参数取自 [冻结首候选](https://github.com/wran021004-gif/softrobot-agent/blob/15d4667050351c1cbf84e6ade6f573286d6d8ed0/paper_experiments/paper_results_master_20261113/SOURCE_DATA/CANDIDATES/T10/030ec52c054eb0e92eec5dd0192785fa78beb58180f4a9e131d754fd61d54824.json)。最终工况候选身份见下表；不同工况的候选 ID 可不同，共同硬件须按结构字段比较。

| 段 | 长度 m | 材料参数（SI） | 截面站点 |
| --- | --- | --- | --- |
| segment_0 | 0.16 | {"bending_ei_nm2":null,"bending_viscosity_nm2_s":[0.0005,0.0007],"density_kg_m3":1100.0,"line_density_kg_m":null,"mode":"material","young_pa":7200000.0} | s=0.0:ellipse {"semi_y_m":0.0095,"semi_z_m":0.0076} angle=0.35 |
| segment_1 | 0.11 | {"bending_ei_nm2":null,"bending_viscosity_nm2_s":[0.0003,0.0004],"density_kg_m3":1050.0,"line_density_kg_m":null,"mode":"material","young_pa":5400000.0} | s=0.0:rectangle {"height_z_m":0.0095,"width_y_m":0.0133} angle=-0.25; s=1.0:rectangle {"height_z_m":0.008549999999999999,"width_y_m":0.0114} angle=0.15000000000000002 |

腱路请求：`[{"anchor_angle_offset_rad":0.0,"anchor_s":null,"angular_offsets_rad":[],"count":3,"first_segment":0,"guide_angle_offset_rad":0.0,"guide_s":null,"last_segment":0,"phase_rad":0.0,"radius_m":null},{"anchor_angle_offset_rad":0.0,"anchor_s":null,"angular_offsets_rad":[],"count":3,"first_segment":0,"guide_angle_offset_rad":0.0,"guide_s":null,"last_segment":1,"phase_rad":1.0471975511965976,"radius_m":null}]`。该表述只作索引，真实逐腱 RoutePoint、孔位、附件、COM、惯量、自然曲率和连接关系，以 [最终完整候选](https://github.com/wran021004-gif/softrobot-agent/blob/15d4667050351c1cbf84e6ade6f573286d6d8ed0/paper_experiments/paper_results_master_20261113/SOURCE_DATA/T10_positive_y_CANDIDATE.json) 的 `/configuration/robot/structure/data` 为准。

| 保存run / 版本 | 代表候选artifact | 长度 m | E Pa | 实际差异摘要 |
| --- | --- | --- | --- | --- |
| codex-expert-T10-20261113 / 1 | `6b19e5db0a1e4545f9322422e2e50c59905930b68aab6dfb30211483588748df` | [0.16, 0.11] | [7200000.0, 5400000.0] | 该run首版本；不是跨run因果父项 |
| codex-expert-T10-20261113-core027 / 1 | `85c3f4fe3d971adb909f0c156ffa8b3659d15b55c2e078acdaeb56d7761a39bd` | [0.16, 0.11] | [7200000.0, 5400000.0] | 该run首版本；不是跨run因果父项 |
| codex-expert-T10-20261113-nativefb / 1 | `0a730deb7f71567e7e68821597d055f5681923d5d1f755e6f3c3eda39a3835cd` | [0.16, 0.11] | [7200000.0, 5400000.0] | 该run首版本；不是跨run因果父项 |
| codex-expert-T10-20261113-nativefb-final / 1 | `4f086608d790b4bb09fc514beb0088c6b450dac940d273a2eef6d2711e7ddd49` | [0.16, 0.11] | [7200000.0, 5400000.0] | 该run首版本；不是跨run因果父项 |
| codex-expert-T10-20261113-verified-common / 1 | `030ec52c054eb0e92eec5dd0192785fa78beb58180f4a9e131d754fd61d54824` | [0.16, 0.11] | [7200000.0, 5400000.0] | 该run首版本；不是跨run因果父项 |

版本及科学ID来自 [冻结CANDIDATE_EVOLUTION](https://github.com/wran021004-gif/softrobot-agent/blob/15d4667050351c1cbf84e6ade6f573286d6d8ed0/paper_experiments/paper_results_master_20261113/CANDIDATE_EVOLUTION.csv)。同一 run 内保存顺序只用于差异导航，未据此补造 `causal_parent`。前驱/已废弃研究的实际生成请求和结构差异另保留在决策 CSV；不把这些前驱候选的结果替换为 FULL 最终结果。

**控制与数学。** 保存了早期GVS/NMPC盲反馈执行及失败；原生Native Direct启动/制动代理虽改善名义结果，完整原M7预保持与密集执行器约束仍需重放，不能把开环到达称为恢复。最终转family.native_feedback_control@1.0.0：每次执行以least_squares构造原生参考，围绕状态q做中心全力切线，矩阵指数精确保持输入离散化，solve_discrete_are构造LQR，随后逐次根据实测q/v反馈与闭式有界张力分配。切线对状态求导，不是对结构求导。早期RUN_04虽有三required通过，positive_y的有效holding_tip_speed_weight/terminal_tip_speed_weight为0.1/0.1，其余为0.5/0.0，共同性证书选择被拒；最终RUN_06明确统一0.5/0.0并保留三required与两frozen control角色。

| 实际请求方法 | 控制版本 | 返回状态 | 去重保存请求数 |
| --- | --- | --- | --- |
| mujoco_direct_control_v1 | local_control_search_v2 | computed | 1 |

| 节点 / run | Observation | Hypothesis | Decision / Modification | 保存结果 / 后续验证 |
| --- | --- | --- | --- | --- |
| `T10-017-native-direct-startup-braking` / `codex-expert-T10-20261113` | 原GVS/NMPC及启动路线存在预保持、腱速/行程冲突。 | 先以原生开环启动/制动诊断真实约束。 | Native Direct仅作开环诊断，随后完整原协议重放。 | 不能由名义到达宣称冲击恢复；后续转原生状态反馈。 |
| `T10-210-generate-original-M2-native-feedback` / `codex-expert-T10-20261113-verified-common` | 固定原M2硬件需要盲于外部脉冲的共同反馈配方。 | 原生平衡参考、全状态切线与离散LQR可产生恢复控制。 | 每次执行重新构造参考和增益；固定同一配方，后续默认值/证书修复另立run。 | 早期共同性选择失败保留；最终RUN_06三required通过，两frozen control失败。 |
| `T10-222-execute-native-feedback-positive_y` / `codex-expert-T10-20261113-verified-common` | 三required与两control必须保持共同结构及共同有效控制配方。 | 原生测量状态反馈应对未知时刻±Y脉冲恢复。 | 环境注入力与冻结；控制器仅接收普通状态、目标和参考时钟。 | 最终required3/3，control0/2；最大保持误差4.1314 mm；只有单硬件闭环性能，不是M3敏感性。 |

这些链条是对原 rationale 和相邻请求的编辑性整理。`mathematical_method`、`mathematical_result`、`physical_validation_result` 与 `related_evidence_nodes` 保留计算及验收的边界；失败分支不据此推断全局不可行。

| 最终工况 / 角色 | 候选artifact | candidate_id | 原记录通过 | 原始指标（m、s、rad、N，比例无量纲） |
| --- | --- | --- | --- | --- |
| positive_y / required | `fff9adb4826ccaf640b582071bd1938c82971daf4dcf59f78d8332406118c9f8` | `core-b2a59681ed9e12b5ec977fd47d2f53ad9e1fb0fa5daf1e34c786dac0cd9a7da1` | True | `{"final_hold_max_error_m":0.00403181200271061,"final_hold_max_speed_m_s":0.005430562171212072,"recovery_time_after_pulse_s":0}` |
| negative_y / required | `256d46f0737110c3876098bf34e0f39c207709f93ffe8a9220ddf93994d14b1a` | `core-3947ef5037a01de484d56dd091a403a1fc06f7f7d8f10671cb91efed40ba9691` | True | `{"final_hold_max_error_m":0.004131381938040607,"final_hold_max_speed_m_s":0.005565169055264074,"recovery_time_after_pulse_s":0.0014999999999946168}` |
| no_impulse / required | `ef31b5cdafd9d5e0295fa25a60c46dfbe2e6342eaf65815c6f91148e51e92496` | `core-a7f71259049ab00070b887386f9e855f9143257cca0e3dc704e9e5927d4bb473` | True | `{"final_hold_max_error_m":0.004028091382257626,"final_hold_max_speed_m_s":0.005416475657616396,"recovery_time_after_pulse_s":0}` |
| positive_y_frozen / control | `8024a04a6da95786206444f818cad64ca94cbb249de1c5dc27d6a607d9b4b366` | `core-d4f1ef81fc8906a39d2431e65e54d9e0a46ad2dfb5cab19ea5951a11fa77fbb3` | False | `{"final_hold_max_error_m":0.007127696966858097,"final_hold_max_speed_m_s":0.02158253799868025,"recovery_time_after_pulse_s":0.29449999999996235}` |
| negative_y_frozen / control | `67826ba93009284a13e1e5f521ffea858cf5db8fddee2f6dc00644b16d1b4ddf` | `core-700c5dee300932b4769cd8b1be9b7ef795e86f1e47612a5d41d67ff64d44a4ce` | False | `{"final_hold_max_error_m":0.0076200030322926045,"final_hold_max_speed_m_s":0.025357390029626073,"recovery_time_after_pulse_s":null}` |

最终值引用 [冻结 TASK_CASE_RESULTS](https://github.com/wran021004-gif/softrobot-agent/blob/15d4667050351c1cbf84e6ade6f573286d6d8ed0/paper_experiments/paper_results_master_20261113/TASK_CASE_RESULTS.csv) 与 [T10 candidate/result/XML绑定](https://github.com/wran021004-gif/softrobot-agent/blob/15d4667050351c1cbf84e6ade6f573286d6d8ed0/paper_experiments/paper_results_master_20261113/SOURCE_DATA/MODEL_BINDINGS.json)；完整约束、原 result artifact 和 raw reference 保留在原表及决策 CSV 的 `FULL-final-*` 行。该表是原保存结果的审计视图，不增加执行或成本。

**M0–M3。** M0=`not_executed`；M1=`not_executed`；M2=`not_executed`；M3=`not_executed`。逐项定义、实际扰动、控制处理、证据 ID 和判定理由见配套审计 CSV。

## PHS-2D 九段四腱主案例

**版本和结构。** 主案例为第三轮v2的 `P3_real9_E80_full8`，candidate_id=`core-3e18c3a90bbeb743615036a80043041629763771fe64d4e1563b0b414e36e233`，candidate artifact=`023bea360a83f67f12c7aee8346e9e62f2cc09e48a979dc2689c5881460932e5`，assembly artifact=`0bde4fd77ac561a441ab9e5faf65d65760ca2b5bdd2caa41ff8307e22ff03d3d`。原生被动XML的SHA-256为 `75de64d10a2e2eaa605e3d59d16eec1bea6a8081d9c537c8deb2f6a09b47c77a`，实际XML actuator子项数为0。生成候选/编译中间结构仍有4个声明通道；它们在固定被动绳模型中不是4个实际电机，不能按中间physics列表误计执行器。

第三轮首个实际生成候选为 `P1_diagonal_084`：一段0.28 m、E=2 MPa、6×6 mm矩形、24单元、两根Base-to-payload斜拉腱；candidate artifact=`c851be5888cacfd4321786e44e117dc5912ec91d08776ea8af72fd714ad9fdd6`。它不是FULL七段研究的F0。完整46个实际保存候选与47次生成尝试的区别保留：一个失败生成不补造候选。

| 最终字段 | 保存值 | 证据 |
| --- | --- | --- |
| 柔性骨架 | 9 × 0.031111111111111114 m；总0.28 m；每段8单元，72单元、144弯曲坐标 | [generation / physics.discretization](https://github.com/wran021004-gif/softrobot-agent/blob/9d6d160e050c836b87d0563a497fc0ec1c3761a8/evidence/phs2d_round3_20261028/solution/design.json) |
| 材料/截面 | 各段圆半径0.003 m，E=8000000 Pa；第一段1100，其余1050 kg/m³；物理弯曲黏性两个方向均0.00006 N·m²·s | 同一design的实际components；保留零自然曲率 |
| 附件/长度 | 8块2 g导向板、8个3 g连接件、10 g偏心payload；8个14 mm间隔及14 mm Tip偏移；无变形Base–Tip=0.406 m | 柔性长度不含刚性间隔；保留完整COM/惯量 |
| 总物理质量 kg | 0.058356636458548904 | /total_physical_mass_kg |
| 实际腱路 | 4根从同一fixed_base，经8板的真实具名孔，锚定payload内部；Base y=±0.007 m,z=±0.025 m；z力臂随剩余距离递减 | 逐点坐标在design，不从图估算；无额外world锚或Tip固定 |
| 固定放绳长度 m | `{"tendon_0":0.39274245978073885,"tendon_1":0.39274245978073885,"tendon_2":0.39274245978073885,"tendon_3":0.39274245978073885}` | 四根全部工况一致；偏移均0；pretension_n声明不施加主动初始化力 |

**研究路线与数学影响。** 局部Jacobian/行空间、秩、零空间和单侧QP响应确实参与选择斜拉力臂、渐变路线及导向拓扑。局部机制优势在有限载荷下会被弦长缩短、绳松弛、几何穿透及未停稳否定；这些失败使研究放弃仅靠局部完美匹配或仅增黏性的解释。

| 阶段 / 实际候选 | Observation → Hypothesis | 数学/决策/修改 | 保存物理或适用性后果 |
| --- | --- | --- | --- |
| v1 / P1_diagonal_084及b168/b200系列 | 局部Tip行可约束，但有限弯曲造成弦长缩短/松弛 | 实际Jacobian、局部单侧QP、非线性硬绳静力；比较Base斜角/材料/截面 | P1_b200_r8_h85在±0.1 N下Tip位移虽小，4 s原标准仍invalid；半步长也invalid，不能计成功 |
| v1 / P2_dense22_z20/z40/z60 | 局部完美约束不足以保持有限变形 | 密集渐变偏置站点改善约束传递；固定原材料黏性继续检验 | z40动态Tip约0.00568–1.02369 mm，但6工况仍invalid；位移小不替代残差/停稳有效性 |
| v1→v2 / P2_dense22_visc60 | 有限载荷位移改善而原时窗未停稳 | 新v2材料域允许物理黏性0.00003–0.0004，实际试0.00006；扣除v1已用资源 | 名义初次6工况invalid，半步长6工况通过；仍非最终实体安装结构 |
| v2 / P2_match_0…9 | 实际Tip行空间匹配可作局部路线指标 | minimize_scalar bounded只搜索terminal end factor，10次几何评价；optimizer_success=false | 有限预算匹配与端力臂敏感性被保留；不作为有限载荷成功或全局最优证明 |
| v2 / P2_real_guides_3/4/5 | 偏置站点不等于真实安装；有限跨度仍会松弛 | 只经过有质量的真实板孔；部分三段形状穿透；继续改变实体导向拓扑 | 停止把无实体柔段悬空站点方案当最终安装答案 |
| v2 / P2_real_guides_7_circle、9_circle | 更短无支撑跨度可能改善有限弦长效应 | 7段与9段成对比较，真实孔/连接间隔随段数变化 | 段数、刚性附件质量、间隔、路由同时变化，不能把改善独立归因于段数 |
| v2 / P3_real9_E32/E36/E40/gradient/E60/E80/gradient60 | 九段实际路由建立后，仍须保留受力点≥10 mm并抑制Tip | 比较均匀与分布E；3.2/3.6/4 MPa及梯度方案保留失败；6/8 MPa静力筛选通过 | 选择统一8 MPa；36单元筛选只作筛选，不替代72单元最终数学/动态验证 |
| v2 / P3_real9_E80_full8 | 72单元Windows原生XML构造栈溢出 | 旧请求output_unavailable封存；独立诊断后新版本32 MiB编译线程；不改XML/方程 | 未知内部构造成本不补估；新请求完成几何、数学和物理验证 |
| 同一full8 / 六搜索+四留出 | 数学资格仍须独立软约束动态验收 | 统一固定长度，4 s时域、0.5 s加载、±0.1 N；s=.4/.6首次留出 | 首次10/10通过即停止设计搜索；随后独立进程、半步长及初态扰动复核 |
| 同一full8 / 设计梯度 | 设计已固定，须解释正则分支的材料响应 | KKT隐式微分含受载/无载基准；六搜索分支重新求平衡FD核查 | 梯度在E80_full8生成和初次搜索动态后记录；未据此修改最终结构，不声称梯度造成最终性能改进 |

以上逐候选原假设、变量、线性预测、非线性观察、后续假设与动态结果，分别绑定 [experiment_journal](https://github.com/wran021004-gif/softrobot-agent/blob/9d6d160e050c836b87d0563a497fc0ec1c3761a8/evidence/phs2d_round3_20261028/experiment_journal.json)、[v1](https://github.com/wran021004-gif/softrobot-agent/blob/9d6d160e050c836b87d0563a497fc0ec1c3761a8/evidence/phs2d_round3_20261028/study_v1.json) 和 [v2](https://github.com/wran021004-gif/softrobot-agent/blob/9d6d160e050c836b87d0563a497fc0ec1c3761a8/evidence/phs2d_round3_20261028/study_v2.json)；决策CSV中PHS-v1/v2-design-*、analysis-*、dynamic-set-*行附实际artifact与call请求索引。

**数学工具的真实使用与边界。** `passive_modal_target_v1` 输出实际J_tip/J_point/J_length、约束Lagrangian Hessian、秩、正乘子集合与零空间，分开报告A运动学存在性、B单侧活跃锥、C真实材料点力激发。`tendon_jacobian_matching_v1` 在最终无变形几何姿态的Tip-x行相对残差为1.6364296715924423e-15，Tip-y为0.48270304469407427；不能宣称两条水平行都精确覆盖。低维四曲率组只是机制原型。硬绳KKT静力筛选的最终最大Tip预测0.00011266535109816278 m，与软约束动态最大Tip约0.003067948 m不是同一个模型/结果；局部或硬绳理想结果不能取代动态值。

`passive_design_sensitivity_v1` 在固定拓扑/材料点绑定/正则稳定活跃集合上，以归一化u=(E−2 MPa)/13 MPa进行KKT隐式微分。原生Jacobian和数值Hessian/参数差分共同构成线性化；没有把它称为全解析或自动微分结构梯度。任务位移导数同时扣除随设计变化的无载基准。输出实际检查LICQ、严格互补、稳定性及KKT；非正则/拓扑或绑定变化返回不适用，最大平面外范数仅方向差分。此前terminal_end_factor导数属于另一中间候选，不能替换最终六分支导数。

| s | 力 N | d受力点/du m | dTip/du m | d ratio/du | 最大任务梯度相对误差 | artifact |
| --- | --- | --- | --- | --- | --- | --- |
| 0.7 | -0.1 | -0.018125204007449262 | -0.004887665246779612 | -0.10365391416986125 | 0.0006078686243074622 | `197839ae64e447fa28f2e19b2773b009e8edebbb05d4cab241dabf673ce9cf21` |
| 0.3 | 0.1 | -0.006283434065300894 | -0.0008251874567809593 | -0.040038217655761425 | 0.00015824016668863634 | `b0251413eb6e13e01b46cbe1d3af2967264fcb234e8ddbcfdbecd2b6d6ebbbc8` |
| 0.3 | -0.1 | -0.006249995716721017 | -0.0008967860479778638 | -0.044413227158604233 | 0.0011912227179584377 | `9507fa4b9719bd1fad9e49ad5b464f8f37374f92cb0b3d894591c0f9387520fd` |
| 0.5 | -0.1 | -0.010142890603697184 | -0.001536366352543036 | -0.03809196740114544 | 0.0002777289585265149 | `05c95aed3733a424aa193dac45f9598501021d5b8fbaea2cb15e5b00da4a57c6` |
| 0.7 | 0.1 | -0.018101329184508394 | -0.004411970383448403 | -0.09343550074803937 | 0.00043790135016298 | `9a701ef2acc5a3863a587487bcb19c38918be124b13705a6827f073688e6ebf4` |
| 0.5 | 0.1 | -0.010179351331418039 | -0.001382077333124044 | -0.033469480187045555 | 0.0002975890698334241 | `23eb33bb2cbcae8c71493ea68519ba3cd57b0af53ecde093a4bae720aa21ffe5` |

六分支最大相对误差为0.0011912227179584377（0.11912227179584377%）。这是已保存的隐式导数与重新求平衡有限差分的一致性，作用是设计响应解释/核查；没有新主动控制优化，也没有在软约束动态模型上执行相同结构梯度。最终被动梯度的 `step=0.001` 是u的归一化步长，不能误读为材料SI单位的步长。

| s | 力 N | 受力点 m | Tip m | 比例 | 平面外 m | 原开发评价 |
| --- | --- | --- | --- | --- | --- | --- |
| 0.3 | 0.1 | 0.011178871149159043 | 0.0006730550790620634 | 0.060207785748804844 | 7.175414966822249e-07 | development_pass |
| 0.3 | -0.1 | 0.011155111084834766 | 0.0007175925214694458 | 0.0643285858842772 | 1.0476427256701176e-06 | development_pass |
| 0.5 | 0.1 | 0.02292276866454783 | 0.001387313149586647 | 0.060521186157248726 | 3.4238315464653904e-06 | development_pass |
| 0.5 | -0.1 | 0.02289566237990813 | 0.00150205297502241 | 0.06560425944874704 | 4.144849907218541e-06 | development_pass |
| 0.7 | 0.1 | 0.028020974111792423 | 0.0027819124094638726 | 0.09927964668056008 | 1.1531346326065184e-05 | development_pass |
| 0.7 | -0.1 | 0.02808019811751736 | 0.0030679484830552412 | 0.10925665375349873 | 1.2824391841964474e-05 | development_pass |
| 0.4 | 0.1 | 0.017383839229452448 | 0.000984523663150627 | 0.05663442063376913 | 1.0430123978705627e-06 | development_pass |
| 0.4 | -0.1 | 0.017354590876514347 | 0.0010567052783195259 | 0.06088909187421675 | 1.3420326366272385e-06 | development_pass |
| 0.6 | 0.1 | 0.026897285349280178 | 0.001983574899725279 | 0.07374628606445459 | 7.10475831554445e-06 | development_pass |
| 0.6 | -0.1 | 0.026890291942492744 | 0.0021661171390863214 | 0.08055387214533608 | 8.153374898274173e-06 | development_pass |

上述十行来自 [solution/design.json /cases](https://github.com/wran021004-gif/softrobot-agent/blob/9d6d160e050c836b87d0563a497fc0ec1c3761a8/evidence/phs2d_round3_20261028/solution/design.json)，是九段独立复现结果。原门槛为受力点≥0.01 m、Tip≤0.005 m、ratio≤0.30、平面外≤0.002 m，并保留原稳定性、残差及接触要求。每次从独立无载基准、零速度开始；无载与受载基准不从硬绳受载解直接冒充。

v2保存的10组dynamic_sets中，最终full8有四对六搜索/四留出集合，分别为首次通过、独立复现、半步长0.0000625 s及无载初态1e-4*sin(j) rad扰动。主步长0.000125 s。[数值复核](https://github.com/wran021004-gif/softrobot-agent/blob/9d6d160e050c836b87d0563a497fc0ec1c3761a8/evidence/phs2d_round3_20261028/numerical_comparison.json)保留减半步长最大受力点差1.4398839134899255e-09 m、Tip差1.9560562067658105e-10 m，初态扰动最大受力点差5.136805668326527e-10 m、Tip差2.2678912836669035e-08 m；两个步长和一个初态扰动族不构成普遍收敛/鲁棒性证明。实体腱路检查覆盖保存姿态，不等于连续扫掠或通用绳自接触模型。

**M0–M3。** M0=`partial_or_analogous`；M1=`partial_or_analogous`；M2=`not_applicable`；M3=`not_applicable`。逐项定义、实际扰动、控制处理、证据 ID 和判定理由见配套审计 CSV。

PHS没有主动控制重优化和闭环执行，因此M2/M3不适用。机制Jacobian分析为M0的partial_or_analogous；固定被动长度下的正则平衡设计敏感性单列directly_executed，M1仅标partial_or_analogous，避免把开发静力设计梯度强行归为主动任务层。

## 证据索引、覆盖与unavailable字段

三个交付文件采用UTF-8。决策CSV共460行，覆盖重要决策、支持执行、失败/拒绝、46个实际PHS候选、六对保存输入匹配及最终结果审计视图；`importance` 可筛major_decision。M审计CSV固定11任务×4层=44行。`not_used_at_this_node`、`not_executed_at_this_node`、`not_applicable` 和 `unavailable` 含义不同，均未以0补缺。所有单位换算仅为原记录的显示换算，没有拟合、差商或重算物理。

| 字段/入口 | 解释 |
| --- | --- |
| task_id / stage_id / run_id | 联合主键，避免跨run重复T04-211/T10-222等节点混淆 |
| source_scope / source_commit | FULL最终结果、研究过程、前驱/废弃run、九段lineage分别标记；本地Trace没有伪造Git commit归属 |
| structure_before / structure_after / structure_changes | JSON物理快照/逐字段差异；相邻保存版本不推定因果父项；失败生成没有新物理结构 |
| mathematical_request_id / mathematical_artifact_ids | 实际请求与数学输出，不是工具目录；generation请求另有request_id |
| control_initialization | 完整保存设置/输入源；初值迁移与最终物理输入的相等性分开 |
| physical_validation_result / result_scope | 原生代理、失败试验、独立完整验收和开发有效分类分开 |
| decision_influence / causal_boundary | 实际后续改变及解释边界；未将每次工具调用都记为有效改进 |
| evidence_refs | 结构化JSON：Git commit+文件+pointer，或Trace文件+行+event_id+SHA-256，或原Store路径+artifact_id |
| related_evidence_nodes | 重要节点的同run数学/决策和最终验收交叉索引；不把重复审计视图重复计为执行 |
| M审计的separate_passive_sensitivity_* | 仅PHS/M1行单列实际执行的被动平衡设计梯度，不改变M0–M3严格分类 |

冻结 master 的 ALL_TASK_RESULTS、TASK_CASE_RESULTS、KEY_RESEARCH_NODES、CANDIDATE_EVOLUTION、HARNESS_COMPONENT_EVIDENCE、RESEARCH_PROCESS、EVIDENCE_INDEX、SELECTED_RESEARCH_EVENTS、DECISION_CATALOG、RESOURCE_DETAILS、KNOWLEDGE_READS 和 MODEL_BINDINGS 均已作为入口读取/对照；二级概括与原请求不一致时以原请求、候选artifact及完整验收为准。RESOURCE_DETAILS只用于识别已有计算范围，没有推算缺失Token、CPU或solver成本。历史Knowledge/Skill的实际读取版本来自 [KNOWLEDGE_READS](https://github.com/wran021004-gif/softrobot-agent/blob/15d4667050351c1cbf84e6ade6f573286d6d8ed0/paper_experiments/paper_results_master_20261113/SOURCE_DATA/KNOWLEDGE_READS.json)；读取或迁移本身不证明收益。

### 实际使用方法的代码位置导航

| 已调用方法 | 代码位置 | 证据约束 |
| --- | --- | --- |
| Native Response / Pattern | `.worktrees/core-five-task-completion-20261113/tools/research/local_control_search.py:115`、`control_correction.py:260` | T01/T02/T03/T05/T06/T07等实际research.math返回的native_analysis与numerical_evidence；不据同目录其他函数补填调用 |
| Native平衡组SLSQP | `task.initial_state.construct`请求/返回：T04-211、T04-216 | 89点优化标志与独立资格检查分别读取；非结构导数 |
| Native反馈/LQR | `.worktrees/core-five-task-native-feedback-20261113/extensions/tendon_family/native_feedback.py:72`、`:115`、`:136` | 最终T10 profile.native_feedback_preparation artifact实际包含A/B/K/Q/R、Jacobian及方法名；非结构切线 |
| PHS被动KKT/隐式导数 | [冻结passive_inverse.py](https://github.com/wran021004-gif/softrobot-agent/blob/9d6d160e050c836b87d0563a497fc0ec1c3761a8/extensions/tendon_family/passive_inverse.py)::design_sensitivity/task_design_sensitivity | 绑定实际19个analyses及最终六分支artifact；非自动推断工具能力已使用 |
| PHS路线匹配/筛选 | [冻结phs2d_inverse.py](https://github.com/wran021004-gif/softrobot-agent/blob/9d6d160e050c836b87d0563a497fc0ec1c3761a8/tools/research/phs2d_inverse.py)::optimize_matching/screen | 实际route_optimizations及screen引用；minimize_scalar成功标志false亦保留 |

本地Core代码仅作解释导航，原运行版本以各Trace core_sha / result implementation及保存数学输出为准。PHS候选科学ID从原封存Store只读提取，并将候选body的SHA-256与冻结archive_manifest的成员哈希逐项核对；没有用当前生成器重建候选。

### 原始Trace快照

| 本地原始路径（相对D:/softrobot-agent） | SHA-256 |
| --- | --- |
| `paper_experiments/ten_task_codex_solve_20261112/T01_M1_reach_hold/STUDY_TRACE.jsonl` | `51c17ff6d7c2adf6f4cee8e83d2eff6e79caa3af5a5e9196bc19859b9fd5c913` |
| `paper_experiments/ten_task_codex_solve_20261112/T01_M1_reach_hold/T01_RUN_02/STUDY_TRACE.jsonl` | `d7573fe5ddb42d2dea593199a1b13d3eae61accbaf834373a127987292cc13dc` |
| `paper_experiments/ten_task_codex_solve_20261112/T02_M2_loaded_hold/STUDY_TRACE.jsonl` | `0fe8ea8bfc97d5635fdf2e66c9980b251bdb6adeb71244399fba988e27723c7a` |
| `paper_experiments/ten_task_codex_solve_20261112/T03_M3_fast_reach/STUDY_TRACE.jsonl` | `de7d7ab96efb1cf01f8045b8d4d42af7dbe67588acc29665d03e1f3e730662b9` |
| `paper_experiments/ten_task_codex_solve_20261112/T04_figure_eight_tracking/STUDY_TRACE.jsonl` | `8ab57ae57be8a8f9d6590a023b36da70fa7327583ddb9246b2bf3dce06661a09` |
| `paper_experiments/ten_task_codex_solve_20261112/T05_M5_tool_axis/STUDY_TRACE.jsonl` | `5cee28619a5ef73ef098218aa5fc361c50239ac95cf6713b243411548115d9e6` |
| `paper_experiments/ten_task_codex_solve_20261112/T06_M6_loaded_scan/STUDY_TRACE.jsonl` | `933dac0c873745713e5beb46c20b6768de2b2048cd57550529d6e45f1a351f7c` |
| `paper_experiments/ten_task_codex_solve_20261112/T07_C1_four_tendon/STUDY_TRACE.jsonl` | `2b1244ec2d31c4eb21aa1854076cd7724baecd21345e2c533a792fb6ae523af0` |
| `paper_experiments/ten_task_codex_solve_20261112/T08_P3_progressive_stiffness/STUDY_TRACE.jsonl` | `5cac552af5c3fc7b183aba42d60c598cb07aaa85a43c4a91d12cc16f7857e4ae` |
| `paper_experiments/ten_task_codex_solve_20261112/T09_spring_button/STUDY_TRACE.jsonl` | `c547b68734db6c625e84b2b14759dfd7bf391b1779814e923d3c999753dd7cca` |
| `paper_experiments/ten_task_codex_solve_20261112/T10_M7_impact_recovery/STUDY_TRACE.jsonl` | `257bf24e3bfbd57b60ac8e394055ac5c5fdfefe8bc023b906fdc8c6cfff3cfa9` |
| `paper_experiments/ten_task_codex_solve_20261112/T10_M7_impact_recovery/T10_RUN_02/STUDY_TRACE.jsonl` | `658e1a1434e11e42186d930d5303c64c333f9d44e44c3335bdc7384f73052e52` |
| `paper_experiments/five_task_completion_20261113/T01_M1_reach_hold/STUDY_TRACE.jsonl` | `08499cd044b23fd080fb4ed9a17ca3cdb76451e1d6b6dc2dfeae7b7f4e0cce29` |
| `paper_experiments/five_task_completion_20261113/T04_figure_eight_tracking/STUDY_TRACE.jsonl` | `9a42af9e83d049e82d764b698045075234f77a19e4ca8b889b1d4fb04e16776e` |
| `paper_experiments/five_task_completion_20261113/T04_figure_eight_tracking/T04_RUN_02/STUDY_TRACE.jsonl` | `3d590965f93976fd9889ffa373253d206ccc5c6f649f80f299c99b94664869de` |
| `paper_experiments/five_task_completion_20261113/T04_figure_eight_tracking/T04_RUN_03/STUDY_TRACE.jsonl` | `e83ffa74c0053f4565bad0d78b62d9e70e5314887e165dcbf498903c3eadfb9c` |
| `paper_experiments/five_task_completion_20261113/T07_C1_four_tendon/STUDY_TRACE.jsonl` | `09ab65b65539a7c9cf45d33942fe7a417f0d6805731b2a4e5e3760610c6ac30b` |
| `paper_experiments/five_task_completion_20261113/T09_spring_button/STUDY_TRACE.jsonl` | `7a9bca1243b026a3ce69727d375a49ce8f55b9c76cf0a1b88053402bcb862cea` |
| `paper_experiments/five_task_completion_20261113/T09_spring_button/T09_RUN_02/STUDY_TRACE.jsonl` | `dd899b51f246c701123c39f68eae8404b5db84ec0687143bdc8be146f4679dce` |
| `paper_experiments/five_task_completion_20261113/T10_M7_impact_recovery/STUDY_TRACE.jsonl` | `91d341f661574e10a31fe06d053b0d71a2f2a97c4e1860e718b0558a34484d94` |
| `paper_experiments/five_task_completion_20261113/T10_M7_impact_recovery/T10_RUN_02/STUDY_TRACE.jsonl` | `6807bb22498f8855d57cd7d06c0890af7ea90c6d676fc8d208afaf38d476df71` |
| `paper_experiments/five_task_completion_20261113/T10_M7_impact_recovery/T10_RUN_03/STUDY_TRACE.jsonl` | `f0d35c505e200f60be9223f51896cb96ca3c7abf0bc21d85df27b70b4fd1499d` |
| `paper_experiments/five_task_completion_20261113/T10_M7_impact_recovery/T10_RUN_04/STUDY_TRACE.jsonl` | `1bb9d5649d0abd7bbbbc9ba7f80e55ffacff18b7da096cf398b34c0caa84996a` |
| `paper_experiments/five_task_completion_20261113/T10_M7_impact_recovery/T10_RUN_05/STUDY_TRACE.jsonl` | `2f57ab4a5be0b5a5da03d0632397c34776d468595b77b49993a33fb8a31bfa2c` |
| `paper_experiments/five_task_completion_20261113/T10_M7_impact_recovery/T10_RUN_06/STUDY_TRACE.jsonl` | `bfd5118313bf22cbfd4b836b1e6ed7ad8e40c341ea4438f74ce280d468407e4c` |

这些补充Trace和原Store不是此次新提交内容；其原路径必须随论文原始证据归档保留。Git冻结master中的所选事件与最终候选/结果仍可独立访问。CSV保留引用及解析出的结果，不声称所有本地前驱Trace已在15d466705冻结包内完整发布。

### 仍不可用或不应补造的证据

- 九段PHS的原生栈溢出请求输出、内部构造/forward计数和该请求elapsed_s仍为unavailable；零积分尝试与一次顶层数学费用按原记录保留，没有重发该未知请求。
- 被拒绝/未物化的生成请求没有candidate ID或物理验收结果；Study级stop/select可不携带候选。它们分别记“未产生/不适用”，不能生成虚构候选。
- CANDIDATE_EVOLUTION的真实因果父候选字段原为unavailable；本审计只给实际前后保存结构差异，不补造因果谱系。
- T01/T02/T07的真实最优值、结构导数、单参数独立贡献及M3结构敏感性未执行，不能以工具能力或任务名称补齐；它们属于未执行，不是缺失数值待估。
- 各run未完整记录的Token、CPU、求解器成本没有估算；本次不重算或重复累计历史成本。

## 可直接用于论文的结果表述

在十项主动/被动FULL任务和九段被动主案例中，研究路线的有效改变主要表现为适用性检查后的模型切换、有限预算结构—控制交替比较、控制初值迁移、实体安装/接触修复及独立验收。T01/T07的保存序列可事后核对出同输入的有限尺度结构响应；T01、T02和T07另记录了结构变更后重新优化控制的经验性任务能力比较。这些证据分别属于M1-style与M2-style，没有提供严格结构导数。T04的平衡组、T09的完整接触重放及T10的LQR反馈成功也没有自动构成结构敏感性分析。九段PHS另外实际执行了带无载基准的正则KKT被动平衡设计敏感性，并通过重新求平衡有限差分核查；该梯度用于固定设计的响应解释，现存时间线不支持将最终性能改进归因于梯度指导的后续改型。
