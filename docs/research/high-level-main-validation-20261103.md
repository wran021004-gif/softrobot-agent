# 高层科研接口与有限 Main 验证

本次任务沿用 `m1-low-tendon-speed004-20261102-campaign3`，不新增科研 Store、Agent 或数学内核。正式续研前必须保存原 nonpass STOP、精确实现绑定和资源追加授权；本文件中的工程测试不能代替 Main 自主科研。

## 方法职责

| 入口 | 实际工作 | 前提与结论边界 |
|---|---|---|
| `research_plan(generate)` | 构造真实物理结构；支持选定父结构上的明确物理参数改动 | 冻结 FamilySpace、结构可编译；不执行控制优化，不继承通过证据 |
| `research_plan(search)` / `scientific_structure_search_v1` | 编译为原 `bounded_mixed_coordinate_v1`，在 Main 选定变量组和范围内提出结构，并按已选 Native 或代理模型评价 | Native 每个冻结工况独立 T1；Conic 代理与真实 Native 不互换。不可无损表达的父结构仍拒绝并提供 generate 入口 |
| `mechanism_structure_v1` | inspect / differentiate / optimize / compare 已注册物理机制 | 明确实际工作点、物理输入界限、目标和方向；机制方向不等于完整任务改进 |
| `mujoco-nonlinear-task-capability-v1`（T1） | 给定结构、工况、初态及合法输入，执行有限 Native 控制搜索 | 全部冻结任务约束保留；有限最好值不等于全局最优或不可行性证明 |
| `mujoco-reoptimized-structure-response-v1`（T2） | 聚合已保存的匹配 T1，对照固定输入与重优化后的结构效应 | 同实现、任务、初态语义、合法公共初始输入、参数化和努力；不附带生成结构或执行 T1；局部割线不冒充最优梯度 |
| Conic task capability | 冻结初始预张力下的 sampled affine minimax | 不在任意 Native schedule 周围线性化，不等于独立物理通过 |
| qualified sensitivity | 原已保存合格 Conic 模型 stencil 的条件敏感度 | 必须满足原匹配、正则性及数值可信度检查；不是 Native T2 |

结构修改不以 T2 为门禁，RL/NMPC 也不是结构研究的强制步骤。

## Main 的输入

V4 Native 控制与结构联合搜索共用现有 `control_search_effort`：

```json
{"resolution":"coarse","exploration":"broad","evaluation_requests":16}
```

Provider Schema 不再要求内部 knot 数、迭代数、差分步长、活动系数或信赖半径。粗/适中/细对应 3/5/9 个真实时间基函数结点；全任务结点绑定冻结控制网格，无法表达时明确拒绝。广范围允许实际物理张力跨度，局部精修使用其 10%；仍由原输入裁剪与合法性检查执行。程序确定 response 数值实现和数值步长，原数学准入与 Worker 工程限制保持权威。历史数值请求和结果保持原义。

Main 可选择全任务、冻结 reach/holding 阶段或明确时间窗口，可明确选择一个或多个合法起点。共同 callback 上限由原优化器计量，相同实际输入复用计算。实际 knot、活动系数、输入界限、来源、回调与物理成本保存在原请求/结果中。

父结构局部修改使用 `generation.changes={物理参数ID:绝对SI值}`，父候选由 `decision.selected_candidate` 指定。程序复制完整父结构，修改且仅修改所选路径，保留截面旋转和非默认参数；原物理域与构造器继续校验。非主工况的父候选保留同一冻结工况绑定。完整拓扑生成仍使用原生成契约，FamilySpace 身份由冻结配置绑定。

## T2 准备与证据投影

`/t2_preparation` 默认只给出当前基准、可执行 T2 数、缺失项及高层选择入口。V4 结构问题明确选择参数和 `local_radius_fraction` 后，准备反馈列出真实合法对称步长、负/正结构是否存在及生成请求；不得悄悄改选另一个尺度。`/t2_preparation/details` 才返回完整参数域、T1 引用、拒绝原因和底层执行模板。只有 Main 明确提交生成或 T1 请求才执行对应动作。

Main L0 持续交付瓶颈诊断与 T2 准备导航；Reporter 使用同源瓶颈事实，并交付 T2 就绪状态。机制工作点只自动交付时间/阶段和准确查询入口，完整状态留在按需证据中。历史各最佳控制的内部设置数组改为努力摘要和精确设置查询；原始值、费用与证据从不重写。Reporter 保留事实/预测/假设的区别，不选择 Main 的结构或实验。

## 已核实的原始边界

只读核实原 h43 STOP，39/39 结果引用完整。Provider 144/152，公共操作 134/569，Replay 0/18，数学累计 58 且无累计配额；没有 pending、未消耗 SDK response 或未封口 reservation。2244 条原 artifact 与封存清单逐项匹配。原数据库 SHA256 为 `47350c5c56f87a2b1b28e206b38de77b4f2baa568b6b331b48cf60839f68d833`。

原冻结实现为 `d9b357f`，不是本次起始代码 `7bf449f`。旧 T1 不会被自动视为新实现的合格 T2。

原真实最后探索 Main 请求为 334,996 bytes / Provider 报告 prompt 49,705 tokens；最后收尾 Main 为 346,796 bytes / 50,629 prompt tokens；最后 Reporter 为 30,012 bytes / 7,892 prompt tokens。原 h43 同一状态的只读 L0 投影为 86,299 bytes；没有完整张力、原始状态或矩阵数组泄漏。修改后测量与实际新请求必须分别记录，不能用离线投影冒充新 Provider 使用量。

## 验证与授权状态

定向测试覆盖真实 SDK/Mock Provider Schema、高层意图到原请求、物理参数原样保留、控制尺度与实际自由度、阶段边界、T2 缺失反馈和原准入。Mock 回复与工程夹具不属于自主科学证据。

累计 72 个定向用例通过（包括修正后重跑的旧 fixture）：59 项核心/信息流用例和 13 项历史 ScientificQuestion V2 用例。旧信息流夹具缺少现行数学授权，且把未明确选择的默认 generate 路由当作持久路由；测试现显式建立离线授权和 generate 选择，生产准入没有被放宽。真实 Mock Provider 搜索用例改用本次高层努力输入。历史数值努力仍要求原明确 method，防止 V2 语义被静默改变。

提交 `a29aad3` 后，已在既有隔离工程 Store 完成 6 个真实 Worker：多起点、细分辨率、3 个匹配 T1 和一次 T2。3 个起点含一个重复实际输入；4 个 callbacks 对应 3 次 rollout。粗细维度为 6/18，全部验证总计 11 次 rollout、6,600 物理步；T2 复用 3 份 T1，新增 rollout/物理步均为 0，方向仍为 unresolved。Young 模量的对称工程扰动实际为 ±260,000 Pa。所有 Worker 终止均确认，原正式数据库校验和未变。

后续仅修正 Reporter 的重复展示，基于上述已完成回执只读重新组装请求，没有重跑 Worker：双结果 Reporter 组装体从 54,553 降至 50,267 bytes，保留全部不同指标、变化、阈值、数值不确定性和 source catalog。活动系数只自动给出数量和准确原始查询，完整索引留在 Store。同一原 h43 状态的 Main L0 从 86,299 降至 78,985 bytes；这是离线同状态投影，不是实际新 Main 请求，也没有新 Provider token 使用量。

正式续研仍需精确提交、resolved identity、Provider 累计上限 176（新增 24）、20 次探索与原最后 12 次收尾保护的可审核授权。公共操作和 Replay 不追加，数学累计配额仍为空。本任务不授权 PPO 训练。正式授权落实前保持原 STOP；新实验、监督检查与最终结算必须另附实际回执报告。本次新增提交的普通推送也被自动审批要求取得单独的明确导出授权；未绕过此限制。
