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

后续小幅投影变更另做定向检查，结果在 `p62f_validation.json` 中记录。真实发送必须在这些检查通过、实现提交并绑定之后执行。

## 真实执行记录

待有界窗口完成后填入。机器记录将写入 `p62f_luna_results.json`；所有原请求、响应和 SDK 快照留在新 Store。未执行的条件必须标为 NOT TESTED，不能用 Mock 结果替代真实成功。
