# PHS-2D 上下文读取与 Handoff 性能修复

本修复继续同一个 `phs2d-topology-successor-20261106` Store，保留原始任务、物理模型、
FamilySpace、Knowledge、科学资格和累计费用。修复期间没有实际 Provider 预演或数值 Worker。
第 17 次正式请求已明确收到 HTTP 502 `network_error`、`retryable=true` 并计费结算；
没有未知外发结果或 pending Worker。完成修复后从原恢复入口继续，不删除或重置该失败。

## 确认的瓶颈

原始动态数学结果约 565 MB。一次标量投影约 2.25 s；五个缺失字段约 9.82 s。
不同字段集反复取整块 BLOB、校验、解析；缺失字段还逐个调用 json_type。
原 request-local cache 能复用相同字段，却不能复用另一组字段的解析结果。

真实 Store 的一次只读 cProfile 基线耗时 294.925 s，约 9.49 亿函数调用；
累计约 192.7 s 落在深拷贝，约 78.2 s 落在 SQLite execute。
这些累计项存在调用嵌套，不能相加当成独立成本。
此外，recent-round Handoff 在完整构造一次不会发送的 packet 后才切换，
新 SDK 会话再次构造同一科研视图。

## 最小修改

1. Store 的投影在原 `read_snapshot` 作用域内复用已校验 JSONB。
   JSONB 只在内存中使用，原 artifact、hash、raw bytes 和路径语义不变。
   值和类型在一次 SQL 中提取，保留缺失／null、布尔、数字、数组和 JSON Pointer 转义。
   DB commit 仍使原 snapshot cache 失效；显式写事务始终重新校验，不能借缓存掩盖未提交篡改。
2. recent-round 的已结算成对反馈在构造 packet 前执行现有 Handoff。
   原配对、独立 snapshot 恢复验证、未消费响应和预算暂停检查保留。
   Mock SDK 验证每个实际发送请求只构造一次 packet，而不是 Handoff 前后各一次。
3. 无载资格复查改读 qualification、method 和 candidate；旧记录仍经原始精确指针读取。
   Knowledge 的有限搜索触发检查先查是否实际存在 Native search，避免加载被动动态轨迹。
   mechanism scope 摘要只读原 claim 与实际数值根节点，避免读取与该摘要无关的样本。
4. 原 bind 增加显式 `store_io_only=True` 的已审查迁移选项，默认保持保守行为。
   仅 Store 源 hash 更新且其余依赖声明、源码集合、科学源码、软件包、环境均不变时，
   才保留科学 profile；所有依赖指纹仍更新并记录。其他物理／依赖变化仍触发原 profile 迁移。

使用现有 Python 环境的 SQLite 3.53.2；JSONB API 需要 SQLite 3.45 及以上。
未安装库，未引入另一套 Store、Worker、知识或状态管理系统。
完整原始读取仍可用；内存缓存随读取作用域结束释放，未持久化压缩或删改原始数据。

## 定向验证

新增测试覆盖：不同字段共享一次校验／解析、返回副本与原始 bytes、作用域退出后的重新校验、
显式写事务篡改检测、缺失与 null、JSON Pointer 数字键与转义、
机制证据 scope 与完整读取一致、纯 Store I/O 迁移不掩盖其他依赖变化、
Handoff 构造次数和预算暂停发生在下一次发送之前。
原有投影完整性和跨候选资格／STOP 复查测试也通过。
SDK 响应均为离线 fixture，不是正式科研证据。

真实 Store 的完整科研 packet 按 JSON 序列化比较，而不是比较 Python tuple/list 容器类型；
初次比对发现的 tuple/list 差异不改变实际 wire。最终视图内容一致，
只读对照中的 Store 事件数与账本均未变化。
性能标量和最终串行对照见随提交保存的 evidence；完整 packet、profile 和原始数据留在本地。

串行、无 profiler、同 Store 与同 registry 的对照为 **146.626 s → 46.254 s（3.17 倍）**。
这是单次工作视图构造的本机测量，不是求解器或完整研究速度的保证。
额外 Handoff 构造的消除由 SDK 测试验证，不将两项收益直接相乘作端到端实测。
首个标量仍需首次校验与解析（本次 2.319 s）；之后另一标量 0.145 s，
五个缺失字段从先前约 9.817 s 降至 0.146 s。
摘要指标见 [summary.json](../../evidence/phs2d_context_performance_20261106/summary.json)。

共 6 个新增定向测试及 3 个既有投影／资格测试通过。旧 tempfile fixture 在当前 Windows
沙箱下无法访问新建临时目录，改由现有 workspace fixture_directory 执行原投影测试；
未扩大权限或修改正式 Store 来使测试通过。另一个早期 SDK fixture 依赖 MATLAB，
替换为现有 PHS 被动 fixture 后通过。未重跑完整工程套件。

## 监督与继续执行

已按用户要求启用每 5 分钟同聊天 heartbeat，自动化 id 为 `phs-2d-5`。
检查 Plan／候选／结果／Reporter／Main 决策绑定、实际进展、异常与预算，
避免重复进程；仅关键变化、问题、完成或需用户处理时通知。
确认接口问题后在结算边界最小修复，科学失败保留，不降低阈值或替 Main 选研究路线。

监督发现并保留了一处解释纠正：s3～s7 是 material_s=0.3～0.7 的加载位置，
十工况施力幅值均为 0.1 N，并非力大小递增。该事实已通过原 operator_request 入口记录，
恢复后随原任务来源提供给 Main；不改原历史解释或科学数据。

修复已绑定到 `07631cb05bf313f7317795b3dd94a387d45ced85`。
原 resolved identity `560ac79e6f82f9367359fa941ea47cb29e3a35125b916f2eff15a319f8fe5111`、
科学 profile、pilot/Handoff 和完整账本逐项比较均保持不变；授权与 guard 通过。
纯 Store I/O 指纹更新保留了七个相关依赖的精确记录，未标为物理模型变化。
原恢复入口已验证第 17 次已结算的失败初始请求，window006 继续同一 Study。

window006 的真实恢复检查：07:56:45 UTC 完成旧失败入口验证，07:57:35 构造完 packet，
07:57:36 发出第 18 次请求。实际 wire 为 gateway `gpt-5.6-sol`、单一 packet，包含加载位置纠正。
07:57:49 再次收到相同可重试 HTTP 502；失败已结算。科研状态仍为 ready，数学评价 3、
候选 1，没有 pending、未消费响应或未知请求；这不是 Main STOP。
当前问题是 Gateway 无法连通上游 ChatGPT。监督保持每 5 分钟启用，但不继续循环收费重试；
先检查日志／服务／连通性，有新恢复证据或用户告知恢复后才从原入口继续。
health/models 的本地 HTTP 200 本身不证明上游恢复，未更换账户、模型或付费路径。
