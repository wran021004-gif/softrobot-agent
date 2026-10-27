# C4 正式无基线 Reach/Hold Study

2026-10-27，Asia/Shanghai。**已结束：Agent 合法 STOP，未找到通过解，未 SELECT；预算未耗尽。**
最佳完整独立结果的保持位置、速度分别超限约3.0957%、3.1241%。
这是有限研究未决结果，不是结构不可行或全局不可行证明。

## 修复、身份与授权

C-F 实现提交 `af5f5bca405ebf235d722fab2afbcedb0437e224`，已普通 push。
实际七个生产文件、五项新定向检查和四项相关回归见 [C-F 清单](cf_minimal_prerequisites.md)。
修复阶段 Provider、科学 worker、物理积分均为零。没有 Provider-only 再评分或模型竞赛。
提交与改动清单已发给 A 聊天，由 A 选择性集成；C 未等待集成。

执行中审计发现初版通用模板示例误含 Native 可选字段 `action_prerequisites`，
导致第6次请求的 endpoint 查询拒绝。这项归属工程表达，原费用保留。
补丁 `2677c700a` 仅从通用示例移除此字段，Native 精确组合查询仍保留，另1项零计算检查通过；
已 push 并通知 A。随后于76次已确认 Provider 请求处，连同交接摘要修复正式迁移；
此前结果仍归属旧实现，不将后续补丁收益归入旧结果。

原 Study `c4-coldstart-reach-hold-20261026`；Store 保持在
`D:/softrobot-agent/.worktrees/c4-decision-efficiency-coldstart/runs/research/c4-coldstart-reach-hold-20261026`。
执行 checkout 由旧绑定 `2c64f5a50` 移到已提交 C-F 实现后，调用原 `bind(reason=...)`。
迁移记录见 `evidence/cf_minimal_prerequisites/migration.json`：spec、profile、账本未变，
changed_scientific_dependencies 为空，material_behavior_change=false，未创建新 Study 或重置额度。
正式 resolved identity 为 `60a684e2389e5719b9c30afaaeb27215a9224087b5df33dc991662cf7a642d66`，
canonical task identity 为 `062de8ca2fd2acaebdbf856ba8fc3420d88c8d3943cfa789c5c9e6f06e486c6b`。

迁移前已确认空科学候选、reference/selected=null、无历史数学/观测/控制种子或 supplied evidence，
无未知 pending worker、Provider 外发或未消费响应。原正式授权与 guard 通过；原 Handoff
admission 和 `restore_only` 在零外发条件下通过。用户本轮明确授权正式执行。
使用原 DeepSeek `deepseek-flash`，未混入 A/B 新代码、历史成功控制或人为研究路线。

任务仍为目标世界坐标 `[0.29,-0.035,0.19]` m、mount `[0,0,0.15]` m、重力 `[0,0,-9.81]` m/s²，
0.50 s 全过程，控制/采样周期 0.01 s、物理步 0.0005 s；终点和保持位置均≤0.01 m，
保持速度≤0.02 m/s，保持窗口0.45–0.50 s。原完整组合验收所有组件仍适用。
FamilySpace 全域保持原冻结注册范围，标准初态为每候选全部自由度为零。

冻结额度：Provider128（保护12）、公共操作240（保护16）、共享物理16、数学36；
NMPC≤2、完整固定回放≤12、PPO≤2阶段/32768动作/2评价。Native 每请求≤120回调/4更新/4节点。
Plan control_search 声明上限17回调，并受真实共享和回放子额度限制；它不是120次免费物理回放。
实际费用均在原 Store 记录，Reporter 与主 Agent 共享 Provider 上限。

## 当前已核实的研究与成本

Agent 自主提交结构生成，经一次生成失败后构造合法三段候选，随后以几何假设生成两段候选；
没有监督者代构参数。首次数值研究是其自行选择的 CONIC sampled-affine task capability。

第7次 Provider 请求完成首个合法数值分析。此前累计输入203814、输出25501、总229315 Tokens，
reasoning19643已含在输出；6次 evidence_read 尝试，2次此前非法工具反馈。
该分析占2个数学单位，测得数值时间15.9344602 s。模型中采样最小最大违反为约−0.20，
浮点支持估计/gap已核验；这是局部仿射模型可行见证，独立物理验收未测。

同一响应的另一分析因没有使用完整冻结协议被硬拒绝，未启动计算。
Agent 随后自行 initialize_control，再选择 NMPC 进行真实闭环检验。
该首次物理启动前累计确认10次 Provider 请求、338475 Tokens；它占用1次共享物理额度。
首次 NMPC 完整完成，数值时间1069.4714274 s，实际求解5次、控制更新50次；
终点误差0.00330110 m、保持位置0.00433918 m通过，保持速度0.07614933 m/s失败。
其后 Agent 自主回放仿射见证控制，完整失败（终点/保持误差0.13636143 m、保持速度0.30049712 m/s）。
这两项是新鲜物理结果，不能将前述仿射可行见证等同于物理通过。

Agent 据此将 NMPC 实测输入显式转录为开放环源。首次 Native 请求仍误把0s标准初态
与[0.3,0.5]晚窗混用；工具准确返回原因、合法[0,0.5]窗口、worker_started=false、数学支出0。
Agent 随后改为完整窗口，四次 Native 搜索实际分别77/101/101/101回调，内部积分380000步，
每次1个数学单位；已用数学共6（含首次仿射2单位）。第二轮结果已独立回放，
成为当前最佳有效失败：终点0.00988444 m通过，保持位置0.01053962 m、速度0.02115126 m/s仍失败。
第三轮预测最大违反约4.638%，第四轮停滞；最新更好预测尚未独立验收，不升级成物理最佳。
后续研究仍由 Agent 决定，监督未选择参数、控制或追加实验。

用户询问停滞原因后，监督只读核对最近两轮已有优化记录：局部求解器均正常返回，
每轮四次 local_response_proposal 均预测改善但 Native 实际 rollout 恶化，半径按规则减半，
最终 stop_reason=iteration_limit。最新一轮半径0.2→0.1→0.05→0.025→0.0125 N，
四次实际改进均为负；故最优控制未更新。响应矩阵满列秩但条件数约5.3×10⁶，
这不是误差界、不可控或全局不可行证明。这一只读监督核对没有派发积分，也未注入 Agent 当作新科研证据。

随后对最近8条错误中已有下一次确认主请求的7条进行只读实际 wire 核对：
7条均经原 Handoff `exact_feedback` 原样送达，错误码及精确纠正查询完整存在。
见 `recent_feedback_delivery.json`。这不是新的模型测试或理解评分，也不能据此声称所有大结果都完整交付；
但这些重复错误不能解释为没有收到相应纠正。

## 已完成的执行中工程迁移

另查出真实交接摘要缺失：部分较大的成功读取在 session handoff 后仅保留
status/task_acceptance 或 reference，已请求的 J、stop_reason、best_metrics 等被省掉。
这可能促成反复读取；不能据7条错误原样送达声称所有读取完整，也不能把全部停滞归因于此。
`e83998a15` 只在原 bounded pending_feedback_delivery 中保留已选对象标量和容得下的小字段，
列出 omitted_keys，summary 保留 preview 语义；原层级、接口 schema、配置、精确反馈、
L2 原件与 read credit 不变。2项新离线回归与1项原 SDK/模拟 HTTP 交接恢复检查通过，
真实 Provider/科学 worker/物理积分均0。已普通 push，并将提交及清单通知 A 选择性集成。

76次确认请求、3529903 Tokens、数学9单位、共享物理4次处，通过原
validation_extension_pending_binding 门禁让旧进程在下一次发送前退出；没有强杀、未知请求重发或实验重跑。
切换已提交实现后调用原 bind，changed_scientific_dependencies=[]、material_behavior_change=false；
spec/profile、候选、结果、控制源及完整账本逐项相同，restore-only 通过且零外发。
记录见 `context_repair_migration.json`，随后原 CLI 继续同一 Study，DeepSeek Flash 保持不变。
恢复启用原 pause_exploration_remaining=4，以便保护额度前按用户新授权审查有限请求追加，
不增加人工科研批准门槛。当前没有追加预算或修改科学限额。

迁移时共7次 Native 搜索、683次实际内部 rollout、683000物理积分步；后两次最大违反
保持约4.2538%，只有速度/次排序细微改善。第3次独立回放已确认当前有效最佳：
终点0.0098478951 m通过，保持位置0.0104253785 m、速度0.0208421033 m/s失败。
这是真实完整失败，未 SELECT；最新 Native 预测不自行提升为物理通过。

第81次请求完成第8次 Native 搜索，改了节点与半径但最大超限未改善。
第85次请求 Agent 自主转为 Plan 物理回调搜索：请求6次回调，实际复用1个已测基线、
启动5次新完整回放。它正确区分了 Plan 与 Native 额度，使用真实失败构造了可反驳的控制假设；
最佳有效结果最大超限降至约3.1241%，终点0.0097163207 m、保持位置0.0103095703 m、
保持速度0.0206248215 m/s，仍是完整有效失败。监督未提供该控制参数化或派发实验。

87次请求处又发生标准0s初态配[0.1,0.5]晚窗的 Native T1 请求；工具准确拒绝，
worker_started=false、additional_analysis_evaluations=0，并返回合法[0,0.5]及 T1 完整任务要求。
不能声称模型已经消除时间窗误读。Plan 的晚窗是控制修改掩码，不能误计成同类 Native 错误。

`0d2a2db7c` 修正 C-F 动作前提被目录旧复制逻辑带入只读 T2 的问题，并在 L0 保留已有
Native 精确模板查询。1项定向离线检查通过，真实 Provider/科学 worker/积分均0，已 push 并通知 A。
87次确认、4055648 Tokens、数学10单位、共享物理9次处，再次经原门禁自然退出、原 bind
迁移及 restore-only，spec/profile/结果/成本不变；见 `query_repair_migration.json`。
随后恢复取消额外160000-byte运行阈值，沿用原保守 Provider 容量保护与 SDK 上下文机制。
此前85次请求已出现64次交接，近期单次新请求本身约141–156KB；该额外阈值会频繁触发交接。
这是一项单独记录的运行调整，无 schema、冻结配置或上下文层级修改；后续效果不能单独归因于某个补丁。

请求93完成 equilibrium，worker正常返回，数学1单位/19.2101555 s，不能视为完整任务通过。
请求96初始化手写控制有51行（本任务要求50区间），原绑定准入正确拒绝但摘要原因过宽；
请求99又将显式 inputs 与 source 同填，被 schema 准确拒绝。相关失败的公共操作与初始化检查耗时保留。
`b715df920` 保留原 binding 条件与错误码，增加实际/期望维度、时间点数、身份/通道匹配事实，
并在错误摘要保留 bounded 原始 reason；1项离线检查通过，已 push 并向 A 提供清单。

请求101后请求迁移门禁时，下一次模型发送已越过 before_model 检查，发生1次时序竞争。
请求102正常确认（176911 Tokens），其 mujoco_direct_control_v1 动作被工程绑定门禁拒绝，
worker未启动、无新数学/物理次数；这是监督工程干预成本，不能归为模型科研错误或未知重发。
旧进程随后正常退出，102次确认、5578386 Tokens、数学12、共享物理9处，原 bind/restore-only
迁移到 b715df920，spec/profile/全部结果及成本保持；见 `binding_reason_migration.json`。
后续按已启用的原生 supervisor review 边界审查额度，避免再次用运行中门禁做临时暂停。

第103次请求以3次内部回调检查新平衡点导出的控制源，数学1单位/1.3765205 s，
预测保持误差0.0273966 m、速度0.2221928 m/s，明显未通过；没有占独立回放额度。
对原10次 Native 结果的426次同输入重复回调只读比对，位置/速度/时间输出逐值一致，
没有观察到这些重复回调的状态恢复漂移；这不证明局部近似正确或全局可行。

第106次 Provider 响应 HTTP200、finish_reason=length：输出32768 Tokens，其中 reasoning29302，
输入198283，总231051。存在未验证的 research_plan 字段，原框架在提交前准确拒绝并退出，
无新科学 worker。不是全研究输出耗尽，也不是未知网络失败。
用户随后明确要求不要让输出额度阻碍 Study 并恢复。经官方文档核实 Flash 单次最高384K，
通过同 Store 授权附录把单次 max_tokens 从32768提高到131072，其余 Provider 设置与请求/
数学/物理额度不变。来源：https://api-docs.deepseek.com/quick_start/pricing/（2026-10-27）。

在原执行实现下，先只读验证106收据已结算、原主进程退出、SDK原历史与该请求 wire 前缀一致、
截断工具ID从未提交、无未结算调用。随后把已确认截断草稿作为 archived_unsubmitted 留存，
保留原响应、原收据、SDK文件和全部费用，通过原正式授权更新、bind、restore-only 接入新输出额度。
见 `output_allowance_migration.json`；resolved identity 变为
`bd238797ffcbf6cc15ecdb897271f795674a373253f01832dedb1870f2dedbe8`，
task/profile/全部候选结果与已用账本不变，恢复核验零 Provider/科学 worker。
使用原 CLI 恢复同一 Study，未执行截断参数、未重发未知结果、未创建新研究或重置预算。

## 最终结果、结构权限与停止判断

提高单次输出额度后，同一 Study 又完成5次 Provider 请求（107–111），均以完整 tool_calls
结束，未再截断。Agent 自主初始化另一控制源并用3次 Native 回调检查，保持位置约
0.0103454 m、速度约0.0470817 m/s，未取得独立通过。
第110次请求首次 STOP 因没有引用全部新结果而被硬拒绝；第111次请求补齐22项新结果引用，
原规则合法接纳 STOP，final_disposition 为
`66194eca08c6292beb31710a0f02677208e7be9ef22378b29c43079c3539a4b9`。
没有手工 SELECT、伪造成功、追加确认或解封原 STOP。

停止时 Provider 剩17（含保护12）、公共操作剩58（含保护16）、数学剩22、共享物理剩7，
独立固定回放子额度剩4，NMPC还可1次，PPO未启动。因此结局必须归类为
**合法的 Agent 主动停止、科学未决**，不能写成预算耗尽、接口阻断或可行路线已穷尽。
预备的有限请求追加未执行；Agent 在原监督额度审查暂停实际发生前自行停止。

停止理由强调单结构控制搜索的位置—速度折衷、多次局部无改善及两种新控制源失败，
但这些观察不足以证明 plant 的全局 Pareto 边界或没有其他合法机制。
其声称 PPO 在32768动作内不可用，未通过训练验证；offline NLP本来没有授权额度，
不能暗示已执行并耗尽。原 STOP 是自主决策的历史证据，其科学解释不因硬准入通过而成立。

本轮冻结 `initial_structure_strategy=heuristic_generate`，因此第一步确实要求启发式生成；
第一合法候选后即可使用数学结构搜索。原实际发送 wire 已核实：停止前仍含
`structure_actions.search`，允许 lengths/materials/sections/routing/spans 以及离散段数/腱数。
控制重优化结构敏感性也标明 authorized=true，缺少的是尚未准备的模型差分组或三个可比较 T1。
这些是可由 Agent 准备的前提，不是权限禁止。见 `structure_access_audit.json`。

实际提交3次 generate（1次失败、2个合法结构），0次结构 search、0次结构敏感性分析。
六腱及两段/三段组合由 Agent 提出；未指定细节由冻结 FamilySpace 原生成器解析。
本轮数值研究全部集中在两段六腱候选，数学并未求出六腱最优或结构最优。
因此“固定结构控制优化多次停滞后，未准备结构比较就停止”是本轮研究决策缺陷，
不能作为新增科学硬门禁、监督者替选结构或修改原任务的理由。

未来可用已有 `initial_structure_strategy=math_search` 明确要求数学结构搜索起步，
随后仍由 Agent 根据完整任务物理反馈比较结构、控制或联合修改。
本报告仅记录后续可选研究政策，没有改动本轮冻结配置，也未启动新 Study。

最佳完整独立结果仍为 `ecba8d8ee8186e830860764e8fe2ec06b17b6343d5ad81759e29ab51a7966b65`：

| 原验收指标 | 实测 | 上限 | 结论 |
|---|---:|---:|---|
| 终点误差 | 0.00971632070155 m | 0.01 m | 通过 |
| 保持最大位置误差 | 0.01030957030577 m | 0.01 m | 失败 |
| 保持最大速度 | 0.02062482153811 m/s | 0.02 m/s | 失败 |

该结果其余原完整验收组件通过，evaluation_validity=valid，execution_complete=true；
仍为 valid_failure，不能 SELECT。所有9次完整独立执行均没有通过。

## 成本与效率结论

正式 Study 的111次 Provider 请求全部确认，102次主科研会话、9次 Reporter：

| 实际 Provider 用量 | Tokens |
|---|---:|
| 输入 | 6,713,318 |
| 输出 | 834,232 |
| 总计 | 7,547,550 |
| 输出内 reasoning（不重复相加） | 743,742 |
| 输入缓存命中 | 3,793,280 |
| 输入缓存未命中 | 2,920,038 |

Provider 未返回实际货币账单，money=null；不能以估算替代真实扣费。
原 C4-R 的14次请求/575452 Tokens属于独立准备研究，不混入本表。
原 Store 共享账本消耗：Provider111/128、公共操作182/240、共享物理9/16；
账本 wall_s=6070.0928952 s，原资源计数 numerical_s=1212.3397704 s。
二者含义不同，也不是研究跨度约14.06小时的同义计量。

| 科学计算 | 实际计算成本 |
|---|---|
| 数学计费单位 | 14/36；13项完成结果 |
| 完成数学结果数值时间 | 129.6085097 s |
| 其中 Native 控制搜索 | 11次，94.4638940 s，891次内部 rollout、891000积分步 |
| NMPC 独立执行 | 1次，1069.4714274 s；5次求解、50次控制更新 |
| 独立固定序列回放 | 8次，9.7623855 s，原始计数合计8000积分步 |
| PPO | 0训练阶段、0动作、0评价 |

数学时间已含 Native，不能再次相加；总 numerical_s 还含原聚合/流程实际记录的时间，
不得简单用上表子项相加冒充总账。NMPC原结果没有总积分步字段；按冻结
0.5/0.0005推得名义任务1000步，明确区别于有原始字段的回放/Native步数。
ledger.worker_calls=0是原预算计数单位，不能解读为没有启动科学 worker。

首次数值动作第7次请求、229315 Tokens、2数学单位/15.9344602 s。
首次完整物理计算第10次请求、338475 Tokens；其完整 Reporter 反馈完成后为
第11次请求、353426 Tokens（其中Reporter14951），保留两种清晰时间边界。
首个完整物理结果为有效失败，不能用模型采样可行替代。

模型仍出现标准0s初态配晚窗的 Native 请求（包含第87次），故时间窗误读未消除。
Plan 第85次物理搜索则正确使用6回调、复用1基线、新增5独立回放，
未将 Native120内部回调当作独立物理额度；最佳实际超限从约4.2538%降至3.1241%。
读到真实失败后转向实测 NMPC 输入、物理控制搜索及静态目标构造，说明有利用失败证据，
但固定结构反复局部优化、结构路线未使用与过早停止仍需如实报告。
102个主会话请求中67个只读；共38项错误反馈，其中包含工程模板错误和监督迁移竞争，
不能统归模型。错误交付抽样7/7实际进入下一次请求，不代表所有大结果均无摘要损失。

原3000-byte交接摘要缺失已局部修复；取消额外160000-byte阈值后，实际末次请求
保留21条assistant、22条tool历史消息，沿用原容量保护和SDK上下文机制。
重复回调只读抽样426次同输入状态输出逐值一致；没有据此宣称梯度可信、无其他数值问题
或增加新的物理计算。修复与运行调整没有配对因果试验，不能独立归因性能收益。

## 工程交付与证据

通用代码提交全部普通 push，A 已收到提交与实际清单，C 未等待合并：

| 提交 | 实际改动 |
|---|---|
| `af5f5bca4` | 原动作前提、初态时间/合法窗口、回调与共享/回放额度、真实失败/worker成本 |
| `2677c700a` | 通用方法模板查询去掉非通用可选字段 |
| `e83998a15` | 原 bounded 交接摘要保留已选证据事实及省略键 |
| `0d2a2db7c` | T2只读聚合前提、保留已有精确方法查询 |
| `b715df920` | 原序列绑定拒绝显示真实维度/时间点与 bounded 错误原因 |

合计9个生产文件：`agent.py`、`analysis.py`、`budget.py`、`native_analysis.py`、
`native_control.py`、`physical_replay.py`、`research_context.py`、`session_handoff.py`、
`task_constraints.py`，均位于 `tools/research/`；优先检查的 `local_control_search.py` 无改动。
总15项定向离线检查已通过，真实 Provider/科学 worker/积分均0；没有大套件、评分竞赛、
防御式重构或第二套上下文。迁移均走原 bind/restore-only，原任务/profile/结果与成本保留。

结束后只调用一次原 `core.export`，本地交付目录：
`D:/softrobot-agent/.worktrees/c4-decision-efficiency-coldstart/evidence/c4_coldstart_reach_hold_20261026/`。
`design_package.json` 包含实际最佳结构、控制、完整验收结果和来源，标记
`status=best_valid_candidate, accepted=false`；不把失败包命名为成功解。
原候选 validator 通过，导出配置/评价与最佳原件一致，所有调用收据已结算，
pending worker/Provider/占用/未消费响应均空。私有不可变归档与原始科研/Provider历史留在本地，
不提交 reasoning、凭据或原始归档。

Git 仅提交非敏感审计：`formal_audit.json`、`closeout_audit.json`、
`structure_access_audit.json`、各迁移、摘要/错误交付/历史数量/重复回调审计。
没有通过解、合法 SELECT 或实际待修工程阻塞；最终交付为合法 STOP 的真实最佳失败和
上述尚未解决的科学及研究决策问题。
