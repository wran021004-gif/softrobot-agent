# C3-P0：数学搜索与对照实验准备（不执行正式实验）

2026-10-25，Asia/Shanghai。基线 `e28fda1eda0da3f695ac7ef1862b2ed2df258e58`，
远端 `research/c3-autonomous-softarm-study` 核验一致；独立分支
`feat/c3-math-search-readiness`，独立 worktree；其他工作树和封存证据未修改。

## 1. 请求上下文

只读 `evidence/c3_blank_autonomous_softarm/immutable_artifacts.tar.gz`，
脚本 `python -m tests.research.c3_readiness_audit`。数字是完整 httpx JSON 请求的 UTF-8 字节，
token 是仓库固定 DeepSeek tokenizer 对序列化 JSON 的离线估算，不是 Provider 实报。

| 主请求边界 | 原始字节 / tokens | 保留旧历史、替换 L0 | 原验证 Handoff 后完整请求投影 |
|---|---:|---:|---:|
| 1 | 84,965 / 22,565 | 84,965 / 22,565 | 85,175 / 22,608 |
| 13 | 332,894 / 95,218 | 309,577 / 88,852 | 109,400 / 30,284 |
| 25 | 639,373 / 188,692 | 597,672 / 176,378 | 88,944 / 26,996 |

末轮 Handoff 投影减少 86.1% 字节；未轮换会话仅减少 6.5%。第一个边界无历史可去掉，
短会话说明反而增加 210 字节，不应为了数字好看宣称所有边界均改善。
早/中/末 Schema 分别 51,622 / 51,622 / 15,730 字节；系统指令均 4,735；
Assistant 历史 0 / 170,100 / 452,431；工具反馈 0 / 30,263 / 56,293；
当前 packet 26,096 / 70,420 / 101,645。分项各自带 JSON 框架，不能直接加总。

实际重复：末轮数学 baseline signed excess `61.52347153119494` 出现 4 次，
瘦身后一次；物理保持误差 `0.19304308687570046` 从 5 次到 3 次
（物理指标、临界样本、带源 Reporter 假设内仍可能重复）。数学 quantities 与 comparison
重复相同分数，L0 又重复旧数学结果；方法目录大量重复 coverage 和说明。
现在保留状态/成本/缺失前提及精确详情查询、当前核心问题、最近动作、少量结果，
原矩阵、控制、推理、Reporter 全文、候选与完整 STOP 索引继续在原 Store。
完整任务和 controller schema 本阶段保留，未改科学语义。

原 C3 pilot 没有 Handoff 准入标志。新增 `--handoff-request-bytes`，例如待批准运行时
配合 `--session-handoff --handoff-request-bytes 160000`，仅在原已验证的
request-feedback 边界轮换；完成 invocation 的原轮换机制不变。
必须先获得原 `session_handoff_live_admitted` 与 `session_handoff_boundary=request_feedback`
准入，不能绕过；未知请求/worker、未配对工具、未交付 Reporter 仍阻止轮换。
离线投影不是已恢复封存 Study 或已开展 live continuation 的声明。

STOP/SELECT、预算、推断限制和原始证据引用保留；Reporter 解释在决策投影中显式标为 hypothesis。
旧 SDK 历史、原请求/响应和报告均不修改。原 C1 投影 API 默认保持历史行为。

验证：8 项 request-boundary/provider-context 定向测试通过（mock HTTP，无外发）；
首次因本 worktree 的 Windows MAX_PATH 失败，缩短测试专用 ID 后通过。
C1 历史上下文测试另有既存环境相关失败（80,255 ≥ 78,644），已用原 HEAD 代码在内存中
复现同一结果；没有改写历史验收来隐藏它。其余 C1 3 项通过。

## 2. 搜索发现、计费与效率

空池也提供 `structure_actions`：generate 使用 **generation** payload；search 使用
`family_mixed_search_v1` 与 `variable_groups`；已有候选分析使用 research_analysis。
列出必填字段、冻结 grant、fidelity、三种 objective 的不同含义及禁混旧字段。
family 模式只广告当前 generation 和 mixed search Schema；原 source-relative Plan/执行解析保留。
不替 Agent 选择 objective、拓扑或参数块。

只读几何轨迹脚本使用真实 `family_space_v2`、原 mixed_moves 和 generator，固定 incumbent，
没有优化评分、CONIC 求解或科学 worker：

| 子空间（工程示例） | 依次访问的前几个坐标 | 12 数学额度覆盖 |
|---|---|---|
| 全部块，1–3 段/3–4 腱 | initial、段数、腱数、length.0、young.0、section.0.semi_y | 6 合法新结构，6 模型准备 + 6 CONIC |
| lengths + materials，固定 3 段/3 腱 | initial、length.0、young.0、length.1、young.1、length.2 | 6 新结构；young.2 尚未访问 |
| routing + sections，固定 3 段/3 腱 | initial、phase、semi_y.0、guide_s、semi_z.0、anchor_s（重复）、width_y.1 | 7 提案，6 新结构 |

完整组的 spans 只有 whole_chain 一个策略，因此没有活动 span 坐标；路由未轮到。
以上不是任务重要性排序，也不保证实际评分更新 incumbent 后访问顺序不变。
未出现非法结构或仅改表示的有效评价；确认 anchor_s 已在上界，正移动裁剪无变化。
有限自选 bounds 的长度也复现此问题。新增最小去重：构建前发现重复 request 时记录
`skipped_moves`，消耗 proposal、不构建、不新增数学评价；原 receipt 复用和失败费用保持。
不新增算法或重要性启发式，继续按 Agent 给定 variable_groups 顺序轮换。

计费明确区分 proposed_designs、legally_constructed、actual_mathematical_evaluations；
CONIC 内部 branch 由原 conic_subproblems 计算，物理启动独立。rank 仍只把 computed 的
有限数学分数列为有效，失败为 unknown/unsupported，正负和最大/最小方向不变；任务接受仍 unmeasured。

5 项核心搜索回归通过：合法公开 Schema、旧/新字段拒绝、裁剪去重计费、真实生成候选与 lineage、
已封存分析的中断恢复复用、失败和非法候选费用。13 项旧 mixed suite 中另有 3 项既存快照/环境断言
不适用于当前基线（旧 configuration digest、六段失败源身份、未设置线程变量的 execution 门禁），
不修改科学身份/环境门禁去迎合旧断言。

加入搜索 Schema/发现后重新计算完整请求：早/中/末的保留旧历史请求为
76,681 / 301,293 / 599,722 字节，短会话投影 76,891 / 101,116 / 90,994；
相应短会话离线 tokens 20,459 / 28,135 / 27,606。末轮字节减少 85.8%。

## 3. 指定 span 半径的受控敏感性

入口仍为 `research_analysis(operation="task_capability", capability_method="sampled-affine-conic-minimax-v1",
optimal_sensitivity={variable:"spans.0.radius_m", steps:[h], model_results:[base,minus,plus]})`，
另需 candidate、相同 frozen protocol、合法的相同 operating_point。Study 必须显式在
`family_sensitivity_variables.variables` 授权该路径，并授权 CONIC/T2 两方法。
先用原 generate 准备固定拓扑的合法候选，再用原 linearization 准备三个已登记模型；
调用者不得把工程夹具引用用于正式 Study。

FamilySpace 发现现在列出实际 span 索引、SI 范围、有效/继承值及受影响腱索引。
参数路径只扩展列表索引；无 JSONPath 或新优化器。完全 route_override 的 span 返回
PARAMETER_HAS_NO_EFFECT_ON_GENERATED_ROUTING；缺索引、未授权、超域、生成器间隙不合法、
额外结构/拓扑/任务/控制/输入次序/模型/时间变化均由原准入拒绝。
原 segments.length_m/young_pa 和 source-relative 行为保留。

真实生成器夹具：1 或 2 段、一个含 3 腱的 span，半径 0.0175/0.018/0.0185 m。
三根腱的实际路由半径逐一吻合，robot 结构身份和真实 GVS 输入矩阵 B 均不同；不是未生效 JSON。
三个小 GVS 模型直调内核（无 worker、积分或物理验收），经原 saved-model admission、T2、
ResultCard、Reporter L1、L0 投影完成链路。发现并修复真实工程阻碍：初始工作点的
actual_time_s 原为 null，现对具名初态明确为 0；目标/半程静态工作点不擅自赋时刻。

真实夹具执行 3 次 CONIC，出现 optimality-insufficient 警告，结果为未决方向，未提供梯度，
不为此调整 solver/物理或进行扫描。另用原解析小夹具验证 spans 列表路径、固定控制与重优化、
FD/对偶面、score/m 单位和跨拓扑拒绝；不把其数值当机器人科研证据。
原严格 regularity 条件不放宽，有限差分仍非严格包络梯度。模型/采样时域外、独立物理成功、
全局最优、硬件或跨任务性能仍未验证。

24 项原 family/T2 核心测试及新增 3 项（含真实小模型链路）已执行；调试先遇到缺依赖、
真实起始时刻缺口及测试投影字段错误，修复后定向复验；完整通过数在最终验证部分记录。

## 4. 数值诊断、工程准入和待授权实验

MuJoCo native forward/step、固定回放和普通 backend 积分现在复用一个调用前 integration-state
内存缓冲区，仅在可捕获异常时序列化；不逐步写磁盘。快照含物理身份、MuJoCo 版本、state spec、
时间/qpos/qvel、实际送入的 ctrl、最近已计算 actuator force、约束/接触数、warning、
solver/integrator/timestep 设置和错误位置。控制与完整模型仍由原 request、候选和 XML 获取。
原 execution_worker 在失败结果/原输出目录保存快照，保留 execution_incomplete、已确认步数下界；
失败调用内部进度未知，不合成完整轨迹、最终积分步或优化更新。

一次原输入隔离复现：原结果 `663a2387…`，原 source `74d2e452…`，binding 核对通过；
上限 700 步/0.35 s 模拟、30 s 墙钟，实际 kernel 0.438604 s。
相同 FatalError 在 `playback.step` 再现；调用前 t=0.21350000000000016 s，确认完成 427 步，
`ncon=0, nefc=0`；下一次失败调用内部步数未知。快照和原模型/采样保存在忽略目录
`runs/c3_failure_reproduction/`，未注册正式科学结果、未改旧 Store/ledger/失败。
新诊断显示失败前无接触/约束，但不能排除失败调用中生成约束；不能据此唯一定位引擎、
模型参数、接触或调用方式。已确认是 MuJoCo 内部数值分解报错，而非外层 SLSQP 目标 Hessian，
更不能据此证明结构不可行。未改任何物理、solver、积分器或步长，也未做第二次复现/扫描。
进程硬崩溃而未进入 Python catch 时，内存快照仍可能无法保存；不能宣称该边界已解决。

### 环境与预算

原 `.s135-env` 是单独解释器，继承 `.f3-prestudy-env`/`.rl-pilot-env` 库路径；
它不等于冻结 `.mainline5-env` 的解释器路径。原数学 worker 使用 sys.executable，
NMPC 使用配置 research_python 且要求 exact interpreter，这解释了 C3 先前的 Host 门禁问题。
`.mainline5-env` 本机缺 cvxpy/clarabel；原 `.s135-env` 实际已经具备 cvxpy 1.9.3、clarabel 0.11.1。
两份新配置显式使用同一个 `.s135-env` 作为 Host/数学/NMPC 入口，旧配置和共享环境不修改。
原 RL worker 路径保持 `.rl-pilot-env`。

只读 `python -m tools.research environment --spec <AB-config>` 返回 ready：
NumPy 2.4.6、SciPy 1.17.1、CasADi 3.7.2、MuJoCo 3.13.0、Pydantic 2.14.0、
Strands 1.59.0/harness 0.2.0、线程变量全为 1、exact interpreter 与 CONIC solver 可用。
新 AB 主入口在读取凭据/发送 Provider 前检查该准入；没有改变原数学 worker 的解释器选择。
初查曾试建忽略目录测试 overlay，按原 S130-T3 依赖声明解析失败，未安装/升级共享包；
随后发现并优先复用了现有完整环境。测试 overlay 未作为新 Study 运行环境，未提交。
工程准入是 import/协议检查，不是完整 NMPC/PPO 或所有候选运行时成功的保证。

decision_budget 增加 Reporter 已用/待用上界、实际仍可携带探索工具的主请求数、
Reporter 后容量和提前监督提示；原预算/保护字段保留。新的
`--pause-exploration-remaining 4` 在原独立准入的 paired-feedback 边界暂停，
不发送下一请求，不伪造 invocation 完成或改会话。有限追加仍须原授权和 ledger，STOP 后不重开。
成功/保护状态下新科学请求容量为 0；数学/物理剩余额度不代表仍允许探索。

### A/B 与决策对照

完整共同协议见 [`c3_ab_protocol.md`](c3_ab_protocol.md)，配置：
`configs/research/study_c3_heuristic_ab.json`、`study_c3_math_search_ab.json`、`runtime_c3_ab.json`。
两组共同：Provider 64（收尾 8）、public 160（收尾 16）、数学总 24（单搜索子上限 12）、
物理 8、NMPC 1、PPO 1 stage/4096 actions/1 独立评价、固定回放≤5；均为待授权上限。
新 scope 只冻结公共 1–3 段/3–4 腱子域，原 FamilySpace 文件不变；generate/search 都受限。
数学组首个受支持结构必须经 task_violation mixed search，失败后不能绕过为直接 generate。
启发式组保留自主选择。原独立验收、全部控制机会和成本保存均一致。

数学证据对照使用同一协议中的独立小对照和
`tests/research/fixtures/c3_math_decision_template.json`，复用原 agent_math_decision_probe。
新增 c3-template 只读预览、review 只读字段/usage 审查；freeze 可接收新 cases/out，
自定义输入不继承旧授权，draft/pending 均拒绝 live。计划一案例/两组/两轮，总 Provider≤4；
所有候选、原状态、证据、独立后续反馈、六项 rubric 在未来执行前绑定。
本轮模板不含科学答案、实际候选、成功控制、目标方向或预填评分。
只读 compare-exports 复用原导出和验收，验证其自身比较返回同一共同条件、25 主请求/6 Reporter；
没有重算 C3 或引入第二套任务评价器。

## 最终验证、规模与限制

最终集中定向检查 **52/52** 通过，55.782 s：family/T2 参数/数值 27、
C3 准入/快照/上下文 4、probe 4、handoff 5、Provider capacity 4、native admission 2、
预算边界 1、搜索核心回归 5。最后两项小补充（保护时科学容量为零、记录 MuJoCo 版本）
相关 3 项复验通过，0.454 s；每阶段 `git diff --check` 通过。
测试 Probe 输出的八条 passed 是显式 mock transport 夹具，真实外发为 0。
此前调试失败与旧基线断言不匹配保留在前文，未改冻结指标、身份、费用或历史结果迎合测试。

全部最终投影（包含缩窄 Schema、新搜索发现和预算字段）：

| 边界 | 原始 bytes/tokens | 保留旧 SDK 历史 bytes/tokens | 短会话投影 bytes/tokens |
|---|---:|---:|---:|
| 1 | 84,965 / 22,565 | 77,027 / 20,507 | 77,237 / 20,550 |
| 13 | 332,894 / 95,218 | 301,639 / 86,794 | 101,462 / 28,226 |
| 25 | 639,373 / 188,692 | 600,066 / 177,079 | 91,338 / 27,697 |

末轮减少 **85.7% 字节、85.3% 离线 tokens**；有旧历史仍只降 6.1%，不能把投影当已做 live continuation。
完整原始证据可定位，STOP/SELECT、原预算值和限制保留。重复数学 scalar 4→1，物理 scalar 5→3。

生产 Python：17 个既有文件，267 增/43 删，净 **+224 行**，无新生产模块。
新增仅为两个测试/只读审计文件、配置/模板和两份文档；未提交环境、密钥、日志、原始请求或额外归档。
四阶段提交由本分支日志和最终交付列出；未合并主线、未强推、未改其他 worktree。

资源：真实 Provider/DeepSeek 请求 0、正式科学 worker 0、NMPC 0、PPO 0；
一次工程回放 427 个确认完成步及一次失败调用，原任务账本变动 0。
小 GVS 三模型/解析 CONIC 夹具在测试调试中有重复调用，其时间属于工程测试，
未伪装为正式数学证据或计作免费科研；最终真实夹具 3 模型/3 CONIC，最优性仍不足、未决方向。
单元夹具的总内部 solver 次数未建立新账本，不能把上列 suite wall 当纯 CPU 或与工程 kernel 简单相加。

工程实现和待授权协议已备齐。正式对照仍需用户批准每组有限成本/外发范围，冻结最终源码与环境，
通过原 live Handoff 准入；决策小对照还须绑定真实相同 candidate/state、验证数学诊断及冻结后续反馈。
不能声称目前已有科学优势、可靠结构方向或完整 NMPC/PPO 验证。
本轮到此停止，不启动下一场 Study。
