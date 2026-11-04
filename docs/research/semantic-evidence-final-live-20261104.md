# 语义取证最终审查与真实 Main 验证（2026-11-04）

本轮在原 Study 上完成接口修复、正式接续与真实 Gateway 验证。
`gpt-5.6-sol` 自主运行了真实有限时域数学检查，并依据结果提出新的刚度假设。
后续求导未通过原参数授权，新假设的 diagnose 又未通过合同，故没有第二次数值计算、
新结构或独立物理验收。已在安全结算边界监督暂停；不是 Main 自主 STOP。

## 接口审查与修复

基线：`codex/semantic-evidence-20261104@7ffb98ff40149894fe626f62bff9d667b50b4942`。
交付分支：`codex/semantic-evidence-final-live-20261104`，不合并 main。

Reporter 的 current_task 不能仅把 structure 改为 task：冻结输入 snapshot 不属于其候选/保存结果
ResultCard 合同。修复从已实现 subject 选项中删除 current_task；旧直接入口明确返回 unsupported
与 `evidence_read(subject=current_task, topic=task)`。实际 SDK 拒绝旧入口并提供合法入口说明。
Main 直接读取仍绑定原 session snapshot 的 `/input/task`，冷启动无需候选，不生成报告或科学证据。

focus 是给 Reporter 的科研问题文本，不负责选择字段。原默认五类主题会无条件展开参数、机制、
方法目录；现默认仅 structure/task，详细主题通过既有 reads/topic/group/selection 显式选择。
没有自由文本关键词映射，没有扩大 Reporter 推断权限。

EvidenceReadQuery 保留 EvidenceIntentQuery | EvidenceQuery；evidence_query_schema 经原 provider_schema
保留联合合同和条件结构，Runtime 复用同一确定性编译器。混合输入仍拒绝，精确原始读取、
acceptance_certificate、正式 SELECT/STOP 保留，没有修改物理、评价器、阈值或参数授权。

运行中另证实一处必要修复：最新数学结果 detail_query 仍在每轮 L0 宣传旧 working_set
`/mathematical_decision_view`。6277 字节派生视图被转为目录；请求33/36输入与反馈哈希完全相同。
仅将该自动详情链接改为现有 `subject=结果, topic=mathematical_results`。
历史反馈和精确 raw/derived review 不重写。真实请求37随后采用新入口，收到完整事实与真实来源，
formal_read_credit=false；之后的证据读取全部使用语义查询。

生产源码仅改 reporter.py 与 research_context.py；没有新 Agent、Planner、Registry、Store、
调度器、任务适配器或正式 SELECT/STOP 流程。

## 验证与真实 Schema

36 项不同定向测试通过：语义/实际 SDK Mock 16 项、既有 Reporter 17 项、旧 Schema 恢复刷新1项、
原完整证书 SELECT 与 STOP 索引2项。M1、被动v2、M5、真实来源、原始/派生视图区分和不授信保持。
运行中详情链接新增回归修复前失败，修复后与 Reporter/SDK 恢复共3项定向回归通过。
1项旧测试的4个 subcase 因缺少 `evidence/s129_math_capability/gvs_pair.json` 未完成，不报告为通过。
两个旧离线 Reporter 夹具补齐原门禁所需测试 scope，其中一个补注册合成结果；生产授权未放宽。
首次失败及补测日志均私有保留。所有离线测试不产生真实 Provider、Worker 或积分。

当前 Gateway `http://127.0.0.1:8787/v1` 的健康检查和账号目录确认精确模型 `gpt-5.6-sol`。
Main reasoning=none，Reporter reasoning=medium。实际请求28–43均 HTTP200，接受带 EvidenceIntentQuery /
EvidenceQuery 联合条件的工具 Schema；正式 diagnose 后 research_analysis 确实在实际 Main wire 中。
这证明该非 strict Gateway 合同的实际接受，不保证模型每次输出符合合同；Host 仍执行独立验证。
所有实现接续后均先 restore_only，再发送有限请求；旧历史、最后反馈与最新工具合同恢复正确。

## 原 Study、授权与实现身份

原 Study：`passive-mechanism-autonomy-20261104`，未另建后继 Study。
开始时540个 artifact、133个 Store/SDK文件及共享授权库与既有完整备份一致；复用原备份。
原授权文本字节哈希核验通过，原批准允许累计48、每次最多+8及非科学接口版本接续。

开发工作树第一次写入前因 AUTHORITY_ANCHOR_MISMATCH 被原门禁拒绝；改为在原执行工作树
检出已提交实现后，从原路径使用原共享授权库。没有复制授权索引或绕过 check_root。
预算32→40、40→48均通过原 attached-authority 原子增补及 formal_study_authorization /
live_handoff_admission / core.bind，旧费用没有重新扣除或清零。

原 Store 的冻结 Provider 实际是 DeepSeek。用户明确指定应使用 Gateway 后，正式记录运行配置接续，
没有把模型切换冒充单一模型的接口对照实验。更正前已结算的额外1次 DeepSeek请求保留：
19310 tokens、一次历史回看和一次机制语义读取，无数学/物理计算；不能计作目标 Gateway 验证。
此前桌面自动审批拒绝及后续用户明确外发批准也保留，拒绝本身没有产生 Provider 消耗。

| 阶段 | 实现 / resolved identity |
|---|---|
| 原暂停 | `8517772445741d7871a5b0c468249637e5688ce1` / `2c7105e30478c5bcb6cad3b37492e5b178a7c3932f723bbaf7cf31c911e496cc` |
| Reporter修复、总额40 | `90e3e2a5ee96e1213eb5a2e73dc4208f58d8c46e` / `b1ae07b461059d4d074407394dadcf78b5cedaa2b5b3aa7452101d8835e0b2ae` |
| 用户更正为Gateway | 同一实现 / `32908efe1f98500ce72db41a0453f595b47dd12ade5e4b9fcee82e5454ea082b` |
| 最后+8至48 | 同一实现 / `d9ef09d43645415a67c79980631c9cf145c06abaa3ec070453ae2372d6713fc3` |
| 保存数学结果详情修复 | `a9873b995150afd499182f3817d1df1c72d297aa` / 同一 resolved identity |

科学 profile 始终为 `9f95b160c2aa80a89ca40d324d75fc33e660fd51a86f3fe6a65235cdc376dcd3`。
原任务、FamilySpace、评价器、积分协议、科学文件、参数授权和 execution_instructions 均保持。
数学累计配额仍 null，单 Worker180秒，共享物理256 episode /128000步、独立Replay16次不变。
后续报告提交不更换原 Study 的执行 SHA。
唯一数学结果产生于90e3e2a阶段；a9873b9接续后读取该原结果，没有重算或重标其来源SHA。

## 自主科研实际过程

Gateway 段15次 Main、1次 Reporter。第一轮 Main 自主选择已注册 finite_time_task_response /
finite_time_task_violation inspect，真实 Worker完成1次数学评价、1次模型构建、1个完整0.5秒episode、
500步积分。它计算的是有限时域响应，不能声称已验证原H1全文中的所有静态/Jacobian机制。

记录的响应最大值为 `9.166032107660516e-05 m`，冻结上界 `1e-09 m`，规范化超限
`91659.32107660515`。no-contact hard gate通过，结果为有效 task-metric failure；
没有结构改进、没有请求导数，task_acceptance=unmeasured。
Reporter给出3项有真实来源的解释，区分有效失败、未建立因果方向和独立验收仍未测。
实际后续 Main wire 持续包含上述数值、限制和数学 Schema；反馈未丢失。

原详情链接造成目录循环，修复并再次正式绑定后，Main采用语义结果读取，继而自主提交求导问题，
后又提出H2：提高授权的杨氏模量是否降低位移超限且保持无接触，并给出可削弱该假设的观察。
H2明确引用真实基线数值，不是监督者注入的科研路线。

后续执行限制必须保留：

- 请求38选择了一个未授权参数，原冻结授权门禁返回 ORIGINAL_FROZEN_PARAMETER_AUTHORIZATION_REQUIRED；
  没有启动 Worker或增加数学/积分。不能将其记成求导失败或结构不可行。
- 请求40的diagnose包含多余顶层selected_candidate，Host明确要求移到decision内。
- 请求42删除该多余字段，但research_intent仍不符合DIAGNOSE常量；Host再次明确拒绝。
- 请求43又读取已有数学结果，未完成H2正式登记，没有执行单参数求导。

Gateway证据读取8次语义、5次原始；另有额外DeepSeek段1次语义读取。
5次原始读取包含完整结果索引1次及4次目录反馈，其中数学决策视图有1次字节完全相同的重复。
没有发生本轮原始/派生字段混用错误。修复后6次读取全为语义输入；仍有对相同已保存结果的重复读取，
不能把这种模型行动停滞全部归为接口错误。原参数门禁与Plan拒绝符合当前实际Schema，不予绕过。

| 层级 | 本轮证据与边界 |
|---|---|
| L1 信息获取 | 真实语义读取任务机会、注册参数及已保存数学事实；旧详情入口缺口已修复并真实采用 |
| L2 研究行动 | 自主执行真实数学检查；H2为后续自主提出的可检验假设，但其新diagnose未获准 |
| L3 结果利用 | H2与杨氏模量选择明确基于实际结果；有决策意图证据，尚无完成的第二轮辨别计算或结构采纳 |
| L4 结构与独立执行 | 未完成；未生成新结构、未独立Replay，不能声称数学指导结构设计已通过 |

## 最终费用、安全与发布

| 范围 | Main | Reporter | Provider | tokens |
|---|---:|---:|---:|---:|
| 原历史26次 | 22 | 4 | 26 | 321492 |
| 更正前额外DeepSeek | 1 | 0 | 1 | 19310 |
| 本轮Gateway | 15 | 1 | 16 | 216952 |
| 原Study累计 | 38 | 5 | 43 | 557754 |

数学评价1，模型构建1，episode/rollout1，积分500，独立物理Replay0，新结构0。
数值时间 `2.177401200053282 s`，积分kernel时间 `0.6139879999682307 s`；
共享账本 backend_solves=1、model_calls=43、tool_calls=60、wall_s=`346.38794880046044`。
平台通用 worker_calls=0不代表数学子进程未启动；真实启动由原数学Worker回执、结果及实际积分记录证明。
货币账单未记录，cost_usd为unknown，不按当前价格反推历史实付费用。

总额48、剩5，其中4为保护收尾；原legacy门禁 science_capable_main_requests=0、
next_request_will_protect=true。未消费保护额度做探索、未超过授权48，也没有为耗尽配额继续发送。
最后监督暂停明确 not_main_stop=true，SDK ready是可恢复状态，不代表仍有请求执行。
最终897个artifact哈希通过；原540个artifact、510个事件和全部原调用/费用逐项保持。
共享授权绑定正确，无pending/unknown Worker、未结算调用、unconsumed响应或资源占用。

源码修复提交：b0ce55a；离线夹具补齐：6428496 /90e3e2a；运行中详情修复：a9873b9。
仅发布非敏感源码、测试与本摘要。私有Store、完整wire、凭据、原批准全文、运行脚本和历史成功参数不公开。
没有自动启动正式PHS-2D/P3，没有合并main。下一阶段是否开展应基于上述未完成项另作决定。
