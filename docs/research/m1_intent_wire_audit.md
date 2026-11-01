# M1 42 次真实请求链路审计

逐条读取原 Store 的 r3_request、实际序列化 wire、r3_response 和配对工具反馈。SQLite 使用 mode=ro/query_only；两轮数据库读取前后 SHA-256 一致。表中数学 Worker 指正式进入原计算入口，Reporter 单独标明；仅 HTTP 200 不算科学行动。

确认：9 次 V4 错误均收到正确嵌套 Schema，下一次 Main wire 的 pending_feedback 按 tool_id 精确交付原拒绝内容。Handoff 没有吞掉这 9 次反馈。3 次非法生成是 Schema 未投影原冻结 base-only 约束；2 次结构请求在 Schema 合法后才被编译器以语义不适用拒绝。来源缺失的两次拒绝属真实前提不足。不能将这些情况统一归责于模型。

未在相关实际 wire 发现 scientific_question_v2 或旧版示例。额外根字段本身属于当前结构子对象或 Plan 契约，但无法仅凭记录确定模型为何把它们移到根层。

| 请求 | 阶段 | Main 实际动作 | Schema | 执行/拒绝 | 数学/积分步 | 下一次 Main |
|---:|---|---|---|---|---|---|
| 1 | exploration | experience_retrieve read | 合法 | success | 0 / 0 | 2：research_plan generate |
| 2 | exploration | research_plan generate | 合法 | BASE_ONLY_REQUIRES_FIRST_SEGMENT_ZERO | 0 / 0 | 3：research_plan generate |
| 3 | exploration | research_plan generate | 合法 | BASE_ONLY_REQUIRES_FIRST_SEGMENT_ZERO | 0 / 0 | 4：research_plan generate |
| 4 | exploration | research_plan generate | 合法 | BASE_ONLY_REQUIRES_FIRST_SEGMENT_ZERO | 0 / 0 | 5：research_plan generate |
| 5 | exploration | research_plan generate | 合法 | generated | 0 / 0 | 6：evidence_read |
| 6 | exploration | evidence_read | 合法 | raw_result_not_delivered | 0 / 0 | 7：experience_retrieve |
| 7 | exploration | experience_retrieve read | 合法 | success | 0 / 0 | 8：research_plan diagnose |
| 8 | exploration | research_plan diagnose | 不合法 | Additional properties are not allowed ('selected_candidate' was unexpected) | 0 / 0 | 9：research_plan diagnose |
| 9 | exploration | research_plan diagnose | 合法 | read_only_diagnosis | 0 / 0 | 10：evidence_read |
| 10 | exploration | evidence_read | 合法 | raw_result_not_delivered | 0 / 0 | 11：research_analysis control |
| 11 | exploration | research_analysis control | 合法 | COMPLETE_LEGAL_CONTROL_SOURCE_REQUIRED | 0 / 0 | 12：experience_retrieve |
| 12 | exploration | experience_retrieve read | 合法 | success | 0 / 0 | 13：research_analysis control |
| 13 | exploration | research_analysis control | 合法 | COMPLETE_LEGAL_CONTROL_SOURCE_REQUIRED | 0 / 0 | 14：evidence_read |
| 14 | exploration | evidence_read | 合法 | success | 0 / 0 | 15：experience_retrieve |
| 15 | exploration | experience_retrieve read | 合法 | success | 0 / 0 | 16：evidence_read |
| 16 | exploration | evidence_read | 合法 | success | 0 / 0 | 17：research_route initialize_control |
| 17 | exploration | research_route initialize_control | 合法 | success | 0 / 0 | 18：research_plan initialize_control |
| 18 | exploration | research_plan initialize_control | 合法 | success | 0 / 0 | 19：research_plan initialize_control |
| 19 | exploration | research_plan initialize_control | 合法 | success | 0 / 0 | 20：research_plan initialize_control |
| 20 | exploration | research_plan initialize_control | 合法 | success | 0 / 0 | 21：evidence_read |
| 21 | exploration | evidence_read | 合法 | success | 0 / 0 | 22：research_route diagnose |
| 22 | exploration | research_route diagnose | 合法 | success | 0 / 0 | 23：research_plan diagnose |
| 23 | exploration | research_plan diagnose | 不合法 | Additional properties are not allowed ('selected_candidate' was unexpected) | 0 / 0 | 24：research_plan diagnose |
| 24 | exploration | research_plan diagnose | 合法 | read_only_diagnosis | 0 / 0 | 25：research_analysis control |
| 25 | exploration | research_analysis control | 合法 | Native T1 完成；预测未达标；独立验收未测 | 1 / 19200 | 27：research_plan diagnose |
| 26 | exploration | Reporter | 无工具调用 | Reporter 完成 | 0 / 0 | 27：research_plan diagnose |
| 27 | exploration | research_plan diagnose | 合法 | read_only_diagnosis | 0 / 0 | 28：research_analysis structure |
| 28 | exploration | research_analysis structure | 不合法 | INVALID_SCIENTIFIC_V4_INPUT | 0 / 0 | 29：research_analysis structure |
| 29 | exploration | research_analysis structure | 不合法 | INVALID_SCIENTIFIC_V4_INPUT | 0 / 0 | 30：experience_retrieve |
| 30 | exploration | experience_retrieve read | 合法 | success | 0 / 0 | 31：research_analysis structure |
| 31 | exploration | research_analysis structure | 不合法 | INVALID_SCIENTIFIC_V4_INPUT | 0 / 0 | 32：research_analysis structure |
| 32 | exploration | research_analysis structure | 不合法 | INVALID_SCIENTIFIC_V4_INPUT | 0 / 0 | 33：research_analysis structure |
| 33 | exploration | research_analysis structure | 不合法 | INVALID_SCIENTIFIC_V4_INPUT | 0 / 0 | 34：research_analysis structure |
| 34 | exploration | research_analysis structure | 不合法 | INVALID_SCIENTIFIC_V4_INPUT | 0 / 0 | 35：research_analysis structure |
| 35 | exploration | research_analysis structure | 不合法 | INVALID_SCIENTIFIC_V4_INPUT | 0 / 0 | 36：research_analysis structure |
| 36 | exploration | research_analysis structure | 不合法 | INVALID_SCIENTIFIC_V4_INPUT | 0 / 0 | 37：research_analysis structure |
| 37 | exploration | research_analysis structure | 合法 | M2_REQUIRES_REGISTERED_TASK_CONSTRAINT_OR_TASK_VIOLATION | 0 / 0 | 38：research_analysis structure |
| 38 | exploration | research_analysis structure | 不合法 | INVALID_SCIENTIFIC_V4_INPUT | 0 / 0 | 39：research_analysis structure |
| 39 | exploration | research_analysis structure | 合法 | M2_REQUIRES_REGISTERED_TASK_CONSTRAINT_OR_TASK_VIOLATION | 0 / 0 | 40：evidence_read |
| 40 | closeout | evidence_read | 合法 | success | 0 / 0 | 41：evidence_read |
| 41 | closeout | evidence_read | 合法 | raw_result_not_delivered | 0 / 0 | 42：research_plan stop |
| 42 | closeout | research_plan stop | 合法 | success | 0 / 0 | —：结束 |

每次请求的完整当前假设、科学选择、实际核心参数、工具列表、动态 Schema 身份、字段级拒绝、Provider tokens/耗时、下一轮动作及原证据引用见 m1-interface-request-audit.json。

本轮 42 次包含 41 次 Main 和 1 次 Reporter，全部 HTTP 200；成功响应 513,879 tokens。数学 1 次、Native 32 回调/16 迭代/19,200 积分步、独立 Replay 0。首次基础设施失败另有 1 次 HTTP 400 和工程 STOP，未抹去或退费。金额未知。

这份审计识别了接口投影、方法发现和意图交接问题，也保留模型在正确 Schema/反馈下仍重复出错的事实；没有证明任一单项修复就能获得自主科研成功。
