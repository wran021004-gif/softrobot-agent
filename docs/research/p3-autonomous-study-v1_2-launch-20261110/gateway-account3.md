# 原 Study 切换 Gateway 第三个账号（2026-11-10）

用户明确要求“切换成gateway第三个账号继续study”。使用既有第三账号独立 DPAPI 状态、现有 Gateway runtime、`127.0.0.1:8789` 及独立本地凭据引用；其他账号服务不变。保留 gpt-5.6-sol、原 Main/Reporter 推理设置、Study、SDK session、所有科学要求、候选、结果、历史失败及已用费用。原共享 80 次 Provider 总预算不重置。本次不 Push。

原 launcher 只在没有在途 Provider、没有 pending 科学计算、没有未消费响应，且 SDK request-feedback handoff 已 committed 时停止。原始 Store 保留切换边界记录。之后通过既有 `transition_transport`、`core.bind`、身份授权和 SDK restore 接续。

通用迁移入口此前将 Gateway 端口写死为 8787。本次允许精确授权范围中的 IPv4 loopback HTTP `/v1` 实例，继续拒绝远程地址、凭据 URL、查询、fragment、非法端口及模型/研究设置变化。技术交接证明可在相同 Gateway 协议的本地实例间复用；它不证明账号额度或可用性，第三账号仍需独立凭据绑定和只读模型目录检查，实际推理收据另行记录。原模型、推理、HTTP 200、请求哈希、SDK restore、工具 ID 和 exact feedback 交接核验保留。

三项定向测试全部通过，覆盖原 Chat/Responses 路径、Responses 原始收据与派生消息一致性、本地多实例协议证明和非法地址拒绝。第三账号 authenticated GET `/v1/models` 确认精确模型可用，未发验证推理。切换边界为总账本已用 61/80、剩余 19；[前置快照](gateway-account3-before.json) 保存原科学不变量和账本。
