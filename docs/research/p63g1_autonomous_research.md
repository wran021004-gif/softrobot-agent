# P6.3-G1：自主 Reach/Hold 科研与证据审计

本轮使用唯一新 Study `p63g1-m3-autonomous-sol-20261030`。运行代码冻结于 `e980f2d3cff923fc50d4c131c65d1ac86e300212`，基线为 `d3abff14c6a56e6e9677ef17d7280a60e72807f1`，分支 `codex/p6-3g-autonomous-research`。G0 离线验收已完成，详见 `p63g0_bounded_evidence.md`；本报告只把实际执行和实际交付算作 G1 证据。

## 任务、所有权与 Knowledge

保留原 M3 开发任务：目标世界坐标 `[0.29,-0.035,0.19] m`，时长 0.50 s，保持窗 `[0.45,0.50] s`，终点及保持误差阈值 0.01 m，保持最大平移速度阈值 0.02 m/s；积分步长 0.0005 s，控制/采样周期 0.01 s。任务、FamilySpace、分析协议与控制合同与 F2 配置逐项比较相等。保留原零初态、重力、张力上限、12 cells/segment 最终保真度、原 evaluator 和原验收组装。这里只验证同一 MuJoCo 模型的冻结采样协议，不建立硬件、跨模型或连续时间保证。

Operator 只准备任务、模型空间和执行环境。启动前候选、控制来源、Plan、数学结果、物理结果与 Provider 计数均为 0；未导入 F2 或历史科学结果。Main/Reporter 固定为 `gpt-5.6-sol / none`，同一窗口最多 80 次真实 Provider 请求（含 Reporter、实际失败发送和其中 4 次保护收尾）。数学及相关科学 count 额度为充足合法整数，保留原每次方法技术限制；没有动态扩充 Provider、切换模型/提示或替 Main 提交 Plan。

用户后续明确允许简短历史 trace，包括透露成功路线和已知结果的 M3 trace，因此覆盖附件最初关闭同任务 trace 的要求。Knowledge 已开启，冻结目录 25 条，`procedure` 与 `success_case` 共用原 `experience_retrieve`。首次实际检索就列出 M1、M2、M3 和通用程序经验；历史目录可见不等于已经阅读其完整条目，更不等于当前 Study 的科学证据或验收资格。没有导入历史完整结构、控制轨迹或原 Store。

实际正文读取只有 `research-bounded-continuation@2`（11 次）和 `model-physics-comparison@1`（3 次）；没有读取任何 success_case 正文。7 次检索因自然语言 kind/failure_type 或不匹配 task 等精确过滤得到空结果。Main 的已执行 Plan 将两条程序经验记为 adopted；不把其重复读取算作新科学证据。M3 trace 在目录中可见，未被 Main 正文使用，因此不声称利用了其完整历史路线，也不声称关闭了同任务 Knowledge。

## Main 的假设、行动与结果

| Provider 序号 | Main 自主行动及实际结果 |
|---|---|
| 1–2 | 检索 Knowledge、查询 FamilySpace。将根 JSON Pointer `/` 修正为空根；读取两条程序经验。 |
| 3 | H1 提议三根全长 + 三根仅远端腱、两段六腱、半径 0.012 m。Plan 被接收，但构造返回 `invalid: BASE_ONLY_REQUIRES_FIRST_SEGMENT_ZERO`，未生成候选。不能把工具封套 success 算作科学构造成功。 |
| 4 | Main 改成全部从基座出发：三根跨 0–1 段、三根跨 0–0 段，第二组三腱相位 π/3，半径采用空间默认。成功生成一个合法候选。 |
| 5–12 | 提出完整任务可行性问题，修正两次误放的顶层 `selected_candidate` 参数。第一次科学意图得到缺少完整控制 source 的前置反馈；随后 Main 自主选择 baseline 初始化控制，再重新提交候选绑定 diagnose。尚无科学评价消耗。 |
| 13–14 | Main 选择原 C2 `control_feasibility / full_task / reoptimized_task_capability`，pattern、申请 120 回调，关注保持速度但仍优化全部任务约束。原编译器使用两个端点 knot 和 16 次迭代；实际执行 Native T1。Reporter 只读解释，HTTP 200、available。 |
| 15–18 | Main 查询优化序列 provenance，提出 H3：用原完整独立物理评价检验该确切优化序列，而非从数学改善直接宣称成功；实际 Replay 完整结束，得到有效失败。第二次 Reporter 正常完成。 |
| 19 起 | 原失败确实改变后续决策：Main 转向结构改变后逐结构重优化控制的联合搜索，提出 H4 等假设和四 knot response 参数。但后续请求需逐项区分“提出”与“合法执行”。 |

后续共提交 18 次 search Plan，全部在科学执行前被拒绝；其中 8 次为错误研究意图，另 10 次为 Plan 合同验证失败。期间反复读取知识和错误请求，没有新的结构搜索结果、控制再优化或独立验证。精确的每次输入/反馈引用和本地合同校验列于审计 JSON。

第一份数学结果 `6a6a78aa9503b28fb201fbb1492288df35695ca5aea982da03f22bf86635cc04`：

| 完整任务指标 | 初始序列（Native） | 优化后（Native） | 独立物理 Replay | 原阈值 |
|---|---:|---:|---:|---:|
| 终点位置误差 m | 0.1102153654 | 0.1488208064 | 0.1488208064 | ≤0.01 |
| 保持最大位置误差 m | 0.1240262271 | 0.1593203101 | 0.1593203101 | ≤0.01 |
| 保持最大速度 m/s | 0.4285357151 | 0.3627887282 | 0.3627887282 | ≤0.02 |
| 最坏归一化超额 J | 20.4267857531 | 17.1394364125 | 17.1394364125（由原指标比较） | ≤0 才满足三项 |

J 改善 3.2873493406，但两项位置误差恶化。最坏约束仍为保持速度，搜索以 `iteration_limit` 结束，无收敛或全局最优结论。原始 Native 假设与“重优化后控制”的结果分开保留；独立 Replay 使用的是优化后 source，未偷偷改成初始控制。

## 完整候选与独立验收

本轮只有一个构造成功且完整独立评价过的候选，故以下是唯一已完整评价候选；没有可与其排名的其他完整实验，更没有 passing best。

已独立检验候选引用为 `1e013ec62b7ee8a88070434b581ac51e0c6826f481ebf9cc26c7ea6838453d5a`。其两柔性段长度为 0.16 / 0.11 m，Young 模量 7.2 / 5.4 MPa，第一段椭圆截面、第二段原渐变矩形截面，六腱顺序及默认布线半径 0.018 m。Main 选择了上述基座分组及相位；材料、长度和截面保留冻结空间默认，未自主试验新的材料或长度。

baseline source 为 `7fd5f69204ea8cf06b47840dc1972fbeb444e0a1ab5dc22ed9c48315889a5ba5`，初始六腱均 0.2 N。优化控制由原工具保存为 `556f1040c12ac0ca98f9b6c36d4c11c324c34d426dc1576b84531467216cb831`：两个 knot `[0,0.5] s`、12 个偏置参数，最终第六通道 knot 偏置 +1.6 N，其余 0；实际分段保持序列、末次执行输入和 provenance 保留在 Store，不能以 knot 端点误称执行了不同的序列。

独立结果 `9abe11248877b85531c5c42315ad232445e8b1a973cbbcb632b3719d9ae9b870`，execution `89f062833e974409b1fea638b6889f3a`，引用同一优化 source。原验收状态 `valid_failure`：计算完整、force bounds、solver errors、保持覆盖有效；终点、保持位置、保持速度三项全部失败。保持窗有原要求的六个含端点均匀样本。无任务通过，无正式 SELECT；数学结果和 Reporter 解释没有被计作物理通过。

本轮 Main 没有请求 `acceptance_certificate`，也没有提交 SELECT；不能把 Store 存在完整评价或 Reporter 看过结果记作正式验收读取。G0 对 passing certificate → SELECT 的验证是明确标记的离线 Mock fixture，本轮真实失败结果不提供真实成功 SELECT 证据。

第 73 次 Main 请求首次读取两项完整新结果引用索引，后续真实请求确认交付；第 77、78 次为明确标记的重复索引。第 79 次查询独立结果 root-full 超过单条正文额度，返回明确的受限反馈及原事实。第 80 次实际 wire 的索引进度为 `current_index_confirmed=true`、`pending_confirmation=false`、`complete_body_reads=[]`；Main 引用两项结果、解释各自范围后成功 STOP。这是真实轻量 STOP 的证据，没有把索引或受限正文升级为完整结果阅读。

## 停止边界与接口观察

约 12、30、55 次监督仅作只读状态检查，在已封口的原 request-feedback 边界续跑同一 Study。未插入科学路线、人工修正 Main 参数或重跑历史实验。Main 在第 80 次请求中提交原 STOP，研究状态 stopped。其 Plan 与引用保留于审计。最后 pending、unconsumed response、未封口 calls 均为空；两个实际科学 Worker 均 returncode=0 且 termination_confirmed，无遗留科学执行。

G0 原始大正文保护在真实运行中返回过明确的 `raw_result_not_delivered`，后续请求仍可发送；没有恢复 F2 的整份大数组。方法结果固定事实、两份 Reporter 解释和真实引用进入后续 Main wire。本轮 80 次均 HTTP 200，无失败实际发送；最大保存的真实请求体积 86936 bytes，小于 1,048,576。科学结果后的事实和 Reporter 已出现在真实 wire，不只存在本地生成 packet。

后续搜索准入失败有可核实的接口与决策层细节：search 的当前原 Schema 要求 `MATHEMATICAL_ANALYSIS`，Main 多次提交 `DESIGN_MODIFICATION`；在切换到正确意图后仍使用 `controller_start_input`，原 Native mixed-search 合同要求 `standardized_initial_pretension`，且原合法变量不允许把 `control` 当作结构变量。部分请求还用了当前空间以外的段/腱计数和自然语言 identity/fidelity。它们没有启动结构搜索 Worker，不能把申请的几十次条件评价算作实际研究。

原错误反馈将联合类型验证文本截在 1000 字符，开头是未匹配的旧 Search 分支，而实际 FamilyMixedSearch 的报错位于后面；只读本地 `Plan.model_validate` 可核实该问题，无科学执行。Main 反复查询原 `input_query=/tool_use/input`；该 4 KiB 以上局部值会沿用原导航反馈，仍可细分字段读取，但没有观察到成功恢复。这说明目前的参数准入反馈和模型恢复行为存在明显局限；未做对照，不能把结果全归因于模型、Knowledge、反馈截断或两 knot 之一。

## 成本与未执行方法

| 项目 | 原记录 |
|---|---:|
| Provider Main / Reporter / 总量 | 78 / 2 / 80，授权上限 80 |
| 实际失败 HTTP / 后台重试 | 0 / 0（原 transport/client retries 均为 0） |
| public operations / backend launches | 81 / 1 |
| prompt / completion / total tokens | 1354251 / 31570 / 1385821 |
| usage.reasoning_tokens / 金额 | 0 / 未知 |
| Provider elapsed / ledger.wall_s | 1527.276000000 / 1531.531878500 s |
| 正式数学评价 / 实际数学 Worker | 1 / 1 |
| Native builds / rollouts / callbacks | 1 / 17 / 17；申请 120，16 次迭代终止 |
| Native steps / forward evaluations | 17000 / 1718 |
| Native kernel / Worker charged numerical_s | 1.790182400 / 2.934862700 s |
| 独立 Replay builds / rollouts / steps | 1 / 1 / 1000 |
| 独立 Replay forward / kernel / charged wall | 101 / 0.279126500 s / 1.321015800 s |
| 两类执行已记录总 rollouts / steps | 18 / 18000（attempted steps 相同） |
| 原 numerical_s / construction_numerical_s | 4.874421500 / 0.473336800 s |
| NMPC / RL training、evaluation / T2 / GVS 正式分析 / 结构搜索 | 均未成功发起，实际 0；不把 proposed search 计为 executed |

Kernel 时间包含在相应 Worker 执行时间内，不重复相加；数值状态和构造时间沿用原账本口径。`ledger.worker_calls=0` 是分类方式，不表示没有真实子进程。Provider 没有给出金额，费用保持未知，不以 token 数臆算。数学正式评价尚余 999999，物理 Replay 尚余 999999。科学额度没有耗尽；本轮主要消耗了 Provider 在知识查询、格式/参数错误恢复上的窗口。原每次搜索技术限制仍有效，充足总额度不自动改变 C2 两 knot/16 迭代语义。

## 与九项历史 Trace 的方法差异

以下只复用 C0 已有只读审计和保留的简短 trace，不重跑历史计算、不把历史研究归于 Main。不同任务的数值不能直接排名。

| 历史项 | 已记录方法与范围 | G1 的实际差异 |
|---|---|---|
| C1 | 两/四腱筛查、各工况 Native 控制、2.5 mm 缩短比较、最终四工况原采样验收 | G1 单一完整 Reach/Hold 条件，未完成这种跨结构/工况比较。 |
| M1 | 全窗 response 控制、三条件独立 Replay；分组改变后重新控制 | G1 用 pattern 做一次有限控制优化并独立 Replay；没有成功执行结构改变后的再优化。 |
| M2 | 绑定外载、保持速度微小超额仍判失败、同源带搜索 margin 续算 | G1 误差远离阈值，无临界达标续算；保留原阈值失败，不采用四舍五入。 |
| M3 | 初始结构在 0.50 s 开发任务失败，历史启发分组后重建控制并 Replay；不是正式 Benchmark | G1 从空候选开始，M3 trace 可检索但未读取其正文；当前证据不能继承历史开发见证的通过。 |
| M4 | 完整定时反向 tracking 控制、首次独立 Replay/selection；无结构优势证明 | G1 未执行 tracking 或反向时序任务，只有固定目标 Reach/Hold。 |
| M5 | 联合位置与有向轴搜索，两项原谓词驱动选择；不是完整 6D 姿态 | G1 只有原位置及保持速度目标，未执行轴控制。 |
| M6 | 不完整接触/数值执行、完整但失败的材料试验，再分组和新带载定向控制 | G1 Replay 完整有效但失败，未执行材料或接触对比。 |
| P3 | 静力筛查、路由、动态及消融；1/2 cells 通过、4 cells INVALID，机制未知 | G1 未执行被动静力、离散收敛或消融；不能把主动理想张力结果迁移为被动机制。 |
| PHS-2D | KKT 基线、模态/Jacobian 筛查、有限负载、材料与物理导向比较、十条件开发见证；无正式 SELECT | G1 未使用这些局部/被动数学工具，没有对应机制或多条件证据。 |

这些历史项均为 Operator/固定脚本主导的研究记录，`main_autonomous=false`；M3、P3、PHS-2D 的开发/无正式 SELECT 边界保留，不能统称九项正式 Benchmark 成功。

## 证据保存与结论边界

原 Store 位于本 worktree 的 `runs/research/p63g1-m3-autonomous-sol-20261030/platform.sqlite`。同目录保留冻结配置、原模型/XML、Native 进度与原始数组、独立 Replay 序列、Worker boundary/lifecycle、Provider 原请求与响应、Reporter 和所有失败记录；这些 ignored 原始资料未塞入 Git 文档。公开精简审计 `p63g1_live_audit.json` 给出精确结果/Plan/wire/反馈事件引用、成本与历史方法来源，不包含密钥或模型不透明推理。

本轮真实证明了 Main 可以从空候选池修正构造请求、初始化控制、提出并执行一次数学优化、读取其事实、形成后续独立验证 Plan，并根据有效失败转向新的研究假设。但没有完成后续合法结构搜索，未达到完整任务通过与正式 SELECT 的研究目标。观察到的瓶颈是科学请求形成和错误恢复；控制搜索只完成一个有限配置，结构比较不足，其他路线的适用性和更充分搜索的效果保持未知。没有找到可行解不能证明结构或任务无解，也不能用历史成功 trace 替本轮补足验收。

研究结束后仅提交报告和精简审计；未更改运行时科学代码、重新启动第二个 Study、追加预算或合并其他分支。
