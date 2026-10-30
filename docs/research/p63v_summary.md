# P6.3 V0/V1 暂停交付总结

2026-10-30，按用户“先暂时停止这次 study，整理 push”的新指令暂停 V1。
研究没有自行结束；不把这次暂停算作 Main STOP、预算耗尽或正式成功。

| 项目 | V0 独立复验 | V1 空白自主 Study |
|---|---|---|
| 归属 | Operator 对 G3 旧解精确复验 | 本轮 Main 新结构—控制研究 |
| Provider | 0 | 24/80：Main 14，Reporter 10 |
| 数学结果 | 使用原数学解作只读比对 | 94：84 computed，10 incomplete |
| 独立物理 Replay | 1 次 | 0 次 |
| 结果 | 严格 valid_failure | 数学改进已见，尚未独立验收 |
| SELECT | 无 | 无 |

V0 在完整 0.5 s 任务与最后 0.05 s 保持窗口上，保持速度为
0.020000000000629993 m/s，超过原 0.02 m/s 限值 6.299925858765931e-13。
位置通过，完整与数值有效性通过；不改阈值、不重复复验。与原数学保存样本对齐
后，位置、速度、张力最大差异均为 0，故并非观察到模型与复验轨迹分离。

V1 两轮合法联合搜索由 Main 自主执行，第一轮最优模型 J=-0.014355323230259676，
第二轮为 -0.0069635885347172355。两轮都不是全局最优或独立通过证明。
数值账本 3372.6726571998443 s；已报告的 Native 内部计数为 32410 rollouts、
32410000 steps；10 次 incomplete 的内部细分未知而非零。
Provider tokens 为 207944（prompt 198250 / completion 9694），货币费用未知。

真实 SQLite handoff 自锁用冻结原代码复现；只修复 Store.events 和交接反馈读取
对同一写事务连接的复用。两个直接相关离线测试通过，未额外运行科研。
原 migrate 创建 profile v2，保留旧结果与成本。修复后同一 Study 恢复成功，
请求 22 检索经验，23 读取通用 procedure，24 提出新搜索，但因引用旧 profile
候选被原准入拒绝，未启动第三轮计算。暂停时无 pending 或未封存调用。

实际 Main 简短 trace 仍有中断前两轮 completed 搜索，最佳候选及最佳 J 未直接
出现在随后的 Main wire；完整搜索引用仍可读取。经验正文服务端读取已完成，
截至请求 24 尚未确认完整正文交付；不能声称已阅读/理解最佳解或经验正文。

全部原始 Store、SDK 会话、轨迹和回执保留，另提供完整运行备份、原证据 export、
暂停审计及 Git bundle。V1 保持 ready，进程停止，剩余总请求 56；恢复需用户指令，
只能原 Study、原预算接续，先走原 SDK/反馈恢复和 profile 校验。

详细文件：p63v0_independent_replay.md、p63v1_autonomous_study.md、
p63v1_pause_audit.json、p63v1_pause_trace_audit.json、p63v1_user_pause.json、
p63v1_lock_repair_audit.json、p63v_final_checks.json。
