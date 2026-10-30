# B6 网关响应修复与独立重测

基线 `172ad585a3037251c80ce5296720abcee0184ce2`，分支
`codex/p6-3b6-gateway-repair-retest`。用户后续明确要求「修复网关响应，然后重新测试」。
旧 B6 的 HTTP 502 请求与已扣 1 次 Provider 原样保留；本轮另建独立 Study，不重发或重置旧请求。

## 可复现的响应丢失路径

确认实际监听 127.0.0.1:8787 的旧进程 PID=640676，来源为
`.worktrees/research-harness-v2/local-chatgpt-gateway`，不是仓库根目录的旧副本。
该推理转换只处理 terminal `response.completed.output`，忽略此前 `response.output_item.done`。
当 completed 事件缺少 output 或为空，而前面已有完整 item 时，本地丢失文本/工具调用并误报
empty_response。这条路径已用原 HTTP→Responses→工具反馈测试复现。

历史 B6 只保留了本地 502 错误，没有保存上游 SSE；因此不能证明该缺陷是那次失败的唯一原因。
真正的模型空输出仍可能发生，不能通过伪造回答或把半截调用当成功来掩盖。

修复仅在 inference.mjs 累积原始 completed item，按 output_index 排序；只有全局响应 completed
且 terminal output 为空时采用它们。非空 terminal output 仍优先。原始 call ID、参数、opaque
reasoning 和 usage 保留，不猜测缺失 token；全局 incomplete/failed/中断及未完成 item 仍拒绝。
server.mjs 允许合法的仅工具响应，保留真正 empty_response，并附带无敏感内容的输出来源/计数。
自动重试仍为 0，未修改 OAuth、DPAPI、账户/权限、代理路由、额度或 Agent 科研代码。

参考 [官方 Responses 事件定义](https://developers.openai.com/api/reference/resources/responses/streaming-events)
和 [官方 Sign in with ChatGPT 集成说明](https://developers.openai.com/cookbook/articles/sign-in-with-chatgpt)。
事件完整性依赖实际终止状态；离线测试不代表账户或模型行为已经真实验证。

## 离线验证与运行切换

`node --test --test-isolation=none test/inference.test.mjs test/server.test.mjs`：**25/25 通过**。
使用已有依赖；node_modules 和 .devkit 只在忽略目录中关联到旧运行安装，未修改其中的认证源码、
依赖或受保护状态。测试覆盖漏 terminal output、仅工具调用、call ID 与 reasoning 精确保留、
后续工具结果、terminal output 优先、真正空输出及各类失败；所有上游推理均为 Mock。
同进程测试避免当前 sandbox 的 Node 子进程 spawn EPERM，不需要网络或真实模型。

旧网关 health=ok、connected、plan_usage=true。只替换该端口已识别的网关进程，沿用相同受保护
账户状态与本地代理；不登录、重授权或切换账户。修复版从本分支启动并保留运行来源记录。

## 新 M 范围

[冻结配置](../../configs/research/study_p63b6_gateway_retest_sol.json)：
`p63b6-m-native-sol-gateway-20261030`。沿用 B6 冻结任务、FamilySpace、零初始态、数值协议和
九项 success_case 权限，原生成器与 seed_control baseline 提供 Operator 未评价结构/控制。
不导入旧控制结果、数学结果、科研判断或预算；Main 仍自主选择 Native 方法与科学参数。

Sol/none；Provider≤12（含 Reporter、失败与最后 1 次保护收尾），公共操作≤32（含 2 次保护），
共享数学≤4，Native callbacks≤24、iterations≤3、knots≤4；独立物理/NMPC/RL/NLP/BDF 全 0。
原环境、代码绑定、formal_study_authorization 和 live_handoff_admission 通过后只运行一次原入口，
不加 smoke 推理、不代交科学请求。Native 工作完整计账，任何数值都是仿真参考，不是实物真值。

以下为运行结束后的原事件审查；真实窗口内没有修改代码或冻结配置。

## 网关真实恢复证据

[准确运行来源、逐请求原输入/反馈、科学结果与费用](p63b6_gateway_retest_audit.json)。
修复网关实际 PID=40556，源码来自本 worktree，原代理与 protected account 状态保持不变；
新进程 health=ok、connected、plan_usage=true。已有 gateway 服务保留运行，未再登录或切换账户。

代码/Study freeze=`76a3e1db1f50797031149e55248299227d958e59`，resolved identity 为
`42ca38c68d24992119476e272065166cc3255c0816e56bb0db4398249749b430`。
正式授权引用 `e6c7a04c53a62018b0c1bd12ccaad03f9a1daf2ecf228c58fef7e71ad4b52638`，
Handoff 准入引用 `68e3d0631edebed4cd221bb5e816640bb5a83286f81aeb1df091bb88c474e726`。
原 require_authorization 在缺失正式记录时拒绝，原 bind、环境与兼容性检查通过后才启动。

**12 次正式 Provider 请求全部 HTTP 200**，没有重试、模型切换或 smoke 推理。每次真实响应的
gateway_completion 均为 output_source=completed_item_events、terminal_output_items=0。
第 1 次实际返回 4 个完整 item，Main 的四个读取动作均精确收到；第 7 次数学工具调用同样从
完整 item 恢复，原始 call ID/arguments 进入原绑定。第 8 次 Reporter 的文本也正确交付。
旧转换器只读 terminal output，面对这 12 次实际流量会丢掉已完成内容。这是修复在真实请求中
生效的直接证据；它不补造历史 B6 未保存的 SSE，也不宣称排除了历史那次失败的所有其他原因。

原 B6 失败 Store 的完整 state identity 前后相同，仍为原 1 次失败请求；新 Study 从 0 开始计账。
运行前后修复网关源码 SHA-256 一致。完整 Store、原请求和返回体保留本地，审查仅输出非敏感
科学字段、引用与计数，不提交 opaque reasoning、凭据或 Knowledge 正文。

## Main 实际行动

| 次数 | 角色与实际行为 | tokens | 秒 |
| --- | --- | ---: | ---: |
| 1 | Main 读参数、来源、Operator control 链接和 research_opportunities | 7867 | 16.516 |
| 2 | Main 搜索 success_case 元数据，匹配 0，未读正文 | 9754 | 9.344 |
| 3 | Main 直接提交 diagnose；research_intent=MATHEMATICAL_ANALYSIS 被 TOOL_SCHEMA_CONST 拒绝，Worker 未启动 | 9285 | 18.703 |
| 4 | Main 再读 opportunities | 8962 | 8.781 |
| 5 | Main 再读参数、来源、control 链接及 T1 opportunity 子项 | 9659 | 18.078 |
| 6 | Main 自行改为 DIAGNOSE，正式候选绑定 Plan 完成：M1 | 10083 | 17.704 |
| 7 | Main 提交合法 research_analysis；实际 Native Worker computed：M2 | 11865 | 15.141 |
| 8 | 原 Reporter 解释实际结果，共享 Provider 额度；不算 Main 决策 | 7741 | 16.344 |
| 9 | Main 读 best J/metrics/stop_reason/search_quality；fresh-result index 用 full，被 EVIDENCE_VIEW_MISMATCH 拒绝 | 17288 | 10.953 |
| 10 | Main 自行改 working_set，成功读 fresh-result index | 17378 | 10.953 |
| 11 | Main 读初始/数学输出 control 链接、再次读相同结果指标和 index | 17254 | 14.328 |
| 12 | 保护收尾中再次读取同一 index，未提交 STOP | 14451 | 7.734 |

前 6 次 direct_plan 为 diagnose；没有为加载 diagnose 或 analysis 调用 research_route。
第 6 次正式 Plan 后，第 7 次原探索窗口实际 Schema 加载 research_analysis，选择方法/候选、
已绑定字段和剩余科学输入均在原 L0，未被保护期提前隐藏。第 12 次才按原规则切到 stop 保护。

第 3 次文字意图仍提出末尾 0.20 s 修正及 scalar correction_window_s；它首先因 research_intent
const 被拒，未进入数学 Contract。第 6 次重新提交和第 7 次真实科学请求均由 Main 自行选择，
Operator 没有修参数或补交。实际请求为 response、v2、window=[0,0.6] s、knots=[0,0.2,0.4,0.6] s、
margin=0、difference_step=0.01 N、initial/minimum_radius=0.1/0.0001 N、coefficient_limit=2 N、
callbacks=24、iterations=3，source 是本 Study 的 Operator 初始化引用
`63609c3249aad6f473cef22e3e9415a4aaa429a9d185367b10806054dbdc030b`。
完整 raw_main_input、full_request 和 field_sources 保留；原 Contract、来源、绑定、时间与
applicability 检查全部通过，未放宽准入或自动替换科学输入。

本次读的是 opportunities 派生入口，未直接读取 `/methods/<method>` 行动视图；已读摘要因此保守
标记该视图 unconfirmed，不能把它解释成完整方法正文已交付。正式选择后的 L0/Schema 则确实
给出控制区间和约束。本轮只修网关，没有继续改动 B6 的 Agent 界面或阅读机制。

## 实际 Native 数值：改善但未满足任务界限

Main 自主提出固定结构、以 supplied full schedule 为基线的有界 Native 控制修正假设，并明确
预期观测、削弱条件和有限搜索范围。没有导入 M0，也没有使用 GVS/SoRoSim/学习代理作为数值结果。
唯一科学结果引用：
`a0658019fde980f3e501b74b1ab100ada84e4da6ae6799e73435ed0dc0598517`。
原 Worker returncode=0、worker_started=true、termination_confirmed=true，status=computed。

| 原直接 Native 指标 | 基线 | best-found | 冻结阈值 |
| --- | ---: | ---: | ---: |
| 原 signed maximum excess J | 13.45390642085818 | 11.269234347898596 | 非任务接受证书 |
| terminal position error，m | 0.1445390642085818 | 0.12269234347898597 | 0.01 |
| holding maximum position error，m | 0.1445390642085818 | 0.12269234347898597 | 0.01 |
| holding maximum speed，m/s | 0.35103466343837014 | 0.3331442296553496 | 0.03 |

原 improvement=2.184672072959584。保持误差/速度依旧超标，task_acceptance 与独立接受均为
**unmeasured**，没有独立物理评价。不能把 computed 或有限改善解释为任务通过、硬件改善、全局
可行/不可行或严格梯度。搜索因 evaluation_request_budget 停止，convergence=unresolved，
global_optimality=not_established；best 标签为 finite_difference，不能冒称收敛最优解。
局部响应的 16 个有效系数、rank=16 与约 3.83e6 条件数只是该局部数值诊断，不是稳健性证书。

数学输出另登记了完整控制 schedule
`172b2089896320bcffd75f6a2e82d994c206101b147c1c73cbc2fd967ff04613`，来源精确指向该 Native
请求、初始 source 和 Main 设置；不是第二次 Operator 初始化，也未继承任务接受。
完整原始轨迹、局部响应数组及控制序列保留在原 Store；审查 JSON 给出精确查询，未用摘要覆盖它们。

## 计账、M3 与停止

| 项目 | 实际记录 |
| --- | ---: |
| Provider / 公共操作 | 12/12（其中 Reporter 1）/ 21/32 |
| prompt / completion / total tokens | 138305 / 3282 / 141587 |
| reasoning tokens / 金额 | 0 / 未知，不从 token 数估算 |
| Provider elapsed 合计 / 原 ledger.wall_s | 164.579 / 167.12571 s |
| 共享数学评价 / 真实数学 Worker | 1/4 / 1 |
| Native model_builds / rollouts / callbacks | 1 / 24 / 24 |
| Native physics_steps / attempts | 14400 / 14400 |
| forward / mechanics evaluations | 1465 / 0 |
| iterations_started / completed_response_steps | 2 / 1 |
| Native kernel_wall_s / Worker charged_numerical_s | 1.4598752 / 2.54671 s |
| 原 numerical_s（含准备） | 3.0311714 s |
| 独立物理 / NMPC / RL / NLP / BDF | 全 0 |

Kernel 时间包含在 Worker 数值时间内，不能相加重复计费。原 ledger.worker_calls=0 是既有账本
分类，**不代表数学 Worker 为 0**；实际 1 次以 Worker 生命周期与原边界回执为准。24 次 Native
积分没有因独立物理额度为 0 而免费或被省略。

Main 第 9/11 次确实直接读取上述科学结果字段，原 read_coverage 分别为 complete_fields、
exact_repeat；但 Main 在结果后没有可见解释文字、新科研 Plan 或 STOP。第 8 次有来源约束的
解释来自 Reporter，不能冒充 Main。最终只有一个已完成 diagnose Plan；**M1/M2 通过，M3 未通过**。

与 B5 的观察比较：正式 diagnose 从第 11 次提前到第 6 次，analysis 从 0 到 1，computed 从 0 到 1，
仍未取得结果后自主科研决策。不同独立 Study 和工程条件不能构成严格因果消融。
后续自主机制敏感性研究已有真实 Native 执行通路证据，但结构机制敏感性本身未在本轮研究，
M3 的持续决策能力仍未验证，不能宣称自主科研闭环已完成。

最终 Provider 余 0，公共操作余 11，数学余 3，全部 pending/occupied 为空。原状态 ready，停止方式
是 supervisor_pause（next_request_sent=false），不是 Main STOP/SELECT。原 CLI exit=0。
不追加窗口或 Worker，不修改旧 Store，不合并；提交本轮非敏感结果后停止科研执行。
