# P3 v1.2：正式 2-cell 自主研究启动

Task：`passive-progressive-stiffness-dev-v1-2`。Study：`p3-passive-progressive-stiffness-autonomous-20261110-v1_2`。

正式研究、Refinement、Final Evaluation 与独立 Replay 均采用 **2 cells/segment**。1 cell 仅可选筛选；4/8/12/16/32 cells 仅可选数值研究，不参与通过门槛。历史 4-cell INVALID 保留为诊断知识，不证明结构不可行。无需空间收敛。

新任务从原 v1.1 文件直接复制。双方向、material_s=0.7、五阶段载荷与时长、smoothstep、原始 dt、评分窗口、位移、恢复、渐进刚度比、同腱 slack-to-taut、张力、长度、有效配对机制及物理资格阈值均保持。版本化的确认范围为真正新执行的独立 2-cell 配对 Replay 与原始 CSV 状态复核；半时间步和初态扰动不再是强制条件。原版本默认确认范围及序列化保持不变。

原 P3 FamilySpace：2–6 段、2–4 腱。所有真实注册有效参数通过 `*` 参数发现开放，包含段长、材料、截面、路由、导向、相位、payout；自然曲率仅依实际模型注册能力。Baseline 无默认消融，Coordinate 和 Coupled Block 均可真实准入。Main 自选理论、结构、数学、搜索与动态范围，未提供历史成功 seed 或预置首轮研究 Plan。

Knowledge Manifest 见 [knowledge-manifest.json](knowledge-manifest.json)。包含用户指定的 `p3-case@3`、mechanics、routing、material/inertia、三类 diagnostic、qualification/replay、六项研究 Skill 及两个 research process。禁止 benchmark answers，不携带旧候选、XML 或重建答案。

Main 与 Reporter 共用 **80 次实际发送请求**，无角色子预算、隐藏额外额度或自动追加。数学评价/方法、累计时间、物理、积分步、候选、搜索、配对和 Replay 无累计上限，适用额度为 null；单次请求努力与 Worker watchdog 保留。80 次耗尽时由现有 request-feedback supervisor 在结算边界暂停，不作为科学失败。

[preflight.json](preflight.json) 记录十二类必要启动检查：真实任务解析、2-cell 编译和 Worker/Evaluator 准入、正式 Fidelity、无高精度前置、物理目标逐字段一致、P3 设计域、参数工具发现、搜索准入、完整 Knowledge、80 次请求、累计 unlimited、独立 Store。预检禁止 Provider 和积分，未构建高精度模型，未重跑此前十二项架构测试。仅新增两个合成 fixture 检查确认范围及真实独立执行路径，不是物理成功证据。

代码与配置先本地提交，再创建 Store。为避免 Git 提交哈希自引用，启动脚本从已提交配置生成同目录忽略的启动叶配置，仅将 `base_commit` 固定为当时真实完整 HEAD；不保留字符串 HEAD。冻结实现与任务身份见 [launch-receipt.json](launch-receipt.json)。旧 Study 的状态摘要和完整账本在预检与启动后只读核对，未迁移或重置。此次不 Push。

## 实际启动记录

冻结执行 HEAD 与 `base_commit` 均为 **`4245e5a4501e6ee915877ab0b80892e4a799bf7a`**；代码、任务与启动工具提交为 `7d74577773eaf2cd712e8dd963d08ccf4af82559`，其后仅将已审查的实现哈希固定到版本化配置，再以当时真实完整 HEAD 创建冻结启动配置。后续报告提交不迁移正在运行的实现。

2026-11-10 18:24:02 +08:00 的启动快照见 [live-status.json](live-status.json)。后台进程已正式运行，以真实 Main 组织研究，80 次初始额度用尽后在现有 request-feedback 结算边界暂停；未自动追加。下表描述启动快照，不是最终研究结果。

| 状态 | 已核实事实 |
|---|---|
| Study 已创建 | 独立 `runs/research/p3-passive-progressive-stiffness-autonomous-20261110-v1_2/platform.sqlite`；初始候选、Plan、成本及 Provider 使用均为零 |
| Main 已启动 | 已有真实 Provider 请求；与 Reporter 共用同一 80 次账本 |
| Main 已提交 Plan | 两份 Plan；首份为 Main 自主生成三段、四腱对称 slack-to-taut 假设，并生成一个新候选 |
| Worker 已执行 | 已完成一次真实 `mechanism_structure_v1` 数学 Worker，状态 computed：卸载平衡与活动约束检查 |
| 找到可行候选 | 尚未证实；当前仅为研究候选 |
| 通过正式验收 | 否；未完成完整动态任务、有效机制及独立 Replay 验收 |

首份完整 Plan 见 [first-main-plan.json](first-main-plan.json)。该 Plan 由真实 Main 返回并登记，启动脚本未编写其假设、参数选择或执行顺序。Main 在此前已真实读取 `passive-structure-mechanics@1`、`mechanism-research-process@2`、`skill-parameter-model@4`，其他已冻结条目继续由 Main 按需检索读取。

| 实际成本（同一启动快照） | 数值 |
|---|---:|
| Provider 已记账请求 | 7 / 80，剩余 73；当时 1 个请求进行中 |
| 已完成数学评价 / Worker 结果 | 1 / 1 |
| 卸载平衡求解 / native model build | 1 / 1 |
| native forward / 约束 Jacobian 提取 | 28 / 26 |
| 物理积分步 / 动态 rollout | 0 / 0 |
| 正式物理 Replay 结果 / 案例 | 0 / 0 |
| 已结算研究数值时间（含构造） | 1.670472 s |

原 Store 保留逐请求、数学和物理成本；上表不把正在执行或尚未结算的工作记作零成本。Provider 美元价格未提供，不能捏造金额。后续研究继续写入新 Store；此处仅记录启动状态，不将数学结果或生成候选当作任务成功。旧 Study 状态与完整账本再次核对未变。

第 28 次请求的工具 Schema 中断及用户授权的原 Study 恢复，见 [schema-recovery.md](schema-recovery.md)。原启动快照不覆盖后续运行状态。

35 次请求后的通用状态包重复展开与容量错误修复，见 [context-recovery.md](context-recovery.md)。
