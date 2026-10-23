# S134 科研上下文与数学证据交付

完成日期：2026-10-23（Asia/Shanghai）。基线为远端核对后的
`feat/s132-tracking-task@4eb740f932d1cd01ece575777c0fcef4bc646880`。
独立工作树 `.worktrees/s134-research-context`，分支 `fix/s134-research-context`。
代码提交：`1846dbec`。本轮没有获得新远端目标的推送授权，保持本地提交。

## 修复与边界

- `capability.py` 识别旧 CONIC 与 PATH 两个版本，沿用原数量强度解释，修复 PATH
  `quantities` 采用 `strength` 而非 `status` 引起的异常。摘要保留有符号值、support/gap、
  数值最优性、实际覆盖、进度、角点分支/并列、内部求解次数、模型范围及原始指针。
  `analysis.py` 和 `evidence_views.py` 按 `path_bound.radius` 投影路径阈值。
- Reporter L1 不再按前三项指标或前三个结果截断。它保留每项数值验收指标的阈值、
  原始 passed、单位和数值/阈值来源。Reach 明确标出终点位置误差、保持最大位置误差、
  保持最大速度；Tracking 直接使用它自己的评价契约，不补入 Reach 保持指标。
  搜索卡交付最佳评价及其指标、停止原因、实际资源和完整步骤入口，不展开所有中间 probe。
- 对有适用后续纠正、但未读入纠正的旧 Reporter 解释，L1 标记
  `superseded_pending_reinterpretation`，当前只交付确定性事实。原解释、来源校验状态、
  错误/拒绝及原报告不变；该标记不判定整段旧解释全部为假。显式 investigation 会把对应
  纠正子节点加入 selected reads；消费纠正后的新解释可以正常交付，不自动重发 Reporter。
- 默认最近五条 trace 移除完整父假设/解释/预期观察，保留行动、方法、候选、执行状态、
  结果概要、receipt 和原来源。完整 trace 仍由原 working_set 查询获得。
  当前显式研究意图单独保留；同一计划的 latest_decision/last_research 只展开一次。
  假设原文、削弱观察、supporting_evidence 和计划引用仍可读，不自动认定“最新即科学有效”，
  也没有新增假设生命周期或长期记忆系统。
- 数学目录绑定当前明确研究意图/结果中的候选，候选不明时要求先选候选；不再随意选择最后
  生成的候选。共同候选/任务绑定只展开一次。目录有 10 种既有 analysis operation 及 T1/T2
  两种模式，区分内核支持、已构建模型、覆盖、冻结 grant、正式授权、执行前提、缺失输入、
  成本与限制。模型存在不等于模型已适用于所有工作点，conditional 也不等于已通过最终准入。

没有改数学内核、Registry、Store/receipt、SDK 历史、Live Handoff、Provider 恢复或封存 F3。
生产修改集中在 7 个现有文件，新增 196 行、删除 45 行，无新增生产模块。

SOCP 数值 `numerically_checked`、独立浮点重放、解析下界与严格最优值分别保留。
`optimal_value`/`rigorous_upper_bound` 仍 unavailable，物理验收仍独立；正值或求解失败不被
升级为无限完成时间不可行、严格全局最优、结构必要性或机器人成功的证明。

## 可使用的按需入口

已有 `evidence_read` 现在先构建同一候选的派生数学能力视图，再应用 JSON Pointer。
根部保留旧 T2 readiness/planning/variables 字段，附加 methods 和原 AnalysisRequest Schema。
例如用真实已拥有的候选替换下面的引用：

```json
{
  "reference": {"artifact_id": "<owned candidate sha256>", "media_type": "application/json"},
  "view": "mathematical_capabilities",
  "pointer": "/methods/controllability"
}
```

其他节点包括 `/methods/task_capability`、`/methods/sampled-affine-conic-minimax-v1`、
`/methods/controlled-capability-sensitivity-v1`、`/analysis_request_schema`。
详情包含适用性、覆盖、数学含义、结果强度、所需补充参数、调用模板和 Schema 查询。
需要 saved state、配对候选或完整 stencil 的模板明确列出尚缺字段，不能直接当成可执行请求。
原 native 工具名称、required/enum/$defs/互斥校验均保持可见。

主 Agent 已明确用规范方法名 selected_method 选择某方法时，下一包直接附该方法详情。
它也可按原 Schema 直接调用已知方法，或与其他必要只读查询合批；不强制增加发现回合。
自由文本 selected_method 不做猜测式路由。其他数学/控制行动继续由原 available_research_actions
和原工具契约表达，本目录不声称覆盖任意未来算法。

## 离线验证

代码回归 117 项通过，53.168 s；最终新增交付复核 8 项通过，7.825 s，包含：

- 旧 SOCP、PATH 直线、折线分支及正违规/并列分支，经过 tool summary → ResultCard →
  ScientificReport → Reporter wire/source catalog → L1 → 主 Agent 数学视图；原指针逐项复读。
  新交付 fixture 明确是合成契约数据，复用已保存 S132 数值，不构造新机器人科学结果。
- 原 Reach、S130、S132 Tracking/CONIC/T2 回归；原 SOCP 语义和未认证状态不变。
- 封存 F3 成功结果三项硬指标全部投出且各自 passed=true：终点约 9.24463 mm、
  保持最大位置误差约 9.77175 mm、保持最大速度约 0.0191342833 m/s，均复读原来源。
- 保存的 Tracking evaluator 各案例全部数值约束及 passed 保留，不沿用 Reach 字段。
- 纠正后的旧解释不作为当前解释重新交付；原报告与校验状态保留；显式调查读入纠正。
- 五条短 trace 的来源、结果、receipt、状态仍在；当前假设及削弱观察仍可读。
- 两候选查询不混淆模型来源/就绪性；当前候选不被最后生成候选替换；Tracking 内核支持
  不会被目录宣称为可执行机器人方法；详情入口及普通方法调用模板可验证。
- 离线真实 SDK/MockTransport 接续回归及 Schema 保留。测试中的模拟边界错误日志为故障注入；
  原合成 dual-face 测试仍有 Clarabel inaccurate warning，没有因此提升数值证据强度。

一次旧测试失败仅为 `test_mainline` 的导入路径；加入既有测试目录 PYTHONPATH 后重跑通过。
推荐复现命令和完整模块列表见 [validation.json](../../evidence/s134_delivery/validation.json)。

新真实 Provider 请求、Study 科学执行、物理 rollout、NMPC、PPO 均为 0。
现有解析/数值离线回归只验证实现，不登记为新的科研证据。

## 保存请求的静态对照

使用 S133 索引的四份真实 F3 wire；只读 SQLite 连接强制
`mode=ro&immutable=1`、`query_only=ON`，写事务立即拒绝。
仅在内存中替换列出的 packet 投影，SDK 历史、system、native Schema 逐项相等。
科研事实、合法行动、预算、任务、trace 原引用及每项验收数值覆盖均断言保留。
方法描述按该请求的候选、profile、implementation、已注册模型前缀与剩余数学次数重建；
这不是对历史决策/执行状态的完整运行重放。

| 请求 | 原 wire bytes / 估计 tokens | 当前 S132 纠正投影基线 | S134 投影 |
|---|---:|---:|---:|
| 87ce80cb… | 1,146,090 / 333,646 | 1,133,450 / 328,806 | 1,102,887 / 320,572 |
| f8fb8f97… | 209,579 / 63,978 | 196,939 / 59,138 | 170,572 / 51,921 |
| 24dce98e… | 446,119 / 136,633 | 433,479 / 131,793 | 403,973 / 123,502 |
| 9dc07ec3… | 563,300 / 174,587 | 550,660 / 169,747 | 519,387 / 161,974 |

相对当前代码基线，本轮再减少 26,367–31,273 bytes、7,217–8,291 个离线估计 tokens。
原 wire 到当前纠正基线每份减少的 12,640 bytes / 4,840 tokens 属于已完成 S131 修复，
不计成本轮新增收益。

最终请求的分段原始字段大小如下；完整四请求和逐段 token 估计见
[offline_comparison.json](../../evidence/s134_delivery/offline_comparison.json)。

| 字段 | S132 基线 bytes / 估计 tokens | S134 bytes / 估计 tokens |
|---|---:|---:|
| action_trace | 35,327 / 10,416 | 5,101 / 1,741 |
| research_intent | 11,605 / 3,003 | 6,402 / 1,675 |
| mathematical_capabilities | 14,058 / 3,256 | 12,345 / 3,339 |
| latest_reports | 6,086 / 1,901 | 13,480 / 4,407 |
| packet 消息（含 JSON 转义） | 148,013 / 45,833 | 116,740 / 38,060 |

能力目录字节下降但此样例 token 略增，补齐的报告指标/来源/搜索成本也使 L1 变大。
保留这些科学信息优先于最大 token 节省。tokenizer SHA256 为
`89085f12ef79460ac5f66d1119325ddfc694b4ab209d80bbd81d35f081dc9614`；
不含 Provider 精确聊天模板，独立分段 token 不可相加为精确整请求数。

原四请求实际 prompt usage 分别为 319,396 / 60,221 / 130,283 / 166,521，继续原样保存在
对照 JSON。新请求未发送，实际新增 Provider usage 为 0；没有已实现账单节省或科学决策质量
提升的实测结论。理论输入减少、实际 usage、模型决策质量是三个不同结论。

F3 数据库前后 SHA256 同为
`1e090b2d152bd9a46ac89c24272b5dbeb765ed63aadd30bfb395ea5dbd4dccc6`。
F3 原有 12 个未跟踪封存导出保留，S132 原工作树干净。S133 五份外部审计的路径与哈希记录在
validation.json，不改写原审计文件。

## 无需修改与仍缺能力

S131 纠正精简、latest feedback 与报告的同源关联、真实 request-feedback Handoff、SDK Offload、
Store 和 receipt 已有机制足够，未重做。没有新的 Agent、数学内核、证据数据库或记忆系统。

仍缺 Tracking 的机器人模型/初态构建、控制器与执行绑定、完整独立组合验收及新正式授权；
T2 仍需当前候选的受控模型组。PATH 的正式准入/旧 planning 仍以 B=1 计数，而当前正式
Tracking 入口整体拒绝；目录已给 M×B 与模型准备另计的成本边界，未来放开执行前必须先
统一准入计数。墙时未知，内核已实现不能补齐这些生产能力。

## 后续决策专用 A/B 建议（未执行）

仅三个代表场景：NLP strict-false 与约 1.6e-14 m/s 残差、Untimed PATH 有限时域与未覆盖
几何验收、T2 已授权但缺当前模型组。每场景原/新两臂各一次，共 6 次主模型请求；
每次 max_tokens 建议先限 2,048，总输出上限 12,288，科学执行/Reporter 额度 0。
先冻结六份确切 wire，再据其输入和模型价格申请实际请求预算，不在本轮执行。

固定模型/采样/任务/候选/Schema/证据/合法动作/预算。逐案评分是否准确引用残差和来源、
区分有限时域与全任务、识别模型/授权/成本缺口、选择合法且有辨别力的观察。
同时记录真实 usage/缓存/错误；一格一次仅作语义冒烟，不能推出统计性决策提升。
上下文精简与补充纠正/指标是共同变化的因素，若要归因于长度，需要另作因素控制。
