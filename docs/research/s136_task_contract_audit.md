# S136：任务语义与科研数学接口审计

日期：2026-10-23（Asia/Shanghai）。分支：`research/s136-task-contracts`。

## 结论与本轮边界

一个审核后的任务规范可以成为独立评价、数学分析、NMPC 目标与 RL Reward 的共同依据；
现有代码尚不能只换目标、评价和约束就自动执行任意新任务。已有的可复用基础是
TaskDefinition、注册评价器、带信号/来源的数学约束、独立物理验收和受限控制参数选择。
主要缺口在任务到控制输出/目标项的适配，以及模型、观测和执行能力的逐项匹配，
不是缺少另一套 Tracking 求解器。

“只提供新目标、评价规则和约束”成立的前提是：它们使用已支持的观测、单位、坐标、
物理模型和执行接口。若新任务引入接触力、全身距离、对象捕获或事件阶段，必须先有
相应信号、模型和独立评价实现；Agent 不应从文字自动制造缺失的物理能力。

本轮遵守审计范围：小范围接口修复、离线契约测试和具体扩展建议。没有新 Study、
真实 Provider 请求、MuJoCo/MATLAB/NMPC/PPO 实验，没有迁移 F3 验收，没有新审核 Agent、
Reward DSL、Task Registry/Store/SDK 重写，也没有实现下文提出的通用控制接口。

## 基线与权威来源

从已验证 S132 `4eb740f932d1cd01ece575777c0fcef4bc646880` 创建独立 worktree
`.worktrees/s136-task-contracts`。通过 `git ls-remote` 核对：S132 远端仍为该 SHA，
S131 为 `8af4ab82337ebcb2fceb6f6ce835f3e29e49d0d3`，S134 分支当时未出现在远端。
S132 工作树干净；主工作树为 `feat/gvs-dynamics`，已有未跟踪研究文件，未修改。
读取的约定是本基线 [AGENTS.md](../../AGENTS.md)，根工作树没有该文件。

权威来源应分成三个身份，而不能只拿 task_id 或文件名：

1. 审核后的 TaskDefinition 内容及评价器版本，拥有目标、环境、初始化、信号、时间和评价规则。
2. 冻结 Study/有效 SessionInput 与验收协议。现有 Reach+Hold 的完整权威是这一组合，
   因为保持条件不在 TaskDefinition 中。旧 Study 只能使用其保存快照，不能重读可变 JSON 解释历史。
3. 候选控制/训练配置及实际证据身份。它们可以变化，但必须引用同一冻结任务及验收协议。

`tools/research/config.py:resolve` 将源任务 bundle 的 `/settling` 复制到
`/policy/controller/parameters/data/settling`；`ResearchTaskAdapter` 和
`assemble_acceptance` 读取有效快照。`task_identity=digest(task)` 单独不能区分两份
保持阈值不同的 Reach 配置；数学需求还绑定 `effective_configuration_identity`，
研究比较另保留 protocol、profile、来源和各分量 limit/unit。

候选生成中的 recipe/solver 可编辑项与 settling 分开；`design.py` 从冻结 base 配置复制，
只应用授权的 recipe/solver 改动，现有测试确认无法用 controller_recipe 修改 tolerance。
任意手工替换有效配置的 settling 仍会改变保持判据，因此未来任务应将硬保持条件放在
版本化任务规范中，而不是扩大 controller 编辑权限。这里保留 F3 的旧位置和旧解释。

## 从自然语言到独立验收

| 层 | 实际入口和输出 | 语义与边界 |
| --- | --- | --- |
| N1 草稿 | `schemas/task_intake.py`、`tools/task_intake.py:parse_response` | 原文引句、意图、时序关系、来源和缺失问题；`needs_confirmation`、`executable=false` |
| 人工审核 | Codex/研究者，对照原文、可信快照及实现 | 审核完整性、单位、时序、硬阈值、缺失物理量；不新增运行时审核系统 |
| N2 预览 | `compile_draft` | 仅 Reach/Reach+Hold、显式采用完整可信参考、原值一致时形成 draft 预览；不能批准或执行 |
| 定义准入 | `platform_tasks.check_definition` | Schema + 注册 goal/evaluator/initializer + task family 校验；定义有效不等于可执行 |
| 执行准入 | `compile_input`、controller route hook、backend checks | 检查开发状态、信号、模型、机器人、控制器和 backend；正式批准另属冻结协议 |
| 数学转换 | `ResearchTaskAdapter.analysis_requirements` | 从有效快照提取有来源的约束、网格、物理输入及任务身份；不从 objectives 猜成功阈值 |
| 数学适用性 | `research/task_constraints.py` | 按模型、信号签名、物理假设、时域、操作和约束种类声明 applicable/partial/not_applicable |
| 数学求解 | `trajectory.py`、`conic_capability.py`、`capability_sensitivity.py` | 共用局部仿射、采样、受限输入内核；不证明真实机器人成功 |
| 控制/训练 | `gvs_trajectory.py`、`sorosim_control.py`、`tools/rl/env.py` | 当前仍为 Reach 目标/保持特化；权重、预算变化不能修改正式阈值 |
| 正式结果 | 注册 evaluator + 冻结协议的 `assemble_acceptance` | Reach 组合执行完整性、求解错误、力界限、保持覆盖/位置/速度等；Tracking 完整组合协议尚未实现 |

N1 枚举 Reach、Tracking、障碍、捕获、扰动和其他意图；离线合成用例证明类别能够保留，
不能证明真实 LLM 必然分类正确。`user_explicit` 保留逐字引句；`verified_configuration`
只解引用上下文指针；推测和缺失条件只能保留问题与 null，不能成为默认参数。
单独提供 AcceptanceView 并不构成新的可信快照证明，N2 会重新投影显式 trusted_reference，
重放 N1 并核对来源。数字问题可以复用原文/可信配置出现的数字，但仍待审核。

S130 历史记录与 [S131 六项人工审核](s131_integration.md) 已区分窗口、欧氏距离、
世界速度、采样、碰撞和扰动。真实验证曾未形成可执行预览，不能用合成测试改写这一事实。
S132 注册了两种线性 Tracking 评价；本轮更新 N2 能力文字以包含 explicitly timed，
仍不自动编译圆形、任意曲线或其他新任务，不把注册能力升级成控制/backend 支持。

## Goal、Objectives、评价规则和时间

Goal 给出目标对象/参考，并不独自定义成功。`Objective` 是带方向、单位和权重的优化偏好，
不含通过阈值。硬条件来自 evaluator 及冻结协议。名称相同的“最大误差”可以同时是
优化指标和硬条件，但阈值必须取 evaluator；RMS 没有隐含硬上限。

几何 Tracking 的五项硬条件均使用 `max_error_m`；这是当前版本评价器的明确实现，
同时只是开发样例选择，不能声称研究者已批准五项共用阈值。`geometry_step_m` 是评价算法的
空间采样分辨率，应随评价版本冻结，不是控制器可随意调整的权重。两个 Tracking JSON
均为 draft/provisional，默认值不能被升级成正式新任务要求。

| 时间概念 | Reach+Hold | Untimed Tracking | Timed Tracking |
| --- | --- | --- | --- |
| 任务成功时间 | 终点 T；保持 [T-W,T] | 无逐点到达期限，也无整体完成期限 | `goal.times_s` 给定参考时间；在评分窗口逐时比较 |
| 配置 duration_s | 本协议终点/仿真长度 | 开发采集长度、数值见证时域，不是完成截止时间 | 需等于最后参考时间 |
| 数学时域 | 绝对任务网格/实际剩余时间 | 为求有限维解选择的有限时域；失败不能排除更慢完成 | 与任务时间对齐的网格 |
| 控制预测窗口 | recipe.horizon × control period，可短于剩余任务 | 后续需单独选择；不能偷加 deadline | 后续须使用实际预测节点的参考 |
| 保存时间戳 | 完整采样验证与保持窗口选择 | 用于顺序/记录；几何评价对速度、停顿、拉长时间不变 | 严格 post-step 完整时间网格；不匹配为 invalid/incomplete |

本轮给 TaskAnalysisRequirement 增加显式的
`numerical_witness_horizon_inclusive_samples` 枚举值，几何 Tracking 使用它；旧默认
`absolute_task_time_inclusive_samples` 保留，Reach/Timed 不变。现有数值网格、
duration_s 字段和历史记录不迁移；下游仍有 task_duration/remaining_task 命名，解释时需看新字段。

## 逐条件映射矩阵

完整矩阵见 [s136_task_condition_matrix.md](s136_task_condition_matrix.md)。它分别列出
每个判据的来源、物理观测、数学表达、采样范围、模型、支持状态及结论上限。

尤其要区分：`norm_bound` 对指定采样输出的欧氏范数；`path_bound` 对自由路径参数的
采样见证；以及几何评价器对保存折线的空间重采样/投影。三者不能靠相似名称视作等价。
SOCP 固定进度首尾、要求单调，并对折点样本位置枚举；这是有用的路径代理和局部动力学
可行性问题。评价器则容许最多 radius 的最近点进度回退，并从第一条 post-step 测量开始；
数学 path grid 包含 t=0。角点的近似穿过、全部折线覆盖和真实物理采样仍需独立检查。

T1 的有符号任务违反量为对可表达约束的最大归一化超限，norm 项是
`norm(y-r)/radius - 1`，component interval 用该工具声明的物理尺度归一化。
自由路径还联合优化 progress。T2 比较同一来源/拓扑/时间/约束条件下，结构参数变化后
固定绝对控制的结果与重新优化控制/进度的最优值差分及对偶 envelope。它不是对正式
accept/reject 布尔值、RMS、NMPC cost 或 PPO return 求导；数值方向也不是严格可微性证明。

## 发现分类与实际修复

| 编号 | 类别 | 发现、处理和残留范围 |
| --- | --- | --- |
| C1 | 已有接口正确 | 草稿不可执行、N2 Reach-only、注册与执行分离；保留 |
| C2 | 已有接口正确 | 目标偏好不参与 evaluator 判定；Reach 保持独立于终点；增加回归覆盖 |
| C3 | 已有接口正确 | Untimed evaluator 不检查 deadline；已有时间拉伸/暂停/逆序/捷径测试；保留 |
| D1 | 已证实的小型代码缺陷 | 几何分析只保留 path_bound，遗漏五项 evaluator 判据；在现有 unsupported_requirement 中逐项保留名称、goal/evaluator 原始数据、阈值、单位、范围和原因 |
| D2 | 语义说明缺失 | 无时间数学需求仍默认标为绝对任务时间；新增明确 horizon_semantics 值，保留旧默认 |
| D3 | 已证实的小型代码缺陷 | Timed 任务允许选择它并不输出的 path_coverage_error 目标；按时间模式校验可用 metric，几何模式仍支持 |
| D4 | 语义说明缺失 | N2 注册能力说明只写 untimed；补充 timed，同步旧描述断言，执行和编译边界不变 |
| T1 | 测试覆盖不足 | 新增 objectives 不改变硬条件、全部判据留存、数值时域与期限分开、代理可解但完整覆盖为 false、Timed metric 拒绝等 7 项测试 |
| G1 | 后续跨模块能力缺口 | Reach 完整硬条件分散于 task 和 frozen settling/protocol；新版本应迁入任务语义所有权，旧 F3 不迁移 |
| G2 | 后续跨模块能力缺口 | NMPC/RL 的输出参考、目标项和 stage mask 仍 Reach 特化；需要下节最小接口 |
| G3 | 后续跨模块能力缺口 | 研究 adapter 只接受 Reach/Tracking，robot inputs 仍是 tendon family；不能声称任意机器人/任务已经通用 |
| G4 | 后续跨模块能力缺口 | Tracking 模型构造、控制/backend、完整物理验收协议缺失；本轮保持 unsupported |

D1 保留的五项都保守标为 unsupported，含义是现有数学结果没有独立建立与保存折线
评价的等价性，不表示端点/覆盖永远不可数学表达。`geometric_path` 仍可计算，且未复制
求解器；内核自动把 retained rows 放入 unchecked_indices，full_requested_coverage=false。
这与原 full_task_supported=false 一致。覆盖行数增加和新 requirement digest 是预期变化，
旧保存结果不倒填成新输出。Reach 的约束生成、评价器、协议与冻结材料没有改变。

## NMPC/RL 最小泛化接口：后续实施规格

现状核查：`gvs_trajectory.py` 的 `dynamic_tip_tracking` 名称实际读取固定 `target_m`，
stage/terminal position cost 用固定目标，曲率速度与世界 tip speed 使用绝对速度；
holding cost 从 settling 窗口派生。`sorosim_control.py` 也把固定 target 传入 MATLAB，
`sr_nmpc_callbacks.m` 计算 `p-c.target` 和绝对速度惩罚。不能把这些名字中的 tracking
误读成 S132 路径支持。

`tools/research/rl.py` 与 `tools/rl/env.py` 显式 Reach-only。环境观测含 target-position、
绝对 tip velocity、归一化步数及上次张力；reward 是负位置平方、保持窗口绝对速度平方、
张力变化平方及数值失败处理。Direct/Residual 已有模式和参考身份校验，但 reward 仅能
调现有项的权重。修改权重、PPO 超参或训练预算不等于能增加任务语义。

后续只需沿现有模块建立以下边界，不创建第二份权威任务或庞大编译平台：

| 接口/位置 | 最小输入与输出 | 约束和验证 |
| --- | --- | --- |
| 审核任务和协议 | task/evaluator/version、稳定 condition_id、原文/配置来源、硬条件、偏好、时间模式、观测及 required_physics | 新任务将所有硬条件归任务/协议所有；旧 Reach 通过旧适配器读取冻结 settling |
| task extension 的适配 hook | 复用现有 Registry hook 机制，逐项产出 analysis_requirements、输出参考/误差及可用目标项 | 每项 condition → exact/proxy/unsupported 显式映射；未知任务直接 unsupported，不 fallback Reach |
| 模型输出绑定 | SignalSpec（实体、维度、单位、frame、phase）、输出函数/Jacobian、候选/模型身份 | 模型负责 physics，任务负责参考；不可因信号同名忽略实体和单位 |
| 参考/阶段接口 | constant、timed r(t)/可选 rdot(t)、free-progress r(s)、阶段作用域 | Timed 速度若用应为 v-rdot；Untimed 不凭空生成 r(t)、零速度目标或到达期限；事件任务无实现时拒绝 |
| 控制设计配置 | 引用冻结 task/protocol identity；目标项 ID、来源 condition、scale、weight、stage mask、硬约束、预测网格/求解参数 | Agent 在已实现项与授权范围内组合，recipe 不能编辑验收阈值；预测 horizon 与任务 deadline 分开 |
| Reward 配置 | 使用同一已声明信号/误差项与作用域，加控制平滑项、归一化、训练预算及 direct/residual 选择 | Reward 自有 identity；reward 高不等于 pass；residual baseline 必须匹配 task/candidate/channel/time |
| 执行与独立评价 | 支持能力报告、原始观测、独立 evaluator 和协议结果 | 准入逐项检查模型/控制器/backend；不支持的任务不能以已有 Reach backend 执行 |

任务特化逻辑应留在小型 adapter/evaluator，动力学和求解算法消费数值函数、约束及输入边界。
“算法任务无关”不意味着所有物理约束都能交给同一种凸优化器，也不意味着取消任务适配。
Agent 可选择/调节已验证项和方法，不能凭自由文本生成未经验证的任意 cost/reward 代码。

建议实施顺序及验收门槛：

1. 新任务条件所有权与 Registry hook：用一个非 Tracking 的新任务验证（例如有世界位置容差的
   静态保持），确认所有条件均映射或明确 unsupported，且旧 Reach 字节/验收不变。
2. 输出参考与控制目标组合：同一 NMPC 内核消费两个不同任务的合法误差项；先用合成模型
   验证，改目标权重不能改变 evaluator 结果。不能以本轮测试宣称这一阶段已完成。
3. Reward 消费同源误差、单独保存训练身份；Direct/Residual 保留现有证据和预算流程。
4. 最后补具体 robot/controller/backend 与任务组合的独立执行验收，实验需另行授权。

避障示例：新规则要求全身最小间距，不能复用 tip-position norm 代替；有距离观测但局部
模型缺相应输出时保留 unsupported。接触/捕获示例：需要对象状态、接触力、捕获事件与
保持阶段；现有仿射自由空间模型不能单凭换 goal 适配。它们说明接口可扩展的方向和真实边界。

## 离线验证与交付

环境：复用 `D:/softrobot-agent/.f3-prestudy-env/Scripts/python.exe`，没有安装依赖。
完整记录见 [validation.json](../../evidence/s136_task_contracts/validation.json)。

首轮 77 项：75 通过，一项旧描述断言失败，一项测试模块导入路径错误。
修改旧断言使其匹配新的准确能力说明，并设置 `PYTHONPATH=.;tests/research`。
仅重跑这两项，另运行两项 S131 已保存材料核验，4 项全过。
因此共有 **79 个不同测试最终通过**，不是一次 79 项完整运行。
包含 7 项新测试、Tracking/Timed evaluator、自由进度 SOCP/T2 合成模型、任务数学契约、
N1/N2 来源/审批边界以及 F3 保存验收。已有契约套件还执行本地 GVS 初始线性化诊断；
没有物理 rollout、NMPC 优化或训练。CLARABEL 的一个既有 T2 用例产生 solution may be
inaccurate 警告；测试保留其数值资格判断，不能据通过声明严格数值证书。

S134 开始时未提交的文件包含 `analysis.py`、`capability.py`、`core.py`、`evidence_views.py`、
`reporter.py`、`research_context.py`、`task_constraints.py` 与交付测试/证据。
S136 没有修改这些文件。建议先合入 S136 的生产者契约和测试，再合 S134 消费者投影；
如果反序合并，必须检查消费者是否遍历所有 unsupported rows、保留 horizon_semantics、
不从代理成功推导完整任务通过。文件无直接重叠仍存在语义集成风险。

交付前再次核对，S134 已独立提交到 `0bf514f659b6fe002f243f3d50ad11bff1daf024`，
其工作树与 S132 工作树均干净。只读比较该提交的改动清单，与 S136 文件集合无重叠；
没有合并或修改 S134。本轮没有执行两分支集成测试，以上消费者检查仍是合并验收要求。

交给 S134 的接口要求是：保留新增未覆盖条件的身份/来源和 unchecked 状态，展示数值时域
与任务期限的区别；仍使用 `full_task_supported=false`，同时区分内核 witness 和物理验收。
本轮不改其 Reporter、PATH 投影、上下文、SDK 或方法检索实现。

所有代码、测试和文档只提交到 S136 本地分支；未 push。提交 SHA 和最终 worktree 状态
以本次交付消息及 `git log -1 research/s136-task-contracts` 为准，避免在提交内容中自引用 SHA。
