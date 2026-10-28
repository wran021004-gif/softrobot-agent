# P2：共享真实 T1 反馈的 Thinking 配对结果

**后续更新：** 用户已批准全局 Provider 上限 15、本阶段上限 7，并完成第二轮相同反馈配对。两个模式均选择读取相同结果索引，两次真实工具响应一致；数学授权发现记录已修正。最新结果、账本和限制见 [第二轮报告](p2_feedback_paired_round2_zh.md)。以下为第一轮记录，保留当时用量和预算作为历史事实。

## 授权和配对边界

用户批准 P2 全局 Provider 上限 13、沿用已有候选和控制源、执行 T1—反馈—自主修订验证，并要求 Thinking-On/Off 相同输入条件；P3 不启动。原 P2-B 同一账本增加正式授权 addendum `af9eb892a1d1674c695a2a071160f0b16a48e370c305c1b3bc63ae411b17b97f`，原有两次保护额度保留，新阶段另外预留两次收尾额度，因此当前保护阈值为 4。原源 Study 已显式迁移至 `ce716cb2aeee231868ee65f9304dcc395ee5f378`，原科学 profile、候选、控制源和已计费历史保留。

直接执行入口使用冻结的 `D:/softrobot-agent/.mainline5-env/Scripts/python.exe`；它实际导入 MuJoCo 3.13.0、CasADi 3.7.2 和 Agent 依赖，线程限制均为 1。用户提到的 conda `softagent` 也有 MuJoCo 和 CasADi；本次使用已冻结的项目虚拟环境，未更换科学模型。

一次共享真实 T1 使用原候选 `ef2fbc71dc15f1e4fee75687e462e46f4d3d166702693be33d432f0969441a02` 和控制源 `67395ed42e34265a501c1fb6d8ec6f0601a9d860733d1c1911ecc618d9131130`：MuJoCo Native、初始预张力、0.6 s、0.02 s 控制周期、0.001 s 积分步、三腱 0–8 N；`local_control_search_v2` 最多 51 callbacks、1 iteration。原始结果 `b45d5e40b643f8c315077a8ea0812f6b7b2ab426f8a694446059fd1a3effec1f` 状态 `execution_incomplete`：`FactorizeHessian: rank-deficient sparse Hessian`，152 步完成、153 次步进尝试，0.152 s 处控制 `[2.4, 0.3, 3.75] N`，没有完成的回放或有限 J；1 个数学条目和 1.1106795 数值秒已计费。失败不能推出结构不可行。

两个模式收到同一个真实 T1 反馈、相同完整消息、任务包和工具 Schema；配对包 artifact `eb99b4ebc4f363f3cca989e00e11c4d054b02d2a486f7225a5a2769ff03612ad`。只有 `thinking` 与对应 `reasoning_effort` 不同；未复制历史 assistant reasoning。消息明确说明该 T1 是监督者执行的共享结果，没有冒充模型请求或工具历史。SDK 历史 offload 专用的 `retrieve_context` 未在两个新对照会话中提供，其余工具定义相同。两次均无自动重试。

## 真实结果

| 指标 | Thinking-On，高 | Thinking-Off |
| --- | ---: | ---: |
| 请求 | `r3-request-979d5dfe7ed44d15abfe5cdaac4ad7c1` | `r3-request-bcad1ad1e05249a5a234ed9a29bcd600` |
| HTTP / finish reason | 200 / tool_calls | 200 / tool_calls |
| 输入 / 输出 / 总 tokens | 36,617 / 5,520 / 42,137 | 36,592 / 322 / 36,914 |
| reasoning tokens | 4,171 | Provider 未报告 |
| Provider 墙钟 | 34.766 s | 2.516 s |
| 请求体 | 131,746 bytes | 131,721 bytes |
| 模型选择 | `research_plan.physical_replay` | 两次 `evidence_read` |

两组都完整返回，且两个原始请求除模式字段外完全一致。单个样本中 Off 输出更短、响应更快，但多出读取步骤；输入计费也有 25 tokens 差异，不能将配对条件误说成 Provider 计数完全相同。金额和 Off reasoning tokens 未报告。

On 没有修订结构或控制，而是选择用已有控制源进行独立物理回放，提出可检验目标，并把 T1 失败与结构不可行区分开。其完整方案通过实际准入并执行了 1 次回放；研究工具调用成功返回，但科学结果仍为 `execution_incomplete`，不能称为任务通过。回放 artifact `b0af68a98f46fe3fc533f0c058effeabf76d0fe83d4593c1f7f15ed8cbcf9e0f`，原始结果 `00a9c71d59e4d33e1a76056bbfa534ca8b2ddc693f9ba94a62e7f37d6e8b2f11`。回放在相同 0.152 s、相同控制 `[2.4,0.3,3.75] N` 遇到相同 Hessian 错误；终点误差、保持误差、保持速度和任务接受均未知。这两条真实执行都被保留，不将函数调用成功混同于物理任务成功。

Off 没有提交修订，而是请求检查工作集中的控制来源和候选。两项参数均通过静态 JSON Schema/Pydantic 和可见引用检查；实际执行时第一项对列表 `/control_result_links` 使用对象 `fields`，被拒绝为 `EVIDENCE_FIELDS_REQUIRES_OBJECT_POINTER`，第二项 `/candidate_index/0` 成功。错误反馈和成功结果分别保存在 artifacts `f47f4397059268b19cac5fe3641ea922ce4c6ea63d4e202a7cb4cc94fe5a359b` 和 `58431f8dc0060fcae037560b11277504b317749df46f0c28f8820dadfe279ece`。因此不能把静态契约通过当成完整动态工具准入通过，也不能把 Off 的读取选择当成已完成反馈驱动修订。

T1 通过监督者直接调用时，原数学入口记录了数学及数值费用，但没有经过 Agent 外层 public 调用计数。已追加独立的 `p2-feedback-paired-shared-t1-v1-public-accounting` 费用记录补计 1 public 操作；原 T1 收据未更改。Off 两项读取各计 1 public，On 回放的 Plan 计 1 public、1 独立物理回放。原始模型响应、工具参数、各调用结果和错误均已归档在同一个 Store。

## 账本与尚未完成的能力

P2-B 当前 8/13 Provider，剩余 5，其中原 Study 2 和本阶段 2 都受保护，仅 1 次未保护；9/28 public、1/2 数学条目、1/1 独立回放，累计 2.8108355 数值秒。加上 P2-A，整个 P2 累计 8 Provider、13 public、3 数学条目、2 次 T1 尝试、1 次独立回放、7.0716047 数值秒、352,799 Provider tokens。P2 原数值总上限 600 s 未变。本次所有工作均已结算，没有待处理 worker。

两种模式都未基于真实反馈提出并执行结构或控制修订，因此 T1—反馈—自主修订闭环**尚未完成**。保持两组相同的下一轮输入，需要至少两次新的决策请求；现仅有 1 次可用于探索，不能把它单独给某一组并声称仍为配对。当前 Study 维持 ready，未伪造模型 STOP；监督暂停及账本已记录于 artifact `7562b3697c1592d79702246833e1d8152def704edf730a84e04050438816cb54`。P3 仍为 `PENDING_EXPLICIT_P3_APPROVAL`。

若用户选择继续公平配对，一个具体增额方案是：将 P2 全局 Provider 上限从 13 提至 15，同时将本阶段 Provider 上限从 5 提至 7，保留原 2 次及本阶段 2 次收尾保护。两次新请求共享包含 T1、独立回放和两项读取结果的同一事实包，工具和输入完全相同，仅模式不同；两请求之后至少保留 5 次，其中 4 次保护、1 次探索余量。现有剩余 1 个数学条目、0 个独立回放及其余 public/数值上限不自动增加；因此若两组各提出需要独立数学评估的修订，现有预算不足以完整执行两次评估，必须如实停止或另获授权。新请求、预算变更和科学动作均不自动启动。
