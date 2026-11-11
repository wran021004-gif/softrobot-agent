# 原 Study 第三次追加 20 次共享请求（2026-11-11）

用户明确要求“增加20次请求”。本批将原 Study 的 Main/Reporter 共享请求总上限从 120 增至 140，继续 Gateway 第三个账号和原模型/推理设置。原先两批扩展、所有历史成本、失败、候选和科学证据保留，不授予后续批次。本次不 Push。

待当前科学计算、报告及 Provider 请求结算，在 SDK request-feedback handoff 已 committed 的边界停止原 launcher。使用原 `extend_provider_requests` v2、committed bind、身份绑定正式授权及 SDK restore；逐项核对科学配置、profile、候选/结果、原 SDK session 和已用账本完全保留，只增加 20 次有限额度。绑定与 restore 不发送验证推理。

使用原编排脚本 `budget_plus20.py before 120` 与 `apply 120`；本批独立快照和收据为 `budget-plus20-total140-*`，不覆盖既有批次。

## 扩展核验

[绑定收据](budget-plus20-total140-bound.json) 确认原总额 120 增至 140，扩展前后已用请求均为 112、剩余由 8 增至 28。全部工具、计算和时间成本保持一致，科学配置、profile、候选/结果集合、第三账号传输和原 SDK session 不变量核对通过。SDK restore 成功，扩展及 restore 没有发送推理。绑定实现为 `e228c381e`。随后通过原 launcher 恢复后台研究，后续请求继续计入原共享总账本。
