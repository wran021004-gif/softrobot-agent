# 原 Study 追加 10 次共享请求（2026-11-11）

用户明确要求“追加10次请求”。本批只将原 Study 的 Main/Reporter 共享上限从 140 增至 150，继续 Gateway 第三个账号、原模型和推理设置。所有历史授权、失败、成本、候选和证据保留，不重置账本，不授予未来批次。本次不 Push。

先完成当前科学计算和调用，并在 SDK request-feedback handoff 已 committed 的已结算边界停止原 launcher。通过既有 `extend_provider_requests` v2、committed bind、身份绑定正式授权与 SDK restore 追加并接续。逐项核对科学配置、profile、全部候选/结果、SDK session 和已用账本保留；绑定及 restore 不发验证推理。

复用原编排脚本 `budget_plus20.py before 140`、`apply 140`。该批精确使用 10 次增量，收据独立保存为 `budget-plus10-total150-*`，原 20 次批次行为及文件名保持不变。
