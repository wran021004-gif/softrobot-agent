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

工程阶段结束后，用户明确批准推送、迁移和上述有限续研。已普通推送至 `1aa5086`，通过原 B3 原子机制将累计 Provider 上限设为 176，保留 20 次探索和最后 12 次收尾保护。公共操作与 Replay 不追加，数学累计配额仍为空；原 h43 STOP 和完整状态作为不可变记录永久保留。批准 scope 为 `d1d0a7f03a6a88ba562ab4aa170f4e59d8a8640644e8714152914f15ce983ff9`，新 resolved identity 为 `2c53463666dabbfe78e6ad69bb52aa9db6b9ff76f73a45ae2f16993d3c23a012`。用户随后明确授权在其离开期间监督执行、必要时有限追加额度和修复接口。每次实际追加和修复绑定仍需在原 Store 留档，无自动滚动续额，不启动 PPO。

## 迁移前的只读预检修复

从原科学实现迁移后，原候选应保留旧 profile，不能直接执行。只读预检发现机制能力目录与方向视图错误地再次使用执行准入检查，导致整个 Main packet 报错。修复仅使历史读取返回明确的 `requires_current_profile_candidate`；原 `verify_candidate` 对 T1、机制求解和 Replay 的旧 profile 拒绝保持。

Main 可以明确选择 `research_plan(generate, generation.changes={})`，在新实现下重建完全相同配置。该动作创建新 profile 的候选，不继承旧 T1 或验收。非空改动仍绑定原物理路径与域。T2 准备排除旧 profile 的结构库存，并把旧证据标为历史；方向采用关系只读查看原候选，不能授予当前执行权限。新增回归验证了历史目录可读、旧候选仍不可执行、显式重建配置完全一致，以及新候选和旧库存共存时 T2 准备不报错。相关 14 项当前接口用例通过；原真实 Store 的只读模拟 profile 迁移预检通过。没有为此次修复重跑任何已完成数值 Worker。

## 首个真实窗口的反馈交付修复

正式 Main 的前三次请求均重复读取完整结果索引，没有启动数学 Worker。实际 wire 显示 SDK 的 eager offload 在首次交付前就截断了刚请求的索引，Main 只收到历史预览提示；成功工具回执不能替代实际模型读取。三次请求均保留收费。监督器先暂停该窗口自有 Job 内的进程，再核实无 Provider/Worker 在途、无未封口调用、无 SDK 未消费响应，才结束该 Job，未制造科学 STOP。

现使用 SDK 原生 `preserve_recent=1`：最近一次工具反馈完整交付一次，旧反馈继续按原阈值压缩；原 Store、SDK stash 与真实 wire 仍是审计来源。实际 SDK/Mock HTTP 回归验证了 39 项索引首次完整送达、较旧索引随后压缩、下一份最新反馈完整送达，以及读取确认不会授予完整结果正文或 SELECT 信用。Evidence 读取与 nonpass 启动投影复用现有 request-local 只读缓存，缓存不跨操作保存。该修复不改变科研路线、数值方法、费用或验收。

本次交付修复的 6 项 Provider/SDK 用例全部通过，3 项 SDK 恢复用例通过（含 14 种进程中断子场景）。扩展运行的另外 4 项历史恢复用例未通过：3 项旧夹具未建立现行数学授权、先被原准入门禁拒绝；1 项依赖本克隆未包含的历史数据库。保留原失败日志，不放宽生产准入或伪造历史数据；正式 Store 的 SDK 恢复仍须另行实际核实。

正式 Store 已实际完成无发送 SDK 恢复，费用不变。继续后的 Main 明确判断：旧两绳结果来自有限且未匹配的搜索，不能证明结构不可行；自主选择先重建旧候选，再做低绳数联合搜索。首次 diagnose 旧 profile 被原门禁拒绝，Main 随后正确改用 `generation.changes={}`。但宿主旧的身份绑定分支又往 ScientificGeneration 注入 `family_space_identity`，导致两次合法 Main 生成请求被拒绝，没有 Worker。该分支现只为传统完整生成契约补身份；高层物理改动先由原编译器构造完整合法请求。新增真实 SDK/Mock 回归证明旧候选能在新 profile 重建、配置完全保留、Main 原始高层请求不被身份字段污染，原完整生成路径仍通过。8 项定向用例通过。

截至第二次安全暂停累计 Provider 151/176，本轮新请求 7 次，其中 3 次索引交付故障、2 次生成身份注入故障。依据用户后续明确授权，准备一次性追加 5 次至累计 181，补偿上述软件故障占用的探索机会但不退款、不重置费用，最后 12 次收尾保护保持；公共操作和 Replay 不增加，不启动 PPO。追加、实现绑定及准确身份须在原 Store 记录后才能继续发送。完整科学结果另以后续正式结算报告为准。
