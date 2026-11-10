# 2026-11-10：工具 Schema 修复与原 Study 恢复

故障发生在第 28 次实际 Provider 请求。原始响应为 HTTP 502、`invalid_function_parameters`、`param=tools`；失败请求已结算，费用保留，剩余 52/80。此时无运行中 Worker、未结算请求或未消费的成功响应。

只读检查原始请求可复现具体错误：`research_plan` 的 `$defs/ScientificStructureSearch/required` 中重复出现 `screening_fidelity`。v1.2 有两个 Screening 选择时，重复代码连续追加同一字段，违反 JSON Schema 的 uniqueItems 规则。其他六个工具的原始 Schema 均有效。不是物理失败、时间预算或上下文超限。

修复删除重复 Schema 构造，并在实际 Provider 传输边界、费用预留和发送之前检查最终工具 Schema。历史响应恢复仍优先使用原始请求，不重写失败记录。另删除重复提示，并让 Main 看到冻结 Fidelity 名称、合法阶段及完整验收的字段约束；错误反馈附上同一合同，避免将自然语言描述误填为 Fidelity 名称、将探索记录选项附在 `final_acceptance` 上。没有自动修改 Main 的研究选择，也没有放宽物理判据。

仅运行 `tests.research.test_p3_schema_recovery` 的三项定向回归，全部通过：多 Fidelity 全量/聚焦工具 Schema、执行范围与原 Worker 准入一致、非法最终 Schema 在发送和扣费前拦截。离线阶段无 Provider 请求、新物理积分或高精度实验。

[恢复前快照](schema-recovery-before.json) 保留原冻结配置、科研 profile、候选/Plan/结果集合、原账本、原失败 wire/响应/receipt 身份及旧 Study 摘要。修复先本地提交，再通过原 `core.bind` 做说明明确的实现迁移；任务、FamilySpace、Knowledge、80 次额度、2-cell 正式验收与原科学结果不迁移。离线 SDK restore 验证通过后，使用原会话和剩余额度恢复真实 Main。绑定、恢复及真实新响应的核验另记恢复收据；不 Push。
