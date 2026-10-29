# P6.2-F 科学信息可靠性修复与 Luna 真实复验

基线 `574fee7476cdc893e7ff39e0faf34e5df2fb4005`，独立分支 `codex/p6-2f-scientific-information-repair`。开始时远程 P6.2 分支仍为该提交；远程默认 HEAD 为 `2a854280db69425dc50af9012b8da52194a679ee`。不合并默认分支，不改已有工作树或封存 Study。

## 实现和边界

- `evidence_views.py`：结果卡按各个已记录 norm-bound 约束保留极值、单位、阈值、严格状态、采样时刻及覆盖窗，修复只显示全局最严重违反而漏掉微小位置超限的问题。原始向量型旧记录继续使用旧投影。未数值验证的 capability replay 不获得新指标资格。`metric_semantics` 只为原约束定义及已有 reach 评价分量提供方向；其他指标保持 unknown。`quantitative_facts` 分离宿主计算、求解器、数学结论、任务验收、评价有效性、目标位置距离及配置终止条件。
- `reporter.py`：比较添加有符号差值、偏好、方向和双方通过状态。新 Provider 输入只发送紧凑事实及来源目录；自动 summary 读取由已投影事实承接，过大的显式读取给出缺失细节与原查询，完整读取仍留在 Store。旧报告引用解析为原始结果，避免递归展开历史报告。解释不能覆盖结构化事实，原序列化 Schema 和已存 wire 恢复路径保持。这里没有自然语言事实核查器，不能保证自动检测任意错误文本。
- `evidence_policy.py`、`agent.py`、`research_context.py`：报告的读取身份和原始结果的科学引用身份显式分离，拒绝反馈指出具体引用、角色、推论、候选范围及资格查询；不自动替换引用。L0 按结果组织完整约束和状态，避免平铺截断漏约束。`admit_decision`、SELECT/STOP、正式读取资格保持原样。
- `experience.py`：空搜索返回真实可用任务标签、无筛选搜索和精确读取入口，新增 context_only 角色标记。没有新增或更改 Knowledge 正文，没有伪造审阅或成功经验。当前英文 `research-strict-near-tolerance@2` 来自 position_tool_axis；reach/hold 的跨任务适用性未验证。
- `session_handoff.py`：仅在原有反馈压缩路径保留具体引用纠错字段；继续使用原交接、安全边界和已读确认机制，无第二套记忆。
- `p62f_live_audit.py` 复用 P6.2 的导入、有限请求及逐 wire 审计。新 Study 独立 Store，历史科学证据按原 artifact ID 复制，零当前验收信用。实际发送前沿用既有请求账本的角色上限（Main 7、Reporter 3）和共享上限 10；失败计数，不重建或补充预算。

## 已冻结的原失败

原 Luna 物理报告同时存在正确数值和相反的改善方向，将变体终点误差混同保持极值；后续综合报告用 only 漏掉数学位置超限。Mini 原报告还混淆 valid_failure 与无效实验、目标残差与平衡残差，并反复把 Reporter 引用提交到 supporting_evidence。原输出仍完整保存在 P6.2 结果 JSON 和封存 Store，不作改写。

`tests/research/fixtures/p62f_facts.json` 是带原来源身份的只读数值片段，覆盖 SLSQP 100 次上限、success=false、0.33 s 的 `0.02000489088519356 m/s`、0.30 s 的 `0.010000056805892363 m`，以及物理比较三项指标。测试中的候选绑定是合成夹具，不是新科学结果。

## 离线验收

第一组定向组合 104/104 通过，包含信息流、Reporter、证据准入、Knowledge、Recent Round、反馈交接、角色预算和 Provider Schema。日志 `runs/p62f/offline_final.log`。日志中的 RequestBoundaryHandoff、故障注入 ReadError 等是被测试的预期路径。

最后的定向组合 29/29 通过（与 104 项重叠，不相加）。首个真实请求后，记录数/时刻数修正的 6/6 回归通过；监督式入口提示绑定修正的真实 SDK/Mock HTTP 1/1 通过。旧 Study/Harness/F1 投影补充检查 7/7、具体引用纠错经过有界交接反馈压缩的检查 1/1 通过。所有日志及哈希在 `p62f_validation.json` 中记录。没有把 Mock 成功计为真实模型成功。

## 真实执行记录

真实复验已完成，所有 10 次 Provider 请求 HTTP 200，只有 gateway `gpt-5.6-luna`，Main/Reporter reasoning 均为 none。模型目录核对使用 GET /models，没有额外 Echo 或能力探测。实际 HTTP 成功和科学语义正确分别评价。

| 项目 | 结论 | 范围 |
|---|---|---|
| Reporter Scientific Accuracy | **PARTIAL** | 核心数值、全部已知数学违反、物理方向和科学状态正确；仍有时间覆盖措辞及 wall-time 比较文字错误 |
| Reporter Context Efficiency | **PASS** | 三次实际输入显著下降，必要阈值、违反及原始恢复入口仍在；不等同 Main 整体高效 |
| Main Evidence Use | **PARTIAL** | 能描述证据和委托调查；无合法科学 Plan、无拒绝后有效修正，仍完整读取综合报告 |
| Knowledge Delivery | **PASS（监督式）** | 实际英文正文进入确认的 wire；没有证明自主选用或实际采用 |
| Handoff Continuity | **PASS（实测边界）** | 6 次真实反馈边界全部状态和原样反馈一致；未覆盖正文确认送达之后再发生一次新 Provider 交接 |

新 Store：`D:/softrobot-agent/.worktrees/p6-2f-scientific-information-repair/runs/research/p62f-luna-20261029/platform.sqlite`。机器导出：[p62f_luna_results.json](p62f_luna_results.json)。原始请求、响应、SDK 快照和完整反馈保存在该 Store；导出对巨大的双份反馈保留精确相等断言、双侧 digest 和原始恢复引用，未改写原报告。

初始实现绑定 `6756a5aa9`。第一次真实数学输出暴露字段命名歧义后，绑定最小修正 `7d8f9ee462e7efe95109037260784fe8401dba49`，沿用同一 Study 和账本，没有重发数学问题。监督式入口先因错误的模块属性绑定在发送前本地失败，提交 `e37585ad2` 修正；当时请求仍为 7，随后使用原剩余额度。该修正只涉及操作者脚本，没有变更科学或生产运行源码。最终提交身份见交付清单及分支历史。

## Reporter 科学事实核对

数学输入 5,905 tokens。实际输出保留：SLSQP status=9、100 次迭代、success=false；数学结论 inconclusive，无 witness/排除证书；终点误差 `0.009657911738682468 m` 通过，保持位置 `0.010000056805892363 m` 在 0.30 s 严格失败，保持速度 `0.02000489088519356 m/s` 在 0.33 s 严格失败，另指出 0.30/0.31/0.35 s 的速度违反。目标距离 `0.053749418601506754 m` 明确不是力学平衡残差。局部仿射、exact ZOH、0–8 N、离散覆盖和非物理验收的限制均保留。

首份文本把 13 条约束采样记录称为全时域的 13 个 samples，时间覆盖表述不够准确：实际是 6 个唯一时刻（0.30–0.35 s）上的 13 项约束检查，声明的模型轨迹时域为 0–0.35 s。生产派生视图已明确拆成 `checked_constraint_sample_records`、`checked_unique_times_s` 和 `checked_time_range_s`，并在后续真实综合调查及 Main wire 中使用。首份原文保持不变，不宣称已通过新的真实同题复验。

物理输入 10,422 tokens。实际文本正确区分终点误差和保持极值，指出两个有效但失败的评价、位置通过、保持速度失败，峰值在 0.35 s。以第二列为基线：

| 指标 | 基线 | 变体 | 差值（变体−基线） | 程序/实际文本方向 |
|---|---:|---:|---:|---|
| 终点误差 m | 0.0031364418844500026 | 0.0027808380549602055 | −0.00035560382948979707 | 改善 |
| 保持最大位置误差 m | 0.0031364418844500026 | 0.0030310250356348953 | −0.00010541684881510728 | 改善 |
| 保持最大速度 m/s | 0.022849089710631265 | 0.05203049356582944 | +0.029181403855198178 | 恶化 |

结构与控制变化、身份缺项、控制诊断在隔离 Store 中不可恢复等限制均没有被升级为单因素因果证据。原 S142 的所有者会话没有复制，不能将隔离环境诊断不可用解释为原实验没有记录。完整已复制运动数据可用精确 motion 引用恢复。

仍有明确文字错误：物理报告末段将变体的 3210.219 s（resource 3212.395 s）称作比基线 3316.391 s（resource 3321.815 s）“larger”。数值正确，比较形容词相反。没有改写文本或重复请求掩盖此错。程序未声称能核查任意自由文本。

Main 委托的综合报告输入 14,542 tokens，正确保留两项微小数学违反、物理保持速度失败、inconclusive、目标残差含义及非因果范围；没有再次出现原 P6.2 的速度方向反转或数学 only-speed 断言。三次 source_catalog 分别 21、34、52 项，全部精确指针均可恢复。

## Main 自主窗口和监督窗口

| Main 次序 / wire 事件 | 性质 | 实际动作及结果 |
|---|---|---|
| 1 / 36 | 自主 | diagnose 路由成功；只选择工具，无科学执行 |
| 2 / 53 | 自主 | endpoint 诊断缺 selected_candidate，被拒；反馈明确错误字段、候选入口和零 Worker |
| 3 / 70 | 自主 | 综合 research_investigate 成功，引用两份报告和三项原结果；程序解包并去重为三项原结果，触发 Reporter 第三次请求 |
| 4 / 99 | 自主 | evidence_read(full) 完整读取综合报告，造成下一次输入膨胀 |
| 5 / 120 | 监督式 | 无严格筛选的 Knowledge search，真实获得英文目录 |
| 6 / 137 | 监督式 | 精确读取 research-strict-near-tolerance@2 |
| 7 / 154 | 监督式 | 已经收到正文后再次 search；没有知识采用说明或最终科研判断 |

自主窗口在 Main 4 后暂停，`p62f_autonomous_window_closed` 保存状态身份及账本。没有自然 STOP，没有人为重启后声称是同一自然轨迹。监督指令和窗口事件单独保留。共 7 次公共工具调用：路由 1、拒绝 Plan 1、调查 1、报告整读 1、Knowledge 搜索 2、正文读取 1。原始科学结果的 Main 直接读取为 0，重复正文读取为 0，重复搜索为 1。综合调查与前两个问题有重叠，不能当作三个相互独立的新发现。

Main 能表达局部求解失败、物理速度失败和因果未决，但没有修正并提交合法诊断 Plan，也没有形成合法 STOP/SELECT。本次未出现把 Reporter 放入 supporting_evidence 的真实拒绝，因而“收到一次这种拒绝后能否修正”真实结果是 **NOT TESTED**；只由离线用例证明具体反馈和后续显式修正可行，不据此声称模型已学会。

## Knowledge 与 Handoff 的真实证据

唯一英文条目仍来自 position_tool_axis。搜索和读取正文保留原历史来源/哈希、authored_english、human_review=not_claimed，回执明确 context_only、跨任务适用性未验证、无科研验收资格。没有制造 reach/hold 成功知识，也未改动旧中文条目。

第 6 次 Main 工具完成读取，回执 `4ace0f23e6cc92546c510b573898fdb027ea37539e4ad45e27ed8621ac06e814`。交接 151 → 实际新 wire 154 原样带入正文，收到 HTTP 200 后 `read_progress()` 才报告 `body_delivered=true`。发送该请求前的 L0 仍为 false 是正确的：当时尚未确认这个请求。之后用真实保存的 SDK 执行 restore_only，正文送达进度、会话和账本保持，零额外 Provider 请求。

交接事件 50/67/96/117/134/151 对应新请求 53/70/99/120/137/154。6/6 均独立恢复，原始 toolUse/toolResult 配对完整；任务、候选、Focus、确定性事实、Trace、Knowledge、Reporter 和预算与权威 source_state 重建的实际 wire 一致。已选工具、已加载 Schema 和原样反馈都保持，没有重复工具执行。`tool_continuation` 整体不与旧 wire 字节相等，因为 recent 被消费并投影为 pending_feedback；精确反馈相等和其余加载状态单独核对。

正文已确认送达之后再出现一次新 Provider wire 的保持状态，以及模型如何采用知识，均没有余额覆盖，标为 **NOT TESTED / 未证明**。最后一次 search 的工具回执已落 Store，但没有下一次请求送达，不计作已发送反馈。最终无 pending Provider、无未消费响应、无科学 pending；通过原 engineering_count_budget_closure 收口，`model_stop=false`。

## 实耗和效率范围

| 角色 | 请求 | 输入 tokens | 输出 tokens | 总 tokens | 缓存输入 |
|---|---:|---:|---:|---:|---:|
| Main | 7 | 228181 | 790 | 228971 | 0 |
| Reporter | 3 | 30869 | 2255 | 33124 | 0 |
| 合计 | 10 | 259050 | 3045 | 262095 | 0 |

Reporter 实际 wire 字节依次 23,132 / 38,613 / 53,927；实际输入 5,905 / 10,422 / 14,542，相对 P6.2 的 35,247 / 53,639 / 102,455 下降 83.2% / 80.6% / 85.8%。前两次相同原证据及核心问题，第三次综合问题和读取轨迹有所不同；这些下降没有通过省略位置微小违反或其他验收分量实现。

Main 最大输入 109,144 tokens / 433,726 bytes，发生在监督窗口首个请求，主要承接前一自主动作展开的完整报告；原 P6.2 最大为 116,228。完整报告展开的开销问题仍然明显。Main 总 tokens 反而从 188,988 增为 228,971，不能只用总量下降宣布 Main 高效。

两角色总 tokens 从 382,678 变为 262,095（约少 31.5%），两轮均 10 请求，但本轮末三次为监督 Knowledge，原轮是其他自主动作，不能宣称严格因果效率提升。实际金额未报告，保持 unknown。Reporter 每份完成报告平均 11,041.3 tokens；初始数学/物理调查各 6,492 / 11,334 tokens，Main 委托综合调查的 Main 请求加 Reporter 请求合计 35,044 tokens。合法科研决策数为 0，因此每合法科研决策成本不可定义，不填 0。

共享限额 10、Main 7、Reporter 3 均耗尽，没有额外重试或切换模型。数学、物理、NMPC、RL、Worker、Backend 全部新增 0。原 S142 Store SHA-256 前后仍为 `bfc920b67e7c3f42795b408bc9a452210e4e78abff67ab06e76229883de8a581`，原 P6.2 输出文件哈希也保持。

## 结论与复查

本轮完成了最小修复、有界真实复验和审计，但**尚不满足以可信 Reporter + Main 自主判断进入 P6.3 的完整前置标准**。应先解决自由文本剩余比较错误、Main 的合法诊断及拒绝纠正、避免不必要完整报告展开，并真实证明自主 Knowledge 选择和采用。没有启动 P6.3 或任何新科学计算。

离线回归命令见日志和验证 JSON；只读重建真实审计：

```powershell
$env:PYTHONPATH='D:\softrobot-agent\.worktrees\p6-1-research-information-flow\runs\p61-deps;C:\Program Files\MATLAB\R2024a\extern\engines\python\dist'
D:\softrobot-agent\.mainline5-env\Scripts\python.exe -m tests.research.p62f_live_audit audit
```

仅 audit 是无 Provider 的复查入口。prepare/math/physics/main/supervised 是有状态操作者命令，不能作为单元测试重跑或用于重置预算。
