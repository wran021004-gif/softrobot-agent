# P3 v1.2：正式 2-cell 自主研究启动

Task：`passive-progressive-stiffness-dev-v1-2`。Study：`p3-passive-progressive-stiffness-autonomous-20261110-v1_2`。

正式研究、Refinement、Final Evaluation 与独立 Replay 均采用 **2 cells/segment**。1 cell 仅可选筛选；4/8/12/16/32 cells 仅可选数值研究，不参与通过门槛。历史 4-cell INVALID 保留为诊断知识，不证明结构不可行。无需空间收敛。

新任务从原 v1.1 文件直接复制。双方向、material_s=0.7、五阶段载荷与时长、smoothstep、原始 dt、评分窗口、位移、恢复、渐进刚度比、同腱 slack-to-taut、张力、长度、有效配对机制及物理资格阈值均保持。版本化的确认范围为真正新执行的独立 2-cell 配对 Replay 与原始 CSV 状态复核；半时间步和初态扰动不再是强制条件。原版本默认确认范围及序列化保持不变。

原 P3 FamilySpace：2–6 段、2–4 腱。所有真实注册有效参数通过 `*` 参数发现开放，包含段长、材料、截面、路由、导向、相位、payout；自然曲率仅依实际模型注册能力。Baseline 无默认消融，Coordinate 和 Coupled Block 均可真实准入。Main 自选理论、结构、数学、搜索与动态范围，未提供历史成功 seed 或预置首轮研究 Plan。

Knowledge Manifest 见 [knowledge-manifest.json](knowledge-manifest.json)。包含用户指定的 `p3-case@3`、mechanics、routing、material/inertia、三类 diagnostic、qualification/replay、六项研究 Skill 及两个 research process。禁止 benchmark answers，不携带旧候选、XML 或重建答案。

Main 与 Reporter 共用 **80 次实际发送请求**，无角色子预算、隐藏额外额度或自动追加。数学评价/方法、累计时间、物理、积分步、候选、搜索、配对和 Replay 无累计上限，适用额度为 null；单次请求努力与 Worker watchdog 保留。80 次耗尽时由现有 request-feedback supervisor 在结算边界暂停，不作为科学失败。

[preflight.json](preflight.json) 记录十二类必要启动检查：真实任务解析、2-cell 编译和 Worker/Evaluator 准入、正式 Fidelity、无高精度前置、物理目标逐字段一致、P3 设计域、参数工具发现、搜索准入、完整 Knowledge、80 次请求、累计 unlimited、独立 Store。预检禁止 Provider 和积分，未构建高精度模型，未重跑此前十二项架构测试。仅新增两个合成 fixture 检查确认范围及真实独立执行路径，不是物理成功证据。

代码与配置先本地提交，再创建 Store。为避免 Git 提交哈希自引用，启动脚本从已提交配置生成同目录忽略的启动叶配置，仅将 `base_commit` 固定为当时真实完整 HEAD；不保留字符串 HEAD。冻结实现与任务身份见 [launch-receipt.json](launch-receipt.json)。旧 Study 的状态摘要和完整账本在预检与启动后只读核对，未迁移或重置。此次不 Push。

实际启动状态、首份 Main Plan 与成本将在启动后据原 Store 更新。Study 创建、Main 启动、Plan 提交、Worker 执行、发现可行候选与正式通过分别记录，不能相互替代。
