# PHS-2D Knowledge 自主研究：真实启动与前两窗口

Study `phs2d-knowledge-autonomy-20261105` 已真实启动，沿用 resolved identity `31c22b6af32975d2d30c87e1c56943faf0fb47d6273d74d5496a790237b5dab7`、原 Gateway `gpt-5.6-sol / medium`、原完整十工况和原 Store。这里记录前两个已结算窗口，不代表最终科研结论；后续累计状态以 [状态 JSON](phs2d-knowledge-status-20261105.json) 和私有原账本为准。

## 额度恢复与批准

用户先批准精确身份和注册数学；随后明确要求真实测试 Gateway 额度。操作者据此仅发送一次最小推理检查，HTTP200，回答 OK，prompt=27、completion=5、total=32 tokens。此次例外有独立授权事件、原始请求/响应和结算，计入本 Store 的原 24 次共享额度，没有后台重试。接口没有返回账号剩余额度总量，不能从一次成功推断可持续调用总量。

用户随后明确选择“继续当前 Gateway，保留 gpt-5.6-sol / medium”。官方 OpenAI API 确实已有独立配置和 Key 文件，但本 Study 没有切换 Provider、计费账号、模型或重建 Store。

## 工程归类修复

操作者把此次检查标记为 `gateway_quota_probe`，旧 SDK 历史检查仅认识 reporter/provider_validation 等已知非 SDK 请求，因此在首个科研发送前复现 `SDK_HISTORY_HAS_NO_TRUSTED_STORE_ANCHOR`。原始收据未改写。最小生产变更只在已知非会话用途集合中加入该明确类型，保留共享计数与全部原费用。

真实 SDK + Mock HTTP 定向回归验证：先扣账并结算一次 quota probe，再正常进入空的科研 SDK 历史；未知用途和未信任消息后缀仍拒绝；随后原 SDK 可发出一个正常 Mock 请求，累计账目为 2。回归通过，执行约 8.6 s，无真实 Provider 或科学积分。旧 v2 测试入口另受缺少 matlab.engine 的无关夹具依赖阻断；没有为被动 PHS 安装或伪造 MATLAB。生产修复不涉及物理文件、科学合同或验收，按原 bind/migration 保留原 profile 和 resolved identity。

## Main 的真实行为

第一窗口共 4 次 Main 请求：

1. 自主提出可证伪的被动约束假设，并生成一个合法九段、四被动腱候选。其自行选择的首个拓扑为全跨距对称约束，目标是保留内部变形而限制末端位移；继承的合法默认值不是任务通过证据。
2. 自主选择实际张紧集合、Jacobian、零空间和局部柔顺性作为机制检查方向，完成 diagnose 意图登记。接口明确反馈 diagnose 不执行数学。
3. 提交真实 `research_analysis`，但把静力载荷写为 `all_frozen_conditions`；原运行时返回 `SELECT_FROZEN_LOAD_CONDITION`，没有开始科学计算、没有扣数学评价。没有增加模型字段兜底。
4. 自行改为明确的 `unloaded` 条件并执行一次原注册 `mechanism_structure_v1` 检查，得到真实的未合格工作点。

第二窗口共 4 次共享请求：1 次 Reporter、3 次 Main。Reporter 保留资格失败及模型范围；Main 读取路由参数、选择生成接口并进一步读取候选配置。此时尚未生成第二个候选，尚未进行重复数学计算或物理 Replay。存在明确的后续结构决策，因此继续在原额度内观察，没有申请预算增补。

## 真实数学结果与适用性

本次是无载、理想硬单侧约束的零时域局部检查，不是完整动态任务：

- 4 个约束活跃、LICQ=true，但只有 2 个正乘子且 strict complementarity=false。
- optimizer_success=false，终止为 `nonconverged_unqualified`。
- primal violation=0.4165296419 m，stationarity infinity norm=3919.124982 N·m。
- 最大约束张力=5032.632121 N，而声明容量为每通道 0.406 N；容量资格未通过。
- 最小约化刚度=-328.492308 N·m/rad，native soft-limit length excess=0.4165296419 m。

未合格点的负刚度不能被当成一个已合格平衡的稳定性结论。没有可信结构方向、敏感性、下降保证或完整任务通过结论；非收敛不证明全局或结构不可行。Reporter 实际保留了这些区别，Main 的后续理解与结构采用仍待继续观察。

实际成本：1 次数学评价、1 个 Native 模型、1 次平衡、144 Hessian 列、315 native forward、0 积分步；kernel 约 0.338 s，已结算数学 Worker 约 1.571 s。没有加载 episode、独立 Replay 或十工况证书。

## Knowledge、资源与能力判断

六条已审核程序白名单仍不变，历史案例及其引用仍不可读取。首轮确认交付一个 `skill-parameter-model@1` compact 摘要；完整正文读取为 0。Main 在实际 Plan 中明确不声称采用尚未读取/确认适用的 Knowledge。不能据此归因其研究方法由 Knowledge 改善。

截至前两窗口：Provider 9/24，其中 quota probe=1、Main=7、Reporter=1；公共操作 7/160，数学 1/20，共享 backend episode 0/80。9 条响应均有 usage，累计 prompt=235,622、completion=3,195、total=238,817 tokens。货币费用未测量；所有失败、检查和原始费用均保留。原保护收尾 4 次仍保留，没有增补、无计数重置。

L1 已观察到自主合法结构生成及假设；L2 已发生真实机制分析，但工作点不合格，对科学判断能力的评价还需后续行为。L3 数学指导的新结构修改尚未观察到，L4 完整十工况通过尚未建立。当前没有 SELECT，也没有 Main STOP。监督者没有向 Main 提供历史获胜结构、参数方向或指定下一项科学动作。
