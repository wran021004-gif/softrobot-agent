# C4：决策效率与无基线 Reach/Hold 研究

2026-10-26 起，Asia/Shanghai；2026-10-27 完成初轮及一次新状态复核，结论 **no-go**。
**尚不能证明三项能力整体改善，C4-3/4 未启动；未得到自主冷启动可行解。**
累计 20 次真实 Provider 请求、1,006,288 Tokens；科学 worker/物理步/Reporter 均为零。
不启动 C5/B2 外力自主 Study，不增加数学方法。以下准备与授权记录按发生顺序保留，当前结论见文末。

## 基线与最小修复

指定基线 d20cf4ee047d1b5d16befacdee52ed5a3d3905e3；开始时集成分支最新为
d7b0f91f966ef96fa17b181ead99dff9a2d457cc，仅多两份集成状态文档的修改，科研代码相同。
从最新集成建立独立 `research/c4-decision-efficiency-coldstart`，不触碰主工作区和其他研究。

已审阅 C3、C3.2 和 C3.3 真实负结果及现有路由、证据、成本、Handoff 链路。
空 fields 拒绝、精确字段纠错、Native 路由和预算说明已经存在，不重复实现。
没有证据证明靠进一步扩写系统提示就能修好模型判断，因此不做这一改动。

初始生产修改位于 `research_context.decision_brief` 的读取状态说明：
原来整份会话状态摘要变化便提示 `changed; reread to compare content`；现在明确表示
“状态变化，查询内容是否变化尚未验证”，要求读取服务于缺失事实或相关变化的核对。
不改变系统指令、工具 Schema、读取权限、科学事实、内容身份、预算、方法选择或执行。

直接复现：封存 R1 preparation 445→465，只改变 pilot 内的会话编号、Handoff、核验和
live_model_requests，所有非 pilot 状态相同。原措辞把这些变化当成复读理由，证据不足。
原 read_coverage 在 R1 中识别 147 条成功反馈，其中 62 条能确认已完整交付，包含
34 条 exact_repeat。其余只是该解析器不能确认完整交付，不等于未交付；34 条也不能全部
算浪费，SELECT/STOP 核验和用户要求复核可能合理。原记录不改写。

## C4-2：冻结的行为对照

复用 `agent_math_decision_probe.py`、`c3_readiness_audit.py`、原 LiveBoundary 和 Store。
只增加自选历史边界参数、C4 freeze/live 入口及精确授权绑定；没有第二套 harness、账本或上下文系统。

| 场景 | 来源 / preparation | 当时已有事实 |
| --- | --- | --- |
| A | R1 / 383 | 两个候选的 NMPC 观测；位置满足而速度失败；当前数学为零 |
| B | T2 pilot C / 354 | 有限 Native 搜索及候选绑定控制；其后独立回放尚不可读 |
| C | C3 math-search / 473 | 六项模型结果、一次失败回放、一次失败 NMPC；存在控制/实现/结构竞争解释 |

精确源身份、评分标准、权限、顺序和限制在 `tests/research/fixtures/c4_decision_protocol.json`。
三者都不同于 C3.2 N/K/M 的原冻结 source_state；仍有任务和档案谱系相关性，不称完全盲测
或统计独立。A 的两候选速度差异也不能作为同结构控制改善的因果证据。

Control 固定最新 C3.3 集成代码；Treatment 只增加上述 C4 提示修复。
因此本次估计 C4 增量，不能把 C3.1/C3.3 的效果混入。两组可见源状态、方法集、剩余额度
相同；保持历史缺失的准入前提，不制造权限。
两组使用干净的请求会话，不复制历史模型推理或后续成功结果。

第一次真实发送前，`c4-freeze` 保存两组生产工具/动态包、固定系统信息、完整首轮输入来源、
代码提交、逐份 wire 哈希、离线大小和精确查询核验。未来输出由实际只读边界拒绝。
输入、原输出、推理及 Store 只留忽略的 runs，公开只提交标量与来源。

首轮六次；仅当观察真实反馈后的纠错/判断更新确有必要，才倒序执行第二轮，合计最多十二次。
允许多个合理方法；不告诉 Agent 正确路线。所有提案均未执行，反馈明确 full execution
admission 未测，不能把 Schema 合法算作工具执行成功。C4-3 才验证真实执行。

首次可信提案需同时满足事实范围、合法具体调用和有辨别力的科学判断；累计报告请求、Tokens、
工具、读取、纠错及成本。至少两个不同场景通过且无严重证据/权限/费用错误、没有明显增加无效
交互负担，才进入 C4-3。失败时最多一次真实问题修复，使用新状态及原剩余额度，不刷原样本。

## C4-3：有限真实反馈闭环

Study `c4-feedback-loop-20261026`，独立 Store/目录/会话。
配置 `study_c4_feedback_loop.json` 只经原导入器物化 T2 pilot C 的失败固定回放和相关有限
Native 结果；原控制可用，历史费用和归属明确，没有成功见证。其原 0.5 s 任务身份与本轮一致。
这份已冻结真实未决状态与成对探针分开，不覆盖历史状态。

Agent 自行选择一次或少数动作，读取新科学结果并更新判断；指令限制最多两项数值研究动作，
监督在原已结算边界检查，所有实际调用仍受下表共享硬上限。该阶段不开放 PPO 训练。
新证据是否产生、解释是否准确、路线是否随反馈更新，与性能优劣分别评价。
通过后才考虑 C4-4；不因单次优化不佳无限追加。

## C4-4：完全冷启动的正式研究准备

Study `c4-coldstart-reach-hold-20261026`；配置 `study_c4_coldstart.json`。
选择原 `reach_hold_b3_050.json`，而非没有同身份历史通过证据的 C3 mirror 任务。
canonical_task_identity 为 `062de8ca2fd2acaebdbf856ba8fc3420d88c8d3943cfa789c5c9e6f06e486c6b`。
监督只读核对封存 R1 完整独立通过：规范任务、完整时间网格、验收阈值、保持窗口及 backend
设置均与新配置相同。成功结构和输入不导入、不写入 Agent 提示或新 Study。

固定目标 [0.29,-0.035,0.19] m，时域 0.5 s，控制/采样 0.01 s，物理步长 0.0005 s；
原全部零初态，终点及保持位置 ≤0.01 m，保持速度 ≤0.02 m/s，保持 [0.45,0.5] s。
原独立完整验收及最终每段 12 cells 不变；输入通道数量由 Agent 生成候选决定，每通道保持原
非负张力合法域及不超过 8 N 的上界。没有外力新任务。

使用原 start_mode=family_space。初态必须满足 reference_candidate=null、candidates={}、
selected=null、全部当前结果为空；supplied_evidence、history、mathematics、control_seeds
均空；无 fixed_structure_reference、nominal_source、历史 warm-start 或成功提示。
保留原 Host 兼容 scaffold，但不将其注册为科学候选或基线。
首次结构门禁只要求 Agent 自己提交合法 generate 参数；不规定段/腱数、材料、布局、权重或研究顺序。
首次合法生成后开放原全部适用方法。使用原 FamilySpace 真正可执行域，不人为选一个中性结构。

第一次完整独立通过后立即精确读取、SELECT/STOP，零额外确认；不继续优化。
预算耗尽时保存未决解释，不把有限搜索失败称理论不可行。
监督只看真实账本、进程和证据，不代做控制搜索、不提示历史答案，不换 Study 绕过费用。

## 新额度建议与授权范围

以下全是待明确批准的独立上限，不继承旧研究授权；后两阶段还需通过前阶段门禁。

| Study | Provider（含 Reporter）/保护 | public/保护 | 数学评价 | 共享物理启动 | 子额度 |
| --- | ---: | ---: | ---: | ---: | --- |
| c4-decision-pairs-20261026 | 12 / 无 Reporter；先 6 | 只读探针调用逐项记录 | 0 | 0 | 最多两轮；无科学 worker |
| c4-feedback-loop-20261026 | 16 / 4 | 40 / 8 | 4 | 4 | NMPC≤1，固定回放≤3，PPO=0；Native 每项≤60 callbacks/2 updates/4 knots |
| c4-coldstart-reach-hold-20261026 | 128 / 12 | 240 / 16 | 36 | 16 | NMPC≤2，固定回放≤12；PPO≤2 stages、每 trial≤16384 actions、合计≤32768、独立评价≤2；Native 每项≤120 callbacks/4 updates/4 knots |

物理子额度都共享物理总额，不能逐项相加获得额外额度；PPO 评价保护沿原实现。
原工具内部上限和真实调用/积分/迭代成本均保留，内部 Native 积分与独立物理启动分开记录。
没有新增墙钟计费器、理论价格或无限扩额。原有限数学优化器/控制器上限继续适用。

依据：原 C3 blank 在 31 次请求、2,738,052 Tokens 后被 Provider 收尾限制截断，仍余大量科学额度；
原同任务 R1 最终总账 117 次请求（含历史辅助及接续），任务通过后立即收尾。
正式建议 128 次给空白生成、可选择的结构/控制路线及保护收尾留出空间；16 次共享物理和 36 次
数学评价支持多次真实尝试，同时由原账本硬限。不能据这些不同初始化和工具版本的历史数字
保证成功或声称效率已提高。Provider 未返回金额，费用金额保持 unknown。

三阶段统一外部模型为配置中的 DeepSeek `deepseek-flash`，
`https://api.deepseek.com/chat/completions`，high reasoning、thinking enabled、每请求输出上限 32768。
模型别名不是不可变权重版本；尚未进行本轮网络可用性验证。
发送范围仅为冻结任务/验收、合法工程语法和结构/控制参数、对应 Study 许可的科学证据与反馈、
相关 Agent 对话及生产工具契约。成对探针仅包含各自历史边界以前可见资料。
不发送凭据内容、无关文件或隐藏成功答案；密钥只用于认证。

`runtime_c4.json` 使用现有 s135 Python，已装 MuJoCo 3.13.0、CasADi 3.7.2、CVXPY 1.9.3、
tokenizers 0.22.2、Strands 1.59.0/harness 0.2.0，原单线程设置。
默认 mainline5 环境缺 CVXPY/tokenizers，本轮没有安装依赖或改变库版本；真实 Host/worker
应从冻结 research_python 启动，避免旧 C3 的解释器错配。

授权后用原 formal_study_authorization 记录准确 Study/resolved_identity、额度、外发和
`registered mathematics`/能力 scope；Handoff 只复用原零科研的技术准入证明，重新绑定本轮范围，
不把旧外发许可当作授权。采用原合法 request-feedback Handoff，160000 bytes 触发干净接续；
保留原结果反馈和来源，必要核对在相同 Study、相同总账内完成。

## 工程验证与下一步

三项定向工程检查通过：新边界未来物理结果不可见且无 Store 写入；C4 缺授权在 transport/建账前
停止；原两轮共用十二请求硬限及零科学 dispatch 保持。测试 Provider 是明确 mock，实际 Provider=0。
一次编辑缩进错误已在该定向检查前纠正；首次离线审计因默认环境缺 tokenizer 停止，换用已有完整环境，
没有安装、模拟科研结果或发出真实请求。

离线查询预核验通过，未来输出分别 1231/99/467 项均被真实边界拒绝。
标量审计见 `evidence/c4_preparation/offline_audit.json`。后续冻结/空池核验会追加独立准备记录；
不覆盖失败过程。工程测试不构成 C4-2/3/4 科研通过。

用户已明确批准三份额度，随后授权监督自行制定有限预算、追加额度、修复中断和必要问题，无需再次询问。
所有追加仍须同 Store 正式记录有限新上限、依据和旧用量，不改变冻结任务或覆盖原配对负结果。
当前科研 go/no-go：**初轮行为门禁未通过，后两阶段保持未启动。**

## 冻结完成记录

工程冻结提交 `75089982e`。六份真实生产投影均冻结，全部当前推荐查询可读，三对方法集和源状态一致。
成对冻结身份 `6d6c4b8bb0c394c0bc818f79448fc8213ff22ed6a1e4d0a9073e5804ca3a136f`；
标量清单在 `evidence/c4_preparation/paired_freeze.json`，原包仅保存在忽略的运行目录。
完整 Handoff wire 的离线 tokenizer 估计分别为 A 31781→31822、B 33325→33364、C 40736→40775。
修复增加约 39–41 个离线 Tokens，未删除科学信息；不能称 Token 压缩或真实交互改善。
当前可执行推荐查询分别 27/29/23 项，两个版本均通过。

两项正式准备经原 prepare/bind 完成，身份与 Store 分开：

- Cold-start resolved_identity：`60a684e2389e5719b9c30afaaeb27215a9224087b5df33dc991662cf7a642d66`。
  候选池 0，reference/selected 均 null，历史和当前数值结果全空。
- Feedback-loop resolved_identity：`c6c451a57c78b14e8837808be5d52d41c131c8c452f6b01ead4ddcf5e436b89c`。
  原导入器物化一个失败历史候选及控制、一个历史数学结果，当前数值结果全空。

两 Store 的 Provider/public/physical/worker 已用额度均 0；没有物理步或新科学评价。
真实 require_authorization 都拒绝继续，未记录授权事件。
`prepared_studies.json` 保留初态与账本标量；`authorization_request.json` 是三份精确身份绑定的
**授权请求草案，user_approval=null**，不是已授予许可。待用户批准后原样绑定相应范围。

## C4-2 初轮真实结果（2026-10-27）

用户批准后已按原顺序完成首轮六次，再因尚缺可信提案且需要观察真实纠错而倒序完成第二轮。
共 12/12 次请求、12 份确认回执，无 pending、重试、Reporter 或科学 worker。
输入 504762、输出 103550、总 608312 Tokens；reasoning 86452 已含在输出中；金额 unknown。

| 原冻结组 | Provider | 总 Tokens | 工具 / 读取 | 错误 | 可信完整研究动作 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Control | 6 | 307707 | 10 / 7 | 2 | 0 |
| Treatment | 6 | 300605 | 9 / 6 | 3 | 0 |

合法 Plan 包括只读 diagnose、STOP 与一次控制初始化提案，但它们不能自动算作可信科研行动。
Treatment A 添加不存在的 note 字段，且提出未核准的 Native/short-response 组合；B 引用可读却未注册
的原始 motion，并把已经存在的归一化保持速度代价称为缺失；C 对两点受控速度作被动衰减/结构归因，
且未来回放及 FD 成本未能适配剩余完整回放额度。Control 也有来源错配、无实际工具提案、局部增益不可能
断言，以及未纠正请求即 STOP。完整逐份判定与成本在 `evidence/c4_decision_pairs/initial_review.json`。
没有确认相同查询/相同内容的重复或空字段无信息读取；这不足以证明长期效率改善。

因此本轮 **no-go**，不启动 C4-3/4，也不把 Treatment 较少的 7102 Tokens 当作科研效率提高。
模型本身的科学判断错误与以下三个已复现工程交付问题分开记录：

1. 原 `decision_brief` 已生成引用资格提示与精确 L1 查询，后续 L0 压缩却把整个字段删除。
2. 数学/物理关系按 epigraph 活跃信号计算 `constraint_mismatch`，但可能被读成没有检查速度；
   本例实际检查了六项保持速度约束。只修正说明、补覆盖事实，保留旧字段和状态值兼容。
3. 只读探针先做 JSON Schema 检查，截断生产 Pydantic 的精确错误，导致 C3.3 的非法设置反馈没有到达模型。

按用户追加要求，只进行一次针对性修复，保持工具字段、路由、验证和 L0/L1/L2 层级；新状态重新冻结验证，
原 A/B/C 输入、评分、输出与费用全部保持。后续必要预算使用原配对 grant 增量，绝不另开 ID 清零。
本聊天每五分钟监督恢复检查已启用（automation `c4`），正常原进程运行时不启动副本。

## 一次针对性修复与新状态复核准备

生产仅改两处既有交付：保留原 L0 `citation_eligibility` 的简短规则/查询，完整库存仍由原 L1 管理；
数学/物理关系保留所有原字段及 `constraint_mismatch` 状态值，补充比较仅基于 epigraph 活跃集、
实际已检查的约束 ID，以及“活跃位置不等于没有检查速度”的准确说明。不改科研方法、Scope 准入或评分。
原 contracts/工具字段、核心派发、优化器、Store、独立验收和 L0/L1/L2 层级没有改变。

只读探针把原生产 Pydantic 解析放回冻结 JSON Schema 检查之前，从而原 C3.3 精确错误能原样到达模型；
非法 regularization 仍拒绝，不自动删字段、改路由或执行。该公共探针修复对两组都适用，不能把其收益
全部归因于 Treatment。新测试复现原非法设置的实际反馈，原活跃集/物理失败对照测试与原十二请求硬限测试
各一次通过（共三项）；没有全量回归或科学计算。

新协议 `c4_revalidation_protocol.json` 固定两个不同历史状态：D 为 R1 preparation2159（已有新的 Native
预测控制，后续独立物理不可见），E 为 C3 heuristic preparation153（一次位置/速度失败、尚无数学结果）。
二者均非原 C4 A/B/C 或 C3.2 N/K/M 的 source_state；仍与历史任务相关，不称完全盲测或统计独立。
Control 固定 `1bbfdcab9` 的原 C4 生产代码，Treatment 为本次修复；沿用原评分，不指定方法。

用户追加的自主额度授权已通过原 Store/grant owner 作有限增量：Provider 总上限12→20，已用12保持，
只给新 D/E 两组各最多两轮（八次新增请求），无科学额度。旧原始目录和 summary 不覆盖，新的冻结/输出目录
仅保存阶段输入；所有发送仍记入同一个 Provider Store、同一个 grant，不能靠更换目录重置。
详见 `evidence/c4_decision_pairs/revalidation_budget_addendum.json`。若这次仍未通过，不继续刷原样本。

## 新状态复核实际结果与中断恢复

新冻结身份 `4d83418988519bbc8ca15fe20e651c41036959fa3545f6256f2dc293ae8bfa7b`，
四份当前生产投影、推荐查询和未来证据拒绝检查均在外发前通过；标量清单见
`evidence/c4_decision_pairs/revalidation_freeze.json`。未改变 source_state、评分、权限或 max_tokens。
两份准备 Study 经原 bind 迁移到 `34d7fbc66`，原任务、科学 profile、候选池和用量保持；
记录见 `evidence/c4_preparation/repair_binding.json`。

完成新增首轮四次，随后按冻结倒序完成最后四次。新增八次输入 316754、输出 81222、
总 397976 Tokens；reasoning 70774 已含输出。与初轮累计为输入 821516、输出 184772、
总 1006288 Tokens（reasoning 157226 已含输出），20/20 回执确认，原 Store/grant 余量零、
occupied 为空，无未知外发结果、自动重发或 Reporter；金额 unknown。没有科学派发或物理步。

| 新状态复核组 | 请求 | 总 Tokens | 工具 / 读取 | 非法调用 | 截断 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Control | 4 | 176458 | 6 / 4 | 1 | 0 |
| Treatment | 4 | 221518 | 4 / 2 | 0 | 1 |

Treatment E 首轮返回完整 HTTP 200，但 32768 输出 Tokens 全部用于推理，finish_reason=length，
没有原生工具动作。原 LiveBoundary 正确拒绝继续，响应体、异常和费用均已归档。
监督仅明确确认该已结算的无工具截断，不修改生产 incomplete guard；在同一个 Store 记录处理原因，
接续原来从未发送的 E-control 首轮，再走原第二轮。没有重发失败请求、替换样本、增添轮次或改输出上限。
失败继续计入评价；第二轮也不把首轮截断当作成功。标量事件见
`evidence/c4_decision_pairs/confirmed_truncation_recovery.json`，原始推理/响应/账本仅留在忽略目录。

六次读取全部成功。三次补充详细结果/结构字段，三次核对控制来源和部分已交付绑定，不能仅凭重复事实
把核对称为浪费。没有确认同一 case/arm 的相同查询复读、空字段无信息读或非法读取。
Treatment 比 Control 多 45060 Tokens，包含截断及其原第二轮接续负担；样本小且状态谱系相关，
不能据这些数值估计修复的因果效果，也不能宣称上下文效率改善。

逐份判定、实际成本和最终未启动 Store 核验在 `evidence/c4_decision_pairs/revalidation_review.json`。
主要观察如下：

- D 两组都选择了合理的独立完整回放，候选/新 Native 控制绑定及一次共享物理启动、一次完整回放成本正确，
  Plan/引用检查通过。完整 worker 准入没有执行，不能把只读通过写成实际科研执行通过。
- D Control 把竞争解释对应的读数区间称为互不重叠，但结构限制、控制未充分搜索和模型转移误差可能产生相同失败。
  D 两组均把单个基线指标的精确一致推广成后端/模型的近恒等关系，并把回到基线速度排他归因为输入交付错误；
  这些解释仍需进一步证据。
- D Treatment 还把裁零后的 gap 改善相差约 8.5e-11 当作线性/非线性精确一致。
  原预测 signed excess 为 +8.499956294372168e-11，实际为 -0.003284013494889715；
  裁零后改善相同不能证明轨迹准确性或转移误差界。其独立验证选择合理，但完整科学论证没有过关。
- E Control 使用不存在的 regularization 字段，收到原生产的精确拒绝和合法字段提示；
  六 callbacks 加独立验证按七次共享物理额度估算，却忽略只剩五次完整回放的子额度。
  Plan control_search 的新回调走原物理回放路径，不能当成未知数学计费；有限探针也不提供可达下界。
- E Treatment 第二轮正确保留 diagnose 的只读属性和数学授权前提，提出制动/权限竞争解释；
  但 selected_candidate=null，没有注册的具体 AnalysisRequest/模型/参数和可执行成本，
  仍只是概念诊断。申请两个单位不是执行权限或已花费用。

严格完整评分没有可信提案；即使把 D 的合理核心回放动作计为可信，也只有一个不同场景，
E 没有可信可执行实验，仍达不到至少两个场景的原门槛。因此最终 **no-go**，不进入 C4-3/4。
本轮已经用完“真实问题的一次针对性修复 + 新状态复核”，不继续调原 Prompt/样本追求通过。
这不是授权不足或单纯 Provider 总额度不足；需要解决的是动作构造、既有成本信息利用和证据范围判断的可靠性。

## 本轮交付结论

1. **上下文效率：未证明改善。** 原复读误导措辞已修，原 L0 引用规则及 L1 精确查询得以保留；
   真实短窗口未发现无信息复读，但存在输出耗尽而无动作，不能仅比较 Tokens 宣称进步。
2. **工具正确性：局部成立，整体未通过。** 正确绑定的回放提案和只读诊断可解析；
   不支持字段仍被生成，成本子额度仍被误读。精确生产错误反馈已确认实际到达模型。
3. **科研判断：尚不可靠。** 能提出竞争解释和条件停止，但仍过度解读单点一致、裁零 gap 和有限搜索。
4. **完全冷启动：未开展，结果未测。** 原空候选池、reference=null、selected=null、空当前数学/物理结果保持；
   Feedback-loop 与 Cold-start 的原授权已授予但门槛未过，两个 Store 的 Provider/public/backend/worker 用量仍全零。
5. **首个可行解成本：未知。** 本轮完整决策验证成本为 20 请求、1006288 Tokens；
   没有自主新科学实验或完整可行解，不能把历史 R1 成功计入本轮，也不能据 no-go 宣称结构或任务不可行。

工程改动复用现有 Store/预算/路由/Handoff、工具字段和 L0/L1/L2 层级；保留旧关系字段及状态值，
不改变任务阈值、控制器或独立验收。直接相关三项检查已通过，未跑全仓测试。
普通分支发布仅包含必要代码、冻结协议和标量报告，不含原始 Provider 推理、凭据或完整私有 Store。
研究监督已处理本轮唯一确认截断；结论封存后暂停五分钟自动监督，避免重复请求和无限复核。
当前不具备由本轮证据支持的 B2 外力自主研究准入结论。
