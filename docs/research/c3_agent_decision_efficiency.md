# C3 — Agent 科研决策效率验证

2026-10-26，Asia/Shanghai。Control `c153e1731ae0925e756467f75a783b28abce2873`；Treatment `5d73965e1ed52afed689a182976064a2af80ffac`。
分支 `research/c3-agent-decision-efficiency`，独立工作区；不修改原 R1/C1/C2 分支、不合并 main。

**结论：部分通过。** 精确导航与意图契约的工程收益有直接证据；真实配对未显示总体请求、工具或
Token 节省，科学判断也只有局部改善。保留 C1/C2 修复，**不建议据此直接进入下一次完整自主 Study**。

## 设计、边界与复核

先完成 C3-A，再开始 C3-B。沿用 `c3_readiness_audit.py` 的归档读取与真实工作集投影、
`agent_math_decision_probe.py` 的 `LiveBoundary`、原 Store/ProjectConfig 硬预算、
原 Plan/EvidenceQuery/AnalysisRequest、原 `admit_decision` 与纠错反馈。
没有新建 Agent harness、Provider 客户端、研究调度器、账本实现或历史状态重建器。

三个场景都取 **当时 Handoff preparation 的 `source_state` artifact 和 `budget`**，
而非最终 snapshot 的 state/ledger。归档最终 snapshot 仅用于定位事件/请求成员。
历史 host 的 artifact 读取限定为源状态及边界前事件已引用对象的传递闭包；
不在闭包的引用一律拒绝，Store transaction/reserve 禁止，SQLite 查询不可用。
因此，新的工作集投影无法向最终 Store 偷读成功结果。

| 场景 | 封存来源 | preparation 事件 | 科学状态 | 当时剩余 Provider / public / physical |
|---|---|---:|---|---:|
| A：成功前控制修正 | `b3_r1_history_assisted_050` | 425 | 当前候选 e85fc8；自身 NMPC 控制已初始化；保持速度 0.0430096818 > 0.02；native 未执行 | 27 / 56 / 2 |
| B：导航与调用错误 | 同一 R1 | 2110 | 同一科学状态；经历真实 raw/view、wrapper、range、intent 错误及授权追加段；仍无 native 结果 | 34 / 74 / 2 |
| C：数学证据仍未决 | `b3_t2_pilot_050_c` | 425 | native 有限搜索 8 rollouts/2 iterations；独立回放保持速度 0.0878877913，仍失败 | 8 / 48 / 2 |

A 的源状态是 `8a96cdd0c29c211346a2e5c33694908335ef8812109998c8088772e02c7de835`；
B 为 `466c816fa6de7b0b4b76eb7314881ae5010ae4ff6af98560bb7e3dc69f7bc269`。
C 的精确身份、全部配对源与请求引用见 `summary.json`。
C 有继续控制搜索、模型/响应诊断、T2 所需模型准备、结构对照等候选路线；没有预设正确方法。
局部有限搜索未找到通过解不能推出理论不可行；数学预测本身不能授予物理通过信用。

保留原任务、阈值、初态、候选、科学证据和历史预算。两个版本用各自冻结代码构造 research brief、
Plan Schema、EvidenceQuery Schema 和反馈；非 research 的外层字段沿用紧随该 Handoff 的原 wire。
普通会话保留该 wire 的历史；新会话使用原 `initial_messages` 和同一动态包。
两种投影的当前候选、科学约束与证据入口一致。实际 SDK rotation 另以原 mock HTTP 测试覆盖，
离线投影不冒充一次新的真实 SDK 恢复。

## C3-A：离线结果

下表为仓库已固定 tokenizer 对序列化 JSON 的 **离线 Token 估计**，不是 Provider usage。
完整 wire 包含固定提示、动态包、历史和全部原生产工具 Schema。

| 场景/版本 | decision brief | 同会话完整 wire | Handoff 完整 wire | 工具 Schema |
|---|---:|---:|---:|---:|
| A Control | 14,294 | 31,145 | 31,109 | 7,717 |
| A Treatment | 14,081 | 31,165 | 31,129 | 8,002 |
| B Control | 14,671 | 31,778 | 31,742 | 7,752 |
| B Treatment | 14,423 | 31,761 | 31,725 | 8,037 |
| C Control | 14,854 | 31,215 | 31,179 | 7,646 |
| C Treatment | 15,436 | 32,159 | 32,123 | 7,931 |

新版不是稳定的 Token 压缩：A brief 变小但 Schema 抵消收益，C 反而增加。
JSON 中同时保留字节数以及 system、dynamic、history、Schema 的分项；各自序列化带框架，不作机械相加。

- 六份源状态均未变化；两组的源状态 artifact 完全相同；全部 16 项数学方法均可见。
- 新版直接提供当前候选完整实测源 e3a06aa1、未测计划源 e76d3b34 及其不同 origin。
  未将历史来源、数学预测或初始化当作当前物理通过，也未替 Agent 选择来源。
- 当前推荐的精确查询全部可读。B 新版最近读取记录还包含一条已过时的
  `/methods/mujoco_direct_control_v1/measured_control_initialization`：初始化已完成后该节点消失。
  它是历史读取载荷，不能算作当前推荐查询；该变化不代表新的科学证据。
- B 边界前 18 条真实导航错误（包含 A 的 2 条）逐条回放：新版均返回可执行的结构化
  `corrected_query`，旧版没有这项结构化入口。**0/18 vs 18/18 衡量的是精确纠正查询，
  不是旧版完全无法解决 18 条错误**；旧版仍可按字段提示或合法 working_set 继续导航。
- 最终 R1 SELECT、selected_solution、disposition 均不在可读闭包或输入；所有科学输出均只来自边界前。

历史读取记录里，同一 working_set 查询既有科学状态变化后的合法重读，也有完全相同内容的重读。
仅凭查询载荷相同不判浪费。针对 `read_coverage` 自引用引起的 changed_content 风险，
本轮冻结包加最多一次反馈不能验证长期循环；不据此改内容身份或缓存机制。

## C3-B：真实 Provider 与审计

配置取 R1 原 `configuration.json`：`https://api.deepseek.com/chat/completions`，
`deepseek-flash`，`reasoning_effort=high`，`thinking=enabled`，`max_tokens=32768`，
`stream=false`、`tool_choice=auto`，其他原参数一致。模型别名相同；若 Provider 不给不可变版本身份，
不声称已固定其内部权重版本。

原生产工具中仅开放 `evidence_read`、`research_plan`、`research_analysis` 三项相同子集；
保留各组的真实 Schema，不提供 Reporter、隐藏上下文读取或 execute 路径。
系统提示只增加双方相同的 C3 只读边界、最多两轮和自主辨别实验要求。
首批次序 A旧/新、B新/旧、C旧/新；后续反馈批次倒序。
不把 R1 最终成功或行动排序交给任一组。

所有科学工具都只记录提案。Plan 通过真实 Schema、Plan 和 `admit_decision` 检查；
analysis 通过 Schema 和候选身份检查。**没有运行执行级完整准入，因此契约通过不等于可执行实验**。
正常 diagnose 是只读意图；显式 local_diagnostic 在生产会计算，本测试也不执行。
反馈明确未派发、没有新增观测，不伪造成功回执。

独立 Provider grant 的硬限额 12；不使用 R1 剩余额度，不自动重试、不补发、不换模型。
最初启动被自动审批以数据外发授权范围不明确为由拒绝，进程没有运行、Provider 为零；
用户随后明确确认必要科研输入向该 DeepSeek 端点外发，才启动真实调用。
独立 grant/原始请求与回执来源保留在交付证据中，凭据只用于认证、不序列化。

实际 **12/12 次请求、12 份确认回执**，没有重试、Reporter、未知发送、pending 或未消费响应。
科学 worker / NMPC / native / RL / GVS / MuJoCo 步进 / 新数学优化 / 新物理评价 / 正式 Study 均为 **0**。
R1 剩余额度消耗 **0**；R1 的 STOP、SELECT、原费用与封存证据未改。

| 配对场景 | 旧 / 新 Provider | 旧 / 新真实总 Tokens | 旧 / 新公开工具调用 | 旧 / 新 evidence_read | 原始错误 |
|---|---:|---:|---:|---:|---|
| A | 2 / 2 | 87,207 / 104,861 | 3 / 4 | 2 / 3 | 旧 intent；新 JSON |
| B | 2 / 2 | 92,886 / 83,556 | 1 / 5 | 0 / 4 | 均无工具拒绝；新有 1 次空 fields 读取 |
| C | 2 / 2 | 90,668 / 84,133 | 4 / 3 | 3 / 2 | 旧 intent；新对象 range |
| 合计 | **6 / 6** | **270,761 / 272,550** | **8 / 12** | **5 / 9** | **2 / 2** |

旧/新输入 Tokens 为 **216,886 / 219,671**，输出为 **53,875 / 52,879**；
合计输入 436,557、输出 106,754、总数 **543,311**，其中 reasoning 87,267。
Provider 还报告 cache hit 265,088、miss 171,469。费用金额未随回执返回，记为 **unknown**，
不从 Token 数猜测账单。新总 Tokens 高 **0.66%**、工具调用高 **50%**；两组 Provider 数受设计固定，
所以不能声称减少了 Provider 请求。cache/order 和模型输出长度也会影响单次成本。

没有观察到完全相同查询且相同内容的重复读取；可确认的可避免重复数为 0。
这不表示长期循环消失。B 新版 `view=fields, fields=[]` 返回 `{}`，是明确的无信息读取，单独计 1 次，
不伪装成重复读取。动态状态变化后的重读在此冻结探针中未测量。
“公开工具调用”来自模型 tool_calls 和真实只读反馈，独立 Provider 账本只计发送，不把原 Study tool_calls=0
误写成没有公开调用。

第一份契约合法提案：B旧在第 **1** 请求/第 **1** 工具，B新在第 **2** 请求/第 **5** 工具，
C新在第 **2** 请求/第 **3** 工具。其余在两轮内没有合法提案。
这些数只衡量契约准入；B旧虽最快，仍包含科学事实错误，不能直接算作最快可信科研行动。
本样本不足以给出“首个科学上可信行动”的稳健成本排名。

### 科学判断与自主性逐条审阅

| 配对 | 事实与证据范围 | 动作契约 | 实验辨别力 / 成本 |
|---|---|---|---|
| A旧 | 识别主要速度违反项、承认 math 未用；读后仍未分清两个控制源 | diagnose / CONTROL_SEARCH 被拒 | 有针对性地提出时序/支撑假设，但建议重复初始化，未形成合法提案 |
| A新 | 正确找到实测源，提出由末两点速度估计约 50 ms 时间常数的新解释；错误推断 e76 为他结构优化来源 | JSON 在字符 3956 处损坏，并混入 analysis/额外 decision 字段；不修复重发 | 有可证伪的响应实验想法，时间常数只是两点近似；预算单位和 12/19/24 回调陈述不一致 |
| B旧 | 将另一 Study 的 8000 native 步计入当前 R1，尽管当前 R1 math=0 | 首轮 Plan/evidence 准入通过；次轮仅文字 | 提案可服务任务，但来源仍未知、“唯一合法路线”依据不足；正确承认 proposal_recorded 不代表执行准入 |
| B新 | 精确区分实测 e3 与未测 e76；仍不知道 tendon 顺序/active 索引 | diagnose / DIAGNOSE 合法 | 有目标、active set 和余量意识；却把有限局部失败当成排除模型失配/权重路线的证据；只计后缀的成本估算未证明前缀及窗口准入 |
| C旧 | 指标正确；从一条预测/回放逐位相同推广模型可信，断言同 caps 再搜不能改善 | diagnose / MATHEMATICAL_ANALYSIS 被拒 | 想切换能力/制动路线有自主性，但 task_capability/braking + MuJoCo 组合未核准；1–2 次数学预算只是猜测 |
| C新 | 承认 `/samples` 未读到，保留同源复用、参数化、结构权限和搜索预算等解释 | 首轮 range 错误，次轮合法 diagnose | 提出有价值的有界对照，并明确有限搜索不排除可行性；同时称“零物理成本”又列 8000 积分步，须区分机会预算与真实计算 |

所有组都把当前物理失败与尚未执行的提案区分开；未发现把 C3 的反馈说成新通过结果。
但“method 选得具体”与“实验足以识别机制”仍有明显差距。
例如 B新声称有限 native 搜索仍失败就说明残差不是模型失配/权重问题，
没有排除参数化、初始化、局部优化和搜索预算不足；这不是一个可靠的机制判别。
C新则明确保留“预算不足也能导致同样负结果”，是本轮较好的科学自主性例子。

Treatment 三个场景最终均倾向 native；Control 两个倾向 native、一个提出能力/制动分析。
新版实际没有读取其他候选或 T2 细节。完整 16 方法可读只证明可见性保留，
**不能据此证明研究视野和方法切换能力没有受压缩影响**。
原历史边界本来就突出终窗速度和已有控制源，样本又只有三对，不能归因“新版固定诱导 native”。

### 哪些变化可以归因

1. **字段导航**：同一真实错误在新版有精确可读修正，属于确定的工程收益；
   真实配对没有发生 wrapper/raw-view 混淆，因而尚未测得对应的恢复请求节省。
2. **控制来源直接交付**：新版 A/B 能精确使用 e3 的 origin，B旧仍疑惑两源身份；
   但新版并未少读，新版 B 反而读取四次，其中一次为空。
3. **意图 Schema**：同一封存错误在旧版通过 Schema 后由 runtime 拒绝，新版由 Schema 的动作映射拒绝；
   实际旧版 A/C 两次错配、新版零次。机制清晰，样本不足以推断长期发生率。
4. **科学判断**：C新版更谨慎，B新版仍作过强负结果归因，A新版输出无效；没有一致提升。
5. **随机性与完整成本**：A新版首轮 reasoning 为 19,831，旧版为 7,356，是成本差的重要来源；
   B/C 的较少输出不能单独归因上下文整理。没有重复、调 Prompt 或筛掉失败输出。
6. **精简的新风险**：历史动态查询可能过时，完整请求 C 更大，当前候选/原生模板更显眼；
   尚未确认这造成了实际遗漏或 changed_content 循环，因此本轮没有修改生产代码。

### 后续判断

工程接口修复值得保留；当前证据不支持“整体科研决策更快、更省”，也不支持普遍退化结论。
若进入下一步，应先另行开展少量有辨别力的决策验证，检验有限负结果的因果范围、
精确方法适用性、完整计算成本及在证据充分时切换研究路线；不以再开发上下文工具替代判断。
本轮不启动该验证或完整自主 Study，也不追加 Provider 额度。

## 评价口径与限制

逐份使用可复核的事实、行动契约、实验辨别力和成本意识判断，不调用第二个 LLM 评分，
不用加权总分，不规定 native 得高分。实验辨别力要求说明不同观测如何改变后续选择；
提出一个方法名或详细但不可执行的参数并不足够。
首次“有价值行动”指本探针中合法且有依据的研究提案，不是实际产生了新科学结果。

这是每组每场景最多两轮、单样本的冻结决策测试。原 R1 的长期 SDK offload/动态工作集不在这里重跑。
第二轮收到真实只读结果及相同冻结包的历史，不重新消费 R1 预算、不生成新科学证据；
读取覆盖元数据没有按新探针读取重建，故不能归因动态 changed_content 循环是否改善。
归档 host 不连接原执行链 SQLite；本轮使用源状态中已初始化、可完整读取的控制 schedule，
不再次提取/生成 NMPC 的实测控制，也不验证执行链文件解析或完整执行准入。
观察到相同内容仍要结合复核目的判断；没有充分依据的重复不一概计为可避免浪费。

## 代码与定向检查

仅扩展既有两个审计/探针文件，并在既有 probe 测试中增加一个共享硬额度检查。
生产科研代码没有修改。新增范围只涉及三处冻结源状态、两轮只读调用及紧凑结果记录。

- `test_b_decision_evidence_clarity.DecisionWorksetTests`：4 项通过。
- 真实 SDK mock rotation 和旧 Schema 验真后更新：2 项通过。
- 既有 derived delivery 分类检查：1 项通过。
- 既有 unknown outcome 禁止重发：1 项通过。
- 新 C3 两轮共用 12 次额度、拒绝第 13 次和重复启动、零 dispatch：1 项通过。

发送前的离线审计尝试暴露 helper 对 Schema 描述对象、旧版无描述常量、空 navigation 的兼容问题，
以及历史查询和当前查询混算，均在发送前修正；未筛选/替换科学案例。
新增 mock 检查初次误复用了真实 grant，被原 `GRANT_ALREADY_BOUND` 正确阻止；
改为独立 mock grant 后通过，没有重置或扩展真实额度。
未跑全量 pytest、科学回放、优化、训练或压力测试。

## 交付与复核命令

- [summary.json](../../evidence/c3_agent_decision_efficiency/summary.json)：配对身份、字节/离线 Token 分项、真实 usage/账本、逐份判定依据。
- [decisions.json](../../evidence/c3_agent_decision_efficiency/decisions.json)：12 份原输出、tool arguments、反馈状态及请求身份；保留无效 JSON，不猜测修复。
- [provider_trace.tar.gz](../../evidence/c3_agent_decision_efficiency/provider_trace.tar.gz)：原独立 Store SQLite 快照（含原始请求/响应 body/收据）、冻结包及各次只读反馈。约 1.47 MB，凭据内容扫描通过。

在仓库根目录运行 `python -m tests.research.agent_math_decision_probe c3-freeze --out <新的 runs 子目录>`
可零 Provider 重建离线六份输入；需要指定两个原提交的工作树（脚本中 `C3_ROOTS`），
Treatment 允许本交付提交的测试/报告增量，但检查生产目录仍等于 5d73965e1。
`c3_readiness_audit --decision-efficiency A|B|C --evidence-root ... --output ...`
可单独检查边界。**live 命令不用于复核**：原 grant 已用满，重复启动被拒，不能拷贝目录造新额度。
Provider trace 中的 SQLite 只用于读回原记录。
