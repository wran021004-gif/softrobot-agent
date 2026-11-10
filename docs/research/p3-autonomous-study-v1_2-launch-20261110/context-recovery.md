# 通用上下文投影修复与原 Study 恢复（2026-11-10）

本次故障来自通用 Main 状态包投影，不是 P3 专用求解器。原请求反馈交接已成功，随后重建的 L0 又携带多份完整、重复的资格诊断。第 694 个事件的状态包为 916,618 bytes，其中五份 verified_facts 约占 593 KB；重复的最坏约束行、资格矩阵和历史轨迹再次放大请求。实际传输前触发 `R3_CONTEXT_CAPACITY_EXCEEDED_CONSERVATIVE_UTF8_ESTIMATE`，被 SDK 外层包装成 `APIConnectionError`。本次被拒绝的请求没有发送或扣费，原账本为 35/80、剩余 45。

修复只修改通用呈现与错误分类：

- `research_context.compact_result_diagnostics` 复用已有 compact_task_diagnosis，保留全部约束的已知/未知值、阈值、时间窗口、单位、逐腱 observable、资格测量及正式可比性；最坏约束保留 ID，重复资格矩阵由同一对象内的事实入口引用。
- `object_choices.main_packet` 在当前结果、verified_facts 和历史轨迹中使用这一投影。历史轨迹保留所有指标摘要、执行状态和精确读取入口；完整组件、资格窗口、原始结果及报告保持在原 Store。未改写 SDK 原消息、原始证据或验收证书；待交付的 exact certificate 反馈不被本次投影裁剪。
- `ProviderCapacityError` 使本地容量拒绝穿过 SDK 连接错误包装后仍保留真实分类。原请求字节上限、上下文限制、输出预留、预算及实际发送计费规则均不改变。

没有 Task ID 判断、P3 专用分支、新 Agent、额外预算、物理判据放宽或重算旧实验。实现迁移通过原 core.bind 完成，要求冻结配置、科学 profile、候选/Plan/结果集合及账本在恢复前逐项相等。

离线验证：5 项新增通用定向测试全部通过，涵盖完整组成事实与 UNKNOWN、异源资格不合并、待交付完整证书不裁剪、SDK 容量错误分类、拒绝前无发送/扣费。另尝试的 3 项旧 fixture 回归因当前解释器缺少可选 `matlab.engine` 而未进入测试主体；没有安装 MATLAB，也未将其报告为通过。

[恢复前快照](context-recovery-before.json) 记录对真实旧状态包的只读回归：状态包压缩到 **475,295 bytes**；使用相同旧 system/tools、干净调用及新 L0 重构的请求为 **577,544 bytes**，通过原容量保护。该数值是离线重构，不是 Provider 实测 token 数或原未发送请求的精确副本。逐项核对真实约束数值、UNKNOWN、窗口、阈值、observable、覆盖及资格测量不变，原始 packet 身份不变。离线期间 Provider 与新积分均为零。

原 Study 继续使用 `p3-passive-progressive-stiffness-autonomous-20261110-v1_2`、原 Store 及原总额度。先提交修复、绑定并离线验证 SDK，再恢复真实 Main；恢复后的实际 wire、HTTP 响应、原账本和状态保留情况见后续恢复收据。此次不 Push。
