# C4-R：正式 Study 前的动作转换与执行修复

2026-10-27，Asia/Shanghai。从 `263b3ba51aff79bc9dcb5605eedde6f84a6be029`
建立独立 `research/c4-prestudy-action-repair`，不修改 A/B 工作区。
原 C4 两阶段负结果、20 请求及 1006288 Tokens 保持不变。
本轮不开展完整 Cold-start 或 C5；只做必要修复及少量真实反馈验证。

**当前结论：工程硬准入与最小真实反馈闭环已观察到；本轮完成。**
新闭环14次请求、575452 Tokens，一次完整有效但速度失败的 NMPC；Agent 读取并据此初始化实测控制后 STOP。
没有完整任务通过。自主效率、Native 请求首发准确性和科学推理质量仍未证明改善。
按本轮新的进入条件，后续 Cold-start 的工程启动条件已满足；本轮未启动它。

## 门禁审计

原 C4 的“至少两个场景完整可信提案”是监督的阶段门槛，并非生产工具的统一评分器。
其冻结 rubric/no-go 不修改；本轮按新的用户要求不再把它作为真实实验的前置条件。

| 检查 | 本轮处理 |
| --- | --- |
| Plan/AnalysisRequest 必填字段、JSON、action/payload/intent 一致 | 保持硬规则 |
| 实际候选/源/任务/模型绑定，注册引用，正式权限、适用性、实际预算及子额度 | 保持硬规则 |
| pending/未知执行防重复，数值及引擎安全 | 保持硬规则 |
| SELECT/CONFIRM/STOP 正式引用、完整读取、独立验收 | 保持硬规则 |
| `admit_decision` 最后的不受支持 claimed_inference | 探索实验记录 unsupported_inference，不再因此拒绝；不升级为事实 |
| 已注册证据跨设计/模型或已声明背景跨任务的推论外推 | 合法实验保留并标记 claim_scope_issues；正式结论的范围要求仍是硬规则 |
| 竞争假设完整性、信息价值、最佳路线、因果解释 | 事后软评价，不自动阻断合法实验 |

`evidence_policy.admit_decision` 仍解析真实注册证据及身份，保留原 Plan 的原始推论。
不支持的强推论在探索动作的收据/工具反馈中单独标注；正式收尾仍需可信证据。
机制解释的自由文本不经新增评分器，也不从自然语言方法名自动派发。
实际 worker 继续负责来源绑定、执行权限、适用性、预算和原验收。

## 上下文与动作转换

先用原冻结真实请求与已准备闭环状态审计，标量记录在 `evidence/c4r_action_repair/before_audit.json`。
准备状态 packet 为 51475 bytes，离线序列化估计 14379 Tokens，其中 research 9376、
controller_capabilities 2414、family_space 1638。估计不等于 Provider usage，分项不能直接相加。
旧 C4 还存在 32768 输出 Tokens 全为推理而无工具动作的确认截断；不能把浪费全部归于 evidence_read。

继续使用原 L0/L1/L2、read_coverage 和 Handoff。L0 保留任务、当前失败项、候选/控制引用、
方法状态、授权和预算。大型控制器参数 Schema 由原注册 owner 生成，移到既有 L1 working_set
`/controller_capabilities/parameter_schema` 精确查询；原字段语义在完整 L1 视图保留。
数学成本说明、执行子上限及剩余额度仍在 L0；统一模板查询格式不改注册模板。
精确匹配已选方法时，一次查询获取其模板、必需参数、权限与成本。
固定系统前缀、Strands 和工具路由保持；没有第二套上下文/记忆系统。

只读 diagnose 现在明确回报是否提交了执行 payload。缺少候选时指出需要选择候选；有候选时给原方法目录入口。
这份提示不推断自然语言、不默认选择方法、不偷偷计算。真实科研仍须 Agent 自己提交合法 Plan/AnalysisRequest。
原 regularization 精确纠错、空 fields 拒绝、L0 引用资格、约束覆盖解释和历史隔离继续保留。

## 最小真实闭环范围

复用原已准备、已授权的 `c4-feedback-loop-20261026`，原 Store 位于 C4 worktree，
不复制 Store、不重置 grant、不借用已耗尽的 Provider-only 配对额度。
resolved_identity `c6c451a57c78b14e8837808be5d52d41c131c8c452f6b01ead4ddcf5e436b89c`。
已由原 require_authorization 确认绑定授权；开始前原账本 Provider/public/backend/worker 用量全零。
使用原失败历史候选/控制和有限数学背景，没有成功控制注入。

初始有限上限沿用原授权：Provider16（收尾保护4，Reporter共享）、public40（保护8）、数学4、
共享物理4，其中 NMPC≤1、完整固定回放≤3，PPO=0；Native 每项≤60 callbacks/2 updates/4 knots。
最多两项数值研究动作，随后读新结果并给下一步判断/STOP；若独立完整通过则按原 SELECT 收尾。
本轮不要求找到可行解，不扩大优化来消耗额度。必要 Provider/public 有限追加须在同账本明确记录，旧用量保留。

用户最新授权允许自行设定额度、必要追加及中断修复，无需再次询问。
模型仍使用已批准的 DeepSeek deepseek-flash、原端点和必要科研数据范围，不外发凭据或隐藏历史成功答案。
工程提交后依原 bind 迁移实现，冻结科学配置/任务/验收保持不变；未知外发和 pending worker 先核对原回执再恢复。
监督只检查执行链与账本，不代 Agent 选择或执行科学动作。自动监督 `c4` 已按本轮新范围恢复。

## 验证与交付状态

十项直接相关检查通过：不支持推论的实验准入及正式收尾拒绝、伪造引用、任务/模型/设计范围、
必需 decision、action/intent、动作 payload，以及旧精确查询/选定方法投影。投影最终调整后只重跑对应一项，
没有全仓回归。另用已准备原 Store 零计算核验，L1 控制器 Schema 与原完整字段逐项相同，
原任务/最佳失败项/候选来源/引用资格/授权/预算/Native 成本口径保持。
`e638546d6`首轮工程投影的同状态 packet 从 51475→44761 bytes、离线估计14379→12669 Tokens（减少1710，约11.9%）；
后续模板前提查询补全不在这次数值比较中。这是序列化估计，不能推断终版实际交互成本或理解改善。
真实 usage 在闭环后独立报告。

首次独立预检因未设置原冻结单线程变量而停止；显式采用原三个值后通过，没有更换依赖。
首次跨 worktree bind 在事务前因代码根目录下缺原授权锚点失败，原状态和用量未变。
没有复制授权索引或账本：保留原 C4 分支 `263b3ba51`，将原 grant 所属执行 checkout 临时置于
已提交的 C4-R `e638546d6`（detached），通过原 bind 成功迁移。
文档与代码开发仍在独立新分支；A/B 工作区不动。原科学 profile/config/候选/用量相同，
新范围正式授权与 Handoff admission 已绑定，见 `loop_binding.json`。

真实闭环已按原 STOP 规则结束，实际结果见下文。
本轮准入条件是硬规则可靠及至少一次真实合法、反馈可用的闭环，不要求主观科学解释满分。
科学错误、实际交互费用、反馈后的判断及正式 Cold-start 工程就绪结论将在真实执行后追加。
原空候选池 Cold-start 配置仅做离线就绪核验，本轮不启动。

## 首项真实执行后的具体入口修复

首项 Native 请求经原工具返回 not_applicable：标准初态在0 s，请求却把校正窗设为[0.4,0.5]；
没有新数学计算，additional_analysis_evaluations=0。随后一次 NMPC Plan 缺 hypothesis，
生产精确反馈后 Agent 自己补齐，第四次请求的合法 Plan 启动真实 NMPC。
该完整有效执行返回终点误差0.00314837 m、保持位置0.00603803 m，保持速度0.11137394 m/s：
速度未过0.02 m/s，位置两项通过，没有通过任务。Reporter 与公开读取已交付；
Agent 依据本次 NMPC 的真实输入提交 initialize_control，创建候选绑定的未测开放环序列。

八次 Provider、303628 Tokens 后在原已结算 SupervisorReviewPause 边界复核，
没有 pending、未知外发或未消费响应；仍有8次 Provider、原科学余量未重置。
这期间两次相同 Native 模板叶节点读取暴露了入口缺口：该叶节点只给模板，必需的
窗口/状态前提在相邻 required_parameters，模型未同时获取。
因此调整原 `request_template_query` 的查询投影，改为同一方法的字段读取：
candidate、operation、request_template、required_parameters、formal_execution_authorized、
missing、可用 execution_limits 和 cost_scope，一次返回。原叶节点及全部旧指针仍可读，
不增加工具/路由，不推断所选方法，不填控制源、参数或科学答案。
这项修复基于本轮真实错误，在结算边界依原 bind 接续同一个 Study，不改旧冻结样本或评分。

## 真实闭环最终账本与证据

原 Study、Store、grant 和科学 profile 不变，未追加额度。8次暂停时复核尚余8次，
只释放原监督计数暂停，保留总16/保护4；后续按原预算收尾。
`final_review.json` 给出逐项标量、引用与错误；原 Provider 推理、原始数组和私有 Store 不发布。

| 项目 | 实际结果 |
| --- | --- |
| Provider | 14请求/14确认；主Agent13，Reporter1；无未知外发、截断或自动重发 |
| Tokens | 输入506367、输出69085、总575452；reasoning55268已含在输出；金额unknown |
| 首个合法数值动作 | 第4请求，累计155761 Tokens；Agent自己提交完整 Plan，原入口实际执行 |
| 新反馈已用于下一步 | 第8请求，累计303628 Tokens；读取当前结果并转录本次实测控制 |
| 工具尝试 | SDK17次：读取8、Analysis2、Plan7；公共总账已用20，含原NMPC子操作 |
| 实际科学动作 | NMPC1；完整独立验收1；Native/其他数学评价0；固定完整回放0；PPO0 |
| NMPC内部 | 实际求解5次、控制更新50次；原完整0.5s/0.0005s时网格，1000物理步 |
| 测得计算时间 | 结果numerical_s=470.9851803；simulation_wall_s=468.985；总numerical资源472.2953282s |
| 原账本剩余 | Provider2、public20、共享物理3；数学4、完整回放3；NMPC0；occupied为空 |

这里的数学评价0不表示 NMPC 无数值计算。NMPC内部求解使用原独立执行预算；
两次 Native 不适用均未启动数值 worker。内部预测积分步没有作为独立物理回放次数相加。
总资源时间与原ledger逐项保留，不能把准备至收尾的墙钟间隔当作纯计算费用。

新独立结果 `2ebd45f891344ea6a11001de73f29356f880a9c12e918eecdc153854e960bfd9`：
valid_failure，终点误差0.00314837265m、保持最大位置误差0.00603802748m（各≤0.01m）；
保持最大速度0.111373944m/s（要求≤0.02m/s）。完整覆盖、张力边界、solver_errors均合规，速度失败。
这是真实失败观测，不是软评分或工具链错误，也不证明结构不可行。

Agent 将原“反馈能消除残速”假设，更新为“0.40s接受后的末段计划缓存/张力尾段激发”待检验问题；
使用新 NMPC 的精确 candidate/parent/execution 做 initialize_control，产出完整但未测的输入序列，
没有继承验收。这个后续动作确实绑定新证据，满足最小“执行→交付→下一步”闭环。
最终公开读取原 all_fresh_results 索引并引用唯一新数值结果，STOP成功；没有 SELECT 或额外科学动作。

## 保留的错误与最后的反馈修复

本轮没有因科学解释不完整而提前禁止真实 NMPC，但模型仍犯了以下执行/解释错误：

- 两次 Native 将晚窗[0.4,0.5]、[0.35,0.5]与0s标准初态混用，均不适用，数学支出0。
  第二次发生于模板投影修复后；没有观察到模型读取新组合查询，不能声称该修复已改善其行为。
- 一次 NMPC Plan 缺必填 hypothesis，收到原精确反馈后自己补齐；另有一次错误 `/samples` 引用。
- 两次 Plan control_search 请求20、12 callbacks，均超过冻结声明上限5（physical_launches+一个可能复用的基线）。
  两次均是同一容量拒绝，没有任何修正数值执行。Agent 的 STOP 解释却称12已通过容量后遭遇未知ValueError，
  与原回执不符；还曾把剩余3次完整回放说成耗尽。这些错误独立记录，不升级为事实。
- 一次 STOP 使用不受支持的推论标签，被原正式证据门禁拒绝；之后改为 empirical_search 并正确引用后收尾。
- 8次读取中SDK确认7次成功，read_coverage仅能确认其中5次完整交付（3新查询、2exact_repeat）；
  不能将未确认覆盖当交付失败。一个相同查询签名发生复读；核验用途和是否新增信息分开评价。

真实错误说明仍有反馈交付缺口，故在原 STOP 后做最后两项最小表达修复，**不重开研究或刷样本**：
`not_applicable` 的真实原因、未启动标志及0评价支出直接出现在原 execution_feedback；
批量容量拒绝明确指出实际字段、请求cap、冻结上限、剩余共享启动/完整回放，以及 Plan物理回调与Native内部积分的区别。
原完整反馈/异常/结果仍可追溯，原硬检查和路由没有改变。对应定向检查通过；这些最终表达变化没有再做真实Provider行为测试。

最终硬/软审计同时补足：引用已注册的其他设计/模型或已声明背景作为实验依据时，
过强的推论外推会标记 unsupported_inference/claim_scope_issues，不阻断合法实验；
未注册引用、不允许的跨任务引用及实际 payload 的候选/控制/任务绑定仍拒绝，正式结论仍需原身份范围。
定向用例覆盖合法实验与正式STOP的不同结果，没有增加科学可信度评分器。

## 后续正式研究的启动条件

原空池 Cold-start 已离线核验：reference/selected=null、候选/历史/数学/控制种子/supplied_evidence为空，
原任务/profile/全部阈值不变，首个结构仍由 Agent 自己 generate。候选域没有人工缩窄，无历史成功答案导入。
新实现绑定、原formal scope、环境及L1查询在零Provider/零科学条件下通过。
原 request-feedback Handoff 已单独绑定该准备 Study，原 `converse(restore_only=True)` 也通过，
没有发出模型请求或加入科研对话。不是只检查配置文件存在。
最终实现绑定记录见 `final_readiness.json`；这些准备不会创建科学候选或当前结果。

工程启动条件为：原契约/身份/授权/实际资源/工具适用与安全可靠，并已观察到至少一个真实合法、反馈被使用的闭环。
本轮已满足；不再要求多个只读案例主观科学解释满分。完整 Cold-start 仍不在本轮执行范围。
后续正式研究需持续记录 Native 请求、预算理解及机制推论错误，不能宣称现在已具备高效可靠的自主科研能力。

后续范围包含完整 Cold-start 时，可使用以下原入口。原授权归属执行 checkout 已固定在
`2c64f5a50`，避免复制 Store/授权索引；修改实现应先走原 bind 迁移。这条正式运行命令本轮**没有执行**：

```powershell
Set-Location 'D:/softrobot-agent/.worktrees/c4-decision-efficiency-coldstart'
$env:MKL_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
$env:OPENBLAS_NUM_THREADS='1'
& 'D:/softrobot-agent/.worktrees/s135-task-conditioned-control/.s135-env/Scripts/python.exe' -X utf8 -m tools.research run --run-id c4-coldstart-reach-hold-20261026 --session-handoff --handoff-request-bytes 160000 --pause-exploration-remaining 4
```

监督 Codex 完成的是工程修复、账本/进程核对、实现迁移与故障恢复；科学方法、NMPC执行和控制转录由主Agent选择并提交，
数值计算/验收由原程序完成。没有监督代做搜索或给出成功控制。
正常进程未被重启，原失败及成本完整保存；本轮最终报告发布后暂停自动监督。
历史C4与本轮分别记账，合计34请求、1581740 Tokens；这不是冷启动到首个可行解的成本。
