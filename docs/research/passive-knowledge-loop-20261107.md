# Knowledge 读取、被动初始资格与一次真实科研闭环验收

2026-11-07。基线 `87b469909`；沿用 `codex/passive-research-capabilities-20261107`。

代码开发和必要离线验证完成。唯一一次真实会话严格用完 12 次共享请求，但**没有形成 Reporter 反馈后的正式下一轮 Plan，因此科研闭环未通过**。不追加请求，不以维护者代写 Plan 补足验收。

## 1. 移除了哪些 SHA 门禁

`experience.freeze_knowledge()` 不再生成 typed Knowledge 的 `content_sha256` 或 compact Skill 的 `source_sha256`。`retrieve()` 删除重新计算正文哈希、比较和 `FROZEN_KNOWLEDGE_CONTENT_CHANGED` 拒读；同时移除该模块的 hashlib、正文 receipt 哈希和 disposition 中的对应字段。没有增加大小、时间戳、Git 或其他替代读取门禁。

继续由当前 Study 的冻结 manifest 授权 `entry_id`、`revision`、`content_key` 和资源范围。旧 manifest 内已有哈希字段可以留在历史数据中，但不参与拒读。架构说明已更新。知识链路检索未发现其他基于正文 SHA 拒读的机制；历史档案来源哈希不删除。

## 2. 保留的身份与证据机制

候选、配置、数值模型、Task、科学问题、Store artifact、Evidence、原有缓存和 provenance digest 均保留。原有实现冻结、授权和只读证据范围继续生效，没有增加白名单。Evidence 分页 continuation 的身份检查属于原有证据导航，未当作 Knowledge 正文门禁移除。历史成功设计仍不在新 manifest 授权范围，也未导入新 Store。

## 3. 初始资格如何工作

在现有 `passive_equilibrium.solve()` 入口，使用实际编译模型和该求解声明的正式初态，调用一次 `mj_fwdPosition`。预检不调用 `mj_forward` 或 `mj_step`，不重复实现腱路公式，不改变 payout、自然曲率或初始 qpos。

接触检查保存实际 body 位姿、接触对象、距离和位置。MuJoCo 的碰撞掩码、父子过滤和排除规则仍由模型执行；非负距离的 margin 接触不自动判非法。当前注册物理问题为 `contact_mode=none`，原生启用接触对的负距离按该无接触条件判失败，不增加穿透阈值。排除对不被声称已独立证明无重叠，预检通过仅覆盖已声明的初始几何范围。

每根腱读取实际 `ten_length`、固定 payout 和 `g=ell-L`，沿用原有 `length_tolerance_m` 与 `active_tolerance_m`。几何 boundary/slack 不等同实际张力。对解除限制的腱不强加该长度约束。

`failed` 只拦截明确违反；`indeterminate` 保留警告并继续原路径。失败返回正式 `preflight_failed` 数学结果，优化器、完整 forward、有限差分 Hessian 和 KKT 均未进入。`worker.started=true` 表示 Python Worker 已运行；另以 `numerical_solver_started`、`full_forward_entered` 和 `optimizer_entered` 明确数值阶段。

## 4. 是否到达 Reporter 和 Main

是。预检由原数学结果中的 `initial_qualification` 保存，现有诊断和反馈只作按需投影，不注册新工具、Store、Evidence 类型或诊断事件。保留外层候选引用、模型身份、单位、依据、预检成本与 `task_acceptance=unmeasured`。大体位姿/接触表留在原结果，Main 摘要不重复注入。

离线 C 回归使用新 fixture Store，经原生成器、实际 Worker、结果结算及 Reporter `_wire`：保存 `preflight_failed`，Main 数学反馈含资格状态，Reporter 收到预检和当前结果 source catalog，真实 Provider 消耗为 0。

真实会话中，Main 和 Reporter 都收到预检通过、数值求解、静力资格与成本；Reporter 使用当前结果来源解释。预检通过和整体几何认证不同：原有 aggregate geometry layer 仍显示 `not_evaluated`，预检自身准确显示 `passed`。不能将这个更宽的 layer 状态误读为预检未执行。

预检通过后仍可能发生原生 forward 失败。资格专用路径保存两个事实；最终补充了原 Worker 通用异常序列化路径，保存异常携带的资格诊断，防止非资格专用请求丢失已通过的预检。该异常分支只做离线验证，未重跑真实会话。

## 5. 是否避免旧 C 的 Hessian 失败入口

旧 C 私有 request 仅作只读回归，没有改写旧 Store。实际模型仍记录 172 个接触、最深距离约 −0.567 m、四根腱约 +0.808 m 长度超限。新 Worker 保存预检失败，完整 native forward、优化器迭代和项目 Hessian 列数均为 0。它没有证明别处不存在合格平衡，也没有证明这些几何现象是原生矩阵秩缺陷的唯一原因。

真实新候选预检通过，因而正常进入数学求解；本次实际有 707 次 native forward 和 144 个项目 Hessian 列，均为静态计算，physics steps/rollouts 为 0。

## 6–10. 真实 Agent 五项能力

全新 Study：`passive-knowledge-loop-20261107`。配置基于开放被动接口审查配置、原 Base-only FamilySpace 和最新 typed manifest。没有旧 C 候选池、历史决策、成功结构初值或旧 8 次请求预算。

真实运行绑定 `32bc8d661adcf2f585529c0fd30fd221205f7621`，该提交保持可达。之前两个启动错误都在发送前发生，累计请求仍为 0：线程环境未设置，以及开放域 Schema 的 `enum:null` 问题。设置既有线程变量并修复 Schema 后，在同一 Study 记录实施迁移和授权，没有重置计数或建立第二个真实会话。

| 能力 | 判定 | 实际证据与限制 |
|---|---|---|
| PHS 案例理解 | partial | Main 自主发现并完整读取 `phs2d-case@2` 的 12 节 Action Trace；SDK 确认正文交付。Plan 区分历史背景、当前证据、单侧松弛和静力/动态范围。但没有公开逐项解释历史关键失败分支、转向和后验归因，因此不能只凭读取判完全理解。 |
| 新可证伪假设 | passed | 新的对称四腱分布假设预测反向载荷交换延伸侧活动腱并产生恢复响应；列出路长灵敏度过小、非正曲率等削弱条件，并以梁/连接件几何单独造成局部化为竞争解释。保存在生成和诊断 Plan 中。假设形成不等于得到验证。 |
| 被动数学入口 | passed | 自主生成新的合法三段四腱 Base-only 候选，保存 diagnose，提交 `scientific_question_v4`，选择 routing 组的 `constraint_length_jacobian` norm inspect。没有指定底层求解器、差分步长或逐参数内核调用。 |
| Reporter 解释 | passed | 真实 Reporter 引用当前数学结果，以及实际交付的 `general-equilibrium@1`。区分预检、局部平衡、退化、失败多初值分支和动态未知；没有全局不可行或任务成功主张。 |
| Reporter 后正式下一轮 Plan | failed | Store 仅有两个 Plan，均在数学结果和 Reporter 之前。Reporter 后 Main 选择 diagnose 路由，后续两个请求已进入只允许既有 STOP/SELECT 的收尾阶段，用于读取结果索引、机会页及结果导航，未保存下一轮 Plan。 |

Main 第一轮按非标准 task 标签检索未命中，随后自行改为类别检索。其完整读取包括 Case、General routing/equilibrium，以及 Diagnostic slack/local-finite/static-dynamic。没有索取历史成功结构精确参数。新假设涉及反向载荷交换、局部化和恢复机制，单次正向静态 Jacobian norm 不能验证全部预测。

一次数学评估实际求解 unloaded 与 `s3_positive` 两个平衡。新候选初态预检通过；unloaded 的两个开始点中，一个为合格局部极小值，另一个数值收敛但二阶资格失败。unloaded 的 LICQ/严格互补性失败仍明确保留；loaded 的工作点合格且正则。结果没有完整任务验收资格。

Reporter 实际收到 `general-equilibrium@1` 和 `general-sensitivity@1`：前者复用 Main 的完整 read receipt，后者为必要补充读取。`knowledge_refs` 只填写前者；科学 `sources` 指向本 Study 的数学结果 `/structure_research`、`/scoped_claim`、`/task_analysis`。知识 receipt 不作为当前科学 source。Reporter 解释保存且在后续三个 Main 请求中交付，但不能据此宣称 Main 已形成反馈后的决策。

## 11. 实际预算

离线先核对 `last_requests_v2`：总额 12，收尾 2 包含于总额；初始 science-capable capacity 10，剩余 2 时为 closeout 且 science-capable 为 0。Main 与 Reporter 均经原 LiveBoundary 按每次请求扣同一 Store 的 `model_calls`。

| 项目 | 实际 |
|---|---:|
| 合计真实请求 | 12/12 |
| Main | 11（普通阶段 9，收尾阶段 2） |
| Reporter | 1 |
| 扩额 / 第二个真实 Study | 0 / 0 |
| 数学 Worker 评估 | 1/2 |
| 内部 equilibrium solves / model builds | 2 / 1 |
| 物理 timestep / rollout / Replay / 完整十工况 | 全部 0 |
| BDF / NMPC / RL | 全部 0 |
| 未结算 Provider / pending science | 均无 |

实际未达到“普通阶段优先 Main≤8”的建议分配，仍严格遵守共享 12 次硬上限及额度内两次收尾。输入/输出 token：Main 377266/4668，Reporter 10580/1027，总 token 393541；金额未知。数学结算约 1.284 s；总 ledger wall 还包含 Provider 活动，不应当作纯物理计算时间。

## 12. 必要测试与提交

13 项不同的针对性检查通过：组织知识 4 项、旧 manifest/compact Skill 2 项、初始资格 5 项、开放域工具 Schema 1 项、主动原生两尺度兼容 1 项。对失败的测试选择/fixture 细节作了修正后仅重跑受影响检查，没有运行全套、大搜索或十工况。

初始资格检查涵盖合法状态真实小模型求解、通过后 forward 失败及 Worker 序列化、位置数据不足继续原路径、明确腱长失败不调用 full forward、原 C 实际模型与 Store→Main/Reporter 反馈、现有摘要来源投影。组织知识检查含 Case/General/Skill 分别读取、L0 不注正文、隔离及 Reporter 引用。`git diff --check` 通过。

由于补充了共享 Worker 的被动异常序列化，执行了一次既有主动兼容回归：5 个原生模型、16 次 forward、5 次 mechanics evaluations、0 timestep，另一个真实 actuator 模型编译为 nu=4。数值通路可用；两尺度灵敏度仍为低信号、相反符号，`derivative_status=unreliable`，不宣称梯度科学验证通过。输出写入新的 `runs/stage2_validation/knowledge_loop_20261107/`，保留此前主动回归资产。

提交保留全部既有历史：

- `d3c9ca817` — 移除 Knowledge/Skill 运行时内容哈希门禁。
- `9145cbc3e` — 初始资格、反馈投影、receipt 复用及单次会话配置/入口。
- `32bc8d661` — 修复开放计数/连续域工具 Schema 的 null 限制；真实运行冻结点。
- `6fbf829db` — 保留 Worker 异常中的初始资格及原始真实会话审计。
- 最终独立交付提交 `test(agent): validate knowledge-to-plan research loop` 保存能力判定、主动回归摘要、最终来源检查和本报告；正常推送同一功能分支。

审计资产位于 `evidence/passive_knowledge_loop_20261107/`：`budget_check.json`、`audit.json`、`assessment.json`、`active_regression.json`。仅导出本次代码、测试、脱敏知识相关的审计与报告，不提交凭据、Study Store 或历史成功设计。真实运行后新增的通用异常保留分支仅有离线验证，未冒称在唯一真实会话中触发。
