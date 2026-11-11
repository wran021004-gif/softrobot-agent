# P3 三组系统消融准备

仅为权限实现、配置和离线验证交付。历史 Full 已完成，直接复用，不重新创建或运行 Full。本轮没有新的候选、响应曲线或消融实验结果。

Research 基线：`6a1e8ea21ee454b9f693361f460f2decb259f78e`；配置分支：`codex/p3-ablation-configs-20261112`。Core 从 `78e1c8535597f67c365f6a94b4a522a58d5a1e52` 建立 [P3 开关分支](https://github.com/wran021004-gif/softrobot-agent-core/tree/codex/p3-ablation-gates-20261112)，实施说明见该分支的 `docs/p3-ablation-gates-20261112.md`。

## 独立实验定义

| 能力 | No-Math-Analysis | No-Knowledge | No-Interact |
|---|---|---|---|
| 可选 mechanism_structure_v1 | OFF，五种 operation 均拒绝 | ON | ON |
| inspect / differentiate / optimize / compare | OFF | ON | ON |
| interact 四点交互 | OFF | ON | OFF |
| Main 和 Reporter Knowledge/Skill | 沿用 Full policy | OFF，含缓存/预载检索入口 | 沿用 Full policy |
| 普通生成、FamilySearch | ON | ON | ON |
| 完整被动物理响应及原指标评价 | ON | ON | ON |
| 原 Task / FamilySpace / Runtime / System Prompt | 保留 | 保留 | 保留 |

No-Math 用 `mathematical_methods.mechanism_structure_v1=null`；No-Knowledge 仅将原 Knowledge policy 的 `mode` 设为 `off`；No-Interact 增加 `mechanism_operations=[inspect,differentiate,optimize,compare]`。没有同时关闭三项能力。其他组不改变数学 operation 或 Knowledge 权限。

当前 FamilySearch 的 Coupled Block 包装器实质上调用 `MechanismStudy.operation=interact`，不能绕过相同门禁；不是已查明的另一种独立耦合优化能力。保留 `family_search.coupled_block_enabled=true`，No-Interact 仍可做普通坐标搜索、联合参数修改和非 interact 分析。没有把标志关闭当成本次消融。

## 三配置、身份和 Store 隔离

| 文件（相对 configs/research/） | Study ID |
|---|---|
| [study_p3_ablation_no_math_v1.json](../../configs/research/study_p3_ablation_no_math_v1.json) | `p3-ablation-no-math-20261112` |
| [study_p3_ablation_no_knowledge_v1.json](../../configs/research/study_p3_ablation_no_knowledge_v1.json) | `p3-ablation-no-knowledge-20261112` |
| [study_p3_ablation_no_interact_v1.json](../../configs/research/study_p3_ablation_no_interact_v1.json) | `p3-ablation-no-interact-20261112` |

文件与原 Full 同目录，继续解析原 defaults、`family_space_p3_passive_v2.json`、`runtime_phs2d_topology_successor_20261106.json` 及原 TaskDefinition。三份配置的 `base_commit` 均绑定本次新 Core 提交 `9a8a1fd3feee5d966a5981dd965c2a2ec5c681d5`，不使用字符串 HEAD。

每份 `evidence_destination` 为 `runs/research/<该 Study ID>/private-evidence`。将来启动时使用既有默认独立 Store 路径 `DATA_HOME/runs/research/<该 Study ID>/platform.sqlite`，或在单独授权中明确同样分离的目录；不增加不存在的 Store JSON 字段。本轮不调用 prepare，未创建这些 Store 或任何 Study。

所有新组均从空科学候选池、`agent_choice`、零自由度初始化规则开始。没有 fixed_structure_reference、历史候选、控制或 Store 导入；不向 Main 提供历史成功结构。以下历史基准只用于论文比较，本计划和结果报告不作为 supplied_evidence 或 Knowledge 注入 Main。

## 共同物理范围和数值交付

保留 `passive_progressive_stiffness_dev_v1_2` 的 +X/−X、20 s 五阶段：无载、0.05 N、0.10 N、0.20 N、卸载恢复，各 4 s。步长 0.000125 s、记录周期 0.01 s、阶段末 0.25 s 评分窗、材料观察位置 s=0.7、原低/高位移、恢复、刚度比、接触和同腱约束定义均不修改。

低载位移 ≥6 mm、高载位移 ≤25 mm、恢复残差 ≤2 mm、渐进刚度比 ≥1.5；Middle 为原机制记录点。最终最佳候选必须报告双方向完整数值和实际违反量；缺测为 UNKNOWN。违反原阈值不能称为数值可行，更不能将有限预算未通过说成设计域无解。

最终最佳响应使用原 `final_evaluation` 的每段 2 cells；可选筛选精度不替代这个数值模型口径，不追加其他网格或收敛要求。

本次是数值研究比较，不追加 fresh validation_source Replay、半步长、初态扰动、成功后重复检查、成对腱因果证明或正式 SELECT 认证。TaskDefinition 和 Evaluator 自身仍保持原语义，不把未取得正式认证改写成 certified pass。

为避免 No-Math 连带关闭搜索，有限物理预算下的普通 FamilySearch `passive_task_response` 复用现有物理响应执行入口，三个组采用同一路径；完整两方向、五阶段，不接受 execution_profile 覆盖。该路径按原诊断约束的违反量排序，保留接触和腱检查，排除本轮未要求的 paired mechanism proof，明确不授予正式 acceptance。它不调用可选机制数学 Worker。静态 equilibrium 诊断仍属于 No-Math 禁用范围。

## 历史 Full 比较基准

Study：`p3-passive-progressive-stiffness-autonomous-20261110-v1_2`，最佳候选 `candidate_2915`。只复用 [P3 Full 整理](../full_results/P3_full_results.md)，不重跑、也不作为新组初始候选。

| 指标 | 历史 +X | 历史 −X |
|---|---:|---:|
| Low displacement | 6.01794 mm | 6.01794 mm |
| Middle displacement | 11.11727 mm | 11.11727 mm |
| High displacement | 17.75103 mm | 17.75103 mm |
| Recovery residual | 0.001246 mm | 0.001246 mm |
| Progressive stiffness ratio | 1.537391 | 1.537391 |
| Contact | 0 | 0 |

历史成本：Provider 150、数学评价 67、物理 episodes 98、物理 steps 15,680,000。完整 Token/美元费用 UNKNOWN，不作估算。已有可行数值设计、同腱 slack-to-taut 关联与尚未证明唯一因果的边界沿用原报告。

新组除最终指标/违反量，还应报告 Provider、实际数学评价、物理 episodes/steps、提案与有效候选数、失败与 UNKNOWN、停止原因及实际 Token（如原收据可得）。新的低预算、Core 版本和知识资产与历史 Full 有差异，不能把差异自动归因于单个被消融能力，也不做跨任务效率排名。

## 统一预算和合同说明

| 额度 | No-Math | No-Knowledge | No-Interact |
|---|---:|---:|---:|
| Provider requests | 48 | 48 | 48 |
| Protected Provider requests | 4 | 4 | 4 |
| Mathematical evaluations | 0 | 24 | 24 |
| Physical launches | 32 | 32 | 32 |
| 每次 FamilySearch proposals | 24 | 24 | 24 |
| 每次 FamilySearch evaluations | 16 | 16 | 16 |
| Public operations | 160 | 160 | 160 |

所有执行计数上限有限且不自动追加，不要求用完。将原 `request_budget_only=true` 改为 false，否则数学/物理计数仍只记录而不限制，不能满足低预算 Pilot。未使用的 local/offline/BDF/NMPC/RL 计数为 0。

`family_search.max_proposals/max_evaluations` 的现有合同是**每次搜索请求**硬上限，不是 Study 累计 24/16；本轮不伪造累计预算字段。共享 Provider/公共操作/物理额度仍限制整个 Study。

`physical_launches=32` 限制登记的 backend episode。普通完整双方向响应占 2，因此最多 16 次此类新响应，并与其他物理请求共享。可选数学分析内部的积分轨迹由其数学计数控制，不能声称本配置给全 Study 所有物理轨迹统一加了 32 的总上限。各组均须分别报告实际 episode/steps。

旧 count-mode 的 numerical_s/activity_s/local_solve_s/delivery_reserve_s 等时间字段仍为 null，表示未设累计时间额度，不是未限制执行次数；保留有限的单 Worker watchdog。没有新增虚构时间预算。

## Knowledge 迁移差异

No-Math/No-Interact 的 Knowledge policy 与原 Full 一致，No-Knowledge 只改 `mode=off`，并阻断 Main、Reporter、Reporter 缓存及条目预载。基础系统、任务与工具契约保留。

但**实际资产不等同于历史 Full**：历史启动 Knowledge manifest 有 45 条记录、17 个 entry ID；指定独立 Core 基线只解析到 4 条通用条目（general-material-inertia、skill-parameter-model、skill-matched-comparison、skill-finite-search），No-Knowledge 为 0。此次没有越过权限开发范围迁移历史领域知识包，也未把缺失项伪称为已加载。

因此 No-Knowledge Pilot 当前测的是此 Core 的实际 4→0 通道。若论文要声称移除历史 Full 的完整领域知识，需要先明确知识资产对齐方案；不能通过本轮禁止的重跑 Full 或偷偷注入成功结构来补齐。其他组同样记录版本/知识迁移差异。

## 验证、Pilot 顺序与未纳入实验

三配置已真实解析；11 项 P3 定向离线 Mock 测试通过，另有 9 项既有 M1 门禁回归通过。验证了方法/operation 的原始入口拒绝、Schema/发现列表、No-Knowledge 双角色及缓存隔离、No-Math 的 Main 搜索入口和物理准入、Coupled 包装器、共同任务/模型一致性和 Full 文件未改。测试阻止网络、子进程和 MuJoCo；没有新科学结果。

后续建议顺序：

1. 用户授权后先做 **No-Math**，检验必要物理搜索链路和低预算研究行为；只报告该组实际结果，不创建新 Full。
2. 单独授权 **No-Interact**，保持其他机制操作和普通搜索，检查移除实际四点交互后的路径变化。
3. 明确上述 Knowledge 比较口径后，单独授权 **No-Knowledge**；不将其与其他两开关同时关闭。

每组启动前绑定精确 Core SHA、新 Study 身份及独立 Store，并确认无历史候选注入。配置的 OFFLINE_PREPARATION_ONLY 说明不是执行授权；本轮不进入步骤 1。

**No-Inspect** 和 **Reporter 小实验**尚未纳入：当前 No-Math 已包含 inspect 移除，No-Interact 只移除实际交互；Reporter 继续解释工具结果，No-Knowledge 仅关闭其领域知识输入。未来若另行研究需单独定义，不能将本次结果代称这些消融。
