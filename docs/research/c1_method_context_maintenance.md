# C1 数学方法接口与上下文维护

**已修复目录中的参数缺失误判，并减少默认 L0 的重复来源和逐步控制细节。**
独立 worktree `.worktrees/c1-method-readiness-context`，分支 `feat/c1-method-readiness-context`，
基线为远端核验的 `e800389e76573ac9da3bfcf7c743d12f508cc5f2`。
已读 AGENTS、C1/C0 报告、原监督摘要、calls 和封存请求。没有启动 Study、Provider 或科研 worker，
没有打开、写入或重新导出原 C1 活动 Store；只读取新工作树自带的原封存归档。

## 方法准备状态

`analysis_capabilities()` 原来把没有 source/window 的目录查询直接交给执行级窗口检查，
得到 not_applicable。现在仅在目录中用冻结状态起点与任务期限检查所需覆盖，
不构造可执行 source，不填写 Agent 的结点、半径或科学参数。
原 `window_applicability()`、AnalysisRequest 及真实执行入口完全保留。

完整方法视图及紧凑目录增加 `planning_status`：

- `ready`：目录已知前提满足，仍需正式执行准入。
- `requires_parameters`：任务/模型支持，但本次请求的参数或来源尚未给出。
- `unsupported`：任务、物理、时域或模型条件确实不支持。
- `unauthorized` / `insufficient_budget`：缺少原授权或数学额度。
- `blocked`：Study 已停止或原 protected closeout 生效（包括首次完整通过后的科学工作阻挡）。

保留原 execution_status、kernel_supported、Study grant、完整覆盖和执行授权字段的各自含义。
目录声明列出的实现已存在，不能把 kernel/任务不支持解释成算法未实现。
MuJoCo-direct 的静态目录现在显示参数待补，明确列出 source 与 v2 settings，
完整按需视图提供原 AnalysisRequest Schema、合法控制来源、状态/窗口覆盖要求、
Reach/Hold-only 范围、native MuJoCo 模型和 physical_replay 交接。
所有方法共用查询 reference/view，每个条目保留准确 detail_pointer；没有第二份 Schema。

另修复两处实际不一致：

1. 授权投影原要求 user_approval 必须为布尔 true，且只识别 execution_scopes，
   未识别 C1 已由原 require_authorization 接受的文字批准和冻结 scope.capabilities 中的 analysis。
   现在沿用同一批准事实、原 scope_identity 和 Study/冻结身份绑定作展示；没有新增批准或执行 grant。
2. 已返回 control_schedule_reference 的数学结果原仍提示需要静态 input_sensitivity。
   现在提示使用原 physical_replay 的嵌套 candidate/source，并保留 unmeasured、独立评价及公开读取要求。

MuJoCo-direct 对 Tracking、外部载荷、未覆盖的保持样本和不匹配协议继续失败；缺 source 的实际 AnalysisRequest
仍由原 Schema 拒绝，完整合法请求仍通过原适用性检查。目录不授予执行权限。

## 默认上下文的变化

本次只改现有投影，没有改消息历史或增加 LLM 汇总：

- 数学目录保留简短科学用途、状态、预算、约束覆盖、关键成本和按需查询；
  详细描述、请求模板、模型/物理适用性和原 Schema 仍在原 mathematical_capabilities 视图。
- Reporter 默认 L0 不再另列 interpretation_sources；每个 interpretation 已携带完全相同的来源。
  完整 Reporter/L1 结果保持原样。
- L0 中 NMPC relevant_updates 保留求解状态、计划是否采用、失败响应、预测可用性、原始 source，
  恢复保留 attempted/selected/error；逐步张力和恢复目标值从默认 L0 移至原观察查询。
  完整 L1/L3 未删除这些细节，原全量控制工具反馈及 SDK 历史没有压缩或改写。
- 原 latest_scientific_feedback、latest_reports、additional_mathematical_evidence 已按结果引用
  合并展示的逻辑保持；best_valid 中独有的物理诊断、action_trace 和研究假设不因“看起来相似”被删除。

原 NMPC 的 Maximum_Iterations_Exceeded、计划可用、实际任务失败，以及不能据此断言结构不可行，
仍可同时看到。数学的求解状态、关键量、覆盖、适用边界、unmeasured 和后续评价要求全部保留。
任务硬约束、候选、研究意图、可选行动、预算、STOP 结果索引及正式 SELECT 读取门禁均未改变。

## 一次离线基线与等价输入对照

从原 16 个请求中选取 4 个真实主 Agent 请求，直接读取原 wire；断言重新序列化长度
与原 input_bytes 一致。新请求仅替换当前动态 L0，历史、reasoning、固定指令和 Tool Schema
逐项保持不变；不模拟新的 LLM 回答，也不声称已测得新会话的 Token、缓存命中或费用。

下表 L0 使用**紧凑 UTF-8 JSON**，wire 为包含外层字符串转义的完整 HTTP JSON body：

| 决策边界 | L0 原 / 新 bytes | L0 减少 | 原 wire / 等价新 wire bytes | wire 减少 |
| --- | ---: | ---: | ---: | ---: |
| 初始 | 37,675 / 35,064 | 6.93% | 78,644 / 75,763 | 3.66% |
| 完整 NMPC 失败后 | 64,967 / 57,042 | 12.20% | 125,435 / 116,878 | 6.82% |
| native 优化返回后 | 87,022 / 76,153 | 12.49% | 180,314 / 168,583 | 6.51% |
| 最终 SELECT 前 | 76,744 / 71,382 | 6.99% | 200,909 / 195,081 | 2.90% |

C1 原报告的 L0 39,831–92,088 bytes 使用带空格的 JSON 统计，序列化口径不同；
例如本次初始原 L0 同时核对为该口径的 39,831 bytes。不能跨口径计算压缩比例。

真实 wire 的可加分解如下；“reasoning”是移除 reasoning_content 字段的字节差，含字段 framing：

| 边界 | 固定指令 | 历史 assistant（不含 reasoning） | 历史 reasoning | 历史 tool 反馈 | 当前动态 tail | Tool Schema |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 初始 | 2,023 | 0 | 0 | 0 | 41,186 | 35,132 |
| NMPC 后 | 2,023 | 4,041 | 6,257 | 7,280 | 70,394 | 35,132 |
| native 后 | 2,023 | 10,997 | 27,464 | 10,249 | 94,135 | 35,132 |
| SELECT 前 | 2,023 | 33,251 | 44,010 | 22,463 | 82,955 | 15,877 |

另有原用户历史 162 bytes，以及 envelope/分隔符 141/146/152/168 bytes。
SELECT 前 Schema 较小来自原 protected closeout，未改此机制。
Reporter、科学反馈和引用属于上述 tail/tool 内容的子部分，不能再与总额相加：
探索阶段数学目录 14,992→12,271 bytes（收尾为 12,390，包含原 closeout 阻挡）；NMPC 后 latest_reports 19,784→14,470；
native 后 latest_reports 36,594→28,438；SELECT 前 22,776→19,906。
每个研究区块和真实 request_id 的精确分解见
[context_comparison.json](../../evidence/c1_method_context_maintenance/context_comparison.json)。
没有把自由文本历史进一步强行切成科学事实/解释/引用的精确 Token 份额，细分未知。

既有 C1 Provider 用量仍为 prompt 635,639（cache hit 271,616）、completion 26,799，
本次没有重新测量。原 capacity_estimate 在这些长度下使用 serialized UTF-8 byte upper estimate，
对照文件保留该原估计；它不是实际 prompt-token 数。固定前缀和历史没有变更，
未来新会话实际 Token/缓存表现、减少错误请求的收益仍待另行授权验证。
仍有较大的方法目录、Reporter 与会话历史；本次未追求强制压缩率或重构稳定上下文机制。

## C1 七类错误的针对性提示

| 已观察错误 | 处理 |
| --- | --- |
| candidate_index 被当作候选原字段 | fields 错误导航提供原 working_set 的准确 derived_view_query |
| native 缺初态来源 | 指出 frozen initialization 与 saved_state 两种原接口，以及按需方法详情 |
| physical_replay 多余顶层 candidate | 提示原嵌套 physical_replay.candidate/source，保留原 Schema 拒绝 |
| decision candidate 不一致 | 明确匹配 action 中的候选，source 不能替代 candidate |
| 不存在 task_passed | 提供原 /acceptance 查询；不制造字段或替换调用 |
| 未满足 exact_actual_read | 提示对精确物理结果进行原全结果公开读取 |
| 缺正式评价读取标记 | 明确 /acceptance 局部读取与 whole-result 读取的区别，再 SELECT |

没有自动补写科学参数、转换不合法请求、跳过读取门禁或新增错误解析平台。

## 验证、代码量与交付

5 项离线测试最终通过：新测试模块 4 项，覆盖目录/原执行边界、授权与预算、
冻结上下文/字节对照、错误导航/控制交接；复用原 S138 条件准入与静态假设回归 1 项。
验证了真实 C1 数值与数学 scope、Reporter interpretation 来源、任务、预算和证据引用保持，
历史/Schema 未被重写。测试夹具禁止 Store transaction/reserve；没有科研 worker 或 Provider 请求。
初期夹具的冻结模型赋值、缺失诊断字段及不完整 Tracking/载荷定义已修正，未放松生产校验。
未运行全仓库或历史数值搜索；git diff --check 通过。

生产修改 **5 文件 +71/−14 行，净增 57 行**，测试模块 197 行，复用原归档和 mock 边界。
没有新增生产模块、Agent、Store、目录、Schema、记忆/预算系统或 SHA manifest。
MuJoCo-direct、native 数值、GVS、T1/T2 内核、TaskDefinition、预算、receipt、幂等恢复、
Strands 历史、DeepSeek reasoning、发送/恢复、Live Handoff 和 Offload 全部保留。
原 C1 分支仍为 e800389e7，工作树干净；原证据路径在本分支无修改。

实现/定向回归提交：`ef84484c`。本报告与标量对照单独提交，普通推送
[`feat/c1-method-readiness-context`](https://github.com/wran021004-gif/softrobot-agent/tree/feat/c1-method-readiness-context)，
不强推、不合并 main；最终提交号和干净工作树核验见交付回复。

**下一步建议：已具备开展下一次低预算自主设计 Study 的工程条件。**
尚需真实验证 Agent 能否自主提出合法结构对照、为各候选给出公平重优化预算、
识别初始化不足与数值未收敛，正确使用条件性的结构敏感性并形成可反驳判断。
C1 的单任务控制成功不证明结构最优、可靠的最优能力梯度或跨任务泛化。
本次没有启动下一项 Study，也没有以离线压缩对照替代这些科研验证。
