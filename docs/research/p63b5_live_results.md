# P6.3-B5-Live：M1 完成，M2/M3 未达到

用户在准备交付后明确要求「请开始测试」，据此执行已准备的独立 M **一次**真实窗口。
Provider 12/12 用尽，Main 在第 11 次完成正式 diagnose；没有提交 research_analysis，
数学评价为 0，Worker 未启动。不是求解失败、数值无解，也没有新数学结果。
当前已停止，不追加请求或数学计算，不代 Main 执行，不重算或导入 M0。

[逐请求原始工具输入、Plan、实际 wire、来源、费用与分级审查](p63b5_m_live_audit.json)。
沿用原分支 `codex/p6-3b5-native-math-entry`；执行代码 freeze
`d74a97a001519e14e2c674879dcac2553de461a7`，启动时 HEAD
`249696bc46f103fe360380efaad5f4951b68c722` 仅多出绑定文档，原 core/science hashes 与依赖兼容。
本轮没有修改生产代码、模型、求解器、冻结配置、准入或预算，也没有新增回归测试或另一套执行入口。

## 独立授权与原输入

Study `p63b5-m-native-sol-20261029`，resolved identity
`a1ae8242263061e3701270b55d29c6327b424b0dfd4e6fa6fefee1e506caa127`。
原 Store 为本 worktree 的 `runs/research/p63b5-m-native-sol-20261029`，没有重建、重置或迁移。
原授权机制登记本次用户指令、准确身份、sol/none、Knowledge、Native 范围与原额度：

- formal_study_authorization：`60532403f2d0906f325e788665463a53d23a13a2998b2706b423071bc0568961`。
- request-feedback live_handoff_admission：`2ead673b3db1fba2e75a9af28ac1793742efc365f1603181c82d77b279bd3fb6`。

Handoff 沿用先前同 sol/adapter 的实际连续工具反馈传输证据，仅用于工程会话准入，未导入历史科学
结果或候选。启动前原解释器/线程/依赖检查 ready，credential() 原检查通过，未记录密钥。
本轮没有 models GET、smoke 推理、模型切换或 reasoning 升级；全部正式请求使用 gpt-5.6-sol/none。

起点仍只有 Operator 结构 `5ea5e8f8…8a171b04` 和原 initialize_control baseline source
`4d572113…a6de956`。完整引用、各自 Operator 来源凭据、30×4 张力网格、任务/模型/设计绑定及
0.2 N 默认输入见 [准备审查](p63b5_preparation_audit.json)。本次没有新增控制初始化或候选。
二者始终 task_acceptance=unmeasured，不是 Main 原创成果或数学数值证据。

## 实际 12 次请求

所有请求 HTTP 200；表内 tokens 为 Provider 返回的 total_tokens，秒为原 elapsed_s。
工具拒绝和读取同样保留并计账；没有 Reporter Provider 请求。

| 次数 | Main 的实际行为 | tokens | 秒 |
| --- | --- | ---: | ---: |
| 1 | 对 `/methods` 目录使用条目 fields，被 INVALID_EVIDENCE_POINTER 拒绝；反馈提供原准确查询 | 8167 | 9.281 |
| 2 | 移除 fields，成功读取原方法目录 | 8685 | 10.765 |
| 3 | 读候选参数、来源、绑定控制链接和 T1 单方法行动视图 | 9665 | 10.641 |
| 4 | 搜索 success_case 元数据，未读正文 | 10087 | 10.312 |
| 5 | 再读同一个 T1 单方法行动视图 | 9356 | 9.265 |
| 6 | 再搜索 success_case 元数据，未读正文 | 9454 | 10.796 |
| 7 | 第三次读同一个 T1 单方法行动视图 | 9271 | 9.656 |
| 8 | 再读参数、来源、控制链接，并定向读 T1 required_sources/control_input_guidance 等五项 | 9687 | 9.250 |
| 9 | 沿准确 query 读取 T1 request_template | 10140 | 11.265 |
| 10 | research_route(research_plan, diagnose)，只加载 Plan 工具 | 9477 | 16.188 |
| 11 | 正式提交 diagnose，原准入完成，达到 M1 | 9417 | 16.390 |
| 12 | 原保护收尾；用准确 working_set query 读取 `/all_fresh_results`，返回空列表 | 7910 | 11.188 |

准确逐请求秒值以审查 JSON 为准。没有 research_analysis 工具提交、analysis_request_binding、
control_optimization.source 赋值或 Worker 请求。M2 与 M3 均未观察到。

## 正式科研选择及输入说明的实际交付

Main 自选 `mujoco-nonlinear-task-capability-v1`，假设固定结构和已初始化控制上的局部有界三结点
修正可降低 Native reach-and-hold 目标，并可能满足 terminal_error、holding_max_error ≤0.01 m
和 holding_max_speed ≤0.03 m/s。它在 Plan 中限定了仿真、有限局部搜索、失败不证明全局不可行，
并提出结果后解释 baseline/best-rollout 指标再选择继续、结构修订或停止。
原 hypothesis、fixed_conditions、weakening_observation 和 decision 完整保存在审查 JSON。

Plan 文本将修正设为最后 0.18 s、knots=[0.42,0.50,0.58]，并把 correction_window_s 写为 0.18。
这是 Main 的**文字意图**，不是通过 AnalysisRequest 的控制设置：原字段要求显式时间二元组，
该 Native 方法还要求从初始状态覆盖到冻结 deadline。没有把该文本自动改写成合法参数，也没有
启动 Worker 检验它。正式 diagnose 成功不等于数学设置合法或控制 source 已完成选择。

输入展示观察可由原 wire 复核：

- Operator source 完整引用从第 1 次请求就出现在当前 Study 控制信息中；Main 第 3/8 次成功读了
  绑定控制链接。不是候选没有 source，也没有来源准入拒绝。
- 第 3/5/7 次方法返回体含新的 control_input_guidance；后续紧凑投影保留了 required_sources
  和 method/margin/window 说明，不能据返回体假称完整嵌套字段都已原样内联给 Main。
- 第 8 次定向读取后的**第 9 次实际 wire**确实包含完整 candidate_role、source_role、
  recorded_sources、baseline_initialization、after_initialization 和 settings 说明。
  原实际发送对象已检查，审查 JSON 的 input_guidance_actual_wire 保存逐请求文本存在性检查。
- 第 11 次才完成 diagnose；第 12 次原 L0 为 protected_closeout，T1 planning_status=blocked、
  research_analysis.loaded=false，实际工具 Schema 没有 research_analysis。最终不加载数学工具
  与原保护规则一致，不能描述成正常科学窗口内的交接 Schema 丢失。

本次只证明说明和 source 信息被实际交付，以及 Main 完成了正式选择。没有真实数学输入可供验证
source/method/margin 修复效果；初始化后重新 diagnose 的路径也未被本次 Main 调用。
与 B4 两次被拒的 analysis 相比，本次连 analysis 都未提交；不能据此宣称数学闭环改善或退化的
因果结论。重复读取、晚 diagnose 和窗口使用是本次明确可见的推进断点。

## 实际成本与停止状态

| 项目 | 实际值 |
| --- | ---: |
| Provider / 公共操作 | 12/12；18/32 |
| prompt / completion / total tokens | 109389 / 1927 / 111316 |
| reasoning tokens / Reporter Provider | 0 / 0 |
| 原 ledger.wall_s | 134.997 |
| 共享数学评价 / 数学结果 | 0/4；0 |
| 真实数学 Worker / Native model_builds / rollouts / physics_steps | 全 0 |
| 独立物理 / NMPC / RL / NLP / BDF | 全 0 |
| 原 numerical_s / control_initialization_s | 0.482425 / 0.130848，保留准备阶段原开销 |
| pending Provider / pending science / occupied resources | 0 / null / 空 |

金额未知，不从 tokens 推算账单。Native 没有执行，所以没有积分成本；这与存在 Native rollout
但独立物理=0 的情况不同。四次数学余额和十四次公共操作余额不是新增 Provider 窗口的授权。
原九项 success_case 权限保留，仅搜索元数据，正文读取数为 0。

最后的 empty fresh-result index 已公开读到；Main 没有提交 STOP/SELECT。原 research_status=ready，
实际停止是原 supervisor_pause，next_request_sent=false，暂停引用
`6a6e4d5930e995ef7e6e689713187d1fd9cf610430cd3dba05965746214383ed`。
没有将外部额度暂停改记为 Main 科学停止。
原 CLI exit=0；日志中的 RequestBoundaryHandoff / SupervisorReviewPause 是原会话控制路径。
唯一工具拒绝是首个目录 fields 读取错误，不是数学准入或 Worker 运行错误。

**M1 完成；M2/M3 未达到。** 本次没有机器人性能或数学敏感性新结论。所有 MuJoCo 结果即使未来
计算成功也仍是仿真参考，不能当作实物真值。本轮只提交非敏感结果投影与说明，不提交完整 Store、
Knowledge 正文、凭据或 Provider opaque output；不改写历史准备/B4/M0，不续窗、不扩框架、不合并。
