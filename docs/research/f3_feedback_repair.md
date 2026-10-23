# F3 证据反馈与请求边界修复

本次修复属于同一个 Study `f3-autonomous-20261022-01` 的显式实施迁移。冻结任务、FamilySpace、正式授权与预算不变。迁移前所有调用、失败、验收和成本保留；新结果不得冒充旧控制实现下的可比实验。下一次科研请求须等待回归测试、提交与绑定完成。

## 数学授权与就绪条件

正式授权 artifact `04f53584daddc0a4c29f1e1e365d71c26f27a5f8378a4cede2cc033925098491` 已批准本次 Study 的 registered mathematics。冻结配置里的 “Proposed … blocked until independent Study approval” 是批准之前留下的描述，不能覆盖正式授权。

首次数学能力审计 `D:/softrobot-agent-audits/f3-interruption-review/f3_math_effectiveness.json` 中，SOCP (`sampled-affine-conic-minimax-v1`) 为 `conditional`；T2 (`controlled-capability-sensitivity-v1`) 缺少候选变量及已注册模型 stencil，显示 `not_applicable`，实际调用均为 0。这表示当时材料不齐，不能解释为整条路线被禁止，也不能据此自动放行 T2。

当前 Agent 决策反馈分别呈现正式授权引用、冻结方法 grant、配置原文及候选/变量/模型组/依赖/预算准入。冻结原文不改写，方法执行校验保留。授权不会补出缺失的模型、合法索引或数值预算。

## 已确认的工程缺陷

1. 旧接续边界等待整个 SDK `invoke_async()` 自然返回；连续工具循环一直留在第一次 invocation。新边界位于真实模型响应及完整工具反馈落盘、所有调用结算、Reporter 交付之后，下一次模型请求之前。原始 wire、响应、reasoning、工具 ID、反馈、SDK offload 均需一致；prepare、独立恢复、校验和原子指针提交后才继续。旧 invocation 记录为 suspended，`invocation_completed=false`；接续不是一次新 Provider 调用，也不重置预算。首次真实准入与首次接续后真实请求须另行留证。
2. NLP 原始目标为 0、位置/速度 slack 均为 0、SQP exitflag 1；严格原始判定仍为 false。保存的速度正违规分别约 `7.11e-16 m/s`（返回值）和 `1.59e-14 m/s`（重算值）。新反馈同时交付这些量级、单位、原始判定、slack、收敛状态、inconclusive 范围及 `physical_validation=not_run`，不修改容差或判定为通过，也不把本次严格 false 当作全局不可行证据。
3. MATLAB JSON 在剩余 horizon=1 时省略矩阵单行维度。旧 Python 取 `tensions[0]` 得到标量，经 NumPy 广播成为四个相同的实际输入；位置和速度预测也被取成标量。五次 NMPC 的 update 34 均确认计划输入与实际输入不匹配，且均记录为接纳计划、未使用 fallback。修复在选择输入前恢复明确的矩阵轴，校验状态/输入/三维输出形状与有限值，并在理想张力桥拒绝标量广播。新更新保存实际求解终止、接纳、恢复、最终输入及原始求解请求。此修复改变实际控制行为，必须显式版本化。旧独立物理验收描述真实执行，继续有效；不能推断修复后必然通过。
4. 原始三次 Reporter 拒绝的 source IDs 均属于当次持久化 catalog；旧校验漏纳关键采样点/输入来源。修复接受精确请求 catalog 中的已验证来源，仍拒绝未知 ID、越界来源和非法路径，并保存结构化拒绝位置。三份原始响应已在离线重新验证，新增报告版本；原拒绝版本和当时交付历史保留，没有重发或新增收费。

## 反馈与检索

结果提供可执行的原 artifact、JSON Pointer、range 查询和同一 update 绑定；gzip 轨迹可通过既有 evidence_read 读取。错误返回合法字段和下一步查询，派生 working_set 路径不会被当成原 artifact 路径。SoRoSim 的完整 solver request 与既有 CasADi `complete_update_record` 是不同契约：新记录明确不支持直接精确重放，缺失旧完整契约时仍拒绝相应诊断。

候选反馈展示实际解析的截面、密度、黏性、腱顺序、安装位姿与世界坐标，以及相对于按构造事件排序的前一候选的全部参数差异。多参数变化不被包装成单因素因果证据。Agent 的解释保留为假设，辨别观察的取得由已保存科学结果引用标识；工具调用成功不等于科学验证。代码修复不能保证后续模型推理必然正确。

旧五次预测汇总通过只读投影标记不可用于模型误差诊断；旧 artifact 不改写。静态计算也显式反馈求解状态、位置/平衡残差、张力及局部条件。下一次 Agent 请求收到带原始引用的 [证据修正](../../evidence/f3_formal/feedback_repair_20261023/recorded_evidence_correction.json)，避免已有 NLP 和控制记录在接续中丢失。

## 验证记录

- [离线测试](../../evidence/f3_formal/feedback_repair_20261023/offline_tests.json)：真实 SDK/Store 与 mock HTTP，禁止新增 Provider、MATLAB、物理 rollout 或训练。
- [保存证据回读](../../evidence/f3_formal/feedback_repair_20261023/verification.json)：五次执行的全部广告查询及逐 update 引用已执行，科学 artifact 与账本不变。
- [控制诊断](../../evidence/f3_formal/feedback_repair_20261023/control_diagnostics.json)：原验收与逐 update 计划/实际输入、状态、来源。
- [Reporter 重新验证](../../evidence/f3_formal/feedback_repair_20261023/reporter_revalidation.json)：仅重读已保存请求/响应，新增模型请求为 0。

修复审计时 Provider 为 47/128、公共操作 59/400、物理调用 8/80、NMPC 5/6、数学 2/64、offline NLP 1/2。没有获得完整任务通过结论。完整 Store 和 SDK checkpoint 保留在本机，新的原始会话包未纳入本次推送。

## 实际恢复

修复 `07fde5ed` 已推送并通过既有 `core.bind` 显式迁移为评估版本 2；[迁移回执](../../evidence/f3_formal/feedback_repair_20261023/implementation_binding.json) 保留原候选及全部结果与成本，未把旧候选静默绑定到新版本。新候选与科研路线仍由主 Agent 自主选择。

首次真实只读准入发现 Provider 字符串正文与 SDK 文本块列表的表示差异，原文、reasoning、工具 ID 和解析后的参数均一致。拒绝发生时未发送新请求。`55d1b988` 仅规范化精确文本的表示形式，保留逐字符检查；19 项接续/准入/恢复测试通过，[后续绑定](../../evidence/f3_formal/feedback_repair_20261023/boundary_format_binding.json) 保持科学版本 2 和账本不变。

真实请求反馈边界准入已通过，`live_admitted=true`。恢复后的真实工具反馈边界完成 v3 prepare、独立 SDK 恢复验证和原子提交，当时累计 Provider 48 次；其后的新会话请求返回 HTTP 200，正文为 209,579 字节。请求明确携带研究意图、原预算、候选版本绑定、证据修正与正式数学授权；原 invocation 为 suspended，`invocation_completed=false`，没有伪造自然返回。详见 [实际接续证明](../../evidence/f3_formal/feedback_repair_20261023/live_resume_verification.json)。

该证明记录时 Provider 52/128、物理调用 8/80、NMPC 5/6。主 CLI 与每 10 秒检查的监督进程均存活，心跳为 `runs/f3-formal-supervision.json`。运行将继续消耗同一个原始账本；证明中的数字为采样时点，不是最终用量。T2 当前还需新实施版本下的合法候选与完整绑定模型组；方法授权继续有效。未声明获得完整任务通过结果。

## 后续完成与 HTTP 200 调查

上述运行随后于北京时间 2026-10-23 05:09:59 取得首次完整原任务仿真通过，并按原冻结规则完成公开验收读取、选择和封存。最终 Provider 63/128、物理调用 27/80，NMPC 5/6。HTTP 200 是成功状态；接续后已保存的响应均可解析、finish_reason 完整、回执结算，没有 HTTP 故障。对原始 36 个轨迹样本、6 个保持段样本和四通道实际张力的只读复核与原验收一致，未新增模型请求或物理执行。当前 `phase=complete, status=stopped` 是正常结束，已无后台运行需求。详见 [调查回执](../../evidence/f3_formal/feedback_repair_20261023/http200_investigation.json)。
