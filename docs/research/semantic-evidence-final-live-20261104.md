# 语义取证最终审查与原 Study 接续检查（2026-11-04）

本轮已完成最小接口修复、定向离线验证、原 Study 的正式版本接续和 SDK restore_only。
真实发送被桌面自动审批拒绝，正在等待用户对具体 DeepSeek 目标与研究载荷的明确批准。
本轮没有新增真实 Main/Reporter、数学 Worker 或物理积分，不能据此声称科研自主性通过。

## 源码审查与最小修复

基线：`codex/semantic-evidence-20261104@7ffb98ff40149894fe626f62bff9d667b50b4942`。
独立分支：`codex/semantic-evidence-final-live-20261104`。没有合并 main。

Reporter 的 current_task 先被错误地解析为 structure；即使改为 task，冻结输入 snapshot
也不属于 Reporter 的注册候选/保存结果合同，无法合法生成 ResultCard。因此采用明确不支持方案：

- 从 InvestigationRequest.subject 的已实现对象选项中删除 current_task，并说明直接读取入口。
- 旧入口直接调用返回 unsupported、原因、`evidence_read(subject=current_task, topic=task)`；不保存报告。
- 实际 SDK 按更新后的 Schema 拒绝旧入口；合法替代入口留在 Schema 描述中。
- Main 直接读取 current_task 继续由原 session snapshot 的 `/input/task` 提供来源，无需候选。

focus 保持给 Reporter 的科研问题文本，不作为确定性字段路由。
原候选默认自动读取 structure、structure_parameters、task、mechanism_capabilities、mathematical_methods
五类，且每类会继续读取最多约 12KB；这会无条件展开参数、机制和方法目录。
本轮将默认值收敛为 structure/task；详细目录由现有 reads 的合法 topic/group/selection 显式选择。
没有增加材料、腱路或刚度的自由文本映射，没有改变 Reporter 的推断权限。

EvidenceReadQuery 仍为 EvidenceIntentQuery | EvidenceQuery。agent.evidence_query_schema
通过原 provider_schema 保留联合条件与定义，core.read_tool_evidence 复用同一确定性编译器；
混合原始/语义字段由合同拒绝，原精确 full/fields、正式 acceptance_certificate 和 SELECT/STOP 入口保留。
没有修改这三处源码，也没有新增 Registry、Store、调度器、Agent 或任务适配器。

冻结 Provider 实际为 `https://api.deepseek.com` / `deepseek-flash`，thinking disabled，
并非 ChatGPT Gateway。原 wire 未启用 strict；没有切换模型、推理、端点或上下文策略。
DeepSeek 的 [工具文档](https://api-docs.deepseek.com/guides/tool_calls/) 将 strict Schema 校验
另列为 beta 合同；本轮不把 Mock JSON Schema 成功等同于远端接受。远端接受情况仍未实测。

## 定向测试

35 项不同测试通过，1 项旧测试因缺失历史夹具未能运行：

- test_semantic_evidence：15 项，包括新增冷启动 Reporter 拒绝、直接任务读取与默认主题范围。
- 原 SDK 旧 Schema 恢复后刷新新 Schema：1 项。
- 原完整 acceptance_certificate 实际交付后 SELECT，以及完整 STOP 索引：2 项。
- 既有 Reporter：17 项通过，覆盖真实来源、只读投影、SDK 交付、费用、反馈和恢复。
- test_native_science_tool_reporter_boundary_and_unknown_send 的四个 subcase 均在读取仓库缺失的
  `evidence/s129_math_capability/gvs_pair.json` 时失败；不把缺失夹具报告为通过，未补造科学证据。

初次语义测试的被动夹具要求干净提交，另一个新增断言误以为旧对象能穿过更新后的 SDK Schema；
提交后重跑全部 15 项通过。两个旧 Reporter SDK 夹具缺少原门禁要求的离线数学 scope，
其中一个还没有注册其合成结果；仅在测试内用现有 approve/helper 和结果列表补齐，定向复测通过。
所有测试用 HTTP Mock；保留首次失败与补测日志，没有修改生产授权门禁。

## 原 Study、安全与版本接续

原 Study：`passive-mechanism-autonomy-20261104`，未创建后继 Study。
只读核验原暂停事件 510、原正式授权事件 359、全部 540 个 artifact 哈希和
133 个 Store/SDK 文件；与既有完整备份一致，没有新建第二套备份。
26 次 Provider 均结算，无 pending/unknown Worker，无待消费响应、未结算回执或资源占用。
原批准附件的字节哈希与保存的 directive 一致；scope 明确记录 Provider 端点、模型、
累计上限 48、每次最多 +8，以及非科学接口修复的版本接续许可。

首次在开发工作树调用正式 bind 前的 save，被原 check_root 以 AUTHORITY_ANCHOR_MISMATCH 拒绝，
发生在任何写入之前。原因是原授权索引归属于原执行工作树。随后将干净的原执行工作树
检出已提交版本，从原路径使用原 Store/共享授权库；没有复制授权库或绕过 check_root。

正式接续通过原 attached-authority 原子更新、formal_study_authorization、live_handoff_admission
与 core.bind 完成：

| 项目 | 之前 | 本轮接续后 |
|---|---|---|
| 执行 SHA | `8517772445741d7871a5b0c468249637e5688ce1` | `90e3e2a5ee96e1213eb5a2e73dc4208f58d8c46e` |
| resolved identity | `2c7105e30478c5bcb6cad3b37492e5b178a7c3932f723bbaf7cf31c911e496cc` | `b1ae07b461059d4d074407394dadcf78b5cedaa2b5b3aa7452101d8835e0b2ae` |
| 共享 Provider 总额 | 32 | 40 |
| 已用 / 剩余 | 26 / 6 | 26 / 14 |
| 保护收尾 | 4（总额内） | 4（总额内） |

科学 profile 始终为 `9f95b160c2aa80a89ca40d324d75fc33e660fd51a86f3fe6a65235cdc376dcd3`。
科学文件哈希、原评价器、任务、结构域、积分协议、候选、plans、数学/物理结果与累计费用保持。
数学累计预算为 null，单 Worker 180 秒、共享物理 256 episode / 128000 步、独立 Replay 16 次不变。
implementation_binding 保存旧/新实现关系；不把两个 SHA 冒充同一实现。

原 SDK restore_only 已成功，恢复原历史并通过 reconcile/trusted-history 路径，
最后已结算反馈没有重新消费或收费；恢复后仍无 unconsumed_response。
新发送前刷新工具 Schema 的实际 SDK Mock 回归通过；尚无本轮真实新 wire 可供远端接受核查。

## 真实运行与科研验收

原 SDK 的最多 1 次新请求入口在进程启动前被自动审批拒绝两次。
第二次提供原正式 scope 的端点/模型及原批准范围，自动审批仍认为这些工具读取记录不足以
替代用户对具体外部目标和敏感研究上下文的直接批准。已提出精确批准问题；没有绕行发送。
原 Store 已记录监督暂停，明确不是 Main 自主 STOP。

| 观察 | 本轮结果 |
|---|---|
| 真实 Provider 接受新 Schema | 未测，发送在进程启动前被拒绝 |
| 新 Main 语义读取 / 原始读取 | 0 / 0（新 Main 请求为 0） |
| 新的无效目录阅读或视图混用 | 无可观察的新请求；不能宣称问题已在真实模型上消失 |
| 新自主假设、数学请求或数学结果 | 无；原已登记假设保留，不冒充本轮成果 |
| 数学反馈进入后续决策 | 未测 |
| 结构修改 / 独立物理结果 | 无 |
| L1 / L2 / L3 / L4 | 本轮真实验证均未开展；离线接口通过不替代科研验收 |

未进入数学执行的直接原因是桌面外发审批阻断；目前没有新模型行动可用于归因。
不能把它归为 Main 不行动，也不能据此证明接口已完全满足真实科研需求。

## 累计账本与交付

原 Study 累计 Main 22、Reporter 4、共享 Provider 26、tokens 321492；数学评价、Worker、
rollout、模型构建、物理 episode、积分和独立 Replay 均为 0。
Provider/工具实际累计 wall_s=143.3760000001639，public operations=41；数值计算时间为 0。
Store 未保存可核实的货币账单，本轮不按当前价格反推历史实际货币费用。
新增 bind/restore/监督事件不产生 Provider、数学或积分消耗，历史失败和费用均保留。

源码提交：b0ce55a（Reporter 修复与新增测试）、6428496 / 90e3e2a（离线夹具合同补齐）。
本报告的后续文档提交不代表再次更换原 Study 的执行 SHA。
私有 Store、完整 wire、凭据、原批准全文、历史成功参数及本地恢复脚本均未随分支发布。
没有启动正式 PHS-2D/P3、没有合并 main。后续真实发送须先满足尚待的明确外发批准。
