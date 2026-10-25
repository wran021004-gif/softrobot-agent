# 历史结论索引与 B3 Benchmark Readiness

2026-10-25，Asia/Shanghai。基线为远端
`codex/c3-g2-scientific-decision-loop@5e955768ea40dfe447bd2d8e6eb6bfeee430ff25`。
独立分支 `feat/b3-benchmark-readiness`；工作树
`D:/softrobot-agent/.worktrees/b3-benchmark-readiness`。

**结论：conditional。现有任务、数学、控制和独立物理接口可以承载有限 B3 试点；
0.50/0.70 s 的物理难度和可行性尚未验证。三个待授权草案已实际 prepare/bind，
本轮 Provider、真实数学评价、数学模型准备、内部求解、独立物理、NMPC、PPO 全部为 0。**
未启动 B3 正式研究，未重跑 C3 A/B、F1/F2、G1/G2。

## 历史能力审计与极简修改

已读 [A/B](c3_ab_live_comparison.md)、[F1/F2](c3_f1_f2_decision_continuity.md)、
[G1/G2](c3_g1_g2_decision_validation.md)、[最终 G2](c3_g2_scientific_decision_loop.md)
及根 `AGENTS.md`。原 `import_history()` 能导入同任务物理历史、数学结果和控制种子，
但同任务约束使它们不能冒充新 deadline 的实验；`supplied_evidence/scoped_context`
可以提供限定背景，原 working_set/evidence_read、research_intent、action_trace、ResultCard
和 diagnostic_relations 均可复用。缺口是关键历史事实未稳定进入每轮请求，而非缺少数据库。

本轮只在这些既有模块内增加派生视图：

- **L0**：每轮 `agent_decision_brief` 自动投影当前相关的最多五条历史结论。
  此配置为三条，完整 UTF-8 投影 **1,719 bytes**。每条含原 Study、方法、主要数值、数学/物理范围、
  当前任务是否匹配和稳定的 L1 pointer；共同提示机制未决、有目的复核合法、历史不授予当前执行或 SELECT 资格。
- **L1**：`evidence_read(reference=<原已注册锚点>, view=working_set,
  pointer=/research_history_index)` 返回以原结果 artifact ID 为键的完整索引。
  `/research_history_index/<artifact_id>` 可读取单条：原问题、原 Agent 假设最多 240 字符原文摘录、
  候选、方法、结果、限制、未决问题、原 Plan/结果/归档位置及控制—数学来源关系。
  结论从原 Store 事实生成，不保存另一套结论表，不用 Reporter 改写动机。
- **L2**：仍为原结果、完整模型、控制、轨迹、Plan、Worker 日志、评价器结果及原归档收据。
  新的 `research_decisions.background` 只声明原归档引用及必要依赖；沿原 `archived()` 校验后存入原 Store。
  原结果登记到 `scoped_context`，依赖仅保持可读，不加入当前 candidates/results/analysis_results。
  没有新记忆数据库、索引数据库、历史 Agent、缓存或 SHA 清单。

独立 NMPC 的原始执行文件另由 L1 `source.execution_files_query` 导航到
`evidence_read(reference=<声明的旧 NMPC 结果>, view=working_set, pointer=/historical_execution_files)`。
该路径复用原 execution_source/archived，列出原文件引用，并按需读取 JSON 或 gzip JSON，
例如 `/historical_execution_files/controller_observations.json/30/actual_tension_n`。
实际验证了 18 个原文件入口及四路实测张力读取，不复制新执行、不获得完整当前验收读取信用；
非 JSON 文件仍保留在原归档，不能冒充 JSON 数学证据。

四种身份继续分离：当前 Study 的 fresh results；明确声明的旧 Study 背景；原 public_prior_manifest
中的工程默认值；research_intent/action_trace 中尚未验证的 Agent 假设。
跨任务背景只可支持 `empirical_search` 决策引用，不能证明新任务的模型可行性或验收。
定向检查确认强推断仍被 `EVIDENCE_TASK_IDENTITY_MISMATCH` 拒绝，旧物理结果不能 SELECT。

在 CONIC 的原 `mathematical_capabilities` L1 方法说明中，`previous_work` 会核对真实请求模板、
候选物理结构、完整任务、控制器/后端/网格/动力学及原协议。
符合时提示 `same_configuration_and_request`；完整科学实验等价性仍为 `unknown`，
因为尚未核对重建矩阵、环境、精确工作点、控制输入和数值网格。
不同工作点或 deadline 不会被误标为已完成。提示要求说明新增信息或复核目的，**不禁止重复计算**。
原执行准入、预算、恢复和独立验收没有被替换。

## B 第六候选的原始见证

三条均属于 `c3-b-100ms-20261025`，候选为
`e0f2ccf53680ad00b1ed5d258d8b5eed38ced55fbc07f3bde07d3e5ce415ac1d`。

| 原方法/结果 | 记录的主要事实 | 可信范围 |
|---|---|---|
| sampled-affine-conic-minimax-v1，`87d62673…22931` | violation −0.19999999999954968；保持预测峰速 0.013754640667324113 m/s；终点/保持误差约 8 mm；完整控制见证存在 | 局部采样仿射模型见证，无独立物理成功资格 |
| 同见证 MuJoCo 回放，`3f67ca10…8612f` | 终点/保持误差 13.706442 mm；保持峰速 0.2741264353343463 m/s；valid_failure | 原完整独立物理失败 |
| 同结构 NMPC，`ead9bd6e…8474f` | 终点误差 4.092012 mm，保持误差 4.517235 mm；保持峰速 0.18173358255275762 m/s；valid_failure | 位置条件通过，停稳失败；另一套控制 |

完整 ID、Plan 和依赖见三份草案的 background 声明；
原 [B Store 导出](../../evidence/c3_math_search_ab_100ms_20261025/immutable_artifacts.tar.gz) 不变。
CONIC 控制回放的原 provenance 确实指向上述数学结果。NMPC 与 CONIC 不能直接相减当作模型误差。
原同输入诊断仍缺完整绑定的预测样本和逐采样对齐差值，不能重建不存在的误差证据。
见证实现、GVS/MuJoCo 同输入差异、终端制动和结构贡献仍是竞争问题，尚未识别原因。

## 真正的完整请求核对

读取封存 G2 的原请求 #1、#4，在只读副本中明确声明上述三个已获本轮授权引用的来源，
通过生产 `live_model_class.format_request()` 构造请求末尾的 CURRENT_RESEARCH_PACKET，
再序列化完整 HTTP wire。原 transcript、工具 Schema 和实际 SDK 截断预览保留，未修改封存 Study。
L0 是 SDK Offload 处理后追加的请求正文，不是另一个可能被 offload 的大工具反馈。

| G2 原边界 | 原完整 wire bytes | 新完整 wire bytes | 新历史投影 bytes |
|---|---:|---:|---:|
| #1，选择方法之前 | 64,042 | 66,101 | 1,719 |
| #4，已有真实 offload 预览 | 98,723 | 100,783 | 1,719 |

两份新 wire 均完整含原 Study、旧 CONIC 分数与速度、物理回放失败、NMPC 失败及未决制动/模型问题，
尾包没有 `[Truncated`，没有完整矩阵、输入序列、采样轨迹或 raw_primal 进入历史 L0。
因此 **G2 那项旧工作现在可以在实验前被发现**；L1 还会提示同配置同请求。
这证明可见性与读取路径，不证明真实模型一定避免重复、理解正确或决策质量改善；本轮真实 Provider=0。

核对记录：[offline_verification.json](../../evidence/b3_benchmark_readiness/offline_verification.json)；
[两份完整离线 wire](../../evidence/b3_benchmark_readiness/g2_projected_requests.json.gz)。

## B3 条件、接口与证据盘点

任务是快速移动并稳定停止，复用 Reach/Hold、ResearchTaskAdapter、GVS、CONIC、NMPC、
MuJoCo、原 task_constraints/feedback/physical_replay 和独立 `evaluate.reach@1.0.0`。
不新增 evaluator、优化器、任务层级或 Benchmark Agent。

共同冻结：目标世界坐标 **[0.29, −0.035, 0.19] m**；mount [0,0,0.15] m，
world_base_x_forward_yz_cross_section，重力 [0,0,−9.81] m/s²；所有生成自由度 qpos/qvel 为零，
unspecified=zero；终点与保持位置限均 **0.010 m**，保持速度限 **0.020 m/s**，保持长度 **0.05 s**，
理想张力每路 **[0,8] N**。控制/验收采样 **0.01 s**，物理积分 **0.0005 s**，inclusive 保持窗口六点。
完整执行、数值有效、覆盖、solver_errors 和张力边界继续由原独立协议核对。
速度软权重和求解收敛均不能代替这些硬阈值。

| 候选时限/任务文件 | 保持窗口 s | 控制区间/配置物理步数，均未执行 | 已有难度证据 |
|---|---|---|---|
| [0.35 s](../../tasks/reach_hold_b3_035.json) | [0.30,0.35] | 35 / 700 | C3 相同物理条件下，A/B 共七次完整验收均失败；不是整个设计域不可行证明 |
| [0.50 s](../../tasks/reach_hold_b3_050.json) | [0.45,0.50] | 50 / 1,000 | 仅接口/网格预检；没有此时限的物理或数学能力评价 |
| [0.70 s](../../tasks/reach_hold_b3_070.json) | [0.65,0.70] | 70 / 1,400 | 仅接口/网格预检；没有此时限的物理或数学能力评价 |

实际为每个新时域重建任务、控制序列、采样约束、预测参考和分析协议，并验证最后 0.05 s
预测窗口为五个控制区间。0.35 s 的旧序列和旧分数没有用于新时限验收。
三种时限均支持原 CONIC 完整离散任务约束表达，正式执行授权仍为 false。
表中“物理步数”只是配置网格大小，**实际原生积分步数为 0**。
较宽松时限是否容易、0.50 s 是否靠近能力边界、0.35 s 是否过严，均未由本轮确定。

已尝试：C3 六个结构的 CONIC、同见证回放、A/B NMPC、四次局部控制响应回放。
根段 Young 7.2→10.45 MPa 的模型分差约 2.6e−13，原数值区间重叠；F2 半径
17.5/18/18.5 mm 在固定输入下有差异，但控制重优化后均约 −0.2，可信方向未决。
G2 又完整复现同一旧见证。复用这些记录，没有为了追求分差改变阈值、模型或目标。
本轮未花数学额度：已有代理的平分现象不足以给物理难度定级，新增模型筛选的必要性尚不充分。

可能带来新信息的是：冻结 0.50 s 的真实控制优化与独立验收、同初态同完整输入的 GVS/MuJoCo 对照、
有对照的终端制动/控制初始化，以及在同等控制机会下的新结构。
这些只是未来实验选项，Agent 仍自主选路线，不预设必须改结构。

| 接口/条件 | Readiness |
|---|---|
| Reach/Hold 合约、CONIC 离散约束、当前初态 GVS/native 方法、独立 MuJoCo、完整 ZOH 控制 | ready：旧链路已接通，本轮解析/绑定/构造预检通过；没有新数值成功结论 |
| 0.50/0.70 s 难度、实物理可行性、控制充分性 | conditional：未测量 |
| 旧 B update-30 原生状态直接用于新 Study | blocked：原 OWNED_NATIVE_EXECUTION_REQUIRED 仍保留；不伪造跨 Study 状态所有权 |
| 新 Study 的正式发送、科学执行与 Handoff 激活 | conditional：需后续显式身份绑定授权及原准入登记，本轮未授予 |
| PPO、SoRoSim、T2 敏感性在此首轮草案 | 未开放；PPO 预算 0，不声称 B3 已验证；SoRoSim 不是本任务必需依赖 |

## 首次试点冻结配置与公平对照

建议首轮仅采用 **0.50 s**，原因是给已知 0.35 s 停稳失败增加 0.15 s 执行时间，
仍保留原保持长度、硬阈值和控制/物理网格，能够测试新的条件而非重算旧 CONIC。
这是一项工程试点选择，不是“容易”或“边界已找到”的科学判断。

完整配置：
[A](../../configs/research/study_b3_pilot_a_draft.json)、
[B](../../configs/research/study_b3_pilot_b_draft.json)、
[C](../../configs/research/study_b3_pilot_c_draft.json)、
[共同参考生成参数](../../configs/research/b3_reference_generation.json)。
三个草案均已 prepare/bind 到 `e39aae516dc48f24454960f207d5a9f7123aa0e7`，
完整 resolved identities、零使用账本和待授权状态见
[冻结清单](../../evidence/b3_benchmark_readiness/frozen_drafts.json)。没有生成正式候选或执行正式科研。

基准为原 B 第六候选的**结构参数**：两柔性段，长 0.16/0.11 m，Young 10.45/5.4 MPa，
圆截面半径 8 mm，各段 12 cells，四腱均跨两段，路由半径 18 mm、guide_s=0.5，预张力 0.2 N。
必须在每个新 Study 中重新合法生成，不把旧候选 ID 变成当前所有者。
A/B 的 fixed_structure_reference 复用 same_robot_structure，拒绝结构变化，允许控制选择变化。
C 的合法域直接来自原 FamilySpace v2 的 1–3 段、3–4 腱子域；根段长 0.08–0.24 m、
第二段 0.06–0.20 m、其他段 0.06–0.24 m，Young 2–15 MPa，路由半径 0.014–0.023 m；
截面、连接、路由及其他条件域以该冻结 FamilySpace 为准。正式验收固定每段 12 cells、每路上限 8 N。

| 组 | 结构与控制 | Provider 含 Reporter / 数学 / 共享独立物理上限 | NMPC / 回放上限 |
|---|---|---|---|
| A | 固定参考结构，原默认 GVS NMPC 配方，按新完整时域执行 | 16 / 0 / 1 | 1 / 0 |
| B | 固定同一结构，允许控制权重、合法配方/初始化和有界显式序列的重优化 | 32 / 8 / 4 | 2 / 2 |
| C | 至多两种物理结构，含同一参考；修改结构可选，各结构重新优化控制 | 32 / 8 / 4 | 总 2 / 2；每结构至多 1 NMPC + 1 回放 |

B/C 每组 public operations=80，保留 6；Provider 保留 4，均包含在总数中。
native 控制回调上限 8、更新 2、knots 4；每次实际内部尝试、前缀重建和积分仍计原数学账本。
总上限为 80 Provider、16 数学、9 独立物理启动、5 NMPC，PPO=0；不是必须用满的目标。
先完成 A，再分别运行隔离的 B/C；不把 B 中途科学结果注入 C。

关键比较 B/C 使用同一 task、验收、FamilySpace 和总预算。共同 NMPC 配方为 horizon=10、
substeps=1、replan_period_s=0.1、每次求解 max_iterations≤120、tolerance=1e−6。
0.50 s 正常调度预计五次在线求解、50 个控制区间；真实失败/重试/沿用次数照实记录。
结构固定由生成边界执行；每结构机会和上述额外求解设置上限由冻结协议与监督者在派发前核对，
不能无监督改配方后仍声称公平。越界运行保留费用和结果，但不支持本 B/C 受控比较。
直接复用现有 ledger、Plan、request/receipt、candidate physical_design_identity 分组审阅，未加第二套预算账本。

B 应使用不同且有理由的控制优化机会；如果预算内仍未充分优化或没有可靠求解，只能报告最佳已找到结果。
C 不因拓扑变化获得更多独立启动或迭代，也不能靠代理分数 SELECT。
控制优化单独找到完整独立通过就是成功，不强迫修改结构。
**现有证据不足以说明结构修改在充分控制优化之外有额外任务收益，更不能证明固定结构理论无解。**
未来综合三时限任务组必须冻结同一物理结构，各时限分别优化控制，不能拼接各自最优结构宣称整组能力。

## 后续正式运行入口与剩余激活步骤

本地三份冻结 Store 位于 `runs/research/<study_id>`，现有 ID 分别为
`b3-pilot-050-a-draft`、`b3-pilot-050-b-v1-draft`、`b3-pilot-050-c-v1-draft`。
`prepare`/`bind` 已验证；在其他机器上先使用同一已提交配置走相同入口。
本轮不写 formal_study_authorization、不设 session_handoff_live_admitted，不调用 run。

后续另行授权后，监督者需用原 formal_study_authorization + scope_identity 机制绑定每个 resolved_identity，
包含 Provider/科学预算、出口和公平协议；引用已有真实 Handoff 准入及其来源，再沿原机制登记
request_feedback 范围，不能只无来源地切布尔值。参考原 C3 准入 artifact
`aaaf83b7e9f8e2c8e573e42cc7bcef163197d83edcc9537322b97bfee4ac4a88`
及后续 F1/G1 的真实交付记录。没有授权或准入时下面的 run 会按原边界拒绝。

授权后共同参考的工程生成仍用原入口，不写新运行框架，例如对 A：

```powershell
$researchPython='D:/softrobot-agent/.worktrees/s135-task-conditioned-control/.s135-env/Scripts/python.exe'
$env:OPENBLAS_NUM_THREADS='1'; $env:OMP_NUM_THREADS='1'; $env:MKL_NUM_THREADS='1'
# 仅在后续正式授权及 Handoff 准入均已登记之后；本轮未执行：
@'
from tools.platform_host import Host
from tools.research.core import ROOT
from tools.research.state import require_authorization
from tools.research.design import generate_candidate
from tools.state_io import read
run='b3-pilot-050-a-draft'
h=Host(ROOT/'runs/research'/run,run,actor='unified-research')
require_authorization(h)
result=generate_candidate(h,read(ROOT/'configs/research/b3_reference_generation.json'),
    dict(origin='authorized_common_engineering_reference_no_task_outcome'))
assert result['status']=='generated',result
'@ | & $researchPython -
& $researchPython -m tools.research run --run-id b3-pilot-050-a-draft --session-handoff --handoff-request-bytes 160000 --pause-exploration-remaining 4
```

B/C 换为各自已冻结 ID，采用同一生成参数；恢复用原 `recover` 和 `run --restore-only`，不重建 Store。
第一次 fresh、complete、final-fidelity 的独立通过须公开读取并精确 SELECT；额外成功确认=0。
未通过则沿原 STOP 全结果索引读取、引用，保留失败、未决机制和下一实验建议。
没有需要新增的必需 evaluator/控制执行接口；剩余是明确授权/准入激活、实际难度验证和严格按协议执行的控制对照。

## 资源、验证与版本

本轮真实 Provider=0，真实数学评价 **0/6**，数学模型准备=0、内部 CONIC/其他求解=0，
原生积分步=0，独立物理=0，NMPC=0，PPO=0。工程构形/网格/序列构造与包导入检查不冒充数学能力评价。
离线 HTTP wire 构造和隔离 SDK mock 不发送真实请求；没有实际 API 用量。

六项定向 unittest 35.562 s 通过：新历史 wire、L1/L2/复核范围、新时域/独立阈值/固定结构、
原数学可比性、原 request-feedback Handoff、原 A/B 冻结配置回归。
最后一处方法标签整理后，仅相关两项回归再跑，6.876 s 通过。
补齐 NMPC 原始文件路由后，仅其时域/读取范围与 L1/L2 两项回归重跑，25.169 s 通过。
随后只运行只读 wire 审阅和工程 prepare/bind/audit，没有全仓测试或科学重算。
SDK 的 RequestBoundaryHandoff 异常输出是该既有测试预期的切换控制流，最终为 OK。

生产修改仅七个既有文件，相对指定基线 **+112/−4，净增 108 行**：

| 文件 | +/− | 内容 |
|---|---:|---|
| tools/research/research_context.py | 75/1 | 原 Store 背景导入、L1 历史结论、紧凑 L0 投影 |
| tools/research/core.py | 18/0 | 原 working_set 内按需读取历史执行包的真实 JSON 文件 |
| tools/research/task_constraints.py | 6/0 | 原 CONIC 方法说明中的已有工作/复核提示 |
| tools/research/config.py | 5/2 | 解析 background 和固定结构引用 |
| tools/research/design.py | 4/0 | 复用 same_robot_structure 保持固定结构组 |
| tools/research/evidence_policy.py | 3/1 | 允许显式跨任务背景的 empirical_search 引用，保持强推断边界 |
| tools/research/state.py | 1/0 | 原关闭阶段读取白名单保留声明的 L2 依赖 |

测试、七个任务/配置文件、本文与精简离线证据另计；未新增生产模块。
实现提交 `ce43bc1df4134fb5098779c2cfc5f89a04c58f8b`；草案身份修正提交
`e39aae516dc48f24454960f207d5a9f7123aa0e7`。
早期两个零使用、未授权的工程准备已占用 B/C 旧草案 ID，故沿原 engineering_count_budget_closure
行政关闭并保留原 Store/身份/零费用，不伪造 Agent STOP，也没有重置授权预算；最终 B/C 使用新的 v1 草案 ID。
冻结清单保留这项工程过程，旧 C3/A/B/G1/G2 完全不变。

原始文件路由补齐后重新绑定同一批待授权 Store，保持任务身份、全部成本和科学 profile。
共四个提交：实现、未用草案身份修正、原始输入按需读取、最终 Readiness 记录。
本文所属提交是最终交付提交，不通过自引用制造 Git SHA；其完整 SHA、普通 push 后远端 HEAD
和目标树清洁状态在最终交付消息中核实给出。原主树既存未跟踪环境/runs 文件未清理或覆盖，
未强推、未合并 main，未提交密钥、环境、临时日志或重复大型归档。Readiness 准备到此停止。
