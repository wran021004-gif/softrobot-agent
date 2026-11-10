# 原 Study 第二次追加 20 次共享请求（2026-11-10）

用户明确要求“study的请求预算可以追加20”。本批将同一 Study 的 Main/Reporter 共享总限额从 100 增至 120，继续 Gateway 第三个账号、原模型和推理设置。第一批 80 到 100 的授权、收据和历史成本保留，本批不重用第一批授权，不授予后续批次。本次不 Push。

复用原 `extend_provider_requests` v2、committed bind、身份绑定正式授权和 SDK restore。先让当前科学计算及报告结算，并在 SDK 已提交的交接点停止原 launcher，再保存本批独立前置快照和授权。逐项核对已用账本、科学配置、profile、候选/结果集合及 SDK session 不变量；仅共享请求上限增加 20。绑定及 restore 不发送验证推理。

`budget_plus20.py before 100` 与 `apply 100` 使用本批独立的 `budget-plus20-total120-*` 收据，原第一批文件不覆盖。具体实际已用和剩余额度在结算后记录。

## 实际扩展核验

[绑定收据](budget-plus20-total120-bound.json) 确认总上限 100 到 120，扩展前后已用请求均为 94，剩余从 6 增至 26；历史工具、计算和时间成本全部相等。科学配置、profile、候选/结果集合、第三账号传输及 SDK session 不变量通过，SDK restore 成功，扩展及 restore 没有发起推理。执行绑定为 `edaa2dda3`。随后通过原 launcher 恢复后台研究，后续费用继续写入同一共享账本。
