# P6.3-B2 G / M：sol 实际小测试

用户明确要求开始 G、M，先使用 sol。两项沿用 B2 已审查的预算与起点定义，独立分支 `codex/p6-3b2-sol-gm-tests`，不修改历史 Study。正式配置为 `study_p63b2_g_sol_live.json`、`study_p63b2_m_sol_live.json`；基线 `11d5f28a8fdb9962f4f7fe502084ac41c7cbdad0`。[零起点预检](p63b2_gm_sol_preflight.json) 记录两份准确 identity、预算与知识权限。模型目录非推理 GET 返回 200，准确 sol 可用；没有额外 smoke 推理。

首次启动前 guard(expensive=True) 复现 `PROTECTED_CLOSEOUT_REQUIRES_EXISTING_WORK_OR_STOP`：G 的零计算额度使 science_fits=False，故未发送任何模型请求。B2 的 resolver 检查未覆盖这个准入阻断。本轮仅在原 budget.science_fits 增加纯生成情形：FamilySpace、capabilities 为空、动作仅 generate/stop、尚无候选时允许进入原流程；取得合法候选后仍进入收尾，Provider/Public 保护额度不变，不增加任何数学/物理权限。新增一项离线准入测试通过（1.030s），覆盖零计算可生成、Provider 保护仍生效、取得候选即收尾、普通科学 Study 不受该分支影响。保留失败预检记录，并在干净提交后通过原 bind/migrate 更新实现绑定，不重置预算或删除原记录。

M 起点只按既定请求（2 段、4 腱、其余继承）调用一次原 generate_candidate，来源标记 Operator、未经任务评价，不自动搜索或修复。G 不提供候选。两项都使用原 formal_study_authorization 和相同 sol 的 request-feedback Handoff 准入；Knowledge-enabled、九项 success_case 可读、P3 原始中文。独立物理、NMPC、RL、Offline NLP/BDF 均为 0。所有失败请求仍计入各自总额，没有新的豁免。

## 结果与来源

两项均已用完原窗口并停止，**20 次 Provider 请求全部 HTTP 200**，未切换模型、续窗或追加预算。执行绑定为 `96d2e6cb16d99df7aa9f5c2e33fb2e140ea15fc7`。实际请求、工具输入、业务结果、原始引用、关键 L0/Schema、归属和计账见 [真实审查 JSON](p63b2_gm_sol_audit.json)；原始 Store 留在本 worktree 的 `runs/research/<study_id>`，不提交凭据、完整 Store、Knowledge 正文或 Provider opaque output。

| 项目 | G | M |
| --- | --- | --- |
| Study | p63b2-g-sol-20261029 | p63b2-m-sol-20261029 |
| Resolved identity | f2b0520dfc78bcf9390251c8d62873e945a97b8a745f36f32d3424a22561c085 | f1d56444714532389b4c2507273740b1e1c8f9503881ac7e7e765b90a3cc54b7 |
| Provider / Public | 8/8；8/16 | 12/12；22/32 |
| 合法候选 | 1，Main 自主生成 | 1，Operator 提供；Main 未生成修订 |
| 科研 Plan | 1 次 generate | 0；仅 route(diagnose)，未提交 diagnose |
| 数学 / Reporter | 0/0；0 次 Reporter | 数学 0/4；0 次 Reporter |
| 原生 STOP / SELECT | 无 / 无 | 无 / 无 |

两项剩余 Provider 均为 0，无未结算 Provider 或科学执行，无后台 Worker。原始 research_status 仍为 ready，最终是既有 supervisor_pause，不能把外部窗口暂停写成 Main 科学 STOP。没有独立物理评价，任务成功未测量。

## G：合法生成观察通过，收尾未通过

| 请求 | 实际动作 | 结果 |
| --- | --- | --- |
| 1 | search reach_and_hold, limit=5 | 成功 |
| 2 | read research-bounded-continuation@2 | 成功 |
| 3 | 搜索 kind=success_trace、reach 等过滤 | 成功返回空集；未读成功案例正文 |
| 4 | search reach_and_hold, limit=9 | 成功 |
| 5 | 直接 research_plan(generate) | 合法生成当前自有候选 |
| 6 | working_set /all_fresh_results，使用 L0 广告的候选引用 | 保护期 Schema 拒绝 TOOL_SCHEMA_ENUM |
| 7 | 尝试 full 读取先前允许的边界引用 | 已过期于下一次 Handoff 的枚举，再次 TOOL_SCHEMA_ENUM |
| 8 | full 读取上次错误回执的 /result | 返回原错误内容；未完成索引阅读或 STOP，额度用完 |

Main 自选两段、四腱、从第 0 段到第 1 段的等间隔全跨度路由。它的实际请求省略 sections、cells 和未改动的其余设计变量，继承原域默认，首个生成尝试即成功；没有 Codex 补交或自动修复。候选引用 `280f8e2680c447392a178807505b8353ac0edf981459ebe7692bd82b01563afc`，来源为本次 Main 的原 Plan/工具调用，未借用 M 或历史 Study 的所有权。Main 明确把有效性/所有权与可达、保持、任务接受、硬件性能及最优性分开，未作通过声明。

这提供了 B2 稀疏生成接口在真实 Main 上可用的观察：直接提交、默认继承、合法候选均成立。它不证明任务可行，单轮观察也不能证明所有重复读取问题消失。G 的完整原生收尾仍失败，不能把整条工具闭环标为通过。

## M：合法起点仍未转化为数学执行

Operator 仅构建一次默认两段四腱候选：`95fbd0b088bed2a28d760a05ddf2dd248e2e72a8ee4a813bdb1f0325ceff0a3b`。准备记录 `7a8688c96838c0288739e9cf0411214fbb1945b460423402ceb6047fbe45d41f` 保存原请求、结果和授权。无搜索、无控制轨迹导入、无任务或数学评价。该候选不记作 Agent 原创；G 的候选来自另一独立 Store，归属不得合并。

首个真实 M L0 已显示该候选及 candidate_mathematical_research_v1：39 项注册参数，12 项获准有效连续参数，类别 geometry/routing/segment；terminal_error_m、holding_max_error_m、holding_max_speed_m_s、best_found_J 等任务量。fixed_input_structure_v1 为 ready；T1 仍 requires_parameters，缺少控制 source/settings 等前提；T2 保持其原来源要求。这里的 ready 只是规划状态，不替代执行准入。真实入口可见，没有 Main 被迫先造结构的问题。

| 请求 | Main 实际动作 | 结果 |
| --- | --- | --- |
| 1 | 搜索经验；读候选索引和 methods | 成功，方法大对象返回导航 |
| 2 | 把搜索回执 artifact ID 当成 Knowledge entry_id 精确读取 | EXACT_EXPERIENCE_READ_REQUIRES_ONE_ENTRY_AND_REVISION |
| 3 | 正确读取 procedure；重复候选/methods，读 research_opportunities | 成功，仍是导航 |
| 4 | 读 fixed_input_structure_v1 的机会状态 | 返回 ready、成本与方法查询入口 |
| 5 | 搜索、读该方法详情、再读候选 | 成功，详情被截为导航 |
| 6 | 重复读取同一 procedure | 成功 |
| 7 | 重复读取该方法详情 | 同一导航 |
| 8 | 按方法描述搜索 Knowledge | 空集及原恢复提示 |
| 9 | 重复读取该方法详情 | 同一导航 |
| 10 | route research_plan/diagnose；把派生数学视图改成 fields；查询不存在的候选索引字段 | route 成功，随后 EVIDENCE_VIEW_MISMATCH 和 INVALID_EVIDENCE_POINTER |
| 11 | 正确读取 candidate 字段；再次读方法详情 | 成功，仍未提交 diagnose Plan |
| 12 | working_set /all_fresh_results，照用 L0 广告的当前候选引用 | 保护期 TOOL_SCHEMA_ENUM；额度用完 |

Main 对 fixed_input_structure_v1 表现出查询意向，但没有形成正式的候选绑定 diagnose、科学假设/参数请求或 research_analysis。没有人为覆盖成 T1/T2、长度差分或预定路线。Reporter 没有数学结果可解释，数学证据后的下一步决策未验证。该结果不是数值求解失败，也不证明数学工具不可用或结构无解。

## 确认的剩余接口问题与归因

**收尾存在真实的 L0/Schema 不一致。** G 第 6 次与 M 第 12 次的 L0 stop_index.query 均广告当前候选引用、view=working_set、pointer=/all_fresh_results；同一个实际请求的保护期 evidence_read.Schema 枚举却不包含该候选。Main 使用了该广告引用，工具随即拒绝。审查 JSON 的 actual_wire_projection 同时保存广告查询、实际 allowed enum 及比对结论。因此这两次不能归因为模型选错引用。G 第 7 次另外存在读取旧边界引用的错误恢复问题。早期状态说明只看到引用被拒绝；以本次完整 wire 对照为最终归因。

**方法导航未及时交付关键请求细节。** M 读取的整个 methods 约 175430 字节、research_opportunities 约 66352 字节，按原规则返回导航；单个 fixed_input_structure_v1 详情仍有 6750 字节。四次相同详情查询（5/7/9/11）实际首屏只有 operation、method、method_version、scientific_purpose、description、candidate、task_identity、task_family、kernel_supported、model_built、model_sources，request_template 不在这 11 个返回字段中。完整对象仍保留，不表示数据消失；精确子路径可读，但 Main 没有沿它取到模板，错误改用 fields 后又被指回相同大对象。这是已观测的可用性缺口，同时伴随模型重复检索和输入构造错误，不宜把未调用简单归因为纯模型能力或预算数字不足。

本轮只修正启动前的零计算 G 准入，其余阻断在实际有限窗口中保留。窗口耗尽后不临时改 Schema、补额度、代交请求或再跑。若继续，应先针对上述真实 L0/保护枚举一致性和方法请求模板的有界导航做小范围离线复现与最小修复，再另行授权；没有依据扩建优化器、Planner、Knowledge/Memory 或增加数学计算规模。

## 成本与兼容边界

G ledger.wall_s=71.704、M=104.920，均为原 Provider/工具回执口径，不是完整实验墙钟或费用发票。原 numerical_s 分别为 0.3269194 和 0.3717507，包含候选构建/编译/投影准备，不应抹为零。Native 数学模型构建、rollouts、callbacks、物理积分步均为 0，原因是未发生数学执行；不是将 Native 计算视为免费。M 的 callbacks≤24、iterations≤3、knots≤4 和数学四份额度均未使用。独立物理、NMPC、RL、Offline NLP/BDF 为 0。

G 实际 Knowledge 操作 4 次（3 搜索、1 精确读），M 6 次（3 搜索、2 次重复精确读、1 次错误读取）。两项成功读取的都是 research-bounded-continuation@2；success_case 正文读取均为 0。九项权限仍冻结可用，不能宣称 Agent 已利用九项历史 Trace。Reporter 两项均为 0，没有科学解释交付。所有原不可变证据、授权身份、候选所有权、原科学准入与独立接受标准保留。

本次交付两份实际配置、零起点预检、启动阻断的三行预算修复及一项定向离线测试、真实审查 JSON 和本文。提交/push 独立分支，不合并主线。两项实验到此停止；G 的合法生成目标已有正面证据，G 收尾和 M 数学决策目标均未通过，不能以全部 HTTP 200 替代这些结论。
