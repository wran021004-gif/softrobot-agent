# BF4：时间约束轨迹跟踪 Benchmark 候选

日期：2026-10-27。基线 `d7b0f91f966ef96fa17b181ead99dff9a2d457cc`。
本报告区分工程链路验证和科学可行性研究。**尚未开展新科学搜索，独立可行见证与结构效应均未决。**
任务明确要求新任务使用单独的事先额度，不继承 BF1/BF2；本轮先交付准备工作和最小工程检查。

## 冻结规范

权威文件：

- [新任务 v1](../../tasks/bf4_tracking_direction_change_v1.json)：`bf4-timed-direction-change@1.0.0`，`development_valid`，不授予正式科学执行权限。
- [冻结计划 v1](../../configs/research/bf4_tracking_freeze_v1.json)：任务/FamilySpace 身份、三组事先结构、初始化、搜索设置、阶段上限。
- [零科学额度准备配置](../../configs/research/study_bf4_tracking_preparation.json)：原 loader、FamilySpace v2、空科学结果；数学评价和物理启动均为零。
- [独立工程检查配置](../../configs/research/study_bf4_tracking_engineering.json)：仅一条 native baseline 和一次独立回放，不产生控制优化迭代或结构比较。

| 项目 | 冻结值及物理解释 |
|---|---|
| 轨迹 | 世界系分段线性节点 `(0.300,0,0.150)`、`(0.285,0.035,0.170)`、`(0.285,-0.025,0.180)` m；节点时刻 `0,0.30,0.60` s |
| 应用 | 一次短工具端路径执行；中途横向运动改变方向，不是单点 Reach/Hold |
| 时钟 | 物理步长 1 ms；控制/采样 20 ms；总时域 0.6 s；30 个保存的 post-step 位置 |
| 评分 | `[0.02,0.60]` s 含两端，全部 30 个样本的 `max ||p_k-r(t_k)|| <= 0.012 m` |
| 容差理由 | 12 mm 约为名义 0.30 m 臂长的 4%；这是首版开发任务分辨率，不是硬件精度承诺。两个评分节点相距约 60.8 mm，大于 24 mm，因此不存在可通过的恒定 tip 位置。未依据某结构成败调节阈值 |
| 参考速度 | 两段参考速度约 `(-.050,.117,.067)` 和 `(0,-.200,.033)` m/s；折点允许分段线性速度不连续。未规定速度误差硬上限 |
| 初始化与环境 | 所有候选命名 qpos/qvel 为零；安装位置 `[0,0,.15]` m，重力 `[0,0,-9.81]` m/s²；原 free 环境，无额外外力 |
| 驱动 | 6 个独立理想绝对张力通道，`0..8 N`，每个候选各自产生并绑定通道顺序；非执行器位移控制 |
| 保真度 | 每段 12 个 bending cells；MuJoCo implicitfast；不混入粗网格分数 |
| 完整验收 | `evaluate.tracking@1.0.0` 加 `offline_timed_tracking_v1` 的执行/采样、求解错误和张力边界；无连续时间保证 |

原开发文件保持不变。canonical task 将候选相关的命名零状态归一为 `all_candidate_dofs_zero_v1`，同时各候选保留真实命名初始化和 effective task identity。

## 已实现链路

任务 → 原 FamilySpace 合法结构 → 原控制初始化 → 原 `local_control_search` → NativeModel 序列 → 独立 `physical_replay` → 原 Tracking evaluator → 完整验收。

1. 新增 task-adapter 的控制条件提取；timed Tracking 的向量正是评分时刻的归一化位置误差。缺失/错位的评分时刻直接拒绝，无终点和绝对保持速度替代。
2. 原 response/pattern 算法不变；public `control_search` 与 native direct control 接入同一任务条件。untimed 完整几何目标仍明确 unsupported。
3. 原物理路由接受经工程审查的 timed development 任务，仍检查 controller 12、参考模式、零状态、合法张力和网格；draft 不可执行。
4. 新增有版本的 timed 复合协议；复用 evaluator 的原 `tracking_max_error`，缺必需条件时返回 missing_evidence，失败完整保留。
5. 独立回放现在保存单独 profile artifact，并让结果、profile、验收和 Store receipt 使用同一真实 execution ID；request ID 单独保留。这修正了已有回放结果中的来源缺口，未重写历史实验。
6. native 优化只给 sampled diagnostic 和可执行序列；`task_acceptance=unmeasured`。完成独立回放后才有原任务结论。

GVS/SoRoSim 局部方法不被强制迁移。SoRoSim controller 仍不支持 Tracking；机器人上的 GVS timed 预测精度、闭环 NMPC 性能未做本轮科学验证。
nonlinear T1/T2 不纳入 Tracking；本轮可用数学指导仅为搜索内部的有限差分时序响应及其秩/方向诊断。

## 公平结构比较（已事先固定，尚无物理比较）

三组均两段、六腱、每段 12 cells，总柔性长度 0.27 m，其余材料、截面、张力边界和数值设置相同：

- full_span：六腱均跨两段，等角布置，长度 `.16/.11` m。
- split_span：三腱跨两段、三腱仅驱动远端，远端腱组相位错开 `pi/3`，长度仍 `.16/.11` m。
- redistributed_lengths：沿用 split_span 腱路，长度改为 `.135/.135` m。

三个请求均由真实生成器和几何检查接纳，尚不构成任务可行性证据。
最初 split_span 两组相位相同被导孔间隙检查拒绝；仅在任何物理测量前改为不重叠的等角布局。原始失败情况记在验证记录中，没有凭物理成败调任务。

初始化统一为恒定 `.2 N`；必要的独立起点为恒定 `.6 N`，不继承历史控制或成功路线。
每个设计/起点独立优化，response 搜索四个时间结点 `[0,.2,.4,.58]`，24 维，3 次迭代、至多 76 回调，系数界 2 N、起始半径 .2 N、差分 .02 N，局部目标有 5% 裕量。
原张力界和 12 mm 验收不变。

比较顺序为独立通过与否、原约束违反量、首次独立通过成本、全部 physics_steps 与实际耗时。
达到首个完整独立可行见证即停止**可行性阶段**；后续结构比较属于另一阶段。每个对照组也在其首次独立通过后停止追分。
若差异随控制优化消失，保留为控制优先任务；有限失败永远不解释为结构理论不可行。

## 阶段额度提案（未授权执行）

| 阶段 | 新额度上限 | 停止与记账 |
|---|---|---|
| S0 工程检查（已由任务授权） | 1 次 native baseline + 1 次独立物理回放；共至多 1,200 步；Provider/NMPC/RL 为零 | 单一起点，禁止额外科学搜索。私有 Store 独立保留 |
| S1 可行性 | 至多 3 结构 × 1 起点 × 76 native 回调，至多 3 次独立回放；总上限 138,600 步，3 次数学搜索调用 | 首个完整独立通过立即停止；所有基线、差分、建议及失败均计数；每组总 76 回调，不能用重启补额 |
| S2 结构效应 | 3 结构 × 2 起点总共至多 456 native 回调、6 次独立回放、277,200 步 | **含 S1 已发生的匹配组与成本**，不是重置或另加同样余额。先审查 S1，再给此阶段独立授权 |

每条完整 native 序列 600 步，独立回放再 600 步；表中上限按此相加，无后缀初始化额外积分。
若 native 代理未通过，仍在额度内评价该组 best，保留有限失败。若代理通过而独立回放失败，保留差异，不能增加回放或重启配额。
不设置虚构的科学耗时预测；实际积分步数、模型构建、回调、数学次数、物理启动、wall time 均由原结果及 Store 记录。
S1/S2 不由准备配置自动开通，需要新 Study/阶段的明确授权及独立账本。

## 验证和实际成本

已通过 39 项直接相关测试（BF4 6、既有局部搜索 14、native control 6、跨任务集成 3、task runtime 10）。随后保持 Reach native 指标原有算术顺序，并复核 BF4 六项和历史控制重放一项，7 项通过。
覆盖任务编译/冻结/时间网格、原评价一致性、不可退化常值、完整验收及来源、合成 response 搜索首次通过停止、原 Reach/Hold 路径和历史控制回放。
测试不会发 Provider 请求或执行真实积分；合成成功记录明确仅为测试。

历史控制重放的一条测试在原基线与 BF4 下均出现 SLSQP 系数约 `1e-17` 的末位差异。仅将该测试的数值比较设为 `atol=1e-12, rtol=1e-10`；历史数组、结构/控制哈希和执行身份仍精确保留。

S0 已在提交 `277c7404cc6a101325d3d1ebb0bf410296eed0aa` 上绑定并完成，使用原 Store、worker、执行回放和注册评价。一次 native baseline 的完整序列预测和另一次从任务零状态重新开始的完整物理执行各 600 步。原验收返回 **valid_failure**：未优化基线最大误差 `0.1773713726 m`，大于 `0.012 m`；这不是结构不可行结论，也不是可行解搜索。

| 实际新增计算 | 次数 / 步数 | 实测时间 |
|---|---|---|
| 候选构造 | 1 个生成候选；不做结构物理比较 | 0.325970 s |
| 控制初始化 | 1 条恒定 pretension 序列；不做积分 | 0.151271 s |
| Native worker | 1 次数学调用、1 次 baseline 回调、1 次模型构建、600 次积分尝试/完成；0 次完成的 response 建议 | 内核 0.100434 s；含 worker 的实际记账 1.065769 s |
| 独立物理回放 | 1 次启动、1 次模型构建、600 次积分尝试/完成 | 内核 0.129674 s；含 worker 的实际记账 1.108395 s |
| Store 数值累计 | 1,200 步；数学评价 1、backend solve 1、public tool calls 5 | 2.651406 s，已含以上构造/初始化和两个 worker，不能再相加 |
| Host 兼容准备 | 非科学候选 scaffold，无积分 | 另计 0.523474 s |
| 整个 S0 驱动 | 含准备、绑定、记录、读取及停止 | 6.655161 s，包含上述时间，不能再次累计 |
| 定向单元检查 | 共五批含失败与基线问题复现；92 个测试执行，未调用真实积分 | 测试框架记录合计 12.429 s |

S0 再提交同一 native/replay 请求仅复用原 receipt，新增积分为零、额度不变；Store 已停止封存。原评价、profile、原始回放和验收的来源关系及真实 execution ID 均已核对。Provider 请求、NMPC 更新、RL 动作和正式科学搜索均为零。

公开 [工程摘要](../../evidence/bf4_tracking_preparation/engineering_summary.json) 只含成本、验证与失败指标；[验证记录](../../evidence/bf4_tracking_preparation/validation.json) 保留先前测试失败、基线重现及修正说明。结构、控制、原始轨迹与 Store 留在 `runs/bf4-engineering/`，不上传。
没有独立可行见证，结构效应仍未决，未转移任何旧 Study 余额。任务阈值、轨迹、时域与控制设置没有因该基线失败而改变。

## 交接与结论边界

当前为工程已适配的 Benchmark 候选，尚不能称为验证过结构收益的正式 Benchmark。
后续 Agent 必须独立 checkout、Store 和可读范围；不提供本开发分支的结构请求、控制或任何成功答案，也不导入本地工程 Store。
公开工程摘要不等于盲态评价材料。B 线可查全部本地开发证据；盲态任务只给任务、FamilySpace、公开工具契约、成本规则与授权额度。

完成 Tracking 的可信可行性/公平重优化验证后，再考虑位置—工具轴方向任务，详见 [跨类别审计](bf4_cross_family_task_review.md)。
