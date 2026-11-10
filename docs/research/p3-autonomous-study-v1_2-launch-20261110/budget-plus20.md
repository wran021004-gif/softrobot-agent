# 原 Study 增加 20 次共享请求（2026-11-10）

用户明确要求“增加20次请求预算”。此次使用既有 `extend_provider_requests` 的精确有限 v2 授权，将同一 Study 的 Main/Reporter 共享总限额从 80 增至 100。历史已用请求、失败和成本保留，不退款、不重置，不授予后续批次。继续 Gateway 第三个账号、原模型和推理设置，科学任务、物理阈值、候选和证据均不变。本次不 Push。

先在无在途 Provider 或科学计算、SDK request-feedback handoff 已 committed 的边界停止原 launcher，再保存前置快照、提交、通过原 Store 预算扩展、committed bind、身份绑定正式授权和 SDK restore 接续。编排脚本逐项核对仅请求上限改变，已用成本、科学配置、profile、结果集合和 SDK session 不变量保留。绑定与 restore 不发送测试推理；接续后的实际费用继续写入原账本。
