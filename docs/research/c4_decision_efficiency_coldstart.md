# C4：决策效率与无基线 Reach/Hold 研究

2026-10-26，Asia/Shanghai。当前阶段：工程准备完成，真实外发与科学执行待本轮明确授权。
**尚不能判断三项能力是否改善，尚未启动正式自主研究。** 不启动 C5/B2 外力自主 Study，不增加数学方法。

## 基线与最小修复

指定基线 d20cf4ee047d1b5d16befacdee52ed5a3d3905e3；开始时集成分支最新为
d7b0f91f966ef96fa17b181ead99dff9a2d457cc，仅多两份集成状态文档的修改，科研代码相同。
从最新集成建立独立 `research/c4-decision-efficiency-coldstart`，不触碰主工作区和其他研究。

已审阅 C3、C3.2 和 C3.3 真实负结果及现有路由、证据、成本、Handoff 链路。
空 fields 拒绝、精确字段纠错、Native 路由和预算说明已经存在，不重复实现。
没有证据证明靠进一步扩写系统提示就能修好模型判断，因此不做这一改动。

唯一生产修改位于 `research_context.decision_brief` 的读取状态说明：
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

当前科研 go/no-go：**等待新外发和科学预算授权；行为门禁仍未验证。**
用户可以一次批准上述三份额度并要求自动依门禁顺序推进；未通过则停在对应阶段，不自动消耗后续额度。

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
