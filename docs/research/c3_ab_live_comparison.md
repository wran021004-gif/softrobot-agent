# C3 A/B 真实准入与对比记录

2026-10-25；起点 `f62a6c40cc831fa005771f046449e861c30a0377`，专用分支
`feat/c3-math-search-readiness`。用户本次指令授权独立准入后自动顺序运行 A/B；
不增加任何额度，不导入工程预检或旧 C3 科学答案。共同条件见 `c3_ab_protocol.md`。

首次门禁复用现有状态：A 在首个合法 `generate` 前仅允许生成/诊断/STOP，
非法生成不解除门禁；B 在首个有支持的任务 CONIC 搜索候选前保持搜索/诊断/STOP。
L0、Plan Schema 与执行使用同一个判定。取得首个候选后开放共同能力。

短轨迹保留初始路线、首次结构/数学/物理/控制节点及最近三项，最多八项，
只呈现动作、状态、结果和原 Store 来源，不推断因果。最近假设三字段各取原文
最多 240 字符，明确标为摘录，并保留完整 Plan 指针；Reporter 不改写动机。

| 旧 C3 请求边界 | 原完整请求 bytes | 新 Handoff 离线投影 bytes | 轨迹节点 | 最近原始假设 |
|---|---:|---:|---:|---|
| 1 | 84,965 | 77,372 | 0 | 尚无 Plan |
| 13 | 332,894 | 104,698 | 6 | 可见 |
| 25 | 639,373 | 95,536 | 7 | 可见 |

这里只是原存档的离线完整 wire 投影，使用本地 tokenizer，不是新的 Provider 用量。
历史 reasoning 未放回新会话；原 Store 历史仍可查询。STOP、SELECT、原预算字段、
独立验收及 Reporter 非权威地位不变。

原 `converse` 增加 `--restore-only`：沿原 reconcile/trusted-history/反馈恢复入口核对
SDK 与 Store 后返回，不启动新 Provider 请求；不另建会话管理。
定向检查覆盖 A 非法重试/解除门禁、B 两格成本/解除门禁、共同配置、
真实 SDK mock HTTP 切换后无发送恢复，均通过。实际 Worker/HTTP 准入尚待执行。
