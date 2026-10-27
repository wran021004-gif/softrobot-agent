# C4-R：正式 Study 前的动作转换与执行修复

2026-10-27，Asia/Shanghai。从 `263b3ba51aff79bc9dcb5605eedde6f84a6be029`
建立独立 `research/c4-prestudy-action-repair`，不修改 A/B 工作区。
原 C4 两阶段负结果、20 请求及 1006288 Tokens 保持不变。
本轮不开展完整 Cold-start 或 C5；只做必要修复及少量真实反馈验证。

## 门禁审计

原 C4 的“至少两个场景完整可信提案”是监督的阶段门槛，并非生产工具的统一评分器。
其冻结 rubric/no-go 不修改；本轮按新的用户要求不再把它作为真实实验的前置条件。

| 检查 | 本轮处理 |
| --- | --- |
| Plan/AnalysisRequest 必填字段、JSON、action/payload/intent 一致 | 保持硬规则 |
| 候选、源、任务、模型身份，正式权限、适用性、实际预算及子额度 | 保持硬规则 |
| pending/未知执行防重复，数值及引擎安全 | 保持硬规则 |
| SELECT/CONFIRM/STOP 正式引用、完整读取、独立验收 | 保持硬规则 |
| `admit_decision` 最后的不受支持 claimed_inference | 探索实验记录 unsupported_inference，不再因此拒绝；不升级为事实 |
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

当前处于工程定向检查、同 Store 绑定和真实闭环执行准备阶段。
本轮准入条件是硬规则可靠及至少一次真实合法、反馈可用的闭环，不要求主观科学解释满分。
科学错误、实际交互费用、反馈后的判断及正式 Cold-start 工程就绪结论将在真实执行后追加。
原空候选池 Cold-start 配置仅做离线就绪核验，本轮不启动。
