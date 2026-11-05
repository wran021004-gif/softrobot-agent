# PHS-2D Knowledge 自主研究：真实启动与持续监督

Study `phs2d-knowledge-autonomy-20261105` 已真实启动，初始 resolved identity 为 `31c22b6af32975d2d30c87e1c56943faf0fb47d6273d74d5496a790237b5dab7`、原 Gateway `gpt-5.6-sol / medium`、原完整十工况和原 Store。这里记录前两个已结算窗口，不代表最终科研结论；后续累计状态以 [状态 JSON](phs2d-knowledge-status-20261105.json) 和私有原账本为准。

## 最新状态：Main 正式停止，无可行解、无 SELECT

第 **111** 次共享 Provider 请求中，Main 改正引用字段，提交了全部 **18** 个当前 Study 结果引用；原门禁接受了 `empirical_search` 范围的无选择 STOP。第 109、110 次被拒提案与费用完整保留，没有放宽或绕过证据门禁。原状态现为 `stopped`，最终 disposition 为 `4810ad750142ee3477cf73cbe1d671546ec85d63739a09b295a3c45fc2b4d1b8`，`selected=null`。无 pending/unknown、无未消费响应。

最终 **15 个合法候选记录、14 个不同物理设计、18 次数学评价**（13 次静力检查、5 次完整十工况尝试）。实际加载 episode=0、科学积分步=0、独立 Replay=0；不存在合格工作点或完整任务通过证书。Main 根据已观察到的反复资格失败和分支切换，判断进一步当前局部调整的信息价值较低而停止；这是有范围的研究决策，不证明整个设计族不可行，也不表示用户“找到可行解”的目标已达成。

STOP 并非预算耗尽触发：Provider **111/120**，原预授权政策最高 128；数学评价累计仍为 **不限**，episode 预留 **50/80**，公共操作 **102/160**。所有失败、授权增补和成本保留。108 个响应有 usage，已知 subtotal prompt=6,897,039、completion=50,911、total=6,947,950 tokens；3 次错误未返回 usage，不能视为零。货币费用未知。数学 Worker 累计 42.2783897 s，包括候选构造等工作的总 numerical_s=54.7247798 s。

持续科研监督心跳 `phs-2d` 已在正式 STOP 后删除。**18:22:53 Asia/Shanghai 后切回 Gateway 的独立定时任务仍有效**，但它只恢复配置、保留封存状态和数学不限授权，不重启研究、不再发送 Provider 请求。当前完整状态见 [状态 JSON](phs2d-knowledge-status-20261105.json)。

## 此前监督窗口：第 109 次请求已结算，未接受 STOP

window27 新增一次不同活跃集合的静力检查，累计仍无合格工作点。window28 读取当前结果索引后，Main 提交停止提案，但未提供结构化 `supporting_evidence`；原门禁返回 `INFERENCE_NOT_SUPPORTED_BY_TRUSTED_EVIDENCE: local_diagnostic`，没有接受 STOP、没有执行科学计算，也没有改变计数。该字段遗漏不是放宽证据门禁的理由。Study 仍为 `ready`，无 pending/unknown 或未消费响应，后续科研决定仍由 Main 作出。

当前累计 **15 个合法候选记录、18 次数学评价**（13 次静力检查、5 次完整十工况尝试），Provider **109/120**。数学累计不限；实际加载 episode、科学积分、独立 Replay、SELECT 均为 0。没有因本窗口重复索引读取或被拒 STOP 增补额度。

只读审计发现共享预算视图漏读本任务真实的 `structure_research.cost`，曾将 17/18 个结果显示为缺少成本。生产修复 `15614b1` 仅把已有成本路径纳入原投影，现正确区分有记录的 16 个结果与缺少完整成本的 2 个历史失败；不伪造缺失次数。定向离线回归通过（1.989 s），原 bind 与 SDK restore-only 通过、无新增请求、profile 和旧账目不变。

精简状态报告也区分了数学 Worker 数值成本 **42.2783897 s** 与包括候选构造等工作在内的总 `numerical_s` **54.7247798 s**；后者此前误用了“数学数值成本”标签。当前报告改为直接汇总原 `analysis_costs`，历史记录不改写。

## 最新授权：数学评价与分析累计次数不限

用户新明确要求“数学评价、数学分析等不设置上限”。已在第 16 次数学评价后的安全结算边界，通过原 `tools/research/budget.py` 中的精确授权 addendum 将本 Study 的累计 `mathematical_evaluations` 从 20 改为 `null`，复用现有 unlimited admission 语义。新 resolved identity、正式研究授权、committed bind 和 SDK restore-only 均已完成；原 16 次实际评价及其成本完整保留，profile v3、原任务、会话和验收不变。此后已实际执行第 17 次数学评价，证明原位接续没有重置计数。

两项定向离线回归通过（3.338 s），验证精确授权、幂等、旧计数/成本/profile 保留、超过旧累计次数仍可准入；过期身份、非明确 unlimited 目标、未消费响应与未封口 Worker 均被原子拒绝。没有取消 Main 已明确选择的单次计算努力或改动原注册方法。

最新已结算窗口累计 **15 个合法候选、17 次数学评价**（12 次静力检查、5 次完整十工况 finite-time 尝试），尚无合格工作点、加载积分、独立 Replay 或 SELECT。Provider **101/112**，仍按已批准的每次最多 +8、总上限 128 的政策监督增补。数学次数不再是累计停止条件。用户授权的持续监督心跳 `phs-2d` 已启用，定时接口切回由独立心跳 `phs-2d-gateway` 督办；未改变或无需行动时保持安静。

## 临时官方 API，定时切回 Gateway（先前接续记录）

用户明确要求“先用官方API（第三种）方式续上，等一个半小时之后继续使用gateway方式”。已在同一 Store 应用精确身份的 transport addendum、正式授权与 committed bind，保留 `gpt-5.6-sol`、Main `medium`、Reporter `none`、原科学 profile v3、Python/线程环境、SDK 会话和全部费用。切回时间为 **2026-11-05 18:22:53 Asia/Shanghai（10:22:53 UTC）**，当前聊天心跳 `phs-2d-gateway` 已保存该指令；在已结算边界使用同一正式机制恢复原 Gateway。该时间不表示已经证明 Gateway 额度恢复。

官方账户 `GET /v1/models` HTTP200 确认存在精确模型，未发送额外推理探针。第 77 次共享请求真实返回 HTTP400：此模型的 Chat Completions 不支持 `medium` 与 function tools 的组合，明确要求 Responses 或 `none`。保留原错误及费用，未降低 reasoning。最小接口修复将官方 `medium` 工具请求转换为 stateless Responses；同一原计费边界保存原始上游请求、原始上游响应和明确标记的 SDK Chat 投影视图，按工具调用身份保留加密 reasoning 项。SDK 仍负责唯一的科研会话与工具执行。参考 [官方模型文档](https://developers.openai.com/api/docs/models/gpt-5.6-sol) 和 [Responses 迁移文档](https://developers.openai.com/api/docs/guides/migrate-to-responses)；真实 HTTP 反馈优先于宽泛的模型能力列表。

后续两个已结算窗口共 **8 次真实官方 API 研究请求全部 HTTP200**。累计 **11 个合法候选、14 次数学评价**（9 次静力检查、5 次完整十工况 finite-time 尝试），仍无合格工作点、实际加载积分、独立 Replay 或 SELECT。Main 自行评价第十个候选，继而生成并评价新的路由变体；新的静力结果仍未满足收敛、容量或稳定性资格，不证明全族不可行。监督者没有提供结构数值或替 Main 选择方向。

原账本 Provider **85/96**（9 次合法 +8 增补）、数学 **14/20**、episode 预留 **50/80**、公共操作 **75/160**。8 次官方成功响应已知 prompt=617,878、completion=3,209、total=621,087 tokens；第 77 次错误 usage 未返回，原 Gateway 的两次缺失 usage 也仍未知。所有 Provider 货币费用仍未知。原冻结科学资源未扩张。

定向离线验证共 4 项，覆盖精确授权、原子往返、非法模型/设置与未结算边界拒绝、真实 SDK 跨接口接续、原工具反馈、上游原始证据、加密 reasoning 再交接，以及 incomplete 响应只扣一次且不得提交工具。最新 3 项完整运行 31.757 s，新增 incomplete 回归 2.331 s；没有声称全仓测试通过。最初旧通用夹具因 `matlab.engine` 缺失失败的记录保留，随后改用本任务现有 PHS 离线夹具；没有安装或伪造 MATLAB。

当前累计状态以 [状态 JSON](phs2d-knowledge-status-20261105.json) 和原账本为准。下文为此前阶段的历史记录。

## 上次暂停：第 76 次 Gateway 额度阻断

第 76 次共享 Provider 请求返回 HTTP429 `subscription_sharing_usage_limit_exceeded`、`retryable=false`。已停止后续发送，没有后台重试或自动更换 Provider。当前原 SDK restore-only 已再次通过，不发送模型或科学请求；无 pending/unknown、无未消费响应、无 SELECT、无被接受的科学 STOP。当前仍保留原 Gateway `gpt-5.6-sol / medium`。

本 Study 共有 **10 个合法候选、12 次数学评价**（7 次无载静力检查、5 次完整十工况 finite-time 尝试）。工作点均未合格或初始化失败，实际加载 episode=0、积分步=0、独立 Replay=0，无完整通过证书。Main 自主改变紧凑几何后解除了最初全零状态的 floor 交叉，但后续平衡仍未通过 KKT、稳定性或容量资格。后续两个 payout 变体保留为失败证据，第十个候选尚未评价；不从这些局部失败推断全族不可行。

累计 8 个合法 +8 增补，Provider **76/88**，其中 Main conversation=68、Reporter=7、授权 quota probe=1；数学 **12/20**，episode 预留 **50/80**，公共操作 **67/160**，原 4 次保护收尾额度不变。Gateway 账户阻断不能由增加 Study 额度解决，因此当前 12 次剩余 Provider 未继续发送。原有限 policy 总上限仍为 128，没有扩张数学或物理冻结限额。

74 个响应有 usage，已知 subtotal 为 prompt=3,964,677、completion=34,840、total=3,999,517 tokens；第 48 次 504 与第 76 次 429 均扣请求数且原记录保留、usage 未返回，不能当成零 tokens。货币费用未知。已知科研 Native 模型 12 个，已结算数学数值耗时（含原准备费用）累计 25.8568415 s，Worker 边界耗时累计 25.8568415 s；原 ledger wall_s=1524.1358415 是其原定义的已记账耗时，不是整个监督聊天经过时间。工程复现和两个小玩具回归积分步另记，不授予 Study 物理信用。

当前 resolved identity `d467380ffa990fe05ecf46d5a324690f74d5f36c29ab0405f2425274ff362043`，profile v3 `e952d4bb2a456ef3ab6a9ce54b691a6f6efff6292be7aadf59a6dd919f74e80b`。原 prepared Study 四文件哈希最终再次全部核对未变，原 Store 的失败、费用和所有授权增补均保留。运行阻断与 Main 科学 STOP 严格区分；额度恢复后可原位继续。

## 额度恢复与批准

用户先批准精确身份和注册数学；随后明确要求真实测试 Gateway 额度。操作者据此仅发送一次最小推理检查，HTTP200，回答 OK，prompt=27、completion=5、total=32 tokens。此次例外有独立授权事件、原始请求/响应和结算，计入本 Store 的原 24 次共享额度，没有后台重试。接口没有返回账号剩余额度总量，不能从一次成功推断可持续调用总量。

用户随后明确选择“继续当前 Gateway，保留 gpt-5.6-sol / medium”。官方 OpenAI API 确实已有独立配置和 Key 文件，但本 Study 没有切换 Provider、计费账号、模型或重建 Store。

## 工程归类修复

操作者把此次检查标记为 `gateway_quota_probe`，旧 SDK 历史检查仅认识 reporter/provider_validation 等已知非 SDK 请求，因此在首个科研发送前复现 `SDK_HISTORY_HAS_NO_TRUSTED_STORE_ANCHOR`。原始收据未改写。最小生产变更只在已知非会话用途集合中加入该明确类型，保留共享计数与全部原费用。

真实 SDK + Mock HTTP 定向回归验证：先扣账并结算一次 quota probe，再正常进入空的科研 SDK 历史；未知用途和未信任消息后缀仍拒绝；随后原 SDK 可发出一个正常 Mock 请求，累计账目为 2。回归通过，执行约 8.6 s，无真实 Provider 或科学积分。旧 v2 测试入口另受缺少 matlab.engine 的无关夹具依赖阻断；没有为被动 PHS 安装或伪造 MATLAB。生产修复不涉及物理文件、科学合同或验收，按原 bind/migration 保留原 profile 和 resolved identity。

## Main 的真实行为

第一窗口共 4 次 Main 请求：

1. 自主提出可证伪的被动约束假设，并生成一个合法九段、四被动腱候选。其自行选择的首个拓扑为全跨距对称约束，目标是保留内部变形而限制末端位移；继承的合法默认值不是任务通过证据。
2. 自主选择实际张紧集合、Jacobian、零空间和局部柔顺性作为机制检查方向，完成 diagnose 意图登记。接口明确反馈 diagnose 不执行数学。
3. 提交真实 `research_analysis`，但把静力载荷写为 `all_frozen_conditions`；原运行时返回 `SELECT_FROZEN_LOAD_CONDITION`，没有开始科学计算、没有扣数学评价。没有增加模型字段兜底。
4. 自行改为明确的 `unloaded` 条件并执行一次原注册 `mechanism_structure_v1` 检查，得到真实的未合格工作点。

第二窗口共 4 次共享请求：1 次 Reporter、3 次 Main。Reporter 保留资格失败及模型范围；Main 读取路由参数、选择生成接口并进一步读取候选配置。此时尚未生成第二个候选，尚未进行重复数学计算或物理 Replay。存在明确的后续结构决策，因此继续在原额度内观察，没有申请预算增补。

## 真实数学结果与适用性

本次是无载、理想硬单侧约束的零时域局部检查，不是完整动态任务：

- 4 个约束活跃、LICQ=true，但只有 2 个正乘子且 strict complementarity=false。
- optimizer_success=false，终止为 `nonconverged_unqualified`。
- primal violation=0.4165296419 m，stationarity infinity norm=3919.124982 N·m。
- 最大约束张力=5032.632121 N，而声明容量为每通道 0.406 N；容量资格未通过。
- 最小约化刚度=-328.492308 N·m/rad，native soft-limit length excess=0.4165296419 m。

未合格点的负刚度不能被当成一个已合格平衡的稳定性结论。没有可信结构方向、敏感性、下降保证或完整任务通过结论；非收敛不证明全局或结构不可行。Reporter 实际保留了这些区别，Main 的后续理解与结构采用仍待继续观察。

实际成本：1 次数学评价、1 个 Native 模型、1 次平衡、144 Hessian 列、315 native forward、0 积分步；kernel 约 0.338 s，已结算数学 Worker 约 1.571 s。没有加载 episode、独立 Replay 或十工况证书。

## Knowledge、资源与能力判断

六条已审核程序白名单仍不变，历史案例及其引用仍不可读取。首轮确认交付一个 `skill-parameter-model@1` compact 摘要；完整正文读取为 0。Main 在实际 Plan 中明确不声称采用尚未读取/确认适用的 Knowledge。不能据此归因其研究方法由 Knowledge 改善。

截至前两窗口：Provider 9/24，其中 quota probe=1、Main=7、Reporter=1；公共操作 7/160，数学 1/20，共享 backend episode 0/80。9 条响应均有 usage，累计 prompt=235,622、completion=3,195、total=238,817 tokens。货币费用未测量；所有失败、检查和原始费用均保留。原保护收尾 4 次仍保留，没有增补、无计数重置。

L1 已观察到自主合法结构生成及假设；L2 已发生真实机制分析，但工作点不合格，对科学判断能力的评价还需后续行为。L3 数学指导的新结构修改尚未观察到，L4 完整十工况通过尚未建立。当前没有 SELECT，也没有 Main STOP。监督者没有向 Main 提供历史获胜结构、参数方向或指定下一项科学动作。

## 后续窗口、接口修复与首批增补

Main 两次提交超出冻结 payout 范围的生成请求，均原样拒绝，没有产生候选或扣数学成本。真实接口缺少精确 domain 诊断，已补充字段名、原请求值及冻结上下界；没有改变范围或自动修复设计。定向边界回归通过，提交后原 bind 迁移。因 source-hash 保守规则，profile 进入 v2；旧结果保留原 profile，不迁移接受性。

Main 随后自主生成第二个合法短跨距候选并执行自己的无载静力 active-set 检查：LICQ=true、active=1、boundary=1、positive=0、slack=3；optimizer_success=false、qualified=false。primal violation=0.0006085993 m，stationarity=0.4689319942 N·m，最小约化刚度=0.1834846881 N·m/rad，张力=0。因未收敛且不严格互补，不能作为可信局部梯度或任务可行证据。第二次成本：1 个模型、1 次平衡、144 Hessian 列、1314 native forwards、0 积分步。两次检查 profile 不同，不能从数值下降声称受控因果改善。

第 20 次共享调用尝试 STOP，Main 明确承认仍有未测合法机会，仅因临近收尾预算选择结束。原科学门拒绝 EVIDENCE_DESIGN_IDENTITY_MISMATCH：为单一设计引用了另一个设计结果。反馈格式器又把短别名错误当成 EvidenceRef，使原始拒绝原因被掩盖；现已仅在错误呈现处解析公开别名，保留原门与拒绝，测试通过。没有接受 STOP，也没有 SELECT。最新 Knowledge 定向模块 9 项通过（55.426 s，Mock Provider），不代表科学验收。

用户明确授权持续监督、必要时增补、修复接口并继续直到找到可行解。首批 +8 已经原 Store 原子事务完成，Provider 24→32；新 resolved identity 为 `3d022f81a28dd10e6e525a75772f3441171cd0f476b8fba371ea1756575d7283`。授权记录区分用户原话与监督者推导的精确身份。原数学 20、episode 80、公共操作 160、收尾保留 4 次不变，20 次历史调用和全部失败保留。当前恢复原 Gateway/SDK 后续窗口；以状态 JSON 与原账本为最新值。

## 第二次增补与发现接口重复构建修复

累计 28 次 Provider 后，4 个合法候选、3 次真实数学检查、0 次物理评价。第三个工作点仍不合格：primal violation=0.0001504863 m，stationarity=0.0931120346 N·m，minimum reduced stiffness=-832.814398 N·m/rad，optimizer 400 次未收敛。Main 根据这次反馈自主形成第四个候选，尚待评价。第二批 +8 在第 24 次调用的安全结算边界原子增补，Provider 上限 32→40，其他限额不变。当前 identity 为 `9bebbb956ad3a5192fa5720af8e3b2e6231aab24745a903b1afe627892840d84`。

只读性能剖析确认一次决策包触发 577 次结构生成。最小修复仅在同一次 v2 候选发现调用中复用已验证的参数元数据；正式执行仍独立验证，v1 路径相关标准化保持原逻辑。完整决策包序列化内容逐项相等，同状态未剖析计时 36.357 s→13.899 s。定向回归覆盖全部发现变量事实、只构建一次、旧版路径、篡改配置仍拒绝及零科学扣账（1 项，12.871 s）。旧 F3 测试因稀疏工作区缺少已封存数值夹具未运行，不作全套通过声称。

## 第 44 次请求：真实有限时域尝试与初始化失败诊断

当前 6 个合法候选、7 次数学评价。第五次静力检查仍不合格且容量超限。Main 随后自主选择对第四、第六个候选分别执行原完整十工况 finite-time 检查；两次均在无载静力初始求解时触发 `FatalError: FactorizeHessian: rank-deficient sparse Hessian`，未开始加载 episode，未积分。它们各扣 1 次数学评价及 10 个 episode 的原预留额度，全部费用保留；20 个是已扣预留预算，不能说实际完成了 20 个 episode。没有独立 Replay 或证书。Provider 经过第三、第四个原子 +8 增补，当前上限 56，累计使用 44；数学 7/20，episode 预算已扣 20/80，公共操作 41/160。

原静力前向调用未使用已有 MuJoCo 失败快照，导致上述错误缺少失败前状态、准确位置和静力中间费用。最小修复仅在 `StaticProblem.at` 复用原 `MujocoFailureSnapshot`，保留原异常，并通过既有 Worker 的 `native_diagnostic` 路径结算部分计数；失败调用内部进度仍标为 unknown。没有更换求解器、regularization、初始条件、物理或验收。2 项定向测试通过（0.387 s），包含失败前状态不被异常后状态污染、部分费用、正常原生前向数组完全一致与原 Worker 快照持久化。因科学源文件 hash 变化，原 bind 保守生成 profile v3；旧失败和旧 profile 候选保留，Main 须自行选择并在当前 profile 合法构建后继续，不转移旧接受性。旧 prepared Study 四文件哈希再次全部核对未变。

## 第 52 次请求：Gateway 接续、初态接触与部分费用保留

Provider 上限 64，累计 52 次；数学 8/20，episode 预留已扣 30/80，仍没有加载 episode 或积分。第 48 次返回已知 retryable HTTP504，没有科学动作，原收费保留；原 SDK restore-only 校验通过后恢复同一 Gateway，第 49 次正常成功。第 50 次由 Main 自主对其当前 profile 重构候选执行完整十工况检查，同样初始化失败。新快照明确为全零 q、静力第一次 forward，优化迭代 0；异常后的碰撞诊断记载 228 个地面接触。

使用同一冻结 XML 和已保存 pre-call state 的最小工程复现，完整 forward 复现原 FatalError；位置/速度两阶段检查可返回，确认全零几何有 228 个 floor 接触和 912 约束行。只用于工程归因，不给科研接受性信用，不改变地面、约束、物理或求解器。该复现 1 个模型、1 个失败 forward、2 个组件调用、0 积分/优化，约 0.051 s；此前一次直接 Windows XML 编译退出 1，完成模型数未知，随后改用仓库已有编译线程 loader。这些工程费用另存原 Store，不能与 Main 的成功证据混淆。

发现原 `analysis.recover` 会把 Worker 已保存的部分 `internal_calculations` 再覆盖为 unknown。最小修复改为仅在没有计数时提供 unknown fallback；保留失败状态、原预留扣账及未知内部进度。真实离线 Store 回归验证“已知部分计数保留”和“缺失计数仍 unknown”两分支（1 项，2.799 s），不重新执行 Worker。旧第 50 次结果和收据不改写，原 `/native_diagnostic/cost` 仍可精确读取；监督者仅链接纠正其呈现归因。科学 profile 保持 v3。

## 第 56 次请求：区分设计生成与数学方向权限

Main 读取三个参数页后将未获数学方向授权的参数理解为设计中不可修改，并提交了“等待初始化/结构变量授权”的诊断意图；没有接受 STOP。实际冻结 FamilySpace 与原生成合同仍允许这些字段的合法生成，数学方向授权则另有范围。公共目录虽然有 design_supported，却同时用 study_authorized/selectable 表示数学资格，且正常分页不提供全部参数组目录，造成设计可变性呈现歧义。

最小修复补充 generation_available 的条件含义，明确 study_authorized/selectable 仅指数学方向；每页列出现有全部参数组，指定组可看到精确参数 ID，沿用原 selection 过滤和原 provenance。没有指定参数方向、科学动作或最终结构，没有扩张域或数学授权。定向合法生成/原数学拒绝回归通过（2.973 s）。语义证据模块 16 项已验证：首次 15 项通过、1 项被未提交工作树 bind 门正确拦截；提交源码后仅重跑此项通过（45.433 s），失败日志保留，没有绕过门禁。绑定后 profile 仍为 v3。

第六批 +8 原子增补后 Provider 上限 72，当前 identity `2ccd50ed9a479c194540114298bab7ddb2c895017dbdd128b42a5432a2d35c26`。Main 收到的是通用权限/导航纠正与新预算事实，无科学行动指令。原数学 20、episode 80、公共操作 160 和收尾 4 次不变，仍从原 Store 接续。
