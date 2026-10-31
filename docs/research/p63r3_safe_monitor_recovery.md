# P6.3 R3：短连接监控与受控 Reporter 恢复

基线为 `d8a9c8a48a7f89169f57c1d335222736fe4d0c27`，独立分支
`codex/p6-3r3-safe-monitor-recovery`。已从 GitHub Git-data 原始元数据重建并验证
准确提交对象与父链，未用相同 tree 的其他提交冒充基线。

唯一原 Study 为 p63v1-m3-autonomous-feasibility-sol-20261030。准备时保持 32/80、
155 数学评价、3 轮搜索、Profile v3、独立 Replay/SELECT 0，原 unknown 请求和
科学冻结 b0f0faa 不变。用户本轮明确授权研究 Reporter-only 的本地工程放弃路径；
原响应仍不能恢复，不将本地处置描述成 Provider 取消或执行失败。

## 监控连接生命周期

原 p63r_live_audit 入口改为短观察，不再 runpy 嵌套全文审计。新 p63r3_monitor
每个 SELECT 使用 mode=ro、query_only=ON 和 contextlib.closing；fetchall 返回后
立即关闭连接，Python JSON 解析、分组、输出和等待均发生在关闭之后。没有显式
长事务，没有在运行期复制全文审计或 ZIP。观察是多个短读取，不冒充原子科学证书。
历史 p63v1_audit 的每次取数也显式关闭连接，去掉模块级 db/BEGIN；重审计仍只在
隔离副本或运行结束后使用。没有改 Store 数据库类型、数值算法或科研准入。

隔离并发回归使用独立监控进程，重复 5 轮 Reporter 与 Main Mock Provider 归档
（10 次虚构 Provider）、确定性 Reporter 保存和下一次 decision_packet 读取。
原响应 bytes 逐字核对、回执全部封口、无 database is locked；监控退出后可获得
BEGIN EXCLUSIVE；监控参数错误单独退出，不影响科研写入。2 项定向测试通过，
真实 Provider 和科学 Worker 均为 0，详见 p63r3_monitor_validation.json。

## 受控恢复进度

以下各阶段在原 Store/SDK 隔离副本验证前，不在真实 V1 上执行本地放弃或发送新请求。
后续补充严格反例、SDK/Mock wire、原账本保持与真实接续结果。

已实现 operator-only 的 abandon_unrecoverable_reporter_attempt，不注册为 Main 工具，
不自动调用。要求精确 Study/请求的本次用户授权、唯一 unknown Reporter、原响应缺失、
确定性基础报告、已封口科学结果、无活 Worker、无未消费响应、匹配原 science_delivery
边界的已配对 SDK 快照，且该未知调用是最后一次发送。事务中再次核对状态和唯一未封口
调用，通过原 Store.complete 以 cancelled 终结本地 reservation，保留 model_calls=1。
不创建 r3_response、HTTP 状态或解释文本；provider_outcome 仍 unknown，tokens/money
为未知。本地放弃事件和 receipt 输出精确保留授权、原 wire/base report 和范围声明。
重复执行只返回已存在的处置；Main 或其他 unknown 仍由原 pending 机制阻断。

17 项不同的相关离线测试已通过，覆盖并发监控、8 类恢复准入/反例、原 5 项证据门槛
以及两种 Mock 终局；后者明确检查 SELECT 写入 selected_solution 后自动 stopped，
失败 SELECT 被拒绝后由 Mock Main 使用完整索引合法 STOP。没有修改正式阈值或准入。
完整输入、关键断言、日志和结果见 p63r3_targeted_validation.json。

真实操作前备份已保存为 P63-R3-before-recovery.zip；逐字节核对当前 SQLite 与原归档
一致、全部 30 个 SDK 文件一致，freeze/profile/spec 一致。SHA-256、原 DB SHA 和原始
路径见 p63r3_pre_recovery_backup.json。当前真实 Study 仍未执行本地放弃；以下继续
验证完整隔离 SDK 恢复链路，只有通过后才允许按用户授权处置真实第 32 次请求。
