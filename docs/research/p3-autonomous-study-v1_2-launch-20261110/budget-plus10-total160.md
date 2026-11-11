# 原 Study 追加 10 次共享请求至 160（2026-11-11）

用户明确要求“追加10次study”。本批仅将同一 Study 的 Main/Reporter 共享上限从 150 增至 160，继续 Gateway 第三个账号及原模型、推理设置。全部历史授权、费用、失败、候选和证据保留，不重置账本，不授予未来批次。本次不 Push。

使用既有 `extend_provider_requests` v2、committed bind、身份绑定正式授权和 SDK restore；当前调用/计算结算，并在 SDK request-feedback handoff 已 committed 后停止原 launcher。科学配置、profile、候选/结果、原 SDK session 与已用账本逐项核对，绑定及 restore 不发送推理。

复用 `budget_plus20.py before 150`、`apply 150`；本批收据独立保存为 `budget-plus10-total160-*`。

用户同时询问是否已取得合格机制证据。11:30 只读核验时，最新两条成对机制诊断仍为 exploration/sampled，返回 `COMPLETE_QUALIFICATION_GRID_REQUIRED`，双向 paired_mechanism 均为 UNKNOWN。采样性能通过不能授予合格机制证据；当时没有独立 Replay 或任务验收通过。本次预算授权不改变这些历史科学结论。
