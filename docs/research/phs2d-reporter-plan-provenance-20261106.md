# Reporter 的 Plan 谱系材料接口修复

在原 `phs2d-topology-successor-20261106` window010 中，Main 第 28、29 次请求先后询问
candidate_5 → plan_3 → candidate_382 的精确谱系和完整参数差异，以判断十工况独立 Replay 是否有信息价值。
两次都将本 Study 的 plan_3 与候选和结果放入 investigation references。
旧接口只接受候选、科学结果和报告作为 ResultCard，因 Plan 不在该集合而拒绝，
但反馈只返回 `INVESTIGATION_SUBJECT_NOT_REGISTERED_IN_STUDY`，未说明哪条引用不合适。
Main 改变 subject 后重试，仍被同一条件拒绝。原始工具请求、失败反馈和两次 Provider 费用保留。

window010 在 30/64 正常有限窗口边界结束，没有 pending、未消费响应、未结算回执或运行副本，
才进行本次修复。没有新的数学/物理结果或独立验收；原候选和科学计划不变。

修复复用现有 InvestigationRequest/EvidenceQuery/ResultCard：

- 只有精确出现在当前 Study `state.plans` 中的 Plan 才识别为谱系材料。
- 从主 ResultCard 引用中取出这些 Plan，追加原始 `/original_plan` 只读查询，并在保存的请求中记录支持材料引用。
- 已有相同查询不重复追加；没有显式 reads 时，保留原候选的自动 structure/task 主题。
- Plan 不产生科学 ResultCard、指标、正式阅读信用或任务验收。
- 仅有 Plan 而没有候选/结果的调查明确拒绝；未登记或外来 Plan 仍被原 allowlist 拒绝。
- 原始模型输入不改写；不包含 Plan 的既有请求不增加新字段。

定向测试覆盖以上边界，并检查原语义查询、引用目录和 Reporter→Main 交付路径。
新增测试最初的冻结模型赋值和 fixture 适配问题在离线回归中发现并修正；未修改正式 Store。
3 项定向测试通过（新增谱系边界测试、既有显式/自动查询测试和完整 Reporter→Main 交付测试）。
保留原工具 schema，避免当前 Handoff 的已承诺工具身份因无关描述变化而改变。
绑定和继续执行状态在完成后追加。
