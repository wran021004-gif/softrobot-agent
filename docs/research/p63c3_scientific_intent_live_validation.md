# P6.3-C3 M3 科研意图真实验证

基线 C2 `2581e01a9e17461224bc712f5e4cbe26e04685af`；独立分支
`codex/p6-3c3-scientific-intent-live-validation`。本轮只授权一个小规模 Study。

## 执行前冻结

修复只涉及 scientific_question_v1 的两处旧提示：research_context 的
control_initialization_handoff，以及 agent 按需初始化 Schema 内 ControlSeedRequest.method 的说明。
新说明要求使用新 source、重新提交候选绑定 diagnose，再直接提交 ScientificQuestion；
不要求底层求解器名称，不将初始化称为数学计算。旧 v1/v2 保持原说明及执行行为。
没有修改数学适配器、Worker、任务、预算或 Store 实现。

新增三个节点的实际 Mock wire 测试，并运行旧初始化/diagnose 交接和 C2 原编译执行边界测试：
**3/3 通过，71.126 s**。命令：

```text
python -m unittest tests.research.test_p63c2_scientific_intent.ScientificIntentTests.test_c3_three_handoff_nodes_deliver_question_semantics_without_solver_choice tests.research.test_p63b5_native_entry.NativeEntryTests.test_method_margin_guidance_schema_and_diagnose_initialize_diagnose_wire tests.research.test_p63c2_scientific_intent.ScientificIntentTests.test_mock_wire_diagnose_without_method_loads_question_and_executes_original_request -v
```

Mock 数值不是科学证据；此阶段没有真实 Provider 或科学 Worker。git diff --check 通过。

## M3 原任务与运行配置

原 Trace：memory/cases/m3_research_v1/success_trace.json；原 Store 只读：
`D:/softrobot-agent/.worktrees/base-only-benchmark-feasibility/runs/base-only-owner-20261028-r2/M3/private-store/platform.sqlite`。
原 Study `base-only-m3-20261028-r2`；初始候选
`c5a370c614cf5ef6a2c9e4d5813494f0deac448feb1ae8ccb4210fc01cad06d4` 仅用于读取历史结构来源，
不作为新 Study 的自有候选或科学证据。

使用现有 tasks/reach_hold_b3_050.json，与原冻结 canonical_task、FamilySpace、control 和
analysis_protocol 按值一致。Reach/Hold 时长 0.50 s，最后 0.05 s 保持；位置 0.01 m、速度
0.02 m/s；控制/采样周期 0.01 s，积分步长 0.0005 s；目标 [0.29,-0.035,0.19] m。
原始两段、六腱、每段 12 cells、零命名初态和物理环境保持原样。仍属 development draft，
不升级为正式 Benchmark，不导入历史成功张力或验收。

[当前配置及运行来源](../../configs/research/study_p63c3_m3_scientific_intent_sol.json)：
`p63c3-m3-scientific-intent-sol-20261030`。沿用原 Sol/none Gateway 与 Reporter 策略、
英文架构和按需工具，启用 scientific_question_v1。Provider 总上限 12（含 Reporter/失败/最后
1 次保护），公共操作 32（含 2 次保护），数学 **3**，Native 每次 callbacks≤8、累计≤24；原 iterations≤100、knots≤4。
独立 Replay、NMPC、RL、T2 新实验、NLP/BDF 均为 0。C2 实际数值默认值不改变。

先最多 6 次真实 Provider 请求到 C3-A 监督检查点，只读审查后决定是否在同一冻结额度内继续。
没有预填 ScientificQuestion 或替 Main 选择假设、控制范围、策略或下一实验。

最初准备的数学上限为 1。首次真实请求之前，用户明确选择提高至 3 次，
以保留首个结果后的研究行动空间；在同一 Study 记录授权补充与显式绑定，保留原配置、候选、source、计账和所有事件。
Provider、公共操作和其他科学上限均未增加。原 count 保护仍在全部数学额度用尽后进入收尾；
如它影响 A3，将与模型行动未完成分别记录，强制 STOP 不算自主 STOP。未修改预算或状态路由实现。

实际运行时版本为 `f095b9c6a234f73db8bab8cfcea6f68079f54312`，resolved identity 为
`3865f9de72fd99783055533b55993579c052e33002bd37341fc41e185ace314d`。
期间未修改生产源码或配置。当前配置中的数学上限 12 来自下述第二次用户补充，不能回填为实际窗口的额度。

## 真实准备与监督检查点

完整的非敏感逐请求证据、实际 Schema、原始 Main 请求、完整编译请求、Worker 准入与费用见
[只读审计](p63c3_live_audit.json)。原始 Provider 请求/响应、科学数组、控制轨迹、回执和报告仍保留在上述新 Study Store，
没有将凭据、opaque reasoning 或 Knowledge 正文复制到报告。

Operator 通过原 generate_candidate 与 initialize_control baseline/seed_control 重建初始结构，
decision_owner 明确为 `operator`，没有替 Main 提交 Plan。新候选：
`fc7509609aa206a0ba8d5e3b0ca10de518b922f27fda4c59aa6ccf25ada5d3de`；
新控制源：`d69f942eda05f4063906ba71f513e3c12c4b885bc9d36bda90a3f8541d63ac6a`。
完整 51 个时间点、50 个控制区间，每通道初始 0.2 N，六个独立通道各限 0–8 N。
canonical task、任务、协议、FamilySpace、机器人结构、seed、backend、dynamics_model、mesh、controller
共十项按值与原 M3 一致。初始化不积分、不评价任务，task_acceptance=unmeasured。

首次准备中的未认证 health GET 返回 401；随后使用原 credential 入口访问健康检查，得到
ok/connected/plan_usage=true。没有推理请求、登录、换账户或改 Gateway。原环境检查通过。
原 require_authorization、implementation bind、候选和控制 binding 均实际执行；未绕过准入。
运行授权引用 `7046a993870ccf13eb5be7fcac138472beee61d7fce90fae569aee53944ea2cb`，
原 request-feedback 交接准入引用 `779f8c55ca922a46bbb2852d24f50de5fdf193ea567c38389a98562d0e026495`。
该准入依据本次明确的监督授权、原 B6 交接机制和三项直接离线测试，未伪称新 Study 在首次发送前已有真实连续请求。

C3-A 原 CLI 最多新增 6 次 Provider 请求后暂停：5 次 Main、1 次 Reporter，数学 1/3，pending/occupied 为空。
第 4 次的科学语义错误得到准确 unsupported 反馈，没有计算或自动替换问题；第 5 次由 Main 自行修正并获得真实结果。
不存在错误 Schema、来源绑定或执行阻断，因此在同一 Store、同一冻结预算内继续 C3-B，最多再新增 6 次。
没有新增用户消息、补填科研参数或更换 Main 提示以强迫结果后行动。

## 逐轮真实行为

全部 12 次 HTTP 200，冻结 Provider 为 gpt-5.6-sol/none；无推理 smoke、重试或模型/Thinking 切换。
下表只列相关可见入口；完整工具名、Schema、原始参数、反馈引用与当轮预算保存在审计中。

| 请求 | 可见入口 / 角色 | Main 实际行动 | 工具结果 → 下一步 |
|---|---|---|---|
| 1 | Main：diagnose Plan、读取等 | 读取当前控制来源链接 | 正确获得新 Study 的完整 source → 读程序 |
| 2 | Main：同上 | 读取 research-bounded-continuation@2 | 取得程序说明 → 自主 Plan |
| 3 | Main：候选绑定 diagnose | 提出 H1：初始完整控制能否满足三个 Reach/Hold 指标 | 合法只读 diagnose 完成 → 直接加载 ScientificQuestion |
| 4 | Main：轻量 ScientificQuestion | control_feasibility + closed_loop_performance，full_task、response、8 callbacks | unsupported；scientific_execution_started=false → Main 自行修正 |
| 5 | Main：同一轻量 Schema | 明确改为 reoptimized_task_capability，沿用自行选择的 source/范围/策略/预算 | 确定性编译、原准入通过，真实 Native computed → Reporter |
| 6 | Reporter：原 source-linked 解释 | 非 Main 行动 | 解释真实结果 → C3-A 监督暂停 |
| 7 | Main：ScientificQuestion 与候选 Plan 仍可用 | 读 /all_fresh_results | 返回唯一正确结果引用 → 重读 |
| 8 | Main：同上 | 重读同一索引 | 同一引用 → 重读 |
| 9 | Main：同上 | 重读同一索引 | 同一引用 → 重读 |
| 10 | Main：同上 | 重读同一索引 | 同一引用 → 重读 |
| 11 | Main：同上 | 重读同一索引 | 同一引用 → 进入最后一次 Provider 保护 |
| 12 | Main：保护收尾 | 再次读同一索引 | 同一引用；未提交 STOP → 原监督边界停止 |

第 3 次 Main 自愿填写了可选旧标签 `selected_method=trajectory_feasibility`，未填写 T1/Native 求解器名称。
实际发送的 diagnose Schema 不要求 selected_method；该标签不分派计算。第 4/5 次的真实 Schema
是 ScientificQuestion，没有向 Main 暴露复杂 AnalysisRequest；实际方法由第 5 次的科学语义确定。
H1 原意是评价初始序列；后续 Main 明确选择了控制重优化，编译器没有把第一条闭环问题偷换成它。
初始及 best-found 指标都被保存，因此可以分开评价初始序列和有限搜索结果。

编译请求绑定原候选、原控制源、MuJoCo、standardized_initial_pretension、完整 0–0.50 s 协议；
原 T1，response，knots=[0,0.5]，window=[0,0.5]，callback cap=8。
其余数值设置继承 C2 原默认值，原 Study 的 iterations≤100、knots≤4 限制不变。
原 Pydantic/精确 Schema、source、时间、物理输入、适用性及费用准入都通过；Worker returncode=0、
worker_started=true、termination_confirmed=true。没有改写请求或绕过 Worker。

## 实际数值及其限制

真实结果：`cc2669b0044aadfb4921c018d14d317ed1b9dd75a4cbab3e85b08db50c643c73`。
精确值及原指针见审计；下表缩写显示。

| 指标 | 初始序列 | best-found | 冻结阈值 |
|---|---:|---:|---:|
| signed maximum excess J | 20.451755 | 20.353797 | 非接受证书 |
| terminal position error / m | 0.111427 | 0.111564 | 0.01 |
| holding max position error / m | 0.125317 | 0.125394 | 0.01 |
| holding max speed / m/s | 0.429035 | 0.427076 | 0.02 |

J 改善 0.09795830435461994，主要来自最坏保持速度指标的有限改善，两个位置指标略变差。
三个模型指标仍超限。stop_reason=evaluation_request_budget；convergence=unresolved，
global_optimality=not_established。全通道两端点控制的维度为 12，8 个回调没有完成一个响应更新；
best 标签是 finite_difference，不能称为收敛最优控制。
低维参数化和有限预算都限制结论，失败不证明该结构不存在可行完整张力序列。
本次没有选择 time_window，不能把局部三角脉冲修正标成已真实验证；它仍只有 C2 离线等价测试。
模型 sampled proxy 不是独立 Replay；独立任务接受仍为 unmeasured，未执行 SELECT。

## 结果交付与 A1/A2/A3

第 7–11 次原请求中，ScientificQuestion 仍已加载，数学剩余 2，closeout.active=false；
L0 实际包含上述三项超限值/阈值、J、停止原因、未收敛/未证全局最优和独立接受未知。
读取索引每次都成功返回真实结果引用，没有空索引、错误 Schema、来源绑定失败或提前保护。
Main 没有进一步直接读取结果字段，也没有任何可见结果解释或假设判断文字。
Reporter 第 6 次的解释不是 Main 的判断。

| 验收 | 判定 | 依据 |
|---|---|---|
| A1 科研问题提出 | 通过 | 自主提出有任务阈值、固定条件和削弱条件的 H1；自行提交并纠正具体控制研究语义 |
| A2 科研意图执行 | 通过 | C2 原链路忠实编译，原准入通过，真实 Worker computed，成本完整记录 |
| A3 结果后自主决策 | 未通过 | 六次重复索引读取，无新科研 Plan、假设更新或 STOP；前五次仍具备科学行动空间 |

“收到结果”“理解超限约束”“判断 H1 支持/削弱/未决”与“自主行动”不能等同。
本次有正确交付证据，没有 Main 完成后三项的可见证据。最终停止是 supervisor_pause，
不是 Main 自主 STOP，更不是任务成功。观察支持“本次 Sol/none 在结果后未完成研究行动”，
不构成普遍模型无能力或单一原因的严格因果证明；也不把有限数学搜索失败归咎于 Main 判断失败。

## 计账、再次放宽数学额度及停止

| 项目 | 实际记录 |
|---|---:|
| Provider（Main / Reporter） | 12（11 / 1）/ 12 |
| 公共操作 | 11 / 32 |
| prompt / completion / total tokens | 130118 / 2041 / 132159 |
| usage.reasoning_tokens / 金额 | 0 / 未知 |
| Provider elapsed 合计 / 原 ledger.wall_s | 136.439 / 138.2144446 s |
| 正式数学评价 / 真实数学 Worker | 1 / 1 |
| Native model_builds / rollouts / callbacks | 1 / 8 / 8 |
| physics_steps / attempts | 8000 / 8000 |
| forward / mechanics evaluations | 809 / 0 |
| completed_response_steps | 0 |
| kernel_wall_s / charged Worker numerical_s | 0.7648436 / 1.7754446 s |
| 原 numerical_s / construction_numerical_s | 2.3480839 / 0.4332423 s |
| 独立 Replay / NMPC / PPO / T2 新实验 | 全 0 |

Kernel 包含在 Worker 数值时间内，不能相加重复收费。原 ledger.worker_calls=0 是分类，
不表示数学 Worker 为零；其生命周期和回执证明实际启动 1 次。独立物理额度为零也不意味着 8000 个积分步免费。

用户随后要求数学额度充足、以 Provider 限制总量。已在同一 Store 的安全监督边界登记数学
**3→12**，每次 Native callbacks≤8、总潜在上限≤96；Provider 仍为 12，其他上限不变。
补充引用 `ca3f74a400e34d06cb8b44282412aa928fc0b59ad404740883daa7711ed97a3b`。
该补充生效时既有 12 次请求已经结束，没有再发请求，也没有运行时让 Main 看到上限 12。
不能声称完成了“12 次数学额度下的新实验”；实际窗口本来只用了 1/3，因此停滞没有触及原数学上限。
全部旧状态、两次授权补充、候选、source、科学结果与费用均保留，没有重置或借用预算。

最终 Provider 余 0，公共操作余 21，授权数学余 11；pending、occupied、unconsumed_response、
未封口 calls 均为空。原 Study 状态 ready，两个原 CLI exit=0；没有模型 STOP、SELECT、第二次 Study 或 C4。
运行后提交只读审计和文档，不再发真实请求。

下一轮最小必要工作是预先冻结同任务、同工具、充足数学额度与有限 Provider 的推理配置对照，
检验结果后假设更新及实际行动；需要另行授权。本轮不增加引导词、不扩建 Harness、不自动换模型或继续实验。
