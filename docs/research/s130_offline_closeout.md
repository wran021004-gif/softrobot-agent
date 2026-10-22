# S130 最后一次离线收敛（起点 ea230de8）

**第三轮原始 Reach 回答现在可以形成合法、非权威的 TaskIntakeDraft，并进入 N2。**
14 条要求、6 个原始问题、1 条时序关系全部保留；没有修改原始响应、删除问题或生成配置预览。
进一步编译停在问题审核，而不再停在 kind 格式或参考数值来源。

本轮零 Provider 请求、零新增 Provider tokens，不合并主线、不启动科研、不增加阶段。
历史仍为 15 次请求、52,057 tokens，货币费用未知。
[第三轮真实验证](s130_final_validation.md) 的失败记录不变；
[本轮摘要](s130_offline_closeout.json) 仅是新规则离线重放，不是新的真实调用成功率。

## 最小契约及接口变化

1. `RequirementProposal.kind=undefined` 现在表示未分类的缺失问题，**仅允许 source=undefined**。
   question 仍必填且与 quote/config_pointer 互斥；用户明确约束、配置事实和 llm_candidate
   都不能借此使用未分类类型。原 kind 字面值保留，不自动改写成验收类别。
2. `parse_response(..., trusted_reference=...)` 可验证问题引用的参考数字。
   原完整参考或任务源经既有 acceptance_view 重新投影，与提供的 AcceptanceView 整体比较，
   同时核对 source_identity、task_identity、facts 和派生字段。只提供一个 view/identity 不足以授权新数字。
   允许的是视图中的数值叶节点，以及原 adapter/投影已经给出的保持区间和限值；
   不解析版本字符串中的数字、不执行模型算式、不推导新阈值。
3. 程序给 DraftRequirement 添加只读 `numeric_references`；问题数字绑定实际来源路径和 source_identity。
   模型不能输出此字段，问题的 value 始终为 null。数字相同不代表单位、物理意义或阈值获准；
   问题仍需审核。N2 用自己的可信完整快照重算，再比较元数据，伪造 identity/路径/value 都会阻止编译。
4. `request_draft` 同样接受可选 trusted_reference，并在任何请求前检查上下文匹配；
   本轮没有实际调用。CLI 的 --context 会把原始参考源传给同一校验入口。
   未使用参考数字的原有调用兼容；需要引用参考独有数字时必须同时提供可信源。

本次 Reach 问题中的 `0.3` 被记录为：

```json
{
  "source_identity": "31af3e097ad29fef1ffd74c5178a6267fc5ffe35889c63e98f531dd42c0df69e",
  "numeric_references": {"0.3": ["view:/holding_interval_s/0"]},
  "value": null,
  "confirmation": "required"
}
```

来源是原可信快照的 `[0.30, 0.35] s` 保持区间，没有把问题转为配置。
无需仅为这项来源修复重发 LLM 请求。

## 只读已知条件与时序检查

`capabilities.reference_review` 并列展示经过验证的 facts、holding_interval_s、adapter_limits、
reference identity 和全部原始问题，所有问题保持 unresolved。
不使用语言关键词猜测某问题已经被回答，也不自动删除多余问题。

固定 Reach 额外允许检查 `hold_window during duration`：引用要求必须属于原有固定语法，
用户全部原文与参考值无冲突，且参考派生的最终窗口确实位于任务时长内。
它只确认既有时间区间的包含关系，不新增到达截止时间、连续时间保证或成功条件。
反向关系、throughout 整个 duration、before/after 到达关系仍需审核。

第三轮 Reach 的唯一关系现为 mapped；八条明确用户要求都映射成功。真实剩余阻碍为：

| 原始问题 | 现有证据与待审核事项 |
| --- | --- |
| 最终窗口是否为 `[0.3,0.35] s` | 已有可信派生区间；仍需确认这是重复问题，不能因程序看到相同数字就删除 |
| 终点/窗口位置误差的距离度量 | 可对照既有 evaluate.reach 与参考限值，由现有评价实现解释；不由 LLM 新定义 |
| 位置、速度如何观测/估计 | 已有 tip_position 的 world/m/post_step 定义及原保持验收接口；审核实际信号语义 |
| 窗口采样覆盖要求 | 参考 sample_period_s=0.01、含端点保持窗口及原组合协议可供核对；不新增连续时间要求 |
| 是否需要接触/碰撞约束 | 对照 reach_free 环境，判断是否只是多余澄清；若用户新增条件，不能默默并入现有 Reach |
| 是否有外部扰动/外力 | 参考 external_forces=[]；确认是否采用原设置，而不是自动创建扰动任务或假定新条件已满足 |

实际阻止预览的诊断是 UNRESOLVED_REQUIREMENT_MAPPINGS 和六项 MISSING_DEFINITION。
这里 MISSING_DEFINITION 是保留的模型未决问题，**不等于参考中对应事实全部缺失**；
真正未完成的是对这些声明与参考采纳的审核。本轮未实现审核批准或自动消解流程。
不存在额外的源校验失败或 TEMPORAL_RELATIONS_REQUIRE_REVIEW 阻碍。

## 三份原始响应的离线重放

| 案例 | 历史真实状态 | 新规则离线状态 | N2 / 预览 | 仍未解决的语义问题 |
| --- | --- | --- | --- | --- |
| Reach + Hold | Pydantic 拒绝六处 kind=undefined；无草稿、未进入 N2 | 合法草稿，全部原问题/关系保留 | 已进入；needs_review；无预览 | 六个问题需要对照参考审核，包含多余缺失声明 |
| 斜坡滚落接球 | 合法草稿；N2 不支持 | 合法草稿；原文、滚落机制、质量、捕获后保持与未知条件均保留 | 已进入；unsupported；无预览 | LLM 未主动识别接触/捕获/保持判据与评价器；N2 继续报告这些能力缺失 |
| 全身避障 Reach | 合法草稿；N2 不支持 | 合法草稿，全程全身避障保留，设计范围缺口可见 | 已进入；unsupported；无预览 | 模型仍遗漏“设计一条软臂”；没有把结构设计等同于控制既有机器人 |

本轮 **3/3 离线解析准入、3/3 进入 N2、0 配置预览**，没有新的模型语义得分。
接球、避障不再需要 Reach 快照或“采用参考配置”声明才能做语义诊断；Tracking 同样由回归覆盖。
TRUSTED_SESSION_INPUT_REFERENCE_REQUIRED / EXPLICIT_REFERENCE_SETTINGS_ADOPTION_REQUIRED
仅适用于支持的 Reach 配置预览路径。不支持任务仍保留全文未映射项、覆盖缺口及实际能力报告，
不能因这些误导性前置要求被移除而获得执行或评价能力。

原始三份回答逐字读取，没有补写模型问题；重放验证每条 proposal 字段和关系与原始 JSON 一致。
历史摘要中旧语义审查原样附在新摘要 historical_semantic_review 字段，作为旧证据，不是当前契约状态。

## 验证与证据保全

```powershell
$taskIntakePython = 'D:/softrobot-agent/.mainline5-env/Scripts/python.exe'
& $taskIntakePython -m tests.research.replay_task_intake --round-three --output runs/s130-closeout-replay-new
& $taskIntakePython -m tools.task_intake --file runs/s130-live-round3-20261022/01_reach_hold/task.txt --response-file runs/s130-live-round3-20261022/01_reach_hold/response.txt --context runs/s130-n2/reference.json --compile-reference runs/s130-n2/reference.json
```

第二条应返回退出码 2：草稿已成立，但问题未审核，没有预览；不是格式解析失败。
重放入口禁止 SDK/网络连接，输出目录必须全新。本次结果在
`runs/s130-offline-closeout-final-20261022/`，完整原始响应仍在原忽略目录。

原 59 项相关回归加 7 项新增边界测试：**66 tests 全通过，24.111 s**。
日志为本次目录 regression.txt；git diff --check 通过。
新增测试覆盖未分类类型越权、新数字、伪造视图/identity/数值来源/value、错误单位不能成为验收、
固定窗口包含关系、错误/更早时序、CLI 来源传递、请求前上下文校验及跨任务无 Reach 采纳前置。
省略设计范围的模型提取仍显示覆盖缺口并阻止错误配置。

实际三份重放均没有配置可执行；原 gate 在合法合成 draft 预览上仍抛出
DEVELOPMENT_HOST_REQUIRES_DEVELOPMENT_VALID。没有用真实问题删减版制造通过样例。
原验收组合和数学要求与无新增关系的相同参考预览完全相同，相关既有协议/验收/证据/主线回归通过。
未修改平台基础模块、冻结任务、数学实现、评价器、Agent/Reporter/Store/预算。
前三轮所有已登记历史证据、报告和原参考快照在重放前后哈希一致。

## 最终状态与主线可选接入

本轮离线收敛目标完成：旧 Reach 的非权威问题可进入审核链路，真正未决项仍阻止配置预览；
不支持任务保留语义并报告能力缺失。停止开发，交付验收，不继续追求无人审核的真实预览通过。

若后续选择作为独立任务准备入口接入主线，最小工作是传入明确可信参考源，调用现有
parse_response/compile_draft，并展示原文、覆盖缺口、known_conditions、原始问题和能力报告。
问题确认、正式配置修改、任务身份与审批仍由现有人工流程负责；不能自动转换为 development_valid。
本次离线结果不构成修改后 Prompt 的真实可靠性证明，也不替代正式科研准入。
