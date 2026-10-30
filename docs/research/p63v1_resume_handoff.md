# P6.3 V1 用户暂停与后续接续说明

本文件是 Operator 交接记录，不自动进入 Main 的 Knowledge 或科研证据。
2026-10-30 用户明确要求暂时停止并整理 push；未经用户新指令不要恢复运行。

- 唯一 Store：`runs/research/p63v1-m3-autonomous-feasibility-sol-20261030`。
- SQLite 状态仍为 ready；运行器与监视器已停止，不是 Main STOP。
- Provider 已用 24/80，剩余总量 56（含原 protected reserve）；不能重置配额。
- 数学结果 94（84 computed、10 incomplete），独立 Replay 0，SELECT 0。
- 科学冻结提交 `c9a2280c39f9462d55c1aded145070cfbc9897a0`，evaluation profile v2。
- 原 SDK 会话 `rh-2211e6d503b92b992a7c947a`；快照身份在 `p63v1_user_pause.json`。
- 最近请求 24 与工具反馈均已封存，但暂停未再执行 handoff，不宣称 invocation 完成。

用户恢复后，先读原 Store/SDK 和近期回执，使用原恢复路径核对或补齐反馈边界，
不要重放已完成的科学动作，不要启动第二个 V1。先核对代码冻结/guard；如果文档
提交引起原绑定检查要求，按原 migrate 规则处理并记录 profile/依赖指纹，不能
直接改数据库冻结值或绕过门槛。生产科学配置、算法、评价器、阈值和模型不变。

原 `converse` 支持 `max_new_provider_requests`；只能在确认已用仍为 24、无新请求
之后把本次新请求上限设为 56，确保累计不超过 80。旧临时恢复脚本断言 21 次且
上限 59，已经不适用，不可直接重跑。原 CLI 位于 `tools/research/__main__.py`；
先查当前 Store 的恢复状态再决定原 restore/recovery 参数，不盲目启动。

第 24 次 Main 希望执行第三轮 search，但选择了 profile v1 旧候选，原准入返回
`OLD_EVALUATION_PROFILE_CANDIDATE_REQUIRES_NEW_CONSTRUCTION`，scientific_execution_started=false。
后续必须由 Main 自主满足当前 profile 的新构建与来源校验。Operator 不克隆旧候选、
不替 Main 选最佳解、不安排物理 Replay，不把旧两轮结果回写为当前 profile。

需要继续观察的事实：两轮完成动作可见于实际 Main 简短 Trace；最佳候选/J 未直接
展示给随后的 Main。通用 procedure 在服务端读取，但截至请求 24 完整正文交付
未确认。详细审计与报告包含这些限制，不应把 Main 的选择解释为已读过全部最佳证据。

完整本地运行备份、原 export 证据包、暂停审计和精确本地 Git bundle 随 outputs
交付。恢复前优先保留现存 Store 和快照；不要用 export 结果覆盖原运行目录。
