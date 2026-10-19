# S6.0–S6.3 交付记录（2026-10-19）

**交付状态：工程实现、离线验证及镜像任务的四次真实工程评价已完成；真实 Agent 运行被自动审批阻止，S6.1 的真实连接以及 S6.2/S6.3 自主研究没有完成。没有发现新的原任务可行解，也没有虚构模型决策记录。**

本轮基线为 `68c9e61413e896e191000d47c0509eb7be6a4f1b`，目标分支为 `feat/sorosim-matlab-nmpc`。开始时目标工作树干净，fetch 后本地/远端差异为 0/0。IDE 中其他工作树没有参与修改。

工程接入复用既有 Strands、DeepSeek transport、Plan、Core、Store、预算、archive importer、candidate generator、physical replay 和原始验收。新模块 `research_context.py` 仅负责已授权历史的精确导入与紧凑研究视图；没有第二套执行器、缓存、预算或评价器。`control_search` 是新增明确动作，旧 `search` 保留原义；只有显式 `research_decisions.version=research_decision_v1` 的新 Study 启用决策审查。旧 Plan 序列化省略新增空字段。

P1 最优实际张力通过原 archive/member SHA256 验证，并与新候选的机器人、任务、seed、模型、设计、时序和腱顺序精确比较。历史观察保留旧执行身份；原始控制可以作为新搜索基线而不重复物理执行。只读测试恢复完整 35×4 实际输入；仅 0.30/0.33 s 速度超限，G=0.054502039，历史结果仍是有效失败。

通用接口 v2 从实际通道和时间网格确定维度；v1 保留旧 35×4 契约。指定修正窗口时，窗口外的基函数严格为零。局部响应仍评价全部终点和保持约束。当前数值优化器是 reach 任务工具，其他任务明确 unsupported；不声称实现障碍或接球物理平台。新结构可显式以旧同通道控制初始化，但重新绑定新设计/模型并由原独立评价器测量，不继承旧验收。

执行前，Core 从可信 Store 结果解析证据，拒绝未注册引用、跨任务证据、跨设计/模型推论及未获支持的全局结论；合法探索无需先获得数学可行证书。每次新物理评价仍逐次经公共 replay、Store 和共享后端额度准入。批处理也保护收尾操作额度，首个完整通过后停止。中断只封装已结算证据；不自动重启未知工作或声称恢复优化器内部状态。

预执行验证：72 项聚焦测试通过；随后新增公共搜索缓存/重复请求验证及独立公共能力检查，50 项相关测试通过。执行命令使用现有 `.mainline5-env/Scripts/python.exe`、仓库 PYTHONPATH 和已安装 MATLAB Engine 路径，三个数值线程环境变量均为 1。一次未设线程变量的回归被现有 NMPC 环境准入拒绝，设为冻结值后通过；没有在测试中运行真实 provider、NMPC、PPO 或物理步。早期 tempfile 测试触发 Windows ACL/SQLite 清理问题，改用仓库测试目录、独立 fixture grant 及 GC 后通过。一次测试初始化在 DB 建立前绑定了无实际科学消耗的 `s6-2-20261019` grant；它保留在本地 authority 中，未删除或重置。真实 Study 明确使用带 `-live-` 的 ID，测试此后使用独立 UUID fixture grant。

真实研究尚待启动。各 Study 的 provider、公开操作、共享后端及数学/NMPC/PPO 上限在 `configs/research/study_s6_*.json` 中冻结；S6.1 不启用数学、NMPC、PPO。S6.2/S6.3 不借用封存预算。真实模型动作、原始请求、反馈、成本和接受结果将由既有 export 及 `python -m tests.research.s6_audit` 归档，完成后更新本报告。当前没有新增物理成功结论。

首个工程冻结为 `c3c1f5aa`，已普通 push。S6.1 已 prepare/bind 并导入历史，provider/后端用量均为 0。真实启动两次被自动审批在进程建立前拒绝：第一轮认为目的地/载荷授权不明确；随后生成 24,204 字节科学载荷清单、核实没有凭据字段并引用附件明确条款，复核仍不接受附件条款为可信用户授权。已向用户请求在当前对话明确批准 `https://api.deepseek.com` 的指定科学数据发送，没有通过间接执行绕过。清单及拒绝记录在 `evidence/s6_1/`。

等待授权期间增加显式镜像工程验证配置和驱动（独立最多 4 次后端、0 provider），以及跨设计初始化、模型范围和不同终点阈值测试。补充后的 63 项相关检查通过；另一组 55 项检查含 1 项按 opt-in 规则跳过的真实 RL 测试。仅已跑过的测试作为工程证据，未运行项目不充当科学结果。

## A. 最终验收与仓库身份

| 阶段 | 已完成 | 尚未完成 |
|---|---|---|
| S6.0 | P1 精确身份、完整控制、动态超限样本、预算和紧凑上下文 | 无新增科学成功结论 |
| S6.1 | 公共 Plan/控制搜索、证据准入、旧语义兼容、模拟工作流和 Strands 工具 schema 接入 | 真实 DeepSeek 工具闭环，启动前被审批阻止 |
| S6.2 | 独立有限预算配置、P1 起点和真实运行入口 | 全部真实模型决策与自主科学执行 NOT_RUN |
| S6.3 | 合法结构与控制初始化接口、不同维度契约、镜像任务四次真实工程评价 | 原任务 Agent 结构—控制联合研究 NOT_RUN |

最终生产源码冻结为 `0664cec3`（完整 SHA 见 Git），已普通 push；原镜像物理执行冻结为 `5285c3c4a5b45765efc65de341d416238c027e93`，之后源码修改不追溯改写其科学身份。交付提交另含报告和不可变归档，最终分支 tip 在最终回复中列出以避免报告提交自引用。所有修改限目标工作树；无 force、reset、其他分支合并或历史档案修改。

## B. 实现复用与范围

生产源码相对基线约 **+465/-26 行，净 +439 行**，低于建议规模，不以行数填充实现。新增生产模块只有 `tools/research/research_context.py`，91 行，解决上下文与授权历史导入这一独立职责。数学、NMPC、RL、候选生成、Store、预算、任务验收均复用原实现。测试、配置和原始证据另计。

公共准入拒绝未注册证据、错误任务、非零初态被伪装成零初态、错误设计/模型范围和未证实的全局推论。独立数学入口显式检查新 Study 的能力声明；独立物理入口保留完整绑定和共享额度检查。模型不能提交任意 verification_status 或证据摘要作为证书。研究意图是兼容的类型字段；旧 `search` 的含义没有变化。

局部搜索的旧 v1 维度约束保留；新 v2 根据实际张力矩阵确定通道、时间与参数数目。原终点阈值和保持位置阈值可不同。窗口掩码同时应用于实际控制与响应基函数，窗口外输入逐值不变。内部新评价仍逐次调用 Core/physical_replay 并计费；缓存不重复收费。root Plan 与内部物理操作保留同一 model/engineering 来源。中断只恢复已存在结果，后续搜索需要新 Plan。

## C. 模型自主证据与阻塞

真实模型请求 0；真实工具调用 0；模型 STOP 0；模型 token 0。`evidence/s6_1/decisions.json` 中没有虚构决策。现有 `r3_request`、原始响应、工具请求/反馈和原 Plan 的持久化路径保留；真实调用获准后仍使用相同 Strands Harness。

批准问题已明确列出发送目的地 `https://api.deepseek.com`、配置模型 `deepseek-flash`、允许的科学内容与 4/24/24 次请求上限。审批拒绝发生在进程创建前，未形成未知 provider 请求；没有重发未知结果。后续只等待用户明确授权，未用其他执行路径绕过。S6.1 保持 ready，便于继续，不能把这种工程等待记作 Agent STOP。

## D. 数学证据与预测范围

导入 S5.9 的三条既有局部制动/静态敏感性结果，并从原 artifact 重新生成证据摘要；其来源、任务、模型、操作点及限制可通过原引用读取。它们不证明新结构的动态改进、整个保持窗口可行性、全局结构不可行或未访问候选的下降保证。新增数学分析、完整 NLP、数学重积分、NMPC、PPO 均为 0。镜像验证使用确定性 pattern 搜索，没有数学模型下降保证，也没有把小幅位置变化解释为通用设计方向。

## E–F. 真实结构、控制与物理评价

工程迁移独立 Study 为 `s6-mirror-transfer-20261019`，原任务身份为 `882b3493037dcc8f8da294b3473e1223f0465e92c35bc3064bfc42d467bf212e`；镜像实际任务身份为 `bd9df2d930423f2b2a12152f076e2ae88b4d1a0af84d6126aa13b0b1fac9ec77`。目标从 y=+0.035 m 改为镜像配置的 -0.035 m，其他冻结阈值保留。两任务的验收与排名不合并。

结构均为两段、四腱，长度 0.195/0.11 m，原截面/腱路及通道顺序保留；修订结构只将近端杨氏模量从 10.45 MPa 增加到 10.5545 MPa。完整结构、模型身份及实际 35×4 张力矩阵在 `evidence/s6_transfer/best_control.json`，不以报告中的简述替代可重现输入。

第一项评价显式把 P1 控制初始化到新任务，未转移原任务验收；随后新材料候选通过 `adaptation_from` 显式绑定旧候选控制，再执行有限局部适配。修正窗口为 [0.30,0.35] s，结点 [0.30,0.34] s，pattern 半径 0.001 N，新结构请求预算为 3（1 个新结构基线及 2 个控制探测）。这些是明确的工程接口验证选择，**不是 Agent 选择，也不作为研究方法优越性的证据**。

| 镜像评价 | 近端模量 MPa | 终点误差 m | 保持误差 m | 保持速度 m/s | G | 原镜像验收 |
|---|---:|---:|---:|---:|---:|---|
| 原结构控制初始化 | 10.45 | 0.072484498110 | 0.072484498110 | 0.021090040785 | 6.248449811 | 失败 |
| 新结构控制初始化 | 10.5545 | 0.072226100301 | 0.072226100301 | 0.022401105675 | 6.222610030 | 失败 |
| 新结构探测 1 | 10.5545 | 0.072224924947 | 0.072224924947 | 0.022401105675 | 6.222492495 | 失败 |
| 新结构探测 2 | 10.5545 | 0.072223750019 | 0.072223750019 | 0.022401105675 | 6.222375002 | 失败 |

四次均为完整有效执行；位置和保持速度均未通过。原评价器判断保留原样；另从保存的原始采样独立重算全部 G，逐个 archive/member SHA256 校验通过，未再启动科学计算。最优评价引用、控制 source、设计候选及接受组件见 `summary.json`、`best_control.json` 和 `independent_audit.json`。这个四次小验证不足以比较结构全局优劣。

原 reach_hold 尚无新增真实研究结果；其可继承的 P1 最优仍是终点 0.005193064 m、保持位置 0.005193910 m、保持速度 0.021090041 m/s、G=0.054502039 的有效失败。镜像任务失败不改变这一原任务结论。

## G. 成本和生命周期

| Study | provider 已用/上限 | 公开操作已用/上限 | 共享后端已用/上限 | 状态 |
|---|---:|---:|---:|---|
| S6.1 live | 0/4 | 0/14 | 0/2 | ready，审批阻止 |
| 镜像工程验证 | 0/0 | 8/12 | 4/4 | engineering STOP，已封存 |
| S6.2 | NOT_RUN，配置上限 24 | 配置上限 90 | 配置上限 48 | 未创建科学 Study |
| S6.3 Agent | NOT_RUN，配置上限 24 | 配置上限 90 | 配置上限 48 | 未创建科学 Study |

镜像数值累计约 5.058348 s，四次 worker 账本 elapsed 合计约 4.434581 s；数值准备与物理执行均保留，没有把它们冒充整个开发对话墙钟耗时。S6.1 导入/构建准备另见其账本和状态，不记为新物理执行。所有 Study 都无 pending、占用资源或存活 worker；镜像剩余公开操作 4，但后端额度为 0，未另开 ID 延续相同实验。没有消费任何旧研究的余额。

## H. 通用性与明确限制

纯接口测试覆盖 1/3/6 个控制通道、7/12/20 个控制周期、不同结点和不同终点/保持阈值；这些全部为标记清楚的合成夹具。真实物理只验证两段四腱、35 周期、两种材料值和镜像目标。改变拓扑后缺少对应控制初始化时明确 unsupported；tracking 等当前局部搜索不支持的任务明确拒绝，不能替换为 reach。障碍、接球、扰动任务后端、任意腱数物理执行、硬件、鲁棒性、重复性和总体统计结论均未建立。

## I. 最终验证

最终聚焦集合共 **119 项，118 通过、1 跳过、0 失败/错误**。跳过项是只有显式设置 `SOFTROBOT_REAL_RL_TEST=1` 才启动的真实 RL 链；本轮没有设置该开关。原始模块列表、耗时、完整测试输出及原因在 `evidence/s6_verification/tests.json`。

命令为现有研究 Python 的 `-m unittest`，模块包含 `test_s6_research`、`test_local_control_search`、`test_candidate_portfolio`、`test_evidence_policy`、`test_control_correction`、`test_count_continuation`、`test_s58_agent`、`test_s59_guidance`、`test_agent_feedback`、`test_rl_integration`，均位于 `tests.research`。真实工程验证命令为 `python -m tests.research.s6_transfer`，读取已 prepare/bind 的独立镜像 Study；该驱动已 STOP，再调用只导出保存结果。离线审计命令为 `python -m tests.research.s6_audit RUN_ID DESTINATION`。

## J. 科学结论与后续入口

工程执行链路在镜像任务走通；没有发生真实模型自主研究，没有新增原 reach_hold 可行方案。原任务最佳证据仍为 P1 的有效失败，未验证假设包括局部控制表达能力、保持阶段制动和结构—控制适配效果。不能从当前有限工程验证推出结构不可行、通用能力或 Agent 优于固定方法。

真实 Agent 的唯一外部阻塞是审批要求当前对话明确批准上述 DeepSeek 数据发送。获准后先继续现有 S6.1 Study，保留其零发送状态和所有迁移记录；再按已冻结上限新建 S6.2、S6.3，先导入前阶段结果以避免科学重复，提交并推送新增配置后才启动。首个完整通过结果出现即完成该 Study 的读取、精确选择和停止，不为展示反馈而增加实验。

## K. ???????

?????? SHA???????????????????JSON ????????????????? artifact ????? manifest ?????????????

| ?? | ??/????? | ?? |
|---|---:|---|
| `configs/research/study_s6_1.json` | +89/-0 | Independent frozen counts, capabilities and authorization |
| `configs/research/study_s6_2.json` | +98/-0 | Independent frozen counts, capabilities and authorization |
| `configs/research/study_s6_3.json` | +98/-0 | Independent frozen counts, capabilities and authorization |
| `configs/research/study_s6_transfer.json` | +60/-0 | Independent frozen counts, capabilities and authorization |
| `docs/research/s6_delivery.md` | +146/-0 | Delivery status, evidence boundaries and remaining blocker |
| `evidence/s6_1/decisions.json` | +4/-0 | Exact observation, decision, cost, configuration or audit export |
| `evidence/s6_1/payload_manifest.json` | +29/-0 | Payload or immutable member/hash inventory |
| `evidence/s6_1/prelaunch_review.json` | +18/-0 | Exact observation, decision, cost, configuration or audit export |
| `evidence/s6_1/study/archive_manifest.json` | +95/-0 | Payload or immutable member/hash inventory |
| `evidence/s6_1/study/calls.json` | +1/-0 | Exact observation, decision, cost, configuration or audit export |
| `evidence/s6_1/study/configuration.json` | +3034/-0 | Exact observation, decision, cost, configuration or audit export |
| `evidence/s6_1/study/disposition.json` | +92/-0 | Exact observation, decision, cost, configuration or audit export |
| `evidence/s6_1/study/immutable_artifacts.tar.gz` | binary 370656 bytes | Original immutable Store artifacts; no second execution store |
| `evidence/s6_1/study/ledger.json` | +24/-0 | Exact observation, decision, cost, configuration or audit export |
| `evidence/s6_1/summary.json` | +428/-0 | Exact observation, decision, cost, configuration or audit export |
| `evidence/s6_transfer/best_control.json` | +2544/-0 | Exact observation, decision, cost, configuration or audit export |
| `evidence/s6_transfer/decisions.json` | +4/-0 | Exact observation, decision, cost, configuration or audit export |
| `evidence/s6_transfer/independent_audit.json` | +667/-0 | Exact observation, decision, cost, configuration or audit export |
| `evidence/s6_transfer/study/archive_manifest.json` | +329/-0 | Payload or immutable member/hash inventory |
| `evidence/s6_transfer/study/calls.json` | +170/-0 | Exact observation, decision, cost, configuration or audit export |
| `evidence/s6_transfer/study/configuration.json` | +3008/-0 | Exact observation, decision, cost, configuration or audit export |
| `evidence/s6_transfer/study/disposition.json` | +127/-0 | Exact observation, decision, cost, configuration or audit export |
| `evidence/s6_transfer/study/immutable_artifacts.tar.gz` | binary 346097 bytes | Original immutable Store artifacts; no second execution store |
| `evidence/s6_transfer/study/ledger.json` | +24/-0 | Exact observation, decision, cost, configuration or audit export |
| `evidence/s6_transfer/summary.json` | +7737/-0 | Exact observation, decision, cost, configuration or audit export |
| `evidence/s6_transfer/validation.json` | +10/-0 | Exact observation, decision, cost, configuration or audit export |
| `evidence/s6_verification/tests.json` | +29/-0 | Actual focused test results and skip reason |
| `tests/research/s6_audit.py` | +59/-0 | Offline contracts or explicit opt-in engineering/audit driver |
| `tests/research/s6_transfer.py` | +69/-0 | Offline contracts or explicit opt-in engineering/audit driver |
| `tests/research/test_s6_research.py` | +186/-0 | Offline contracts or explicit opt-in engineering/audit driver |
| `tools/research/agent.py` | +8/-0 | Compact state and actual Strands schema/feedback |
| `tools/research/analysis.py` | +2/-0 | Independent public capability admission |
| `tools/research/candidate_portfolio.py` | +0/-1 | Remove fixed dimensions from archive recovery |
| `tools/research/config.py` | +5/-0 | Freeze versioned opt-in decision semantics |
| `tools/research/contracts.py` | +32/-4 | Typed decision and unambiguous control-search action |
| `tools/research/control_correction.py` | +16/-10 | Window-masked basis and distinct registered thresholds |
| `tools/research/core.py` | +25/-3 | Public evidence/action admission, recovery and import |
| `tools/research/evidence_policy.py` | +57/-0 | Trusted evidence/task/design/model-scope checks |
| `tools/research/local_control_search.py` | +85/-5 | Variable dimensions and bounded existing-Store dispatch |
| `tools/research/physical_replay.py` | +23/-3 | Explicit new-candidate initialization; retain old evaluator |
| `tools/research/research_context.py` | +91/-0 | Exact authorized history and compact evidence view |
| `tools/research/state.py` | +5/-0 | Existing evidence readability only |
| `tools/research_tasks.py` | +16/-0 | Task-owned actual violating-sample diagnostic |
