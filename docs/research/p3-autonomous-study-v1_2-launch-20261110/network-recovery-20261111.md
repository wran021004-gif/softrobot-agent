# 原 Study 网络中断恢复（2026-11-11）

状态核验发现原 launcher 已因第 109 次请求返回 Gateway HTTP 502、`network_error`、`retryable=true` 而退出。Store 的 `ready` 不代表进程仍在运行。原失败已结算，无 pending 科学计算、未消费响应或未结算调用；保留该次成本，原总额 120、已用 109、剩余 11。

在用户持续授权的原研究与剩余额度内，先只读核验第三账号模型目录，确认原 gpt-5.6-sol 可用，再通过原 launcher 恢复同一 SDK session 和 Store。没有更改代码、配置、物理、验收或预算，没有新建 Study，也没有发送验证推理。

恢复请求 `r3-request-1005a1855d0948ff945ee281784b5562` 已真实返回 HTTP 200 / tool_calls，Main 随后完成一次生成操作并保存交接。恢复核验时共有 30 个候选、57 次数学评价记录、41 条分析；总请求已用 110/120、剩余 10，仍没有正式任务验收、SELECT 或独立 Replay。[实际收据](network-recovery-20261111.json) 与原 Store 保留本次成本和状态。原旧 Study 状态和账本再次核对不变。研究继续后台运行，本次不 Push。
