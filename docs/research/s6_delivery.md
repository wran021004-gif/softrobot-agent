# S6.0–S6.3 交付报告（2026-10-19）

**已找到第一个通过原 reach_hold 全部注册约束的开环方案。** Agent 在 S6.3 第 24 次新独立 MuJoCo 评价中发现通过结果，随后读取、精确选择并立即停止。终点和保持最大位置误差均为 **0.0054392057526873525 m**，保持最大速度 **0.019977863170385274 m/s**，G=0。这是一次原任务的采样仿真通过，不是 NMPC/RL 反馈控制、硬件、连续时间、鲁棒性或重复性证明。

入口：[可行见证](../../evidence/s6_3/feasible_witness.json)、[完整配置与35×4实际控制](../../evidence/s6_3/best_control.json)、[原始决策和反馈](../../evidence/s6_3/decisions.json)、[独立核验](../../evidence/s6_3/independent_audit.json)、[总费用](../../evidence/s6_verification/accounting.json)。

## A. 仓库、冻结与验收

工作树 `D:/softrobot-agent/.worktrees/sorosim-matlab-nmpc`；分支 `feat/sorosim-matlab-nmpc`；起始 SHA `68c9e61413e896e191000d47c0509eb7be6a4f1b`，开始时干净，fetch 后差异 0/0。IDE 中 rl-control-pilot 和其他工作树未修改。最终源码 SHA：`db0008f8bf89d67babf60ed82db99a231ede292e`。最终交付还含本文，其提交 SHA 在最终回复列出，避免本文自引用。交付后核对 HEAD 与 origin 分支一致、目标工作树干净；无 force、reset 或其他分支合并。

| 阶段/Study | 实际完成与科学冻结 | 结束 |
|---|---|---|
| S6.0 | P1 精确导入、完整控制、真实超限样本、约束/Pareto/预算上下文；历史基线不重跑 | 工程验收完成 |
| S6.1 | 公共决策/证据审查、控制搜索、模拟集成、4 次真实 provider；冻结 `5528ef5e7d1ec4e4aab96db69413f9ecdc9f4c06` | 工程 provider 预算关闭，非模型 STOP |
| S6.2 | 自主两轮搜索、44 次新评价；冻结 `d04154ee72c2fb7bde7cbc87c12bc23a940a6f76` | 原生模型 STOP，严格失败 |
| S6.3 | 自主新结构及适配，读取失败反馈后改回继承结构；冻结 `c780e3fb826c0b6f09057666da1830c435f71374` | 原生模型 SELECT，首次通过即停止 |
| 镜像工程 | 独立迁移验证；冻结 `5285c3c4a5b45765efc65de341d416238c027e93` | engineering STOP，不能归功于 Agent |

实现、测试、commit/push、冻结、真实运行与导出分开。S6.1 结束后才修复引用易用性；S6.2 结束后才添加可选余量目标并冻结 S6.3。成功后仅做兼容、只读摘要与停止/选择准入收尾，未改变已记录科学输出，未重开、迁移或重新执行封存 Study。

## B. 实现与复用

生产代码相对起点 **+419/-35，净 384 行**，逐文件统计见附录。新增生产模块只有 research_context.py，负责授权历史导入和紧凑上下文；没有第二套 Agent、Store、缓存、预算、评价器、物理后端或求解器注册系统。

新审查由 research_decisions.version=research_decision_v1 显式启用。Plan 的 decision 与 control_search 为兼容扩展；旧 search 仍是原结构/数学搜索。旧设置序列化不插入新默认项。只读验证证明旧 P1 resolved configuration 逐字段相等，旧 S6.2 原请求 ID 可恢复同一收据且费用不变。

Core 从注册 Store artifact 解析证据，核对任务/初态、设计、模型范围和允许推论；非零初态不能被零初态规则掩盖。模型自报 verification_status、supported_inferences 不作为证书。已知控制源、原始采样和候选可用于探索；未知引用、越界全局推论被拒绝。合法探索不要求先证明数学可行。独立数学/物理/RL 入口保留能力、身份、预算、重复性与生命周期准入。

控制搜索仍经 physical_replay、Core、统一 Store、逐次共享后端计费和原评价器。批次有限、保护收尾、已结算控制精确复用、未知结果不自动重启；首次完整通过禁止新探索，且必须先精确 SELECT，不能用 STOP 跳过选择。中断恢复只封装已存在输出，不宣称恢复优化器内部状态。

v1 保留旧 35×4 搜索契约；v2 从实际通道、时间轴和输入界推导维度。窗口掩码同时应用到基函数与实际输入；终点/保持位置可用不同阈值。可选 safety_margin_fraction 只改变响应模型目标，零默认保留旧行为；原物理验收阈值不变。

## C. 原始 Agent 决策与反馈

各 Study 的 decisions.json 和 immutable_artifacts.tar.gz 保存原始 provider 请求/响应、tool use、Plan、反馈、来源与费用。manifest 逐项列出 SHA256；以下研究参数由模型实际选择，工程预处理单列。

| 决策 | 实际参数及反馈 | 后续 |
|---|---|---|
| S6.1 | 模型提出 2 回调 response、窗口 [0.27,0.35]；保护额度拒绝启动。另有错误 /samples 路径与未注册引用 STOP，原样保存 | 4 请求后工程关闭，不是 accepted model STOP |
| S6.2 response | P1 源1b5bbfbd…；窗口 [0.24,0.35]、结点 [0.24,0.30,0.35]；差分0.02 N、半径0.1 N、界0.35 N、32回调；31次新评价 | 两次模型提议将 G 降至1.97e-7，仍严格失败；模型读取 best 与控制后改方法 |
| S6.2 pattern | 模型仍选 P1 源而非近通过源；相同窗口/结点；步长0.02 N、界0.05 N、16回调；13次新评价，另有缓存 | 本批最优G=0.012979516，未优于前批；模型 STOP 并提出寻求严格余量的问题 |
| S6.3 新结构 | E近端12 MPa、远端7 MPa，近端semi_z=0.0084 m、路由半径0.0195 m；从S6.2最优显式 adaptation_from；全时域结点[0.05,0.15,0.25,0.35]，22回调、0.01 N差分、0.1 N半径、2 N界、5%模型目标余量 | 22次评价，最优G=2.052652485，未通过。有限且不等的适配预算不能证明结构本质优劣 |
| S6.3 回继承结构 | 近通过源3046329a…；窗口[0.18,0.35]，结点[0.20,0.26,0.31,0.35]；20回调、差分0.01 N、半径0.05 N、界2 N、5%模型目标余量 | 历史基线免费复用；第二个有限差分探针通过，仅新增2次评价即停止；模型读取并精确 SELECT |

**通过的是有限差分探针，不是优化器提议。** 系数向量只有索引1为+0.01 N，其余为零，即首结点的 tendon_1；窗口外输入完全不变。该轮尚未完成响应矩阵/优化子问题，不能归因于 SLSQP 收敛或宣称达到5%余量。实际速度余量约2.21368e-5 m/s，即限值的0.1107%。

LLM 文本不作权威事实：S6.2 STOP 中误称42个结果，账本实际为44；其“边界/数值问题”仍是未验证解释。原文本保留，报告采用确定性计数和原验收。

## D. 数学、数值与适用范围

导入了 S5.9 三条局部制动/静态敏感性证据，原 hash、模型、操作点、任务和限制保留。没有新增注册数学分析、完整 NLP 或独立数学重积分。共完成3个 SciPy 局部响应子问题；迭代数、状态、预测及物理差异见 accounting.json.local_solver_records，不是全局证明。

S6.2 最优提议模型预测 gap约3.77e-15，实际1.97e-7，说明预测等式不能代替物理验收。新结构的速度经适配改善但位置仍失败；最终探针没有先验下降预测。未访问候选的保证、连续时间误差界、结构排除和根因证明均未建立。

## E. 精确结构—控制见证

评价 `a92601d47c8143b458c598caeaaaf3881a861e01ff239cdd0b72e275bbb17fc3`；候选 `dd98c6eabc6c2ebd5c0588ffdc91325e9cccbfced6b05c30c28d268b38c90d32`；控制源 `42a8565869c2e6769befdbf5b1d624a6f2b9886488f9be8f06d097d0c35d044d`。

原任务身份 `882b3493037dcc8f8da294b3473e1223f0465e92c35bc3064bfc42d467bf212e`；模型 `8f8eceb5f74d4b171c87f333db4db0f353aad051b375ff26aca795f7ac1fbaf2`；设计 `10035885ded80b7afbf2faa28988c6275a18ac04f3232c5d0972acced81af9ad`。完整 raw/evaluator 引用在 feasible_witness.json。

最终选择继承的两段四腱结构：长度0.195/0.11 m，E=10.45/5.4 MPa；近段椭圆半轴0.01175/0.0076 m，远段矩形0.0133×0.0095 m，原腱路半径0.018 m。其余材料、截面角度、mesh、零初始化、seed和后端以完整 configuration 为准，不以简述替代输入。

控制为 ideal_tension 开环实际张力，35个0.01 s区间、顺序tendon_0…tendon_3、各[0,8] N。原目标[0.29,0.035,0.19] m，时长0.35 s、物理步0.0005 s，原命名关节零初态。完整36个时间结点、35×4张力及配置在 best_control.json；没有新增成功 NMPC/RL 控制器。

## F. 全部物理结果

| 组别 | 新评价 | 最优终点m | 最优保持位置m | 最优保持速度m/s | G | 验收 |
|---|---:|---:|---:|---:|---:|---|
| P1历史 | 0 | 0.005193064009 | 0.005193909968 | 0.021090040785 | 0.054502039 | 有效失败 |
| S6.2两轮 | 44 | 0.005266495050 | 0.005266495050 | 0.020000003941 | 1.970680878e-7 | 有效失败 |
| S6.3新结构 | 22 | 0.030519849824 | 0.030526524845 | 0.059701727929 | 2.052652485 | 有效失败 |
| S6.3继承结构新基函数 | 2 | 0.005439205753 | 0.005439205753 | 0.019977863170 | 0 | **通过** |
| 镜像工程 | 4 | 0.072223750019 | 0.072223750019 | 0.022401105675 | 6.222375002 | 不同目标失败，不与原任务混排 |

逐次完整结果、接受组件及原始采样都在各 summary、archive 与 manifest；未丢弃失败。全部72次新评价完整有效。最终 solver_errors=0、force_bounds=0、holding_coverage=6，evaluation_validity、execution_complete、task_evaluator及全部位置/速度条件均 passed。

| 保持采样s | 最终位置误差m | 最终速度m/s |
|---:|---:|---:|
| 0.30 | 0.005400848288 | 0.019977863170 |
| 0.31 | 0.005367155130 | 0.013483061601 |
| 0.32 | 0.005298472750 | 0.009382691468 |
| 0.33 | 0.005237558422 | 0.019890531675 |
| 0.34 | 0.005288221033 | 0.011887499758 |
| 0.35 | 0.005439205753 | 0.019062396582 |

独立只读审计校验 S6.2 的522个成员/44个新实验、S6.3的513个成员/24个新实验，逐项SHA256、候选/模型/任务绑定、实际施加控制、窗口外不变和重算G均一致。跨Study共72个不同科学身份，合计50,400个物理步和2,520个控制区间。S6.3唯一通过是最后一次新评价，选择引用相同，之后新增物理启动为0；没有因复核再仿真，没有重复性确认。

## G. 成本和剩余额度

| Study | provider已用/限 | public已用/限 | 共享后端已用/限 | 数值账本s | live墙钟s |
|---|---:|---:|---:|---:|---:|
| S6.1 | 4/4 | 6/14 | 0/2 | 0.305279 | 104.599 |
| S6.2 | 9/24 | 66/90 | 44/48 | 49.456617 | 611.529 |
| S6.3 | 6/24 | 32/90 | 24/48 | 40.174542 | 218.543 |
| 镜像工程 | 0/0 | 8/12 | 4/4 | 5.058348 | 不混计模型live |

总计19 provider、112 public operations、72完整后端评价。prompt/completion/total tokens=1,394,940/94,523/1,489,463；reasoning=76,700；cache hit/miss=230,272/1,164,668。按request_id去重，19条都有usage。无金额收据，货币费用未知，不自行估价。

新增注册数学分析/NLP/数学重积分/完整NMPC/PPO训练与评价均为0。3个内部SciPy子问题未独立计CPU秒，不能把数值账本冒充完整CPU计时。live墙钟不覆盖全部开发、前期准备及人工审批等待，不声称节时或成本优势。

S6.3成功时尚余18 provider、58 public、24后端额度，均停止探索。所有收据结算，无pending、资源占用或活动训练worker。不借用旧余额，不重置预算，不以新Study重做相同科学内容。

## H. 迁移与通用性

镜像工程Study为engineering，0 provider、4次物理评价；验证新目标身份、材料变化（近端E=10.45→10.5545 MPa）、显式控制初始化和内层适配，没有转移旧验收。y=-0.035 m任务的真实失败不是迁移成功；原目标下的新结构适配另由S6.3的22次评价验证路径。

纯接口夹具覆盖1/3/6通道、7/12/20周期、不同结点、窗口及不同终点/保持阈值。真实物理仅验证两段四腱、35周期、已声明材料/截面/腱路变化和两个目标。当前局部优化器针对reach-hold范数约束；tracking等不适用任务、跨拓扑不兼容初始化明确unsupported，不静默替换问题。障碍/接球/扰动平台、任意拓扑物理执行、硬件/鲁棒性/连续时间及统计优越性未建立。

## I. 测试与异常记录

完整集合121项：120通过、1跳过、0失败/错误；收尾分组另有47项和26项相关检查通过，不重复相加。跳过项仅为显式SOFTROBOT_REAL_RL_TEST=1才运行的真实RL链。普通unittest没有provider、完整NMPC/PPO或物理rollout。模块、输出和源码hash见 tests.json。

命令为既有 .mainline5-env/Scripts/python.exe -m unittest，模块含 tests.research 下 test_s6_research、test_local_control_search、test_candidate_portfolio、test_evidence_policy、test_control_correction、test_count_continuation、test_s58_agent、test_s59_guidance、test_agent_feedback、test_rl_integration。PYTHONPATH含仓库/已装MATLAB Engine，三个数值线程变量为1；未安装/升级依赖。

早期tempfile ACL/SQLite清理及线程环境准入测试失败已纠正，fixture改用独立UUID。数据库建立前一个零科学消费的旧预飞grant保留、未重置，真实研究使用独立-live-ID。S6.1错误路径、保护拒绝、引用错误、工程关闭全部保留。

自动审批最初两次拒绝外发，发生在进程创建前、0请求/0后端；用户随后在当前对话明确批准DeepSeek目的地、科学数据范围和4/24/24上限，才实际发送。prelaunch_review.json是当时记录，非当前阻塞。原始请求不持久化认证header；新证据/archive对实际配置key及token模式扫描0匹配，未输出/提交key。

派生summary已分开模型STOP与SELECT，原final_disposition为权威；修正轨迹在accounting.json，未改写原Store、费用或科学archive。最终只读claims的新版本识别一次已执行的新结构控制适配和原任务通过，旧claims语义保留。收尾分类预算/停止视图、选择准入与兼容增强不冒充过去模型的输入；旧P1 resolved配置逐字段相等，旧S6.2收据实际恢复0新增费用。

## J. 最终结论

首次原任务可行解发现完成。模型自选方向、失败反馈、新结构适配、转回继承结构及精确选择有原始调用证据。更硬的新结构未通过，最终成功来自继承结构的新基函数探针；不能声称新结构优越、5%余量达成、NMPC/RL成功、全局保证或Agent优于固定方法。适配预算不等，正式P4消融/统计比较未运行。所有科学Study已停止，不继续消耗剩余额度。

## K. File-by-file inventory

Relative to the starting SHA. JSON lines are evidence volume; each immutable archive member is listed separately in its manifest.

| File | Added/deleted or size | Responsibility and reuse |
|---|---:|---|
| `configs/research/study_s6_1.json` | +89/-0 | Independent frozen capabilities, authorization and finite counts |
| `configs/research/study_s6_2.json` | +98/-0 | Independent frozen capabilities, authorization and finite counts |
| `configs/research/study_s6_3.json` | +406/-0 | Independent frozen capabilities, authorization and finite counts |
| `configs/research/study_s6_transfer.json` | +60/-0 | Independent frozen capabilities, authorization and finite counts |
| `docs/research/s6_delivery.md` | +202/-0 | Delivery status, evidence, costs and limits |
| `evidence/s6_1/authorization_resolution.json` | +14/-0 | Actual decisions, costs, observation summary or read-only audit |
| `evidence/s6_1/decisions.json` | +366/-0 | Actual decisions, costs, observation summary or read-only audit |
| `evidence/s6_1/payload_manifest.json` | +29/-0 | Exact payload or artifact/hash inventory |
| `evidence/s6_1/prelaunch_review.json` | +18/-0 | Actual decisions, costs, observation summary or read-only audit |
| `evidence/s6_1/study/archive_manifest.json` | +425/-0 | Exact payload or artifact/hash inventory |
| `evidence/s6_1/study/calls.json` | +142/-0 | Actual decisions, costs, observation summary or read-only audit |
| `evidence/s6_1/study/configuration.json` | +3034/-0 | Actual decisions, costs, observation summary or read-only audit |
| `evidence/s6_1/study/disposition.json` | +95/-0 | Actual decisions, costs, observation summary or read-only audit |
| `evidence/s6_1/study/immutable_artifacts.tar.gz` | binary 641150 bytes | Original immutable Store artifacts; exact member hashes in manifest |
| `evidence/s6_1/study/ledger.json` | +24/-0 | Actual decisions, costs, observation summary or read-only audit |
| `evidence/s6_1/summary.json` | +502/-0 | Actual decisions, costs, observation summary or read-only audit |
| `evidence/s6_2/best_control.json` | +2502/-0 | Complete configuration/control and exact independent result refs |
| `evidence/s6_2/decisions.json` | +1502/-0 | Actual decisions, costs, observation summary or read-only audit |
| `evidence/s6_2/independent_audit.json` | +1243/-0 | Actual decisions, costs, observation summary or read-only audit |
| `evidence/s6_2/study/archive_manifest.json` | +3137/-0 | Exact payload or artifact/hash inventory |
| `evidence/s6_2/study/calls.json` | +1668/-0 | Actual decisions, costs, observation summary or read-only audit |
| `evidence/s6_2/study/configuration.json` | +3043/-0 | Actual decisions, costs, observation summary or read-only audit |
| `evidence/s6_2/study/disposition.json` | +303/-0 | Actual decisions, costs, observation summary or read-only audit |
| `evidence/s6_2/study/immutable_artifacts.tar.gz` | binary 3620243 bytes | Original immutable Store artifacts; exact member hashes in manifest |
| `evidence/s6_2/study/ledger.json` | +24/-0 | Actual decisions, costs, observation summary or read-only audit |
| `evidence/s6_2/summary.json` | +65921/-0 | Actual decisions, costs, observation summary or read-only audit |
| `evidence/s6_3/best_control.json` | +2545/-0 | Complete configuration/control and exact independent result refs |
| `evidence/s6_3/decisions.json` | +856/-0 | Actual decisions, costs, observation summary or read-only audit |
| `evidence/s6_3/feasible_witness.json` | +613/-0 | Complete configuration/control and exact independent result refs |
| `evidence/s6_3/independent_audit.json` | +620/-0 | Actual decisions, costs, observation summary or read-only audit |
| `evidence/s6_3/study/archive_manifest.json` | +3083/-0 | Exact payload or artifact/hash inventory |
| `evidence/s6_3/study/calls.json` | +870/-0 | Actual decisions, costs, observation summary or read-only audit |
| `evidence/s6_3/study/configuration.json` | +3351/-0 | Actual decisions, costs, observation summary or read-only audit |
| `evidence/s6_3/study/disposition.json` | +2171/-0 | Actual decisions, costs, observation summary or read-only audit |
| `evidence/s6_3/study/immutable_artifacts.tar.gz` | binary 4142900 bytes | Original immutable Store artifacts; exact member hashes in manifest |
| `evidence/s6_3/study/ledger.json` | +24/-0 | Actual decisions, costs, observation summary or read-only audit |
| `evidence/s6_3/summary.json` | +36819/-0 | Actual decisions, costs, observation summary or read-only audit |
| `evidence/s6_transfer/best_control.json` | +2544/-0 | Complete configuration/control and exact independent result refs |
| `evidence/s6_transfer/decisions.json` | +4/-0 | Actual decisions, costs, observation summary or read-only audit |
| `evidence/s6_transfer/independent_audit.json` | +667/-0 | Actual decisions, costs, observation summary or read-only audit |
| `evidence/s6_transfer/study/archive_manifest.json` | +329/-0 | Exact payload or artifact/hash inventory |
| `evidence/s6_transfer/study/calls.json` | +170/-0 | Actual decisions, costs, observation summary or read-only audit |
| `evidence/s6_transfer/study/configuration.json` | +3008/-0 | Actual decisions, costs, observation summary or read-only audit |
| `evidence/s6_transfer/study/disposition.json` | +127/-0 | Actual decisions, costs, observation summary or read-only audit |
| `evidence/s6_transfer/study/immutable_artifacts.tar.gz` | binary 346097 bytes | Original immutable Store artifacts; exact member hashes in manifest |
| `evidence/s6_transfer/study/ledger.json` | +24/-0 | Actual decisions, costs, observation summary or read-only audit |
| `evidence/s6_transfer/summary.json` | +7740/-0 | Actual decisions, costs, observation summary or read-only audit |
| `evidence/s6_transfer/validation.json` | +10/-0 | Actual decisions, costs, observation summary or read-only audit |
| `evidence/s6_verification/accounting.json` | +470/-0 | Actual decisions, costs, observation summary or read-only audit |
| `evidence/s6_verification/cross_study_audit.json` | +23/-0 | Actual decisions, costs, observation summary or read-only audit |
| `evidence/s6_verification/final_claims_audit.json` | +1991/-0 | Actual decisions, costs, observation summary or read-only audit |
| `evidence/s6_verification/legacy_p1_configuration.json` | +5/-0 | Actual decisions, costs, observation summary or read-only audit |
| `evidence/s6_verification/legacy_plan_cache.json` | +12/-0 | Actual decisions, costs, observation summary or read-only audit |
| `evidence/s6_verification/secret_scan.json` | +9/-0 | Actual decisions, costs, observation summary or read-only audit |
| `evidence/s6_verification/tests.json` | +97/-0 | Actual decisions, costs, observation summary or read-only audit |
| `tests/research/s6_audit.py` | +62/-0 | Offline fixtures or explicit engineering/audit driver |
| `tests/research/s6_transfer.py` | +69/-0 | Offline fixtures or explicit engineering/audit driver |
| `tests/research/test_s6_research.py` | +221/-0 | Offline fixtures or explicit engineering/audit driver |
| `tools/research/agent.py` | +12/-0 | Compact state, native Strands tools and original feedback |
| `tools/research/analysis.py` | +2/-0 | Independent public capability admission |
| `tools/research/budget.py` | +2/-1 | Existing closeout guard requires exact first-pass selection |
| `tools/research/candidate_portfolio.py` | +0/-1 | Infer archive recovery dimensions from task and tendons |
| `tools/research/config.py` | +5/-0 | Freeze versioned opt-in decision semantics |
| `tools/research/contracts.py` | +45/-5 | Typed decisions/settings; preserve legacy serialization |
| `tools/research/control_correction.py` | +20/-13 | Window basis, distinct bounds and optional model margin |
| `tools/research/core.py` | +35/-6 | Public evidence admission, dispatch, recovery and unified claims |
| `tools/research/evidence_policy.py` | +65/-0 | Trusted reference/task/initial/design/model-scope checks |
| `tools/research/local_control_search.py` | +87/-6 | Variable dimensions and bounded existing-Store execution |
| `tools/research/physical_replay.py` | +23/-3 | Explicit candidate-bound control initialization |
| `tools/research/research_context.py` | +102/-0 | Authorized exact history and compact research/budget view |
| `tools/research/state.py` | +5/-0 | Existing evidence readability; no new Store |
| `tools/research_tasks.py` | +16/-0 | Task-owned actual violating-sample diagnostic |
