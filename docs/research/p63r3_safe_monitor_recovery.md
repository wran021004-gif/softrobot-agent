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
