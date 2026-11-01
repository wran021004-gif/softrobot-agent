# U1/U2 通用任务适配

开发基线 `a73981c12a6212b5201c297f52d52d1c27f05d40`，独立分支
`codex/u1-u2-general-task-adaptation`。2026-11-01 核对远端 HEAD：
`main@2a854280db69425dc50af9012b8da52194a679ee`；R0 分支仍为开发基线。
本轮遵循 R0 九任务审计及其真实历史来源口径；未重跑历史搜索。

## U1

V4 的 `control_feasibility` 从当前候选的 `mathematical_method_view` 选择已授权、
模型/任务适用且有预算的方法。Reach/Hold 保留原默认 T1；Tracking、位置与工具轴、
带载有向 Tracking 可选择原 Direct。显式 `numerical_method` 可表达目录中的科学选择；
被阻断的 Reach/Hold T1 不会被自动换成另一身份。方法选择仍只是编译，原
AnalysisRequest、dispatch、Worker 和累计预算执行最终准入。

| 当前任务族 | V4 默认数值身份 | T1/T2 | 物理成功依据 |
|---|---|---|---|
| Reach/Hold（含合法 COM 外力） | T1，原有限预算 J 解释 | 保留原 T1 / 可比较已保存 T1 的 T2 | 原独立 Replay 全 acceptance |
| timed Tracking | `mujoco_direct_control_v1` | 不适用 | 原 timed evaluator |
| position + tool axis | `mujoco_direct_control_v1` | 不适用 | 位置与有向轴两个谓词 |
| loaded oriented Tracking | `mujoco_direct_control_v1` | 不适用 | 原时序、刚性工具与每步无接触门禁 |
| passive / 未支持主动模式 | 无合法控制方法 | 不适用 | 不以控制诊断建立被动成功 |

Direct 不生成 T1 科学身份，不成为 T2 来源。Response/Pattern、NMPC、Conic、T1/T2
数值算法未修改。原控制来源绑定、effort、Native 设置上限和 Worker 准入保持有效。
Main 仍只选择 `control_feasibility`，按需 Schema 中展示当前候选合法数值身份，
短 handoff 给出 `control_methods` 的身份、目的、准入状态和缺失项。

最小 Main 请求（无私有 ID，候选由完成的 diagnose 绑定）：

```json
{"version":"scientific_question_v4","domain":"control","control":{"question_type":"control_feasibility","effect_semantics":"reoptimized_task_capability","control_scope":{"mode":"full_task"},"control_search_effort":{"method":"response","knot_count":4,"iterations":1,"evaluation_requests":1}}}
```

对适用的 M4–M6，动态 Schema 的 `domain.const="control"`、
`control.question_type.const="control_feasibility"`，`numerical_method.enum` 仅包括
`null` 和当前候选目录可选择的方法。原 V1/V2/V3 Schema 不增加这个字段。

U1 定向验证：新增一个参数化 Mock 准入测试覆盖 M4/M5/M6 的正式候选生成、
initialize_control、V4 编译、T1/T2 拒绝和预算耗尽拒绝；复用原 M1 SDK/Mock、
T1 编译/原计费、Native 上限在 Worker 前拒绝的测试。所有数字与运动输出是 fixture。
真实 Provider、正式数学 Worker、新积分、正式 Replay 均为 0。
